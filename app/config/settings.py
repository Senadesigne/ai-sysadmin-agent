from __future__ import annotations

import os
from pathlib import Path

# Repo root = .../app/config/settings.py -> parents[2] == repo root
ROOT_DIR = Path(__file__).resolve().parents[2]

# Allow override, default to repo-root/.data
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT_DIR / ".data"))).expanduser().resolve()

CHAINLIT_DB_PATH = DATA_DIR / "chainlit.db"
INVENTORY_DB_PATH = DATA_DIR / "inventory.db"
CHROMA_DIR = DATA_DIR / "chroma_db"
TMP_DIR = DATA_DIR / "tmp"


def ensure_data_dirs() -> None:
    """Ensure all product data directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)