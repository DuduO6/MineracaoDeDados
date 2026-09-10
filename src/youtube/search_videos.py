"""Find, filter, rank, and select match-specific YouTube videos."""
from __future__ import annotations

import csv
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config import settings
from src.common import configure_logging, update_summary, write_csv_atomic
from src.youtube.youtube_client import YouTubeClient, YouTubeError

LOG = logging.getLogger(__name__)
FIELDS = ["video_id", "match_id", "title", "description", "channel_id", "channel_name", "published_at", "period", "views", "likes", "comment_count", "url", "search_query"]
EXCLUDED = re.compile(r"\b(fifa|ea\s*fc|efootball|sub[- ]?\d+|feminino|base|hist[oó]ric[oa]|shorts?)\b", re.I)
TEAM_A = re.compile(r"atl[eé]tico(?:-mg| mineiro)?|\bgalo\b", re.I)
TEAM_B = re.compile(r"cruzeiro|\braposa\b", re.I)


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def queries(match: dict[str, str]) -> list[str]:
    date = datetime.fromisoformat(match["match_date"]).strftime("%d/%m/%Y")
    comp = match["competition"].split(" - ")[0]
    fixture = f'{match["home_team"]} x {match["away_team"]}'
    return [f'"{fixture}" {date}', f'"{fixture}" {comp}', f'Atlético Cruzeiro pré jogo {date}', f'Atlético Cruzeiro pós jogo melhores momentos {date}']


def period_for(published: datetime, kickoff: datetime) -> str | None:
    published = published.astimezone(kickoff.tzinfo)
    if kickoff - timedelta(days=settings.PRE_GAME_DAYS) <= published < kickoff:
        return "pre_game"
    if kickoff <= published <= kickoff + timedelta(days=settings.POST_GAME_DAYS):
        return "post_game"
    return None


def relevance(item: dict[str, Any]) -> float:
    text = f'{item["title"]} {item["description"]}'
    direct = 50 if TEAM_A.search(text) and TEAM_B.search(text) else 0
    views = int(item.get("views", 0))
    comments = int(item.get("comment_count", 0))
    return direct + min(20, views / 50_000) + min(20, comments / 500) + (5 if re.search(r"cl[aá]ssico|melhores momentos|p[oó]s[- ]?jogo|pr[eé][- ]?jogo", text, re.I) else 0)


def candidates_for(client: YouTubeClient, match: dict[str, str]) -> list[dict[str, Any]]:
    kickoff = parse_dt(match["match_datetime"])
    found: dict[str, dict[str, Any]] = {}
    published_after = (kickoff - timedelta(days=settings.PRE_GAME_DAYS)).isoformat()
    published_before = (kickoff + timedelta(days=settings.POST_GAME_DAYS)).isoformat()
    for query in queries(match):
        page = client.get("search", part="snippet", q=query, type="video", maxResults=50, order="relevance", publishedAfter=published_after, publishedBefore=published_before)
        for result in page.get("items", []):
            snippet = result["snippet"]
            video_id = result["id"]["videoId"]
            found.setdefault(video_id, {"video_id": video_id, "match_id": match["match_id"], "title": snippet["title"], "description": snippet.get("description", ""), "channel_id": snippet["channelId"], "channel_name": snippet["channelTitle"], "published_at": snippet["publishedAt"], "search_query": query})
    ids = list(found)
    for start in range(0, len(ids), 50):
        details = client.get("videos", part="statistics,snippet,contentDetails", id=",".join(ids[start:start + 50]), maxResults=50)
        for detail in details.get("items", []):
            row = found[detail["id"]]
            stats = detail.get("statistics", {})
            row.update(views=int(stats.get("viewCount", 0)), likes=int(stats.get("likeCount", 0)), comment_count=int(stats.get("commentCount", 0)))
    accepted = []
    for row in found.values():
        text = f'{row["title"]} {row["description"]}'
        period = period_for(parse_dt(row["published_at"]), kickoff)
        if period and TEAM_A.search(text) and TEAM_B.search(text) and not EXCLUDED.search(text):
            row.update(period=period, url=f'https://www.youtube.com/watch?v={row["video_id"]}')
            accepted.append(row)
    return accepted


def main() -> None:
    configure_logging()
    matches_path = settings.RAW_DIR / "matches.csv"
    if not matches_path.exists():
        raise FileNotFoundError("Run python -m src.matches.collect_matches first")
    with matches_path.open(encoding="utf-8", newline="") as handle:
        matches = list(csv.DictReader(handle))
    client = YouTubeClient()
    selected: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    found_count = 0
    for match in matches:
        try:
            candidates = candidates_for(client, match)
            found_count += len(candidates)
            for period, limit in (("pre_game", settings.MAX_PRE_GAME_VIDEOS_PER_MATCH), ("post_game", settings.MAX_POST_GAME_VIDEOS_PER_MATCH)):
                ranked = sorted((x for x in candidates if x["period"] == period), key=relevance, reverse=True)
                selected.extend(ranked[:limit])
            LOG.info("%s: %d candidates", match["match_id"], len(candidates))
        except YouTubeError as exc:
            LOG.exception("Could not search %s", match["match_id"])
            errors.append({"stage": "video_search", "match_id": match["match_id"], "error": str(exc)})
    unique = {row["video_id"]: row for row in selected}
    write_csv_atomic(settings.RAW_DIR / "videos.csv", FIELDS, unique.values())
    update_summary(videos_found=found_count, videos_selected=len(unique), errors=errors)


if __name__ == "__main__":
    main()
