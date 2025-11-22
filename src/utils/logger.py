"""日志配置工具。"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


def configure_logging(config: Dict[str, Any], override_level: Optional[str] = None) -> None:
    """根据配置初始化日志系统。"""

    logging_cfg = config.get("logging", {})
    log_level = (override_level or logging_cfg.get("level", "INFO")).upper()
    log_format = logging_cfg.get("format", "%(asctime)s - %(levelname)s - %(message)s")
    log_file = logging_cfg.get("file", "./logs/app.log")
    max_size = _parse_bytes(logging_cfg.get("max_size", "10MB"))
    backup_count = int(logging_cfg.get("backup_count", 5))
    console_output = logging_cfg.get("console_output", True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    formatter = logging.Formatter(log_format)

    file_path = Path(log_file)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(file_path, maxBytes=max_size, backupCount=backup_count, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    module_levels = logging_cfg.get("modules", {})
    for module_name, module_level in module_levels.items():
        logging.getLogger(module_name).setLevel(module_level.upper())


def _parse_bytes(value: str) -> int:
    """将易读的容量配置转换为字节数。"""

    normalized = value.strip().upper()
    units = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
    for suffix, multiplier in units.items():
        if normalized.endswith(suffix):
            return int(float(normalized.replace(suffix, "")) * multiplier)
    return int(float(normalized))
