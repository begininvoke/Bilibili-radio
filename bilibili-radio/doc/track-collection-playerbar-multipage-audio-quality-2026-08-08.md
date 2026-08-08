# Track Collection、底部多 P 队列与音频设置实现记录

日期：2026-08-08

## 模型

- 内部统一按 `Collection -> Track[]` 理解曲目集合。
- `Track` 增加 `ownerMid`，用于从曲目行、底部播放器和播放详情进入 UP 主页。
- `Collection` 保留 `sourceType` 与 `sourceBvid`：
  - `user-created`
  - `bilibili-multipage`
  - `bilibili-favorite`
- 不再存储 `editable`。当前三类 Collection 默认可编辑；以后只读共享集合应由权限动态判断。

## 交互

- 直接输入或添加整组多 P 时，调用 `/api/tracks/<bvid>`，将 `pages[]` 展开为多个单 P `Track`。
- 播放队列抽屉复用搜索结果的 `TrackRow` 展示单 P，点击队列中的单 P 直接切换播放。
- Collection 详情页升级为编辑器，支持改标题、改封面、追加 BV/整多 P、删除曲目和拖拽排序。
- 播放队列与“我喜欢”保持加入顺序，不提供拖拽排序。
- 有 `ownerMid` 的 UP 名可进入 `/up/:mid`。
- UP 页展示头像、名字、简介和公开稿件，支持时间排序与热度排序，首屏 20 条并向下加载更多。

## API

- `GET /api/bili/users/<mid>/profile`
  - 返回头像、名字、简介和等级。
- `GET /api/bili/users/<mid>/tracks?page=1&page_size=20&order=pubdate|click`
  - 仅返回稿件。
  - 默认按发布时间排序。
  - `click` 表示按热度排序。
- `PUT /api/library/playlists/<playlist_id>/items`
  - 用 `Track[]` 替换 Collection 曲目列表，供删除和排序使用。
- `PATCH /api/settings`
  - 支持 `audioQualityPreference` 与 `playbackSpeed`。

## 音频设置

- 音质仅保留音频流：
  - `auto`
  - `64k` -> `30216`
  - `132k` -> `30232`
  - `192k` -> `30280`
  - `dolby` -> `30250`
  - `hires` -> `30251`
- Dolby 与 Hi-Res 只有当前流信息返回可用时才在底栏显示。
- 倍速使用 `HTMLAudioElement.playbackRate`，并设置 `preservesPitch`、`mozPreservesPitch`、`webkitPreservesPitch` 保持变速不变调。

## 私人评价标签

- 前后端继续兼容旧字段名 `mood`，交互语义改为“标签”。
- 保留预设标签，新增自定义标签输入。
- 自定义标签限制 1 到 4 个字，前端和后端均校验。
- 推荐理由文案改为“标签是「xxx」”。

## 明确不做

- 不实现 AV1 / HEVC / AVC 播放策略。
- 不实现音量均衡。
- 不把虚拟专辑伪装成 B 站多 P；B 站多 P 只是 Collection 的导入来源。
- 不改后端 admin API，仅移除前端可见管理入口和 `/admin` 路由。
