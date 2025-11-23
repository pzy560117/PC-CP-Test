"""环境检查脚本 - 验证新电脑部署是否正确。"""
import os
import sys
import subprocess
from pathlib import Path


def print_section(title: str) -> None:
    """打印章节标题。"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_python() -> bool:
    """检查 Python 版本。"""
    print("\n检查 Python 版本...")
    version = sys.version_info
    print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"  ⚠️  建议使用 Python 3.11 或更高版本（当前: {version.major}.{version.minor}）")
        return False
    return True


def check_pip() -> bool:
    """检查 pip 是否可用。"""
    print("\n检查 pip...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  ✓ {result.stdout.strip()}")
        return True
    except Exception as e:
        print(f"  ✗ pip 不可用: {e}")
        return False


def check_git() -> bool:
    """检查 Git 是否安装。"""
    print("\n检查 Git...")
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  ✓ {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("  ✗ Git 未安装")
        print("     下载地址: https://git-scm.com/download/win")
        return False
    except Exception as e:
        print(f"  ✗ Git 检查失败: {e}")
        return False


def check_tesseract() -> bool:
    """检查 Tesseract OCR 是否安装。"""
    print("\n检查 Tesseract OCR...")
    
    # 从配置文件读取路径
    config_path = Path("config/config.json")
    tesseract_cmd = None
    
    if config_path.exists():
        try:
            import json
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
                tesseract_cmd = config.get("search", {}).get("tesseract_cmd")
        except Exception as e:
            print(f"  ⚠️  读取配置文件失败: {e}")
    
    # 尝试配置路径
    if tesseract_cmd:
        tesseract_path = Path(tesseract_cmd.replace("/", "\\"))
        if tesseract_path.exists():
            try:
                result = subprocess.run(
                    [str(tesseract_path), "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                version_line = result.stdout.split('\n')[0]
                print(f"  ✓ {version_line}")
                print(f"     路径: {tesseract_path}")
                return True
            except Exception as e:
                print(f"  ✗ Tesseract 执行失败: {e}")
        else:
            print(f"  ✗ 配置的 Tesseract 路径不存在: {tesseract_path}")
    
    # 尝试系统 PATH
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version_line = result.stdout.split('\n')[0]
        print(f"  ✓ {version_line}")
        print("     (从系统 PATH 找到)")
        return True
    except FileNotFoundError:
        print("  ✗ Tesseract 未安装或未配置")
        print("     下载地址: https://github.com/UB-Mannheim/tesseract/wiki")
        print("     安装后请在 config/config.json 中配置 tesseract_cmd 路径")
        return False
    except Exception as e:
        print(f"  ✗ Tesseract 检查失败: {e}")
        return False


def check_dependencies() -> bool:
    """检查 Python 依赖包。"""
    print("\n检查 Python 依赖包...")
    
    required_packages = [
        "pywinauto",
        "pyautogui",
        "easyocr",
        "pytesseract",
        "Pillow",
        "requests",
        "supabase",
        "pymysql",
    ]
    
    all_installed = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (未安装)")
            all_installed = False
    
    if not all_installed:
        print("\n  运行以下命令安装缺失的依赖:")
        print("  pip install -r requirements.txt")
    
    return all_installed


def check_config() -> bool:
    """检查配置文件。"""
    print("\n检查配置文件...")
    
    config_path = Path("config/config.json")
    if not config_path.exists():
        print(f"  ✗ 配置文件不存在: {config_path}")
        return False
    
    print(f"  ✓ 配置文件存在: {config_path}")
    
    try:
        import json
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        
        # 检查关键配置
        app_config = config.get("target_app", {})
        executable_path = app_config.get("executable_path", "")
        
        if executable_path:
            exe_path = Path(executable_path)
            if exe_path.exists():
                print(f"  ✓ 目标应用路径存在: {executable_path}")
            else:
                print(f"  ⚠️  目标应用路径不存在: {executable_path}")
                print("     请在 config/config.json 中设置正确的 executable_path")
        else:
            print("  ⚠️  未配置目标应用路径 (target_app.executable_path)")
        
        return True
    except Exception as e:
        print(f"  ✗ 配置文件解析失败: {e}")
        return False


def check_directories() -> bool:
    """检查必要的目录。"""
    print("\n检查项目目录...")
    
    required_dirs = [
        "data",
        "data/results",
        "logs",
        "images",
        "src",
        "config",
        "docs",
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ✗ {dir_path}/ (不存在)")
            all_exist = False
    
    if not all_exist:
        print("\n  运行以下命令创建缺失的目录:")
        for dir_path in required_dirs:
            path = Path(dir_path)
            if not path.exists():
                print(f"  mkdir {dir_path}")
    
    return all_exist


def main() -> None:
    """主函数。"""
    print_section("环境检查工具 - 新电脑部署验证")
    print("\n本工具将检查项目运行所需的环境和依赖是否正确安装。")
    
    results = []
    
    # 执行各项检查
    results.append(("Python 版本", check_python()))
    results.append(("pip 工具", check_pip()))
    results.append(("Git 版本控制", check_git()))
    results.append(("Tesseract OCR", check_tesseract()))
    results.append(("Python 依赖包", check_dependencies()))
    results.append(("配置文件", check_config()))
    results.append(("项目目录", check_directories()))
    
    # 汇总结果
    print_section("检查结果汇总")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status:8} - {name}")
    
    print(f"\n  总计: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("\n  🎉 恭喜！所有检查都通过了，环境配置正确！")
        print("\n  下一步:")
        print("  1. 手动启动'奇趣腾讯分分彩'应用")
        print("  2. 手动打开'计划接口-奇趣腾讯分分彩'窗口")
        print("  3. 运行: python main.py --real-run")
    else:
        print("\n  ⚠️  部分检查未通过，请根据上述提示修复问题。")
        print("\n  详细部署指南:")
        print("  docs/deployment_guide.md")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
