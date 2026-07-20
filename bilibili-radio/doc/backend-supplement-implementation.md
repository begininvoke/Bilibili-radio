# 后端补充计划实现记录

日期：2026-07-20

## 范围

- 播放行为：heartbeat、有效收听、skip、完播和继续播放数据。
- 音质策略：用户偏好、实际可用流、自动降级和返回实际播放信息。
- 批量导入：歌单导入预览、批量写入、重复项和不可用项统计。

## 播放行为

- 已实现 `POST /api/playback/events`。
- 已实现 `GET /api/playback/recent`。
- 已实现 `GET /api/playback/resume/<track_id>`。
- 后端按 `sessionId + trackId` 聚合播放会话，不保存每个 heartbeat 原始事件。
- heartbeat 只更新聚合进度；暂停、切歌、结束等关键事件才进入审计表。
- 完播规则：播放到 90%，或总时长超过 30 秒且剩余不足 30 秒。
- skip 规则：有效收听少于 15 秒并切歌/停止，标记为 skipped，不进入高价值最近播放。

## 音质策略

- 已实现后端设置服务 `settings_service`。
- 新增 `GET /api/settings` 和 `PATCH /api/settings`。
- 新增 `GET /api/settings/audio-quality` 和 `PATCH /api/settings/audio-quality`。
- `audioQualityPreference` 支持 `auto | standard | high`。
- `stream-info` 未显式传 `quality` 时使用后端音质偏好。
- 请求显式传 `quality` 时以请求参数为准。
- B站实际音频流不可用时按最接近可用流自动降级，并返回：
  - `quality`
  - `actualQuality`
  - `codec`
  - `bitrate`
  - `fallback`

## 批量导入

- 已实现 `POST /api/library/playlists/<id>/items:preview`。
- 已实现 `POST /api/library/playlists/<id>/items:batch`。
- 输入支持 `tracks[]` 和 `trackIds[]`。
- 预览不写库，批量接口写库。
- 返回统一统计：
  - `total`
  - `added`
  - `duplicated`
  - `unavailable`
- 多 P 加入歌单和后续收藏夹导入可以复用同一套批量导入服务。

## 实际验证

- 后端：`python -m unittest discover -s tests`，17 个单测通过。
- 覆盖点包括：
  - 搜索 412 重试。
  - 音质选择降级。
  - 音质偏好持久化与非法值拒绝。
  - `stream-info` 使用后端音质偏好。
  - heartbeat 有效收听阈值。
  - skip 不进入高价值最近播放。
  - 批量导入预览和写入接口。
  - P 级代理 URL 返回。

## 后续前端项

- 前端已经切换到 HTTP 播放和后端本地库。
- 后续如需用户可见音质设置，需要在设置面板接入 `/api/settings/audio-quality`。
- 收藏夹真实导入时直接复用 `items:preview` 和 `items:batch`。
