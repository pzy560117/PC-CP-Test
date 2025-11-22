"""检查当前活动窗口的元素。"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper


def print_controls(window, depth=0, max_depth=4, max_children=100):
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


def search_controls_by_keywords(window, keywords):
    """搜索包含关键词的控件。"""
    found_controls = []
    
    try:
        all_controls = window.descendants()
        for ctrl in all_controls[:300]:  # 检查前300个
            try:
                text = ctrl.window_text()
                ctrl_type = ctrl.element_info.control_type
                auto_id = ctrl.element_info.automation_id
                
                for keyword in keywords:
                    if (text and keyword in text) or (auto_id and keyword in auto_id):
                        found_controls.append({
                            'type': ctrl_type,
                            'text': text,
                            'id': auto_id
                        })
                        break
            except:
                pass
    except:
        pass
    
    return found_controls


def main():
    """主函数。"""
    print("="*70)
    print("当前活动窗口元素检查工具")
    print("="*70)
    
    # 获取当前活动窗口
    desktop = Desktop(backend="uia")
    active_window = desktop.windows()[0]  # 获取第一个窗口
    
    print(f"\n当前窗口: {active_window.window_text()}")
    print("="*70)
    
    # 方法1：打印控件树
    print("\n方法1：控件树结构（4层）：")
    print("="*70)
    print_controls(active_window, max_depth=3, max_children=50)
    
    # 方法2：搜索特定控件
    print("\n" + "="*70)
    print("方法2：搜索相关控件：")
    print("="*70)
    
    keywords = ["搜索", "开始", "查询", "确定", "按钮", "Button", "公式", "期数", "个数", "准确"]
    found = search_controls_by_keywords(active_window, keywords)
    
    if found:
        for ctrl in found[:30]:  # 只显示前30个
            print(f"  [{ctrl['type']}] 文本='{ctrl['text']}' ID='{ctrl['id']}'")
    else:
        print("  未找到匹配的控件")
    
    # 方法3：列出所有Button控件
    print("\n" + "="*70)
    print("方法3：所有按钮控件：")
    print("="*70)
    try:
        buttons = active_window.descendants(control_type="Button")
        print(f"找到 {len(buttons)} 个按钮控件：")
        for i, btn in enumerate(buttons[:30]):  # 只显示前30个
            try:
                text = btn.window_text()
                auto_id = btn.element_info.automation_id
                print(f"  {i+1}. [Button] 文本='{text}' ID='{auto_id}'")
            except:
                pass
    except:
        print("  获取按钮失败")
    
    # 方法4：列出所有Edit控件（输入框）
    print("\n" + "="*70)
    print("方法4：所有输入框控件：")
    print("="*70)
    try:
        edits = active_window.descendants(control_type="Edit")
        print(f"找到 {len(edits)} 个输入框控件：")
        for i, edit in enumerate(edits[:30]):  # 只显示前30个
            try:
                text = edit.window_text()
                auto_id = edit.element_info.automation_id
                print(f"  {i+1}. [Edit] 文本='{text}' ID='{auto_id}'")
            except:
                pass
    except:
        print("  获取输入框失败")
    
    print("\n" + "="*70)
    print("检查完成")
    print("="*70)


if __name__ == "__main__":
    main()
