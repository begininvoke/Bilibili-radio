# Windows desktop client implementation notes

## Conclusion

The first desktop version keeps the existing Vue + Flask architecture. The desktop shell is Tauri, and the Flask backend is packaged as a PyInstaller sidecar that Tauri starts on loopback.

This avoids a risky first-pass Go rewrite of the Bilibili login, cookie, SQLite, audio proxy, subtitles, chapters, comments, playback history, and monitoring paths.

## Runtime contract

- Desktop backend entrypoint: `py-radio/desktop_entry.py`.
- Tauri starts the backend with:
  - `APP_RUNTIME=desktop`
  - `AUTH_MODE=disabled`
  - `SESSION_COOKIE_SECURE=false`
  - `APP_BIND_HOST=127.0.0.1`
  - `APP_BIND_PORT=<desktop port>`
  - `APP_DATA_DIR=<tauri app data dir>/data`
- Tauri polls `/health/ready` before exposing the backend endpoint to the frontend.
- The frontend obtains `http://127.0.0.1:<port>` through the Tauri command `desktop_backend_endpoint`.
- The desktop shell prefers port `41517`; if it is occupied, it falls back to a random loopback port and passes that port through the Tauri command.
- If Tauri command injection fails but the page is clearly running inside Tauri, the frontend falls back to `http://127.0.0.1:41517`.

## Fixes from installation testing

- The installed app previously flashed and exited because the packaged resource kept its relative path under `_up_/_up_/py-radio/dist/`. The Tauri side now recursively locates `bilibili-radio-backend.exe` under the resource directory.
- Startup failures are written to `%LOCALAPPDATA%/Bilibili Radio/startup-error.log`.
- The "temporarily unable to connect to service" screen can happen even when the backend is alive if WebView requests are blocked or the endpoint is not injected. Desktop mode now:
  - allows Tauri origins and loopback origins in CORS,
  - keeps credentials support enabled,
  - uses a stable default loopback port as a frontend fallback.

## Cover and icon asset

- The app cover/icon has been replaced with the pink Bilibili music image.
- Frontend shell and login assets use `bilibili-player/src/assets/icon.png`.
- Tauri bundle assets use `bilibili-player/src/icon/icon.png`.
- Windows executable and installer icon use `bilibili-player/src-tauri/icons/icon.ico`, regenerated from the same source image with multiple icon sizes.

## Build commands

Backend sidecar:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\build-desktop-backend.ps1
```

Windows installer:

```powershell
cd .\bilibili-player
npm run desktop:build
```

## Verified

- `python -m pytest -q`
- `npm run build`
- `npm run desktop:build`
- Installed app starts from `D:\test\Bilibili Radio\bilibili-radio-desktop.exe`.
- Installed backend responds on loopback with `/health/ready` and `/api/session/me`.

## Current limits

- First desktop version is Windows-only.
- WebView2 is handled by the Tauri Windows installer.
- PyInstaller and Tauri build outputs are ignored by git and should not be committed.
