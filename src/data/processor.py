"""推荐号码数据处理模块。"""
from __future__ import annotations

from typing import Iterable, List

from src.data.models import ComparisonResult
from src.exception.custom_exceptions import DataProcessException


class RecommendationProcessor:
    """提供推荐号清洗与排序能力。"""

    @staticmethod
    def parse_recommendation(text: str) -> List[int]:
        """将推荐号码字符串转换为有序数组。"""
        if not text:
            raise DataProcessException("推荐号码不能为空")
        cleaned = text.replace(",", " ").replace("|", " ")
        tokens = [token for token in cleaned.split() if token]
        numbers: List[int] = []
        for token in tokens:
            try:
                value = int(token)
            except ValueError as exc:
                raise DataProcessException(f"推荐号码包含非法字符: {token}") from exc
            RecommendationProcessor._validate_digit(value)
            numbers.append(value)
        if len(numbers) != 5:
            raise DataProcessException(f"推荐号码数量应为 5 个，当前为 {len(numbers)}: {text}")
        return sorted(numbers)

    @staticmethod
    def process_batch(raw_list: Iterable[str]) -> List[List[int]]:
        """批量处理推荐号码集合。"""
        return [RecommendationProcessor.parse_recommendation(item) for item in raw_list]

    @staticmethod
    def build_comparison_result(recommended: List[int], lottery: List[int]) -> ComparisonResult:
        """根据推荐号与开奖号码生成比对结果（仅比较开奖号码首位）。"""
        if not lottery:
            raise DataProcessException("开奖号码为空，无法对比")

        first_digit = lottery[0]
        hits = [first_digit] if first_digit in recommended else []
        return ComparisonResult(recommended=recommended, lottery=lottery, hits=hits)

    @staticmethod
    def _validate_digit(value: int) -> None:
        """确保数字在 0-9 范围内。"""
        if value < 0 or value > 9:
            raise DataProcessException(f"号码 {value} 不在 0-9 范围内")
