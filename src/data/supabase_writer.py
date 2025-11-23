"""Supabase REST 客户端，用于写入推荐号。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

import requests
from requests import HTTPError

from src.data.models import ComparisonResult, LotteryResult


class SupabaseWriter:
    """将推荐号码写入 Supabase 数据表。"""

    def __init__(self, config: Optional[dict] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._config = config or {}
        self.enabled = bool(self._config.get("enabled"))
        self._rest_url = self._normalize_rest_url(self._config.get("rest_url"))
        self._table = self._config.get("table", "recommendations")
        self._result_table = self._config.get("result_table", self._table)
        self._api_key = self._config.get("api_key")
        self._timeout = int(self._config.get("timeout", 10))
        self._conflict_columns = self._config.get("conflict_columns", "period,order_index")

        if self.enabled:
            if not self._rest_url or not self._api_key:
                self.logger.warning("Supabase 配置不完整，已自动禁用写入。")
                self.enabled = False
            else:
                self.logger.info("Supabase 写入已启用，目标表：%s", self._table)
        else:
            self.logger.debug("Supabase 写入未启用")

    def write_recommendations(self, period: str, recommendations: List[List[int]]) -> None:
        """将推荐号码存储到云端。"""

        if not self.enabled:
            return
        if not recommendations:
            self.logger.debug("Supabase 写入跳过：无推荐号码")
            return

        endpoint = self._build_endpoint(self._table)
        headers = self._build_headers()

        payload = [
            {
                "period": period,
                "order_index": idx + 1,
                "recommended_numbers": json.dumps(nums, ensure_ascii=False),
                "status": "pending",
                "created_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            }
            for idx, nums in enumerate(recommendations)
        ]

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=self._timeout)
            response.raise_for_status()
            self.logger.info("已将期号 %s 的 %s 条推荐写入 Supabase", period, len(payload))
        except HTTPError as exc:
            status = exc.response.status_code if getattr(exc, "response", None) else "UNKNOWN"
            details = exc.response.text if getattr(exc, "response", None) else ""
            self.logger.warning("写入 Supabase 失败（HTTP %s）: %s", status, details)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.warning("写入 Supabase 失败: %s", exc)

    def write_comparison_results(
        self,
        lottery_result: LotteryResult,
        comparisons: List[ComparisonResult],
    ) -> None:
        """将推荐对比结果写入 Supabase。"""

        if not self.enabled or not comparisons:
            return

        endpoint = self._build_endpoint(self._result_table)
        headers = self._build_headers()

        payload = [
            {
                "period": lottery_result.period,
                "order_index": idx + 1,
                "recommended_numbers": json.dumps(item.recommended, ensure_ascii=False),
                "lottery_numbers": json.dumps(lottery_result.numbers, ensure_ascii=False),
                "hits": json.dumps(item.hits or [], ensure_ascii=False),
                "is_hit": item.is_hit,
                "open_time": lottery_result.open_time,
                "status": "evaluated",
                "evaluated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            }
            for idx, item in enumerate(comparisons)
        ]

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=self._timeout)
            response.raise_for_status()
            self.logger.info(
                "已将期号 %s 的 %s 条对比结果写入 Supabase",
                lottery_result.period,
                len(payload),
            )
        except HTTPError as exc:
            status = exc.response.status_code if getattr(exc, "response", None) else "UNKNOWN"
            details = exc.response.text if getattr(exc, "response", None) else ""
            self.logger.warning("写入 Supabase 结果失败（HTTP %s）: %s", status, details)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.warning("写入 Supabase 结果失败: %s", exc)

    def _normalize_rest_url(self, base_url: Optional[str]) -> str:
        """规整 Supabase REST 地址，自动补齐 /rest/v1。"""

        if not base_url:
            return ""
        cleaned = base_url.rstrip("/")
        if not cleaned.endswith("/rest/v1"):
            cleaned = f"{cleaned}/rest/v1"
        return cleaned

    def _build_endpoint(self, table: str) -> str:
        """构建支持 on_conflict 的 REST Endpoint。"""

        if self._conflict_columns:
            return f"{self._rest_url}/{table}?on_conflict={self._conflict_columns}"
        return f"{self._rest_url}/{table}"

    def _build_headers(self) -> dict[str, str]:
        """统一构建带 UPSERT Header 的请求头。"""

        prefer_directives = ["resolution=merge-duplicates"]
        # 维持最小返回量，避免冗余响应
        prefer_directives.append("return=minimal")
        prefer_value = ",".join(prefer_directives)
        return {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Prefer": prefer_value,
        }
