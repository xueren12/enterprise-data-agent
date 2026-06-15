# AGENTS.md

## 项目名称

企业数据问答与报告生成 Agent 系统

## 项目定位

本项目是一个面向企业经营分析与数据查询场景的智能 Agent 系统。

用户通过自然语言提出数据分析需求，系统需要自动完成：

1. 理解用户问题；
2. 选择数据源；
3. 生成查询计划；
4. 调用 SQL / CSV / Excel / Pandas 等工具；
5. 对结果进行校验和分析；
6. 生成图表；
7. 输出结构化分析报告；
8. 记录 Agent 执行链路日志；
9. 对异常情况进行兜底处理。

本项目不是普通聊天机器人，也不是简单的 RAG Demo，而是一个可控、可追踪、可扩展的企业数据分析 Agent。

---

## 技术栈

核心技术栈：

* Python
* LangChain
* LangGraph
* FastAPI
* Pandas
* SQLAlchemy
* PostgreSQL
* Matplotlib
* DeepSeek API
* Docker

优先保证后端 Agent 主流程跑通，不要优先开发复杂前端。

---

## 项目目标

最终系统需要支持以下能力：

* 自然语言问数；
* SQL 查询；
* CSV / Excel 数据读取；
* Pandas 数据分析；
* 图表生成；
* 结构化报告生成；
* LangGraph 状态图编排；
* LangChain Tool 工具封装；
* Agent 执行链路日志；
* SQL 安全校验；
* 工具调用失败兜底；
* FastAPI 接口服务化；
* Docker 部署。

---

## MVP 优先级

请按以下优先级开发，不要一开始做大而全。

### 第一阶段：跑通最小数据分析闭环

目标：

用户输入：

```text
统计各部门接口调用失败率，并生成分析报告
```

系统完成：

1. 读取 CSV 数据；
2. 使用 Pandas 计算各部门接口调用失败率；
3. 生成柱状图；
4. 输出文本分析报告。

这一阶段可以暂时不接大模型，不接 PostgreSQL，不做复杂前端。

---

### 第二阶段：接入 LangGraph

将第一阶段的流程拆成 LangGraph 节点：

* parse_question_node：解析用户问题；
* select_datasource_node：选择数据源；
* generate_plan_node：生成查询计划；
* run_tool_node：调用数据工具；
* validate_result_node：校验查询结果；
* analyze_data_node：执行 Pandas 分析；
* generate_report_node：生成分析报告；
* fallback_node：异常兜底。

需要使用 StateGraph 构建状态图，并使用 Conditional Edge 控制成功和失败分支。

---

### 第三阶段：封装 LangChain Tool

将核心能力封装为 LangChain Tool：

* sql_query_tool：执行受控 SQL 查询；
* csv_read_tool：读取 CSV / Excel 文件；
* pandas_analysis_tool：执行数据分析；
* chart_generate_tool：生成图表；
* report_generate_tool：生成结构化报告。

每个 Tool 都必须包含：

* 清晰的 name；
* 清晰的 description；
* 明确的入参；
* 明确的返回值；
* 异常处理；
* 日志记录。

---

### 第四阶段：接入 DeepSeek API

大模型优先用于：

1. 根据用户问题生成查询计划；
2. 根据分析结果生成结构化报告。

不要一开始让大模型直接生成并执行任意 SQL。

如果需要生成 SQL，必须先通过 SQL 安全校验。

---

### 第五阶段：接入 PostgreSQL + SQLAlchemy

支持数据库查询能力。

要求：

* 使用 SQLAlchemy 连接 PostgreSQL；
* 查询必须经过安全校验；
* 只允许 SELECT；
* 禁止 DROP、DELETE、UPDATE、INSERT、ALTER、TRUNCATE 等危险语句；
* 必须限制表名白名单；
* 必须限制字段白名单；
* 必须自动追加或检查 LIMIT；
* 查询失败要返回友好错误信息，不能直接抛出底层异常给用户。

---

### 第六阶段：FastAPI 服务化

提供以下接口：

* POST /agent/query：提交自然语言问数请求；
* GET /agent/task/{task_id}：查询任务状态；
* GET /agent/report/{task_id}：获取报告结果；
* GET /agent/chart/{task_id}：获取图表路径或图表文件信息。

第一版可以先只实现：

* POST /agent/query

---

### 第七阶段：工程化补强

补充：

* TraceID；
* Agent 执行链路日志；
* 失败重试；
* 结果为空兜底；
* README；
* Dockerfile；
* docker-compose.yml；
* 示例数据；
* 示例请求；
* 示例输出。

---

## 推荐项目目录

请尽量遵循以下目录结构：

```text
enterprise-data-agent/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── state.py
│   ├── graph.py
│   ├── nodes/
│   │   ├── parse_node.py
│   │   ├── plan_node.py
│   │   ├── tool_node.py
│   │   ├── analyze_node.py
│   │   ├── report_node.py
│   │   └── fallback_node.py
│   ├── tools/
│   │   ├── sql_tool.py
│   │   ├── csv_tool.py
│   │   ├── pandas_tool.py
│   │   ├── chart_tool.py
│   │   └── report_tool.py
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── db_service.py
│   │   ├── log_service.py
│   │   └── safety_service.py
│   ├── schemas/
│   │   ├── request.py
│   │   └── response.py
│   └── prompts/
│       ├── query_plan_prompt.txt
│       └── report_prompt.txt
├── data/
│   ├── sample_api_logs.csv
│   └── init.sql
├── charts/
├── reports/
├── logs/
├── tests/
├── requirements.txt
├── README.md
├── Dockerfile
└── docker-compose.yml
```

如果某个阶段暂时用不到某些目录，可以先不创建，但整体结构要向该结构靠拢。

---

## 示例业务数据

优先使用企业接口调用日志作为示例数据。

推荐表名：

```text
api_call_logs
```

推荐字段：

```text
id
department
project_name
api_name
status
status_code
latency_ms
request_time
error_message
```

字段说明：

* department：部门；
* project_name：项目名称；
* api_name：接口名称；
* status：success / failed；
* status_code：HTTP 状态码；
* latency_ms：接口耗时；
* request_time：请求时间；
* error_message：错误信息。

该数据集用于支持以下问题：

* 统计各部门接口调用失败率；
* 分析最近 30 天接口失败率趋势；
* 找出失败率最高的接口 Top10；
* 找出平均响应时间最高的接口；
* 生成接口稳定性分析报告；
* 分析不同部门的接口调用量变化。

---

## LangGraph 设计要求

Agent State 至少包含以下字段：

```python
trace_id: str
user_question: str
intent: str
data_source: str
query_plan: str
sql: str
raw_data: list
analysis_result: dict
chart_path: str
report: str
error: str | None
retry_count: int
```

每个 Node 的输入和输出都应该是 State。

不要在 Node 中写过多无关逻辑。

Node 应该职责单一：

* 解析节点只负责解析；
* 计划节点只负责生成查询计划；
* 工具节点只负责调用工具；
* 校验节点只负责判断结果是否有效；
* 分析节点只负责 Pandas 分析；
* 报告节点只负责生成报告；
* 兜底节点只负责异常提示。

---

## LangChain Tool 设计要求

Tool 必须遵循以下原则：

1. 名称清晰；
2. description 明确说明工具适用场景；
3. 入参尽量结构化；
4. 返回值尽量使用 dict 或 list[dict]；
5. 不要返回过长文本；
6. 异常必须捕获；
7. 工具调用过程必须记录日志；
8. 不允许工具直接执行危险操作。

示例 Tool 名称：

```text
sql_query_tool
csv_read_tool
pandas_analysis_tool
chart_generate_tool
report_generate_tool
```

---

## SQL 安全规则

如果实现 Text-to-SQL 或 SQL 查询工具，必须遵守：

1. 只允许 SELECT；
2. 禁止 DDL / DML；
3. 禁止多语句执行；
4. 禁止注释绕过；
5. 必须限制 LIMIT；
6. 必须校验表名白名单；
7. 必须校验字段白名单；
8. 不允许模型直接执行未经校验的 SQL；
9. 查询失败时返回友好错误；
10. 日志中记录 SQL，但不要记录敏感配置和密码。

禁止语句包括但不限于：

```text
DROP
DELETE
UPDATE
INSERT
ALTER
TRUNCATE
CREATE
GRANT
REVOKE
EXEC
MERGE
CALL
```

---

## Pandas 分析要求

Pandas 分析能力至少支持：

* read_csv；
* read_excel；
* groupby；
* agg；
* merge；
* sort_values；
* fillna；
* isnull；
* TopN；
* 同比；
* 环比；
* 异常值识别；
* 失败率计算；
* 平均耗时计算。

第一版优先实现：

* 分组统计；
* 失败率计算；
* TopN 排序；
* 折线图 / 柱状图生成。

---

## 图表生成要求

图表使用 Matplotlib。

第一版支持：

* 柱状图；
* 折线图。

要求：

* 图表保存到 charts/ 目录；
* 返回图表文件路径；
* 文件名包含 trace_id 或 task_id；
* 图表生成失败时返回友好错误；
* 不要因为中文字体问题阻塞主流程，必要时图表标题可以使用英文。

---

## 报告生成要求

报告应为结构化文本，至少包含：

1. 分析目标；
2. 核心结论；
3. 数据依据；
4. 异常发现；
5. 业务建议；
6. 图表路径。

报告语气应专业、简洁，不要生成空泛套话。

不要在没有数据支持的情况下编造结论。

如果数据不足，需要明确说明：

```text
当前数据不足以支持该结论。
```

---

## 日志与 TraceID 要求

每次 Agent 调用都必须生成 trace_id。

日志建议保存为 JSONL 格式，路径：

```text
logs/agent_trace.jsonl
```

建议记录字段：

```text
time
trace_id
node_name
user_question
intent
tool_name
tool_args
tool_result_summary
error
latency_ms
final_report
```

日志中不要记录：

* 数据库密码；
* API Key；
* 用户敏感信息；
* 大段原始数据。

---

## 异常兜底要求

必须处理以下场景：

* 工具调用失败；
* SQL 校验失败；
* 查询结果为空；
* Pandas 分析失败；
* 图表生成失败；
* 大模型调用失败；
* 用户问题无法识别；
* 数据源不存在；
* 字段不存在。

兜底回答要友好，并说明下一步建议。

例如：

```text
本次查询未获得有效结果，可能是查询条件过窄或数据源缺少相关字段。你可以尝试放宽时间范围，或指定具体部门 / 项目名称后重新查询。
```

---

## FastAPI 开发要求

接口返回格式尽量统一：

```json
{
  "trace_id": "...",
  "question": "...",
  "status": "success",
  "report": "...",
  "chart_path": "...",
  "error": null
}
```

错误时返回：

```json
{
  "trace_id": "...",
  "question": "...",
  "status": "failed",
  "report": null,
  "chart_path": null,
  "error": "错误原因"
}
```

不要直接把 Python traceback 返回给前端。

---

## 配置管理要求

项目配置放在：

```text
app/config.py
```

敏感信息放在：

```text
.env
```

不要把真实 API Key、数据库密码提交到仓库。

需要提供：

```text
.env.example
```

示例：

```text
DEEPSEEK_API_KEY=your_api_key
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/agent_db
```

---

## 代码风格

请遵守：

* 函数职责单一；
* 文件不要过大；
* 命名清晰；
* 尽量使用类型注解；
* 关键逻辑加简短注释；
* 不要写无意义注释；
* 不要堆砌过度抽象；
* 优先保证项目可运行；
* 优先保证核心链路清晰；
* 不要为了炫技引入过多框架。

---

## 开发方式

每次修改代码前，请先判断当前阶段目标。

不要一次性生成整个项目。

优先按以下顺序逐步实现：

1. 先实现普通 Python 数据分析函数；
2. 再接入 LangGraph；
3. 再封装 LangChain Tool；
4. 再接入 FastAPI；
5. 再接入 DeepSeek API；
6. 再接入 PostgreSQL；
7. 最后补日志、Docker、README 和测试。

每完成一个阶段，需要保证可以运行。

---

## 测试要求

至少提供基础测试或手动测试脚本。

推荐命令：

```bash
python run_demo.py
uvicorn app.main:app --reload
```

如果添加单元测试，使用：

```bash
pytest
```

测试重点：

* Pandas 分析函数是否正确；
* SQL 安全校验是否生效；
* LangGraph 主流程是否能跑通；
* 查询结果为空是否走兜底；
* FastAPI 接口是否返回统一格式。

---

## README 要求

README 至少包含：

1. 项目介绍；
2. 技术栈；
3. 项目架构；
4. 核心流程图；
5. 快速启动；
6. 示例问题；
7. 示例输出；
8. 目录结构；
9. 后续优化方向。

示例问题：

```text
统计各部门接口调用失败率 Top10，并生成分析报告。
分析最近 30 天各项目接口平均响应时间。
找出失败率最高的接口，并给出可能原因。
生成本月接口稳定性分析报告。
```

---

## 禁止事项

不要做以下事情：

* 不要一开始开发复杂前端；
* 不要直接执行未经校验的模型生成 SQL；
* 不要把 API Key 写死在代码中；
* 不要返回数据库密码或敏感信息；
* 不要生成无法运行的大段代码；
* 不要一次性引入过多无关依赖；
* 不要将所有逻辑写在 main.py；
* 不要忽略异常处理；
* 不要只做聊天机器人；
* 不要编造数据分析结论。

---

## 验收标准

项目达到以下标准才算完成第一版：

1. 能通过 FastAPI 接收自然语言问题；
2. 能通过 LangGraph 执行完整流程；
3. 至少有 4 个以上状态节点；
4. 至少有 3 个 LangChain Tool；
5. 能读取 CSV 或 PostgreSQL 数据；
6. 能使用 Pandas 完成失败率 / TopN / 趋势分析；
7. 能生成图表；
8. 能生成结构化报告；
9. 能记录 trace_id 和节点日志；
10. 能处理查询为空和工具调用失败；
11. README 能说明项目如何启动和演示；
12. 项目代码可运行，不只是静态文件。

---

## 面试导向说明

本项目最终服务于 Agent 应用开发 / 大模型应用开发 / AI 后端开发岗位。

实现时请优先突出以下能力：

* LangGraph 状态图编排；
* LangChain Tool 工具封装；
* 自然语言问数；
* SQL 安全执行；
* Pandas 数据分析；
* Agent 执行链路日志；
* 失败兜底；
* FastAPI 后端服务化；
* AI Coding 辅助开发但核心逻辑可解释。

代码应尽量做到：

```text
能运行
能演示
能讲清楚
能被面试追问
```
