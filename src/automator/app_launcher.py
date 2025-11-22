"""桌面应用启动器。"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from src.exception.custom_exceptions import AutomationException, ConfigException


class AppLauncher:
    """负责启动、检测与终止桌面应用。"""

    def __init__(self, app_config: Dict[str, Any]) -> None:
        """保存配置并准备日志句柄。"""
        self._config = app_config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._process: Optional[subprocess.Popen[Any]] = None

    def launch(self) -> None:
        """根据配置启动目标应用。"""
        if self.is_running:
            self.logger.info("目标应用已在运行状态，无需重复启动。")
            return

        executable = self._resolve_executable()
        self.logger.info("正在启动目标应用: %s", executable)
        try:
            self._process = subprocess.Popen(
                [executable],
                cwd=Path(executable).parent,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0,
            )
        except OSError as exc:
            raise AutomationException(f"无法启动目标应用: {executable}") from exc

        self._wait_for_ready()

    def terminate(self) -> None:
        """结束已启动的目标应用。"""
        if not self._process:
            return

        if self._process.poll() is None:
            self.logger.info("尝试终止目标应用进程。")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning("应用未及时退出，尝试强制结束。")
                self._process.kill()
        self._process = None

    def _wait_for_ready(self) -> None:
        """等待应用进入就绪状态。"""
        timeout = int(self._config.get("launch_timeout", 30))
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._process and self._process.poll() is not None:
                raise AutomationException("目标应用启动后立即退出，请检查安装状态。")
            time.sleep(1)
        self.logger.info("应用启动等待完成，后续将进行界面导航。")

    def _resolve_executable(self) -> str:
        """校验并返回应用可执行文件路径。"""
        executable = self._config.get("executable_path", "").strip()
        if not executable:
            raise ConfigException("配置项 target_app.executable_path 不能为空。")
        path = Path(executable)
        if not path.exists():
            raise ConfigException(f"目标应用路径不存在: {executable}")
        return str(path)

    @property
    def is_running(self) -> bool:
        """判断当前是否已启动目标应用。"""
        return bool(self._process and self._process.poll() is None)
