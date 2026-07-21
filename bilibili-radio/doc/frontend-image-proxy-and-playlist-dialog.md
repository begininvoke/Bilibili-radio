# Frontend Image Proxy And Playlist Dialog

## Problems Fixed

- Bilibili cover images and user avatars could fail to load when the browser requested them directly from `localhost`.
- Search results, recent cards, player cover, favorite folders, and user avatar now route remote Bilibili images through the backend image proxy.
- The native browser prompt for creating a playlist showed `localhost:3000` and did not match the app UI.
- The home page no longer shows mock Bilibili favorite folder placeholders.

## Backend

- Added `GET /api/images/proxy?url=`.
- The proxy only allows Bilibili-related image hosts:
  - `*.hdslb.com`
  - `*.bilibili.com`
  - `*.bilivideo.com`
- The proxy forwards image requests with a Bilibili referer and caches successful image responses for one day.

## Frontend

- Added `mediaUrl()` to the API client.
- Components that render remote covers or avatars now use `mediaUrl()`:
  - `TrackCard`
  - `TrackRow`
  - `PlayerBar`
  - `NowPlayingView`
  - `PlaylistDetailView`
  - `FavoritesView`
  - `TopBar`
  - `LoginView`
- Replaced `window.prompt()` in `Sidebar.vue` with an in-app playlist creation modal.
- Removed the home page's mock Bilibili favorite folder section.

## Notes

- Local app assets and QR code `data:` URLs are not proxied.
- The favorite page remains the source of truth for Bilibili favorite folders.
