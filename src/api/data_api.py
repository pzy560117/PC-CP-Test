"""开奖数据 API 客户端。"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests
from bs4 import BeautifulSoup

from src.data.models import LotteryResult
from src.exception.custom_exceptions import APICallException, DataProcessException


class LotteryApiClient:
    """封装开奖数据请求与解析逻辑。"""

    def __init__(self, api_config: Dict[str, Any], session: Optional[requests.Session] = None) -> None:
        """读取配置，准备请求会话。"""
        self._config = api_config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = session or requests.Session()
        self.base_url = (self._config.get("base_url") or "").rstrip("/")
        self.endpoints = dict(self._config.get("endpoints", {}))
        self.timeout = int(self._config.get("timeout", 10))
        self.headers = dict(self._config.get("headers", {}))
        self.rate_limit = dict(self._config.get("rate_limit", {}))
        self.links_file = self._config.get("links_file")
        self._hydrate_endpoints_from_links()

    def fetch_latest_result(self) -> LotteryResult:
        """获取最新一期开奖号码。

        优先尝试JSON接口，失败时回退到HTML页面解析。
        """
        try:
            payload = self._request_endpoint("history_data")
            try:
                data = payload["data"]
                latest = data[0]
            except (KeyError, IndexError, TypeError) as exc:
                raise DataProcessException("历史开奖数据返回为空或结构异常") from exc
            return LotteryResult.from_api_payload(latest)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.warning("JSON接口获取开奖失败，改用HTML解析: %s", exc)
            return self._fetch_latest_result_from_html()

    def fetch_history_by_date(self, date_str: str) -> Iterable[LotteryResult]:
        """按日期获取全部开奖数据。"""
        payload = self._request_endpoint("date_data", path_params={"date": date_str})
        try:
            data = payload["data"]
        except KeyError as exc:
            raise DataProcessException("指定日期数据结构异常") from exc
        return [LotteryResult.from_api_payload(item) for item in data]

    def _request_endpoint(self, endpoint_key: str, path_params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """发送 HTTP 请求并返回 JSON。"""
        url = self._build_url(endpoint_key, path_params)
        delay = float(self.rate_limit.get("delay_seconds", 0) or 0)
        if delay > 0:
            time.sleep(delay)

        response = self.session.get(url, headers=self.headers, timeout=self.timeout)
        if response.status_code != 200:
            raise APICallException(f"请求 {url} 失败，状态码 {response.status_code}")
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise DataProcessException("API 响应非 JSON 格式") from exc

    def _build_url(self, endpoint_key: str, path_params: Optional[Dict[str, str]] = None) -> str:
        """拼装请求 URL。"""
        path = self.endpoints.get(endpoint_key)
        if not path:
            raise APICallException(f"未配置 endpoint: {endpoint_key}")
        if path_params:
            path = path.format(**path_params)
        return f"{self.base_url.rstrip('/')}{path}"

    def _hydrate_endpoints_from_links(self) -> None:
        """从本地链接文件补全端点信息。"""
        if not self.links_file:
            return
        link_path = Path(self.links_file)
        if not link_path.exists():
            self.logger.warning("链接文件不存在：%s", self.links_file)
            return
        content = link_path.read_text(encoding="utf-8")
        urls = re.findall(r"https?://\S+", content)
        if not urls:
            return
        if "history_data" not in self.endpoints:
            self.endpoints["history_data"] = urls[0].replace(self.base_url, "") if self.base_url else urls[0]
        if len(urls) > 1 and "date_data" not in self.endpoints:
            self.endpoints["date_data"] = urls[1].replace(self.base_url, "") if self.base_url else urls[1]

    def _fetch_latest_result_from_html(self) -> LotteryResult:
        """从HTML详情页解析最新开奖号码。"""
        date = datetime.now()
        max_lookback = int(self._config.get("html_lookback_days", 3))
        for _ in range(max_lookback):
            date_str = date.strftime("%Y-%m-%d")
            try:
                result = self._parse_detail_page(date_str)
                if result:
                    return result
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.debug("解析 %s 详情页失败: %s", date_str, exc)
            date -= timedelta(days=1)
        raise DataProcessException("HTML 页面解析开奖数据失败")

    def _parse_detail_page(self, date_str: str) -> Optional[LotteryResult]:
        """解析指定日期的详情页面。"""
        if "date_data" not in self.endpoints:
            raise APICallException("配置缺少 date_data 详情页地址")
        url = self._build_url("date_data", {"date": date_str})
        response = self.session.get(url, headers=self.headers, timeout=self.timeout)
        if response.status_code != 200:
            raise APICallException(f"请求 {url} 失败，状态码 {response.status_code}")
        soup = BeautifulSoup(response.text, "html.parser")
        table_body = soup.find("tbody", id="datalist")
        if not table_body:
            raise DataProcessException("详情页缺少开奖表格")
        first_row = table_body.find("tr")
        if not first_row:
            return None
        cells = first_row.find_all("td")
        if len(cells) < 3:
            raise DataProcessException("开奖表格结构异常")
        period = cells[0].get_text(strip=True)
        open_time = cells[1].get_text(strip=True)
        numbers = self._extract_numbers_from_cell(cells[2])
        if not numbers:
            raise DataProcessException("开奖号码解析失败")
        return LotteryResult(period=period, numbers=numbers, open_time=open_time)

    @staticmethod
    def _extract_numbers_from_cell(cell_node: Any) -> list[int]:
        """从HTML单元格中提取开奖号码。"""
        numbers: list[int] = []
        for tag in cell_node.find_all("i"):
            text = tag.get_text(strip=True)
            if text.isdigit():
                numbers.append(int(text))
        if not numbers:
            # 后备：直接解析文字内容
            raw_text = cell_node.get_text(" ", strip=True)
            tokens = [token for token in raw_text.split() if token.isdigit()]
            numbers = [int(token) for token in tokens]
        return numbers
