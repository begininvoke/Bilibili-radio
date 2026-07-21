from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from database import DEFAULT_DB_PATH, get_connection, init_db
from error_code import APIError
from library_service import utc_now
from models import Track


VALID_PLAY_MODES = {"order", "loop", "single", "shuffle"}


class PlayerQueueService:
    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        init_db(self.db_path)

    def get_queue(self) -> dict[str, Any]:
        with get_connection(self.db_path) as conn:
            state = conn.execute("SELECT * FROM player_queue_state WHERE id = 1").fetchone()
            rows = conn.execute(
                """
                SELECT t.*, qi.position, qi.added_at
                FROM player_queue_items qi
                JOIN tracks t ON t.track_id = qi.track_id
                ORDER BY qi.position ASC
                """
            ).fetchall()

        queue = [self._track_from_row(row).to_dict() for row in rows]
        current_index = int(state["current_index"]) if state else -1
        if not queue:
            current_index = -1
        else:
            current_index = max(-1, min(current_index, len(queue) - 1))

        play_mode = state["play_mode"] if state and state["play_mode"] in VALID_PLAY_MODES else "order"
        return {
            "queue": queue,
            "currentIndex": current_index,
            "playMode": play_mode,
            "updatedAt": state["updated_at"] if state else None,
        }

    def save_queue(
        self,
        tracks: list[Track],
        current_index: int = -1,
        play_mode: str = "order",
    ) -> dict[str, Any]:
        if play_mode not in VALID_PLAY_MODES:
            raise APIError.validation_error("invalid playMode")

        normalized = []
        for track in tracks:
            if not track.track_id or not track.bvid or not track.title:
                continue
            normalized.append(track)

        if not normalized:
            current_index = -1
        else:
            current_index = max(-1, min(int(current_index), len(normalized) - 1))

        now = utc_now()
        with get_connection(self.db_path) as conn:
            for track in normalized:
                conn.execute(
                    """
                    INSERT INTO tracks (
                        track_id, bvid, cid, title, owner, cover, duration, play_count,
                        published_at, page, page_title, source, raw_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(track_id) DO UPDATE SET
                        bvid = excluded.bvid,
                        cid = excluded.cid,
                        title = excluded.title,
                        owner = excluded.owner,
                        cover = excluded.cover,
                        duration = excluded.duration,
                        play_count = excluded.play_count,
                        published_at = excluded.published_at,
                        page = excluded.page,
                        page_title = excluded.page_title,
                        source = excluded.source,
                        raw_json = excluded.raw_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        track.track_id,
                        track.bvid,
                        track.cid,
                        track.title,
                        track.owner,
                        track.cover,
                        track.duration,
                        track.play_count,
                        track.published_at,
                        track.page,
                        track.page_title,
                        track.source,
                        None,
                        now,
                    ),
                )

            conn.execute("DELETE FROM player_queue_items")
            for position, track in enumerate(normalized):
                conn.execute(
                    """
                    INSERT INTO player_queue_items (position, track_id, added_at)
                    VALUES (?, ?, ?)
                    """,
                    (position, track.track_id, now),
                )

            conn.execute(
                """
                INSERT INTO player_queue_state (id, current_index, play_mode, updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    current_index = excluded.current_index,
                    play_mode = excluded.play_mode,
                    updated_at = excluded.updated_at
                """,
                (current_index, play_mode, now),
            )

        return self.get_queue()

    def clear_queue(self) -> dict[str, Any]:
        return self.save_queue([], current_index=-1, play_mode="order")

    @staticmethod
    def _track_from_row(row: Any) -> Track:
        return Track(
            track_id=row["track_id"],
            bvid=row["bvid"],
            cid=row["cid"],
            title=row["title"],
            owner=row["owner"],
            cover=row["cover"],
            duration=row["duration"],
            play_count=row["play_count"],
            published_at=row["published_at"],
            page=row["page"],
            page_title=row["page_title"],
            source=row["source"],
        )
