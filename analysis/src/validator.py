"""开奖数据校验与落盘脚本。"""
from __future__ import annotations

import logging
from typing import Any

import json

from sqlalchemy import text

from .database import insert_validated_draw, session_scope

logger = logging.getLogger(__name__)


REQUIRED_FIELDS = ("period", "openTime", "openCode")


def load_pending_raw(limit: int = 200) -> list[dict[str, Any]]:
    """拉取等待校验的 raw_lottery_draws 记录。"""

    with session_scope() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, payload
                FROM raw_lottery_draws
                WHERE status='pending'
                ORDER BY fetched_at ASC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings()
        result = []
        for row in rows:
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            result.append({"id": row["id"], "payload": payload})
        return result


def validate_payload(payload: dict[str, Any]) -> tuple[bool, str | None]:
    """执行字段完整性与范围检验。"""

    for field in REQUIRED_FIELDS:
        if field not in payload:
            return False, f"missing field {field}"
    numbers = [int(x) for x in payload["openCode"].split(",")]
    if any(num < 0 or num > 9 for num in numbers):
        return False, "number out of range"
    return True, None


def transform_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """将原始响应转换为 lottery_draws 表结构。"""

    numbers = [int(x) for x in payload["openCode"].split(",")]
    total = sum(numbers)
    return {
        "period": payload["period"],
        "draw_time": payload["openTime"],
        "timestamp": payload.get("timestamp", payload.get("openTimestamp")),
        "numbers": numbers,
        "sum": total,
        "span": max(numbers) - min(numbers),
        "odd_even": "odd" if total % 2 else "even",
        "big_small": "big" if total >= 23 else "small",
    }


def run_validation() -> None:
    """入口：校验 raw 数据并写入 lottery_draws。"""

    pending = load_pending_raw()
    if not pending:
        logger.info("no pending raw draws")
        return

    with session_scope() as conn:
        for row in pending:
            payload = row["payload"]
            is_valid, error = validate_payload(payload)
            if not is_valid:
                logger.error("payload invalid period=%s reason=%s", payload.get("period"), error)
                conn.execute(
                    text("UPDATE raw_lottery_draws SET status='failed' WHERE id=:id"),
                    {"id": row["id"]},
                )
                continue
            insert_validated_draw(conn, transform_payload(payload))
            conn.execute(
                text("UPDATE raw_lottery_draws SET status='passed' WHERE id=:id"),
                {"id": row["id"]},
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_validation()
