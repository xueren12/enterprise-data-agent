CREATE TABLE IF NOT EXISTS api_call_logs (
    id BIGSERIAL PRIMARY KEY,
    department VARCHAR(100) NOT NULL,
    project_name VARCHAR(100) NOT NULL,
    api_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'failed')),
    status_code INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    request_time TIMESTAMP NOT NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_call_logs_department
    ON api_call_logs (department);

CREATE INDEX IF NOT EXISTS idx_api_call_logs_request_time
    ON api_call_logs (request_time);

INSERT INTO api_call_logs (
    department,
    project_name,
    api_name,
    status,
    status_code,
    latency_ms,
    request_time,
    error_message
)
SELECT *
FROM (
    VALUES
        ('销售部', '客户关系系统', '/api/customer/search', 'success', 200, 126, TIMESTAMP '2026-05-01 09:12:31', NULL),
        ('销售部', '客户关系系统', '/api/customer/search', 'failed', 500, 812, TIMESTAMP '2026-05-01 09:14:08', '数据库超时'),
        ('财务部', '财务系统', '/api/payment/reconcile', 'failed', 500, 940, TIMESTAMP '2026-05-02 15:17:09', '空指针异常'),
        ('财务部', '财务系统', '/api/budget/query', 'success', 200, 219, TIMESTAMP '2026-05-03 16:04:12', NULL),
        ('运维部', '运维中心', '/api/device/event', 'failed', 503, 720, TIMESTAMP '2026-05-02 01:14:00', '服务过载'),
        ('运维部', '运维中心', '/api/alert/list', 'success', 200, 138, TIMESTAMP '2026-05-04 03:15:30', NULL),
        ('风控部', '风控系统', '/api/risk/score', 'failed', 504, 1324, TIMESTAMP '2026-05-01 12:03:54', '模型调用超时'),
        ('风控部', '风控系统', '/api/risk/report', 'success', 200, 421, TIMESTAMP '2026-05-04 12:48:17', NULL),
        ('平台部', '网关平台', '/api/gateway/route', 'failed', 502, 512, TIMESTAMP '2026-05-02 06:20:45', '网关转发失败'),
        ('平台部', '网关平台', '/api/health', 'success', 200, 42, TIMESTAMP '2026-05-04 06:35:20', NULL)
) AS seed_data (
    department,
    project_name,
    api_name,
    status,
    status_code,
    latency_ms,
    request_time,
    error_message
)
WHERE NOT EXISTS (SELECT 1 FROM api_call_logs);
