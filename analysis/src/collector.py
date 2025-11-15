"""腾讯分分彩数据采集脚本。"""
from __future__ import annotations

import logging
import time
import re
from datetime import datetime
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup
from requests import Response

from .config import CollectorConfig, CollectorSourceConfig, load_config
from .database import insert_raw_draw, record_collector_log, record_pipeline_stat, session_scope

logger = logging.getLogger(__name__)


def run_collection() -> None:
    """入口：拉取各采集源开奖并写入 raw_lottery_draws。"""

    config = load_config()
    summary: list[dict[str, Any]] = []
    total_inserted = 0

    for source_cfg in config.sources:
        inserted = _collect_from_source(config, source_cfg)
        summary.append({"source": source_cfg.name, "inserted": inserted})
        total_inserted += inserted

    if config.monitoring_enabled and summary:
        with session_scope() as conn:
            record_pipeline_stat(
                conn,
                component="collector",
                metric="payloads_inserted",
                value=float(total_inserted),
                detail={"summary": summary},
            )


def _collect_from_source(config: CollectorConfig, source_cfg: CollectorSourceConfig) -> int:
    """执行单个采集源逻辑，包含异常监控。"""

    try:
        payloads = list(_fetch_source_payloads(config, source_cfg))
    except Exception as exc:  # noqa: BLE001
        logger.exception("source %s failed", source_cfg.name)
        _log_collector(source_cfg.name, "error", f"collect failed: {exc}")
        return 0

    if not payloads:
        _log_collector(source_cfg.name, "warning", "no payloads returned")
        return 0

    inserted = 0
    with session_scope() as conn:
        for item in payloads[: config.batch_size]:
            insert_raw_draw(conn, payload=item, source=source_cfg.name)
            inserted += 1
        record_collector_log(
            conn,
            source=source_cfg.name,
            level="info",
            message=f"inserted {inserted} payloads",
            detail={"batch_size": config.batch_size},
        )
    return inserted


def _fetch_source_payloads(config: CollectorConfig, source_cfg: CollectorSourceConfig) -> Iterable[dict[str, Any]]:
    if source_cfg.parser == "history_html":
        yield from _fetch_history_html(config, source_cfg.endpoint)
    elif source_cfg.parser == "latest_json":
        yield from _fetch_latest_payloads(config, source_cfg.endpoint)
    else:
        raise ValueError(f"unsupported parser {source_cfg.parser}")


def _fetch_history_html(config: CollectorConfig, endpoint: str) -> Iterable[dict[str, Any]]:
    resp = _request(endpoint, config)
    soup = BeautifulSoup(resp.text, "html.parser")
    dates: list[str] = []
    for anchor in soup.select("a[href*='/hallhistoryDetail/txffcqiqu/']"):
        text_val = anchor.get_text(strip=True)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text_val) and text_val not in dates:
            dates.append(text_val)
    for date_str in dates:
        detail_url = f"https://kjapi.com/hallhistoryDetail/txffcqiqu/{date_str}"
        detail_resp = _request(detail_url, config)
        if config.throttle_seconds > 0:
            time.sleep(config.throttle_seconds)
        soup_detail = BeautifulSoup(detail_resp.text, "html.parser")
        for row in soup_detail.select("tbody#datalist tr"):
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            period = cols[0].get_text(strip=True)
            draw_time = cols[1].get_text(strip=True)
            numbers = [
                li.get_text(strip=True)
                for li in row.select("td ul li i")
                if li.get_text(strip=True)
            ]
            payload = _normalize_payload(period, draw_time, numbers)
            if payload:
                yield payload


def _fetch_latest_payloads(config: CollectorConfig, endpoint: str) -> Iterable[dict[str, Any]]:
    resp = _request(endpoint, config)
    data: Any
    try:
        data = resp.json()
    except ValueError:
        logger.warning("latest endpoint returned non-json, fallback to html parser")
        yield from _fetch_history_html(config, endpoint)
        return
    records = data.get("data") if isinstance(data, dict) else data
    if not isinstance(records, list):
        return
    for item in records:
        period = str(item.get("period") or item.get("issue") or "")
        draw_time = item.get("openTime") or item.get("draw_time")
        open_code = item.get("openCode") or item.get("open_code")
        numbers: list[str]
        if isinstance(open_code, str):
            numbers = [num.strip() for num in open_code.split(",") if num.strip()]
        elif isinstance(open_code, list):
            numbers = [str(num) for num in open_code]
        else:
            numbers = []
        payload = _normalize_payload(period, draw_time, numbers, timestamp=item.get("timestamp"))
        if payload:
            yield payload


def _normalize_payload(period: str, draw_time: str | None, numbers: list[str], timestamp: int | None = None) -> dict[str, Any] | None:
    if not period or not draw_time or not numbers:
        return None
    try:
        parsed_ts = int(timestamp or datetime.strptime(draw_time, "%Y-%m-%d %H:%M:%S").timestamp())
    except ValueError:
        return None
    return {
        "period": period,
        "openTime": draw_time,
        "openCode": ",".join(numbers),
        "timestamp": parsed_ts,
    }


def _request(url: str, config: CollectorConfig) -> Response:
    """封装 HTTP 请求，添加必要 headers 与重试。"""

    headers = {"User-Agent": config.api.user_agent, "Referer": "https://kjapi.com"}
    backoff = max(config.retry_backoff, 0)
    last_status: int | None = None
    last_exception: Exception | None = None
    for attempt in range(1, config.retry + 1):
        try:
            resp = requests.get(url, timeout=config.api.timeout, headers=headers)
        except requests.RequestException as exc:
            last_exception = exc
            logger.warning("request %s exception (%s/%s): %s", url, attempt, config.retry, exc)
        else:
            last_status = resp.status_code
            if resp.status_code == 200:
                return resp
            logger.warning(
                "request %s failed status=%s (attempt %s/%s)", url, resp.status_code, attempt, config.retry
            )
        if backoff > 0:
            sleep_time = backoff * attempt
            time.sleep(sleep_time)
    if last_exception:
        raise last_exception
    raise RuntimeError(f"request {url} failed after {config.retry} attempts, last_status={last_status}")


def _log_collector(source: str, level: str, message: str) -> None:
    detail = {"level": level}
    with session_scope() as conn:
        record_collector_log(conn, source=source, level=level, message=message, detail=detail)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_collection()
