"""数据库连接与通用持久化操作。"""
from __future__ import annotations

from contextlib import contextmanager
import json
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .config import load_config


_engine: Engine | None = None


def get_engine() -> Engine:
    """初始化或获取全局 SQLAlchemy Engine。"""

    global _engine
    if _engine is None:
        cfg = load_config()
        _engine = create_engine(cfg.database.mysql_dsn, pool_pre_ping=True, future=True)
    return _engine


@contextmanager
def session_scope() -> Iterator[Engine]:
    """提供一个简单的连接上下文，用于执行 SQL。"""

    engine = get_engine()
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
        trans.commit()
    except SQLAlchemyError:
        trans.rollback()
        raise
    finally:
        conn.close()


def insert_raw_draw(conn, payload: dict, source: str) -> None:
    """将原始开奖响应写入 raw_lottery_draws。"""

    conn.execute(
        text(
            """
            INSERT INTO raw_lottery_draws(period, payload, source, fetched_at, status)
            VALUES (:period, :payload, :source, NOW(), 'pending')
            ON DUPLICATE KEY UPDATE payload=:payload, source=:source, fetched_at=NOW()
            """
        ),
        {
            "period": payload["period"],
            "payload": json.dumps(payload),
            "source": source,
        },
    )


def insert_validated_draw(conn, record: dict) -> None:
    """将校验通过的数据写入 lottery_draws 并关联特征任务。"""

    conn.execute(
        text(
            """
            INSERT INTO lottery_draws(period, draw_time, timestamp, numbers, sum, span, odd_even, big_small)
            VALUES (:period, :draw_time, :timestamp, :numbers, :sum, :span, :odd_even, :big_small)
            ON DUPLICATE KEY UPDATE draw_time=:draw_time, timestamp=:timestamp, numbers=:numbers,
                sum=:sum, span=:span, odd_even=:odd_even, big_small=:big_small, updated_at=NOW()
            """
        ),
        {
            **record,
            "numbers": json.dumps(record["numbers"]),
        },
    )

    enqueue_analysis_job(conn, "feature_extract", {"period": record["period"]}, priority=3)
    enqueue_analysis_job(
        conn,
        "trend_summary",
        {"period": record["period"], "window": 20},
        priority=6,
    )
    enqueue_analysis_job(
        conn,
        "statistical_analysis",
        {"period": record["period"], "window": 180},
        priority=7,
    )
    enqueue_analysis_job(
        conn,
        "strategy_backtest",
        {
            "period": record["period"],
            "window": 360,
            "short_window": 12,
            "long_window": 60,
            "stake": 1.0,
            "payout_multiplier": 0.92,
        },
        priority=8,
    )


def enqueue_analysis_job(conn, job_type: str, payload: dict[str, Any], priority: int = 5) -> None:
    """向 analysis_jobs 写入任务。"""

    conn.execute(
        text(
            """
            INSERT INTO analysis_jobs(job_type, payload, priority, status)
            VALUES (:job_type, :payload, :priority, 'pending')
            """
        ),
        {"job_type": job_type, "payload": json.dumps(payload), "priority": priority},
    )


def record_collector_log(conn, source: str, level: str, message: str, detail: dict | None = None) -> None:
    """将采集异常/监控信息写入 collector_logs。"""

    conn.execute(
        text(
            """
            INSERT INTO collector_logs(source, level, message, detail, created_at)
            VALUES (:source, :level, :message, :detail, NOW())
            """
        ),
        {"source": source, "level": level, "message": message[:255], "detail": json.dumps(detail) if detail else None},
    )


def record_pipeline_stat(conn, component: str, metric: str, value: float, detail: dict | None = None) -> None:
    """写入 pipeline_stats 指标。"""

    conn.execute(
        text(
            """
            INSERT INTO pipeline_stats(component, metric, metric_value, detail)
            VALUES (:component, :metric, :value, :detail)
            """
        ),
        {
            "component": component,
            "metric": metric,
            "value": value,
            "detail": json.dumps(detail) if detail else None,
        },
    )


def record_pipeline_alert(conn, component: str, level: str, message: str, detail: dict | None = None) -> None:
    """记录调度/监控告警。"""

    conn.execute(
        text(
            """
            INSERT INTO pipeline_alerts(component, level, message, detail)
            VALUES (:component, :level, :message, :detail)
            """
        ),
        {
            "component": component,
            "level": level,
            "message": message[:255],
            "detail": json.dumps(detail) if detail else None,
        },
    )


def fetch_recent_stats(component: str, limit: int = 5) -> list[dict[str, Any]]:
    """查询最近的 pipeline_stats 记录。"""

    with session_scope() as conn:
        rows = conn.execute(
            text(
                """
                SELECT component, metric, metric_value, detail, created_at
                FROM pipeline_stats
                WHERE component=:component
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"component": component, "limit": limit},
        ).mappings().all()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        detail = row.get("detail")
        if isinstance(detail, str):
            try:
                item["detail"] = json.loads(detail)
            except json.JSONDecodeError:
                item["detail"] = detail
        result.append(item)
    return result
