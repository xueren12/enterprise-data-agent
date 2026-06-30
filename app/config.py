from pathlib import Path
import os

from dotenv import load_dotenv

from app.catalog.schema_registry import get_queryable_columns, list_queryable_tables


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHART_DIR = BASE_DIR / "charts"
REPORT_DIR = BASE_DIR / "reports"
TASK_DIR = DATA_DIR / "tasks"
SAMPLE_API_LOGS_PATH = DATA_DIR / "sample_api_logs.csv"
PROMPT_DIR = BASE_DIR / "app" / "prompts"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

DATABASE_URL = os.getenv("DATABASE_URL", "")
DEFAULT_DATA_SOURCE = os.getenv("DEFAULT_DATA_SOURCE", "auto").lower()
SQL_MAX_LIMIT = int(os.getenv("SQL_MAX_LIMIT", "200"))
SQL_MAX_RETRIES = int(os.getenv("SQL_MAX_RETRIES", "2"))
SQL_ALLOWED_TABLES = list_queryable_tables()
SQL_ALLOWED_COLUMNS = get_queryable_columns("api_call_logs")
