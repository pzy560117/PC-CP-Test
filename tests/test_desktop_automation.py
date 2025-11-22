"""桌面自动化功能测试脚本。

使用说明：
1. 确保已安装所有依赖包：pip install -r requirements.txt
2. 确保目标应用（奇趣腾讯分分彩）已安装
3. 更新 config/config.json 中的 target_app.executable_path
4. 运行此测试脚本：python tests/test_desktop_automation.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.automator.app_automator import AppAutomator
from src.config.config_loader import ConfigLoader


def setup_logging() -> None:
    """配置日志输出。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/test_desktop_automation.log", encoding="utf-8")
        ]
    )


def test_window_connection() -> None:
    """测试1：测试窗口连接功能。"""
    print("\n" + "="*50)
    print("测试1：窗口连接功能")
    print("="*50)
    
    try:
        # 加载配置
        config_loader = ConfigLoader("config/config.json")
        
        # 创建自动化控制器
        automator = AppAutomator(config_loader)
        
        # 启动应用
        print("正在启动应用...")
        automator.app_launcher.launch()
        
        # 连接窗口
        print("正在连接窗口...")
        automator.window_manager.connect_to_window(timeout=30)
        
        # 激活窗口
        print("正在激活窗口...")
        automator.window_manager.activate_window()
        
        # 等待就绪
        print("等待窗口就绪...")
        automator.window_manager.wait_for_window_ready()
        
        print("✅ 窗口连接测试成功！")
        
        # 清理
        automator.stop()
        
    except Exception as exc:
        print(f"❌ 窗口连接测试失败: {exc}")
        raise


def test_search_configuration() -> None:
    """测试2：测试搜索参数配置功能。"""
    print("\n" + "="*50)
    print("测试2：搜索参数配置功能")
    print("="*50)
    
    try:
        # 加载配置
        config_loader = ConfigLoader("config/config.json")
        
        # 创建自动化控制器
        automator = AppAutomator(config_loader)
        
        # 启动应用并连接窗口
        print("正在启动应用...")
        automator.app_launcher.launch()
        automator.window_manager.connect_to_window(timeout=30)
        automator.window_manager.activate_window()
        automator.window_manager.wait_for_window_ready()
        
        # 初始化搜索配置器
        from src.automator.search_configurator import SearchConfigurator
        configurator = SearchConfigurator(automator.window_manager)
        
        # 配置搜索参数
        print("正在配置搜索参数...")
        configurator.configure_search_parameters(automator.search_parameters)
        
        print("✅ 搜索参数配置测试成功！")
        
        # 清理
        automator.stop()
        
    except Exception as exc:
        print(f"❌ 搜索参数配置测试失败: {exc}")
        raise


def test_full_automation_pipeline() -> None:
    """测试3：测试完整的自动化流程。"""
    print("\n" + "="*50)
    print("测试3：完整自动化流程")
    print("="*50)
    
    try:
        # 加载配置
        config_loader = ConfigLoader("config/config.json")
        
        # 创建自动化控制器
        automator = AppAutomator(config_loader)
        
        # 执行完整流程
        print("正在执行完整自动化流程...")
        automator.start(dry_run=False, use_desktop_automation=True)
        
        print("✅ 完整自动化流程测试成功！")
        
        # 清理
        automator.stop()
        
    except Exception as exc:
        print(f"❌ 完整自动化流程测试失败: {exc}")
        raise


def main() -> None:
    """主测试函数。"""
    setup_logging()
    
    print("="*50)
    print("桌面自动化功能测试")
    print("="*50)
    print("\n注意事项：")
    print("1. 确保目标应用已安装并配置正确")
    print("2. 测试过程中请勿操作鼠标和键盘")
    print("3. 测试将自动执行多个测试用例")
    print("\n按 Enter 键开始测试...")
    input()
    
    try:
        # 执行测试
        test_window_connection()
        
        print("\n按 Enter 键继续下一个测试...")
        input()
        
        test_search_configuration()
        
        print("\n按 Enter 键开始完整流程测试...")
        input()
        
        test_full_automation_pipeline()
        
        print("\n" + "="*50)
        print("所有测试完成！")
        print("="*50)
        
    except Exception as exc:
        print(f"\n测试失败: {exc}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
