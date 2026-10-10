import os

# Tests never call Claude or LangSmith; keep tracing off even if .env enables it.
os.environ["LANGSMITH_TRACING"] = "false"
