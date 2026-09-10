"""Collect top-level comments and every available reply incrementally."""
from __future__ import annotations

import csv
import hashlib
import logging
from collections import Counter
from typing import Any, Iterator

from config import settings
from src.common import append_rows, configure_logging, ensure_csv, read_ids, update_summary
from src.youtube.youtube_client import YouTubeClient, YouTubeError

LOG = logging.getLogger(__name__)
FIELDS = ["comment_id", "video_id", "match_id", "author_channel_id", "author_name", "text", "published_at", "updated_at", "like_count", "reply_count", "is_reply", "parent_comment_id", "parent_author_channel_id", "period", "team_result_context"]


def author_id(snippet: dict[str, Any]) -> str:
    raw = snippet.get("authorChannelId", {}).get("value", "")
    if not raw:
        raw = "missing:" + snippet.get("authorDisplayName", "unknown")
    if settings.ANONYMIZE_USERS:
        return hashlib.sha256(f"{settings.ANONYMIZATION_SALT}:{raw}".encode()).hexdigest()
    return raw


def make_row(comment: dict[str, Any], video: dict[str, str], result: str, *, is_reply: bool, parent_id: str = "", parent_author: str = "") -> dict[str, object]:
    snippet = comment["snippet"]
    return {
        "comment_id": comment["id"], "video_id": video["video_id"], "match_id": video["match_id"],
        "author_channel_id": author_id(snippet), "author_name": snippet.get("authorDisplayName", ""),
        "text": snippet.get("textOriginal", snippet.get("textDisplay", "")), "published_at": snippet.get("publishedAt", ""),
        "updated_at": snippet.get("updatedAt", ""), "like_count": snippet.get("likeCount", 0),
        "reply_count": 0 if is_reply else snippet.get("totalReplyCount", 0), "is_reply": str(is_reply).lower(),
        "parent_comment_id": parent_id, "parent_author_channel_id": parent_author,
        "period": video["period"], "team_result_context": result,
    }


def collect_video(client: YouTubeClient, video: dict[str, str], result: str, known: set[str]) -> Iterator[dict[str, object]]:
    emitted = 0
    for page in client.pages("commentThreads", part="snippet", videoId=video["video_id"], maxResults=100, textFormat="plainText", order="time"):
        for thread in page.get("items", []):
            top = thread["snippet"]["topLevelComment"]
            top_row = make_row(top, video, result, is_reply=False)
            parent_author = str(top_row["author_channel_id"])
            if top["id"] not in known:
                yield top_row
                known.add(top["id"])
                emitted += 1
                if settings.MAX_COMMENTS_PER_VIDEO is not None and emitted >= settings.MAX_COMMENTS_PER_VIDEO:
                    return
            total_replies = int(thread["snippet"].get("totalReplyCount", 0))
            if total_replies:
                for reply_page in client.pages("comments", part="snippet", parentId=top["id"], maxResults=100, textFormat="plainText"):
                    for reply in reply_page.get("items", []):
                        if reply["id"] not in known:
                            yield make_row(reply, video, result, is_reply=True, parent_id=top["id"], parent_author=parent_author)
                            known.add(reply["id"])
                            emitted += 1
                            if settings.MAX_COMMENTS_PER_VIDEO is not None and emitted >= settings.MAX_COMMENTS_PER_VIDEO:
                                return
            if settings.MAX_COMMENTS_PER_VIDEO is not None and emitted >= settings.MAX_COMMENTS_PER_VIDEO:
                return


def main() -> None:
    configure_logging()
    videos_path, matches_path = settings.RAW_DIR / "videos.csv", settings.RAW_DIR / "matches.csv"
    if not videos_path.exists() or not matches_path.exists():
        raise FileNotFoundError("Run match and video collection first")
    with videos_path.open(encoding="utf-8", newline="") as handle:
        videos = list(csv.DictReader(handle))
    with matches_path.open(encoding="utf-8", newline="") as handle:
        matches = {row["match_id"]: row for row in csv.DictReader(handle)}
    output = settings.RAW_DIR / "comments.csv"
    ensure_csv(output, FIELDS)
    known = read_ids(output, "comment_id")
    client = YouTubeClient()
    disabled: list[str] = []
    errors: list[dict[str, str]] = []
    for video in videos:
        match = matches[video["match_id"]]
        result = f'atletico_{match["result_atletico"]}'
        try:
            count = append_rows(output, FIELDS, collect_video(client, video, result, known))
            LOG.info("%s: %d new comments/replies", video["video_id"], count)
        except YouTubeError as exc:
            message = str(exc)
            if "commentsDisabled" in message or "disabled comments" in message.lower():
                disabled.append(video["video_id"])
                LOG.warning("Comments disabled: %s", video["video_id"])
            else:
                errors.append({"stage": "comments", "video_id": video["video_id"], "error": message})
                LOG.exception("Comment collection failed for %s", video["video_id"])
    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    counts = Counter(row["is_reply"] for row in rows)
    update_summary(comments=len(rows) - counts["true"], replies=counts["true"], unique_users=len({r["author_channel_id"] for r in rows}), videos_comments_disabled=disabled, errors=errors)


if __name__ == "__main__":
    main()
