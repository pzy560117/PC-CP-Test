"""MySQL 持久化工具，用于写入推荐与开奖对比结果。"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional

import pymysql

from src.data.models import ComparisonResult, LotteryResult


class MySQLWriter:
    """负责将比对结果写入 MySQL。"""

    def __init__(self, config: Optional[dict] = None) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._config = config or {}
        self.is_enabled = bool(self._config.get("enabled", False))
        self._connection: Optional[pymysql.connections.Connection] = None
        self._table = self._config.get("table", "comparison_results")

        if self.is_enabled:
            self.logger.info("MySQL 写入已启用，目标表：%s", self._table)
        else:
            self.logger.debug("MySQL 写入未启用")

    def write_comparisons(self, lottery_result: LotteryResult, comparisons: List[ComparisonResult]) -> None:
        """将对比结果批量写入 MySQL。"""

        if not self.is_enabled:
            return

        if not comparisons:
            self.logger.warning("写入 MySQL 时发现空的 comparisons，已跳过")
            return

        connection = self._get_connection()
        if not connection:
            return

        insert_sql = (
            f"INSERT INTO `{self._table}`"
            " (period, order_index, open_time, lottery_numbers, recommended_numbers, hits, is_hit, created_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        )

        payload_rows = []
        for idx, item in enumerate(comparisons, start=1):
            payload_rows.append(
                (
                    lottery_result.period,
                    idx,
                    lottery_result.open_time,
                    json.dumps(lottery_result.numbers, ensure_ascii=False),
                    json.dumps(item.recommended, ensure_ascii=False),
                    json.dumps(item.hits or [], ensure_ascii=False),
                    1 if item.is_hit else 0,
                    datetime.utcnow(),
                )
            )

        try:
            with connection.cursor() as cursor:
                cursor.executemany(insert_sql, payload_rows)
            connection.commit()
            self.logger.info("已将期号 %s 的 %s 条对比结果写入 MySQL", lottery_result.period, len(payload_rows))
        except Exception as exc:  # pylint: disable=broad-except
            connection.rollback()
            self.logger.error("写入 MySQL 失败: %s", exc)

    def close(self) -> None:
        """关闭数据库连接。"""

        if self._connection and self._connection.open:
            try:
                self._connection.close()
            except Exception:  # pylint: disable=broad-except
                pass
            finally:
                self._connection = None

    def _get_connection(self) -> Optional[pymysql.connections.Connection]:
        """获取或建立数据库连接。"""

        if not self.is_enabled:
            return None

        if self._connection and self._connection.open:
            return self._connection

        try:
            self._connection = pymysql.connect(
                host=self._config.get("host", "localhost"),
                port=int(self._config.get("port", 3306)),
                user=self._config.get("user", "root"),
                password=self._config.get("password", ""),
                database=self._config.get("database", "lottery"),
                charset=self._config.get("charset", "utf8mb4"),
                autocommit=False,
            )
            self._ensure_table()
            return self._connection
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error("连接 MySQL 失败: %s", exc)
            self._connection = None
            return None

    def _ensure_table(self) -> None:
        """确保结果表存在。"""

        if not self._connection or not self._connection.open:
            return

        create_sql = f"""
        CREATE TABLE IF NOT EXISTS `{self._table}` (
            `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            `period` VARCHAR(64) NOT NULL,
            `order_index` INT NOT NULL,
            `open_time` VARCHAR(64) DEFAULT NULL,
            `lottery_numbers` JSON NOT NULL,
            `recommended_numbers` JSON NOT NULL,
            `hits` JSON,
            `is_hit` TINYINT(1) NOT NULL DEFAULT 0,
            `created_at` DATETIME NOT NULL,
            PRIMARY KEY (`id`),
            KEY `idx_period` (`period`)
        ) ENGINE=InnoDB DEFAULT CHARSET={self._config.get("charset", "utf8mb4")}
        """

        with self._connection.cursor() as cursor:
            cursor.execute(create_sql)
        self._connection.commit()
