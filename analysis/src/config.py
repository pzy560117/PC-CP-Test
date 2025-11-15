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
    sources: list["CollectorSourceConfig"]
    monitoring_enabled: bool
    max_error_before_alert: int
    batch_size: int
    retry: int
    retry_backoff: float
    throttle_seconds: float


@dataclass
class CollectorSourceConfig:
    """单个采集源配置。"""

    name: str
    endpoint: str
    parser: str  # history_html / latest_json
    enabled: bool = True


@dataclass
class SchedulerConfig:
    """调度配置。"""

    collector_interval: int
    validator_interval: int
    worker_interval: int
    alert_window: int
    alert_threshold: int
    loop_sleep: float
    alert_cooldown: float


def _bool_env(key: str, default: str = "true") -> bool:
    """解析布尔环境变量。"""

    return os.environ.get(key, default).strip().lower() in {"1", "true", "yes", "on"}


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
    sources = [
        CollectorSourceConfig(
            name="history",
            endpoint=api_cfg.history_endpoint,
            parser="history_html",
            enabled=_bool_env("COLLECT_HISTORY_ENABLED", "true"),
        ),
        CollectorSourceConfig(
            name="latest",
            endpoint=api_cfg.latest_endpoint,
            parser="latest_json",
            enabled=_bool_env("COLLECT_LATEST_ENABLED", "false"),
        ),
    ]
    return CollectorConfig(
        api=api_cfg,
        database=db_cfg,
        sources=[src for src in sources if src.enabled],
        monitoring_enabled=_bool_env("COLLECT_MONITORING_ENABLED", "true"),
        max_error_before_alert=int(os.environ.get("COLLECT_ALERT_THRESHOLD", "5")),
        batch_size=int(os.environ.get("COLLECT_BATCH", "120")),
        retry=int(os.environ.get("COLLECT_RETRY", "3")),
        retry_backoff=float(os.environ.get("HTTP_RETRY_BACKOFF", "1.0")),
        throttle_seconds=float(os.environ.get("HTTP_THROTTLE_SECONDS", "0.5")),
    )


def load_scheduler_config() -> SchedulerConfig:
    """加载调度与告警相关配置。"""

    return SchedulerConfig(
        collector_interval=int(os.environ.get("SCHED_COLLECTOR_INTERVAL", "300")),
        validator_interval=int(os.environ.get("SCHED_VALIDATOR_INTERVAL", "120")),
        worker_interval=int(os.environ.get("SCHED_WORKER_INTERVAL", "60")),
        alert_window=int(os.environ.get("SCHED_ALERT_WINDOW", "5")),
        alert_threshold=int(os.environ.get("SCHED_ALERT_THRESHOLD", "3")),
        loop_sleep=float(os.environ.get("SCHED_LOOP_SLEEP", "5")),
        alert_cooldown=float(os.environ.get("SCHED_ALERT_COOLDOWN", "300")),
    )
