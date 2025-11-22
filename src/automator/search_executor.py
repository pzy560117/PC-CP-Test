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
        self.logger.info("等待搜索完成（超时: %d秒）...", timeout)
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 检查是否有"停止"按钮（搜索中）或结果表格已显示
            if self._is_search_completed():
                self.logger.info("搜索已完成")
                return
            
            time.sleep(1)
        
        raise AutomationException(f"搜索在 {timeout} 秒内未完成")

    def _is_search_completed(self) -> bool:
        """检查搜索是否已完成。
        
        Returns:
            True 表示已完成，False 表示仍在进行
        """
        main_window = self._window_manager.main_window
        if not main_window:
            return False
        
        try:
            # 方法1：检查是否有数据行（表格中有内容）
            tables = main_window.descendants(control_type="DataGrid")
            if tables:
                # 检查表格是否有数据项
                table = tables[0]
                items = table.descendants(control_type="DataItem")
                if len(items) > 0:
                    return True
            
            # 方法2：检查"停止"按钮是否已消失或变为不可用
            buttons = main_window.descendants(control_type="Button")
            stop_button_active = False
            for button in buttons:
                try:
                    button_text = button.window_text()
                    if "停止" in button_text or "Stop" in button_text:
                        if button.is_enabled():
                            stop_button_active = True
                            break
                except Exception:  # pylint: disable=broad-except
                    continue
            
            # 如果停止按钮不活跃，说明搜索可能已完成
            if not stop_button_active:
                # 再次确认是否有结果
                time.sleep(1)
                tables = main_window.descendants(control_type="DataGrid")
                if tables:
                    items = tables[0].descendants(control_type="DataItem")
                    if len(items) > 0:
                        return True
            
        except Exception:  # pylint: disable=broad-except
            pass
        
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
            # 尝试导入easyocr
            try:
                import easyocr
            except ImportError:
                self.logger.warning("easyocr未安装，跳过OCR识别。安装: pip install easyocr")
                return []
            
            main_window = self._window_manager.main_window
            if not main_window:
                return []
            
            # 获取窗口位置
            rect = main_window.rectangle()
            
            # 右侧统计区域（根据截图估算，相对窗口位置）
            # 统计区域大约在窗口右侧，X偏移约845，Y偏移约50
            stats_region = (
                rect.left + 845,  # X起始（推荐号统计框左边）
                rect.top + 50,    # Y起始
                125,              # 宽度
                400               # 高度
            )
            
            self.logger.info("OCR识别区域: (%d, %d, %d, %d)", *stats_region)
            
            # 截取区域并保存为临时图片
            screenshot = pyautogui.screenshot(region=stats_region)
            
            # 转为numpy数组供easyocr使用
            import numpy as np
            img_array = np.array(screenshot)
            
            # 初始化OCR（首次会下载模型）
            self.logger.info("初始化OCR引擎...")
            reader = easyocr.Reader(['en'], gpu=False)  # 只识别英文数字
            
            # OCR识别
            self.logger.info("执行OCR识别...")
            results = reader.readtext(img_array)
            
            # 解析结果
            number_stats = []
            pattern = r'^(\d)\s*[:：]\s*(\d{1,3})$'
            
            for (bbox, text, prob) in results:
                text = text.strip()
                self.logger.debug("OCR检测到: '%s' (置信度: %.2f)", text, prob)
                
                # 容错处理：字母O替换为数字0（OCR常见误识别）
                text = text.replace('O', '0').replace('o', '0')
                
                # 匹配 "数字: 数字" 格式
                match = re.match(pattern, text)
                if match:
                    try:
                        number = int(match.group(1))
                        count = int(match.group(2))
                        
                        if 0 <= number <= 9 and 1 <= count <= 200:
                            number_stats.append((number, count))
                            self.logger.debug("✓ OCR提取: %d: %d", number, count)
                    except Exception:
                        continue
            
            if number_stats:
                self.logger.info("✓ OCR成功识别 %d 条统计数据", len(number_stats))
            else:
                self.logger.warning("OCR未识别到有效数据")
            
            return number_stats
            
        except Exception as exc:
            self.logger.error("OCR识别失败: %s", exc)
            import traceback
            self.logger.debug(traceback.format_exc())
            return []

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
