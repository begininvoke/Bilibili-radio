# UP 链接与 Collection 拖拽排序修复记录

日期：2026-08-08

## UP 名跳转

- 问题：旧缓存、播放队列或收藏里的曲目可能只有 UP 名，没有 `ownerMid`，点击 UP 名无法进入主页。
- 处理：
  - 新增 `useOpenOwner()`。
  - 如果曲目已有 `ownerMid`，直接跳转 `/up/:mid`。
  - 如果没有 `ownerMid`，按 `bvid` 调用 `/api/tracks/<bvid>` 解析详情，再从详情或分 P 中读取 `ownerMid` 后跳转。
  - `TrackRow`、底部播放器和播放详情页统一使用该逻辑。

## Collection 拖拽排序

- 问题：原实现把整行设为 `draggable`，行内按钮和文本区域会干扰拖拽启动，部分场景拖不起来。
- 处理：
  - 改成只允许左侧 `☰` 手柄启动拖拽。
  - `dragstart` 写入 `dataTransfer`，drop 时优先读取传输索引。
  - 整行只负责接收 drop，并提供 `drop-target` 高亮。
  - 播放队列和“我喜欢”仍不支持拖拽排序。
