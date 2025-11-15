"""数据库连接与通用持久化操作。"""
from __future__ import annotations

from contextlib import contextmanager
import json
from typing import Iterator

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

    conn.execute(
        text(
            """
            INSERT INTO analysis_jobs(job_type, payload, status)
            VALUES ('feature_extract', JSON_OBJECT('period', :period), 'pending')
            ON DUPLICATE KEY UPDATE payload=VALUES(payload), updated_at=NOW()
            """
        ),
        {"period": record["period"]},
    )
