"""Runtime configuration, read from environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
SOURCES_DIR = DATA_DIR / "sources"   # generated "raw" project files (xlsx, xml, pdf)
INBOX_DIR = DATA_DIR / "inbox"       # sample files for the live-ingestion demo
UPLOADS_DIR = DATA_DIR / "uploads"   # files uploaded through the Ingest screen
DB_PATH = DATA_DIR / "conduto.db"

# Bump when the synthetic dataset changes so deployments reseed automatically.
SEED_VERSION = "2026.09.28-6"

# Month of the latest closed cost cut-off in the synthetic dataset.
STATUS_PERIOD = "2026-08"

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")
# Q&A and extraction are latency-sensitive in a live demo; tune per deployment.
ANTHROPIC_EFFORT = os.getenv("ANTHROPIC_EFFORT", "medium")

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]


def ai_enabled() -> bool:
    if os.getenv("AI_DISABLED") == "1":
        return False
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


for _d in (DATA_DIR, SOURCES_DIR, INBOX_DIR, UPLOADS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
