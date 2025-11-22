"""数据模型定义。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from src.exception.custom_exceptions import ConfigException, DataProcessException


@dataclass(frozen=True)
class SearchParameters:
    """封装搜索参数配置。"""

    formula_count: int
    data_periods: int
    fixed_code_count: int
    plan_cycle: int
    min_accuracy: int
    max_results: int

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SearchParameters":
        """根据配置字典创建实例。"""
        data = payload or {}
        instance = cls(
            formula_count=cls._require_positive(data, "formula_count", 100, "公式数量"),
            data_periods=cls._require_positive(data, "data_periods", 200, "数据期数"),
            fixed_code_count=cls._require_positive(data, "fixed_code_count", 5, "定码个数"),
            plan_cycle=cls._require_positive(data, "plan_cycle", 1, "计划周期"),
            min_accuracy=cls._require_between(data, "min_accuracy", 57, 1, 100, "最低准确率"),
            max_results=cls._require_positive(data, "max_results", 5, "最大结果数"),
        )
        return instance

    def to_dict(self) -> Dict[str, int]:
        """输出原始字典表示。"""
        return {
            "formula_count": self.formula_count,
            "data_periods": self.data_periods,
            "fixed_code_count": self.fixed_code_count,
            "plan_cycle": self.plan_cycle,
            "min_accuracy": self.min_accuracy,
            "max_results": self.max_results,
        }

    @staticmethod
    def _require_positive(data: Dict[str, Any], key: str, default: int, label: str) -> int:
        """读取正整数配置。"""
        value = SearchParameters._normalize_int(data, key, default, label)
        if value <= 0:
            raise ConfigException(f"{label} 必须为正整数，当前值: {value}")
        return value

    @staticmethod
    def _require_between(
        data: Dict[str, Any], key: str, default: int, low: int, high: int, label: str
    ) -> int:
        """读取并校验范围值。"""
        value = SearchParameters._normalize_int(data, key, default, label)
        if not low <= value <= high:
            raise ConfigException(f"{label} 必须在 {low}-{high} 区间，当前值: {value}")
        return value

    @staticmethod
    def _normalize_int(data: Dict[str, Any], key: str, default: int, label: str) -> int:
        """将字段转换为整数。"""
        raw_value = data.get(key, default)
        try:
            return int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ConfigException(f"{label} 配置无效: {raw_value}") from exc


@dataclass(frozen=True)
class LotteryResult:
    """表示单期开奖号码。"""

    period: str
    numbers: List[int]
    open_time: str

    @classmethod
    def from_api_payload(cls, payload: Dict[str, Any]) -> "LotteryResult":
        """从 API 返回的字典构建对象。"""
        try:
            period = str(payload["period"])
            raw_numbers = payload["number"]
            open_time = payload.get("time", "")
        except KeyError as exc:
            raise DataProcessException(f"开奖数据缺少字段: {exc}") from exc

        numbers = cls._parse_numbers(raw_numbers)
        return cls(period=period, numbers=numbers, open_time=open_time)

    @staticmethod
    def _parse_numbers(raw_numbers: Any) -> List[int]:
        """解析开奖号码字符串。"""
        if isinstance(raw_numbers, str):
            tokens = raw_numbers.replace(",", " ").split()
        elif isinstance(raw_numbers, Sequence):
            tokens = list(raw_numbers)
        else:
            raise DataProcessException(f"无法解析开奖号码: {raw_numbers}")

        try:
            numbers = [int(token) for token in tokens]
        except ValueError as exc:
            raise DataProcessException(f"开奖号码包含非数字: {raw_numbers}") from exc

        return numbers


@dataclass(frozen=True)
class ComparisonResult:
    """记录推荐号码与开奖号码的对比结果。"""

    recommended: List[int]
    lottery: List[int]
    hits: List[int]

    @property
    def is_hit(self) -> bool:
        """判断是否命中。"""
        return bool(self.hits)
