"""基于 OCR 的开奖号码读取器。"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any, List, Optional

from PIL import Image

from src.data.models import LotteryResult


class LotteryOCRReader:
    """负责从计划接口窗口 OCR 提取最新开奖期号与号码。"""

    def __init__(self, lottery_config: dict[str, Any]) -> None:
        """保存配置并准备日志。"""

        self.logger = logging.getLogger(self.__class__.__name__)
        self._lottery_config = lottery_config or {}
        self._ocr_config = self._lottery_config.get("ocr", {}) or {}
        self._reader = None

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

        import numpy as np
        import pyautogui

        reader = self._get_reader()
        region = self._normalize_region()
        if not region:
            self.logger.warning("OCR 区域未配置，无法识别开奖数据")
            return None

        screenshot = pyautogui.screenshot(region=region)
        if not isinstance(screenshot, Image.Image):
            self.logger.warning("无法截取开奖窗口图像")
            return None

        img_array = np.array(screenshot)
        self.logger.debug("开始识别开奖 OCR 文本，区域=%s", region)
        results = reader.readtext(img_array)
        if not results:
            self.logger.debug("OCR 未识别到任何文本")
            return None
        return [text.strip() for (_, text, _) in results if text]

    def _get_reader(self):
        """创建并缓存 easyocr Reader。"""

        if self._reader:
            return self._reader

        try:
            import easyocr
        except ImportError as exc:  # pylint: disable=broad-except
            raise RuntimeError("easyocr 未安装，无法执行开奖 OCR") from exc

        languages = self._ocr_config.get("languages") or ["ch_sim", "en"]
        self.logger.info("初始化 easyocr 识别器，语言=%s", languages)
        self._reader = easyocr.Reader(languages, gpu=False)
        return self._reader

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

    def _parse_lottery_from_lines(self, lines: List[str]) -> Optional[LotteryResult]:
        """从 OCR 结果中查找期号与开奖号码。"""

        if not lines:
            return None

        period_length = int(self._ocr_config.get("period_length", 12))
        numbers_length = int(self._ocr_config.get("numbers_length", 5))
        pattern = re.compile(
            rf"(\d{{{period_length}}})(?:期)?[\u4e00-\u9fa5：:]*?(\d{{{numbers_length}}})"
        )
        joined_text = " ".join(lines)
        match = pattern.search(joined_text)
        if not match:
            self.logger.debug("OCR 文本中未匹配到期号/开奖号码: %s", joined_text)
            return None

        period = match.group(1)
        numbers_raw = match.group(2)
        numbers = [int(char) for char in numbers_raw]
        open_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info("OCR 识别到开奖：期号 %s，号码 %s", period, numbers_raw)
        return LotteryResult(period=period, numbers=numbers, open_time=open_time)
