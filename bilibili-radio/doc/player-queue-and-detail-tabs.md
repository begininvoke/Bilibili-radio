# 播放队列持久化与播放详情页接口接入

## 本轮目标

- 播放队列刷新后不丢失。
- 播放详情页的“字幕 / 简介 / 章节 / 评论区”从占位文案切换为真实后端接口。

## 播放队列持久化

- 后端新增 `player_queue_state` 与 `player_queue_items` 两张 SQLite 表。
- 新增 `PlayerQueueService`，以队列快照方式保存 `queue`、`currentIndex`、`playMode`、`updatedAt`。
- 前端 `playerStore` 启动时会读取 `/api/player/queue`。
- 如果后端已有队列状态，以后端为准。
- 如果后端没有状态但本地 localStorage 有队列，首次自动迁移到后端。
- 如果后端不可用，继续使用 localStorage fallback。
- 刷新页面后只恢复队列和当前曲目信息，不自动恢复播放。

## 新增队列 API

```text
GET /api/player/queue
PUT /api/player/queue
DELETE /api/player/queue
```

`PUT /api/player/queue` 请求：

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
  "queue": [],
  "currentIndex": -1,
  "playMode": "order",
  "updatedAt": "2026-07-21T14:00:00+08:00"
}
```

## 播放详情页接口

新增后端接口：

```text
GET /api/tracks/<bvid>/intro
GET /api/tracks/<bvid>/<cid>/intro
GET /api/tracks/<bvid>/subtitles
GET /api/tracks/<bvid>/<cid>/subtitles
GET /api/tracks/<bvid>/chapters
GET /api/tracks/<bvid>/<cid>/chapters
GET /api/tracks/<bvid>/comments?page=&page_size=
GET /api/tracks/<bvid>/<cid>/comments?page=&page_size=
```

数据来源：

- 简介：B站 `x/web-interface/view`
- 字幕：B站 `x/player/v2` 的字幕清单与字幕 JSON
- 章节：B站 `x/player/v2` 的 `view_points`
- 评论区：B站 `x/v2/reply/main`

前端 `NowPlayingView` 已接入：

- 切换曲目会清空旧面板数据。
- 切换 Tab 按需请求当前 Tab 数据。
- 请求失败显示可点击重试状态。
- 字幕、章节、评论为空时显示明确空态，不再显示开发占位。
- 字幕和评论区内容固定在详情面板内部滚动，不允许撑高整屏播放详情页。

## 播放控制兼容修正

- 修正 `skip-back` / `skip-forward` 图标路径命名反置问题。
- 按钮行为保持不变：左侧是上一首，右侧是下一首。

## 验证

```text
python -m unittest discover -s tests
npm run type-check
```

当前验证结果：

- 后端 28 个单测通过。
- 前端 `vue-tsc --noEmit` 通过。
