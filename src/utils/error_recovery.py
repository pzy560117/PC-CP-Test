"""错误恢复管理器，实现错误分类、重试和自动恢复功能。"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from src.exception.custom_exceptions import (
    APICallException,
    AutomationException,
    ConfigException,
    DataProcessException,
    InterfaceNotFoundException,
)


class ErrorSeverity(Enum):
    """错误严重程度枚举。"""
    LOW = "low"          # 低：可忽略的错误
    MEDIUM = "medium"    # 中：可重试的错误
    HIGH = "high"        # 高：需要人工干预的错误
    CRITICAL = "critical"  # 严重：必须立即停止的错误


class RecoveryStrategy(Enum):
    """恢复策略枚举。"""
    IGNORE = "ignore"          # 忽略错误继续执行
    RETRY = "retry"            # 重试操作
    SKIP = "skip"              # 跳过当前步骤
    RESTART = "restart"        # 重启流程
    STOP = "stop"              # 停止执行


@dataclass
class ErrorRecord:
    """错误记录。"""
    error_type: str              # 错误类型
    error_message: str           # 错误消息
    severity: ErrorSeverity      # 严重程度
    timestamp: float             # 发生时间
    stack_trace: Optional[str]   # 堆栈信息
    context: dict[str, Any]      # 上下文信息
    recovery_attempted: bool = False  # 是否尝试恢复
    recovery_successful: bool = False  # 恢复是否成功


T = TypeVar('T')


class ErrorRecoveryManager:
    """错误恢复管理器，提供错误分类、重试和自动恢复功能。"""
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        exponential_backoff: bool = True,
        enable_auto_recovery: bool = True,
    ) -> None:
        """初始化错误恢复管理器。
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            exponential_backoff: 是否使用指数退避
            enable_auto_recovery: 是否启用自动恢复
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._exponential_backoff = exponential_backoff
        self._enable_auto_recovery = enable_auto_recovery
        
        # 错误记录
        self._error_history: list[ErrorRecord] = []
        self._error_count_by_type: dict[str, int] = {}
        
        # 错误分类映射
        self._error_severity_map: dict[type, ErrorSeverity] = {
            ConfigException: ErrorSeverity.CRITICAL,
            InterfaceNotFoundException: ErrorSeverity.MEDIUM,
            APICallException: ErrorSeverity.MEDIUM,
            DataProcessException: ErrorSeverity.MEDIUM,
            AutomationException: ErrorSeverity.HIGH,
            ConnectionError: ErrorSeverity.MEDIUM,
            TimeoutError: ErrorSeverity.MEDIUM,
            ValueError: ErrorSeverity.LOW,
            KeyError: ErrorSeverity.LOW,
        }
        
        # 恢复策略映射
        self._recovery_strategy_map: dict[ErrorSeverity, RecoveryStrategy] = {
            ErrorSeverity.LOW: RecoveryStrategy.IGNORE,
            ErrorSeverity.MEDIUM: RecoveryStrategy.RETRY,
            ErrorSeverity.HIGH: RecoveryStrategy.RESTART,
            ErrorSeverity.CRITICAL: RecoveryStrategy.STOP,
        }
    
    def classify_error(self, error: Exception) -> ErrorSeverity:
        """根据错误类型分类错误严重程度。
        
        Args:
            error: 异常对象
            
        Returns:
            错误严重程度
        """
        # 按异常类型查找严重程度
        for error_type, severity in self._error_severity_map.items():
            if isinstance(error, error_type):
                return severity
        
        # 默认为高严重程度
        return ErrorSeverity.HIGH
    
    def get_recovery_strategy(self, severity: ErrorSeverity) -> RecoveryStrategy:
        """根据错误严重程度获取恢复策略。
        
        Args:
            severity: 错误严重程度
            
        Returns:
            恢复策略
        """
        return self._recovery_strategy_map.get(severity, RecoveryStrategy.STOP)
    
    def record_error(
        self,
        error: Exception,
        context: Optional[dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
    ) -> ErrorRecord:
        """记录错误信息。
        
        Args:
            error: 异常对象
            context: 上下文信息
            stack_trace: 堆栈跟踪
            
        Returns:
            错误记录
        """
        error_type = type(error).__name__
        severity = self.classify_error(error)
        
        record = ErrorRecord(
            error_type=error_type,
            error_message=str(error),
            severity=severity,
            timestamp=time.time(),
            stack_trace=stack_trace,
            context=context or {},
        )
        
        # 保存记录
        self._error_history.append(record)
        self._error_count_by_type[error_type] = self._error_count_by_type.get(error_type, 0) + 1
        
        # 记录日志
        self.logger.error(
            "记录错误 [%s|%s]: %s",
            error_type,
            severity.value,
            record.error_message
        )
        
        return record
    
    def execute_with_retry(
        self,
        func: Callable[[], T],
        operation_name: str = "操作",
        context: Optional[dict[str, Any]] = None,
    ) -> T:
        """执行函数并在失败时自动重试。
        
        Args:
            func: 要执行的函数
            operation_name: 操作名称（用于日志）
            context: 上下文信息
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次执行的异常
        """
        last_error: Optional[Exception] = None
        
        for attempt in range(self._max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.info(
                        "%s 第 %s/%s 次重试，等待 %.1f 秒...",
                        operation_name,
                        attempt,
                        self._max_retries,
                        delay
                    )
                    time.sleep(delay)
                
                result = func()
                
                if attempt > 0:
                    self.logger.info("%s 重试成功", operation_name)
                
                return result
                
            except Exception as exc:
                last_error = exc
                severity = self.classify_error(exc)
                
                # 记录错误
                record = self.record_error(exc, context)
                
                # 如果是严重错误，不重试直接抛出
                if severity == ErrorSeverity.CRITICAL:
                    self.logger.error("%s 遇到严重错误，停止重试", operation_name)
                    raise
                
                # 如果已达最大重试次数
                if attempt >= self._max_retries:
                    self.logger.error(
                        "%s 失败，已达最大重试次数 %s",
                        operation_name,
                        self._max_retries
                    )
                    break
                
                self.logger.warning(
                    "%s 失败 [%s|%s]: %s",
                    operation_name,
                    type(exc).__name__,
                    severity.value,
                    exc
                )
        
        # 所有重试都失败，抛出最后一次错误
        if last_error:
            raise last_error
        
        raise RuntimeError(f"{operation_name} 执行失败且无错误记录")
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟时间。
        
        Args:
            attempt: 当前重试次数
            
        Returns:
            延迟秒数
        """
        if self._exponential_backoff:
            # 指数退避：delay * 2^(attempt-1)
            return self._retry_delay * (2 ** (attempt - 1))
        else:
            # 固定延迟
            return self._retry_delay
    
    def attempt_recovery(
        self,
        error: Exception,
        recovery_func: Optional[Callable[[], None]] = None,
    ) -> bool:
        """尝试从错误中恢复。
        
        Args:
            error: 异常对象
            recovery_func: 恢复函数（可选）
            
        Returns:
            是否恢复成功
        """
        if not self._enable_auto_recovery:
            self.logger.info("自动恢复未启用")
            return False
        
        severity = self.classify_error(error)
        strategy = self.get_recovery_strategy(severity)
        
        self.logger.info(
            "尝试恢复错误 [%s|%s]，策略=%s",
            type(error).__name__,
            severity.value,
            strategy.value
        )
        
        try:
            if strategy == RecoveryStrategy.IGNORE:
                self.logger.info("忽略错误，继续执行")
                return True
            
            elif strategy == RecoveryStrategy.RETRY:
                if recovery_func:
                    recovery_func()
                    self.logger.info("恢复成功")
                    return True
                else:
                    self.logger.warning("未提供恢复函数，无法重试")
                    return False
            
            elif strategy == RecoveryStrategy.SKIP:
                self.logger.info("跳过当前步骤")
                return True
            
            elif strategy == RecoveryStrategy.RESTART:
                self.logger.warning("需要重启流程")
                return False
            
            elif strategy == RecoveryStrategy.STOP:
                self.logger.error("严重错误，必须停止")
                return False
            
        except Exception as exc:
            self.logger.exception("恢复过程中发生错误: %s", exc)
            return False
        
        return False
    
    def get_error_statistics(self) -> dict[str, Any]:
        """获取错误统计信息。
        
        Returns:
            统计信息字典
        """
        total_errors = len(self._error_history)
        
        if total_errors == 0:
            return {
                "total_errors": 0,
                "error_rate": 0.0,
                "most_common_error": None,
            }
        
        # 按严重程度统计
        severity_counts = {severity: 0 for severity in ErrorSeverity}
        for record in self._error_history:
            severity_counts[record.severity] += 1
        
        # 找出最常见的错误类型
        most_common_error = max(
            self._error_count_by_type.items(),
            key=lambda x: x[1]
        )[0] if self._error_count_by_type else None
        
        return {
            "total_errors": total_errors,
            "error_by_type": dict(self._error_count_by_type),
            "error_by_severity": {s.value: c for s, c in severity_counts.items()},
            "most_common_error": most_common_error,
        }
    
    def clear_history(self) -> None:
        """清空错误历史记录。"""
        self._error_history.clear()
        self._error_count_by_type.clear()
        self.logger.info("错误历史记录已清空")
    
    def get_recent_errors(self, count: int = 10) -> list[ErrorRecord]:
        """获取最近的错误记录。
        
        Args:
            count: 要获取的记录数量
            
        Returns:
            错误记录列表
        """
        return self._error_history[-count:] if self._error_history else []
