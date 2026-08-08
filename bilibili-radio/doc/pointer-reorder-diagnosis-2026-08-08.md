# 顺序拖动失效诊断与修复

日期：2026-08-08

## 诊断结论

播放队列和 Collection 详情页之前使用 HTML5 Drag & Drop：

- 左侧手柄是 `<button draggable="true">`。
- 排序依赖 `dragstart`、`dragover`、`drop`。

这在桌面 WebView 里不稳定。按钮元素本身有点击、焦点和文本选择语义，实际操作时可能不会稳定触发 `dragstart/drop`，表现就是左侧 `☰` 看得到，但按住拖不动。

“我喜欢”没有左侧 `☰`，原因是上一版按“我喜欢顺序固定”实现，没有开放排序入口。

## 修复方案

- 新增 `usePointerReorder`：
  - 使用 Pointer Events，不再依赖 HTML5 Drag & Drop。
  - 按住手柄后，通过 `document.elementFromPoint()` 找当前悬停的目标行。
  - 松开鼠标时直接调用排序函数。
- 播放队列：
  - 保留紧凑行，不显示封面。
  - 使用 `player.moveQueueItem(from, to)` 调整队列。
  - 当前播放曲目不会因为排序重播。
- Collection 详情页：
  - 改用同一套 Pointer Events 排序。
  - 继续保存到 Collection tracks。
- 我喜欢：
  - 新增左侧 `☰` 排序手柄。
  - 新增 `library.moveLikeItem(from, to)`，当前先更新前端本地顺序。

## 后续风险

后端 likes 表当前只按 `created_at DESC` 返回，没有自定义顺序字段。因此“我喜欢”的拖拽顺序目前是前端本地顺序；如果后端刷新覆盖本地列表，顺序可能回到后端默认排序。要彻底生产化，需要给 likes 增加 position/order 字段或新增 likes reorder API。
