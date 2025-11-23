"""应用入口，负责解析参数并启动自动化流程。"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from typing import Any, List, Optional

from src.automator.app_automator import AppAutomator
from src.config.config_loader import ConfigLoader
from src.exception.custom_exceptions import AutomationException
from src.utils.error_recovery import ErrorRecoveryManager
from src.utils.exception_handler import handle_exception
from src.utils.logger import configure_logging
from src.utils.performance_tracker import PerformanceTracker
from src.utils.resource_monitor import ResourceMonitor
from src.ui.status_dashboard import RunState, StatusDashboard


def parse_arguments() -> argparse.Namespace:
    """构建命令行解析。"""

    parser = argparse.ArgumentParser(description="腾讯分分彩公式搜索自动化工具")
    parser.add_argument("--config", dest="config_file", help="自定义配置文件路径，默认使用 config/config.json")
    parser.add_argument("--log-level", dest="log_level", help="覆盖配置中的日志级别，示例：DEBUG/INFO")
    parser.add_argument("--loop", action="store_true", help="启用循环模式（若配置已启用可省略）")
    parser.add_argument("--interval", type=int, help="循环间隔秒数，优先级高于配置文件")
    parser.add_argument("--max-iterations", type=int, help="循环最大次数，0 表示不限制")
    parser.add_argument("--real-run", dest="dry_run", action="store_false", help="执行真实自动化流程，默认仅校验配置")
    parser.set_defaults(dry_run=True)
    return parser.parse_args()


def _predict_next_period(current_period: str | None) -> str:
    """根据当前期号预测下一期（保持长度，不存在则返回空字符串）。"""

    if not current_period:
        return ""
    try:
        value = int(current_period)
        next_value = value + 1
        return str(next_value).zfill(len(current_period))
    except ValueError:
        return current_period


def build_config_loader(config_file: str | None) -> ConfigLoader:
    """创建配置加载器并保证目录存在。"""

    loader = ConfigLoader(config_file)
    loader.ensure_directories()
    return loader


def run_automation(loader: ConfigLoader, args: argparse.Namespace) -> None:
    """根据配置和参数执行一次或多次自动化流程。"""

    config_dict: dict[str, Any] = loader.as_dict()
    configure_logging(config_dict, args.log_level)
    logger = logging.getLogger("Main")
    
    # 初始化增强功能组件
    performance_cfg = config_dict.get("performance", {}) or {}
    loop_cfg = config_dict.get("loop", {}) or {}
    
    # 性能追踪器
    perf_tracker = PerformanceTracker(enable_detailed_tracking=True)
    logger.info("✓ 性能追踪器已初始化")
    
    # 资源监控器
    resource_monitor = ResourceMonitor(
        cpu_threshold=performance_cfg.get("cpu_threshold", 80),
        memory_threshold=80.0,
        check_interval=loop_cfg.get("status_check_interval", 10),
        enable_alerts=performance_cfg.get("monitoring_enabled", True)
    )
    resource_monitor.start()
    logger.info("✓ 资源监控器已启动")
    
    # 错误恢复管理器
    error_recovery = ErrorRecoveryManager(
        max_retries=config_dict.get("app", {}).get("retry_count", 3),
        retry_delay=config_dict.get("app", {}).get("retry_delay", 5),
        exponential_backoff=True,
        enable_auto_recovery=loop_cfg.get("auto_restart", True)
    )
    logger.info("✓ 错误恢复管理器已初始化")
    
    # 创建自动化控制器
    automator = AppAutomator(loader)
    
    # 运行状态与面板
    run_state = RunState()
    run_state.update(status="初始化", dry_run=args.dry_run, iteration=0)
    dashboard = StatusDashboard(run_state, perf_tracker, resource_monitor, error_recovery)
    dashboard.start()
    
    # 设置信号处理
    stop_requested = False
    
    def signal_handler(signum, frame):
        nonlocal stop_requested
        logger.info("收到中断信号 (%s)，准备停止...", signum)
        stop_requested = True
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    # 循环配置
    loop_enabled = args.loop or loop_cfg.get("enabled", False)
    interval = args.interval or loop_cfg.get("interval", 300)
    max_iterations = args.max_iterations if args.max_iterations is not None else loop_cfg.get("max_iterations", 0)
    pause_on_error = loop_cfg.get("pause_on_error", True)
    error_threshold = loop_cfg.get("error_threshold", 3)
    
    iteration = 0
    consecutive_errors = 0
    pending_recommendations: Optional[List[List[int]]] = None
    pending_target_period: Optional[str] = None
    last_observed_period: Optional[str] = automator.get_last_recorded_period()
    
    try:
        logger.info("=" * 80)
        logger.info("开始自动化流程")
        logger.info("循环模式: %s", "启用" if loop_enabled else "禁用")
        if loop_enabled:
            logger.info("循环间隔: %s秒, 最大次数: %s", interval, max_iterations or "无限")
        logger.info("=" * 80)
        
        while not stop_requested:
            iteration += 1
            
            # 检查是否达到最大次数
            if max_iterations > 0 and iteration > max_iterations:
                logger.info("已达到最大循环次数 %s，结束执行", max_iterations)
                break
            
            # 检查错误阈值
            if consecutive_errors >= error_threshold:
                logger.error("连续错误次数 %s 已达阈值，停止执行", consecutive_errors)
                break
            
            logger.info("-" * 80)
            logger.info("开始第 %s 次流程执行，dry_run=%s", iteration, args.dry_run)
            run_state.update(iteration=iteration, dry_run=args.dry_run, status="等待新期开奖", message="")
            
            # 使用性能追踪器追踪整个流程
            with perf_tracker.track("完整流程"):
                execution_success = False
                lottery_result: Optional[Any] = None

                try:
                    if args.dry_run:
                        logger.info("Dry-run 模式，执行配置校验。")
                        automator.start(dry_run=True, compare_mode="full")
                        run_state.update(status="Dry-run 完成", message="")
                        execution_success = True
                        continue

                    if stop_requested:
                        logger.info("检测到停止请求，跳出循环")
                        break

                    reference_period = last_observed_period
                    run_state.update(status="等待新期开奖", message="监控新开奖...")
                    logger.info("步骤1: 等待新开奖（参考期号: %s）...", reference_period or "无")
                    lottery_result = automator.wait_for_new_lottery(
                        reference_period=reference_period,
                        stop_checker=lambda: stop_requested,
                    )
                    if not lottery_result:
                        logger.warning("⚠️ 等待新开奖超时或被中断，跳过本轮")
                        run_state.update(status="等待开奖超时/终止", message="本轮跳过")
                        continue

                    last_observed_period = lottery_result.period
                    run_state.update(
                        last_lottery_period=lottery_result.period,
                        last_lottery_numbers=lottery_result.numbers,
                        message=f"已获取期号 {lottery_result.period}",
                    )

                    # 若当前期号与待比对期号一致，则立即对比
                    if pending_target_period and pending_recommendations:
                        if lottery_result.period == pending_target_period:
                            logger.info("步骤2: 对比待比对期号 %s ...", pending_target_period)
                            comparisons = automator._build_comparisons(pending_recommendations, lottery_result)
                            automator._log_comparison_details(lottery_result, comparisons)
                            automator._persist_comparison_results(lottery_result, comparisons)

                            history_entries = [
                                {
                                    "period": lottery_result.period,
                                    "recommended": item.recommended,
                                    "is_hit": item.is_hit,
                                    "hits": item.hits,
                                }
                                for item in comparisons
                            ]
                            run_state.add_comparison_history(history_entries)
                            run_state.update(
                                status="已对比",
                                message="等待下一期开奖",
                                pending_target_period=None,
                                pending_recommendations=[],
                            )
                            pending_recommendations = None
                            pending_target_period = None
                            logger.info("✅ 推荐与期号 %s 对比完成", lottery_result.period)
                        else:
                            logger.info(
                                "当前期号 %s 尚未达到待比对目标 %s",
                                lottery_result.period,
                                pending_target_period,
                            )

                    if stop_requested:
                        logger.info("检测到停止请求，跳出循环")
                        break

                    # 执行搜索，准备下一期推荐
                    target_period = _predict_next_period(lottery_result.period)
                    run_state.update(status="搜索中", message=f"准备期号 {target_period} 的推荐")

                    def execute_task() -> list[list[int]]:
                        with perf_tracker.track("自动化启动"):
                            result = automator.start(dry_run=False, compare_mode="collect")
                            if not result:
                                raise AutomationException("未提取到推荐号码")
                            return result

                    new_recommendations = error_recovery.execute_with_retry(
                        execute_task,
                        operation_name=f"第{iteration}次流程执行",
                        context={"iteration": iteration, "target_period": target_period}
                    )

                    pending_recommendations = new_recommendations
                    pending_target_period = target_period
                    automator.write_recommendations_to_cloud(target_period, new_recommendations)
                    run_state.update(
                        status="待比对",
                        last_recommendations=new_recommendations,
                        last_recommendations_period=target_period,
                        pending_target_period=target_period,
                        pending_recommendations=new_recommendations,
                        message=f"已提取 {len(new_recommendations)} 条，等待期号 {target_period}",
                    )
                    logger.info("✅ 第 %s 次搜索执行成功，目标期号 %s", iteration, target_period)

                    execution_success = True
                    consecutive_errors = 0

                except Exception as exc:
                    consecutive_errors += 1
                    execution_success = False

                    logger.error("❌ 第 %s 次流程执行失败: %s", iteration, exc)
                    handle_exception(exc, logger)
                    run_state.update(status="执行失败", message=str(exc))

                    error_recovery.record_error(exc, context={"iteration": iteration})

                    if pause_on_error:
                        logger.warning("⏸️ 出错后暂停，连续错误次数: %s", consecutive_errors)
                        if consecutive_errors < error_threshold:
                            logger.info("将在 %s 秒后重试", interval)

                finally:
                    with perf_tracker.track("自动化停止"):
                        try:
                            automator.stop()
                        except Exception as e:
                            logger.warning("停止自动化时出错: %s", e)

            # 显示状态信息
            if iteration % 5 == 0 or not execution_success:  # 每5次或失败时显示
                _log_status_summary(
                    logger, perf_tracker, resource_monitor, 
                    error_recovery, iteration
                )
            
            # 检查是否继续循环
            if not loop_enabled:
                logger.info("单次执行模式，流程结束")
                break
            
            if stop_requested:
                logger.info("收到停止请求，结束循环")
                break
            
            # 等待间隔
            logger.info("⏱️ 等待 %s 秒后继续下一轮...", interval)
            run_state.update(status="休眠", message=f"{interval} 秒后继续")
            for _ in range(interval):
                if stop_requested:
                    break
                time.sleep(1)
        
        logger.info("=" * 80)
        logger.info("流程执行完成，总执行次数: %s", iteration)
        
    except KeyboardInterrupt:
        logger.info("⚠️ 收到键盘中断信号，准备退出")
        
    except Exception as exc:
        logger.exception("流程执行过程中发生未预期错误: %s", exc)
        handle_exception(exc, logger)
        sys.exit(1)
        
    finally:
        # 清理资源
        logger.info("正在清理资源...")
        
        try:
            resource_monitor.stop()
            logger.info("✓ 资源监控器已停止")
        except Exception as e:
            logger.warning("停止资源监控器失败: %s", e)
        finally:
            dashboard.stop()
        
        # 输出最终统计
        logger.info("=" * 80)
        logger.info("最终统计报告")
        logger.info("=" * 80)
        
        # 性能统计
        logger.info("\n--- 性能统计 ---")
        perf_tracker.log_summary()
        
        # 错误统计
        logger.info("\n--- 错误统计 ---")
        error_stats = error_recovery.get_error_statistics()
        logger.info("总错误次数: %s", error_stats["total_errors"])
        if error_stats["most_common_error"]:
            logger.info("最常见错误: %s", error_stats["most_common_error"])
        
        # 资源使用
        logger.info("\n--- 资源使用 ---")
        avg_usage = resource_monitor.get_average_usage(duration_seconds=300)
        logger.info("平均CPU: %.1f%%", avg_usage["avg_cpu"])
        logger.info("平均内存: %.1f%%", avg_usage["avg_memory"])
        logger.info("平均进程内存: %.1fMB", avg_usage["avg_process_memory_mb"])
        
        logger.info("=" * 80)


def _log_status_summary(
    logger: logging.Logger,
    perf_tracker: PerformanceTracker,
    resource_monitor: ResourceMonitor,
    error_recovery: ErrorRecoveryManager,
    iteration: int
) -> None:
    """记录状态摘要。"""
    logger.info("┌─ 状态摘要 (第%s次执行)", iteration)
    
    # 性能信息
    metrics = perf_tracker.get_metrics("完整流程")
    if metrics:
        logger.info("│ 平均耗时: %.2f秒, 成功率: %.1f%%", 
                   metrics.avg_time, metrics.success_rate)
    
    # 资源信息
    snapshot = resource_monitor.get_latest_snapshot()
    if snapshot:
        logger.info("│ CPU: %.1f%%, 内存: %.1f%%, 进程内存: %.1fMB",
                   snapshot.cpu_percent, snapshot.memory_percent, 
                   snapshot.process_memory_mb)
    
    # 错误信息
    error_stats = error_recovery.get_error_statistics()
    logger.info("│ 总错误: %s", error_stats["total_errors"])
    
    logger.info("└─────────────────────────────────────")


def main() -> None:
    """程序入口。"""

    args = parse_arguments()
    loader = build_config_loader(args.config_file)
    run_automation(loader, args)


if __name__ == "__main__":
    main()
