# 新电脑部署指南

本文档说明如何在新电脑上部署和运行腾讯分分彩公式搜索自动化工具。

## 环境要求

### 操作系统
- **Windows 10/11** (64位)
- 不支持 macOS 和 Linux（依赖 Windows 桌面自动化）

### 软件要求
- **Python 3.11** 或更高版本
- **Git** (用于克隆项目)
- **Tesseract OCR** (文字识别引擎)
- **目标应用**: 奇趣腾讯分分彩桌面应用

---

## 部署步骤

### 1. 安装 Python

**下载地址**: https://www.python.org/downloads/

**安装要点**:
- ✅ 勾选 "Add Python to PATH"
- ✅ 选择 "Install for all users"
- 推荐安装到 `C:\Python311\`

**验证安装**:
```bash
python --version
# 输出: Python 3.11.x

pip --version
# 输出: pip 23.x.x from ...
```

---

### 2. 安装 Git

**下载地址**: https://git-scm.com/download/win

**验证安装**:
```bash
git --version
# 输出: git version 2.x.x
```

---

### 3. 安装 Tesseract OCR

**下载地址**: https://github.com/UB-Mannheim/tesseract/wiki

**推荐版本**: tesseract-ocr-w64-setup-v5.3.0.exe 或更高

**安装路径建议**: `D:\Tools\Tesseract\` 或 `C:\Program Files\Tesseract-OCR\`

**安装后**:
- 记录安装路径（后续配置需要）
- 确保安装了中文语言包（安装时勾选 "Chinese - Simplified"）

**验证安装**:
```bash
# 将 Tesseract 路径添加到系统 PATH，或使用完整路径测试
D:\Tools\Tesseract\tesseract.exe --version
# 输出: tesseract 5.x.x
```

---

### 4. 克隆项目

**方式一: HTTPS (推荐)**
```bash
cd D:\
git clone https://github.com/pzy560117/PC-CP-Test.git
cd PC-CP-Test
```

**方式二: SSH**
```bash
cd D:\
git clone git@github.com:pzy560117/PC-CP-Test.git
cd PC-CP-Test
```

---

### 5. 安装 Python 依赖

```bash
# 进入项目目录
cd D:\PC-CP-Test

# 升级 pip（可选但推荐）
python -m pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

**常见依赖**:
- `pywinauto==0.6.8` - Windows UI 自动化
- `pyautogui==0.9.54` - 鼠标键盘控制
- `easyocr` - OCR 文字识别
- `pytesseract` - Tesseract 的 Python 接口
- `Pillow` - 图像处理
- `requests` - HTTP 请求
- `supabase` - 云端数据存储

**安装时间**: 首次安装约 5-10 分钟（取决于网络速度）

---

### 6. 配置项目

#### 6.1 修改 `config/config.json`

打开 `config/config.json`，修改以下关键配置：

**① 目标应用路径**:
```json
{
  "target_app": {
    "executable_path": "C:\\你的应用路径\\奇趣腾讯分分彩.exe",
    "window_title": "奇趣腾讯分分彩",
    "skip_app_launch": false
  }
}
```

**说明**:
- `executable_path`: 改为你电脑上的实际安装路径
- `skip_app_launch`: 如果手动启动应用，设为 `true`

**② Tesseract 路径**:
```json
{
  "search": {
    "tesseract_cmd": "D:/Tools/Tesseract/tesseract.exe"
  }
}
```

**说明**: 改为你的 Tesseract 实际安装路径（使用正斜杠 `/`）

**③ MySQL 配置（可选）**:
```json
{
  "mysql": {
    "enabled": false,
    "host": "localhost",
    "port": 3306,
    "user": "your_user",
    "password": "your_password",
    "database": "lottery_db"
  }
}
```

**说明**: 如不使用 MySQL，保持 `enabled: false`

**④ Supabase 配置（可选）**:
```json
{
  "supabase": {
    "enabled": false,
    "url": "https://your-project.supabase.co",
    "key": "your-anon-key"
  }
}
```

**说明**: 如不使用 Supabase，保持 `enabled: false`

#### 6.2 创建必要的目录

项目会自动创建，但也可以手动确认：
```bash
mkdir -p data/results
mkdir -p data/backup
mkdir -p data/history
mkdir -p logs
mkdir -p images
```

---

### 7. 验证安装

#### 7.1 检查配置
```bash
python main.py
# 应输出配置验证信息（dry-run 模式）
```

#### 7.2 测试窗口连接
```bash
# 先手动启动"奇趣腾讯分分彩"应用
python tests/test_desktop_automation.py
```

---

### 8. 运行项目

#### 8.1 首次运行（推荐）

**步骤**:
1. 手动启动"奇趣腾讯分分彩"应用
2. 手动打开"计划接口-奇趣腾讯分分彩"窗口（用于开奖 OCR）
3. 运行自动化脚本:

```bash
python main.py --real-run
```

#### 8.2 配置自动启动应用

修改 `config/config.json`:
```json
{
  "target_app": {
    "skip_app_launch": false,
    "executable_path": "C:\\实际路径\\奇趣腾讯分分彩.exe"
  }
}
```

然后运行:
```bash
python main.py --real-run
```

#### 8.3 循环模式

启用循环自动执行:
```bash
python main.py --real-run --loop --interval 60
```

**参数说明**:
- `--real-run`: 执行真实自动化流程
- `--loop`: 启用循环模式
- `--interval 60`: 每次循环间隔 60 秒

---

## 常见问题

### Q1: pip 命令找不到

**症状**: 
```
pip : 无法将"pip"项识别为 cmdlet、函数、脚本文件或可运行程序的名称
```

**原因**: pip 没有添加到系统 PATH 环境变量

**解决方法 1（推荐）**: 使用 Python 模块方式调用 pip
```bash
python -m pip install -r requirements.txt
python -m pip install --upgrade pip
```

**解决方法 2**: 手动添加 PATH
1. 找到 Python 安装目录（例如 `D:\python311\python311\`）
2. 将以下两个路径添加到系统 PATH：
   - `D:\python311\python311\`
   - `D:\python311\python311\Scripts\`
3. 重新打开 PowerShell
4. 测试：`pip --version`

**注意**: 如果重新安装 Python，请勾选 "Add Python to PATH" 选项

---

### Q2: 提示 "未找到窗口"

**原因**: 应用未启动或窗口标题不匹配

**解决**:
1. 确认应用已启动
2. 检查 `config.json` 中的 `window_title` 是否与实际窗口标题一致
3. 可以使用 `tools/inspect_window.py` 查看所有窗口标题:
   ```bash
   python tools/inspect_window.py
   ```

### Q3: OCR 识别失败

**原因**: Tesseract 未安装或路径配置错误

**解决**:
1. 确认 Tesseract 已安装
2. 检查 `config.json` 中的 `tesseract_cmd` 路径是否正确
3. 测试 Tesseract:
   ```bash
   D:\Tools\Tesseract\tesseract.exe --version
   ```

### Q4: 依赖安装失败

**原因**: 网络问题或缺少 C++ 编译环境

**解决**:
1. 使用国内镜像源:
   ```bash
   python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```
2. 安装 Microsoft Visual C++ 14.0:
   - 下载地址: https://visualstudio.microsoft.com/visual-cpp-build-tools/

### Q5: 开奖 OCR 一直识别不到

**原因**: 计划接口窗口未打开或被遮挡

**解决**:
1. 手动打开"计划接口-奇趣腾讯分分彩"窗口
2. 确保窗口可见且未被最小化
3. 检查 `config.json` 中 `lottery.ocr.window_title` 配置:
   ```json
   {
     "lottery": {
       "ocr": {
         "enabled": true,
         "window_title": "计划接口-奇趣腾讯分分彩"
       }
     }
   }
   ```

### Q6: 推荐号提取失败

**原因**: 窗口尺寸或 OCR 区域配置不正确

**解决**:
1. 查看 `logs/full_window_capture.png` 确认截图是否正确
2. 调整 `config.json` 中的 `ocr_stats_region` 参数
3. 使用工具辅助定位:
   ```bash
   python tools/capture_button.py
   ```

---

## 项目结构

```
PC-CP-Test/
├── config/
│   └── config.json          # 主配置文件 ⚙️
├── src/
│   ├── automator/           # 自动化模块
│   ├── api/                 # API 客户端
│   ├── data/                # 数据处理
│   └── utils/               # 工具函数
├── tests/                   # 测试脚本
├── tools/                   # 辅助工具
├── data/                    # 数据目录
├── logs/                    # 日志目录
├── docs/                    # 文档
├── main.py                  # 主入口 🚀
└── requirements.txt         # 依赖列表
```

---

## 快速开始检查清单

- [ ] 安装 Python 3.11+
- [ ] 安装 Git
- [ ] 安装 Tesseract OCR
- [ ] 克隆项目到本地
- [ ] 安装 Python 依赖 (`pip install -r requirements.txt`)
- [ ] 修改 `config/config.json` 中的路径配置
- [ ] 手动启动目标应用
- [ ] 手动打开计划接口窗口
- [ ] 运行测试验证 (`python main.py`)
- [ ] 执行真实流程 (`python main.py --real-run`)

---

## 技术支持

如遇到其他问题，可以:
1. 查看 `logs/app.log` 日志文件
2. 查看项目 README.md
3. 提交 GitHub Issue: https://github.com/pzy560117/PC-CP-Test/issues

---

## 版本信息

- **文档版本**: v1.0
- **更新日期**: 2025-11-23
- **适用项目版本**: v1.2+
