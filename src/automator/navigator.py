"""应用界面导航器。"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pyautogui

from src.automator.window_manager import WindowManager
from src.exception.custom_exceptions import AutomationException


class Navigator:
    """负责应用内的界面导航。"""

    def __init__(self, window_manager: WindowManager, app_config: Dict[str, Any]) -> None:
        """初始化导航器。
        
        Args:
            window_manager: 窗口管理器实例
            app_config: 应用配置字典
        """
        self._window_manager = window_manager
        self._config = app_config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def navigate_to_search_interface(self) -> None:
        """导航到搜索公式界面。
        
        执行步骤：
        1. 点击"腾讯分分彩"标签页
        2. 点击"搜索公式"按钮或标签
        """
        self.logger.info("开始导航到搜索公式界面...")
        
        try:
            # 步骤1：点击"腾讯分分彩"标签
            self._click_lottery_tab()
            self.logger.info("等待彩种界面加载...")
            time.sleep(2)  # 等待界面完全加载
            
            # 步骤2：点击"搜索公式"按钮
            self._click_search_tab()
            self.logger.info("等待搜索界面加载...")
            time.sleep(1.5)  # 等待搜索界面加载
            
            self.logger.info("成功导航到搜索公式界面")
            
        except Exception as exc:
            raise AutomationException("导航到搜索公式界面失败") from exc

    def _click_lottery_tab(self) -> None:
        """点击"腾讯分分彩"标签页。"""
        lottery_tab_name = self._config.get("elements", {}).get("lottery_tab", "腾讯分分彩")
        
        self.logger.info("查找并点击标签页: %s", lottery_tab_name)
        
        # 支持的搜索关键词（按优先级）
        search_keywords = [
            lottery_tab_name,  # 完整名称
            "腾讯",            # 部分匹配
            "分分彩",          # 部分匹配
            "TXFFC"            # 可能的缩写
        ]
        
        main_window = self._window_manager.main_window
        if not main_window:
            raise AutomationException("主窗口未连接")
        
        # 尝试多种方式查找标签页
        tab_found = False
        
        # 方式1：查找TabItem或RadioButton控件
        try:
            # 先尝试RadioButton（根据日志，界面使用RadioButton）
            tabs = main_window.descendants(control_type="RadioButton")
            if not tabs:
                tabs = main_window.descendants(control_type="TabItem")
            self.logger.debug("找到 %d 个控件", len(tabs))
            for tab in tabs:
                try:
                    tab_text = tab.window_text()
                    # 使用关键词匹配
                    for keyword in search_keywords:
                        if keyword in tab_text:
                            self.logger.info("找到标签页: %s (匹配关键词: %s)", tab_text, keyword)
                            # 高亮显示
                            self._window_manager.highlight_control(tab, duration=0.2)
                            # 点击
                            tab.click_input()
                            self.logger.info("已点击标签页: %s", lottery_tab_name)
                            tab_found = True
                            return
                except Exception:  # pylint: disable=broad-except
                    continue
        except Exception:  # pylint: disable=broad-except
            pass
        
        # 方式2：查找包含文本的Button或Text控件
        if not tab_found:
            try:
                controls = main_window.descendants()
                for control in controls:
                    try:
                        control_text = control.window_text()
                        # 使用关键词匹配
                        for keyword in search_keywords:
                            if keyword in control_text:
                                control_type = control.element_info.control_type
                                # 只处理可点击的控件
                                if control_type in ["Button", "TabItem", "Hyperlink", "Text", "RadioButton"]:
                                    self.logger.info("找到控件: %s (类型: %s, 匹配: %s)", control_text, control_type, keyword)
                                    # 高亮显示
                                    self._window_manager.highlight_control(control, duration=0.2)
                                    # 点击
                                    control.click_input()
                                    self.logger.info("已点击: %s", lottery_tab_name)
                                    tab_found = True
                                    return
                    except Exception:  # pylint: disable=broad-except
                        continue
            except Exception:  # pylint: disable=broad-except
                pass
        
        if not tab_found:
            # 调试：打印所有可能的文本控件
            self.logger.error("未找到标签页: %s", lottery_tab_name)
            self.logger.error("正在列出所有可能的控件...")
            try:
                all_controls = main_window.descendants()
                control_texts = []
                for ctrl in all_controls[:50]:  # 只打印前50个
                    try:
                        text = ctrl.window_text()
                        if text and len(text) > 0:
                            control_type = ctrl.element_info.control_type
                            control_texts.append(f"{control_type}: '{text}'")
                    except:
                        pass
                self.logger.error("前50个控件: %s", ", ".join(control_texts[:20]))
            except:
                pass
            raise AutomationException(f"未找到标签页: {lottery_tab_name}")

    def _click_search_tab(self) -> None:
        """点击"搜索公式"按钮或标签。"""
        search_tab_name = self._config.get("elements", {}).get("search_tab", "搜索公式")
        
        self.logger.info("查找并点击: %s", search_tab_name)
        
        main_window = self._window_manager.main_window
        if not main_window:
            raise AutomationException("主窗口未连接")
        
        # 尝试多种方式查找
        found = False
        
        # 方式1：查找Button控件
        try:
            buttons = main_window.descendants(control_type="Button")
            self.logger.debug("找到 %d 个 Button 控件", len(buttons))
            for button in buttons:
                try:
                    button_text = button.window_text()
                    # 使用关键词匹配
                    for keyword in search_keywords:
                        if keyword in button_text:
                            self.logger.info("找到按钮: %s (匹配: %s)", button_text, keyword)
                            # 高亮显示
                            self._window_manager.highlight_control(button, duration=0.2)
                            # 点击
                            button.click_input()
                            self.logger.info("已点击: %s", search_tab_name)
                            found = True
                            return
                except Exception:  # pylint: disable=broad-except
                    continue
        except Exception:  # pylint: disable=broad-except
            pass
        
        # 方式2：查找TabItem控件
        if not found:
            try:
                tabs = main_window.descendants(control_type="TabItem")
                self.logger.debug("找到 %d 个 TabItem 控件", len(tabs))
                for tab in tabs:
                    try:
                        tab_text = tab.window_text()
                        # 使用关键词匹配
                        for keyword in search_keywords:
                            if keyword in tab_text:
                                self.logger.info("找到标签: %s (匹配: %s)", tab_text, keyword)
                                # 高亮显示
                                self._window_manager.highlight_control(tab, duration=0.2)
                                # 点击
                                tab.click_input()
                                self.logger.info("已点击: %s", search_tab_name)
                                found = True
                                return
                    except Exception:  # pylint: disable=broad-except
                        continue
            except Exception:  # pylint: disable=broad-except
                pass
        
        # 方式3：查找所有可能的控件
        if not found:
            try:
                controls = main_window.descendants()
                self.logger.debug("开始遍历所有控件...")
                for control in controls[:200]:  # 限制检查数量
                    try:
                        control_text = control.window_text()
                        # 使用关键词匹配
                        for keyword in search_keywords:
                            if keyword in control_text:
                                control_type = control.element_info.control_type
                                # 只处理可点击的控件
                                if control_type in ["Button", "TabItem", "Hyperlink", "MenuItem", "Text", "ListItem"]:
                                    self.logger.info("找到控件: %s (类型: %s, 匹配: %s)", control_text, control_type, keyword)
                                    # 高亮显示
                                    self._window_manager.highlight_control(control, duration=0.2)
                                    # 点击
                                    control.click_input()
                                    self.logger.info("已点击: %s", search_tab_name)
                                    found = True
                                    return
                    except Exception:  # pylint: disable=broad-except
                        continue
            except Exception:  # pylint: disable=broad-except
                pass
        
        # 方式4：使用图像识别（备用方案）
        if not found:
            self.logger.warning("UI Automation 未找到控件，尝试图像识别...")
            
            # 尝试不同的图片名称
            image_files = [
                "search_formula_button.png",
                "formula_search.png",
                "gongshi_sousuo.png",
                "search_button.png"
            ]
            
            for image_file in image_files:
                if self._click_by_image(image_file, confidence=0.8):
                    self.logger.info("通过图像识别成功点击: %s", search_tab_name)
                    found = True
                    return
        
        if not found:
            # 调试：列出可用的控件
            self.logger.error("未找到: %s", search_tab_name)
            self.logger.error("提示：请截取'公式搜索'按钮并保存为 images/search_formula_button.png")
            self.logger.error("正在列出所有可能的控件...")
            try:
                all_controls = main_window.descendants()
                control_texts = []
                for ctrl in all_controls[:50]:
                    try:
                        text = ctrl.window_text()
                        if text and len(text) > 0:
                            control_type = ctrl.element_info.control_type
                            control_texts.append(f"{control_type}: '{text}'")
                    except:
                        pass
                self.logger.error("前50个控件: %s", ", ".join(control_texts[:20]))
            except:
                pass
            raise AutomationException(f"未找到: {search_tab_name}，请截取按钮图片保存到 images/search_formula_button.png")

    def _click_by_image(self, image_name: str, confidence: float = 0.8, region: Optional[Tuple[int, int, int, int]] = None, timeout: int = 10) -> bool:
        """通过图像识别点击控件（带显式等待）。
        
        Args:
            image_name: 图片文件名（相对于 images/ 目录）
            confidence: 匹配置信度（0-1）
            region: 搜索区域 (left, top, width, height)，None 为全屏
            timeout: 等待超时时间（秒）
            
        Returns:
            是否成功找到并点击
        """
        try:
            # 构建图片路径
            image_path = Path("images") / image_name
            
            if not image_path.exists():
                self.logger.warning("图片不存在: %s", image_path)
                return False
            
            self.logger.info("通过图像识别查找: %s (置信度: %.2f, 超时: %ds)", image_name, confidence, timeout)
            
            # 显式等待：循环查找图片直到找到或超时
            start_time = time.time()
            location = None
            
            while time.time() - start_time < timeout:
                try:
                    location = pyautogui.locateOnScreen(
                        str(image_path),
                        confidence=confidence,
                        region=region
                    )
                    
                    if location:
                        break
                    
                    # 未找到，等待0.5秒后重试
                    time.sleep(0.5)
                    
                except Exception:
                    # 识别失败，继续重试
                    time.sleep(0.5)
                    continue
            
            if location:
                # 获取中心点
                center = pyautogui.center(location)
                elapsed = time.time() - start_time
                self.logger.info("找到图像位置: %s, 中心点: %s (耗时: %.1fs)", location, center, elapsed)
                
                # 快速移动并点击
                pyautogui.moveTo(center.x, center.y, duration=0.1)  # 加快移动
                time.sleep(0.05)  # 减少等待
                
                # 点击
                pyautogui.click(center.x, center.y)
                self.logger.info("✓ 已通过图像识别点击: %s", image_name)
                return True
            else:
                self.logger.warning("等待 %ds 后仍未找到图像: %s", timeout, image_name)
                return False
                
        except Exception as exc:
            self.logger.error("图像识别失败: %s, 错误: %s", image_name, exc)
            return False

    def wait_for_interface_ready(self, timeout: int = 10) -> None:
        """等待界面加载完成。
        
        Args:
            timeout: 超时时间（秒）
        """
        self.logger.info("等待界面加载完成...")
        time.sleep(0.3)  # 快速检查
        self.logger.info("界面已就绪")
