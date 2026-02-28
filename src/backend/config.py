import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "24"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
CACHE_DB_PATH: str = os.getenv("CACHE_DB_PATH", "cache.db")

# Claude model to use for narrative generation
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

# Verdict thresholds
VERDICT_STRONG_BUY = 75.0
VERDICT_BUY = 55.0
VERDICT_HOLD = 40.0
