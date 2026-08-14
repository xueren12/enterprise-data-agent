# 企业数据问答与报告生成 Agent

面向企业接口调用日志的数据分析 Agent。用户用自然语言提出分析问题，系统通过 LangGraph 编排多节点流程，自动完成结构化查询计划、数据读取、SQL 安全校验、Pandas 分析、图表生成、结构化报告输出和 TraceID 链路日志。

简历展示地址：<https://github.com/xueren12/enterprise-data-agent>

## 项目简介

这个项目不是普通聊天机器人，也不是简单 RAG Demo，而是一个可控、可追踪、可兜底的企业数据分析 Agent。当前示例场景聚焦企业接口调用日志，支持统计各部门失败率、失败率最高接口 TopN、平均响应时间、失败趋势和部门调用量变化。

核心目标：

- 用结构化 `QueryPlan` 约束模型输出，减少自由文本不可控问题。
- 用 LangGraph 多节点状态图编排完整 Agent 链路。
- 对 PostgreSQL SQL 做只读安全校验、白名单限制、最小权限执行和失败修复重试。
- 用 Pandas 完成失败率、TopN、趋势和响应时间分析。
- 生成 Matplotlib 图表和结构化 Markdown 报告。
- 用 TraceID 记录 Agent 执行链路日志。

## 技术栈

- Python 3.11+
- FastAPI
- LangGraph
- LangChain Tool
- DeepSeek API
- Pandas
- Matplotlib
- SQLAlchemy
- PostgreSQL
- sqlglot
- Docker / Docker Compose
- Pytest

## 项目亮点

- **结构化 QueryPlan 约束模型输出**：DeepSeek 优先返回 JSON，Pydantic 校验失败后自动回退到确定性规则。
- **LangGraph 多节点状态图编排**：解析、选源、计划、工具调用、SQL 校验、SQL 修复、分析、报告、兜底节点职责清晰。
- **PostgreSQL SQL 安全校验**：只允许单条 `SELECT`，限制表、字段、聚合字段和 `LIMIT`，禁止 DDL / DML、多语句、注释绕过、普通 `SELECT *` 与 `pg_sleep` 等高风险函数。
- **数据库纵深防护**：Docker 中应用使用仅具 `SELECT` 权限的 `agent_reader` 账号；SQLAlchemy 连接还会开启只读事务和语句超时。
- **SQL 生成失败修复重试**：SQL 校验失败后把原 SQL 和错误原因反馈给模型，最多修复 2 次，仍失败进入 fallback。
- **Pandas 数据分析**：CSV 和 PostgreSQL 明细数据统一进入 Pandas，复用失败率、TopN、趋势和平均耗时分析逻辑。
- **图表和结构化报告生成**：Matplotlib 保存图表，报告包含分析目标、核心结论、数据依据、异常发现、业务建议和图表路径。
- **TraceID 链路日志**：每次请求生成 `trace_id`，节点和工具调用写入 JSONL 日志，便于追踪和排错。

## 数据目录 / Schema Registry

项目新增统一数据目录，集中管理 `api_call_logs` 表、字段权限和指标口径，避免让 LLM 在提示词里猜字段、猜表名或猜可筛选条件。

- `table_catalog.json` 定义表名、中文描述、字段含义、字段类型、是否允许查询、是否允许筛选、是否允许聚合和是否敏感。
- `schema_registry.py` 负责加载数据目录，并向 SQL 校验提供表白名单、可查询字段、可筛选字段和敏感字段信息。
- `field_resolver.py` 负责把 QueryPlan 中的筛选条件映射到真实字段，例如 `days` 对应 `request_time`。
- `metric_registry.py` 统一管理指标口径，例如 `department_failure_rate` 需要 `department`、`status` 字段，允许哪些 filters，默认 TopN 是多少，是否生成图表和报告。
- QueryPlan fallback 不再维护一份硬编码字段表，而是从 `metric_registry` 读取 required_columns，并通过 `field_resolver` 校验 filters。
- SQL 安全校验不再信任模型输出字段，SELECT 字段必须 `allow_query=true`，WHERE 字段必须 `allow_filter=true`，聚合字段必须 `allow_aggregate=true`，敏感字段会被拒绝。

## 合成数据与可复现性

- `data/sample_api_logs.csv` 是完全合成的企业接口日志，共 40 条记录，不包含真实用户、客户或生产系统数据。
- Docker PostgreSQL 通过 `COPY` 直接加载该 CSV，避免 CSV 分支与数据库分支使用不同样例数据。
- [可复现评测说明](docs/evaluation_report.md) 固定包含 150 条支持问题和 12 条异常问题，并区分 QueryPlan、SQL 校验、SQL 实际执行和 fallback 指标。

## 系统架构图

```mermaid
flowchart TD
    U[用户自然语言问题] --> API[FastAPI]
    API --> G[LangGraph StateGraph]
    G --> Q[结构化 QueryPlan]
    Q --> CSV[CSV 分支]
    Q --> PG[PostgreSQL 分支]
    CSV --> P[Pandas Analysis]
    PG --> S[SQL 安全校验与修复]
    S --> P
    P --> C[Chart 图表]
    P --> R[Report 结构化报告]
    C --> O[统一响应]
    R --> O
    G --> T[TraceID 链路日志]
```

## LangGraph 流程图

```mermaid
flowchart TD
    A[parse_question] --> B[select_datasource]
    B --> C[generate_plan]
    C --> D{route_data_source}
    D -->|csv| E[run_tool]
    D -->|postgresql| F[generate_sql]
    F --> G[validate_sql]
    G -->|safe| H[execute_sql]
    G -->|unsafe and retry_count < 2| I[repair_sql]
    I --> G
    G -->|max retries| Z[fallback]
    E --> J[validate_result]
    H --> J
    J --> K[analyze_data]
    K --> L[generate_report]
    L --> M[END]
    Z --> M
```

## 快速启动

### 方式一：本地 Python

```powershell
cd C:\Users\64789\Desktop\Agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_demo.py
python -m uvicorn app.main:app --reload
```

访问：

```text
http://localhost:8000/docs
```

### 方式二：Docker Compose

```powershell
cd C:\Users\64789\Desktop\Agent
copy .env.example .env
docker compose up -d
```

访问：

```text
http://localhost:8000/docs
```

首次启动会把 `data/sample_api_logs.csv` 导入 PostgreSQL。升级初始化数据或角色后，可执行 `docker compose down -v` 后重新 `up -d`；这只会重建项目的合成演示数据。

## 环境变量说明

| 变量 | 示例值 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | `your_api_key` | DeepSeek API Key，留空时走本地规则 fallback |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型名称 |
| `DATABASE_URL` | `postgresql+psycopg://agent_reader:agent_reader_password@localhost:15432/agent_db` | PostgreSQL 只读账号连接地址 |
| `DEFAULT_DATA_SOURCE` | `auto` | 数据源选择策略：`auto` / `csv` / `postgresql` |
| `SQL_MAX_LIMIT` | `200` | SQL 查询最大 LIMIT |
| `SQL_MAX_RETRIES` | `2` | SQL 修复最大次数 |
| `SQL_STATEMENT_TIMEOUT_MS` | `5000` | 数据库单条 SQL 最长执行时间（毫秒） |

## 示例问题

- 统计各部门接口调用失败率，并生成分析报告
- 统计各部门接口调用失败率 Top10，并生成分析报告
- 找出失败率最高的接口，并给出可能原因
- 分析最近 30 天各项目接口平均响应时间
- 生成本月接口稳定性分析报告
- 分析不同部门的接口调用量变化

## 示例输出

```json
{
  "trace_id": "a1b2c3d4e5f6",
  "question": "统计各部门接口调用失败率，并生成分析报告",
  "status": "success",
  "report": "## 分析目标\n统计各部门接口调用失败率，并生成分析报告\n\n## 核心结论\n...",
  "chart_path": "/app/charts/a1b2c3d4e5f6_department_failure_rate.png",
  "task_url": "/agent/task/a1b2c3d4e5f6",
  "report_url": "/agent/report/a1b2c3d4e5f6",
  "chart_url": "/agent/chart/a1b2c3d4e5f6",
  "error": null
}
```

## 接口说明

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/docs` | 本地 Web Demo 页面 |
| `GET` | `/health` | 服务健康检查 |
| `POST` | `/agent/query` | 提交自然语言数据分析问题 |
| `GET` | `/agent/task/{task_id}` | 查询任务状态和完整结果 |
| `GET` | `/agent/report/{task_id}` | 获取任务分析报告 |
| `GET` | `/agent/chart/{task_id}` | 获取任务图表文件 |

请求示例：

```bash
curl -X POST "http://localhost:8000/agent/query" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"统计各部门接口调用失败率，并生成分析报告\"}"
```

## 测试方式

```powershell
py -3.11 -m pytest -q
```

当前测试覆盖：

- QueryPlan 结构化解析和非法 fallback
- SQL 安全校验
- SQL 修复重试
- CSV 分支不触发 SQL 修复
- Pandas 分析函数
- FastAPI 接口响应
- 完整 LangGraph 主流程
- 数据目录与敏感字段防护
- 聚合字段、危险函数、只读 SQL 安全规则
- 150 条离线评测集和 12 条异常兜底评测

### 可复现评测

```powershell
# QueryPlan、SQL 校验和 fallback
py -3.11 evaluation/run_evaluation.py

# PostgreSQL 真实 SQL 执行率
docker compose up -d postgres
py -3.11 evaluation/run_evaluation.py `
  --database-url "postgresql+psycopg://agent_reader:agent_reader_password@localhost:15432/agent_db"
```

评测结果和指标定义见 [docs/evaluation_report.md](docs/evaluation_report.md)。

## 项目截图

### Web Demo 页面

![Web Demo 页面](docs/images/docs_page.png)

### POST /agent/query 返回结果

![接口返回结果](docs/images/agent_query_response.png)

### 图表和报告

![图表和报告](docs/images/chart_report.png)

### 真实接口流程

![真实接口流程](docs/images/agent_demo.gif)

## 后续优化

- 引入异步任务队列，支持长耗时分析任务。
- 接入更细粒度的数据权限和用户认证。
- 扩展多表查询、字段语义映射和数据目录管理。
- 增加多表权限、行级权限和审计策略。
- 接入日志平台、指标监控和告警。
- 支持更多图表类型和报告导出格式。
- 将 Web Demo 升级为更完整的运营分析控制台。

## 开源协议

本项目采用 [MIT License](LICENSE)。
