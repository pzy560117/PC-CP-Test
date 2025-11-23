"""循环执行控制器，管理自动化流程的循环执行和状态监控。"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class LoopStatus(Enum):
    """循环执行状态枚举。"""
    STOPPED = "stopped"  # 已停止
    RUNNING = "running"  # 运行中
    PAUSED = "paused"    # 已暂停
    ERROR = "error"      # 错误状态


@dataclass
class LoopStatistics:
    """循环执行统计信息。"""
    total_iterations: int = 0       # 总执行次数
    successful_iterations: int = 0  # 成功次数
    failed_iterations: int = 0      # 失败次数
    last_error: Optional[str] = None  # 最后一次错误信息
    start_time: Optional[float] = None  # 开始时间
    last_iteration_time: Optional[float] = None  # 最后一次迭代时间
    
    @property
    def success_rate(self) -> float:
        """计算成功率。"""
        if self.total_iterations == 0:
            return 0.0
        return (self.successful_iterations / self.total_iterations) * 100


class LoopExecutor:
    """循环执行管理器，提供循环控制、状态监控和统计功能。"""
    
    def __init__(
        self,
        task_func: Callable[[], None],
        interval: int = 300,
        max_iterations: int = 0,
        auto_restart: bool = False,
        pause_on_error: bool = True,
        error_threshold: int = 3,
    ) -> None:
        """初始化循环执行器。
        
        Args:
            task_func: 要循环执行的任务函数
            interval: 循环间隔秒数
            max_iterations: 最大循环次数，0表示无限循环
            auto_restart: 出错后是否自动重启
            pause_on_error: 出错后是否暂停
            error_threshold: 连续错误阈值，超过后停止执行
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._task_func = task_func
        self._interval = interval
        self._max_iterations = max_iterations
        self._auto_restart = auto_restart
        self._pause_on_error = pause_on_error
        self._error_threshold = error_threshold
        
        # 状态控制
        self._status = LoopStatus.STOPPED
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 默认不暂停
        
        # 统计信息
        self._stats = LoopStatistics()
        self._consecutive_errors = 0
        
        # 线程控制
        self._loop_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def start(self) -> None:
        """启动循环执行。"""
        with self._lock:
            if self._status == LoopStatus.RUNNING:
                self.logger.warning("循环执行器已在运行状态")
                return
            
            self._status = LoopStatus.RUNNING
            self._stop_event.clear()
            self._pause_event.set()
            self._stats.start_time = time.time()
            
            # 在新线程中执行循环
            self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
            self._loop_thread.start()
            
            self.logger.info("循环执行器已启动，间隔=%s秒，最大次数=%s", self._interval, self._max_iterations or "无限")
    
    def stop(self) -> None:
        """停止循环执行。"""
        with self._lock:
            if self._status == LoopStatus.STOPPED:
                self.logger.warning("循环执行器已是停止状态")
                return
            
            self.logger.info("正在停止循环执行器...")
            self._status = LoopStatus.STOPPED
            self._stop_event.set()
            self._pause_event.set()  # 确保不会在暂停状态卡住
        
        # 等待循环线程结束
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=5)
            if self._loop_thread.is_alive():
                self.logger.warning("循环线程未能在5秒内停止")
        
        self.logger.info("循环执行器已停止")
    
    def pause(self) -> None:
        """暂停循环执行。"""
        with self._lock:
            if self._status != LoopStatus.RUNNING:
                self.logger.warning("只能暂停运行中的循环执行器")
                return
            
            self._status = LoopStatus.PAUSED
            self._pause_event.clear()
            self.logger.info("循环执行器已暂停")
    
    def resume(self) -> None:
        """恢复循环执行。"""
        with self._lock:
            if self._status != LoopStatus.PAUSED:
                self.logger.warning("只能恢复已暂停的循环执行器")
                return
            
            self._status = LoopStatus.RUNNING
            self._pause_event.set()
            self.logger.info("循环执行器已恢复")
    
    def _run_loop(self) -> None:
        """循环执行主逻辑（在独立线程中运行）。"""
        try:
            while not self._stop_event.is_set():
                # 检查是否暂停
                self._pause_event.wait()
                
                # 检查是否停止
                if self._stop_event.is_set():
                    break
                
                # 检查是否达到最大次数
                if self._max_iterations > 0 and self._stats.total_iterations >= self._max_iterations:
                    self.logger.info("已达到最大循环次数 %s，停止执行", self._max_iterations)
                    break
                
                # 检查是否超过错误阈值
                if self._consecutive_errors >= self._error_threshold:
                    self.logger.error("连续错误次数 %s 已达阈值，停止执行", self._consecutive_errors)
                    self._status = LoopStatus.ERROR
                    break
                
                # 执行任务
                self._execute_task()
                
                # 等待间隔时间
                if not self._stop_event.is_set():
                    self.logger.info("等待 %s 秒后继续下一轮", self._interval)
                    self._stop_event.wait(timeout=self._interval)
        
        except Exception as exc:
            self.logger.exception("循环执行器发生未预期错误: %s", exc)
            self._status = LoopStatus.ERROR
        finally:
            if self._status == LoopStatus.RUNNING:
                self._status = LoopStatus.STOPPED
    
    def _execute_task(self) -> None:
        """执行单次任务。"""
        self._stats.total_iterations += 1
        iteration = self._stats.total_iterations
        
        self.logger.info("开始第 %s 次循环执行", iteration)
        start_time = time.time()
        
        try:
            self._task_func()
            duration = time.time() - start_time
            
            # 任务成功
            self._stats.successful_iterations += 1
            self._stats.last_iteration_time = time.time()
            self._consecutive_errors = 0  # 重置连续错误计数
            
            self.logger.info("第 %s 次循环执行成功，耗时 %.2f 秒", iteration, duration)
            
        except Exception as exc:
            duration = time.time() - start_time
            
            # 任务失败
            self._stats.failed_iterations += 1
            self._stats.last_error = str(exc)
            self._consecutive_errors += 1
            
            self.logger.error("第 %s 次循环执行失败，耗时 %.2f 秒: %s", iteration, duration, exc)
            
            # 根据配置决定是否暂停
            if self._pause_on_error:
                self.logger.warning("出错后暂停循环执行，需手动恢复")
                self.pause()
            
            # 根据配置决定是否自动重启
            if self._auto_restart and not self._pause_on_error:
                self.logger.info("自动重启模式已启用，将在间隔后重试")
    
    @property
    def status(self) -> LoopStatus:
        """获取当前状态。"""
        return self._status
    
    @property
    def statistics(self) -> LoopStatistics:
        """获取统计信息。"""
        return self._stats
    
    def get_status_report(self) -> str:
        """获取状态报告。"""
        stats = self._stats
        elapsed = time.time() - stats.start_time if stats.start_time else 0
        
        report = [
            f"循环执行器状态: {self._status.value}",
            f"总执行次数: {stats.total_iterations}",
            f"成功次数: {stats.successful_iterations}",
            f"失败次数: {stats.failed_iterations}",
            f"成功率: {stats.success_rate:.1f}%",
            f"连续错误: {self._consecutive_errors}",
            f"运行时长: {elapsed:.1f}秒",
        ]
        
        if stats.last_error:
            report.append(f"最后错误: {stats.last_error}")
        
        return "\n".join(report)
