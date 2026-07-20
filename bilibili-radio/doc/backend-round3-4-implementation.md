# 后端第三、四轮实现记录

日期：2026-07-20

## 范围

- 第三轮：播放器服务化，播放和下载按 `bvid + cid` 获取 HTTP 音频流。
- 第四轮：本地库同步，后端 SQLite 成为最近播放、喜欢、歌单的事实来源，前端 localStorage 保留为 fallback。

## 第三轮改动

- 新增 `GET /api/tracks/resolve?input=`，用于解析 BV 号或 B站视频链接，并返回统一 Track 详情。
- 新增 `GET /api/tracks/<bvid>/stream-info?cid=&quality=auto`。
- 新增 `GET /api/tracks/<bvid>/<cid>/stream-info?quality=auto`。
- `stream-info` 返回绝对代理 URL、相对代理 URL、实际音质、码率、codec、fallback 标记。
- 前端播放器从 Socket.IO 播放请求切换为 HTTP 链路：
  - `resolve/detail -> stream-info -> HTMLAudioElement.loadStream()`。
  - 搜索结果没有 `cid` 时，播放前自动用详情接口补齐第一 P。
  - 队列匹配优先使用 `trackId`，其次 `bvid + cid`，最后才回退 `bvid`。
- 下载当前音频改为按当前 Track 的 `bvid/cid` 请求 `stream-info`，不依赖这首歌是否已经播放过。
- Socket.IO 连接保留为状态通道兼容；即使 Socket.IO 不可用，HTTP 播放仍可继续。

## 第四轮改动

- 新增 `DELETE /api/library/recent`，支持清空后端最近播放。
- 前端 `libraryStore` 初始化时会读取：
  - `GET /api/library/recent`
  - `GET /api/library/likes`
  - `GET /api/library/playlists`
- 初始化时保留 localStorage 快照，并把本地已有但后端缺失的数据补写到 SQLite。
- 后端可用时：
  - `addRecent` 会写 `POST /api/library/recent`。
  - `toggleLike` 会写 `POST/DELETE /api/library/likes/<bvid>`。
  - `createPlaylist/removePlaylist/addToPlaylist` 会写后端歌单 API。
- 后端不可用时：
  - 前端继续使用 localStorage。
  - `backendAvailable=false`，`syncError` 保存最近一次同步错误。

## 实际验证

- 后端：`python -m unittest discover -s tests`，11 个单测通过。
- 前端：`npm run type-check` 通过。
- 前端：`npm run build` 通过。
- 运行中后端已重启到 `http://127.0.0.1:5000`。
- 运行中前端仍在 `http://127.0.0.1:3000`。
- 运行中验证：
  - `GET /api/tracks/resolve?input=<B站URL>` 返回 `BV1uz421X7bg` 和 `cid=1454380339`。
  - `GET /api/tracks/BV1uz421X7bg/1454380339/stream-info` 返回代理 URL 和 `actualQuality=high`。
  - 对代理 URL 发起 `Range: bytes=0-1023` 返回 `206` 和 1024 bytes。
  - `POST /api/library/recent` 后，`GET /api/library/recent` 可读到记录。
  - `POST /api/library/likes/<bvid>` 后，`GET /api/library/likes` 可读到记录。
- 补充验证：
  - 音质偏好设置服务已加入后端测试。
  - `stream-info` 未传 `quality` 时使用后端音质偏好。
  - 批量导入预览和写入接口已加入后端测试。

## 注意事项

- 当前搜索结果仍可能只有 BV 级信息，播放前会补详情拿 cid。
- localStorage 现在是 fallback，不再是最终事实来源。
- 前端页面里的 B站收藏夹仍是示例数据，收藏夹真实 API 进入后续第五、六轮。
- 当前 dev 日志、构建产物、SQLite 文件均被 `.gitignore` 忽略。
