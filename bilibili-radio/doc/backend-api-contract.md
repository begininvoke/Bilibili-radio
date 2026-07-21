# 后端 API 契约

## 通用响应

普通 JSON API 返回：

```json
{
  "success": true,
  "data": {}
}
```

错误返回：

```json
{
  "success": false,
  "error": {
    "code": "INVALID_BVID",
    "message": "Invalid BVID format: BVxxx"
  }
}
```

音频流接口直接返回媒体字节，透传 `Range`，成功时可能返回 `200` 或 `206`。

## Track

后端不透传 B站原始响应，统一返回 Track：

```json
{
  "trackId": "bili:BVxxx:cid:123",
  "bvid": "BVxxx",
  "cid": 123,
  "title": "标题",
  "owner": "UP主",
  "cover": "https://...",
  "duration": 245,
  "playCount": 123456,
  "publishedAt": "2026-07-20T10:00:00+08:00",
  "page": 1,
  "pageTitle": "P1"
}
```

`cid`、`page`、`pageTitle` 在搜索结果里可能为空；播放前可调用详情接口补齐。

## 内容 API

### `GET /api/search?keyword=&page=&page_size=`

搜索 B站视频，返回归一化 Track 列表。
后端会维护 B站游客 Cookie；如 B站返回 412，会刷新 Cookie 并重试一次。

```json
{
  "success": true,
  "data": {
    "keyword": "lofi",
    "page": 1,
    "pageSize": 20,
    "tracks": []
  }
}
```

### `GET /api/tracks/<bvid>`

获取单个视频详情。多 P 视频会在 `pages` 返回 P 级 Track。

```json
{
  "success": true,
  "data": {
    "track": {},
    "pages": []
  }
}
```

### `GET /api/tracks/resolve?input=`

解析 BV 号或 B站视频链接，并返回与详情接口一致的数据结构。

### `GET /api/tracks/<bvid>/stream-info?cid=&quality=auto`

返回音频代理流元信息，不直接返回媒体字节。

```json
{
  "success": true,
  "data": {
    "url": "http://127.0.0.1:5000/api/tracks/BVxxx/123/stream?quality=auto",
    "relativeUrl": "/api/tracks/BVxxx/123/stream?quality=auto",
    "bvid": "BVxxx",
    "cid": 123,
    "quality": "auto",
    "actualQuality": "high",
    "codec": "aac",
    "bitrate": 241172,
    "fallback": false
  }
}
```

### `GET /api/tracks/<bvid>/<cid>/stream-info?quality=auto`

返回指定 P 的音频代理流元信息。

### `GET /api/tracks/<bvid>/stream?cid=&quality=auto`

返回音频代理流。未传 `cid` 时使用视频默认 `cid`。

### `GET /api/tracks/<bvid>/<cid>/stream?quality=auto`

返回指定 P 的音频代理流。

### `GET /api/video/info/<bvid>`

兼容旧接口，返回默认 P 的 Track 信息。

### `GET /api/video/audio/<bvid>/<cid>?quality=auto`

兼容旧接口，返回当前可用音频流的代理信息。

```json
{
  "success": true,
  "data": {
    "url": "/api/tracks/BVxxx/123/stream?quality=auto",
    "quality": "auto",
    "actualQuality": "standard",
    "codec": "aac",
    "bitrate": 128000,
    "fallback": false
  }
}
```

### `GET /api/tracks/<bvid>/intro`

返回播放详情页简介面板数据。可通过 `?cid=` 指定 P，或使用 `GET /api/tracks/<bvid>/<cid>/intro`。

### `GET /api/tracks/<bvid>/subtitles`

返回播放详情页字幕面板数据。可通过 `?cid=` 指定 P，或使用 `GET /api/tracks/<bvid>/<cid>/subtitles`。

### `GET /api/tracks/<bvid>/chapters`

返回播放详情页章节面板数据。可通过 `?cid=` 指定 P，或使用 `GET /api/tracks/<bvid>/<cid>/chapters`。

### `GET /api/tracks/<bvid>/comments?page=&page_size=`

返回播放详情页评论区面板数据。也支持 `GET /api/tracks/<bvid>/<cid>/comments?page=&page_size=`。

这些接口均返回前端可消费结构，不透传 B站原始响应。

## 本地库 API

### `GET /api/library/recent`

返回本地最近播放 Track。

### `DELETE /api/library/recent`

清空最近播放。

### `POST /api/library/recent`

写入最近播放。请求体可传完整 Track，或传 `bvid/cid` 由后端补详情。

### `GET /api/library/likes`

返回喜欢列表。

### `POST /api/library/likes/<bvid>`

加入喜欢。请求体可选完整 Track。

### `DELETE /api/library/likes/<bvid>?cid=`

取消喜欢。传 `cid` 时删除指定 P；不传时删除该 BV 下所有本地喜欢项。

### `GET /api/library/playlists`

返回歌单列表和每个歌单的 Track。

### `POST /api/library/playlists`

创建歌单。

```json
{
  "name": "默认歌单",
  "tracks": []
}
```

### `GET /api/library/playlists/<id>`

返回单个歌单。

### `PATCH /api/library/playlists/<id>`

更新歌单名称或封面。

### `DELETE /api/library/playlists/<id>`

删除歌单。

### `POST /api/library/playlists/<id>/items:preview`

批量导入预览，不写库。

```json
{
  "tracks": [],
  "trackIds": []
}
```

### `POST /api/library/playlists/<id>/items:batch`

批量导入并写库，返回统计。

```json
{
  "success": true,
  "data": {
    "total": 12,
    "added": 9,
    "duplicated": 2,
    "unavailable": 1
  }
}
```

## 播放行为 API

### `POST /api/playback/events`

上报播放 heartbeat、暂停、切歌、结束等事件。

```json
{
  "sessionId": "uuid",
  "trackId": "bili:BVxxx:cid:123",
  "positionMs": 83000,
  "listenMs": 42000,
  "completed": false,
  "event": "heartbeat"
}
```

默认完播规则：播放到 90%，或剩余不足 30 秒。有效收听少于 15 秒且切歌时标记为 skip。

### `GET /api/playback/recent`

返回播放行为聚合后的最近播放。

### `GET /api/playback/resume/<track_id>`

返回指定 Track 的继续播放位置。

## 播放队列 API

### `GET /api/player/queue`

返回当前播放队列快照。

### `PUT /api/player/queue`

保存当前播放队列快照。

```json
{
  "queue": [],
  "currentIndex": -1,
  "playMode": "order"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "queue": [],
    "currentIndex": -1,
    "playMode": "order",
    "updatedAt": "2026-07-21T14:00:00+08:00"
  }
}
```

`playMode` 支持 `order | loop | single | shuffle`。

### `DELETE /api/player/queue`

清空当前播放队列，并保留空队列状态，防止刷新后从旧 localStorage 复活。

## 设置 API

### `GET /api/settings`

返回后端设置。

```json
{
  "success": true,
  "data": {
    "audioQualityPreference": "auto"
  }
}
```

### `PATCH /api/settings`

更新后端设置。

```json
{
  "audioQualityPreference": "high"
}
```

### `GET /api/settings/audio-quality`

返回音质偏好。可选值：`auto | standard | high`。

### `PATCH /api/settings/audio-quality`

更新音质偏好。

```json
{
  "audioQualityPreference": "standard"
}
```

## 后续预留

- `GET /api/auth/qrcode`
- `GET /api/auth/qrcode/status`
- `GET /api/bili/favorites`
- `POST /api/library/playlists/<id>/import/favorite`
- `POST /api/analysis/events`

## Round 5/6 API Addendum

### Auth

#### `GET /api/auth/status?refresh=false`

Returns local Bilibili login state. Raw cookies never leave the backend.

```json
{
  "success": true,
  "data": {
    "qrLoginEnabled": true,
    "isLoggedIn": true,
    "user": {
      "mid": 123,
      "name": "UP主",
      "face": "https://i0.hdslb.com/face.jpg",
      "level": 5,
      "vipType": 2
    },
    "cookieUpdatedAt": "2026-07-20T22:30:00+08:00"
  }
}
```

#### `GET /api/auth/qrcode`

Creates a Bilibili QR login session.

```json
{
  "success": true,
  "data": {
    "qrcodeKey": "key",
    "url": "https://account.bilibili.com/h5/account-h5/auth/scan-web?...",
    "expiresAt": "2026-07-20T22:33:00+08:00",
    "pollIntervalMs": 2000
  }
}
```

#### `GET /api/auth/qrcode/status?qrcodeKey=`

Polls QR login status. `status` is one of `waiting | scanned | confirmed | expired | unknown`.
When confirmed, the backend saves encrypted cookies and returns the normalized user profile.

#### `GET /api/auth/profile?refresh=true`

Refreshes and returns the logged-in Bilibili profile. Returns `AUTH_REQUIRED` when no valid login exists.

#### `POST /api/auth/logout`

Deletes backend-stored Bilibili auth state.

### Cover

#### `GET /api/tracks/<bvid>/cover?cid=`

#### `GET /api/tracks/<bvid>/<cid>/cover`

Returns cover metadata from the Bilibili video detail API. `videoCover` comes from `data.pic`; P-level `pageCover` comes from `data.pages[].first_frame` when available.

```json
{
  "success": true,
  "data": {
    "bvid": "BVxxx",
    "cid": 123,
    "cover": "https://i0.hdslb.com/p-first-frame.jpg",
    "videoCover": "https://i0.hdslb.com/archive-cover.jpg",
    "pageCover": "https://i0.hdslb.com/p-first-frame.jpg",
    "ownerFace": "https://i0.hdslb.com/face.jpg",
    "pages": []
  }
}
```

### Bilibili Favorites

#### `GET /api/bili/favorites?upMid=`

Returns favorite folders for the logged-in user. If `upMid` is omitted, backend reads it from the current login profile.

```json
{
  "success": true,
  "data": {
    "folders": [
      {
        "mediaId": 123,
        "id": 123,
        "fid": 456,
        "title": "默认收藏夹",
        "cover": "https://...",
        "mediaCount": 20
      }
    ]
  }
}
```

#### `GET /api/bili/favorites/<media_id>/tracks?page=1&page_size=20`

Returns favorite contents normalized to `Track[]`. Deleted or unavailable entries are counted in `unavailable`.

#### `POST /api/library/playlists/import/favorite`

Creates a local playlist from a Bilibili favorite folder.

```json
{
  "mediaId": 123,
  "name": "导入的收藏夹",
  "maxPages": 10,
  "pageSize": 20
}
```

#### `POST /api/library/playlists/<id>/import/favorite`

Imports a Bilibili favorite folder into an existing playlist. Both import endpoints reuse the existing playlist batch service and return the same `added / duplicated / unavailable` counters.

### Analysis Events

#### `POST /api/analysis/events`

Reserved event ingress for AMEM and future daily recommendation services.

```json
{
  "event": "favorite_imported",
  "trackId": "bili:BVxxx:cid:123",
  "sessionId": "uuid",
  "payload": {}
}
```
