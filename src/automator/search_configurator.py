"""搜索参数配置器。"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pyautogui

from src.automator.window_manager import WindowManager
from src.data.models import SearchParameters
from src.exception.custom_exceptions import AutomationException


class SearchConfigurator:
    """负责配置公式搜索界面的各项参数。"""

    def __init__(self, window_manager: WindowManager) -> None:
        """初始化搜索配置器。
        
        Args:
            window_manager: 窗口管理器实例
        """
        self._window_manager = window_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    def configure_search_parameters(self, params: SearchParameters) -> None:
        """配置搜索参数（优先使用图像识别，失败则回退到UI Automation）。
        
        Args:
            params: 搜索参数对象
            
        Raises:
            AutomationException: 配置失败时抛出
        """
        self.logger.info("开始配置搜索参数...")
        
        try:
            # 方式1：尝试使用图像识别配置（推荐，因为UI Automation无法识别此应用）
            self.logger.info("尝试使用图像识别配置参数...")
            if self._configure_by_relative_position(params):
                self.logger.info("✅ 搜索参数配置完成（使用图像识别）")
                return
            
            # 方式2：回退到UI Automation（通常会失败，因为应用使用自定义渲染）
            self.logger.warning("图像识别失败，尝试使用 UI Automation...")
            
            self._set_input_value("搜索公式数量", str(params.formula_count))
            self._set_input_value("数据期数", str(params.data_periods))
            self._set_input_value("定码个数", str(params.fixed_code_count))
            self._set_input_value("计划周期", str(params.plan_cycle))
            self._configure_accuracy_filter(params.min_accuracy)
            
            self.logger.info("✅ 搜索参数配置完成（使用 UI Automation）")
            
        except Exception as exc:
            self.logger.error("配置搜索参数失败: %s", exc)
            # 不抛出异常，允许使用默认参数继续
            self.logger.warning("将使用默认参数继续执行")

    def _set_input_value(self, label: str, value: str) -> None:
        """设置输入框的值。
        
        Args:
            label: 输入框标签
            value: 要设置的值
        """
        try:
            # 查找输入框（通过标签查找附近的Edit控件）
            main_window = self._window_manager.main_window
            if not main_window:
                raise AutomationException("主窗口未连接")
            
            # 尝试通过自动化ID或标题查找
            controls = main_window.descendants(control_type="Edit")
            for control in controls:
                try:
                    # 获取控件附近的静态文本，判断是否匹配
                    siblings = control.parent().children()
                    for sibling in siblings:
                        if sibling.element_info.control_type == "Text":
                            if label in sibling.window_text():
                                # 高亮显示控件
                                self._window_manager.highlight_control(control, duration=0.15)
                                
                                control.set_focus()
                                control.set_edit_text("")
                                time.sleep(0.1)
                                control.type_keys(value, with_spaces=True)
                                self.logger.debug("设置 %s = %s", label, value)
                                return
                except Exception:  # pylint: disable=broad-except
                    continue
            
            self.logger.warning("未找到输入框: %s，尝试通过位置定位", label)
            
        except Exception as exc:
            self.logger.error("设置输入框失败: %s, 错误: %s", label, exc)
            raise AutomationException(f"设置输入框 {label} 失败") from exc

    def _configure_accuracy_filter(self, min_accuracy: float) -> None:
        """配置准确率过滤条件。
        
        Args:
            min_accuracy: 最小准确率
        """
        try:
            # 查找准确率复选框
            main_window = self._window_manager.main_window
            if not main_window:
                raise AutomationException("主窗口未连接")
            
            # 查找"准确率"相关的复选框
            checkboxes = main_window.descendants(control_type="CheckBox")
            for checkbox in checkboxes:
                try:
                    text = checkbox.window_text()
                    if "准确率" in text:
                        # 高亮显示复选框
                        self._window_manager.highlight_control(checkbox, duration=0.15)
                        
                        # 勾选复选框
                        if not checkbox.get_toggle_state():
                            checkbox.click_input()
                            time.sleep(0.1)
                        
                        # 设置准确率值
                        # 查找附近的下拉框和输入框
                        parent = checkbox.parent()
                        edits = parent.descendants(control_type="Edit")
                        if edits:
                            edit = edits[-1]  # 通常值输入框在最后
                            # 高亮显示输入框
                            self._window_manager.highlight_control(edit, duration=0.15)
                            edit.set_focus()
                            edit.set_edit_text("")
                            time.sleep(0.1)
                            edit.type_keys(str(int(min_accuracy)), with_spaces=True)
                            self.logger.debug("设置准确率 >= %s", min_accuracy)
                        
                        return
                except Exception:  # pylint: disable=broad-except
                    continue
            
            self.logger.warning("未找到准确率配置控件")
            
        except Exception as exc:
            self.logger.error("配置准确率失败: %s", exc)

    def _configure_by_relative_position(self, params: SearchParameters) -> bool:
        """通过相对坐标配置参数（基于窗口位置的图像识别）。
        
        Args:
            params: 搜索参数对象
            
        Returns:
            是否成功配置
        """
        try:
            # 快速检查界面状态
            self.logger.info("准备配置参数...")
            time.sleep(0.3)  # 减少等待时间
            
            # 获取窗口位置
            main_window = self._window_manager.main_window
            if not main_window:
                return False
            
            rect = main_window.rectangle()
            window_x, window_y = rect.left, rect.top
            
            self.logger.info("窗口位置: (%d, %d)，开始配置参数...", window_x, window_y)
            
            # 基于窗口位置计算输入框坐标（根据截图估算）
            base_x = window_x + 280  # 输入框X偏移
            base_y = window_y + 200  # 第一个输入框Y偏移
            
            # 配置各个参数（Y坐标依次递增）
            self._click_and_input(base_x, base_y + 0, str(params.formula_count), "搜索公式数量")
            self._click_and_input(base_x, base_y + 44, str(params.data_periods), "数据期数")
            self._click_and_input(base_x, base_y + 71, str(params.fixed_code_count), "定码个数")
            self._click_and_input(base_x, base_y + 96, str(params.plan_cycle), "计划周期")
            
            # 准确率（先勾选复选框，再输入值）
            checkbox_x = window_x + 147
            checkbox_y = window_y + 351
            pyautogui.click(checkbox_x, checkbox_y)
            time.sleep(0.1)  # 减少等待
            self._click_and_input(base_x + 10, base_y + 151, str(params.min_accuracy), "准确率")
            
            self.logger.info("通过相对坐标配置参数完成")
            return True
            
        except Exception as exc:
            self.logger.error("相对坐标配置失败: %s", exc)
            return False

    def _click_and_input(self, x: int, y: int, value: str, label: str = "") -> None:
        """点击指定坐标并输入值（快速模式）。
        
        Args:
            x: X坐标
            y: Y坐标
            value: 要输入的值
            label: 字段标签（用于日志）
        """
        try:
            # 快速点击
            pyautogui.click(x, y)
            time.sleep(0.05)  # 减少等待
            
            # 快速清空
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.03)
            pyautogui.press('delete')
            time.sleep(0.03)
            
            # 快速输入
            pyautogui.write(value, interval=0.02)  # 减少输入间隔
            time.sleep(0.05)
            
            # 快速确认
            pyautogui.press('tab')
            time.sleep(0.05)
            
            if label:
                self.logger.info("✓ %s=%s", label, value)
                
        except Exception as exc:
            self.logger.error("输入失败 %s: %s", label, exc)
