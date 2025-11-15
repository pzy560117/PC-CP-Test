"""数据库连接工具，复用 analysis 模块的 Engine。"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.engine import Connection

from analysis.src.database import get_engine


_engine = None


def get_connection() -> Connection:
    """获取 SQLAlchemy Connection。"""

    engine = get_engine()
    return engine.connect()


@contextmanager
def connection_scope() -> Iterator[Connection]:
    """提供上下文便于 API 查询。"""

    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def fetch_draws(limit: int) -> list[dict]:
    """查询最近开奖记录。"""

    with connection_scope() as conn:
        rows = conn.execute(
            text(
                """
                SELECT period, draw_time, timestamp, numbers, sum, span, odd_even, big_small
                FROM lottery_draws
                ORDER BY draw_time DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
        return [dict(row) for row in rows]


def fetch_draw_by_period(period: str) -> dict | None:
    """按期号查询单条记录。"""

    with connection_scope() as conn:
        row = conn.execute(
            text(
                """
                SELECT period, draw_time, timestamp, numbers, sum, span, odd_even, big_small
                FROM lottery_draws
                WHERE period=:period
                """
            ),
            {"period": period},
        ).mappings().first()
        return dict(row) if row else None
