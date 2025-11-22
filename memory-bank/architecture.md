# 项目架构文档

## 当前架构概述

本文档描述腾讯分分彩公式搜索自动化工具的当前架构，包括模块结构、类设计和接口关系。

## 项目目录结构

```
PC-Test/
├── main.py                     # 应用程序入口点
├── requirements.txt            # 项目依赖
├── README.md                   # 项目说明文档
├── CLAUDE.md                   # AI代理开发规则
├── config/                     # 配置文件目录
│   ├── settings.py            # 应用程序设置
│   └── config.json            # 配置文件
├── memory-bank/               # 项目记忆库
│   ├── game-design-document.md  # 项目设计文档
│   ├── tech-stack.md          # 技术栈文档
│   ├── implementation-plan.md  # 实施计划
│   ├── architecture.md        # 架构文档（本文件）
│   └── progress.md            # 进度跟踪
├── src/                       # 源代码目录
│   ├── __init__.py
│   ├── automator/             # 自动化模块
│   │   ├── __init__.py
│   │   ├── app_automator.py   # 主应用自动化类
│   │   ├── app_launcher.py    # 应用启动器
│   │   ├── navigator.py       # 界面导航器
│   │   ├── base_automator.py  # 自动化基类
│   │   ├── search_configurer.py # 搜索参数配置器
│   │   ├── search_executor.py # 搜索执行器
│   │   └── result_extractor.py # 结果提取器
│   ├── data/                  # 数据处理模块
│   │   ├── __init__.py
│   │   ├── models.py          # 数据模型
│   │   ├── storage.py         # 数据存储
│   │   └── analyzer.py        # 数据分析器
│   ├── api/                   # API接口模块
│   │   ├── __init__.py
│   │   └── data_api.py        # 数据API接口
│   ├── exception/             # 异常处理模块
│   │   ├── __init__.py
│   │   └── custom_exceptions.py # 自定义异常
│   └── utils/                 # 工具模块
│       ├── __init__.py
│       ├── logger.py          # 日志工具
│       └── exception_handler.py # 异常处理器
├── tests/                     # 测试目录
│   ├── __init__.py
│   ├── unit/                  # 单元测试
│   │   ├── __init__.py
│   │   ├── test_automator.py
│   │   ├── test_data.py
│   │   └── test_api.py
│   └── integration/           # 集成测试
│       ├── __init__.py
│       └── test_integration.py
├── logs/                      # 日志目录
└── data/                      # 数据目录
    ├── history/               # 历史数据
    └── results/               # 结果数据
```

## 核心模块设计

### 1. 应用程序入口 (main.py)

**职责**：应用程序的启动和初始化

**主要功能**：
- 解析命令行参数
- 初始化配置和日志
- 创建主应用实例
- 启动应用程序

**接口**：
- `parse_arguments()` - 解析命令行参数
- `initialize_app()` - 初始化应用程序
- `main()` - 主函数

### 2. 自动化模块 (src/automator/)

#### 2.1 AppAutomator (app_automator.py)

**职责**：主应用自动化控制器，协调各个自动化组件

**主要功能**：
- 初始化和管理各个自动化组件
- 控制自动化流程的执行
- 处理自动化过程中的异常
- 管理浏览器资源

**接口**：
- `__init__(config)` - 初始化自动化器
- `start()` - 启动自动化流程
- `stop()` - 停止自动化流程
- `restart()` - 重启自动化流程
- `cleanup()` - 清理资源

#### 2.2 AppLauncher (app_launcher.py)

**职责**：应用程序的启动和状态检测

**主要功能**：
- 启动目标应用程序
- 检测应用程序状态
- 处理启动异常

**接口**：
- `launch_app()` - 启动应用程序
- `is_app_running()` - 检测应用是否运行
- `wait_for_app_ready()` - 等待应用就绪
- `close_app()` - 关闭应用程序

#### 2.3 Navigator (navigator.py)

**职责**：应用程序界面导航

**主要功能**：
- 导航到指定界面
- 定位界面元素
- 执行基本导航操作

**接口**：
- `navigate_to_lottery()` - 导航到彩票界面
- `navigate_to_search()` - 导航到搜索界面
- `find_element()` - 查找界面元素
- `wait_for_element()` - 等待元素出现

#### 2.4 BaseAutomator (base_automator.py)

**职责**：提供基础自动化操作

**主要功能**：
- 执行基本UI操作（点击、输入等）
- 提供等待策略
- 处理操作异常

**接口**：
- `click_element()` - 点击元素
- `input_text()` - 输入文本
- `select_option()` - 选择选项
- `wait()` - 等待操作

#### 2.5 SearchConfigurer (search_configurer.py)

**职责**：配置搜索参数

**主要功能**：
- 设置搜索参数
- 验证参数设置
- 处理参数配置异常

**接口**：
- `configure_search()` - 配置搜索参数
- `set_formula_count()` - 设置公式数量
- `set_data_periods()` - 设置数据期数
- `verify_configuration()` - 验证配置

#### 2.6 SearchExecutor (search_executor.py)

**职责**：执行搜索操作

**主要功能**：
- 启动搜索
- 监控搜索状态
- 处理搜索异常

**接口**：
- `start_search()` - 开始搜索
- `stop_search()` - 停止搜索
- `clear_search()` - 清除搜索
- `get_search_status()` - 获取搜索状态

#### 2.7 ResultExtractor (result_extractor.py)

**职责**：提取搜索结果

**主要功能**：
- 定位结果表格
- 提取结果数据
- 格式化结果数据

**接口**：
- `extract_results()` - 提取结果
- `parse_result_table()` - 解析结果表格
- `get_top_results()` - 获取前N条结果
- `get_recommended_numbers()` - 获取推荐号码

### 3. 数据处理模块 (src/data/)

#### 3.1 数据模型 (models.py)

**职责**：定义数据模型

**主要功能**：
- 定义开奖结果数据模型
- 定义搜索参数数据模型
- 定义对比结果数据模型

**接口**：
- `LotteryResult` - 开奖结果模型
- `SearchParams` - 搜索参数模型
- `ComparisonResult` - 对比结果模型

#### 3.2 数据存储 (storage.py)

**职责**：数据存储和管理

**主要功能**：
- 存储历史数据
- 存储搜索结果
- 数据缓存管理

**接口**：
- `save_history_data()` - 保存历史数据
- `save_search_results()` - 保存搜索结果
- `load_history_data()` - 加载历史数据
- `clear_cache()` - 清除缓存

#### 3.3 数据分析器 (analyzer.py)

**职责**：数据对比分析

**主要功能**：
- 对比搜索结果与历史数据
- 生成对比报告
- 统计分析

**接口**：
- `compare_results()` - 对比结果
- `generate_report()` - 生成报告
- `calculate_statistics()` - 计算统计数据

### 4. API接口模块 (src/api/)

#### 4.1 数据API (data_api.py)

**职责**：历史数据获取API

**主要功能**：
- 获取历史开奖数据
- 获取指定日期数据
- API请求处理

**接口**：
- `get_history_data()` - 获取历史数据
- `get_data_by_date()` - 按日期获取数据
- `parse_api_response()` - 解析API响应

### 5. 异常处理模块 (src/exception/)

#### 5.1 自定义异常 (custom_exceptions.py)

**职责**：定义项目特定异常

**主要功能**：
- 定义基础异常类
- 定义特定功能异常类

**接口**：
- `AutomationException` - 基础自动化异常
- `NavigationException` - 导航异常
- `SearchException` - 搜索异常
- `DataException` - 数据异常
- `APIException` - API异常

### 6. 工具模块 (src/utils/)

#### 6.1 日志工具 (logger.py)

**职责**：日志记录

**主要功能**：
- 配置日志系统
- 提供日志记录接口
- 日志文件管理

**接口**：
- `get_logger()` - 获取日志器
- `setup_logging()` - 设置日志系统
- `rotate_logs()` - 轮转日志文件

#### 6.2 异常处理器 (exception_handler.py)

**职责**：全局异常处理

**主要功能**：
- 捕获和处理异常
- 异常日志记录
- 异常恢复策略

**接口**：
- `handle_exception()` - 处理异常
- `log_exception()` - 记录异常
- `recover_from_exception()` - 从异常恢复

## 模块间关系

```
main.py
  |
  v
AppAutomator
  |
  +-- AppLauncher
  +-- Navigator
  +-- BaseAutomator
  +-- SearchConfigurer
  +-- SearchExecutor
  +-- ResultExtractor
  |
  +-- Data Models (models.py)
  +-- Data Storage (storage.py)
  +-- Data Analyzer (analyzer.py)
  |
  +-- Data API (data_api.py)
  |
  +-- Custom Exceptions (custom_exceptions.py)
  +-- Exception Handler (exception_handler.py)
  |
  +-- Logger (logger.py)
```

## 数据流

1. **初始化阶段**：
   - main.py 解析参数，初始化配置
   - AppAutomator 创建并初始化各个组件

2. **自动化执行阶段**：
   - AppLauncher 启动应用程序
   - Navigator 导航到搜索界面
   - SearchConfigurer 配置搜索参数
   - SearchExecutor 执行搜索
   - ResultExtractor 提取结果

3. **数据处理阶段**：
   - Data API 获取历史数据
   - Data Analyzer 对比分析
   - Data Storage 存储结果

4. **异常处理阶段**：
   - Exception Handler 捕获和处理异常
   - Logger 记录日志

## 配置管理

配置文件 `config/config.json` 包含以下配置项：

```json
{
  "app": {
    "path": "应用程序路径",
    "timeout": 30
  },
  "search": {
    "formula_count": 10,
    "data_periods": 100
  },
  "api": {
    "base_url": "API基础URL",
    "timeout": 10
  },
  "logging": {
    "level": "INFO",
    "file": "logs/app.log",
    "max_size": "10MB",
    "backup_count": 5
  }
}
```

## 扩展点

1. **新的自动化操作**：通过扩展 BaseAutomator 添加新操作
2. **新的数据源**：通过扩展 Data API 添加新数据源
3. **新的分析功能**：通过扩展 Data Analyzer 添加新分析功能
4. **新的异常类型**：通过扩展 Custom Exceptions 添加新异常类型

---

**注意**：此架构文档将随着开发进度不断更新和完善。每次添加新功能或修改现有功能时，都应更新此文档以反映最新的架构状态。