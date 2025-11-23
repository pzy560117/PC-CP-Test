"""实时状态面板，用于展示循环执行指标。"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

try:  # GUI 模块（若系统缺少 Tk 会自动降级）
    import tkinter as tk
except Exception:  # pylint:disable=broad-except
    tk = None  # type: ignore


class RunState:
    """线程安全的运行状态存储。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "iteration": 0,
            "dry_run": True,
            "status": "idle",
            "last_recommendations": [],
            "last_recommendations_period": None,
            "last_lottery_period": None,
            "last_lottery_numbers": None,
            "message": "",
            "comparison_history": [],  # 最近 10 条
            "total_comparisons": 0,
            "total_hits": 0,
            "pending_target_period": None,
            "pending_recommendations": [],
            "last_updated": time.time(),
        }

    def update(self, **kwargs: Any) -> None:
        """写入状态。"""

        with self._lock:
            self._state.update(kwargs)
            self._state["last_updated"] = time.time()

    def snapshot(self) -> Dict[str, Any]:
        """获取当前状态快照。"""

        with self._lock:
            return dict(self._state)

    def add_comparison_history(self, entries: List[Dict[str, Any]]) -> None:
        """新增对比记录并更新统计。"""

        if not entries:
            return
        with self._lock:
            history = self._state.get("comparison_history", [])
            history.extend(entries)
            self._state["comparison_history"] = history[-10:]
            total_comp = self._state.get("total_comparisons", 0) + len(entries)
            total_hits = self._state.get("total_hits", 0) + sum(1 for item in entries if item.get("is_hit"))
            self._state["total_comparisons"] = total_comp
            self._state["total_hits"] = total_hits
            self._state["last_updated"] = time.time()


class StatusDashboard:
    """实时状态面板。"""

    def __init__(
        self,
        run_state: RunState,
        perf_tracker,
        resource_monitor,
        error_recovery,
        refresh_interval_ms: int = 1000,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.run_state = run_state
        self.perf_tracker = perf_tracker
        self.resource_monitor = resource_monitor
        self.error_recovery = error_recovery
        self.refresh_interval = refresh_interval_ms

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._root: Optional[tk.Tk] = None  # type: ignore[assignment]
        self._enabled = tk is not None

        # UI 元素
        self._iteration_var: Optional[tk.StringVar] = None
        self._recommend_var: Optional[tk.StringVar] = None
        self._lottery_var: Optional[tk.StringVar] = None
        self._perf_var: Optional[tk.StringVar] = None
        self._resource_var: Optional[tk.StringVar] = None
        self._error_var: Optional[tk.StringVar] = None
        self._hit_var: Optional[tk.StringVar] = None
        self._pending_var: Optional[tk.StringVar] = None
        self._history_list: Optional[tk.Listbox] = None

    def start(self) -> None:
        """启动面板。"""

        if not self._enabled:
            self.logger.info("当前环境缺少 Tk 支持，实时面板已跳过。")
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止面板。"""

        self._stop_event.set()
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:  # pylint:disable=broad-except
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    # 内部 -----------------------------------------------------------------
    def _run_loop(self) -> None:
        if tk is None:  # 双重检测
            return
        self._root = tk.Tk()
        self._root.title("执行状态监控")
        self._root.protocol("WM_DELETE_WINDOW", self._request_stop)
        self._build_layout(self._root)
        self._schedule_update()
        try:
            self._root.mainloop()
        except Exception as exc:  # pylint:disable=broad-except
            self.logger.warning("状态面板异常退出: %s", exc)

    def _request_stop(self) -> None:
        self._stop_event.set()
        if self._root:
            self._root.destroy()

    def _build_layout(self, root: tk.Tk) -> None:  # type: ignore[valid-type]
        self._iteration_var = tk.StringVar(value="执行状态：-")
        self._recommend_var = tk.StringVar(value="最新推荐：-")
        self._lottery_var = tk.StringVar(value="最新开奖：-")
        self._perf_var = tk.StringVar(value="性能：-")
        self._resource_var = tk.StringVar(value="资源：-")
        self._error_var = tk.StringVar(value="错误：-")
        self._hit_var = tk.StringVar(value="总体命中率：-")
        self._pending_var = tk.StringVar(value="待比对：-")

        padding = {"padx": 10, "pady": 5, "anchor": "w"}
        tk.Label(root, textvariable=self._iteration_var, font=("Microsoft YaHei", 12, "bold")).pack(**padding)
        tk.Label(root, textvariable=self._recommend_var, font=("Microsoft YaHei", 11)).pack(**padding)
        tk.Label(root, textvariable=self._lottery_var, font=("Microsoft YaHei", 11)).pack(**padding)
        tk.Label(root, textvariable=self._perf_var, font=("Microsoft YaHei", 10)).pack(**padding)
        tk.Label(root, textvariable=self._resource_var, font=("Microsoft YaHei", 10)).pack(**padding)
        tk.Label(root, textvariable=self._error_var, font=("Microsoft YaHei", 10)).pack(**padding)
        tk.Label(root, textvariable=self._hit_var, font=("Microsoft YaHei", 10, "bold")).pack(**padding)
        tk.Label(root, textvariable=self._pending_var, font=("Microsoft YaHei", 10)).pack(**padding)

        tk.Label(root, text="最近10条对比记录：", font=("Microsoft YaHei", 10, "bold"), anchor="w").pack(fill="x", padx=10)
        self._history_list = tk.Listbox(root, height=10, font=("Consolas", 10))
        self._history_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _schedule_update(self) -> None:
        if self._stop_event.is_set() or not self._root:
            if self._root:
                self._root.destroy()
            return
        self._refresh()
        self._root.after(self.refresh_interval, self._schedule_update)

    def _refresh(self) -> None:
        snapshot = self.run_state.snapshot()
        if self._iteration_var:
            self._iteration_var.set(
                f"第 {snapshot['iteration']} 次 | 模式: {'Dry' if snapshot['dry_run'] else 'Real'} | 状态: {snapshot['status']}"
            )
        if self._recommend_var:
            recs = snapshot.get("last_recommendations") or []
            if recs:
                rec_text = "; ".join("[" + ",".join(map(str, rec)) + "]" for rec in recs)
            else:
                rec_text = "-"
            message = snapshot.get("message") or ""
            last_rec_period = snapshot.get("last_recommendations_period")
            prefix = f"期号 {last_rec_period} " if last_rec_period else ""
            self._recommend_var.set(f"最新推荐：{prefix}{rec_text} {message}")
        if self._lottery_var:
            period = snapshot.get("last_lottery_period")
            numbers = snapshot.get("last_lottery_numbers")
            if period and numbers:
                self._lottery_var.set(f"最新开奖：{period} -> {numbers}")
            else:
                self._lottery_var.set("最新开奖：-")

        if self._perf_var:
            metrics = self.perf_tracker.get_metrics("完整流程")
            if metrics:
                self._perf_var.set(
                    f"性能：平均 {metrics.avg_time:.2f}s | 成功率 {metrics.success_rate:.1f}% | 次数 {metrics.execution_count}"
                )
            else:
                self._perf_var.set("性能：-")

        if self._resource_var:
            snapshot_res = self.resource_monitor.get_latest_snapshot()
            if snapshot_res:
                self._resource_var.set(
                    "资源：CPU {cpu:.1f}% | MEM {mem:.1f}% | Proc {proc:.1f}MB".format(
                        cpu=snapshot_res.cpu_percent,
                        mem=snapshot_res.memory_percent,
                        proc=snapshot_res.process_memory_mb,
                    )
                )
            else:
                self._resource_var.set("资源：-")

        if self._error_var:
            error_stats = self.error_recovery.get_error_statistics()
            most_common = error_stats.get("most_common_error") or "-"
            total_errors = error_stats.get("total_errors", 0)
            self._error_var.set(f"错误：{total_errors} | 常见：{most_common}")

        if self._hit_var:
            total_comp = snapshot.get("total_comparisons", 0)
            total_hits = snapshot.get("total_hits", 0)
            hit_rate = (total_hits / total_comp * 100) if total_comp else 0.0
            self._hit_var.set(f"总体命中率：{total_hits}/{total_comp} ({hit_rate:.1f}%)")

        if self._pending_var:
            pending_period = snapshot.get("pending_target_period")
            pending_recs = snapshot.get("pending_recommendations") or []
            if pending_period and pending_recs:
                rec_text = "; ".join("[" + ",".join(map(str, rec)) + "]" for rec in pending_recs)
                self._pending_var.set(f"待比对：期号 {pending_period} -> {rec_text}")
            else:
                self._pending_var.set("待比对：-")

        if self._history_list:
            self._history_list.delete(0, tk.END)
            history = snapshot.get("comparison_history", [])
            for item in history:
                period = item.get("period", "-")
                recommended = item.get("recommended", [])
                status = "命中" if item.get("is_hit") else "未中"
                hits = item.get("hits") or []
                line = f"{period} | {recommended} -> {status} ({hits})"
                self._history_list.insert(tk.END, line)
