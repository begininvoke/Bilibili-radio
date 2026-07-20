from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "bili_radio.sqlite3"


def get_connection(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[Path | str] = None) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tracks (
                track_id TEXT PRIMARY KEY,
                bvid TEXT NOT NULL,
                cid INTEGER,
                title TEXT NOT NULL,
                owner TEXT NOT NULL DEFAULT '',
                cover TEXT NOT NULL DEFAULT '',
                duration INTEGER NOT NULL DEFAULT 0,
                play_count INTEGER NOT NULL DEFAULT 0,
                published_at TEXT,
                page INTEGER,
                page_title TEXT,
                source TEXT NOT NULL DEFAULT 'bili',
                raw_json TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tracks_bvid_cid
                ON tracks (bvid, cid);

            CREATE TABLE IF NOT EXISTS likes (
                track_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                FOREIGN KEY(track_id) REFERENCES tracks(track_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS recent (
                track_id TEXT PRIMARY KEY,
                last_played_at TEXT NOT NULL,
                play_count INTEGER NOT NULL DEFAULT 1,
                position_ms INTEGER NOT NULL DEFAULT 0,
                listen_ms INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(track_id) REFERENCES tracks(track_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cover TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS playlist_items (
                playlist_id TEXT NOT NULL,
                track_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (playlist_id, track_id),
                FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY(track_id) REFERENCES tracks(track_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS playback_sessions (
                session_id TEXT PRIMARY KEY,
                track_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                last_position_ms INTEGER NOT NULL DEFAULT 0,
                listen_ms INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                last_event TEXT NOT NULL,
                FOREIGN KEY(track_id) REFERENCES tracks(track_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS playback_recent (
                track_id TEXT PRIMARY KEY,
                last_played_at TEXT NOT NULL,
                position_ms INTEGER NOT NULL DEFAULT 0,
                listen_ms INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(track_id) REFERENCES tracks(track_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS playback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                track_id TEXT NOT NULL,
                event TEXT NOT NULL,
                position_ms INTEGER NOT NULL DEFAULT 0,
                listen_ms INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(track_id) REFERENCES tracks(track_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
