# Desktop floating lyrics

## Scope

- Desktop only. Web deployment keeps the existing player behavior.
- The floating lyrics window is off by default.
- Default lyric color is pink: `#fb7299`.
- If no track, no subtitle payload, subtitle request failure, or no line matches
  the current playback time, the overlay displays `-`.

## Implementation

- `DesktopLyricsBridge.vue` runs in the authenticated main desktop window only.
- The bridge calls Rust commands to show, hide, and update a transparent,
  undecorated, always-on-top Tauri webview window with label `desktop-lyrics`.
- Window creation is deliberately kept in Rust instead of frontend
  `new WebviewWindow(...)` because packaged asset URLs and capability failures
  are otherwise easy to miss at runtime.
- `DesktopLyricsOverlayView.vue` renders the overlay route `/#/desktop-lyrics`.
- Subtitle data is loaded on demand through the same `getTrackSubtitles` frontend
  API used by the playback detail page.
- The player store owns the current subtitle cache and active-line calculation.
- The player bar exposes the on/off button and preset color swatches.
- The frontend no longer imports or constructs `WebviewWindow` directly.
- The lyrics window keeps cursor events enabled
  (`set_ignore_cursor_events(false)`) so the border strips can start native
  window dragging.
- The lyrics window is positioned at the bottom center of the primary monitor
  each time it is shown, limiting damage even if a platform fails to apply
  cursor pass-through.
- The overlay itself has no close button; users close it from the player bar or
  now-playing toggle, keeping close state owned by the main player UI.
- The root app still mounts the bridge outside overlay/auth layouts, but the
  bridge is now a small state sync layer; window lifecycle is owned by Tauri.
- The overlay route is excluded from auth and app-shell layout so it cannot
  interfere with the playback detail page.
- The main app mounts the bridge on normal app layouts; the bridge only shows
  the lyrics window when the toggle becomes enabled.
- The bridge republishes the latest payload several times after opening the
  window to avoid losing the initial event while the overlay webview is loading.
- The overlay page now renders its own visible pink `-` fallback immediately.
  It must not hide the entire page while waiting for an update event, because
  that creates a transparent empty window when the event is lost.
- The Tauri side stores the latest lyric payload, but the overlay page no
  longer invokes `current_lyrics_window_payload` during its first mount. The
  opening command must be able to finish window creation and execute `show()`
  before the overlay webview starts any reverse backend call.
- Showing the lyrics window now goes through an explicit reveal path:
  configure, position, unminimize, show, restore always-on-top, then enable
  cursor pass-through.
- Positioning, skip-taskbar, all-workspace visibility, and cursor pass-through
  are best-effort operations. They are logged to
  `%LOCALAPPDATA%/Bilibili Radio/desktop-lyrics.log` if they fail, but they must
  never prevent the lyrics window itself from becoming visible.
- The bridge is mounted when the desktop lyrics toggle is enabled on normal app
  layouts; it is not blocked by a stale app-auth computed state.
- The bridge is now mounted for normal desktop layouts and only reacts to the
  toggle state. The player-bar and now-playing buttons also call the Tauri
  show/hide command directly on click, so opening the overlay does not rely on a
  newly mounted watcher.
- Window success is defined at the Windows HWND layer: `Bilibili Radio Lyrics`
  must exist and `IsWindowVisible(hwnd)` must be true after open.
- Rust commands now return a `LyricsWindowDebug` object and append lifecycle
  logs to `%LOCALAPPDATA%/Bilibili Radio/desktop-lyrics.log`, including create,
  existing-window detection, unminimize, show, visibility snapshots,
  positioning, always-on-top, skip-taskbar, cursor pass-through, and payload
  emit results.
- The bridge no longer calls `hide_lyrics_window` on initial mount when the
  toggle is false; it only hides after a true-to-false transition.
- Desktop package version is bumped when rebuilding installers so users do not
  accidentally keep launching an old same-version package.
- The now-playing detail view is statically imported into the main bundle
  because it is a critical player surface; this removes packaged dynamic-chunk
  loading as a reason for "clicks but detail page does not open".
- The player-bar detail button uses the player store's `hasTrack` state rather
  than a local display-only track object, keeping the open action available
  whenever the player owns a playable track.
- The player bar now exposes a text button named `桌面歌词` instead of an
  icon-only subtitle button; the now-playing detail action area exposes the same
  control.
- 2026-08-07 live repro: after a real Win32 click, Rust logged
  `received set_lyrics_window_payload command enabled=true` and
  `get_existing_window ... creating with visible=false`, then stopped before
  `create_window`, `unminimize`, or `show`. Win32 enumeration still showed
  `Bilibili Radio Lyrics` with `Visible=False`, so the current fix removes the
  overlay's startup reverse invoke path rather than changing button styling.
- Follow-up repro after removing the overlay startup invoke still stopped at
  the same `creating with visible=false` line, including when the persisted
  toggle reopened lyrics on app start. That rules out Vue startup IPC as the
  main cause. Window creation now runs through `app.run_on_main_thread(...)`
  and reports `schedule_create_window`, `main_thread_create_window`, and
  `create_window` results before the reveal path continues.
- The decisive Windows-specific fix is to avoid hidden WebView creation. The
  lyrics window is still created only after the user enables desktop lyrics, but
  the builder now uses `visible(true)` and receives an initial bottom-center
  position. Hidden creation produced an HWND but kept `build()` from returning,
  so `show()` never had a chance to run.
- The extra `app.run_on_main_thread(...)` wrapper was removed after checking
  Tauri's builder path. `WebviewWindowBuilder::build()` already goes through the
  runtime/dispatcher, so wrapping it externally can leave the creation closure
  stuck before the debug result is emitted.
- User-visible repro after `visible(true)`: the HWND became visible, but it was
  a white webview and the command still stopped at `create_window build enter`.
  That means dynamic creation can show an OS window before Tauri finishes
  attaching the webview, leaving no reliable payload delivery or hide command.
- Current direction: `desktop-lyrics` is now a configured Tauri window in
  `tauri.conf.json`, hidden by default. Rust commands only get, show, hide, and
  emit payload to this pre-owned window; they no longer call
  `WebviewWindowBuilder::build()` from a button click.
- The overlay route again pulls `current_lyrics_window_payload` on mount and
  emits `desktop-lyrics:ready`, which is safe once the window is static and no
  longer being built from the same opening command.
- The overlay receives cursor events so the user can drag it. The border strips
  are marked with `data-tauri-drag-region` and also call Tauri
  `startDragging()` on mouse down; lyric text stays non-interactive.
- Payload refresh no longer recenters the lyrics window while it is already
  visible, so a user-dragged position is preserved until the overlay is hidden
  and opened again.
- Visual background is transparent. The previous dark translucent panel was
  removed, leaving only lyric text and text shadow by default. The colored
  border is transparent until the mouse enters the lyrics box.

## 2026-08-07 follow-up

- Removed the in-window close `x`; desktop lyrics are now opened and closed only
  from the player controls.
- Added native dragging from the lyrics border strips while preserving the
  transparent background.
- Added single-track deletion for recent playback data, including backend
  persistence through `DELETE /api/library/recent/<bvid>?cid=...`.
- Added delete actions to home recent cards, home play-count Top 10 rows, and
  the full recent playback page.
- Made the player-bar song title open the playback detail page.
- Expanded private review mood chips from 8 to 24 common music-listening tags
  without changing the saved review schema.
- Fixed the remaining drag failure by explicitly granting
  `core:window:allow-start-dragging` to the `desktop-lyrics` window capability
  and making the whole lyrics shell start native dragging on mouse down.

## 2026-08-08 follow-up

- Added a hover-only floating lyrics control strip: previous, play/pause, next,
  lock position, and close floating lyrics.
- Floating lyrics controls send `desktop-lyrics:control` events to the main
  window. The main `DesktopLyricsBridge` applies the action against the real
  player store, because the overlay webview has its own isolated Pinia runtime.
- The lyrics payload now includes `isPlaying` so the overlay can show play or
  pause accurately.
- Locking is implemented as "lock position" rather than OS click-through. The
  overlay remains clickable so users can unlock it or close it from the overlay.
- Dragging is now driven by `getCurrentWindow().startDragging()` instead of
  `data-tauri-drag-region`, so the lock state can actually block drag.

## Validation

- `npm run build`
- `python -m pytest -q`
- `cargo fmt -- --check`
- `npm run desktop:build`
