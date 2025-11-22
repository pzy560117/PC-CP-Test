"""定义项目专用异常类型。"""
from __future__ import annotations


class AutomationException(Exception):
    """自动化流程基础异常。"""


class ConfigException(AutomationException):
    """配置相关异常。"""


class InterfaceNotFoundException(AutomationException):
    """界面或元素定位失败时抛出。"""


class APICallException(AutomationException):
    """API 调用失败时抛出。"""


class DataProcessException(AutomationException):
    """数据解析或处理失败时抛出。"""
