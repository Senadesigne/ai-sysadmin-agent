from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Repo root = .../app/config/settings.py -> parents[2] == repo root
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"

print(f"[ENV] Loading .env from: {ENV_PATH} (exists={ENV_PATH.exists()})")
load_dotenv(dotenv_path=ENV_PATH, override=False)  # Don't override existing env vars (for testing)

# Allow override, default to repo-root/.data
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT_DIR / ".data"))).expanduser().resolve()

CHAINLIT_DB_PATH = DATA_DIR / "chainlit.db"
INVENTORY_DB_PATH = DATA_DIR / "inventory.db"
CHROMA_DIR = DATA_DIR / "chroma_db"
TMP_DIR = DATA_DIR / "tmp"


# Auth configuration
AUTH_MODE = os.getenv("AUTH_MODE", "dev").lower()  # dev | prod
DEV_NO_AUTH = os.getenv("DEV_NO_AUTH", "true").lower() in ("1", "true", "yes")

ADMIN_IDENTIFIER = os.getenv("ADMIN_IDENTIFIER", "admin")  # not secret
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")  # secret in .env only

# PRODUCTION SAFETY GUARD: Prevent DEV_ADMIN_BYPASS in production
DEV_ADMIN_BYPASS = os.getenv("DEV_ADMIN_BYPASS", "0").lower() in ("1", "true", "yes")

if AUTH_MODE == "prod" and DEV_ADMIN_BYPASS:
    raise RuntimeError(
        "SECURITY ERROR: DEV_ADMIN_BYPASS must NEVER be enabled in production (AUTH_MODE=prod). "
        "This flag bypasses user isolation in list_threads() and creates data leak vulnerabilities. "
        "Set DEV_ADMIN_BYPASS=0 or remove it from environment."
    )

if DEV_ADMIN_BYPASS:
    print("[SECURITY WARNING] DEV_ADMIN_BYPASS is enabled (dev/admin debugging only). NEVER use in production.")
    print("[SECURITY WARNING] User isolation in list_threads() is BYPASSED. All threads are visible.")

# RAG configuration
RAG_ENABLED = os.getenv("RAG_ENABLED", "false").lower() in ("1", "true", "yes")

# Debug configuration
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

# Production-grade capability flags
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() in ("1", "true", "yes")
ENABLE_EVENTS = os.getenv("ENABLE_EVENTS", "true").lower() in ("1", "true", "yes")
ENABLE_AUDIT = os.getenv("ENABLE_AUDIT", "true").lower() in ("1", "true", "yes")
EXECUTION_ENABLED = os.getenv("EXECUTION_ENABLED", "false").lower() in ("1", "true", "yes")


def ensure_data_dirs() -> None:
    """Ensure all product data directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)