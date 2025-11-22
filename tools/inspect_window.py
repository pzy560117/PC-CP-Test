"""窗口结构调试工具。"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.automator.window_manager import WindowManager
from src.config.config_loader import ConfigLoader


def print_window_structure(window, indent=0):
    """递归打印窗口结构。"""
    try:
        control_type = window.element_info.control_type
        text = window.window_text()
        class_name = window.class_name()
        auto_id = window.element_info.automation_id
        
        prefix = "  " * indent
        print(f"{prefix}[{control_type}] '{text}' (class={class_name}, id={auto_id})")
        
        # 只打印前2层，避免太深
        if indent < 2:
            children = window.children()
            for child in children[:20]:  # 只打印前20个子元素
                print_window_structure(child, indent + 1)
    except Exception as e:
        pass


def main():
    """主函数。"""
    print("="*60)
    print("窗口结构调试工具")
    print("="*60)
    
    # 加载配置
    config_loader = ConfigLoader("config/config.json")
    window_manager = WindowManager(config_loader.get("target_app", {}))
    
    # 连接窗口
    print("\n正在连接窗口...")
    window_manager.connect_to_window(timeout=30)
    print("✅ 窗口连接成功")
    
    # 打印窗口结构
    print("\n窗口结构：")
    print_window_structure(window_manager.main_window)
    
    print("\n" + "="*60)
    print("调试完成")


if __name__ == "__main__":
    main()
