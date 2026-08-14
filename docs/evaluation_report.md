# 可复现评测基线

评测只使用仓库内的合成问题和本地确定性规则，不依赖 DeepSeek API，因此同一代码和数据版本可重复运行。

| 指标 | 样本数 | 基线结果 | 评测方式 |
| --- | ---: | ---: | --- |
| QueryPlan 解析与校验成功率 | 150 | 100.00% | 规则解析、Schema Registry、Metric Registry、Pydantic 校验 |
| 受控 SQL 校验通过率 | 150 | 100.00% | QueryPlan 构建 SQL，sqlglot 进行安全与一致性校验 |
| PostgreSQL SQL 实际执行成功率 | 150 | 100.00% | `agent_reader` 只读账号连接 Docker PostgreSQL 执行 |
| 异常兜底命中率 | 12 | 100.00% | 非支持领域和危险意图应返回友好 fallback |

基线原始结果见 [postgresql-baseline.json](../evaluation/results/postgresql-baseline.json)。

```powershell
# 离线：验证 QueryPlan、SQL 校验和异常兜底
py -3.11 evaluation/run_evaluation.py

# 启动 PostgreSQL 后：额外验证 SQL 实际执行率
docker compose up -d postgres
py -3.11 evaluation/run_evaluation.py `
  --database-url "postgresql+psycopg://agent_reader:agent_reader_password@localhost:15432/agent_db"
```

评测指标刻意区分“SQL 校验通过”和“数据库实际执行成功”。没有配置数据库时，报告会明确标记 SQL 执行指标为 `skipped`，不会把校验结果冒充执行结果。
