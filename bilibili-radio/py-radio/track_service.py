from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from models import Track, VideoDetail, VideoInfo, normalize_bvid


TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return TAG_RE.sub("", html.unescape(str(value))).strip()


def normalize_cover(url: Any) -> str:
    if not url:
        return ""
    value = str(url).strip()
    if value.startswith("//"):
        return f"https:{value}"
    return value


def parse_duration(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    parts = text.split(":")
    if all(part.isdigit() for part in parts):
        seconds = 0
        for part in parts:
            seconds = seconds * 60 + int(part)
        return seconds
    return 0


def format_pubdate(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return str(value)
    china_tz = timezone(timedelta(hours=8))
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(china_tz).isoformat()


def normalize_search_item(item: dict[str, Any]) -> Track:
    return Track(
        bvid=str(item.get("bvid") or item.get("arcurl", "").split("/")[-1]).strip(),
        title=clean_text(item.get("title")),
        owner=clean_text(item.get("author") or item.get("owner", {}).get("name")),
        cover=normalize_cover(item.get("pic")),
        duration=parse_duration(item.get("duration")),
        play_count=int(item.get("play") or item.get("play_count") or 0),
        published_at=format_pubdate(item.get("pubdate") or item.get("senddate")),
    )


def normalize_video_detail(data: dict[str, Any]) -> VideoDetail:
    bvid = normalize_bvid(str(data.get("bvid", "")))
    title = clean_text(data.get("title"))
    owner = clean_text(data.get("owner", {}).get("name"))
    cover = normalize_cover(data.get("pic"))
    duration = parse_duration(data.get("duration"))
    play_count = int(data.get("stat", {}).get("view") or 0)
    published_at = format_pubdate(data.get("pubdate") or data.get("ctime"))
    default_cid = int(data.get("cid") or 0)

    info = VideoInfo(
        bvid=bvid,
        cid=default_cid,
        title=title,
        duration=duration,
        owner=owner,
        cover=cover,
        play_count=play_count,
        published_at=published_at,
    )

    pages: list[Track] = []
    for page_item in data.get("pages") or []:
        cid = int(page_item.get("cid") or 0)
        page_no = int(page_item.get("page") or len(pages) + 1)
        page_title = clean_text(page_item.get("part"))
        track_title = title if len(data.get("pages") or []) <= 1 else f"{title} - {page_title}"
        pages.append(
            Track(
                bvid=bvid,
                cid=cid,
                title=track_title,
                owner=owner,
                cover=cover,
                duration=parse_duration(page_item.get("duration")),
                play_count=play_count,
                published_at=published_at,
                page=page_no,
                page_title=page_title,
            )
        )

    if not pages and default_cid:
        pages.append(info.to_track())

    return VideoDetail(info=info, pages=pages)
