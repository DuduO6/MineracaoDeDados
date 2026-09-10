"""Central configuration, optionally overridden with environment variables."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    # Match generation and validation remain usable before optional dependencies
    # are installed. The collectors still require requirements.txt.
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"\''))

RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
REFERENCE_DIR = ROOT_DIR / "data" / "reference"
OUTPUTS_DIR = ROOT_DIR / "outputs"

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CLIENT_SECRETS = ROOT_DIR / os.getenv("YOUTUBE_CLIENT_SECRETS", "secrets.json")
YOUTUBE_TOKEN_FILE = ROOT_DIR / os.getenv("YOUTUBE_TOKEN_FILE", "token.json")
PRE_GAME_DAYS = int(os.getenv("PRE_GAME_DAYS", "3"))
POST_GAME_DAYS = int(os.getenv("POST_GAME_DAYS", "3"))
MATCH_DURATION_MINUTES = int(os.getenv("MATCH_DURATION_MINUTES", "120"))
MAX_PRE_GAME_VIDEOS_PER_MATCH = int(os.getenv("MAX_PRE_GAME_VIDEOS_PER_MATCH", "5"))
MAX_POST_GAME_VIDEOS_PER_MATCH = int(os.getenv("MAX_POST_GAME_VIDEOS_PER_MATCH", "5"))
_comment_limit = os.getenv("MAX_COMMENTS_PER_VIDEO", "").strip()
MAX_COMMENTS_PER_VIDEO: Optional[int] = int(_comment_limit) if _comment_limit else None
ANONYMIZE_USERS = os.getenv("ANONYMIZE_USERS", "true").lower() in {"1", "true", "yes"}
ANONYMIZATION_SALT = os.getenv("ANONYMIZATION_SALT", "local-research-salt")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
REQUEST_RETRIES = int(os.getenv("REQUEST_RETRIES", "4"))

for directory in (RAW_DIR, PROCESSED_DIR, REFERENCE_DIR, OUTPUTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
