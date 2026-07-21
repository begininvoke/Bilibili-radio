# Backend Round 5/6 Implementation

## Scope

This update finishes the backend MVP work for Bilibili QR login, favorite folders, favorite import, cover metadata, and AMEM/recommendation event reservation.

## Round 5: Bilibili QR Login

- Added `AuthService` as the owner of Bilibili account state.
- Added QR login APIs:
  - `GET /api/auth/qrcode`
  - `GET /api/auth/qrcode/status?qrcodeKey=`
  - `GET /api/auth/status?refresh=`
  - `GET /api/auth/profile?refresh=`
  - `POST /api/auth/logout`
- Cookies are stored only in backend SQLite.
- On Windows the cookie payload is protected with DPAPI. Other platforms fall back to a local random key plus HMAC-checked encrypted payload.
- The frontend receives only login status, QR URL, QR key, and normalized user profile. It never receives the raw cookie string.

## Round 6: Favorites And Import

- Added authenticated Bilibili favorite APIs:
  - `GET /api/bili/favorites`
  - `GET /api/bili/favorites/<media_id>/tracks?page=&page_size=`
- Favorite folders are normalized to `FavoriteFolder`.
- Favorite items are normalized to the existing `Track` contract.
- Added favorite import APIs:
  - `POST /api/library/playlists/import/favorite`
  - `POST /api/library/playlists/<id>/import/favorite`
- Import reuses the existing playlist batch service, so duplicate detection and unavailable counts stay consistent with multi-P batch import.
- Import defaults to `maxPages=10`, `pageSize=20`, and clamps `maxPages` to 50 to avoid accidental large pulls.

## Cover Metadata

Live check against `GET https://api.bilibili.com/x/web-interface/view?bvid=BV16A4y1D7fW` confirmed:

- Video-level cover is in `data.pic`.
- P-level first frame is available at `data.pages[].first_frame`.
- Page objects include `cid`, `page`, `part`, `duration`, and `first_frame`.

New backend APIs:

- `GET /api/tracks/<bvid>/cover`
- `GET /api/tracks/<bvid>/cover?cid=<cid>`
- `GET /api/tracks/<bvid>/<cid>/cover`

The returned `cover` field is the selected cover. For a requested `cid`, it prefers that page's `first_frame`; otherwise it falls back to the video-level `pic`.

## Analysis Event Reservation

- Added `analysis_events` SQLite table.
- Added `POST /api/analysis/events`.
- Favorite import writes a `favorite_imported` event containing `mediaId`, `playlistId`, and import counters.
- This endpoint is intentionally small: it stores high-level behavior markers for later AMEM/recommendation services without putting analysis into the playback path.

## Frontend Contract

- Added TypeScript client functions and types for auth status, QR login, Bilibili favorites, favorite import, cover info, and analysis events.
- No new UI page was added in this round; the API layer is ready for a focused login/favorites screen later.

## Verification Targets

- Unit tests cover QR login success, encrypted cookie persistence, favorite normalization, cover metadata normalization, playlist batch reuse, and analysis event persistence.
- Runtime smoke checks should include:
  - `GET /api/auth/qrcode`
  - `GET /api/tracks/BV16A4y1D7fW/584878477/cover`
  - `GET /api/bili/favorites` after QR login succeeds
  - Importing a small favorite folder into a new local playlist
