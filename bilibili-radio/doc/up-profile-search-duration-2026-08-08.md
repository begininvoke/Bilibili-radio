# UP profile search and archive duration

## Change

- Added a local search box to the UP profile page.
- Search matches the currently loaded archive tracks by title, UP name, BVID, and page title.
- Playback from filtered results uses the filtered order.
- Bilibili Space archive duration now reads `length` as a fallback to `duration`.

## Reason

Bilibili Space archive list items commonly return duration as `length` such as `03:45`.
The previous normalization only read `duration`, so UP archive rows showed zero duration.

## Not Included

Search is local over loaded archive rows. It does not call a separate remote UP-wide search API.
Users can keep loading more archive pages and the local search result will include newly loaded rows.
