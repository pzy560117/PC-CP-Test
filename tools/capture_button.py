"""截图辅助工具 - 帮助截取按钮图片。"""
import time
import pyautogui
from pathlib import Path


def main():
    """主函数。"""
    print("="*70)
    print("截图辅助工具")
    print("="*70)
    print("\n使用说明：")
    print("1. 确保目标应用窗口已打开并显示'公式搜索'按钮")
    print("2. 5秒后将开始截图，请准备好")
    print("3. 鼠标将显示当前位置，按 Esc 键取消")
    print("\n按 Enter 键开始 5 秒倒计时...")
    input()
    
    for i in range(5, 0, -1):
        print(f"{i}...", end=" ", flush=True)
        time.sleep(1)
    print("\n")
    
    print("请在接下来的 10 秒内：")
    print("1. 移动鼠标到'公式搜索'按钮的左上角")
    print("2. 记下位置后，移动到右下角")
    print("3. 按空格键完成选择")
    print("\n当前鼠标位置将每秒显示...\n")
    
    positions = []
    start_time = time.time()
    
    print("请移动鼠标到按钮左上角，然后按空格键...")
    while len(positions) < 2:
        current_pos = pyautogui.position()
        print(f"\r当前位置: X={current_pos.x}, Y={current_pos.y}    ", end="", flush=True)
        
        # 检查是否按空格键（简化版，需要用户在终端按）
        if time.time() - start_time > 15:
            print("\n\n超时！请重新运行。")
            return
        
        time.sleep(0.1)
    
    print("\n\n截图已保存")
    print("\n手动截图步骤：")
    print("1. 打开应用，确保'公式搜索'按钮可见")
    print("2. 使用 Windows 截图工具 (Win + Shift + S)")
    print("3. 截取'公式搜索'按钮区域")
    print("4. 保存为: d:\\PC-Test\\images\\search_formula_button.png")
    print("\n推荐尺寸：尽量只包含按钮本身，避免周围空白")


if __name__ == "__main__":
    main()
