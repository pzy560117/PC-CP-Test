"""analysis_jobs worker：消费待处理任务并生成多种特征/分析结果。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import time
from typing import Any, Callable

from sqlalchemy import text

from .backtest import run_momentum_backtest
from .database import record_pipeline_stat, session_scope
from .statistics import build_statistical_report

logger = logging.getLogger(__name__)

JobHandler = Callable[[Any, dict[str, Any]], int | None]


def fetch_pending_jobs(limit: int = 20) -> list[dict[str, Any]]:
    """按 priority + created_at 拉取待处理任务。"""

    with session_scope() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, job_type, payload, priority
                FROM analysis_jobs
                WHERE status='pending'
                ORDER BY priority ASC, created_at ASC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings()
        return [dict(r) for r in rows]


def update_job_status(conn, job_id: int, status: str, result_id: int | None = None) -> None:
    """更新任务状态并记录时间。"""

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
    if isinstance(payload, str):
        return json.loads(payload)
    if isinstance(payload, dict):
        return payload
    raise ValueError("payload must be JSON string or dict")


def _extract_basic_features(conn, payload: dict[str, Any]) -> int:
    """写入 basic_stats 特征与 analysis_results。"""

    period = payload["period"]
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
            INSERT INTO lottery_features(period, feature_type, schema_version, feature_value, meta)
            VALUES (:period, 'basic_stats', 1, :feature_value, :meta)
            ON DUPLICATE KEY UPDATE
                feature_value=VALUES(feature_value),
                schema_version=VALUES(schema_version),
                meta=VALUES(meta),
                updated_at=NOW()
            """
        ),
        {
            "period": period,
            "feature_value": json.dumps(features),
            "meta": json.dumps({"source": "jobs_worker", "version": 1}),
        },
    )

    summary = f"{period} sum={features['sum']} span={features['span']}"
    result = conn.execute(
        text(
            """
            INSERT INTO analysis_results(analysis_type, schema_version, result_summary, result_data, metadata)
            VALUES ('basic_feature', 1, :summary, :result_data, :metadata)
            """
        ),
        {
            "summary": summary[:255],
            "result_data": json.dumps(features),
            "metadata": json.dumps({"source": "jobs_worker", "version": 1}),
        },
    )
    return result.lastrowid


def _generate_trend_summary(conn, payload: dict[str, Any]) -> int:
    """生成窗口内和值趋势 summary。"""

    period = payload["period"]
    window = int(payload.get("window", 20))
    target = conn.execute(
        text("SELECT draw_time FROM lottery_draws WHERE period=:period"),
        {"period": period},
    ).scalar()
    if not target:
        raise ValueError(f"period {period} not found for trend job")

    rows = conn.execute(
        text(
            """
            SELECT period, sum, draw_time
            FROM lottery_draws
            WHERE draw_time <= :target
            ORDER BY draw_time DESC
            LIMIT :window
            """
        ),
        {"target": target, "window": window},
    ).mappings().all()
    if not rows:
        raise ValueError(f"no rows for trend job period={period}")

    sums = [row["sum"] for row in rows]
    avg_sum = sum(sums) / len(sums)
    trend = sums[0] - avg_sum
    trend_payload = {
        "period": period,
        "window": window,
        "count": len(sums),
        "average_sum": avg_sum,
        "latest_sum": sums[0],
        "trend_delta": trend,
    }

    conn.execute(
        text(
            """
            INSERT INTO lottery_features(period, feature_type, schema_version, feature_value, meta)
            VALUES (:period, 'trend_summary', 1, :feature_value, :meta)
            ON DUPLICATE KEY UPDATE
                feature_value=VALUES(feature_value),
                schema_version=VALUES(schema_version),
                meta=VALUES(meta),
                updated_at=NOW()
            """
        ),
        {
            "period": period,
            "feature_value": json.dumps(trend_payload),
            "meta": json.dumps({"window": window, "version": 1}),
        },
    )

    summary = f"{period} trendΔ={trend:.2f} (window={len(sums)})"
    result = conn.execute(
        text(
            """
            INSERT INTO analysis_results(analysis_type, schema_version, result_summary, result_data, metadata)
            VALUES ('trend_summary', 1, :summary, :result_data, :metadata)
            """
        ),
        {
            "summary": summary[:255],
            "result_data": json.dumps(trend_payload),
            "metadata": json.dumps({"window": window, "version": 1}),
        },
    )
    return result.lastrowid


def _upsert_feature(conn, period: str, feature_type: str, payload: dict[str, Any], meta: dict[str, Any]) -> None:
    """写入或更新 lottery_features 记录。"""

    conn.execute(
        text(
            """
            INSERT INTO lottery_features(period, feature_type, schema_version, feature_value, meta)
            VALUES (:period, :feature_type, 1, :feature_value, :meta)
            ON DUPLICATE KEY UPDATE
                feature_value=VALUES(feature_value),
                schema_version=VALUES(schema_version),
                meta=VALUES(meta),
                updated_at=NOW()
            """
        ),
        {
            "period": period,
            "feature_type": feature_type,
            "feature_value": json.dumps(payload),
            "meta": json.dumps(meta),
        },
    )


def _run_statistical_analysis(conn, payload: dict[str, Any]) -> int:
    """生成频率/随机性/Markov 报告。"""

    window = int(payload.get("window", 120))
    report = build_statistical_report(conn, window)
    meta = {"window": window, "source": "jobs_worker"}
    period = report.get("period") or payload.get("period")
    if not period:
        raise ValueError("statistical analysis requires period")
    _upsert_feature(conn, period, "frequency_analysis", report["frequency"], meta)
    _upsert_feature(conn, period, "randomness_check", report["randomness"], meta)
    _upsert_feature(conn, period, "markov_transition", report["markov"], meta)
    summary = (
        f"{period} freq_window={report['window']} chi={report['randomness'].get('chi_square', 0):.2f} "
        f"runs={report['randomness'].get('runs', 0)}"
    )
    result = conn.execute(
        text(
            """
            INSERT INTO analysis_results(analysis_type, schema_version, result_summary, result_data, metadata)
            VALUES ('statistical_analysis', 1, :summary, :result_data, :metadata)
            """
        ),
        {
            "summary": summary[:255],
            "result_data": json.dumps(report),
            "metadata": json.dumps({**meta, "sequence": report.get("sequence")}),
        },
    )
    return result.lastrowid


def _run_strategy_backtest(conn, payload: dict[str, Any]) -> int:
    """执行趋势策略回测并写入结果。"""

    window = int(payload.get("window", 360))
    short_window = int(payload.get("short_window", 12))
    long_window = int(payload.get("long_window", 60))
    stake = float(payload.get("stake", 1.0))
    payout_multiplier = float(payload.get("payout_multiplier", 0.92))
    result_payload = run_momentum_backtest(
        conn,
        window=window,
        short_window=short_window,
        long_window=long_window,
        stake=stake,
        payout_multiplier=payout_multiplier,
    )
    period = result_payload["period"]
    _upsert_feature(
        conn,
        period,
        "strategy_backtest",
        {
            "pnl": result_payload["pnl"],
            "win_rate": result_payload["win_rate"],
            "avg_return": result_payload["avg_return"],
            "trades": result_payload["trades"],
            "latest_signal": result_payload["equity_curve"][-1]["signal"] if result_payload["equity_curve"] else None,
        },
        {
            "window": window,
            "short_window": short_window,
            "long_window": long_window,
            "stake": stake,
        },
    )
    summary = (
        f"{period} backtest trades={result_payload['trades']} pnl={result_payload['pnl']:.2f} "
        f"win_rate={result_payload['win_rate']:.2%}"
    )
    result = conn.execute(
        text(
            """
            INSERT INTO analysis_results(analysis_type, schema_version, result_summary, result_data, metadata)
            VALUES ('strategy_backtest', 1, :summary, :result_data, :metadata)
            """
        ),
        {
            "summary": summary[:255],
            "result_data": json.dumps(result_payload),
            "metadata": json.dumps(
                {
                    "window": window,
                    "short_window": short_window,
                    "long_window": long_window,
                    "stake": stake,
                    "payout_multiplier": payout_multiplier,
                }
            ),
        },
    )
    return result.lastrowid


JOB_HANDLERS: dict[str, JobHandler] = {
    "feature_extract": _extract_basic_features,
    "trend_summary": _generate_trend_summary,
    "statistical_analysis": _run_statistical_analysis,
    "strategy_backtest": _run_strategy_backtest,
}


def handle_job(job: dict[str, Any]) -> bool:
    """消费单条任务并返回是否成功。"""

    payload = _parse_payload(job["payload"])
    job_type = job["job_type"]
    job_id = job["id"]

    handler = JOB_HANDLERS.get(job_type)
    if not handler:
        logger.error("unsupported job_type %s (id=%s)", job_type, job_id)
        return False

    with session_scope() as conn:
        update_job_status(conn, job_id, "processing")
        try:
            result_id = handler(conn, payload)
            update_job_status(conn, job_id, "finished", result_id=result_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.exception("job %s failed: %s", job_id, exc)
            update_job_status(conn, job_id, "failed")
            return False


def _process_job_async(job: dict[str, Any]) -> tuple[bool, float]:
    """执行单个 job 并返回耗时。"""

    start = time.perf_counter()
    try:
        result = handle_job(job)
    except Exception:  # noqa: BLE001
        logger.exception("job %s crashed", job["id"])
        result = False
    duration = time.perf_counter() - start
    return result, duration


def run_worker(
    poll_interval: float = 2.0,
    batch_size: int = 10,
    once: bool = True,
    max_workers: int = 4,
) -> None:
    """轮询执行待处理任务，支持线程池批处理。"""

    while True:
        jobs = fetch_pending_jobs(limit=batch_size)
        if not jobs:
            if once:
                return
            time.sleep(poll_interval)
            continue

        success = 0
        failure = 0
        durations: list[float] = []
        batch_start = time.perf_counter()

        if max_workers <= 1 or len(jobs) == 1:
            for job in jobs:
                result, duration = _process_job_async(job)
                durations.append(duration)
                if result:
                    success += 1
                else:
                    failure += 1
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_process_job_async, job): job for job in jobs}
                for future in as_completed(futures):
                    job = futures[future]
                    try:
                        result, duration = future.result()
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("job %s future failed: %s", job["id"], exc)
                        failure += 1
                        durations.append(0.0)
                        continue
                    durations.append(duration)
                    if result:
                        success += 1
                    else:
                        failure += 1

        batch_latency = time.perf_counter() - batch_start
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        if success or failure:
            with session_scope() as conn:
                record_pipeline_stat(
                    conn,
                    component="jobs_worker",
                    metric="batch_processed",
                    value=float(success),
                    detail={
                        "success": success,
                        "failure": failure,
                        "batch_size": len(jobs),
                        "avg_duration": avg_duration,
                        "max_duration": max(durations) if durations else 0.0,
                        "batch_latency": batch_latency,
                        "parallelism": max_workers,
                    },
                )

        if once:
            return
        time.sleep(poll_interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker(once=False)
