# 后端第二轮实现记录

日期：2026-07-20

## 范围

- 完成内容 API 的可用性加固。
- 前端搜索页从 mock 数据切换到真实 `/api/search`。
- 保留 BV 号和 B站视频链接直接播放路径。

## 后端改动

- `BiliClient.search()` 在搜索前预热 B站游客 Cookie。
- 当 B站搜索接口返回 `HTTP 412` 或 `code=-412` 时，强制刷新游客 Cookie 并重试一次。
- 搜索接口继续返回统一 `Track[]`，不向前端透传 B站原始响应。
- 新增测试覆盖 412 重试路径。

## 前端改动

- 新增 `src/api/client.ts`，统一处理后端 JSON 响应和错误响应。
- `SearchView.vue` 改为调用 `searchTracks()` 获取真实 B站搜索结果。
- 移除搜索页 mock 标记和 mock 结果列表。
- 搜索页保留“播放”按钮，用于 BV 号和 B站视频链接直接走旧播放链路。
- 扩展 `Track` 类型，支持 `trackId/cid/playCount/publishedAt/page/pageTitle/source`。

## 实际验证

- 后端：`python -m unittest discover -s tests`，9 个单测通过。
- 后端：Flask test client 请求 `GET /api/search?keyword=lofi&page=1&page_size=2` 返回 200，且返回 2 条 Track。
- 前端：`npm run type-check` 通过。
- 前端：`npm run build` 通过。
- 联调：已启动后端 `http://127.0.0.1:5000` 和前端 `http://127.0.0.1:3000`。
- 联调：运行中请求 `GET http://127.0.0.1:5000/api/search?keyword=lofi&page=1&page_size=2` 返回 2 条 Track。
- 联调：运行中请求 `GET http://127.0.0.1:3000/search?q=lofi` 返回 200。

## 405 和 412 的解释

- `405 Method Not Allowed` 是路由方法校验结果，例如 `POST /api/search` 不支持，因为搜索契约是 `GET /api/search`。本轮确认它会按 HTTP 原状态码返回，不会被全局异常处理误包装成 500。
- `412 Precondition Failed` 来自 B站搜索接口，不是本地后端错误。它通常表示请求缺少 B站期望的游客 Cookie 或触发了风控。本轮通过预热 Cookie 和一次刷新重试降低该问题出现概率；若重试后仍失败，后端会返回统一 `API_ERROR`。

## 非目标

- 本轮不做收藏夹。
- 本轮不做扫码登录。
- 本轮不迁移本地喜欢、最近播放、歌单到后端事实来源。
- 本轮不改播放器主链路为纯 HTTP，Socket.IO 播放入口继续保留。
