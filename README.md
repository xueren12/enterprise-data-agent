# 企业数据问答与报告生成 Agent

面向企业接口调用日志的数据分析 Agent。用户用自然语言提出分析问题，系统通过 LangGraph 编排多节点流程，自动完成结构化查询计划、数据读取、SQL 安全校验、Pandas 分析、图表生成、结构化报告输出和 TraceID 链路日志。

简历展示地址：<https://github.com/xueren12/enterprise-data-agent>

## 项目简介

这个项目不是普通聊天机器人，也不是简单 RAG Demo，而是一个可控、可追踪、可兜底的企业数据分析 Agent。当前示例场景聚焦企业接口调用日志，支持统计各部门失败率、失败率最高接口 TopN、平均响应时间、失败趋势和部门调用量变化。

核心目标：

- 用结构化 `QueryPlan` 约束模型输出，减少自由文本不可控问题。
- 用 LangGraph 多节点状态图编排完整 Agent 链路。
- 对 PostgreSQL SQL 做只读安全校验、白名单限制和失败修复重试。
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
- **PostgreSQL SQL 安全校验**：只允许单条 `SELECT`，限制表白名单、字段白名单、`LIMIT`，禁止 DDL / DML、多语句、注释绕过和普通 `SELECT *`。
- **SQL 生成失败修复重试**：SQL 校验失败后把原 SQL 和错误原因反馈给模型，最多修复 2 次，仍失败进入 fallback。
- **Pandas 数据分析**：CSV 和 PostgreSQL 明细数据统一进入 Pandas，复用失败率、TopN、趋势和平均耗时分析逻辑。
- **图表和结构化报告生成**：Matplotlib 保存图表，报告包含分析目标、核心结论、数据依据、异常发现、业务建议和图表路径。
- **TraceID 链路日志**：每次请求生成 `trace_id`，节点和工具调用写入 JSONL 日志，便于追踪和排错。

## 数据目录 / Schema Registry

项目新增统一数据目录，集中管理 `api_call_logs` 表、字段权限和指标口径，避免让 LLM 在提示词里猜字段、猜表名或猜可筛选条件。

- `table_catalog.yaml` 定义表名、中文描述、字段含义、字段类型、是否允许查询、是否允许筛选、是否允许聚合和是否敏感。
- `schema_registry.py` 负责加载数据目录，并向 SQL 校验提供表白名单、可查询字段、可筛选字段和敏感字段信息。
- `field_resolver.py` 负责把 QueryPlan 中的筛选条件映射到真实字段，例如 `days` 对应 `request_time`。
- `metric_registry.py` 统一管理指标口径，例如 `department_failure_rate` 需要 `department`、`status` 字段，允许哪些 filters，默认 TopN 是多少，是否生成图表和报告。
- QueryPlan fallback 不再维护一份硬编码字段表，而是从 `metric_registry` 读取 required_columns，并通过 `field_resolver` 校验 filters。
- SQL 安全校验不再信任模型输出字段，SELECT 字段必须 `allow_query=true`，WHERE 字段必须 `allow_filter=true`，敏感字段会被拒绝。

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
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_demo.py
uvicorn app.main:app --reload
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

## 环境变量说明

| 变量 | 示例值 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | `your_api_key` | DeepSeek API Key，留空时走本地规则 fallback |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型名称 |
| `DATABASE_URL` | `postgresql+psycopg://agent_user:agent_password@localhost:15432/agent_db` | PostgreSQL 连接地址 |
| `DEFAULT_DATA_SOURCE` | `auto` | 数据源选择策略：`auto` / `csv` / `postgresql` |
| `SQL_MAX_LIMIT` | `200` | SQL 查询最大 LIMIT |
| `SQL_MAX_RETRIES` | `2` | SQL 修复最大次数 |

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
  "chart_path": "C:\\Users\\64789\\Desktop\\Agent\\charts\\a1b2c3d4e5f6_department_failure_rate.png",
  "error": null
}
```

## 接口说明

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/docs` | 本地 Web Demo 页面 |
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
pytest
```

当前测试覆盖：

- QueryPlan 结构化解析和非法 fallback
- SQL 安全校验
- SQL 修复重试
- CSV 分支不触发 SQL 修复
- Pandas 分析函数
- FastAPI 接口响应
- 完整 LangGraph 主流程

## 项目截图

### Web Demo 页面

![Web Demo 页面](docs/images/docs_page.png)

### POST /agent/query 返回结果

![接口返回结果](docs/images/agent_query_response.png)

### 图表和报告

![图表和报告](docs/images/chart_report.png)

## 后续优化

- 引入异步任务队列，支持长耗时分析任务。
- 接入更细粒度的数据权限和用户认证。
- 扩展多表查询、字段语义映射和数据目录管理。
- 增加真实 PostgreSQL 集成测试和 CI 数据库服务。
- 接入日志平台、指标监控和告警。
- 支持更多图表类型和报告导出格式。
- 将 Web Demo 升级为更完整的运营分析控制台。
