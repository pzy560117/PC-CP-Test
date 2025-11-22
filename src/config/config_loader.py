"""配置加载器，负责读取和维护项目配置。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """读取 config/config.json 并提供访问接口。"""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """构造函数，立即加载配置。"""
        project_root = Path(__file__).resolve().parents[2]
        default_path = project_root / "config" / "config.json"
        self.config_path = Path(config_path).resolve() if config_path else default_path
        self._config: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        """重新读取配置文件。"""
        try:
            with self.config_path.open("r", encoding="utf-8") as handle:
                self._config = json.load(handle)
        except FileNotFoundError as exc:
            logging.error("配置文件缺失: %s", self.config_path)
            raise exc
        except json.JSONDecodeError as exc:
            logging.error("配置文件 JSON 解析失败: %s", exc)
            raise exc

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """按照点号路径获取配置值。"""
        cursor: Any = self._config
        for key in dotted_key.split("."):
            if not isinstance(cursor, dict) or key not in cursor:
                return default
            cursor = cursor[key]
        return cursor

    def as_dict(self) -> Dict[str, Any]:
        """返回配置副本，避免外部直接修改内部状态。"""
        return dict(self._config)

    def ensure_directories(self) -> None:
        """根据配置创建数据与日志目录。"""
        directories = set()
        data_cfg = self.get("data", {}) or {}
        directories.update(
            {
                data_cfg.get("storage_path"),
                data_cfg.get("history_path"),
                data_cfg.get("results_path"),
                data_cfg.get("backup_path"),
            }
        )
        log_file = self.get("logging.file")
        if log_file:
            directories.add(str(Path(log_file).parent))

        for directory in filter(None, directories):
            Path(directory).mkdir(parents=True, exist_ok=True)
