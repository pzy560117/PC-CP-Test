"""UI 元素检查工具 - 列出指定窗口的所有控件。"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.automator.window_manager import WindowManager
from src.config.config_loader import ConfigLoader


def print_controls(window, depth=0, max_depth=5, max_children=500):
    """递归打印控件信息。"""
    if depth > max_depth:
        return
    
    try:
        indent = "  " * depth
        control_type = window.element_info.control_type
        name = window.window_text()
        auto_id = window.element_info.automation_id
        class_name = window.class_name()
        
        # 打印控件信息
        info = f"{indent}[{control_type}]"
        if name:
            info += f" 文本='{name}'"
        if auto_id:
            info += f" ID='{auto_id}'"
        if class_name and class_name != control_type:
            info += f" Class='{class_name}'"
        
        print(info)
        
        # 递归打印子控件
        if depth < max_depth:
            try:
                children = window.children()
                for i, child in enumerate(children[:max_children]):
                    print_controls(child, depth + 1, max_depth, max_children)
                    if i >= max_children - 1 and len(children) > max_children:
                        print(f"{indent}  ... 还有 {len(children) - max_children} 个子控件")
                        break
            except:
                pass
                
    except Exception as e:
        pass


def main():
    """主函数。"""
    print("="*70)
    print("UI 元素检查工具")
    print("="*70)
    
    # 加载配置
    config_loader = ConfigLoader("config/config.json")
    window_manager = WindowManager(config_loader.get("target_app", {}))
    
    # 连接窗口
    print("\n正在连接窗口...")
    window_manager.connect_to_window(timeout=30)
    print("✅ 窗口连接成功\n")
    
    main_window = window_manager.main_window
    
    # 方法1：使用自定义树形打印
    print("="*70)
    print("方法1：窗口控件树结构（最多显示5层）：")
    print("="*70)
    print_controls(main_window, max_depth=4, max_children=100)
    
    # 方法2：使用 pywinauto 内置方法
    print("\n" + "="*70)
    print("方法2：pywinauto 详细控件标识符：")
    print("="*70)
    try:
        main_window.print_control_identifiers(depth=4, filename=None)
    except Exception as e:
        print(f"打印失败: {e}")
    
    # 方法3：搜索包含特定文本的控件
    print("\n" + "="*70)
    print("方法3：搜索包含'搜索'或'公式'的控件：")
    print("="*70)
    search_keywords = ["搜索", "公式", "查询", "开始"]
    all_controls = main_window.descendants()
    found_controls = []
    for ctrl in all_controls[:200]:  # 只检查前200个
        try:
            text = ctrl.window_text()
            ctrl_type = ctrl.element_info.control_type
            auto_id = ctrl.element_info.automation_id
            
            for keyword in search_keywords:
                if keyword in text or keyword in auto_id:
                    found_controls.append(f"[{ctrl_type}] 文本='{text}' ID='{auto_id}'")
                    break
        except:
            pass
    
    for ctrl_info in found_controls:
        print(f"  {ctrl_info}")
    
    if not found_controls:
        print("  未找到匹配的控件")
    
    print("\n" + "="*70)
    print("提示：")
    print("- 以管理员身份运行此工具可能会看到更多控件")
    print("- 某些应用使用自定义渲染，UI Automation 无法识别")
    print("="*70)


if __name__ == "__main__":
    main()
