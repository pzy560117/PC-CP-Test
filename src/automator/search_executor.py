"""公式搜索执行器和结果提取器。"""
from __future__ import annotations

import logging
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pyautogui

from src.automator.window_manager import WindowManager
from src.exception.custom_exceptions import AutomationException


class SearchExecutor:
    """负责执行搜索和提取结果。"""

    def __init__(self, window_manager: WindowManager, search_config: Dict[str, Any]) -> None:
        """初始化搜索执行器。
        
        Args:
            window_manager: 窗口管理器实例
            search_config: 搜索配置字典
        """
        self._window_manager = window_manager
        self._config = search_config or {}
        self._ocr_region_config: Dict[str, int] = self._config.get("ocr_stats_region", {})
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute_search(self) -> None:
        """执行公式搜索（失败后自动重试2次）。
        
        Raises:
            AutomationException: 搜索失败时抛出
        """
        max_retries = 2
        retry_delay = 0.5
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.warning("搜索失败，%.1f秒后进行第 %d 次重试...", retry_delay, attempt)
                    time.sleep(retry_delay)
                
                self.logger.info("开始执行搜索... (尝试 %d/%d)", attempt + 1, max_retries + 1)
                
                main_window = self._window_manager.main_window
                if not main_window:
                    raise AutomationException("主窗口未连接")
                
                # 查找"开始搜索"按钮
                search_button = self._find_search_button()
                
                if search_button:
                    # 高亮显示搜索按钮
                    self._window_manager.highlight_control(search_button, duration=0.2)
                    # 点击搜索按钮
                    search_button.click_input()
                    self.logger.info("已点击搜索按钮")
                else:
                    # 使用图像识别备用方案
                    self.logger.warning("UI Automation 未找到搜索按钮，尝试图像识别...")
                    
                    image_files = [
                        "start_search_button.png",
                        "search_button.png",
                        "kaishi_sousuo.png",
                        "begin_search.png"
                    ]
                    
                    found = False
                    for image_file in image_files:
                        if self._click_by_image(image_file, confidence=0.8):
                            self.logger.info("通过图像识别成功点击搜索按钮")
                            found = True
                            break
                    
                    if not found:
                        raise AutomationException("未找到搜索按钮，请截取'开始搜索'按钮并保存为 images/start_search_button.png")
                
                # 等待搜索完成
                self._wait_for_search_complete()
                
                # 成功则返回
                self.logger.info("搜索执行成功")
                return
                
            except Exception as exc:
                if attempt < max_retries:
                    self.logger.error("搜索执行失败: %s，将重试...", exc)
                    continue
                else:
                    # 最后一次尝试也失败，抛出异常
                    self.logger.error("搜索执行失败，已重试 %d 次", max_retries)
                    raise AutomationException("执行搜索失败") from exc

    def extract_top_results(self, max_results: int = 5) -> List[List[int]]:
        """提取右侧"推荐号统计"区域的TOP N号码。
        
        Args:
            max_results: 最大结果数量（取出现次数最多的前N个号码）
            
        Returns:
            推荐号码列表，每个元素是单个号码（按出现次数排序）
            
        Raises:
            AutomationException: 提取失败时抛出
        """
        self.logger.info("开始提取推荐号统计（TOP %d）...", max_results)
        
        try:
            main_window = self._window_manager.main_window
            if not main_window:
                raise AutomationException("主窗口未连接")
            
            # 提取右侧统计区域的TOP号码
            top_numbers = self._extract_statistics_area(max_results)
            
            if not top_numbers:
                self.logger.warning("未提取到推荐号码，回退到表格提取")
                # 回退：提取表格数据
                results = self._extract_table_data(max_results)
                return results
            
            # 返回单个列表（所有TOP号码组成一个推荐）
            self.logger.info("成功提取 TOP%d 推荐号码: %s", max_results, top_numbers)
            return [top_numbers]  # 返回单个推荐列表
            
        except Exception as exc:
            raise AutomationException("提取搜索结果失败") from exc

    def _click_by_image(self, image_name: str, confidence: float = 0.8, timeout: int = 10) -> bool:
        """通过图像识别点击（带显式等待）。
        
        Args:
            image_name: 图片文件名（相对于 images/ 目录）
            confidence: 匹配置信度（0-1）
            timeout: 等待超时时间（秒）
            
        Returns:
            是否成功找到并点击
        """
        try:
            image_path = Path("images") / image_name
            if not image_path.exists():
                self.logger.warning("图片不存在: %s", image_path)
                return False
            
            self.logger.info("通过图像识别查找: %s (超时: %ds)", image_name, timeout)
            
            # 显式等待：循环查找直到找到或超时
            start_time = time.time()
            location = None
            
            while time.time() - start_time < timeout:
                try:
                    location = pyautogui.locateOnScreen(str(image_path), confidence=confidence)
                    
                    if location:
                        break
                    
                    # 未找到，等待0.5秒后重试
                    time.sleep(0.5)
                    
                except Exception:
                    # 识别失败，继续重试
                    time.sleep(0.5)
                    continue
            
            if location:
                center = pyautogui.center(location)
                elapsed = time.time() - start_time
                self.logger.info("找到图像位置: %s (耗时: %.1fs)", location, elapsed)
                pyautogui.moveTo(center.x, center.y, duration=0.1)  # 加快移动
                time.sleep(0.05)  # 减少等待
                pyautogui.click(center.x, center.y)
                self.logger.info("✓ 已点击: %s", image_name)
                return True
            else:
                self.logger.warning("等待 %ds 后仍未找到图像: %s", timeout, image_name)
                return False
                
        except Exception as exc:
            self.logger.error("图像识别失败: %s", exc)
            return False

    def _find_search_button(self) -> Optional[Any]:  # UIAWrapper
        """查找搜索按钮。
        
        Returns:
            搜索按钮控件，未找到返回 None
        """
        main_window = self._window_manager.main_window
        if not main_window:
            return None
        
        # 查找所有按钮
        buttons = main_window.descendants(control_type="Button")
        
        # 按钮文本可能是"开始搜索"、"搜索"等
        search_keywords = ["开始搜索", "搜索", "Search"]
        
        for button in buttons:
            try:
                button_text = button.window_text()
                for keyword in search_keywords:
                    if keyword in button_text:
                        self.logger.debug("找到搜索按钮: %s", button_text)
                        return button
            except Exception:  # pylint: disable=broad-except
                continue
        
        return None

    def _wait_for_search_complete(self) -> None:
        """等待搜索完成。
        
        Raises:
            AutomationException: 超时时抛出
        """
        timeout = int(self._config.get("search_timeout", 300))
        # 宽限时间：如果始终检测不到“停止”按钮激活，则在该时间后假定搜索已完成
        grace_seconds = 15
        self.logger.info("等待搜索完成（超时: %d秒）...", timeout)

        start_time = time.time()
        check_count = 0
        search_started = False  # 标记是否曾检测到搜索进行中

        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = time.time() - start_time

            # 检查搜索状态
            is_searching = self._is_searching()

            if is_searching:
                if not search_started:
                    self.logger.debug("检测到搜索开始（停止按钮已激活）")
                search_started = True
                if check_count % 5 == 0:
                    self.logger.info("搜索进行中... 已等待 %d 秒", int(elapsed))
            else:
                if search_started:
                    # 搜索曾经开始，现在检测为未搜索，说明已完成
                    self.logger.info("✓ 搜索已完成（耗时 %d 秒）", int(elapsed))
                    time.sleep(0.5)  # 额外等待0.5秒确保UI更新完成
                    return

                # 从未检测到搜索开始，可能是停止按钮无法识别
                if elapsed >= grace_seconds:
                    self.logger.warning(
                        "在 %d 秒内未检测到‘停止’按钮激活，可能无法判断搜索状态，"
                        "假定搜索已完成，继续后续步骤。",
                        int(elapsed),
                    )
                    time.sleep(0.5)
                    return

            time.sleep(1)

        raise AutomationException(f"搜索在 {timeout} 秒内未完成")
    
    def _is_searching(self) -> bool:
        """检查搜索是否正在进行。
        
        Returns:
            True 表示正在搜索，False 表示未在搜索
        """
        main_window = self._window_manager.main_window
        if not main_window:
            return False
        
        try:
            # 检查"停止"按钮是否活跃
            buttons = main_window.descendants(control_type="Button")
            for button in buttons:
                try:
                    button_text = button.window_text()
                    if "停止" in button_text or "Stop" in button_text:
                        if button.is_enabled():
                            return True
                except Exception:  # pylint: disable=broad-except
                    continue
            
            return False
        except Exception:  # pylint: disable=broad-except
            return False

    def _extract_statistics_area(self, max_count: int) -> List[int]:
        """提取右侧"推荐号统计"区域的TOP号码。
        
        Args:
            max_count: 提取数量
            
        Returns:
            TOP号码列表，按出现次数降序
        """
        main_window = self._window_manager.main_window
        if not main_window:
            return []
        
        # 方法1：尝试遍历所有控件类型（Text, ListItem, DataItem等）
        number_stats = self._extract_from_ui_controls()
        
        # 方法2：如果方法1失败，使用OCR识别
        if not number_stats:
            self.logger.info("UI控件提取失败，尝试使用OCR识别...")
            number_stats = self._extract_by_ocr()
        
        # 方法3：仍失败时，基于表格内容计算统计
        if not number_stats:
            self.logger.info("OCR识别失败，尝试基于表格数据统计推荐号...")
            number_stats = self._compute_statistics_from_table_counts()
        
        if not number_stats:
            self.logger.warning("所有方法均未找到推荐号统计数据")
            return []
        
        # 按次数降序排序
        number_stats.sort(key=lambda x: x[1], reverse=True)
        
        # 提取TOP N个号码
        top_numbers = [num for num, count in number_stats[:max_count]]
        
        self.logger.info("✓ 推荐号统计:")
        for i, (num, count) in enumerate(number_stats[:max_count], 1):
            self.logger.info("  #%d: 号码 %d (出现 %d 次)", i, num, count)
        
        return top_numbers

    def _extract_from_ui_controls(self) -> List[Tuple[int, int]]:
        """从UI控件提取统计数据。
        
        Returns:
            [(号码, 次数), ...] 列表
        """
        main_window = self._window_manager.main_window
        if not main_window:
            return []
        
        number_stats = []
        
        try:
            # 尝试多种控件类型
            control_types = ["Text", "ListItem", "DataItem", "Custom", "Pane"]
            stats_map: Dict[int, int] = {}
            # 严格匹配：必须有冒号，且次数在合理范围（1-200）
            number_pattern = re.compile(r"^(\d)\s*[:：]\s*(\d{1,3})$")
            
            for ctrl_type in control_types:
                try:
                    controls = main_window.descendants(control_type=ctrl_type)
                    self.logger.debug("检查 %s 类型控件，找到 %d 个", ctrl_type, len(controls))
                    
                    for ctrl in controls:
                        try:
                            # 尝试获取文本
                            text = ctrl.window_text().strip()
                            if not text:
                                # 尝试获取Name属性
                                try:
                                    text = ctrl.element_info.name.strip()
                                except Exception:  # pylint: disable=broad-except
                                    continue
                            
                            # 只处理短文本（推荐号统计格式很短）
                            if len(text) > 10:
                                continue
                            
                            match = number_pattern.match(text)
                            if not match:
                                continue
                            
                            number = int(match.group(1))
                            count = int(match.group(2))
                            
                            # 验证：号码0-9，次数1-200（合理范围）
                            if 0 <= number <= 9 and 1 <= count <= 200:
                                previous = stats_map.get(number)
                                if previous is None or count > previous:
                                    stats_map[number] = count
                                    self.logger.debug("从 %s 提取: %d: %d", ctrl_type, number, count)
                        except Exception:  # pylint: disable=broad-except
                            continue
                    
                    if stats_map:
                        break  # 找到数据就停止
                        
                except Exception:  # pylint: disable=broad-except
                    continue
            
            if stats_map:
                number_stats = [(num, cnt) for num, cnt in stats_map.items()]
        except Exception as exc:
            self.logger.debug("UI控件提取失败: %s", exc)
        
        return number_stats

    def _extract_by_ocr(self) -> List[Tuple[int, int]]:
        """使用OCR识别右侧统计区域（使用easyocr纯Python实现）。
        
        Returns:
            [(号码, 次数), ...] 列表
        """
        try:
            try:
                import easyocr
            except ImportError:
                self.logger.warning("easyocr未安装，跳过OCR识别。安装: pip install easyocr")
                return []

            main_window = self._window_manager.main_window
            if not main_window:
                return []

            rect = main_window.rectangle()
            window_region = (rect.left, rect.top, rect.width(), rect.height())
            full_screenshot = pyautogui.screenshot(region=window_region)

            # 校验窗口截图尺寸，避免误连到错误窗口（如计划接口小窗）
            try:
                min_width = int(self._ocr_region_config.get("min_window_width", 800))
            except Exception:
                min_width = 800
            try:
                min_height = int(self._ocr_region_config.get("min_window_height", 600))
            except Exception:
                min_height = 600

            if full_screenshot.width < min_width or full_screenshot.height < min_height:
                self.logger.warning(
                    "检测到窗口截图尺寸异常 (width=%d, height=%d)，尝试重新连接主窗口后重试OCR...",
                    full_screenshot.width,
                    full_screenshot.height,
                )
                try:
                    # 重新绑定主窗口，纠正句柄
                    self._window_manager.connect_to_window(timeout=5)
                    main_window = self._window_manager.main_window
                    if main_window:
                        rect = main_window.rectangle()
                        window_region = (rect.left, rect.top, rect.width(), rect.height())
                        full_screenshot = pyautogui.screenshot(region=window_region)
                        self.logger.info(
                            "重连后全窗口截图尺寸: %dx%d",
                            full_screenshot.width,
                            full_screenshot.height,
                        )
                except Exception as exc:  # pylint: disable=broad-except
                    self.logger.warning("重新连接主窗口失败: %s", exc)

                # 若重连后尺寸仍异常，则放弃本次 OCR，回退到其它提取方式
                if full_screenshot.width < min_width or full_screenshot.height < min_height:
                    self.logger.warning(
                        "重连后窗口尺寸仍异常 (width=%d, height=%d)，放弃本次推荐区OCR，回退到表格统计/提取。",
                        full_screenshot.width,
                        full_screenshot.height,
                    )
                    return []

            import numpy as np

            self.logger.info("初始化OCR引擎...")
            reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

            # 保存全窗口调试截图
            import os
            os.makedirs("logs", exist_ok=True)
            full_window_path = os.path.join("logs", "full_window_capture.png")
            full_screenshot.save(full_window_path)
            self.logger.info("已保存全窗口截图: %s (尺寸: %dx%d)", full_window_path, full_screenshot.width, full_screenshot.height)

            anchor_region = self._locate_anchor_region(reader, np.array(full_screenshot), rect)
            if anchor_region:
                self.logger.info("✓ 通过锚点自适应定位OCR区域: %s", anchor_region)
                target_region = anchor_region
            else:
                self.logger.warning("⚠ 未找到推荐号锚点，使用固定偏移量（窗口位置/分辨率改变后可能失效）")
                target_region = self._compute_ocr_region(rect)
                self.logger.info("回退使用配置区域: %s", target_region)

            cropped_image = self._crop_region_from_window(full_screenshot, target_region, rect)
            if not cropped_image:
                self.logger.warning("无法裁剪OCR区域，放弃本次识别")
                return []

            # 保存裁剪后的调试截图
            debug_path = os.path.join("logs", "recommendation_ocr_capture.png")
            cropped_image.save(debug_path)
            self.logger.info("已保存推荐号OCR裁剪截图: %s (尺寸: %dx%d)", debug_path, cropped_image.width, cropped_image.height)

            # 图像预处理：灰度 + 放大，提高数字识别率
            preprocessed = cropped_image.convert("L")
            scale_factor = 2
            try:
                cfg_scale = int(self._ocr_region_config.get("scale_factor", 0))
                if cfg_scale >= 2:
                    scale_factor = cfg_scale
            except Exception:
                scale_factor = 2
            if scale_factor > 1:
                new_size = (cropped_image.width * scale_factor, cropped_image.height * scale_factor)
                preprocessed = preprocessed.resize(new_size)
            self.logger.debug("推荐区OCR预处理后图像尺寸: %dx%d", preprocessed.width, preprocessed.height)

            # 使用 Tesseract 对预处理后的整块区域做行级 OCR
            try:
                import pytesseract
            except ImportError:
                self.logger.warning(
                    "pytesseract 未安装，无法使用 Tesseract 识别推荐区，请先安装: pip install pytesseract 并安装 tesseract 引擎"
                )
                return []

            # 配置 Tesseract 可执行文件路径
            tesseract_cmd = self._config.get("tesseract_cmd")
            if tesseract_cmd:
                import os as _os_check
                if _os_check.path.exists(tesseract_cmd):
                    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                    self.logger.info("使用配置的 Tesseract 路径: %s", tesseract_cmd)
                else:
                    self.logger.warning("配置的 Tesseract 路径不存在: %s，请检查文件是否存在", tesseract_cmd)
            else:
                self.logger.info("未配置 tesseract_cmd，尝试使用系统 PATH 中的 tesseract")

            custom_config = "--psm 6 -c tessedit_char_whitelist=0123456789:"
            self.logger.info("使用 Tesseract 识别推荐区统计... (psm=6, whitelist=0123456789:)")
            raw_text = pytesseract.image_to_string(preprocessed, config=custom_config)
            if not raw_text:
                self.logger.warning("Tesseract 未识别到任何文本")
                return []

            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            for idx, line in enumerate(lines, 1):
                self.logger.info("  [TESS 行 %d] '%s'", idx, line)

            # 解析结果：从每一行提取“号码: 次数”
            stats_map: Dict[int, int] = {}
            pattern = r'^(\d)\s*[:：]\s*(\d{1,3})$'

            for line in lines:
                text = line.replace('O', '0').replace('o', '0').replace('：', ':')
                if not text:
                    continue

                parsed: Optional[Tuple[int, int]] = None
                match = re.match(pattern, text)
                if match:
                    parsed = (int(match.group(1)), int(match.group(2)))
                else:
                    parsed = self._parse_ocr_stat_text(text)

                if not parsed:
                    self.logger.debug("跳过无法解析的文本行: '%s'", text)
                    continue
                number, count = parsed
                if not (0 <= number <= 9 and 1 <= count <= 200):
                    self.logger.debug("跳过范围外数据: 号码=%d, 次数=%d", number, count)
                    continue
                previous = stats_map.get(number)
                if previous is None or count > previous:
                    stats_map[number] = count
                    self.logger.info("  ✓ 解析成功: %d: %d", number, count)

            number_stats = [(num, cnt) for num, cnt in stats_map.items()]
            if number_stats:
                number_stats.sort(key=lambda x: (-x[1], x[0]))
                self.logger.info("✓ OCR成功识别 %d 条统计数据", len(number_stats))
            else:
                self.logger.warning("OCR未识别到有效数据")
            
            return number_stats
            
        except Exception as exc:
            self.logger.error("OCR识别失败: %s", exc)
            import traceback
            self.logger.debug(traceback.format_exc())
            return []

    def _compute_ocr_region(self, rect) -> Tuple[int, int, int, int]:
        """根据配置或默认偏移返回 OCR 识别区域。"""

        offset_x = int(self._ocr_region_config.get("offset_x", 845))
        offset_y = int(self._ocr_region_config.get("offset_y", 50))
        width = int(self._ocr_region_config.get("width", 140))
        height = int(self._ocr_region_config.get("height", 420))
        inner_offset_x = int(self._ocr_region_config.get("inner_offset_x", 0))

        left = rect.left + offset_x + inner_offset_x
        # 向右偏移后适当收窄宽度，避免越界
        if inner_offset_x > 0 and width > inner_offset_x + 10:
            width = width - inner_offset_x
        return (left, rect.top + offset_y, width, height)

    def _locate_anchor_region(self, reader, full_image_array, rect) -> Optional[Tuple[int, int, int, int]]:
        """在全窗口截图中寻找“推荐号”锚点，返回其下方区域。"""

        try:
            results = reader.readtext(full_image_array)
            self.logger.debug("全窗口OCR识别到 %d 个文本区域", len(results))
            # 输出前若干个识别结果，便于调试
            for bbox, text, prob in results[:20]:
                self.logger.debug("  OCR: '%s' (prob=%.2f, bbox=%s)", text.strip(), prob, bbox)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.warning("锚点识别失败: %s", exc)
            return None

        # 增强锚点关键字匹配（支持多种变体和模糊匹配）
        anchor_keywords = [
            "推荐号",
            "荐号",
            "推荐号统计",
            "荐号统计",
            "号码统计",
            "推荐",
            "统计",
            "tuijian",
            "recommend",
        ]

        for bbox, text, prob in results:
            normalized = text.strip().replace(" ", "")  # 移除空格
            if not normalized:
                continue

            # 检查是否包含任一关键字
            found_keyword = None
            for keyword in anchor_keywords:
                if keyword in normalized:
                    found_keyword = keyword
                    break

            if not found_keyword:
                continue

            self.logger.debug("匹配到锚点关键字 '%s' in '%s'", found_keyword, text)
            left = min(point[0] for point in bbox)
            right = max(point[0] for point in bbox)
            top = min(point[1] for point in bbox)
            bottom = max(point[1] for point in bbox)
            gap = int(self._ocr_region_config.get("anchor_gap", 10))
            width = int(self._ocr_region_config.get("width", 140))
            height = int(self._ocr_region_config.get("height", 420))
            inner_offset_x = int(self._ocr_region_config.get("inner_offset_x", 0))

            # 计算裁剪区域：从锚点下方开始
            region_left = rect.left + int(left) + inner_offset_x
            region_top = rect.top + int(bottom) + gap
            region_left = max(region_left, rect.left)
            # 向右偏移后，适当收窄宽度，避免越界
            if inner_offset_x > 0 and width > inner_offset_x + 10:
                width = width - inner_offset_x
            region_left = min(region_left, rect.right - width)
            region_top = min(region_top, rect.bottom - height)

            self.logger.info("找到锚点'%s', 局部bbox=%s", text, bbox)
            self.logger.info("窗口全局坐标: left=%d, top=%d, width=%d, height=%d", rect.left, rect.top, rect.width(), rect.height())
            self.logger.info("裁剪区域配置: width=%d, height=%d, gap=%d", width, height, gap)
            self.logger.info("推荐区全局坐标: left=%d, top=%d, width=%d, height=%d", region_left, region_top, width, height)
            return (region_left, region_top, width, height)
        return None

    def _crop_region_from_window(self, screenshot, target_region, rect) -> Optional["Image.Image"]:
        """从整窗截图中裁剪指定的全局区域。"""

        if not target_region:
            self.logger.warning("裁剪失败: target_region 为 None")
            return None
        left, top, width, height = target_region
        if width <= 0 or height <= 0:
            self.logger.warning("裁剪失败: 区域尺寸无效 width=%d, height=%d", width, height)
            return None
        
        # 全局坐标转换为窗口局部坐标
        local_left = left - rect.left
        local_top = top - rect.top
        local_right = local_left + width
        local_bottom = local_top + height
        
        self.logger.debug("裁剪计算: 全局区域(%d,%d,%d,%d) -> 局部区域(%d,%d,%d,%d), 窗口尺寸(%d,%d)", 
                         left, top, width, height, local_left, local_top, local_right, local_bottom,
                         screenshot.width, screenshot.height)
        
        if local_left < 0 or local_top < 0:
            self.logger.warning("裁剪失败: 局部坐标越界 local_left=%d, local_top=%d", local_left, local_top)
            return None
        if local_right > screenshot.width or local_bottom > screenshot.height:
            self.logger.warning("裁剪失败: 局部区域超出窗口 local_right=%d > width=%d 或 local_bottom=%d > height=%d", 
                              local_right, screenshot.width, local_bottom, screenshot.height)
            return None
        
        return screenshot.crop((local_left, local_top, local_right, local_bottom))

    def _parse_ocr_stat_text(self, text: str) -> Optional[Tuple[int, int]]:
        """宽松解析 OCR 返回的文本，提取号码与出现次数。"""

        cleaned = text.strip()
        if not cleaned:
            return None
        digits = re.findall(r"\d+", cleaned)
        if len(digits) < 2:
            return None
        number_char = digits[0][0]
        if not number_char.isdigit():
            return None
        number = int(number_char)
        count_token = digits[-1][-3:]
        try:
            count = int(count_token)
        except ValueError:
            return None
        return number, count

    def _compute_statistics_from_table_counts(self) -> List[Tuple[int, int]]:
        """当UI不可读时，基于表格数据统计数字出现次数。"""
        main_window = self._window_manager.main_window
        if not main_window:
            return []
        
        try:
            tables = main_window.descendants(control_type="DataGrid")
            if not tables:
                self.logger.warning("未找到数据表格用于统计推荐号")
                return []
            
            table = tables[0]
            items = table.descendants(control_type="DataItem")
            if not items:
                return []
            
            counts: Counter[int] = Counter()
            for item in items:
                try:
                    numbers = self._parse_numbers_from_row(item)
                    for number in numbers:
                        counts[number] += 1
                except Exception:  # pylint: disable=broad-except
                    continue
            
            if not counts:
                return []
            
            stats = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
            self.logger.info("基于表格统计推荐号频次，共 %d 个数字", len(stats))
            return stats
        except Exception as exc:
            self.logger.warning("表格统计推荐号失败: %s", exc)
            return []

    def _extract_table_data(self, max_results: int) -> List[List[int]]:
        """从结果表格中提取数据。
        
        Args:
            max_results: 最大结果数量
            
        Returns:
            推荐号码列表
        """
        main_window = self._window_manager.main_window
        if not main_window:
            return []
        
        results: List[List[int]] = []
        
        try:
            # 查找数据表格
            tables = main_window.descendants(control_type="DataGrid")
            if not tables:
                self.logger.warning("未找到数据表格")
                return []
            
            table = tables[0]
            
            # 获取所有数据行
            items = table.descendants(control_type="DataItem")
            
            self.logger.debug("找到 %d 行数据", len(items))
            
            # 提取前N行
            for idx, item in enumerate(items[:max_results]):
                try:
                    # 获取行文本
                    row_text = item.window_text()
                    
                    # 解析号码（通常在"当前推荐号"列）
                    # 根据实际表格结构调整解析逻辑
                    numbers = self._parse_numbers_from_row(item)
                    
                    if numbers:
                        results.append(numbers)
                        self.logger.debug("提取第 %d 条结果: %s", idx + 1, numbers)
                    
                except Exception as exc:  # pylint: disable=broad-except
                    self.logger.warning("解析第 %d 行失败: %s", idx + 1, exc)
                    continue
            
        except Exception as exc:
            self.logger.error("提取表格数据失败: %s", exc)
        
        return results

    def _parse_numbers_from_row(self, row: UIAWrapper) -> List[int]:
        """从数据行中解析号码。
        
        Args:
            row: 数据行控件
            
        Returns:
            号码列表
        """
        try:
            # 获取行中的所有单元格
            cells = row.descendants(control_type="Text")
            
            # 查找包含号码的单元格（通常是"当前推荐号"或"推荐号码"列）
            for cell in cells:
                try:
                    cell_text = cell.window_text().strip()
                    
                    # 检查是否是号码格式（例如："0 1 2 3 4" 或 "01234"）
                    if self._is_number_text(cell_text):
                        numbers = self._extract_numbers_from_text(cell_text)
                        if numbers:
                            return numbers
                        
                except Exception:  # pylint: disable=broad-except
                    continue
            
        except Exception as exc:
            self.logger.debug("解析行号码失败: %s", exc)
        
        return []

    def _is_number_text(self, text: str) -> bool:
        """判断文本是否可能包含号码。
        
        Args:
            text: 要检查的文本
            
        Returns:
            True 表示可能包含号码
        """
        # 检查是否包含数字
        if not any(c.isdigit() for c in text):
            return False
        
        # 检查长度（号码文本通常不会太长）
        if len(text) > 20:
            return False
        
        return True

    def _extract_numbers_from_text(self, text: str) -> List[int]:
        """从文本中提取号码。
        
        Args:
            text: 包含号码的文本
            
        Returns:
            号码列表
        """
        numbers: List[int] = []
        
        # 移除多余的空格
        text = text.strip()
        
        # 方式1：空格分隔（例如："0 1 2 3 4"）
        if " " in text:
            parts = text.split()
            for part in parts:
                if part.isdigit():
                    numbers.append(int(part))
        # 方式2：逐个字符（例如："01234"）
        else:
            for char in text:
                if char.isdigit():
                    numbers.append(int(char))
        
        # 验证号码数量（腾讯分分彩通常是5个号码）
        if len(numbers) == 5:
            return sorted(numbers)
        
        return []
