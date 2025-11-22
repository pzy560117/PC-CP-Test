# 桌面自动化功能配置指南

## 概述

本文档介绍如何配置和使用项目的桌面自动化功能。该功能使用 pywinauto 和 pyautogui 实现对 Windows 桌面应用的自动化控制。

## 前置要求

1. **操作系统**：Windows 10/11
2. **Python版本**：3.8 或更高
3. **目标应用**：奇趣腾讯分分彩桌面应用程序
4. **依赖包**：已安装 `requirements.txt` 中的所有依赖

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包：
- `pywinauto==0.6.8`：Windows UI 自动化框架
- `pyautogui==0.9.54`：鼠标键盘控制库

## 配置步骤

### 1. 配置目标应用路径

编辑 `config/config.json` 文件，设置目标应用的可执行文件路径：

```json
{
  "target_app": {
    "name": "奇趣腾讯分分彩",
    "executable_path": "C:\\Program Files\\QiQuApp\\app.exe",
    "window_title": "奇趣腾讯分分彩",
    "launch_timeout": 30
  }
}
```

**配置项说明**：
- `executable_path`：目标应用的完整路径（必填）
- `window_title`：应用窗口标题，用于查找和识别窗口（必填）
- `launch_timeout`：应用启动超时时间（秒）

### 2. 配置搜索参数

```json
{
  "search": {
    "formula_count": 100,
    "data_periods": 200,
    "fixed_code_count": 5,
    "plan_cycle": 1,
    "min_accuracy": 57,
    "search_timeout": 300,
    "result_wait_timeout": 60,
    "max_results": 5
  }
}
```

**参数说明**：
- `formula_count`：搜索公式数量
- `data_periods`：数据期数
- `fixed_code_count`：定码个数
- `plan_cycle`：计划周期
- `min_accuracy`：最低准确率（%）
- `search_timeout`：搜索超时时间（秒）
- `max_results`：提取的最大结果数

### 3. 配置 API 接口

```json
{
  "api": {
    "base_url": "https://kjapi.com",
    "timeout": 10
  }
}
```

## 使用方法

### 方式一：使用测试脚本

运行测试脚本验证配置：

```bash
python tests/test_desktop_automation.py
```

测试脚本将执行以下测试：
1. 窗口连接测试
2. 搜索参数配置测试
3. 完整自动化流程测试

### 方式二：编程方式使用

```python
from src.automator.app_automator import AppAutomator
from src.config.config_loader import ConfigLoader

# 加载配置
config_loader = ConfigLoader("config/config.json")

# 创建自动化控制器
automator = AppAutomator(config_loader)

# 启动桌面自动化流程
automator.start(dry_run=False, use_desktop_automation=True)

# 停止
automator.stop()
```

### 方式三：主程序入口

```bash
python main.py
```

## 功能模块说明

### WindowManager（窗口管理器）

负责查找、连接和管理桌面应用窗口。

**主要功能**：
- `connect_to_window()`：连接到目标窗口
- `activate_window()`：激活并前置窗口
- `find_control()`：查找窗口中的控件
- `wait_for_window_ready()`：等待窗口就绪

### SearchConfigurator（搜索配置器）

负责配置搜索界面的各项参数。

**主要功能**：
- `configure_search_parameters()`：配置搜索参数
- `clear_filters()`：清除过滤条件

### SearchExecutor（搜索执行器）

负责执行搜索和提取结果。

**主要功能**：
- `execute_search()`：执行搜索
- `extract_top_results()`：提取前N条结果

## 工作流程

完整的桌面自动化流程包括以下步骤：

1. **启动应用**：通过 AppLauncher 启动目标桌面应用
2. **连接窗口**：使用 WindowManager 查找并连接到应用窗口
3. **激活窗口**：将窗口置于前台
4. **配置参数**：使用 SearchConfigurator 设置搜索条件
5. **执行搜索**：使用 SearchExecutor 执行搜索操作
6. **提取结果**：从结果表格中提取推荐号码
7. **数据对比**：调用 API 获取开奖数据并进行对比
8. **记录结果**：保存对比结果到文件

## 故障排除

### 问题1：找不到窗口

**症状**：提示"在 XX 秒内未找到窗口"

**解决方法**：
1. 检查 `window_title` 配置是否与实际窗口标题匹配
2. 增加 `launch_timeout` 时间
3. 手动启动应用，确认窗口标题

### 问题2：控件定位失败

**症状**：提示"未找到控件"

**解决方法**：
1. 确保应用界面完全加载
2. 检查应用版本是否与预期一致
3. 使用 Windows 自带的 Inspect 工具查看控件属性

### 问题3：搜索超时

**症状**：搜索在规定时间内未完成

**解决方法**：
1. 增加 `search_timeout` 配置值
2. 检查搜索参数是否合理
3. 确认应用网络连接正常

### 问题4：结果提取失败

**症状**：无法从表格中提取数据

**解决方法**：
1. 确认搜索已成功完成
2. 检查表格是否有数据
3. 使用调试模式查看表格结构

## 注意事项

1. **不要手动操作**：自动化运行期间，请勿移动鼠标或按键盘
2. **单实例运行**：确保只有一个目标应用实例在运行
3. **窗口可见性**：应用窗口需要可见（非最小化）
4. **权限要求**：确保程序有足够权限访问目标应用
5. **屏幕分辨率**：建议使用标准分辨率（1920x1080 或 1280x720）

## 调试技巧

### 启用详细日志

在 `config/config.json` 中设置日志级别为 DEBUG：

```json
{
  "logging": {
    "level": "DEBUG",
    "modules": {
      "automator": "DEBUG"
    }
  }
}
```

### 使用断点调试

在关键位置添加断点：

```python
import pdb; pdb.set_trace()
```

### 查看窗口结构

使用 pywinauto 的 print_control_identifiers 方法：

```python
automator.window_manager.main_window.print_control_identifiers()
```

## 性能优化

1. **减少等待时间**：合理设置超时参数
2. **复用窗口连接**：避免重复连接窗口
3. **批量操作**：合并多个控件操作
4. **异常处理**：添加重试机制

## 扩展开发

### 添加新的控件操作

在 `WindowManager` 中添加新方法：

```python
def click_button(self, button_text: str) -> None:
    """点击指定文本的按钮。"""
    button = self.find_control("Button", title=button_text)
    button.click_input()
```

### 自定义搜索策略

继承 `SearchConfigurator` 并覆盖方法：

```python
class CustomSearchConfigurator(SearchConfigurator):
    def configure_advanced_filters(self) -> None:
        """配置高级过滤条件。"""
        pass
```

## 参考资源

- [pywinauto 官方文档](https://pywinauto.readthedocs.io/)
- [pyautogui 官方文档](https://pyautogui.readthedocs.io/)
- [Windows UI Automation](https://docs.microsoft.com/en-us/windows/win32/winauto/entry-uiauto-win32)

## 版本历史

- **v1.1.0** (2025-11-22)：初始版本，实现基础桌面自动化功能
