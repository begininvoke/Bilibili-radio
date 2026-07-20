# 多 P 视频播放验证记录

日期：2026-07-20

## 测试 URL

`https://www.bilibili.com/video/BV16A4y1D7fW/?spm_id_from=333.337.search-card.all.click&vd_source=9da7c1f945cec43bf7015cec5700da0d`

## 解析结果

- BV：`BV16A4y1D7fW`
- 标题：`【陈楚生】歌手2019《思念一个荒废的名字》《鱼》《旅途》`
- 默认 cid：`584878477`
- 分 P 数：`3`

| P | cid | 时长 | 标题 |
|---|---:|---:|---|
| P1 | `584878477` | 281s | `《思念一个荒废的名字》` |
| P2 | `584883188` | 298s | `《鱼》` |
| P3 | `584883787` | 282s | `《旅途》` |

## 代理流验证

分别请求以下接口，并对返回的代理 URL 发起 `Range: bytes=0-1023`：

- `GET /api/tracks/BV16A4y1D7fW/584878477/stream-info`
- `GET /api/tracks/BV16A4y1D7fW/584883188/stream-info`
- `GET /api/tracks/BV16A4y1D7fW/584883787/stream-info`

验证结果：

| P | cid | stream-info | Range 状态 | 返回字节 |
|---|---:|---|---:|---:|
| P1 | `584878477` | success | 206 | 1024 |
| P2 | `584883188` | success | 206 | 1024 |
| P3 | `584883787` | success | 206 | 1024 |

## 结论

- 后端可以正确解析多 P 视频。
- P 级 `cid` 播放接口可以分别拿到独立音频流。
- Range 代理正常返回 `206 Partial Content`。
- 当前前端直接粘贴多 P 链接默认播放第 1P；后端已经具备播放任意 P 的能力，后续需要补前端分 P 选择 UI。
