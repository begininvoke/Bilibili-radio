# UP ownerMid schema and play count diagnosis

## Problem

The desktop database in `AppData/Roaming/com.ourhome.bilibiliradio/data/bili_radio.sqlite3` was still at `PRAGMA user_version = 6`.
Its `tracks` table did not have the `owner_mid` column, so persisted tracks only carried the UP display name.

When the UI opened `/up/resolve/:bvid`, the page could not resolve a numeric Bilibili `mid` from old track data and showed `无法解析 UP 主：<name>`.

## Changes

- Frontend UP navigation now accepts legacy owner fields: `ownerMid`, `owner_mid`, `mid`, `upper.mid`, and `ownerInfo.mid`.
- `/up/resolve/:bvid` now also accepts `mid` from query params before falling back to video detail lookup.
- Multipart row normalization preserves a valid part or parent `ownerMid` instead of dropping it while expanding pages.
- Database initialization now runs an idempotent current-schema check for key columns after versioned migrations.
- Recent-play/play-count recording now requires accumulated listen time to reach 80% of track duration.
- Fixed `_space_wbi_get` being incorrectly declared as `@staticmethod`, which made all UP profile/archive API calls fail with a server 500.
- Space WBI requests now use the guest session when no Bilibili auth cookie is available, warm guest cookies, and retry once on 412/risk-control responses.

## Operational Note

If an old desktop process remains running after install, it can keep serving the old backend and old schema.
Restarting the desktop app after installing the new build is required so the latest backend runs the schema migration.

Unauthenticated Bilibili Space APIs can still return risk-control errors from Bilibili itself. The backend should surface that upstream message instead of `Internal server error`.
