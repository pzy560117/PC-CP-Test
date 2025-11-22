"""主自动化控制器，统筹应用生命周期。"""
from __future__ import annotations

import logging
from typing import List, Optional

from src.api.data_api import LotteryApiClient
from src.automator.app_launcher import AppLauncher
from src.automator.navigator import Navigator
from src.automator.search_configurator import SearchConfigurator
from src.automator.search_executor import SearchExecutor
from src.automator.window_manager import WindowManager
from src.config.config_loader import ConfigLoader
from src.data.models import ComparisonResult, LotteryResult, SearchParameters
from src.data.processor import RecommendationProcessor
from src.data.result_storage import ComparisonRecorder, RecommendationRepository
from src.exception.custom_exceptions import AutomationException, DataProcessException


class AppAutomator:
    """协调启动、配置与监控的自动化核心控制器。"""

    def __init__(self, config_loader: ConfigLoader) -> None:
        """保存配置引用并初始化依赖组件。"""
        self._config_loader = config_loader
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 应用启动和窗口管理
        self.app_launcher = AppLauncher(config_loader.get("target_app", {}))
        self.window_manager = WindowManager(config_loader.get("target_app", {}))
        
        # 界面导航
        self.navigator: Optional[Navigator] = None
        
        # 搜索参数和执行器
        self.search_parameters = SearchParameters.from_dict(config_loader.get("search", {}))
        self.search_configurator: Optional[SearchConfigurator] = None
        self.search_executor: Optional[SearchExecutor] = None
        
        # API 客户端
        self.lottery_client = LotteryApiClient(config_loader.get("api", {}))
        
        # 推荐数据管理
        self._recommendation_cfg = config_loader.get("recommendation", {}) or {}
        self._recommendation_limit = int(self._recommendation_cfg.get("max_records", self.search_parameters.max_results))
        self.recommendation_repository = self._build_recommendation_repository()
        
        # 结果记录
        results_dir = config_loader.get("data.results_path", "./data/results")
        history_file = self._recommendation_cfg.get("history_filename", "comparison_history.jsonl")
        self.comparison_recorder = ComparisonRecorder(results_dir, history_file)
        
        self._running = False

    def start(self, dry_run: bool = True, use_desktop_automation: bool = True) -> None:
        """执行一次流程校验，必要时启动目标应用。
        
        Args:
            dry_run: 是否为干跑模式
            use_desktop_automation: 是否使用桌面自动化（True=从桌面应用搜索，False=从文件读取推荐）
        """
        if self._running:
            self.logger.info("自动化流程已在运行状态，无需重复启动。")
            return

        self.logger.info("开始自动化流程，dry_run=%s, use_desktop_automation=%s", dry_run, use_desktop_automation)
        self._running = True

        try:
            self._log_configuration_snapshot()
            
            if not dry_run:
                # 检查是否跳过应用启动
                app_config = self._config_loader.get("target_app", {})
                skip_launch = app_config.get("skip_app_launch", False)
                
                if skip_launch:
                    self.logger.info("⏩ 跳过应用启动（用户已手动启动应用）")
                else:
                    # 启动目标应用
                    self.app_launcher.launch()
                    self.logger.info("目标应用启动完成")
                
                if use_desktop_automation:
                    # 桌面自动化流程
                    self._execute_desktop_automation_pipeline()
                else:
                    # 从文件读取推荐流程
                    self._execute_recommendation_pipeline()
            else:
                self.logger.info("干跑模式下仅校验配置，未尝试实际操作界面。")
                if use_desktop_automation:
                    self.logger.info("将使用桌面自动化模式")
                else:
                    self._execute_recommendation_pipeline()
                    
        except AutomationException:
            self._running = False
            raise
        except Exception as exc:  # pylint: disable=broad-except
            self._running = False
            raise AutomationException("自动化流程启动失败") from exc

    def stop(self) -> None:
        """终止自动化流程并释放资源。"""
        if not self._running:
            self.logger.info("自动化流程未运行，无需停止。")
            return

        self.logger.info("即将停止自动化流程。")
        self.app_launcher.terminate()
        self._running = False

    def _log_configuration_snapshot(self) -> None:
        """输出关键配置快照，便于排障与稽核。"""
        params = self.search_parameters
        self.logger.info(
            "搜索参数：公式=%s，数据期数=%s，定码=%s，计划周期=%s，最低准确率=%s%%",
            params.formula_count,
            params.data_periods,
            params.fixed_code_count,
            params.plan_cycle,
            params.min_accuracy,
        )
        self.logger.info("最大结果条数：%s", params.max_results)

    def _execute_desktop_automation_pipeline(self) -> None:
        """执行桌面自动化流程：（可选连接窗口和导航）->执行搜索->提取结果->对比分析。"""
        try:
            # 读取配置
            app_config = self._config_loader.get("target_app", {})
            skip_launch = app_config.get("skip_app_launch", False)
            skip_navigation = app_config.get("skip_navigation", False)
            skip_config = app_config.get("skip_parameter_config", False)
            
            # 1. 连接到应用窗口（必需，即使手动启动也要连接）
            self.logger.info("步骤1: 连接到应用窗口...")
            self.window_manager.connect_to_window()
            
            # 尝试激活窗口（可选，失败不影响流程）
            try:
                self.window_manager.activate_window()
            except Exception as e:
                self.logger.warning("激活窗口失败: %s，继续执行", e)
            
            # 等待窗口就绪
            try:
                self.window_manager.wait_for_window_ready()
            except Exception as e:
                self.logger.warning("等待窗口就绪失败: %s，继续执行", e)
            
            # 2. 初始化搜索组件
            self.logger.info("步骤2: 初始化搜索组件...")
            self.search_configurator = SearchConfigurator(self.window_manager)
            self.search_executor = SearchExecutor(
                self.window_manager,
                self._config_loader.get("search", {})
            )
            
            # 3. 导航到搜索公式界面（可选）
            if skip_navigation:
                self.logger.info("步骤3: ⏩ 跳过导航（用户已手动导航到搜索界面）")
            else:
                self.logger.info("步骤3: 导航到搜索公式界面...")
                if not self.navigator:
                    self.navigator = Navigator(self.window_manager, app_config)
                self.navigator.navigate_to_search_formula()
                self.navigator.wait_for_interface_ready()
            
            # 4. 配置搜索参数（可选）
            if skip_config:
                self.logger.info("步骤4: ⏩ 跳过参数配置（用户已手动配置参数）")
            else:
                self.logger.info("步骤4: 配置搜索参数...")
                self.search_configurator.configure_search_parameters(self.search_parameters)
            
            # 5. 执行搜索（核心功能）
            self.logger.info("步骤5: 🔍 执行搜索...")
            self.search_executor.execute_search()
            
            # 6. 提取搜索结果
            self.logger.info("步骤6: 提取搜索结果...")
            recommended_sets = self.search_executor.extract_top_results(
                max_results=self.search_parameters.max_results
            )
            
            if not recommended_sets:
                raise AutomationException("未能提取到任何搜索结果")
            
            self.logger.info("成功提取 %d 条推荐号码", len(recommended_sets))
            
            # 7. 获取开奖数据并对比（可选）
            self.logger.info("步骤7: 获取开奖数据并对比...")
            try:
                lottery_result = self.lottery_client.fetch_latest_result()
                comparisons = self._build_comparisons(recommended_sets, lottery_result)
                
                # 8. 记录结果
                self.logger.info("步骤8: 记录对比结果...")
                self._log_comparison_details(lottery_result, comparisons)
                self.comparison_recorder.append_batch(lottery_result, comparisons)
            except Exception as e:
                self.logger.warning("⚠️ 获取开奖数据失败: %s", e)
                self.logger.info("已提取推荐号码，跳过对比环节")
                # 只记录提取到的推荐号码
                for idx, nums in enumerate(recommended_sets, 1):
                    self.logger.info("推荐 #%d: %s", idx, nums)
            
            self.logger.info("✅ 桌面自动化流程执行完成")
            
        except Exception as exc:
            raise AutomationException("桌面自动化流程执行失败") from exc

    def _build_recommendation_repository(self) -> RecommendationRepository | None:
        """根据配置创建推荐数据仓库。"""

        source_file = str(self._recommendation_cfg.get("source_file", "")).strip()
        if not source_file:
            self.logger.warning("尚未配置 recommendation.source_file，无法执行推荐号码比对。")
            return None
        encoding = self._recommendation_cfg.get("encoding", "utf-8")
        return RecommendationRepository(source_file, encoding)

    def _execute_recommendation_pipeline(self) -> None:
        """调度推荐号码与开奖数据的对比流程。"""

        if not self.recommendation_repository:
            raise AutomationException("请配置 recommendation.source_file 以启用推荐号码比对流程。")

        recommended_sets = self._load_recommendations()
        lottery_result = self.lottery_client.fetch_latest_result()
        comparisons = self._build_comparisons(recommended_sets, lottery_result)
        self._log_comparison_details(lottery_result, comparisons)
        self.comparison_recorder.append_batch(lottery_result, comparisons)

    def _load_recommendations(self) -> List[List[int]]:
        """读取推荐号码文本并转换为数组。"""

        raw_list = self.recommendation_repository.load_raw(limit=self._recommendation_limit)
        return RecommendationProcessor.process_batch(raw_list)

    def _build_comparisons(
        self, recommendations: List[List[int]], lottery_result: LotteryResult
    ) -> List[ComparisonResult]:
        """生成每条推荐与开奖号码的对比结果。"""

        lottery_numbers = lottery_result.numbers
        comparisons: List[ComparisonResult] = []
        for recommended in recommendations:
            comparisons.append(RecommendationProcessor.build_comparison_result(recommended, lottery_numbers))
        if not comparisons:
            raise DataProcessException("未能解析任何推荐号码，请检查源文件内容。")
        return comparisons

    def _log_comparison_details(self, lottery_result: LotteryResult, comparisons: List[ComparisonResult]) -> None:
        """输出推荐号码与开奖号码比对的详细日志。"""

        self.logger.info(
            "最新开奖期号：%s，开奖号码：%s，开奖时间：%s",
            lottery_result.period,
            lottery_result.numbers,
            lottery_result.open_time,
        )
        hit_count = 0
        for idx, item in enumerate(comparisons, start=1):
            status = "命中" if item.is_hit else "未命中"
            if item.is_hit:
                hit_count += 1
            self.logger.info(
                "推荐 #%s：%s -> %s，命中号码：%s",
                idx,
                item.recommended,
                status,
                item.hits or "-",
            )
        self.logger.info("本期共 %s 条推荐，命中 %s 条。", len(comparisons), hit_count)

    @property
    def config_loader(self) -> ConfigLoader:
        """返回配置加载器实例供外部查询使用。"""
        return self._config_loader

    @property
    def is_running(self) -> bool:
        """指示自动化流程当前是否处于运行状态。"""
        return self._running
