CREATE TABLE IF NOT EXISTS api_call_logs (
    id BIGINT PRIMARY KEY,
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

COPY api_call_logs (
    id,
    department,
    project_name,
    api_name,
    status,
    status_code,
    latency_ms,
    request_time,
    error_message
)
FROM '/docker-entrypoint-initdb.d/sample_api_logs.csv'
WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8');

CREATE ROLE agent_reader LOGIN PASSWORD 'agent_reader_password';
GRANT CONNECT ON DATABASE agent_db TO agent_reader;
GRANT USAGE ON SCHEMA public TO agent_reader;
GRANT SELECT ON TABLE api_call_logs TO agent_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO agent_reader;
