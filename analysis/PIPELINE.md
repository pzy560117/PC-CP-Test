# 分析数据管道草案

> 本草案用于指导 `analysis/` 目录后续脚本开发，确保采集→校验→分析闭环可快速实现与回放。

## 1. 采集阶段
1. 运行 `python -m analysis.src.collector run_collection`（或在 CLI 中调用 `run_collection()`）；
2. `collector.py` 将请求 `TXFF_HISTORY_ENDPOINT` / `TXFF_LATEST_ENDPOINT`，并把原始响应（含 headers、请求耗时、代理信息）写入 `raw_lottery_draws`；
3. 记录 `status=pending`，并在 `analysis_jobs` 中写入 `collect` 类型任务（用于监控）。

## 2. 校验阶段
1. 控制台或定时任务运行 `python -m analysis.src.validator run_validation`；
2. `validator.py` 消费 `raw_lottery_draws`，对字段、数值范围与时间戳连续性执行校验；
3. 失败记录写入 `validation_logs`（含校验项、错误详情）并保持 `status=failed`；
4. 通过的数据转换为 `lottery_draws` 标准结构，并更新 raw 记录 `status=passed`。

## 3. 特征与统计阶段
1. 以期号为粒度批量读取 `lottery_draws`
2. 计算基础、方向、组合特征后统一写入 `lottery_features`
3. 根据配置生成 `analysis_jobs`（如 frequency、randomness），任务完成后写入 `analysis_results`

## 4. 发布阶段
1. FastAPI 读取 MySQL 与 Redis，提供 `draws`、`features`、`analysis` 等 REST 接口；
2. 分析结果同步缓存至 `lottery:analysis:{type}`，并通过 WebSocket 推送前端；
3. 失败任务回写 `analysis_jobs.status=failed`，由重试器扫描。

## 5. 验证要点
- 任意阶段都可以根据期号回放，因为所有原始/整理/特征数据均可索引
- 所有脚本在 `analysis/src` 内通过函数注释说明 I/O，且不允许引入模拟数据
- 新增分析模块必须先注册 job 类型及结果 schema，再允许前端消费

## 6. raw → lottery 验证步骤
1. 建表：执行 docs/技术架构.md 中的 MySQL DDL，确保 `raw_lottery_draws`、`lottery_draws`、`validation_logs`、`analysis_jobs` 存在；
2. 设置环境变量 `MYSQL_DSN`、`TXFF_HISTORY_ENDPOINT`、`TXFF_LATEST_ENDPOINT` 等；
3. 运行采集脚本：`python -m analysis.src.collector`（写入 raw）；
4. 检查 `SELECT COUNT(*) FROM raw_lottery_draws WHERE status='pending'`；
5. 运行校验脚本：`python -m analysis.src.validator`；确认 `raw_lottery_draws.status` 更新为 `passed/failed`，以及 `lottery_draws` 新增对应期号；
6. 通过 `SELECT * FROM analysis_jobs WHERE job_type='feature_extract' AND status='pending'` 验证后续任务被触发。

## 7. FastAPI 骨架计划
1. 在仓库 `backend/` 创建 FastAPI 项目（`app/main.py`、`app/api/draws.py`、`app/api/analysis.py`）；
2. 通过 SQLAlchemy `Session` 复用 `analysis/src/database.py` 的连接配置，提供 `GET /api/v1/draws`, `GET /api/v1/analysis/frequency` 等路由；
3. 引入 `redis.asyncio` 客户端读取 `lottery:analysis:{type}` 缓存；
4. 使用 `uvicorn` 开发启动（`uvicorn app.main:app --reload`），待数据库表可写后再实现实际查询逻辑；
5. 在部署前确保 FastAPI 仅作为消费层，不在后端写入任何模拟数据。
