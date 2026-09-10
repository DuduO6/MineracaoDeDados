"""Shared CSV, logging and collection-metadata helpers."""
from __future__ import annotations

import csv
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from config import settings

SENSITIVE_QUERY = re.compile(r"([?&](?:key|access_token)=)[^&\s;]+", re.IGNORECASE)


def sanitize_metadata(value: object) -> object:
    """Remove credentials accidentally included in exception URLs."""
    if isinstance(value, str):
        return SENSITIVE_QUERY.sub(r"\1[REDACTED]", value)
    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_metadata(item) for key, item in value.items()}
    return value


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def ensure_csv(path: Path, fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=fields).writeheader()


def read_ids(path: Path, key: str) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as handle:
        return {row[key] for row in csv.DictReader(handle) if row.get(key)}


def append_rows(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, object]]) -> int:
    ensure_csv(path, fields)
    count = 0
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        for row in rows:
            writer.writerow(row)
            handle.flush()
            count += 1
    return count


def write_csv_atomic(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def update_summary(**values: object) -> None:
    path = settings.OUTPUTS_DIR / "collection_summary.json"
    current: dict[str, object] = {}
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logging.warning("Ignoring invalid collection summary")
    new_errors = values.pop("errors", None)
    current = sanitize_metadata(current)  # type: ignore[assignment]
    values = sanitize_metadata(values)  # type: ignore[assignment]
    current.update(values)
    if new_errors is not None:
        combined = list(current.get("errors", [])) + list(new_errors)  # type: ignore[arg-type]
        current["errors"] = list({json.dumps(item, sort_keys=True): item for item in combined}.values())
    current["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    current["parameters"] = {
        "pre_game_days": settings.PRE_GAME_DAYS,
        "post_game_days": settings.POST_GAME_DAYS,
        "match_duration_minutes": settings.MATCH_DURATION_MINUTES,
        "max_pre_game_videos_per_match": settings.MAX_PRE_GAME_VIDEOS_PER_MATCH,
        "max_post_game_videos_per_match": settings.MAX_POST_GAME_VIDEOS_PER_MATCH,
        "max_comments_per_video": settings.MAX_COMMENTS_PER_VIDEO,
        "anonymize_users": settings.ANONYMIZE_USERS,
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
