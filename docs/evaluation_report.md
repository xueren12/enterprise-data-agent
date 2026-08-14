# 可复现评测说明

本仓库将“确定性规则与安全回归”同“真实 LLM 规划质量”严格分开，避免把程序自己生成的固定句式用例包装成模型准确率。

## 规则与安全回归集

`evaluation/cases.py` 生成 150 条固定规则用例和 12 条异常用例。它验证本地规则兜底、QueryPlan 校验、受控 SQL 构建、安全校验和可选的 PostgreSQL 只读执行；不调用 DeepSeek，也不代表模型的自然语言理解能力。

```powershell
python evaluation/run_evaluation.py --mode rule

docker compose up -d postgres
python evaluation/run_evaluation.py --mode rule `
  --database-url "postgresql+psycopg://agent_reader:agent_reader_password@localhost:15432/agent_db"
```

输出写入 `evaluation/results/rule-safety-latest.json`。其中的成功率只能描述为“规则与 SQL 安全回归通过率”。

## 人工标注 LLM QueryPlan 评测集

`evaluation/datasets/query_plan_gold.jsonl` 包含 24 条人工编写、人工标注的不同表达问题，覆盖 6 类指标、部门/项目/接口/时间筛选条件和 TopN。它不是由评测逻辑批量套模板生成。

运行时，脚本会真实调用 DeepSeek，让模型在 Registry 白名单内返回 QueryPlan，并逐条统计：

- `model_query_plan_validation`：模型输出被 Pydantic、Schema Registry 和 Metric Registry 接受的比例；
- `semantic_match_to_human_gold`：`intent`、`filters`、`top_n` 与人工金标完全一致的比例；
- `controlled_sql_validation_after_semantic_match`：由通过金标的 QueryPlan 构造的受控 SQL 是否通过 sqlglot 与计划一致性校验；
- `controlled_sql_execution_after_semantic_match`：可选 PostgreSQL 只读实际执行是否返回结果。

```powershell
copy .env.example .env
# 在 .env 中填入 DEEPSEEK_API_KEY
python evaluation/run_evaluation.py --mode llm

docker compose up -d postgres
python evaluation/run_evaluation.py --mode llm `
  --database-url "postgresql+psycopg://agent_reader:agent_reader_password@localhost:15432/agent_db"
```

结果写入 `evaluation/results/llm-query-plan-latest.json`。该文件被 `.gitignore` 忽略，避免提交包含时间戳、模型运行环境和可能失败详情的临时结果。简历和 README 只应引用在固定模型、固定金标、固定运行日期下保存并复现的真实结果，不能把规则回归集的 100% 写成 LLM 指标。

### 已提交的真实运行基线

[`llm-deepseek-postgresql-gold-2026-08-14.json`](../evaluation/results/llm-deepseek-postgresql-gold-2026-08-14.json) 记录了一次使用 `temperature=0` 的实际 DeepSeek 调用和 PostgreSQL 实执行结果：24 条人工金标中，24 条模型输出通过 QueryPlan 校验和 Registry 规范化，18 条与人工金标的意图、筛选条件和 TopN 完全一致（75.00%）；这 18 条产生的受控 SQL 均通过安全校验并以只读账号在 PostgreSQL 成功执行。该指标仅适用于该日期、模型配置、24 条金标集和当前数据版本。

## 指标边界

受控 SQL 是程序根据通过校验的 QueryPlan 构造的，不是直接执行模型任意生成的 SQL。模型生成 SQL 的在线链路仍会经过 sqlglot、白名单、LIMIT、只读事务和失败修复重试；因此“受控 SQL 执行成功率”不能表述为“模型自由生成 SQL 成功率”。
