# Frontend Auth And Cover Integration

## What Changed

- Added a real login route at `#/login`.
- The top-right login button now navigates to the login page and shows the logged-in user's avatar/name when available.
- Production builds require Bilibili login before entering app routes by default.
- Development and test builds do not require login by default, so local playback/search testing is not blocked.
- Added `VITE_REQUIRE_BILI_LOGIN` override:
  - unset: production requires login, development does not
  - `true`: always require login
  - `false`: never force login

## QR Login Page

- The login page calls `GET /api/auth/qrcode`.
- The frontend uses the local `qrcode` package to render the returned Bilibili scan URL as a QR image.
- The page polls `GET /api/auth/qrcode/status?qrcodeKey=`.
- On confirmed login, it returns to the original route from the `redirect` query.
- Raw cookies never reach the frontend.

## Cover Usage

- Backend video detail normalization now uses `data.pages[].first_frame` as the P-level `Track.cover` when available.
- The player store also calls `GET /api/tracks/<bvid>/<cid>/cover` before playback to hydrate the current queue item with the selected P-level cover.
- If the cover endpoint fails, playback continues with the existing cover.
- Favorite folder and favorite track pages render real cover images from backend API responses instead of mock data.

## Favorites Page

- `#/favorites` now calls the real Bilibili favorite APIs.
- Unauthenticated users see a login prompt.
- Folder cards use `FavoriteFolder.cover`.
- Track rows use normalized `Track.cover`.
- Import uses `POST /api/library/playlists/import/favorite` and refreshes local playlists from the backend after completion.

## Remaining UI Work

- Home recommendations and hot tracks still use existing placeholder data.
- A later pass should add pagination for large favorite folders. The current page loads the first 20 favorite items, while backend import can fetch multiple pages.
