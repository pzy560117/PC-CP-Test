"""
腾讯分分彩公式搜索自动化工具 - 应用程序设置
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class Settings:
    """应用程序设置管理类"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化设置
        
        Args:
            config_file: 配置文件路径，默认为 config/config.json
        """
        self.config_file = config_file or os.path.join(os.path.dirname(__file__), 'config.json')
        self._config = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except FileNotFoundError:
            logging.error(f"配置文件未找到: {self.config_file}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"配置文件格式错误: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'browser.type'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
            raise
    
    @property
    def app_name(self) -> str:
        """获取应用名称"""
        return self.get('app.name', '腾讯分分彩公式搜索自动化工具')
    
    @property
    def app_version(self) -> str:
        """获取应用版本"""
        return self.get('app.version', '1.0.0')
    
    @property
    def browser_type(self) -> str:
        """获取浏览器类型"""
        return self.get('browser.type', 'chrome')
    
    @property
    def browser_headless(self) -> bool:
        """获取是否无头模式"""
        return self.get('browser.headless', False)
    
    @property
    def browser_window_size(self) -> Dict[str, int]:
        """获取浏览器窗口大小"""
        return self.get('browser.window_size', {'width': 1280, 'height': 720})
    
    @property
    def page_load_timeout(self) -> int:
        """获取页面加载超时时间"""
        return self.get('browser.page_load_timeout', 30)
    
    @property
    def element_wait_timeout(self) -> int:
        """获取元素等待超时时间"""
        return self.get('browser.element_wait_timeout', 10)
    
    @property
    def implicit_wait(self) -> int:
        """获取隐式等待时间"""
        return self.get('browser.implicit_wait', 5)
    
    @property
    def target_app_name(self) -> str:
        """获取目标应用名称"""
        return self.get('target_app.name', '奇趣腾讯分分彩')
    
    @property
    def target_app_executable_path(self) -> str:
        """获取目标应用可执行文件路径"""
        return self.get('target_app.executable_path', '')
    
    @property
    def target_app_window_title(self) -> str:
        """获取目标应用窗口标题"""
        return self.get('target_app.window_title', '奇趣腾讯分分彩')
    
    @property
    def target_app_launch_timeout(self) -> int:
        """获取目标应用启动超时时间"""
        return self.get('target_app.launch_timeout', 30)
    
    @property
    def formula_count(self) -> int:
        """获取公式数量"""
        return self.get('search.formula_count', 10)
    
    @property
    def data_periods(self) -> int:
        """获取数据期数"""
        return self.get('search.data_periods', 100)
    
    @property
    def search_timeout(self) -> int:
        """获取搜索超时时间"""
        return self.get('search.search_timeout', 300)
    
    @property
    def result_wait_timeout(self) -> int:
        """获取结果等待超时时间"""
        return self.get('search.result_wait_timeout', 60)
    
    @property
    def max_results(self) -> int:
        """获取最大结果数"""
        return self.get('search.max_results', 5)
    
    @property
    def api_base_url(self) -> str:
        """获取API基础URL"""
        return self.get('api.base_url', 'https://api.example.com')
    
    @property
    def api_timeout(self) -> int:
        """获取API超时时间"""
        return self.get('api.timeout', 10)
    
    @property
    def data_storage_path(self) -> str:
        """获取数据存储路径"""
        return self.get('data.storage_path', './data')
    
    @property
    def data_history_path(self) -> str:
        """获取历史数据路径"""
        return self.get('data.history_path', './data/history')
    
    @property
    def data_results_path(self) -> str:
        """获取结果数据路径"""
        return self.get('data.results_path', './data/results')
    
    @property
    def log_level(self) -> str:
        """获取日志级别"""
        return self.get('logging.level', 'INFO')
    
    @property
    def log_file(self) -> str:
        """获取日志文件路径"""
        return self.get('logging.file', './logs/app.log')
    
    @property
    def log_max_size(self) -> str:
        """获取日志文件最大大小"""
        return self.get('logging.max_size', '10MB')
    
    @property
    def log_backup_count(self) -> int:
        """获取日志备份数量"""
        return self.get('logging.backup_count', 5)
    
    @property
    def loop_enabled(self) -> bool:
        """获取是否启用循环执行"""
        return self.get('loop.enabled', True)
    
    @property
    def loop_interval(self) -> int:
        """获取循环执行间隔（秒）"""
        return self.get('loop.interval', 300)
    
    @property
    def max_iterations(self) -> int:
        """获取最大迭代次数，0表示无限制"""
        return self.get('loop.max_iterations', 0)
    
    def ensure_directories(self) -> None:
        """确保必要的目录存在"""
        directories = [
            self.data_storage_path,
            self.data_history_path,
            self.data_results_path,
            os.path.dirname(self.log_file)
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


# 全局设置实例
settings = Settings()