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

## 本地库 API

### `GET /api/library/recent`

返回本地最近播放 Track。

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

## 后续预留

- `GET /api/auth/qrcode`
- `GET /api/auth/qrcode/status`
- `GET /api/bili/favorites`
- `POST /api/library/playlists/<id>/import/favorite`
- `POST /api/analysis/events`
