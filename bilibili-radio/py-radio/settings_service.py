from __future__ import annotations

from pathlib import Path
from typing import Optional

from database import DEFAULT_DB_PATH, get_connection, init_db
from error_code import APIError
from library_service import utc_now


AUDIO_QUALITY_VALUES = {"auto", "standard", "high"}
AUDIO_QUALITY_KEY = "audio_quality_preference"


class SettingsService:
    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        init_db(self.db_path)

    def get_audio_quality_preference(self) -> str:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (AUDIO_QUALITY_KEY,),
            ).fetchone()
        if not row:
            return "auto"
        value = row["value"]
        return value if value in AUDIO_QUALITY_VALUES else "auto"

    def set_audio_quality_preference(self, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in AUDIO_QUALITY_VALUES:
            raise APIError.validation_error(
                "audioQualityPreference must be one of: auto, standard, high"
            )

        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (AUDIO_QUALITY_KEY, normalized, utc_now()),
            )
        return normalized

    def to_dict(self) -> dict[str, str]:
        return {
            "audioQualityPreference": self.get_audio_quality_preference(),
        }
