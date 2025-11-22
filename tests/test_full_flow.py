"""完整流程快速测试。"""
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
        level=logging.DEBUG,  # 临时启用DEBUG以查看详细窗口信息
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/test_full_flow.log", encoding="utf-8")
        ]
    )


def main() -> None:
    """主测试函数。"""
    setup_logging()
    
    print("="*60)
    print("完整自动化流程测试（手动准备模式）")
    print("="*60)
    print("\n⚠️  操作说明（请按顺序完成）：")
    print("1. ✋ 手动启动应用（D:/software/CpzyrjCom.exe）")
    print("2. ✋ 手动点击'时时彩'标签")
    print("3. ✋ 手动点击'公式搜索'按钮")
    print("4. ✋ 手动配置参数（公式数量、期数、准确率等）")
    print("5. ⏸️  不要点击'开始搜索'，等待程序接管")
    print("\n准备完成后，按 Enter 键启动程序...")
    input()  # 等待用户按Enter
    
    print("\n正在执行自动化流程...\n")
    
    try:
        # 加载配置
        config_loader = ConfigLoader("config/config.json")
        
        # 创建自动化控制器
        automator = AppAutomator(config_loader)
        
        # 执行完整流程（只执行搜索和对比）
        automator.start(dry_run=False, use_desktop_automation=True)
        
        print("\n✅ 测试成功！")
        
        # 清理
        automator.stop()
        
    except Exception as exc:
        print(f"\n❌ 测试失败: {exc}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
