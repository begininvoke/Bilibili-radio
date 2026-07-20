# 后端第一轮实现记录

日期：2026-07-20

## 范围

- 保留 Flask + Socket.IO，不迁移框架。
- 新增服务层模块，降低单文件后端耦合。
- 引入 SQLite 作为本地库持久化。
- 新增第一批内容、本地库和播放行为 API。
- 修正旧 `/api/stream/<bvid>` 对全局音频 URL 的依赖。

## 本轮落地

- `py-radio/bili_client.py`：B站搜索、视频详情、音频流选择。
- `py-radio/track_service.py`：Track 归一化。
- `py-radio/library_service.py`：最近播放、喜欢、歌单、批量导入。
- `py-radio/playback_service.py`：heartbeat 聚合、继续播放、skip/complete 判定。
- `py-radio/stream_service.py`：音频 URL 短期缓存、Range 代理和流量统计。
- `py-radio/database.py`：SQLite schema 和连接管理。
- `py-radio/app.py`：HTTP API、旧接口兼容、Socket.IO 兼容。

## 非目标

- 不做完整 OIDC。
- 不接扫码登录 Cookie。
- 不接 B站收藏夹。
- 不改前端 mock 数据来源。

## 验收点

- `python -m py_compile app.py bili_client.py database.py library_service.py playback_service.py stream_service.py track_service.py`
- `python -m unittest discover -s tests`

## 实际验证

- 已执行 `python -m pip install -r requirements.txt`，Flask 运行依赖安装成功。
- 已执行 `python -m unittest discover -s tests`，8 个单测通过。
- 已执行 Flask test client：`GET /api/auth/status` 返回 200。
- 已执行 B站搜索烟测：`BiliClient.search("lofi", page=1, page_size=2)` 返回 2 条 Track。
- 已执行 B站详情烟测：搜索结果 BV 可补到 `cid`，并生成 P 级 `trackId`。
- 后续重复搜索烟测触发 B站 `HTTP 412 Precondition Failed`，当前已映射为 `API_ERROR`，作为外部 API 风控风险处理。
- pip 安装时提示当前全局 Python 环境存在既有依赖冲突：`typer 0.3.2` 需要旧版 `click`，`spleeter 2.4.0` 需要旧版 `httpx`。后续建议改用项目 venv 隔离后端依赖。

## 注意事项

- SQLite 默认文件：`py-radio/data/bili_radio.sqlite3`。
- 音频 URL 只做短期内存缓存，不入库。
- 当前 Git 根目录在父级，本轮只应提交 `bilibili-radio` 内新增和修改文件。
