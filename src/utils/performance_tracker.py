"""性能追踪器，追踪和分析各操作的性能指标。"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OperationMetrics:
    """操作性能指标。"""
    operation_name: str                    # 操作名称
    execution_count: int = 0               # 执行次数
    total_time: float = 0.0                # 总耗时（秒）
    min_time: float = float('inf')         # 最小耗时（秒）
    max_time: float = 0.0                  # 最大耗时（秒）
    last_time: float = 0.0                 # 最后一次耗时（秒）
    failure_count: int = 0                 # 失败次数
    timestamps: list[float] = field(default_factory=list)  # 执行时间戳
    durations: list[float] = field(default_factory=list)   # 执行耗时列表
    
    @property
    def avg_time(self) -> float:
        """平均耗时。"""
        if self.execution_count == 0:
            return 0.0
        return self.total_time / self.execution_count
    
    @property
    def success_rate(self) -> float:
        """成功率。"""
        if self.execution_count == 0:
            return 0.0
        return ((self.execution_count - self.failure_count) / self.execution_count) * 100
    
    def record_execution(self, duration: float, success: bool = True) -> None:
        """记录一次执行。
        
        Args:
            duration: 耗时（秒）
            success: 是否成功
        """
        self.execution_count += 1
        self.total_time += duration
        self.last_time = duration
        
        if duration < self.min_time:
            self.min_time = duration
        if duration > self.max_time:
            self.max_time = duration
        
        if not success:
            self.failure_count += 1
        
        # 保存时间戳和耗时（最多保留100条）
        self.timestamps.append(time.time())
        self.durations.append(duration)
        
        if len(self.timestamps) > 100:
            self.timestamps = self.timestamps[-100:]
            self.durations = self.durations[-100:]
    
    def get_summary(self) -> str:
        """获取性能摘要。
        
        Returns:
            性能摘要字符串
        """
        return (
            f"{self.operation_name}: "
            f"执行{self.execution_count}次, "
            f"平均{self.avg_time:.3f}s, "
            f"最小{self.min_time:.3f}s, "
            f"最大{self.max_time:.3f}s, "
            f"成功率{self.success_rate:.1f}%"
        )


class PerformanceTracker:
    """性能追踪器，追踪各操作的执行性能并提供统计分析。"""
    
    def __init__(self, enable_detailed_tracking: bool = True) -> None:
        """初始化性能追踪器。
        
        Args:
            enable_detailed_tracking: 是否启用详细追踪（保存每次执行的耗时）
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._enable_detailed_tracking = enable_detailed_tracking
        
        # 性能指标存储
        self._metrics: dict[str, OperationMetrics] = {}
        
        # 当前追踪的操作栈
        self._tracking_stack: list[tuple[str, float]] = []
        
        self.logger.info("性能追踪器已初始化，详细追踪=%s", enable_detailed_tracking)
    
    @contextmanager
    def track(self, operation_name: str):
        """追踪操作性能的上下文管理器。
        
        Args:
            operation_name: 操作名称
            
        Yields:
            None
            
        Example:
            with tracker.track("数据处理"):
                process_data()
        """
        start_time = time.time()
        success = True
        
        try:
            # 入栈
            self._tracking_stack.append((operation_name, start_time))
            yield
        
        except Exception:
            success = False
            raise
        
        finally:
            # 出栈
            if self._tracking_stack and self._tracking_stack[-1][0] == operation_name:
                self._tracking_stack.pop()
            
            # 记录执行时间
            duration = time.time() - start_time
            self.record_operation(operation_name, duration, success)
    
    def record_operation(
        self,
        operation_name: str,
        duration: float,
        success: bool = True
    ) -> None:
        """记录操作执行。
        
        Args:
            operation_name: 操作名称
            duration: 耗时（秒）
            success: 是否成功
        """
        # 获取或创建指标对象
        if operation_name not in self._metrics:
            self._metrics[operation_name] = OperationMetrics(operation_name)
        
        metrics = self._metrics[operation_name]
        metrics.record_execution(duration, success)
        
        # 记录日志
        status = "成功" if success else "失败"
        self.logger.debug(
            "记录操作 [%s] %s，耗时 %.3f 秒",
            operation_name,
            status,
            duration
        )
    
    def get_metrics(self, operation_name: str) -> Optional[OperationMetrics]:
        """获取指定操作的性能指标。
        
        Args:
            operation_name: 操作名称
            
        Returns:
            性能指标对象，不存在返回None
        """
        return self._metrics.get(operation_name)
    
    def get_all_metrics(self) -> dict[str, OperationMetrics]:
        """获取所有操作的性能指标。
        
        Returns:
            性能指标字典
        """
        return self._metrics.copy()
    
    def get_summary(self, operation_name: Optional[str] = None) -> str:
        """获取性能摘要报告。
        
        Args:
            operation_name: 操作名称，为None时返回所有操作的摘要
            
        Returns:
            性能摘要字符串
        """
        if operation_name:
            metrics = self.get_metrics(operation_name)
            if metrics:
                return metrics.get_summary()
            else:
                return f"未找到操作 {operation_name} 的性能数据"
        
        # 返回所有操作的摘要
        if not self._metrics:
            return "暂无性能数据"
        
        lines = ["性能统计摘要:", "=" * 80]
        
        # 按平均耗时排序
        sorted_metrics = sorted(
            self._metrics.values(),
            key=lambda m: m.avg_time,
            reverse=True
        )
        
        for metrics in sorted_metrics:
            lines.append(metrics.get_summary())
        
        lines.append("=" * 80)
        
        # 添加总体统计
        total_operations = sum(m.execution_count for m in self._metrics.values())
        total_time = sum(m.total_time for m in self._metrics.values())
        total_failures = sum(m.failure_count for m in self._metrics.values())
        
        lines.append(f"总操作次数: {total_operations}")
        lines.append(f"总耗时: {total_time:.2f}秒")
        lines.append(f"总失败次数: {total_failures}")
        
        if total_operations > 0:
            overall_success_rate = ((total_operations - total_failures) / total_operations) * 100
            lines.append(f"总体成功率: {overall_success_rate:.1f}%")
        
        return "\n".join(lines)
    
    def get_slowest_operations(self, top_n: int = 5) -> list[OperationMetrics]:
        """获取最慢的N个操作。
        
        Args:
            top_n: 返回的数量
            
        Returns:
            操作指标列表
        """
        sorted_metrics = sorted(
            self._metrics.values(),
            key=lambda m: m.avg_time,
            reverse=True
        )
        return sorted_metrics[:top_n]
    
    def get_most_frequent_operations(self, top_n: int = 5) -> list[OperationMetrics]:
        """获取执行次数最多的N个操作。
        
        Args:
            top_n: 返回的数量
            
        Returns:
            操作指标列表
        """
        sorted_metrics = sorted(
            self._metrics.values(),
            key=lambda m: m.execution_count,
            reverse=True
        )
        return sorted_metrics[:top_n]
    
    def get_operations_with_failures(self) -> list[OperationMetrics]:
        """获取有失败记录的操作。
        
        Returns:
            操作指标列表
        """
        return [m for m in self._metrics.values() if m.failure_count > 0]
    
    def get_performance_trend(
        self,
        operation_name: str,
        window_size: int = 10
    ) -> Optional[dict[str, float]]:
        """获取操作的性能趋势。
        
        Args:
            operation_name: 操作名称
            window_size: 窗口大小（最近N次执行）
            
        Returns:
            趋势数据，包含最近N次的平均耗时等
        """
        metrics = self.get_metrics(operation_name)
        if not metrics or not metrics.durations:
            return None
        
        # 获取最近N次的耗时
        recent_durations = metrics.durations[-window_size:]
        
        if not recent_durations:
            return None
        
        avg_duration = sum(recent_durations) / len(recent_durations)
        min_duration = min(recent_durations)
        max_duration = max(recent_durations)
        
        # 计算趋势（与整体平均值比较）
        if metrics.avg_time > 0:
            trend_percent = ((avg_duration - metrics.avg_time) / metrics.avg_time) * 100
        else:
            trend_percent = 0.0
        
        return {
            "window_size": len(recent_durations),
            "avg_duration": avg_duration,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "trend_percent": trend_percent,  # 正值表示变慢，负值表示变快
        }
    
    def reset_metrics(self, operation_name: Optional[str] = None) -> None:
        """重置性能指标。
        
        Args:
            operation_name: 操作名称，为None时重置所有指标
        """
        if operation_name:
            if operation_name in self._metrics:
                del self._metrics[operation_name]
                self.logger.info("已重置操作 %s 的性能指标", operation_name)
        else:
            self._metrics.clear()
            self.logger.info("已重置所有性能指标")
    
    def export_metrics(self) -> dict:
        """导出性能指标数据。
        
        Returns:
            可序列化的指标数据字典
        """
        export_data = {}
        
        for name, metrics in self._metrics.items():
            export_data[name] = {
                "execution_count": metrics.execution_count,
                "total_time": metrics.total_time,
                "avg_time": metrics.avg_time,
                "min_time": metrics.min_time if metrics.min_time != float('inf') else 0.0,
                "max_time": metrics.max_time,
                "last_time": metrics.last_time,
                "failure_count": metrics.failure_count,
                "success_rate": metrics.success_rate,
            }
        
        return export_data
    
    def log_summary(self) -> None:
        """记录性能摘要到日志。"""
        summary = self.get_summary()
        for line in summary.split('\n'):
            self.logger.info(line)
