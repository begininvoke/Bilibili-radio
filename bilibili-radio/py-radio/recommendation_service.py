from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from database import DEFAULT_DB_PATH, LEGACY_OWNER_USER_ID, get_connection, init_db
from library_service import LibraryService, utc_now


RECENT_PENALTY_DAYS = 2
LONG_ABSENCE_DAYS = 30


@dataclass
class RecommendationCandidate:
    track: dict[str, Any]
    score: float
    source: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "track": self.track,
            "score": round(self.score, 2),
            "source": self.source,
            "reason": self.reason,
        }


class RecommendationService:
    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        user_id: str = LEGACY_OWNER_USER_ID,
    ):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.user_id = user_id
        init_db(self.db_path)
        self.library = LibraryService(self.db_path, user_id=self.user_id)

    def list_recommendations(self, scene: str = "home", limit: int = 8) -> dict[str, Any]:
        normalized_scene = self._normalize_scene(scene)
        bounded_limit = min(max(int(limit or 8), 1), 20)
        rows = self._candidate_rows()
        candidates = [self._score_candidate(row) for row in rows]
        candidates.sort(key=lambda item: item.score, reverse=True)

        positive_candidates = [candidate for candidate in candidates if candidate.score > 0]
        selected = (positive_candidates or candidates)[:bounded_limit]
        self.record_events(
            [
                {
                    "trackId": item.track["trackId"],
                    "event": "shown",
                    "scene": normalized_scene,
                    "source": item.source,
                    "reason": item.reason,
                    "score": item.score,
                }
                for item in selected
            ]
        )
        return {
            "scene": normalized_scene,
            "items": [item.to_dict() for item in selected],
        }

    def record_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        events = self.record_events([payload])
        return events[0]

    def record_events(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now = utc_now()
        normalized = []
        for payload in payloads:
            track_id = str(payload.get("trackId") or payload.get("track_id") or "").strip()
            if not track_id:
                continue
            normalized.append(
                {
                    "trackId": track_id,
                    "event": self._normalize_event(payload.get("event")),
                    "scene": self._normalize_scene(str(payload.get("scene") or "home")),
                    "source": str(payload.get("source") or "")[:64],
                    "reason": str(payload.get("reason") or "")[:240],
                    "score": float(payload.get("score") or 0),
                    "createdAt": now,
                }
            )

        if normalized:
            with get_connection(self.db_path) as conn:
                conn.executemany(
                    """
                    INSERT INTO recommendation_events (
                        user_id, track_id, event, scene, source, reason, score, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            self.user_id,
                            item["trackId"],
                            item["event"],
                            item["scene"],
                            item["source"],
                            item["reason"],
                            item["score"],
                            item["createdAt"],
                        )
                        for item in normalized
                    ],
                )
        return normalized

    def _candidate_rows(self) -> list[Any]:
        with get_connection(self.db_path) as conn:
            return conn.execute(
                """
                SELECT
                    t.*,
                    COALESCE(r.play_count, 0) AS recent_play_count,
                    r.last_played_at AS library_last_played_at,
                    pr.last_played_at AS playback_last_played_at,
                    COALESCE(pr.listen_ms, r.listen_ms, 0) AS listen_ms,
                    COALESCE(pr.completed, r.completed, 0) AS completed,
                    COALESCE(pr.skipped, 0) AS skipped,
                    l.created_at AS liked_at,
                    tr.rating AS review_rating,
                    tr.mood AS review_mood,
                    tr.note AS review_note,
                    pi.playlist_id AS playlist_id,
                    MAX(CASE WHEN re.event IN ('dismissed', 'dislike') THEN re.created_at END) AS dismissed_at,
                    MAX(CASE WHEN re.event IN ('played', 'accepted') THEN re.created_at END) AS adopted_at
                FROM tracks t
                LEFT JOIN recent r
                    ON r.user_id = ? AND r.track_id = t.track_id
                LEFT JOIN playback_recent pr
                    ON pr.user_id = ? AND pr.track_id = t.track_id
                LEFT JOIN likes l
                    ON l.user_id = ? AND l.track_id = t.track_id
                LEFT JOIN track_reviews tr
                    ON tr.user_id = ? AND tr.track_id = t.track_id
                LEFT JOIN playlist_items pi
                    ON pi.user_id = ? AND pi.track_id = t.track_id
                LEFT JOIN recommendation_events re
                    ON re.user_id = ? AND re.track_id = t.track_id
                WHERE r.track_id IS NOT NULL
                   OR pr.track_id IS NOT NULL
                   OR l.track_id IS NOT NULL
                   OR tr.track_id IS NOT NULL
                   OR pi.track_id IS NOT NULL
                GROUP BY t.track_id
                """,
                (self.user_id, self.user_id, self.user_id, self.user_id, self.user_id, self.user_id),
            ).fetchall()

    def _score_candidate(self, row: Any) -> RecommendationCandidate:
        track = self.library._track_from_row(row).to_dict()
        score = 0.0
        signals: list[str] = []

        play_count = int(row["recent_play_count"] or 0)
        if play_count > 0:
            score += min(play_count, 8) * 4
            signals.append(f"你之前播放过 {play_count} 次")

        if row["liked_at"]:
            score += 30
            signals.append("你喜欢过这首")

        rating = int(row["review_rating"] or 0)
        if rating:
            score += rating * 8
            mood = str(row["review_mood"] or "").strip()
            signals.insert(0, f"你给过 {rating} 星" + (f"，情绪是「{mood}」" if mood else ""))
            if row["review_note"]:
                score += 5

        if row["playlist_id"]:
            score += 12
            signals.append("它在你的本地歌单里")

        if int(row["completed"] or 0):
            score += 10
        if int(row["skipped"] or 0):
            score -= 25

        days_since_play = self._days_since(row["playback_last_played_at"] or row["library_last_played_at"])
        if days_since_play is not None:
            if days_since_play <= RECENT_PENALTY_DAYS:
                score -= 18
            elif days_since_play >= LONG_ABSENCE_DAYS and score >= 18:
                score += 20
                signals.insert(0, f"已经 {days_since_play} 天没听了")
            elif days_since_play >= 7:
                score += 6

        if row["dismissed_at"]:
            score -= 40
        if row["adopted_at"]:
            score += 8

        source = self._source_for(row, days_since_play)
        reason = self._reason_for(signals, source)
        return RecommendationCandidate(track=track, score=score, source=source, reason=reason)

    @staticmethod
    def _source_for(row: Any, days_since_play: Optional[int]) -> str:
        if days_since_play is not None and days_since_play >= LONG_ABSENCE_DAYS:
            return "long_absence"
        if row["review_rating"]:
            return "review"
        if row["liked_at"]:
            return "liked"
        if int(row["recent_play_count"] or 0) > 1:
            return "recent_preference"
        return "library"

    @staticmethod
    def _reason_for(signals: list[str], source: str) -> str:
        if signals:
            return "；".join(signals[:2])
        if source == "long_absence":
            return "这首歌有一阵子没听了"
        if source == "liked":
            return "来自你的喜欢列表"
        return "来自你的播放和收藏记录"

    @staticmethod
    def _days_since(value: Any) -> Optional[int]:
        if not value:
            return None
        try:
            normalized = str(value).replace("Z", "+00:00")
            played_at = datetime.fromisoformat(normalized)
            now = datetime.now(played_at.tzinfo)
            return max((now - played_at).days, 0)
        except ValueError:
            return None

    @staticmethod
    def _normalize_scene(scene: str) -> str:
        value = (scene or "home").strip().lower()
        return value[:32] or "home"

    @staticmethod
    def _normalize_event(event: Any) -> str:
        value = str(event or "shown").strip().lower()
        if value not in {"shown", "played", "accepted", "dismissed", "dislike"}:
            return "shown"
        return value
