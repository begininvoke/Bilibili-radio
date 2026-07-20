# 后端服务化路线图

## 目标

把现有单 BV 播放后端升级为前端可消费的播放器服务层。短期继续保留 Flask + Socket.IO，先补齐 HTTP API、统一 Track 模型、本地库持久化和可并发的音频流解析能力；扫码登录、收藏夹和 AMEM 分析放到后续阶段。

## 当前基线

- 后端入口在 `py-radio/app.py`。
- 旧能力是输入 BV 或 B站视频链接后，经 Socket.IO 推送视频信息和代理播放地址。
- 旧 `/api/stream/<bvid>` 依赖全局 `current_audio_info`，不适合队列、多用户和下载。
- 前端本地库仍以 localStorage 为事实来源，后端没有可持久化的歌单、喜欢、最近播放。

## 模块拆分

- `bili_client`：B站接口适配，负责搜索、视频详情、音频流和后续收藏夹。
- `track_service`：把 B站原始响应归一化为前端 Track。
- `library_service`：SQLite 本地库，负责歌单、喜欢、最近播放和批量导入。
- `auth_service`：扫码 Cookie 登录预留，不进入当前播放主链路。
- `stream_service`：音频 URL 短期缓存、代理转发和 Range 透传。
- `playback_service`：播放 heartbeat、有效收听、继续播放和最近播放聚合。

## 执行顺序

### 第一轮：后端基础设施

- 整理目录结构，保留 Flask。
- 建立统一错误响应。
- 引入 SQLite，保存本地歌单、喜欢、最近播放。
- 让 `/api/stream/<bvid>` 不再依赖全局音频 URL，同时保留旧 WebSocket 播放能力。
- 补齐 API 契约和本轮实现记录。

### 第二轮：内容 API

- 接 B站搜索接口。
- 搜索结果统一归一化为 `Track[]`。
- 前端搜索页从 mock 数据切到真实 API。

### 第三轮：播放器服务化

- 以 `bvid + cid` 作为 P 级播放主键。
- 支持队列中任意曲目请求播放和下载。
- 播放失败返回可识别错误，前端可以自动跳下一首。

### 第四轮：本地库同步

- 将 localStorage 的最近播放、喜欢、歌单迁移到后端 SQLite。
- 前端保留 localStorage 作为短期 fallback，不作为最终事实来源。

### 第五轮：B站扫码登录

- 生成二维码、轮询状态、保存 Cookie。
- Cookie 只保存在后端，后续加密保存。
- 使用 Cookie 获取用户资料和收藏夹。

### 第六轮：收藏夹与推荐

- 获取 B站收藏夹列表。
- 收藏夹内容转 `Track[]`。
- 支持导入为本地歌单。
- 为 AMEM 视频分析和每日推荐预留事件接口。

## 数据模型方向

- Track 主键采用 P 级 ID：`bili:<bvid>:cid:<cid>`。
- 搜索结果可能暂时没有 `cid`，前端播放前可通过 `/api/tracks/<bvid>` 补详情。
- 本地库统一存 Track 快照，不透传 B站原始响应。
- 最近播放以后端播放行为聚合为准，不再等同于点击历史。

## 生产风险

- B站公开接口可能限流或返回结构变化，所有外部响应必须先归一化再返回前端。
- 音频 URL 有时效性，只能短期缓存，不写入本地库。
- Cookie 登录必须后置，避免在播放主链路里提前引入账号态复杂度。
- 当前 Git 根目录在 `E:\tool-project`，开发时只改 `E:\tool-project\bilibili-radio` 下文件，避免误处理父级旧路径删除。
