# Rule recommendations, favorite pagination, and desktop download

## Scope

This update keeps recommendations simple and local. It does not use LLMs, vector search, collaborative filtering, or AMEM.

## Recommendation v1

- Backend service: `py-radio/recommendation_service.py`.
- Endpoint: `GET /api/recommendations?scene=home&limit=5`.
- Feedback endpoint: `POST /api/recommendations/events`.
- Candidate pool:
  - recent playback,
  - effective playback history,
  - likes,
  - private reviews,
  - local playlist membership.
- Main scoring signals:
  - likes add strong weight,
  - private review rating adds strong weight,
  - playlist membership adds medium weight,
  - completed play adds weight,
  - recent repeated play adds weight,
  - skipped or dismissed items lose weight,
  - songs not played for a long time can get a comeback boost.
- Cold start fallback: if all candidates score below zero, the service still returns
  existing library candidates instead of showing an empty recommendation section.
- Frontend: Home page replaces the placeholder recommendation section with real items and short reasons.

## Favorite Folder Pagination

- Bilibili favorite detail still loads 20 items per request because the upstream API is page based.
- The detail view now tracks page state and exposes a `加载更多` action.
- Additional pages are merged by track identity so duplicates are not shown twice.

## Desktop Download

- Browser/Web mode keeps the original blob download path.
- Tauri desktop mode calls `POST /api/downloads/track`.
- The desktop backend streams the Bilibili audio to the current user's Downloads directory.
- The backend endpoint is gated to `APP_RUNTIME=desktop` so web deployments do not save files to the server disk.
- Existing names are not overwritten; the backend appends `(1)`, `(2)`, etc.

## Validation

- Backend: `python -m pytest -q`
- Frontend: `npm run build`
