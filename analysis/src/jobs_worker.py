"""analysis_jobs worker：消费待处理任务并生成基础特征。"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .database import session_scope

logger = logging.getLogger(__name__)


def fetch_pending_jobs(limit: int = 20) -> list[dict[str, Any]]:
    """拉取待处理的 analysis_jobs 任务。"""

    with session_scope() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, job_type, payload
                FROM analysis_jobs
                WHERE status='pending'
                ORDER BY created_at ASC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings()
        return [dict(r) for r in rows]


def update_job_status(conn, job_id: int, status: str, result_id: int | None = None) -> None:
    """更新任务状态，记录开始/结束时间。"""

    conn.execute(
        text(
            """
            UPDATE analysis_jobs
            SET status=:status,
                result_id=:result_id,
                started_at=COALESCE(started_at, NOW()),
                finished_at=CASE WHEN :status IN ('finished', 'failed') THEN NOW() ELSE finished_at END,
                updated_at=NOW()
            WHERE id=:id
            """
        ),
        {"status": status, "result_id": result_id, "id": job_id},
    )


def _parse_payload(payload: Any) -> dict[str, Any]:
    """将 payload 转换为字典。"""

    if isinstance(payload, str):
        return json.loads(payload)
    if isinstance(payload, dict):
        return payload
    raise ValueError("payload must be JSON string or dict")


def _extract_basic_features(conn, period: str) -> int:
    """读取 lottery_draws 并落地基础特征与结果，返回 analysis_results.id。"""

    row = conn.execute(
        text(
            """
            SELECT period, numbers, sum, span, odd_even, big_small
            FROM lottery_draws
            WHERE period=:period
            """
        ),
        {"period": period},
    ).mappings().first()
    if not row:
        raise ValueError(f"period {period} not found in lottery_draws")

    numbers_raw = row["numbers"]
    numbers = json.loads(numbers_raw) if isinstance(numbers_raw, str) else list(numbers_raw)
    if not numbers:
        raise ValueError(f"period {period} has empty numbers")

    features = {
        "period": period,
        "count": len(numbers),
        "max": max(numbers),
        "min": min(numbers),
        "mean": sum(numbers) / len(numbers),
        "sum": row["sum"],
        "span": row["span"],
        "odd_even": row["odd_even"],
        "big_small": row["big_small"],
    }

    conn.execute(
        text(
            """
            INSERT INTO lottery_features(period, feature_type, feature_value)
            VALUES (:period, 'basic_stats', :feature_value)
            ON DUPLICATE KEY UPDATE feature_value=:feature_value
            """
        ),
        {"period": period, "feature_value": json.dumps(features)},
    )

    result = conn.execute(
        text(
            """
            INSERT INTO analysis_results(analysis_type, result_data)
            VALUES ('basic_feature', :result_data)
            """
        ),
        {"result_data": json.dumps(features)},
    )
    return result.lastrowid


def handle_job(job: dict[str, Any]) -> None:
    """消费单条任务，当前支持 feature_extract 基础特征。"""

    payload = _parse_payload(job["payload"])
    job_type = job["job_type"]
    job_id = job["id"]

    with session_scope() as conn:
        update_job_status(conn, job_id, "processing")
        try:
            if job_type == "feature_extract":
                result_id = _extract_basic_features(conn, payload["period"])
                update_job_status(conn, job_id, "finished", result_id=result_id)
            else:
                raise ValueError(f"unsupported job_type {job_type}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("job %s failed: %s", job_id, exc)
            update_job_status(conn, job_id, "failed")
            raise


def run_worker(poll_interval: float = 2.0, batch_size: int = 10, once: bool = True) -> None:
    """轮询执行待处理任务，可单次运行或常驻守护。"""

    while True:
        jobs = fetch_pending_jobs(limit=batch_size)
        if not jobs:
            if once:
                return
            time.sleep(poll_interval)
            continue

        for job in jobs:
            try:
                handle_job(job)
            except SQLAlchemyError:
                logger.exception("job %s failed due to database error", job["id"])
            except Exception:
                logger.exception("job %s failed", job["id"])

        if once:
            return
        time.sleep(poll_interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker(once=False)
