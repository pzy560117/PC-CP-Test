"""应用入口，负责解析参数并启动自动化流程。"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any

from src.automator.app_automator import AppAutomator
from src.config.config_loader import ConfigLoader
from src.utils.exception_handler import handle_exception
from src.utils.logger import configure_logging


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
    automator = AppAutomator(loader)

    loop_cfg = config_dict.get("loop", {}) or {}
    loop_enabled = args.loop or loop_cfg.get("enabled", False)
    interval = args.interval or loop_cfg.get("interval", 300)
    max_iterations = args.max_iterations if args.max_iterations is not None else loop_cfg.get("max_iterations", 0)

    iteration = 0
    try:
        while True:
            iteration += 1
            logger.info("开始执行第 %s 次流程，dry_run=%s", iteration, args.dry_run)
            try:
                automator.start(dry_run=args.dry_run)
            finally:
                automator.stop()

            if not loop_enabled:
                break
            if max_iterations and iteration >= max_iterations:
                logger.info("已达到配置的最大循环次数 %s，结束执行。", max_iterations)
                break

            logger.info("等待 %s 秒后继续下一轮。", interval)
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("收到中断信号，准备退出。")
    except Exception as exc:  # pylint: disable=broad-except
        handle_exception(exc, logger)
        sys.exit(1)


def main() -> None:
    """程序入口。"""

    args = parse_arguments()
    loader = build_config_loader(args.config_file)
    run_automation(loader, args)


if __name__ == "__main__":
    main()
