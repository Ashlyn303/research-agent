import os
import sys
from pathlib import Path

# Tests never call Claude or LangSmith; keep tracing off even if .env enables it.
os.environ["LANGSMITH_TRACING"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
