# 项目代理指南（AGENTS）

## 1. 项目概述
- 类型：腾讯分分彩数据采集与分析平台，后端以 Python 为核心（数据采集、校验、分析），FastAPI 提供接口，前端计划使用 React+TypeScript 展示结果。
- 核心价值：先打通数据采集→校验→落库→分析结果的闭环，再逐步补齐前端展示与特征/模型。

```mermaid
flowchart LR
    Collect[采集 collector] --> Validate[校验 validator]
    Validate --> DB[(MySQL/Redis)]
    Validate --> Jobs[analysis_jobs 入队特征任务]
    DB --> API[FastAPI /api/v1/draws]
    API --> FE[前端展示(计划)]
```

## 2. 安装、环境变量、运行/构建命令
- 环境准备：
  - Python 3.9+，本地 MySQL 8.0+，Redis 6.0+。
  - 环境变量（必填）：`MYSQL_DSN`（如 `mysql+pymysql://root:560117@localhost:3306/lottery`），`TXFF_HISTORY_ENDPOINT`，`TXFF_LATEST_ENDPOINT`。
- 依赖安装：
  - 数据分析/采集：`pip install -r analysis/requirements.txt`
  - FastAPI 后端：`pip install -r backend/requirements.txt`
  - （前端未初始化，如需创建请使用 pnpm：`pnpm create vite frontend --template react-ts`，全程禁止 npm）
- 运行命令：
  - 采集：`python -m analysis.src.collector`
  - 校验落库：`python -m analysis.src.validator`
  - FastAPI：`uvicorn backend.app.main:app --reload`
- 测试：
  - `pytest analysis/tests`
- 构建：
  - Python 服务无需构建；若后续补齐前端，请使用 `pnpm install` / `pnpm build`，严禁使用 npm。

## 3. 目录结构、页面路由、API 接口
- 目录（核心已存在）：
  - `analysis/src/`：采集器 `collector.py`，校验器 `validator.py`，数据库封装 `database.py`。
  - `backend/app/`：`api/draws.py`（开奖列表/详情），`db.py`（复用 analysis Engine），`config.py`，`main.py`。
  - `docs/`：技术架构、状态、分析框架等文档。
  - `ddl.sql`：数据库表定义（raw_lottery_draws、lottery_draws、validation_logs、analysis_jobs 等）。
- 计划中的前端路由（待实现，基于 React Router / shadcn/ui）：
  - `/dashboard` 仪表盘
  - `/analysis` 数据分析页
  - `/history` 历史数据
  - `/settings` 设置
- 已有 API（FastAPI）：
  - `GET /api/v1/draws?limit=50`：最近开奖列表
  - `GET /api/v1/draws/{period}`：按期号查询

## 4. 技术栈与依赖说明
- 数据采集/分析：Python（pandas、numpy、requests、BeautifulSoup），SQLAlchemy 驱动 MySQL。
- 后端：FastAPI + Uvicorn，使用同一 MySQL Engine，无鉴权（受控环境）。
- 数据库/缓存：MySQL 作为主存，Redis 预留缓存/实时指标。
- 前端（规划）：React 18+、TypeScript、shadcn/ui（Radix + Tailwind）、数据获取预期用 React Query/SWR，图表 Recharts/ECharts。

## 5. 包管理要求
- 所有 Node 相关操作一律使用 `pnpm`（如安装、构建、脚手架创建）。禁止使用 `npm`。
- Python 环境仍使用 `pip` 安装 requirements。
