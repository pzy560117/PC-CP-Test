"""配置模块：负责加载采集与数据库所需环境变量。"""
from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class ApiConfig:
    """API 相关配置。"""

    history_endpoint: str
    latest_endpoint: str
    user_agent: str
    timeout: float


@dataclass
class DatabaseConfig:
    """数据库与 Redis 连接配置。"""

    mysql_dsn: str
    redis_url: str


@dataclass
class CollectorConfig:
    """采集服务整体配置。"""

    api: ApiConfig
    database: DatabaseConfig
    batch_size: int
    retry: int
    retry_backoff: float
    throttle_seconds: float


def load_config() -> CollectorConfig:
    """从环境变量加载采集与数据库配置。"""

    api_cfg = ApiConfig(
        history_endpoint=os.environ.get("TXFF_HISTORY_ENDPOINT", "https://kjapi.com/hall/hallhistory/txffcqiqu/ksffc"),
        latest_endpoint=os.environ.get("TXFF_LATEST_ENDPOINT", "https://kjapi.com/hall/hallhistoryDetail/txffcqiqu"),
        user_agent=os.environ.get("HTTP_USER_AGENT", "Mozilla/5.0"),
        timeout=float(os.environ.get("HTTP_TIMEOUT", "5")),
    )
    default_dsn = "mysql+pymysql://root:560117@localhost:3306/lottery"
    db_cfg = DatabaseConfig(
        mysql_dsn=os.environ.get("MYSQL_DSN", default_dsn),
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    )
    return CollectorConfig(
        api=api_cfg,
        database=db_cfg,
        batch_size=int(os.environ.get("COLLECT_BATCH", "120")),
        retry=int(os.environ.get("COLLECT_RETRY", "3")),
        retry_backoff=float(os.environ.get("HTTP_RETRY_BACKOFF", "1.0")),
        throttle_seconds=float(os.environ.get("HTTP_THROTTLE_SECONDS", "0.5")),
    )
