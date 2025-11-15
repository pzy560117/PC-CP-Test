"""调度与告警模块：周期执行 collector/validator/worker 并监控失败情况。"""
from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

from .collector import run_collection
from .config import SchedulerConfig, load_scheduler_config
from .database import (
    fetch_recent_stats,
    record_pipeline_alert,
    record_pipeline_stat,
    session_scope,
)
from .jobs_worker import run_worker
from .validator import run_validation

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    """封装单个需要周期执行的任务。"""

    name: str
    component: str
    interval_seconds: int
    runner: Callable[[], None]
    next_run_ts: float = field(default=0.0)


def run_scheduler(
    iterations: int | None = 1,
    simulate_failure: Sequence[str] | None = None,
) -> None:
    """执行调度循环，可指定迭代次数或持续运行。"""

    cfg = load_scheduler_config()
    jobs = _build_jobs(cfg)
    failure_set = set(simulate_failure or [])
    alert_tracker: dict[str, float] = {}
    loop_count = 0

    while True:
        loop_count += 1
        now = time.time()
        executed_this_loop = False

        for job in jobs:
            if now >= job.next_run_ts:
                executed_this_loop = True
                _execute_job(job, failure_set)
                job.next_run_ts = now + job.interval_seconds
                _evaluate_alerts(job.component, cfg, alert_tracker)

        if iterations is not None and loop_count >= iterations:
            break

        if not executed_this_loop:
            time.sleep(cfg.loop_sleep)


def _build_jobs(cfg: SchedulerConfig) -> list[ScheduledJob]:
    """构建默认调度任务列表。"""

    return [
        ScheduledJob("collector", "collector", cfg.collector_interval, run_collection),
        ScheduledJob("validator", "validator", cfg.validator_interval, run_validation),
        ScheduledJob(
            "jobs_worker",
            "jobs_worker",
            cfg.worker_interval,
            lambda: run_worker(once=True),
        ),
    ]


def _execute_job(job: ScheduledJob, simulate_failure: set[str]) -> None:
    """执行单个任务并记录 pipeline_stats。"""

    logger.info("scheduler: running job %s", job.name)
    start = time.perf_counter()
    try:
        if job.name in simulate_failure:
            raise RuntimeError("simulated failure")
        job.runner()
        duration = time.perf_counter() - start
        with session_scope() as conn:
            record_pipeline_stat(
                conn,
                component=job.component,
                metric="job_success",
                value=duration,
                detail={"job": job.name, "duration_seconds": duration},
            )
        logger.info("scheduler: job %s success (%.2fs)", job.name, duration)
    except Exception as exc:  # noqa: BLE001
        logger.exception("scheduler: job %s failed", job.name)
        with session_scope() as conn:
            record_pipeline_stat(
                conn,
                component=job.component,
                metric="job_failed",
                value=0.0,
                detail={"job": job.name, "error": str(exc)},
            )
            record_pipeline_alert(
                conn,
                component=job.component,
                level="error",
                message=f"{job.name} execution failed",
                detail={"job": job.name, "error": str(exc)},
            )


def _evaluate_alerts(component: str, cfg: SchedulerConfig, tracker: dict[str, float]) -> None:
    """基于 pipeline_stats 最近记录判断是否需要触发持续性告警。"""

    stats = fetch_recent_stats(component, limit=cfg.alert_window)
    failure_count = sum(1 for row in stats if row["metric"] == "job_failed")
    if failure_count >= cfg.alert_threshold:
        now = time.time()
        last_alert_ts = tracker.get(component, 0.0)
        if now - last_alert_ts >= cfg.alert_cooldown:
            logger.warning(
                "scheduler: component=%s has %s failures within last %s records",
                component,
                failure_count,
                cfg.alert_window,
            )
            with session_scope() as conn:
                record_pipeline_alert(
                    conn,
                    component=component,
                    level="critical",
                    message="repeated job failures",
                    detail={
                        "failure_count": failure_count,
                        "window": cfg.alert_window,
                        "metrics": [row["detail"] for row in stats],
                    },
                )
            tracker[component] = now


def _parse_args(args: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scheduler for collector/validator/worker.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="循环次数；为 None 表示持续运行",
    )
    parser.add_argument(
        "--run-forever",
        action="store_true",
        help="持续运行直到被终止",
    )
    parser.add_argument(
        "--simulate-failure",
        action="append",
        default=[],
        help="模拟某个 job 失败（collector/validator/jobs_worker），可指定多次",
    )
    return parser.parse_args(args=args)


def main() -> None:
    """CLI 入口。"""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    iterations = None if args.run_forever else args.iterations
    run_scheduler(iterations=iterations, simulate_failure=args.simulate_failure)


if __name__ == "__main__":
    main()
