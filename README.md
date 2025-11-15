# 项目说明

## 任务列表
- [ ] 初始化标准化文档（docs/）
- [ ] 填写 CLAUDE.md 模块信息
- [ ] 配置 Jest 与 ESLint
- [ ] 运行 `/start` `/next` `/update-status` `/progress`
- [x] 重写 AGENTS.md 文档，补充概述/运行指南/目录路由/API/技术栈说明（pnpm 规范）
- [x] 应用 ddl.sql，跑通采集→校验→API 验证数据可读
- [x] 增强采集节流/重试并新增 analysis_jobs worker 入池特征
- [x] 评估后端 TypeScript 方案现状
- [x] 根据个人自用需求更新后端 Python 架构文档
- [x] 强调数据分析核心地位并更新相关文档
- [x] 落地数据采集流程与表结构依赖，并同步项目状态
- [x] 创建 analysis/src 采集与校验脚本骨架及验证指南
- [x] 初始化 backend FastAPI 项目并接入数据库封装

## 快速开始
1. 安装依赖
   ```bash
   pip install -r analysis/requirements.txt
   pip install -r backend/requirements.txt
   ```
2. 配置环境变量（默认 MySQL 密码 560117）：
   ```bash
   set MYSQL_DSN=mysql+pymysql://root:560117@localhost:3306/lottery
   set TXFF_HISTORY_ENDPOINT=https://kjapi.com/hall/hallhistory/txffcqiqu/ksffc
   set TXFF_LATEST_ENDPOINT=https://kjapi.com/hallhistoryDetail/txffcqiqu
   ```
3. 执行数据库 DDL（参见 `docs/技术架构.md` 第 3 章）创建 raw/lottery/validation/analysis_jobs 表。
4. 运行采集与校验脚本：
   ```bash
   python -m analysis.src.collector
   python -m analysis.src.validator
   ```
5. 启动 FastAPI：
   ```bash
   uvicorn backend.app.main:app --reload
   ```
6. 运行测试：
   ```bash
   pytest analysis/tests
   ```
