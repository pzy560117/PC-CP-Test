"""腾讯分分彩数据采集脚本。"""
from __future__ import annotations

import logging
import time
import re
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests import Response

from .config import CollectorConfig, load_config
from .database import insert_raw_draw, session_scope

logger = logging.getLogger(__name__)


def fetch_history(config: CollectorConfig) -> list[dict[str, Any]]:
    """解析历史页面，获取多个日期的开奖详情。"""

    resp = _request(config.api.history_endpoint, config)
    soup = BeautifulSoup(resp.text, "html.parser")
    dates: list[str] = []
    for anchor in soup.select("a[href*='/hallhistoryDetail/txffcqiqu/']"):
        text = anchor.get_text(strip=True)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) and text not in dates:
            dates.append(text)
    payloads: list[dict[str, Any]] = []
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
            if not period or not draw_time or not numbers:
                continue
            try:
                timestamp = int(datetime.strptime(draw_time, "%Y-%m-%d %H:%M:%S").timestamp())
            except ValueError:
                continue
            payloads.append(
                {
                    "period": period,
                    "openTime": draw_time,
                    "openCode": ",".join(numbers),
                    "timestamp": timestamp,
                }
            )
            if len(payloads) >= config.batch_size:
                return payloads
    return payloads


def run_collection() -> None:
    """入口：拉取最新开奖并写入 raw_lottery_draws。"""

    config = load_config()
    payloads = fetch_history(config)
    if not payloads:
        logger.warning("history api returned empty result")
        return

    with session_scope() as conn:
        for item in payloads[: config.batch_size]:
            insert_raw_draw(conn, payload=item, source="history_api")

    # 历史页面已覆盖最新数据，latest 接口暂不可靠


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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_collection()
