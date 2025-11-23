"""基于 OCR 的开奖号码读取器。"""
from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

import warnings

import numpy as np
from PIL import Image

from src.automator.window_manager import WindowManager
from src.data.models import LotteryResult


class LotteryOCRReader:
    """负责从计划接口窗口 OCR 提取最新开奖期号与号码。"""

    def __init__(self, lottery_config: dict[str, Any], window_manager: Optional[WindowManager] = None) -> None:
        """保存配置并准备日志。"""

        self.logger = logging.getLogger(self.__class__.__name__)
        self._lottery_config = lottery_config or {}
        self._ocr_config = self._lottery_config.get("ocr", {}) or {}
        self._reader = None
        self._debug_capture_path = self._ocr_config.get("debug_capture_path")
        self._window_manager = window_manager
        self._window_title = self._ocr_config.get("window_title", "")
        self._window_region_cfg = self._ocr_config.get("window_region", {}) or {}

    @property
    def enabled(self) -> bool:
        """指示是否启用 OCR 数据源。"""

        return bool(self._ocr_config.get("enabled", False))

    def capture_latest_result(self) -> Optional[LotteryResult]:
        """尝试截屏识别开奖信息，成功则返回 LotteryResult。"""

        if not self.enabled:
            return None

        max_retries = max(1, int(self._ocr_config.get("max_retries", 3)))
        retry_interval = max(1, int(self._ocr_config.get("retry_interval", 2)))

        for attempt in range(1, max_retries + 1):
            try:
                text_lines = self._read_text_lines()
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.warning("OCR 截屏或识别失败（尝试 %s/%s）: %s", attempt, max_retries, exc)
                text_lines = None

            if text_lines:
                result = self._parse_lottery_from_lines(text_lines)
                if result:
                    return result
                self.logger.debug("OCR 文本未解析出期号，等待后重试...")

            if attempt < max_retries:
                time.sleep(retry_interval)

        return None

    def _read_text_lines(self) -> Optional[List[str]]:
        """截取配置区域并使用 easyocr 识别文本。"""

        import pyautogui

        reader = self._get_reader()
        rect = self._get_window_rect()
        screenshot: Optional[Image.Image] = None
        region_desc = ""

        if rect:
            window_region = (rect.left, rect.top, rect.width(), rect.height())
            self.logger.debug("采用窗口OCR，区域=%s", window_region)
            screenshot = pyautogui.screenshot(region=window_region)
            region_desc = f"window={window_region}"
        else:
            region = self._normalize_region()
            if not region:
                self.logger.warning("OCR 区域未配置，无法识别开奖数据")
                return None
            screenshot = pyautogui.screenshot(region=region)
            region_desc = f"config={region}"

        if not isinstance(screenshot, Image.Image):
            self.logger.warning("无法截取开奖窗口图像")
            return None

        # 保存调试截图（直接保存整窗）
        self._save_debug_capture(screenshot)

        img_array = np.array(screenshot)
        self.logger.debug("开始识别开奖 OCR 文本，区域来源=%s", region_desc)
        results = reader.readtext(img_array)
        if not results:
            self.logger.warning("OCR 未识别到任何文本")
            return None
        lines = [text.strip() for (_, text, _) in results if text]
        if not lines:
            self.logger.warning("OCR 识别结果为空文本")
            return None
        for idx, line in enumerate(lines, 1):
            self.logger.info("开奖OCR[%d]: %s", idx, line)
        return lines

    def _save_debug_capture(self, screenshot: Image.Image) -> None:
        """保存调试截图，便于分析 OCR 失败。"""

        if not self._debug_capture_path:
            return

        try:
            path = Path(self._debug_capture_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            screenshot.save(path)
            self.logger.info("已保存开奖 OCR 调试截图: %s", path)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.warning("保存开奖 OCR 调试截图失败: %s", exc)

    def _get_reader(self):
        """创建并缓存 easyocr Reader。"""

        if self._reader:
            return self._reader

        try:
            import easyocr
        except ImportError as exc:  # pylint: disable=broad-except
            raise RuntimeError("easyocr 未安装，无法执行开奖 OCR") from exc

        warnings.filterwarnings(
            "ignore",
            message="'pin_memory' argument is set as true but no accelerator is found",
        )
        languages = self._ocr_config.get("languages") or ["ch_sim", "en"]
        self.logger.info("初始化 easyocr 识别器，语言=%s", languages)
        self._reader = easyocr.Reader(languages, gpu=False)
        return self._reader

    def _get_window_rect(self):
        """优先获取配置子窗口的矩形。"""

        if not self._window_manager:
            return None
        if self._window_title:
            rect = self._window_manager.get_window_rect(self._window_title)
            if rect:
                return rect
        main_window = self._window_manager.main_window
        if not main_window:
            return None
        try:
            return main_window.rectangle()
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.debug("获取窗口矩形失败: %s", exc)
            return None

    def _normalize_region(self) -> Optional[tuple[int, int, int, int]]:
        """把配置的区域转换为 pyautogui 使用的 (x, y, w, h)。"""

        region = self._ocr_config.get("region")
        if not isinstance(region, (list, tuple)) or len(region) != 4:
            return None
        try:
            x, y, width, height = (int(value) for value in region)
        except (TypeError, ValueError):
            return None
        if width <= 0 or height <= 0:
            return None
        return (x, y, width, height)

    def _compute_window_region(self, rect) -> Optional[Tuple[int, int, int, int]]:
        if not rect:
            return None
        offset_x = int(self._window_region_cfg.get("offset_x", 0))
        offset_y = int(self._window_region_cfg.get("offset_y", 0))
        width = int(self._window_region_cfg.get("width", rect.width()))
        height = int(self._window_region_cfg.get("height", rect.height()))
        left = rect.left + offset_x
        top = rect.top + offset_y
        left = max(rect.left, min(left, rect.right - width))
        top = max(rect.top, min(top, rect.bottom - height))
        return (left, top, width, height)

    def _locate_lottery_anchor(self, reader, full_image_array, rect) -> Optional[Tuple[int, int, int, int]]:
        if not rect:
            return None
        try:
            results = reader.readtext(full_image_array)
            self.logger.debug("开奖全窗口识别 %d 个文本区域", len(results))
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.debug("开奖锚点识别失败: %s", exc)
            return None

        anchor_keywords = ["开奖号码", "奇趣腾讯", "开奖", "期开奖号码"]
        for bbox, text, prob in results:
            normalized = text.strip().replace(" ", "")
            if not normalized:
                continue
            if not any(keyword in normalized for keyword in anchor_keywords):
                continue
            gap = int(self._window_region_cfg.get("anchor_gap", 20))
            width = int(self._window_region_cfg.get("width", rect.width()))
            height = int(self._window_region_cfg.get("height", rect.height()))
            left = rect.left + int(min(pt[0] for pt in bbox))
            top = rect.top + int(max(pt[1] for pt in bbox)) + gap
            left = max(rect.left, min(left, rect.right - width))
            top = max(rect.top, min(top, rect.bottom - height))
            self.logger.info("开奖锚点匹配 '%s' -> 区域(%d,%d,%d,%d)", text.strip(), left, top, width, height)
            return (left, top, width, height)
        return None

    def _crop_region_from_window(self, screenshot, target_region, rect) -> Optional[Image.Image]:
        if not screenshot or not target_region or not rect:
            return None
        left, top, width, height = target_region
        local_left = left - rect.left
        local_top = top - rect.top
        local_right = local_left + width
        local_bottom = local_top + height
        if local_left < 0 or local_top < 0:
            return None
        if local_right > screenshot.width or local_bottom > screenshot.height:
            return None
        return screenshot.crop((local_left, local_top, local_right, local_bottom))

    def _parse_lottery_from_lines(self, lines: List[str]) -> Optional[LotteryResult]:
        """从 OCR 结果中查找期号与开奖号码。"""

        if not lines:
            return None

        period_length = int(self._ocr_config.get("period_length", 12))
        numbers_length = int(self._ocr_config.get("numbers_length", 5))
        joined_text = " ".join(lines)
        period_match = re.search(rf"(\d{{{period_length}}})", joined_text)
        if not period_match:
            self.logger.debug("OCR 文本中未匹配到期号: %s", joined_text)
            return None

        period = period_match.group(1)
        remaining_text = joined_text[period_match.end():]
        digit_tokens = re.findall(r"\d", remaining_text)
        if len(digit_tokens) < numbers_length:
            self.logger.debug("OCR 文本中开奖号码位数不足: %s", remaining_text)
            return None

        numbers = [int(token) for token in digit_tokens[:numbers_length]]
        numbers_raw = "".join(digit_tokens[:numbers_length])
        open_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info("OCR 识别到开奖：期号 %s，号码 %s", period, numbers_raw)
        return LotteryResult(period=period, numbers=numbers, open_time=open_time)
