# 项目说明

## 任务列表
- [ ] 初始化标准化文档（docs/）
- [ ] 填写 CLAUDE.md 模块信息
- [ ] 配置 Jest 与 ESLint
- [ ] 运行 `/start` `/next` `/update-status` `/progress`
- [x] 再次验证采集→校验→落库闭环并记录库内样本
- [x] 补充分析结果/特征 API 并完成 FastAPI 联调
- [x] 验证 jobs_worker 批处理 analysis_jobs 队列状态
- [x] 重写 AGENTS.md 文档，补充概述/运行指南/目录路由/API/技术栈说明（pnpm 规范）
- [x] 应用 ddl.sql，跑通采集→校验→API 验证数据可读
- [x] 增强采集节流/重试并新增 analysis_jobs worker 入池特征
- [x] 评估后端 TypeScript 方案现状
- [x] 根据个人自用需求更新后端 Python 架构文档
- [x] 强调数据分析核心地位并更新相关文档
- [x] 落地数据采集流程与表结构依赖，并同步项目状态
- [x] 创建 analysis/src 采集与校验脚本骨架及验证指南
- [x] 初始化 backend FastAPI 项目并接入数据库封装
- [x] 指导 WSL 环境配置与 sudo/apt 初始化
- [x] 分析抓包接口清单并输出排查建议

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
   set COLLECT_LATEST_ENABLED=false
   set COLLECT_MONITORING_ENABLED=true
   set API_MAX_RESULTS=200
   set API_MAX_JOBS=200
   set CACHE_TTL_SECONDS=30
   # 如需启用 Redis 缓存
   set REDIS_URL=redis://localhost:6379/0
   # 调度/告警
   set SCHED_COLLECTOR_INTERVAL=300
   set SCHED_VALIDATOR_INTERVAL=120
   set SCHED_WORKER_INTERVAL=60
   set SCHED_ALERT_WINDOW=5
   set SCHED_ALERT_THRESHOLD=3
   set SCHED_ALERT_COOLDOWN=300
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
7. 启动调度与告警：
   ```bash
   python -m analysis.src.scheduler --run-forever
   # 调试模式（单次运行/模拟失败）
   python -m analysis.src.scheduler --iterations 1 --simulate-failure collector
   ```

## 前端仪表盘（frontend/）

1. 复制环境变量：
   ```bash
   cd frontend
   cp .env.example .env.local  # 根据需要修改 VITE_API_BASE_URL（默认 http://localhost:8000）
   ```
2. 安装依赖并启动开发服务器：
   ```bash
   pnpm install
   pnpm dev
   ```
3. 生产构建：
   ```bash
   pnpm build
   ```
   > 说明：目前 `vite@7` 官方建议 Node.js ≥ 20.19，若本地 Node 18.* 可能出现 Warning，功能仍可使用，建议后续升级 Node。
