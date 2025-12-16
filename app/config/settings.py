from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Repo root = .../app/config/settings.py -> parents[2] == repo root
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"

print(f"[ENV] Loading .env from: {ENV_PATH} (exists={ENV_PATH.exists()})")
load_dotenv(dotenv_path=ENV_PATH, override=True)

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


def ensure_data_dirs() -> None:
    """Ensure all product data directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)