"""Backend配置，提供数据库 DSN 等参数。"""
from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class Settings:
    mysql_dsn: str
    max_draws: int = 200
    max_results: int = 200
    max_jobs: int = 200


def get_settings() -> Settings:
    """加载配置，如果未设置环境变量则使用默认 MySQL 密码 560117。"""

    default_dsn = "mysql+pymysql://root:560117@localhost:3306/lottery"
    return Settings(
        mysql_dsn=os.environ.get("MYSQL_DSN", default_dsn),
        max_draws=int(os.environ.get("API_MAX_DRAWS", "200")),
        max_results=int(os.environ.get("API_MAX_RESULTS", "200")),
        max_jobs=int(os.environ.get("API_MAX_JOBS", "200")),
    )
