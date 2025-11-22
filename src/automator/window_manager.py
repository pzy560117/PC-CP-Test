"""Windows 桌面窗口管理器。"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import pyautogui
from PIL import Image, ImageDraw
from pywinauto import Application, Desktop
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.findwindows import ElementNotFoundError

from src.exception.custom_exceptions import AutomationException


class WindowManager:
    """负责查找、激活和管理桌面应用窗口。"""

    def __init__(self, app_config: Dict[str, Any]) -> None:
        """初始化窗口管理器。
        
        Args:
            app_config: 应用配置字典
        """
        self._config = app_config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._app: Optional[Application] = None
        self._main_window: Optional[UIAWrapper] = None
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5

    def connect_to_window(self, timeout: int = 30) -> UIAWrapper:
        """连接到目标应用窗口。
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            主窗口对象
            
        Raises:
            AutomationException: 连接失败时抛出
        """
        window_title = self._config.get("window_title", "")
        if not window_title:
            raise AutomationException("配置项 target_app.window_title 不能为空")

        self.logger.info("正在查找窗口: %s", window_title)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 尝试通过标题查找窗口
                windows = Desktop(backend="uia").windows()
                self.logger.debug("找到 %d 个顶层窗口", len(windows))
                
                for window in windows:
                    try:
                        current_title = window.window_text()
                        self.logger.debug("检查窗口: %s", current_title)
                        
                        # 方式1：直接匹配配置的标题
                        if window_title in current_title:
                            self._app = Application(backend="uia").connect(handle=window.handle)
                            self._main_window = window
                            self.logger.info("✓ 成功连接到窗口: %s", current_title)
                            return self._main_window
                        
                        # 方式2：匹配"公式搜索"关键词（子窗口）
                        if "公式搜索" in current_title:
                            self._app = Application(backend="uia").connect(handle=window.handle)
                            self._main_window = window
                            self.logger.info("✓ 成功连接到窗口: %s （匹配：公式搜索）", current_title)
                            return self._main_window
                        
                        # 方式3：检查子窗口（特别是"奇趣腾讯分分彩"的子窗口）
                        if "奇趣" in current_title or window_title in current_title:
                            self.logger.debug("检查窗口 '%s' 的子窗口...", current_title)
                            try:
                                # 递归检查所有子窗口
                                all_descendants = window.descendants()
                                self.logger.debug("找到 %d 个子控件", len(all_descendants))
                                for child in all_descendants[:100]:  # 只检查前100个
                                    try:
                                        child_title = child.window_text()
                                        if child_title and "公式搜索" in child_title:
                                            self._app = Application(backend="uia").connect(handle=child.handle)
                                            self._main_window = child
                                            self.logger.info("✓ 成功连接到子窗口: %s", child_title)
                                            return self._main_window
                                    except Exception:
                                        continue
                            except Exception as e:
                                self.logger.debug("检查子窗口失败: %s", e)
                                
                    except Exception as e:  # pylint: disable=broad-except
                        self.logger.debug("检查窗口失败: %s", e)
                        continue
                        
            except ElementNotFoundError:
                pass
            
            time.sleep(1)
        
        raise AutomationException(f"在 {timeout} 秒内未找到窗口: {window_title}")

    def activate_window(self) -> None:
        """激活并前置主窗口。
        
        Raises:
            AutomationException: 窗口未连接时抛出
        """
        if not self._main_window:
            raise AutomationException("窗口未连接，请先调用 connect_to_window")
        
        try:
            # 尝试设置焦点
            try:
                self._main_window.set_focus()
                self.logger.debug("窗口已获取焦点")
            except Exception as e:
                self.logger.debug("设置焦点失败: %s", e)
            
            # 尝试恢复窗口（如果是最小化状态）
            try:
                self._main_window.restore()
                self.logger.debug("窗口已恢复")
            except Exception as e:
                # restore失败通常是因为窗口已经正常显示，忽略这个错误
                self.logger.debug("恢复窗口失败（可能窗口已正常显示）: %s", e)
            
            self.logger.info("✓ 窗口已激活")
            
        except Exception as exc:
            # 如果激活失败，不抛出异常，只记录警告
            self.logger.warning("激活窗口时出现问题: %s，但将继续执行", exc)

    def find_control(
        self,
        control_type: str,
        title: Optional[str] = None,
        auto_id: Optional[str] = None,
        class_name: Optional[str] = None,
        timeout: int = 10
    ) -> UIAWrapper:
        """在主窗口中查找控件。
        
        Args:
            control_type: 控件类型（如 Button、Edit、ComboBox 等）
            title: 控件标题
            auto_id: 控件自动化ID
            class_name: 控件类名
            timeout: 超时时间（秒）
            
        Returns:
            找到的控件对象
            
        Raises:
            AutomationException: 未找到控件时抛出
        """
        if not self._main_window:
            raise AutomationException("窗口未连接，请先调用 connect_to_window")
        
        criteria = {"control_type": control_type}
        if title:
            criteria["title"] = title
        if auto_id:
            criteria["auto_id"] = auto_id
        if class_name:
            criteria["class_name"] = class_name
        
        self.logger.debug("查找控件: %s", criteria)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                control = self._main_window.child_window(**criteria, found_index=0)
                if control.exists():
                    self.logger.debug("找到控件: %s", criteria)
                    return control
            except Exception:  # pylint: disable=broad-except
                pass
            
            time.sleep(0.5)
        
        raise AutomationException(f"在 {timeout} 秒内未找到控件: {criteria}")

    def wait_for_window_ready(self, timeout: int = 30) -> None:
        """等待窗口进入就绪状态。
        
        Args:
            timeout: 超时时间（秒）
        """
        if not self._main_window:
            raise AutomationException("窗口未连接，请先调用 connect_to_window")
        
        self.logger.info("等待窗口就绪...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self._main_window.is_enabled() and self._main_window.is_visible():
                    self.logger.info("窗口已就绪")
                    return
            except Exception:  # pylint: disable=broad-except
                pass
            
            time.sleep(1)
        
        raise AutomationException(f"窗口在 {timeout} 秒内未就绪")

    @property
    def main_window(self) -> Optional[UIAWrapper]:
        """获取主窗口对象。"""
        return self._main_window

    def highlight_control(self, control: UIAWrapper, duration: float = 0.2) -> None:
        """在控件周围显示红色高亮框。
        
        Args:
            control: 要高亮显示的控件
            duration: 高亮持续时间（秒）
        """
        try:
            # 获取控件的矩形区域
            rect = control.rectangle()
            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
            
            # 使用 pyautogui 在控件周围绘制红色矩形（通过移动鼠标）
            # 注意：这是一个简化的实现，真正的高亮需要使用 GUI 框架
            import tkinter as tk
            
            # 创建一个透明窗口来显示边框
            highlight_window = tk.Tk()
            highlight_window.overrideredirect(True)
            highlight_window.attributes('-topmost', True)
            highlight_window.attributes('-alpha', 0.3)
            
            # 设置窗口位置和大小
            width = right - left
            height = bottom - top
            highlight_window.geometry(f"{width}x{height}+{left}+{top}")
            
            # 创建红色边框
            canvas = tk.Canvas(highlight_window, bg='red', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # 绘制边框（内部透明）
            border_width = 3
            canvas.create_rectangle(
                border_width, border_width,
                width - border_width, height - border_width,
                outline='red', width=border_width * 2, fill=''
            )
            
            # 显示窗口
            highlight_window.update()
            
            # 等待指定时间
            time.sleep(duration)
            
            # 关闭窗口
            highlight_window.destroy()
            
            self.logger.debug("已显示控件高亮提示")
            
        except Exception as exc:
            self.logger.warning("显示控件高亮失败: %s", exc)

    @property
    def is_connected(self) -> bool:
        """检查是否已连接到窗口。"""
        return self._main_window is not None
