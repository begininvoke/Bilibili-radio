from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from database import DEFAULT_DB_PATH, get_connection, init_db
from error_code import APIError
from models import Track, make_track_id, normalize_bvid


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class LibraryService:
    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        init_db(self.db_path)

    def upsert_track(self, track: Track, raw: Optional[dict[str, Any]] = None) -> Track:
        if not track.bvid or not track.title:
            raise APIError.validation_error("track bvid and title are required")
        now = utc_now()
        with get_connection(self.db_path) as conn:
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
                    json.dumps(raw or track.to_dict(), ensure_ascii=False),
                    now,
                ),
            )
        return track

    def get_track(self, track_id: str) -> Optional[Track]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM tracks WHERE track_id = ?", (track_id,)).fetchone()
        return self._track_from_row(row) if row else None

    def find_tracks_by_bvid(self, bvid: str) -> list[Track]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM tracks WHERE bvid = ? ORDER BY COALESCE(page, 999999), cid",
                (normalize_bvid(bvid),),
            ).fetchall()
        return [self._track_from_row(row) for row in rows]

    def list_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT t.*, r.last_played_at, r.play_count AS recent_play_count,
                       r.position_ms, r.listen_ms, r.completed
                FROM recent r
                JOIN tracks t ON t.track_id = r.track_id
                ORDER BY r.last_played_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._track_payload_with_meta(row) for row in rows]

    def clear_recent(self) -> dict[str, Any]:
        with get_connection(self.db_path) as conn:
            recent = conn.execute("DELETE FROM recent")
            playback_recent = conn.execute("DELETE FROM playback_recent")
        return {
            "removed": recent.rowcount,
            "playbackRemoved": playback_recent.rowcount,
        }

    def add_recent(
        self,
        track: Track,
        position_ms: int = 0,
        listen_ms: int = 0,
        completed: bool = False,
    ) -> dict[str, Any]:
        self.upsert_track(track)
        now = utc_now()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO recent (
                    track_id, last_played_at, play_count, position_ms, listen_ms, completed
                )
                VALUES (?, ?, 1, ?, ?, ?)
                ON CONFLICT(track_id) DO UPDATE SET
                    last_played_at = excluded.last_played_at,
                    play_count = recent.play_count + 1,
                    position_ms = excluded.position_ms,
                    listen_ms = MAX(recent.listen_ms, excluded.listen_ms),
                    completed = excluded.completed
                """,
                (track.track_id, now, int(position_ms), int(listen_ms), int(completed)),
            )
        return {"track": track.to_dict(), "lastPlayedAt": now}

    def list_likes(self) -> list[dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT t.*, l.created_at
                FROM likes l
                JOIN tracks t ON t.track_id = l.track_id
                ORDER BY l.created_at DESC
                """
            ).fetchall()
        return [
            {**self._track_from_row(row).to_dict(), "likedAt": row["created_at"]}
            for row in rows
        ]

    def add_like(self, track: Track) -> dict[str, Any]:
        self.upsert_track(track)
        now = utc_now()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO likes (track_id, created_at)
                VALUES (?, ?)
                ON CONFLICT(track_id) DO NOTHING
                """,
                (track.track_id, now),
            )
        return {"track": track.to_dict(), "likedAt": now}

    def is_liked(self, bvid: str, cid: Optional[int] = None) -> bool:
        with get_connection(self.db_path) as conn:
            if cid is None:
                row = conn.execute(
                    """
                    SELECT 1
                    FROM likes l
                    JOIN tracks t ON t.track_id = l.track_id
                    WHERE t.bvid = ?
                    LIMIT 1
                    """,
                    (normalize_bvid(bvid),),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT 1 FROM likes WHERE track_id = ? LIMIT 1",
                    (make_track_id(bvid, cid),),
                ).fetchone()
        return row is not None

    def remove_like(self, bvid: str, cid: Optional[int] = None) -> int:
        with get_connection(self.db_path) as conn:
            if cid is None:
                rows = conn.execute(
                    """
                    DELETE FROM likes
                    WHERE track_id IN (SELECT track_id FROM tracks WHERE bvid = ?)
                    """,
                    (normalize_bvid(bvid),),
                )
            else:
                rows = conn.execute(
                    "DELETE FROM likes WHERE track_id = ?",
                    (make_track_id(bvid, cid),),
                )
            return rows.rowcount

    def list_playlists(self) -> list[dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            playlists = conn.execute(
                "SELECT * FROM playlists ORDER BY created_at DESC"
            ).fetchall()
        return [self.get_playlist(row["id"]) for row in playlists]

    def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        with get_connection(self.db_path) as conn:
            playlist = conn.execute(
                "SELECT * FROM playlists WHERE id = ?",
                (playlist_id,),
            ).fetchone()
            if not playlist:
                raise APIError.not_found(f"Playlist not found: {playlist_id}")
            item_rows = conn.execute(
                """
                SELECT t.*, pi.position, pi.added_at
                FROM playlist_items pi
                JOIN tracks t ON t.track_id = pi.track_id
                WHERE pi.playlist_id = ?
                ORDER BY pi.position ASC, pi.added_at ASC
                """,
                (playlist_id,),
            ).fetchall()
        tracks = [
            {**self._track_from_row(row).to_dict(), "addedAt": row["added_at"]}
            for row in item_rows
        ]
        return {
            "id": playlist["id"],
            "name": playlist["name"],
            "cover": playlist["cover"],
            "tracks": tracks,
            "createdAt": playlist["created_at"],
            "updatedAt": playlist["updated_at"],
        }

    def create_playlist(self, name: str, tracks: Optional[list[Track]] = None) -> dict[str, Any]:
        name = (name or "").strip()
        if not name:
            raise APIError.validation_error("playlist name is required")

        playlist_id = f"pl_{uuid.uuid4().hex[:12]}"
        now = utc_now()
        cover = tracks[0].cover if tracks else None
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO playlists (id, name, cover, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (playlist_id, name, cover, now, now),
            )
        if tracks:
            self.batch_add_playlist_items(playlist_id, tracks=tracks)
        return self.get_playlist(playlist_id)

    def update_playlist(
        self,
        playlist_id: str,
        name: Optional[str] = None,
        cover: Optional[str] = None,
    ) -> dict[str, Any]:
        current = self.get_playlist(playlist_id)
        next_name = (name if name is not None else current["name"]).strip()
        if not next_name:
            raise APIError.validation_error("playlist name is required")
        next_cover = cover if cover is not None else current["cover"]
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE playlists
                SET name = ?, cover = ?, updated_at = ?
                WHERE id = ?
                """,
                (next_name, next_cover, utc_now(), playlist_id),
            )
        return self.get_playlist(playlist_id)

    def delete_playlist(self, playlist_id: str) -> dict[str, Any]:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        if cursor.rowcount == 0:
            raise APIError.not_found(f"Playlist not found: {playlist_id}")
        return {"id": playlist_id, "deleted": True}

    def preview_playlist_items(
        self,
        playlist_id: str,
        tracks: Optional[list[Track]] = None,
        track_ids: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return self._batch_playlist_items(playlist_id, tracks or [], track_ids or [], write=False)

    def batch_add_playlist_items(
        self,
        playlist_id: str,
        tracks: Optional[list[Track]] = None,
        track_ids: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return self._batch_playlist_items(playlist_id, tracks or [], track_ids or [], write=True)

    def _batch_playlist_items(
        self,
        playlist_id: str,
        tracks: list[Track],
        track_ids: list[str],
        write: bool,
    ) -> dict[str, Any]:
        self.get_playlist(playlist_id)
        normalized: list[Track] = []
        unavailable = 0

        for track in tracks:
            if not track.track_id or not track.bvid or not track.title:
                unavailable += 1
                continue
            normalized.append(track)

        for track_id in track_ids:
            track = self.get_track(track_id)
            if track:
                normalized.append(track)
            else:
                unavailable += 1

        seen: set[str] = set()
        unique_tracks: list[Track] = []
        input_duplicates = 0
        for track in normalized:
            if track.track_id in seen:
                input_duplicates += 1
                continue
            seen.add(track.track_id)
            unique_tracks.append(track)

        with get_connection(self.db_path) as conn:
            existing = {
                row["track_id"]
                for row in conn.execute(
                    "SELECT track_id FROM playlist_items WHERE playlist_id = ?",
                    (playlist_id,),
                ).fetchall()
            }
            next_position = int(
                conn.execute(
                    "SELECT COALESCE(MAX(position), -1) + 1 AS next_position FROM playlist_items WHERE playlist_id = ?",
                    (playlist_id,),
                ).fetchone()["next_position"]
            )

            to_add = [track for track in unique_tracks if track.track_id not in existing]
            if write:
                now = utc_now()
                for offset, track in enumerate(to_add):
                    self.upsert_track(track)
                    conn.execute(
                        """
                        INSERT INTO playlist_items (playlist_id, track_id, position, added_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (playlist_id, track.track_id, next_position + offset, now),
                    )
                if to_add:
                    first_cover = to_add[0].cover
                    conn.execute(
                        """
                        UPDATE playlists
                        SET cover = COALESCE(cover, ?), updated_at = ?
                        WHERE id = ?
                        """,
                        (first_cover, now, playlist_id),
                    )

        duplicated = input_duplicates + len(unique_tracks) - len(to_add)
        return {
            "total": len(tracks) + len(track_ids),
            "added": len(to_add),
            "duplicated": duplicated,
            "unavailable": unavailable,
            "write": write,
        }

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

    def _track_payload_with_meta(self, row: Any) -> dict[str, Any]:
        payload = self._track_from_row(row).to_dict()
        payload.update(
            {
                "lastPlayedAt": row["last_played_at"],
                "recentPlayCount": row["recent_play_count"],
                "positionMs": row["position_ms"],
                "listenMs": row["listen_ms"],
                "completed": bool(row["completed"]),
            }
        )
        return payload
