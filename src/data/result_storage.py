"""推荐数据源与结果记录工具。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

from src.data.models import ComparisonResult, LotteryResult
from src.exception.custom_exceptions import DataProcessException


class RecommendationRepository:
    """负责加载推荐号码原始文本。"""

    def __init__(self, source_file: str, encoding: str = "utf-8") -> None:
        """保存推荐号码文件路径与读取参数。"""

        self.file_path = Path(source_file)
        self.encoding = encoding

    def load_raw(self, limit: int | None = None) -> List[str]:
        """返回推荐号码文本列表，自动跳过空行与注释。"""

        if not self.file_path.exists():
            raise DataProcessException(f"推荐号码文件不存在: {self.file_path}")

        lines: List[str] = []
        with self.file_path.open("r", encoding=self.encoding) as handle:
            for raw_line in handle:
                stripped = raw_line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                lines.append(stripped)
                if limit and len(lines) >= limit:
                    break

        if not lines:
            raise DataProcessException(f"推荐号码文件 {self.file_path} 为空，无法执行对比。")

        return lines


class ComparisonRecorder:
    """负责将推荐与开奖对比结果写入文件。"""

    def __init__(self, result_directory: str, history_filename: str = "comparison_history.jsonl") -> None:
        """初始化结果目录与日志文件。"""

        self.result_dir = Path(result_directory)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.result_dir / history_filename
        self.snapshot_file = self.result_dir / "latest_comparison.json"

    def append_batch(self, lottery_result: LotteryResult, comparisons: Sequence[ComparisonResult]) -> None:
        """写入一次开奖期号的全部对比数据。"""

        if not comparisons:
            raise DataProcessException("没有可写入的对比结果。")

        payload = self._build_payload(lottery_result, comparisons)
        with self.history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.snapshot_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _build_payload(lottery_result: LotteryResult, comparisons: Sequence[ComparisonResult]) -> dict:
        """组装落盘所需的 JSON 数据结构。"""

        timestamp = datetime.now(timezone.utc).isoformat()
        hit_indexes = [idx for idx, item in enumerate(comparisons, start=1) if item.is_hit]
        return {
            "timestamp": timestamp,
            "period": lottery_result.period,
            "open_time": lottery_result.open_time,
            "lottery_numbers": lottery_result.numbers,
            "total": len(comparisons),
            "hit_count": len(hit_indexes),
            "hit_indexes": hit_indexes,
            "comparisons": [
                {
                    "order": idx,
                    "recommended": item.recommended,
                    "hits": item.hits,
                    "is_hit": item.is_hit,
                }
                for idx, item in enumerate(comparisons, start=1)
            ],
        }
