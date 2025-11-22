# 腾讯分分彩公式搜索自动化工具 - 技术栈文档

## 核心技术栈

### 编程语言
- **Python 3.8+**：主要编程语言，提供丰富的库支持和自动化能力

### 界面自动化
- **PyAutoGUI**：用于屏幕截图、图像识别和鼠标键盘操作
- **Pywinauto**：用于Windows应用程序的自动化操作，提供更稳定的元素定位
- **OpenCV-Python**（可选）：用于高级图像识别和处理

### 网络请求
- **Requests**：用于HTTP请求，处理API调用
- **urllib3**：底层HTTP库，提供连接池和重试机制

### 数据处理
- **Python标准库**：
  - `json`：JSON数据解析
  - `re`：正则表达式处理
  - `datetime`：日期时间处理
  - `collections`：高效数据结构
- **NumPy**（可选）：用于高效数值计算和数组操作

### 配置管理
- **configparser**：INI格式配置文件处理
- **PyYAML**（可选）：YAML格式配置文件处理

### 日志记录
- **logging**：Python标准日志模块
- **loguru**（可选）：更简单易用的日志库

### 测试框架
- **unittest**：Python标准测试框架
- **pytest**（可选）：更强大的测试框架

## 项目结构

```
txffc-automation/
├── src/                          # 源代码目录
│   ├── automation/               # 自动化模块
│   │   ├── __init__.py
│   │   ├── AppLauncher.py        # 应用启动器
│   │   ├── Navigator.py          # 界面导航器
│   │   ├── BaseAutomator.py      # 自动化基类
│   │   ├── SearchConfigurer.py   # 搜索参数配置器
│   │   ├── SearchExecutor.py     # 搜索执行器
│   │   ├── ResultExtractor.py    # 结果提取器
│   │   └── LoopExecutor.py       # 循环执行器
│   ├── api/                      # API调用模块
│   │   ├── __init__.py
│   │   └── ApiCaller.py          # API调用器
│   ├── data/                     # 数据处理模块
│   │   ├── __init__.py
│   │   ├── DataProcessor.py      # 数据处理器
│   │   ├── LotteryDataProcessor.py # 开奖数据处理器
│   │   └── DataComparator.py     # 数据对比器
│   ├── config/                   # 配置管理模块
│   │   ├── __init__.py
│   │   ├── ConfigLoader.py       # 配置加载器
│   │   └── LogConfig.py          # 日志配置
│   ├── utils/                    # 工具类模块
│   │   ├── __init__.py
│   │   ├── Logger.py             # 日志工具
│   │   └── ExceptionHandler.py  # 异常处理器
│   └── exception/                # 异常类模块
│       ├── __init__.py
│       ├── AutomationException.py
│       ├── InterfaceNotFoundException.py
│       ├── APICallException.py
│       └── DataProcessException.py
├── tests/                        # 测试目录
│   ├── __init__.py
│   ├── test_automation.py
│   ├── test_api.py
│   └── test_data.py
├── logs/                         # 日志目录
├── config/                       # 配置文件目录
│   ├── config.json               # 主配置文件
│   └── logging.conf              # 日志配置文件
├── docs/                         # 文档目录
│   └── 链接.md                   # API链接文档
├── requirements.txt              # 依赖文件
├── main.py                       # 主程序入口
└── README.md                     # 项目说明
```

## 开发环境

### 操作系统
- **Windows 10/11**：主要运行环境，支持桌面应用自动化

### 开发工具
- **IDE**：PyCharm / VSCode
- **版本控制**：Git
- **包管理**：pip / conda

### 运行环境
- **Python解释器**：Python 3.8+
- **依赖管理**：虚拟环境（venv / conda env）

## 关键依赖包

### requirements.txt 内容
```
pyautogui>=0.9.54
pywinauto>=0.6.8
requests>=2.28.0
opencv-python>=4.6.0
numpy>=1.21.0
pyyaml>=6.0
loguru>=0.6.0
pytest>=7.0.0
```

## 配置管理

### 配置文件结构
- **config.json**：主配置文件，包含应用参数、API设置等
- **logging.conf**：日志配置文件，定义日志级别、格式和输出

### 环境变量
- `TXFFC_ENV`：运行环境（dev/test/prod）
- `TXFFC_LOG_LEVEL`：日志级别（DEBUG/INFO/WARNING/ERROR）
- `TXFFC_CONFIG_PATH`：配置文件路径（可选）

## 部署考虑

### 打包工具
- **PyInstaller**：将Python应用打包为独立可执行文件
- **cx_Freeze**：替代打包工具

### 分发方式
- **独立可执行文件**：无需Python环境，直接运行
- **源码包**：需要Python环境和依赖安装

## 性能优化

### 关键优化点
- **图像识别优化**：使用模板匹配和区域搜索减少计算量
- **API调用优化**：实现缓存和重试机制，减少不必要的请求
- **数据处理优化**：使用高效的数据结构和算法

### 资源管理
- **内存管理**：及时释放大对象，避免内存泄漏
- **CPU使用**：优化循环和计算密集型操作
- **网络资源**：控制并发请求数，避免过度消耗

## 安全考虑

### API安全
- **请求频率控制**：添加请求间隔，避免被封IP
- **请求头伪装**：模拟真实浏览器请求
- **错误处理**：安全处理API错误和异常

### 数据安全
- **敏感信息保护**：不在日志中记录敏感数据
- **本地数据加密**：对存储的敏感数据进行加密
- **访问控制**：限制对配置和数据文件的访问权限