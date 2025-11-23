"""Windows 桌面窗口管理器。"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import pyautogui
from PIL import Image, ImageDraw
from pywinauto import Application, Desktop
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.findwindows import ElementNotFoundError
import win32con
import win32gui

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
        self._window_geometry = self._parse_geometry(self._config.get("window_geometry"))
        self._enable_highlight = bool(self._config.get("enable_highlight", False))
        self._topmost_keywords = self._parse_topmost_keywords(self._config.get("topmost_windows"))
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
                        current_title = window.window_text() or ""
                        if not current_title:
                            continue

                        # 避免将计划接口窗口误认为主窗口
                        if "计划接口" in current_title:
                            self.logger.debug("跳过计划接口相关窗口: %s", current_title)
                            continue

                        self.logger.debug("检查窗口: %s", current_title)
                        
                        # 优先：精确匹配配置标题
                        if current_title == window_title:
                            self._app = Application(backend="uia").connect(handle=window.handle)
                            self._main_window = window
                            self.logger.info("✓ 成功连接到窗口: %s", current_title)
                            self._apply_window_geometry()
                            self._bring_window_to_front()
                            self._ensure_topmost_windows()
                            return self._main_window

                        # 方式1：标题中包含配置标题
                        if window_title in current_title:
                            self._app = Application(backend="uia").connect(handle=window.handle)
                            self._main_window = window
                            self.logger.info("✓ 成功连接到窗口: %s", current_title)
                            self._apply_window_geometry()
                            self._bring_window_to_front()
                            self._ensure_topmost_windows()
                            return self._main_window
                        
                        # 方式2：匹配"公式搜索"关键词（子窗口）
                        if "公式搜索" in current_title:
                            self._app = Application(backend="uia").connect(handle=window.handle)
                            self._main_window = window
                            self.logger.info("✓ 成功连接到窗口: %s （匹配：公式搜索）", current_title)
                            self._apply_window_geometry()
                            self._bring_window_to_front()
                            self._ensure_topmost_windows()
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
                                        child_title = child.window_text() or ""
                                        if not child_title:
                                            continue
                                        if "计划接口" in child_title:
                                            self.logger.debug("跳过计划接口子窗口: %s", child_title)
                                            continue
                                        if "公式搜索" in child_title:
                                            self._app = Application(backend="uia").connect(handle=child.handle)
                                            self._main_window = child
                                            self.logger.info("✓ 成功连接到子窗口: %s", child_title)
                                            self._apply_window_geometry()
                                            self._bring_window_to_front()
                                            self._ensure_topmost_windows()
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

    def _parse_geometry(self, geometry_cfg: Optional[Dict[str, Any]]) -> Optional[Tuple[int, int, int, int]]:
        """解析窗口位置配置。"""

        if not geometry_cfg:
            return None
        try:
            x = int(geometry_cfg.get("x", 0))
            y = int(geometry_cfg.get("y", 0))
            width = int(geometry_cfg.get("width", 0))
            height = int(geometry_cfg.get("height", 0))
        except (TypeError, ValueError):
            self.logger.warning("window_geometry 配置无效: %s", geometry_cfg)
            return None
        if width <= 0 or height <= 0:
            return None
        return (x, y, width, height)

    def get_window_rect(self, title_keyword: str, timeout: int = 5):  # type: ignore[override]
        """获取标题包含关键字的窗口矩形，返回 pywinauto Rectangle。"""

        if not title_keyword:
            return None

        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                windows = Desktop(backend="uia").windows()
                for window in windows:
                    try:
                        current_title = window.window_text() or ""
                        if title_keyword in current_title:
                            self.logger.debug("get_window_rect 命中窗口: %s", current_title)
                            return window.rectangle()
                    except Exception:  # pylint: disable=broad-except
                        continue
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.debug("获取窗口矩形失败: %s", exc)
                break
            time.sleep(0.5)

        return None

    def _parse_topmost_keywords(self, keywords_cfg: Optional[List[str]]) -> List[str]:
        """解析需要置顶的窗口关键字。"""

        if not keywords_cfg:
            return []
        keywords: List[str] = []
        for item in keywords_cfg:
            if not isinstance(item, str):
                continue
            keyword = item.strip()
            if keyword:
                keywords.append(keyword)
        return keywords

    def _apply_window_geometry(self) -> None:
        """根据配置设置窗口位置和大小。"""

        if not self._main_window or not self._window_geometry:
            return
        x, y, width, height = self._window_geometry
        try:
            self._main_window.move_window(x, y, width, height, repaint=True)
            self.logger.info(
                "窗口已调整到位置(%s,%s) 尺寸(%sx%s)",
                x,
                y,
                width,
                height,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.warning("调整窗口位置失败: %s", exc)

    def _bring_window_to_front(self) -> None:
        """尝试前置窗口并确保可见。"""

        if not self._main_window:
            return
        try:
            self._main_window.set_focus()
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.debug("设置窗口焦点失败: %s", exc)
        try:
            self._main_window.restore()
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.debug("恢复窗口失败: %s", exc)
        self._ensure_topmost_windows()

    def _ensure_topmost_windows(self) -> None:
        """根据配置将相关窗口置顶展示。"""

        if not self._main_window and not self._topmost_keywords:
            return

        def _set_topmost(handle: Optional[int], title: str) -> None:
            if not handle:
                return
            try:
                win32gui.SetWindowPos(
                    handle,
                    win32con.HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
                )
                self.logger.debug("窗口已置顶: %s", title)
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.debug("设置窗口置顶失败 (%s): %s", title, exc)

        # 先处理主窗口
        if self._main_window:
            _set_topmost(self._main_window.handle, self._main_window.window_text())

        if not self._topmost_keywords:
            return

        try:
            windows = Desktop(backend="uia").windows()
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.debug("枚举窗口失败: %s", exc)
            return

        for window in windows:
            try:
                title = window.window_text() or ""
                if not title:
                    continue
                if any(keyword in title for keyword in self._topmost_keywords):
                    _set_topmost(window.handle, title)
            except Exception:  # pylint: disable=broad-except
                continue

    def ensure_window_on_top(self, timeout: int = 10) -> None:
        """确保主窗口已连接并置顶显示。"""

        if not self._main_window:
            try:
                self.connect_to_window(timeout=timeout)
            except AutomationException as exc:
                self.logger.warning("确保窗口置顶失败：%s", exc)
                return

        self._bring_window_to_front()

    def ensure_window_visible_by_title(self, title_keyword: str, timeout: int = 5) -> None:
        """根据标题关键字前置并恢复指定窗口（不修改当前主窗口）。

        Args:
            title_keyword: 窗口标题中应包含的关键字
            timeout: 超时时间（秒）
        """

        if not title_keyword:
            return

        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                windows = Desktop(backend="uia").windows()
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.debug("枚举窗口失败: %s", exc)
                break

            for window in windows:
                try:
                    title = window.window_text() or ""
                    if not title or title_keyword not in title:
                        continue

                    try:
                        window.set_focus()
                    except Exception as exc:  # pylint: disable=broad-except
                        self.logger.debug("设置窗口焦点失败 (%s): %s", title, exc)
                    try:
                        window.restore()
                    except Exception as exc:  # pylint: disable=broad-except
                        self.logger.debug("恢复窗口失败 (%s): %s", title, exc)

                    self.logger.info("✓ 已前置并恢复窗口: %s", title)
                    return
                except Exception:  # pylint: disable=broad-except
                    continue

            time.sleep(0.5)

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
        """返回当前已连接的主窗口。"""

        return self._main_window

    def find_child_window(self, title_keyword: str, timeout: int = 5) -> Optional[UIAWrapper]:
        """在当前主窗口中查找包含关键字的子窗口。"""

        if not self._main_window or not title_keyword:
            return None

        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                descendants = self._main_window.descendants()
                for child in descendants:
                    try:
                        child_title = child.window_text() or ""
                        if title_keyword in child_title:
                            self.logger.debug("找到子窗口: %s", child_title)
                            return child
                    except Exception:  # pylint: disable=broad-except
                        continue
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.debug("查找子窗口失败: %s", exc)
                break
            time.sleep(0.5)

        return None

    def highlight_control(self, control: UIAWrapper, duration: float = 0.2) -> None:
        """在控件周围显示红色高亮框。"""

        if not self._enable_highlight:
            return

        try:
            rect = control.rectangle()
            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom

            import tkinter as tk

            highlight_window = tk.Tk()
            highlight_window.overrideredirect(True)
            highlight_window.attributes('-topmost', True)
            highlight_window.attributes('-alpha', 0.3)

            width = right - left
            height = bottom - top
            highlight_window.geometry(f"{width}x{height}+{left}+{top}")

            canvas = tk.Canvas(highlight_window, bg='red', highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            border_width = 3
            canvas.create_rectangle(
                border_width,
                border_width,
                width - border_width,
                height - border_width,
                outline='red',
                width=border_width * 2,
                fill='',
            )

            highlight_window.update()
            time.sleep(duration)
            highlight_window.destroy()
            self.logger.debug("已显示控件高亮提示")

        except Exception as exc:
            self.logger.warning("显示控件高亮失败: %s", exc)

    @property
    def is_connected(self) -> bool:
        """检查是否已连接到窗口。"""
        return self._main_window is not None
