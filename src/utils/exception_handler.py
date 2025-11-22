"""异常处理工具。"""
from __future__ import annotations

import logging
import traceback
from typing import Optional


def handle_exception(exc: Exception, logger: Optional[logging.Logger] = None) -> None:
    """记录异常详情，统一输出。"""

    active_logger = logger or logging.getLogger("ExceptionHandler")
    formatted = "".join(traceback.format_exception(exc))
    active_logger.error("捕获未处理异常：%s", exc)
    active_logger.debug("异常堆栈：\n%s", formatted)
