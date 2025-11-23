"""资源监控器，监控系统资源使用情况。"""
from __future__ import annotations

import logging
import psutil
import threading
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResourceSnapshot:
    """资源使用快照。"""
    timestamp: float              # 时间戳
    cpu_percent: float            # CPU使用率（%）
    memory_percent: float         # 内存使用率（%）
    memory_used_mb: float         # 已使用内存（MB）
    memory_available_mb: float    # 可用内存（MB）
    process_memory_mb: float      # 进程内存（MB）
    process_cpu_percent: float    # 进程CPU（%）
    thread_count: int             # 线程数
    
    def __str__(self) -> str:
        """格式化输出。"""
        return (
            f"CPU={self.cpu_percent:.1f}%, "
            f"内存={self.memory_percent:.1f}%, "
            f"进程内存={self.process_memory_mb:.1f}MB, "
            f"进程CPU={self.process_cpu_percent:.1f}%, "
            f"线程数={self.thread_count}"
        )


@dataclass
class ResourceAlert:
    """资源告警。"""
    alert_type: str        # 告警类型
    severity: str          # 严重程度
    message: str           # 告警消息
    value: float           # 触发值
    threshold: float       # 阈值
    timestamp: float       # 时间戳


class ResourceMonitor:
    """资源监控器，实时监控CPU、内存等系统资源使用情况。"""
    
    def __init__(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 80.0,
        check_interval: int = 10,
        enable_alerts: bool = True,
    ) -> None:
        """初始化资源监控器。
        
        Args:
            cpu_threshold: CPU使用率告警阈值（%）
            memory_threshold: 内存使用率告警阈值（%）
            check_interval: 检查间隔（秒）
            enable_alerts: 是否启用告警
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cpu_threshold = cpu_threshold
        self._memory_threshold = memory_threshold
        self._check_interval = check_interval
        self._enable_alerts = enable_alerts
        
        # 监控状态
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 数据存储
        self._snapshots: list[ResourceSnapshot] = []
        self._max_snapshots = 1000  # 最多保留1000个快照
        self._alerts: list[ResourceAlert] = []
        self._max_alerts = 100  # 最多保留100条告警
        
        # 进程对象
        try:
            self._process = psutil.Process()
        except Exception as e:
            self.logger.error("无法获取当前进程信息: %s", e)
            self._process = None
    
    def start(self) -> None:
        """启动资源监控。"""
        if self._monitoring:
            self.logger.warning("资源监控器已在运行")
            return
        
        self._monitoring = True
        self._stop_event.clear()
        
        # 在新线程中运行监控
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        self.logger.info(
            "资源监控器已启动，CPU阈值=%.1f%%，内存阈值=%.1f%%，检查间隔=%s秒",
            self._cpu_threshold,
            self._memory_threshold,
            self._check_interval
        )
    
    def stop(self) -> None:
        """停止资源监控。"""
        if not self._monitoring:
            self.logger.warning("资源监控器未运行")
            return
        
        self.logger.info("正在停止资源监控器...")
        self._monitoring = False
        self._stop_event.set()
        
        # 等待监控线程结束
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3)
        
        self.logger.info("资源监控器已停止")
    
    def _monitor_loop(self) -> None:
        """监控循环（在独立线程中运行）。"""
        try:
            while not self._stop_event.is_set():
                # 采集资源快照
                snapshot = self._capture_snapshot()
                
                if snapshot:
                    # 保存快照
                    self._save_snapshot(snapshot)
                    
                    # 检查告警条件
                    if self._enable_alerts:
                        self._check_alerts(snapshot)
                
                # 等待下一次检查
                self._stop_event.wait(timeout=self._check_interval)
        
        except Exception as exc:
            self.logger.exception("资源监控循环发生错误: %s", exc)
    
    def _capture_snapshot(self) -> Optional[ResourceSnapshot]:
        """采集当前资源使用快照。
        
        Returns:
            资源快照，失败返回None
        """
        try:
            # 系统级资源
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # 进程级资源
            process_memory_mb = 0.0
            process_cpu_percent = 0.0
            thread_count = 0
            
            if self._process:
                try:
                    process_memory_mb = self._process.memory_info().rss / (1024 * 1024)
                    process_cpu_percent = self._process.cpu_percent(interval=0.1)
                    thread_count = self._process.num_threads()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            snapshot = ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                process_memory_mb=process_memory_mb,
                process_cpu_percent=process_cpu_percent,
                thread_count=thread_count,
            )
            
            return snapshot
        
        except Exception as exc:
            self.logger.error("采集资源快照失败: %s", exc)
            return None
    
    def _save_snapshot(self, snapshot: ResourceSnapshot) -> None:
        """保存资源快照。
        
        Args:
            snapshot: 资源快照
        """
        self._snapshots.append(snapshot)
        
        # 限制快照数量
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
    
    def _check_alerts(self, snapshot: ResourceSnapshot) -> None:
        """检查告警条件。
        
        Args:
            snapshot: 资源快照
        """
        # 检查CPU使用率
        if snapshot.cpu_percent > self._cpu_threshold:
            alert = ResourceAlert(
                alert_type="CPU",
                severity="WARNING",
                message=f"系统CPU使用率过高: {snapshot.cpu_percent:.1f}%",
                value=snapshot.cpu_percent,
                threshold=self._cpu_threshold,
                timestamp=snapshot.timestamp,
            )
            self._add_alert(alert)
        
        # 检查内存使用率
        if snapshot.memory_percent > self._memory_threshold:
            alert = ResourceAlert(
                alert_type="MEMORY",
                severity="WARNING",
                message=f"系统内存使用率过高: {snapshot.memory_percent:.1f}%",
                value=snapshot.memory_percent,
                threshold=self._memory_threshold,
                timestamp=snapshot.timestamp,
            )
            self._add_alert(alert)
        
        # 检查进程内存（超过500MB告警）
        if snapshot.process_memory_mb > 500:
            alert = ResourceAlert(
                alert_type="PROCESS_MEMORY",
                severity="WARNING",
                message=f"进程内存使用过高: {snapshot.process_memory_mb:.1f}MB",
                value=snapshot.process_memory_mb,
                threshold=500.0,
                timestamp=snapshot.timestamp,
            )
            self._add_alert(alert)
    
    def _add_alert(self, alert: ResourceAlert) -> None:
        """添加告警记录。
        
        Args:
            alert: 告警对象
        """
        # 防止重复告警（5秒内同类型告警只记录一次）
        now = time.time()
        for existing in self._alerts[-10:]:  # 只检查最近10条
            if (existing.alert_type == alert.alert_type and 
                now - existing.timestamp < 5):
                return
        
        self._alerts.append(alert)
        self.logger.warning("[%s] %s", alert.alert_type, alert.message)
        
        # 限制告警数量
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]
    
    def get_current_snapshot(self) -> Optional[ResourceSnapshot]:
        """获取当前资源快照。
        
        Returns:
            资源快照
        """
        return self._capture_snapshot()
    
    def get_latest_snapshot(self) -> Optional[ResourceSnapshot]:
        """获取最新保存的资源快照。
        
        Returns:
            资源快照，如果没有则返回None
        """
        return self._snapshots[-1] if self._snapshots else None
    
    def get_average_usage(self, duration_seconds: int = 60) -> dict[str, float]:
        """获取指定时间段内的平均资源使用率。
        
        Args:
            duration_seconds: 时间段长度（秒）
            
        Returns:
            平均使用率字典
        """
        if not self._snapshots:
            return {
                "avg_cpu": 0.0,
                "avg_memory": 0.0,
                "avg_process_memory_mb": 0.0,
            }
        
        # 筛选指定时间段内的快照
        now = time.time()
        cutoff_time = now - duration_seconds
        recent_snapshots = [s for s in self._snapshots if s.timestamp >= cutoff_time]
        
        if not recent_snapshots:
            recent_snapshots = self._snapshots[-10:]  # 至少取最近10个
        
        # 计算平均值
        avg_cpu = sum(s.cpu_percent for s in recent_snapshots) / len(recent_snapshots)
        avg_memory = sum(s.memory_percent for s in recent_snapshots) / len(recent_snapshots)
        avg_process_memory = sum(s.process_memory_mb for s in recent_snapshots) / len(recent_snapshots)
        
        return {
            "avg_cpu": avg_cpu,
            "avg_memory": avg_memory,
            "avg_process_memory_mb": avg_process_memory,
            "sample_count": len(recent_snapshots),
        }
    
    def get_alerts(self, count: int = 10) -> list[ResourceAlert]:
        """获取最近的告警记录。
        
        Args:
            count: 要获取的告警数量
            
        Returns:
            告警记录列表
        """
        return self._alerts[-count:] if self._alerts else []
    
    def get_status_report(self) -> str:
        """获取资源监控状态报告。
        
        Returns:
            状态报告字符串
        """
        snapshot = self.get_latest_snapshot()
        if not snapshot:
            return "资源监控器未采集到数据"
        
        avg_usage = self.get_average_usage(60)
        alert_count = len(self._alerts)
        
        report = [
            f"资源监控状态: {'运行中' if self._monitoring else '已停止'}",
            f"当前快照: {snapshot}",
            f"1分钟平均CPU: {avg_usage['avg_cpu']:.1f}%",
            f"1分钟平均内存: {avg_usage['avg_memory']:.1f}%",
            f"1分钟平均进程内存: {avg_usage['avg_process_memory_mb']:.1f}MB",
            f"告警数量: {alert_count}",
        ]
        
        return "\n".join(report)
    
    def clear_data(self) -> None:
        """清空监控数据。"""
        self._snapshots.clear()
        self._alerts.clear()
        self.logger.info("资源监控数据已清空")
    
    @property
    def is_monitoring(self) -> bool:
        """检查是否正在监控。"""
        return self._monitoring
