# Bilibili Radio 生产优化与响应速度方案

> 日期：2026-07-21  
> 范围：现有 Vue 播放器、Flask/Socket.IO 后端、SQLite、Bilibili 上游、未来 AMEM/Planner 运行时  
> 本轮只做审计与拆解，不修改业务代码。文中的时延均区分“当前观察”与“目标预算”。

## 一、结论

现在不应该先换框架、加 Redis、堆 worker，或者直接开始接 Agent。最高收益顺序是：

1. 修复已经复现的 SQLite 嵌套写自锁。这是确定性故障，不是普通性能问题。
2. 删除前端重复请求、轮询泄漏和播放关键路径中的非必要请求。
3. 把“点击播放到出声”作为独立链路优化，减少 Bilibili 重复查询并复用上游连接。
4. 加入分段耗时指标，再替换开发服务器、梳理流代理并发模型。
5. 接 Agent 前先修 AMEM 的全量扫描、长写事务和伪 `project_fast`，否则数据越多响应越慢。

一句话判断：**当前最大的速度问题不是 Vue、Flask 或模型本身，而是重复工作、串行网络瀑布、错误事务边界以及未来 AMEM 的全量计算。**

## 二、已经确认的问题

| 级别 | 问题 | 证据 | 实际影响 |
|---|---|---|---|
| P0 | 批量加歌发生 SQLite 自锁 | `py-radio/library_service.py:336-361` 在外层写事务内调用 `upsert_track()`，后者另开写连接 | 临时库已复现：批量加入 2 首不同歌曲约 5 秒后 `database is locked` |
| P0 | 播放统计轮询不会在暂停时停止 | `bilibili-player/src/stores/playerStore.ts:265-298` | 播放后每个活跃页面最高 3,600 请求/小时；暂停、异常、队列结束后仍可能继续 |
| P0 | 播放初始化缺少 single-flight | `playerStore.ts:279-375,419-421` | 首屏初始化未完成时点击播放，可重复建 Audio、拉队列、连接 Socket.IO |
| P0 | 常驻 Socket.IO 未参与当前 HTTP 播放主链路 | `playerStore.ts:321,367,633,783` | 启动增加握手、保活和重连；客户端约 40 KB raw / 13 KB gzip 可从主包移除 |
| P0 | 点击播放存在严格串行瀑布 | `playerStore.ts:411-440,707-725` | 已知 `cid` 仍等待封面查询，再等统计 reset，再等 stream-info，最后才开始取媒体 |
| P0 | Docker 运行 Werkzeug 开发服务器 | `py-radio/app.py:739-752`、`py-radio/Dockerfile:15` | 每条长音频流占线程；缺少受控并发、优雅退出和生产容量边界 |
| P0 | AMEM 读写均有结构性全量工作 | `agent/agent_memory_runtime/runtime.py:142-218,256-296,515-556,654-707` | event/memory 增长后 ingest、retrieve、replay、所谓 fast path 持续变慢 |
| P1 | 资料库初始化无条件拉两轮 | `bilibili-player/src/stores/libraryStore.ts:46-77` | 无本地迁移也请求 recent/likes/playlists 各两次，共 6 个请求 |
| P1 | 同一歌曲详情被 Bilibili 重复查询 | `py-radio/bili_client.py:87-254` 与播放/详情页调用链 | 一次播放和打开详情可能产生 3-5 次上游调用，尾延迟和限流风险都被放大 |
| P1 | 音频与图片代理每次新建上游连接 | `py-radio/stream_service.py:47-82`、`py-radio/app.py:693-724` | 重复 TCP/TLS 握手，断连响应未可靠关闭，长期占用 Flask 线程 |
| P1 | SQLite 没有并发参数和关键查询索引 | `py-radio/database.py:21-27,51-157` | 没有 WAL、busy timeout；时间排序和事件分析随数据量增大退化 |
| P1 | 最大静态图片严重过大 | `dist/assets/icon-*.png` | 1254×1254 图约 1.1 MB，只以 36/48 px 展示；登录首屏大部分传输来自它 |
| P1 | Nginx 把所有 API 当长流处理 | `deploy/nginx.conf:14-23` | 全部 `/api/` 禁止 buffering 且超时 1 小时，普通 JSON 与音频流没有隔离 |

补充构建观察：当前主 JS 约 208 KB raw、约 73 KB gzip，主 CSS 约 34 KB raw；路由页面已经动态加载，这部分不是首要瓶颈。真正异常的是约 1.1 MB 的应用图标。

## 三、响应速度应按四条链路分别治理

### 3.1 页面首屏

当前链路大致是：

```text
HTML/JS/CSS -> auth/status -> 进入主布局
             -> recent + likes + playlists（两轮）
             -> queue
             -> Socket.IO connect
             -> 大图标下载/解码
```

优化顺序：

1. 将应用图标导出为实际显示尺寸的 96/128 px WebP 或优化 PNG，目标小于 20 KB。
2. 资料库第二轮 fetch 只在确实执行过本地迁移写入后触发；正常启动保持 3 个并行请求。
3. 给 `player.initialize()` 和 `WsClient.connect()` 增加 Promise single-flight 与幂等保护。
4. 当前 HTTP + `<audio>` 已承担播放、暂停和 seek；确认没有实时业务依赖后删除常驻 Socket.IO。未来确有实时功能时再按需连接。
5. 登录页不要静态带入播放器和完整 NowPlaying 代码；NowPlaying 首次打开再异步加载。
6. 本地 fallback 迁移禁止对最多 100 条 recent、全部 likes/playlists 使用无界 `Promise.all`；改为批量端点或并发限制 4-6。
7. 哈希静态资源设置一年 `immutable` 缓存；HTML 使用 `no-cache`，确保新版本入口可更新。
8. 超过 100-200 行的 Likes、Playlist、Queue、评论和字幕使用虚拟列表。

不建议为了首屏立刻合并成巨型 bootstrap API。先消除重复请求并测量；三个并行的本地 JSON 请求本身成本很低，只有实测 RTT 仍超预算时再考虑聚合。

### 3.2 搜索与详情

当前搜索已经有分页和 `IntersectionObserver`，方向正确；但 `searchSeq` 只是丢弃旧结果，没有取消旧请求。后端仍会完整访问 Bilibili。

建议：

1. 前端使用 `AbortController` 取消前一次搜索、切歌后的旧详情请求。
2. 前端以 `query + page` 建 5-10 分钟有界 LRU，返回搜索页时直接复用。
3. 后端为 video detail 建 `bvid` TTL cache，为 player info 建 `(bvid,cid)` TTL cache，并提供 single-flight，避免同一 key 并发击穿。
4. 搜索结果采用较短 TTL，例如 30-120 秒；失败仅做数秒 negative cache，不能长时间缓存上游错误。
5. 为每条路由设置总 deadline。Bilibili 请求使用 connect/read 分离超时，不再统一一个 10 秒值。
6. 重试只覆盖连接错误、429、502、503 等可重试错误，并限制次数、加入 jitter；不能让 guest-cookie、412 和业务层重试层层叠加。

预期结果：同一歌曲从 3-5 次 Bilibili 请求降到冷启动约 2 次（detail + playurl），温启动 0-1 次。

### 3.3 点击播放到出声

这是播放器最重要的性能指标。当前关键路径包含不应阻塞播放的封面补全和统计 reset。

目标链路应收敛为：

```text
click
  -> 已知 cid：直接请求/命中 stream-info
  -> 浏览器请求 media proxy
  -> 代理复用连接访问 Bilibili CDN
  -> 收到首个音频字节
  -> canplay / playing

封面补全、recent 写入、统计、分析事件：全部旁路或异步
```

具体改造：

1. 已知 `cid` 时不要等待 cover API；封面异步补全并更新队列即可。
2. 从播放关键路径移除 `POST /api/stream/stats/reset`，统计若保留应由流会话自身初始化。
3. stream-info 使用有容量上限的 TTL/LRU + single-flight；签名 URL 到期或返回 403 时原子失效并只重新解析一次。
4. 音频代理使用独立 `requests.Session` 和受控连接池，设置 `(connect timeout, read timeout)`。
5. 优先主 URL，连接/特定上游错误时尝试 backup URL；所有 generator 使用 `finally` 关闭 upstream response。
6. 把 8 KB 分块改为经基准测试确定的 32-128 KB。当前每 8 KB 还更新一次全局锁统计，吞吐越高锁越频繁。
7. 透传 Range、Content-Range、Accept-Ranges，验证 seek、断点续传、206 状态和客户端提前断连。
8. Nginx 仅对音频 stream location 关闭 buffering 并使用长 read timeout；普通 JSON 恢复 buffering 和 15-30 秒超时。

中期如果需要同时服务较多长流，最佳结构是将 media proxy 从 Flask 控制面分离。不要用无限增加 Flask 线程解决长期连接问题。

### 3.4 Agent 首 token 与完整回答

播放器控制与 Agent 必须解耦：play、pause、seek、next 走确定性直达命令，不能先问 LLM。Agent 只负责解释、推荐、组合工具和生成自然语言。

未来问候和推荐应以预计算为主：

```text
播放事件 -> O(1) event/outbox 入队
         -> worker 增量更新 user_track_stats
         -> 定时生成 personality snapshot / gap candidates
         -> 预生成 greeting draft / recommendation card

打开页面 -> 读取 versioned hot-context 或预生成卡片
         -> 需要自由对话时再流式调用 LLM
```

缓存键至少包含：

```text
user_id + memory_revision + intent + locale
```

单 Planner 的正确含义是“唯一决策策略”，不是“所有用户共用一个线程”。同一 user/session 的 turn 串行，不同用户可并发；只读工具可在严格并发和 deadline 下并行。Tool Loop 最多两轮，长期 ingest 放到响应结束后。

## 四、AMEM 接入前必须先修的性能问题

AMEM 目前不能直接承担生产热路径：

1. `ingest_async()` 仍生成全量 snapshot，不是 O(1) 入队。
2. snapshot 会读取全部 events 和 memories、排序并序列化全量 JSON 做 hash。
3. retrieve 使用 `list_records()` 全量反序列化、Python 过滤/评分、全排序，trace 又触发 snapshot。
4. `apply_event()` 与 worker 按 event id 查找都先全量加载事件，replay 至少会退化到 O(E²)。
5. SQLite store 连 SELECT 也进入 `BEGIN IMMEDIATE`，读请求会争抢唯一 writer；只启 WAL 解决不了该事务设计。
6. `project_fast` 先同步构建 fallback，fallback 仍回查数据库；150 ms 只包住 future wait，超时任务不能取消且单线程 executor 会积压。

AMEM P0 改造：

1. `ingest_async = event + queue/outbox + revision` 的短事务，目标 O(1)。
2. Store 增加 `get_event(event_id)` 和带索引的候选查询；先用 SQL/FTS 预筛 50-100 条，再做六维评分。
3. SELECT 使用只读/autocommit；`BEGIN IMMEDIATE` 只用于短写事务，并记录 lock wait。
4. snapshot 改为定时或每 N 个事件生成，全量 hash 放后台。
5. hot-context 持久化完整、安全过滤后的上下文，不只存 memory ids。
6. worker 增加 lease、heartbeat、幂等键、超时回收和 queue lag 指标。
7. 用 1 万、10 万、100 万 events 建基准测试，不能只用几十条 demo 数据验收。

音乐结构化问题优先查聚合表，例如 `user_track_stats`、artist/genre/time-slot stats；只有评价、感想和语义回忆需要 FTS/embedding。把每次 pause/progress 都 embedding 是成本高、效果差的做法。

## 五、数据库与后端生产化

### 5.1 先修事务边界

`_batch_playlist_items()` 的自锁应使用同一 connection 完成 track upsert、查重、position 计算和批量插入。不要通过增大 SQLite timeout 掩盖嵌套写连接；那只会让用户等待更久后再失败。

随后再做：

- schema migration 只在进程启动时执行一次，不要每个 Service 构造都 `init_db()`。
- `journal_mode=WAL`、`busy_timeout`、`synchronous=NORMAL`，并记录 lock wait/retry。
- 按真实 SQL 和 `EXPLAIN QUERY PLAN` 增加索引，不做无依据的索引堆积。
- 推荐候选和人格统计采用增量聚合表，不在请求时扫完整事件历史。

建议候选索引：

```sql
recent(last_played_at DESC)
likes(created_at DESC)
playlist_items(playlist_id, position)
playback_events(track_id, created_at)
playback_events(session_id, id)
analysis_events(event, created_at)
```

引入多用户后，这些复合索引必须以 `user_id` 为首列重新设计。

### 5.2 生产服务器与进程状态

先选一个受支持的生产 WSGI/Socket.IO 部署方案，明确线程数、最大连接、超时、优雅退出和健康检查。然后再评估 worker 数。

当前不能直接增加 Web worker，因为以下状态都在进程内：

- `current_video_info` / `current_audio_info`
- stream-info cache
- stream stats
- Socket.IO 连接与回调状态

多 worker 会让这些状态分裂。正确顺序是先删除全局播放器状态、将需要共享的会话状态持久化或明确为客户端状态，再做水平扩展。

### 5.3 其他生产风险

这些问题不一定直接提高毫秒数，但上线前必须处理：

1. Bilibili 登录 cookie 不是应用登录；至少要有本应用的 session/auth 与用户隔离。
2. `CORS(app)` 和 Socket.IO `cors_allowed_origins="*"` 需要按部署域名收紧。
3. 未知异常不能把 `str(error)` 原样返回客户端，避免泄漏内部信息。
4. 数据库 schema 需要版本化 migration、备份、恢复演练和启动兼容检查。
5. 图片代理必须限制最终重定向 host、Content-Type、Content-Length 和总下载大小。
6. Compose 加 backend/frontend healthcheck、资源限制、日志轮转和只读/最小权限运行策略。

## 六、先建立可验收的指标

不能只测“页面感觉快了”。每个请求使用 request id，并分段记录：

```text
route_total_ms
sqlite_wait_ms / sqlite_query_ms
bili_connect_ms / bili_ttfb_ms / bili_total_ms
cache_hit{detail, player_info, playurl, image}
stream_ingress_to_headers_ms
stream_ingress_to_first_chunk_ms
stream_bytes / disconnect_reason
agent_context_ms / tool_ms / llm_ttft_ms / llm_total_ms
queue_lag_ms / fallback_rate
```

日志禁止记录 cookie、完整签名 URL、评价原文和敏感 memory payload。前端用 `performance.mark()` 记录 click、stream-info done、media request、canplay、playing；页面记录 LCP、INP 和资源大小。

## 七、建议 SLO

以下是目标预算，不是当前实测值：

| 路径 | p95 目标 | 硬上限/说明 |
|---|---:|---|
| 本地 SQLite API | `<20 ms` | p99 `<50 ms`，`database is locked = 0` |
| 播放器控制 API | `<100 ms` | 不经过 LLM |
| 已缓存详情 API | `<50 ms` | 不访问 Bilibili |
| 冷搜索/详情 | `<1.5 s` | p99 `<3 s`，route deadline 8 s |
| stream 入口到首字节，签名命中 | `<800 ms` | p50 `<250 ms` |
| stream 入口到首字节，签名未命中 | `<2.5 s` | 包含一次 playurl 解析 |
| 点击播放到 canplay，warm | `<2.0 s` | 单独统计网络环境 |
| 点击播放到 canplay，cold | `<4.0 s` | 不包含用户手势限制 |
| event/outbox 入队 | `<30 ms` | 不同步派生 |
| 缓存问候/推荐卡 | `<150 ms` | LLM 故障仍可返回 |
| memory candidate retrieval | `<80 ms` | 120 ms 截止 |
| 无工具 Agent TTFT | `<1.2 s` | 流式输出 |
| 无工具完整回答 | `<4 s` | 受输出长度约束 |
| 一轮本地工具完整回答 | `<6 s` | Planner 总超时 8 s |
| 强信号派生队列延迟 | `<2 s` | 评价/明确反馈 |
| 普通播放统计队列延迟 | `<10 s` | heartbeat 聚合写入 |

## 八、实施顺序

### O0：基线与确定性故障，1-2 天

- 固化“批量加入 2/100 首”的回归测试，修复嵌套 SQLite 写连接。
- 加 request id、route、SQLite、Bilibili、stream TTFB 分段指标。
- 建冷/暖播放各 30 次基线；记录 p50/p95/p99 和上游调用次数。

验收：无数据库锁错误；性能报表能解释时间花在哪里。

### O1：零浪费快赢，1-2 天

- 删除或限制 stats 轮询；暂停、隐藏、错误、卸载时必须停止。
- library 初始化取消无条件第二轮请求。
- player/socket 初始化 single-flight。
- 确认后移除没有参与 HTTP 播放链路的常驻 Socket.IO；若保留则改为按需连接。
- 本地资料迁移改批量接口或限制并发 4-6，禁止无界 `Promise.all`。
- 图标压缩到小于 20 KB；配置静态 immutable cache 与 JS/CSS gzip。
- 搜索与详情请求支持 AbortController。

验收：正常首屏 library 请求由 6 降到 3；无重复 Socket；播放页面空闲时 stats 请求为 0。

### O2：播放主链路，3-5 天

- 封面补全和统计移出关键路径。
- detail/player-info/playurl 有界 cache + single-flight。
- 上游 Session/连接池、失败刷新、backup、close、Range 回归测试。
- Nginx 分离 JSON、image、stream location。

验收：warm 点击到 canplay p95 `<2 s`；单次播放的 Bilibili 上游请求上限被契约测试固定。

### O3：生产运行与数据层，3-5 天

- schema migration 单点执行；WAL、busy timeout、索引和并发测试。
- 移除全局播放器状态，再切生产 WSGI/Socket.IO server。
- 1/5/10 并发 Range stream 压测，同时观测普通 API p95、线程、FD、内存。
- 收紧 auth/CORS/error/代理边界，补 healthcheck、备份恢复和日志轮转。

验收：流并发时普通控制 API 仍满足 SLO，提前断连不泄漏连接或线程。

### O4：AMEM/Agent 性能地基，5-10 天

- O(1) ingest_async、短写事务、indexed candidate retrieval、增量 snapshot。
- 建 `user_track_stats` 与 versioned hot-context。
- 问候/推荐预计算，Agent SSE，Tool Loop 两轮上限和全链路 deadline。
- 跑 1 万/10 万/100 万 event 基准与 memory eval 回归。

验收：数据量增长一个数量级时，ingest/retrieve p95 不随全量记录线性增长；LLM 或 worker 故障不影响播放器。

## 九、不要做的伪优化

- 不要先把 Flask 全面改成 async；主要瓶颈仍是外部请求、长流、事务和重复工作。
- 不要直接增加 Web worker；当前进程内状态会先分裂。
- 不要只开启 WAL 就认为 SQLite 并发已解决；嵌套写和 AMEM 的 `BEGIN IMMEDIATE` 仍会锁。
- 不要把 timeout 调大来掩盖锁与重试；这只会放大 p99。
- 不要缓存永久有效的 Bilibili 签名 URL；必须有 TTL、容量和 403 失效。
- 不要压缩音频响应；只压缩 JS、CSS、JSON、SVG 等文本资源。
- 不要让 LLM 参与 play/pause/seek 的同步控制路径。
- 不要给每个播放心跳做 embedding 或同步 Reflection。
- 不要先调 AMEM 六维评分权重，却继续全量加载全部 memories。
- 不要把独立 worker 当成性能修复；如果 `ingest_async` 仍全量 snapshot，拆进程只会把慢操作搬位置。

## 十、最终优先级

如果现在只能做五件事，应当依次是：

1. 修复批量歌单 SQLite 自锁并加回归测试。
2. 移除 stats 每秒轮询、资料库双拉取和重复初始化。
3. 将封面与统计移出播放关键路径，给 Bilibili detail/playurl 加有界 single-flight cache。
4. 加 stream TTFB/上游/DB 指标，随后替换生产服务器并分离流媒体路径。
5. AMEM 先完成 O(1) 入队、索引候选检索、短事务和 hot-context，再接音乐 Agent。

做到这五项后，项目才具备继续建设音乐陪伴 Agent 的性能地基；在此之前增加更多功能只会让延迟和故障更难定位。

## 十一、本轮复核记录

- `python -m unittest discover -s tests -v`：30 个现有后端测试全部通过，耗时 0.522 秒。
- 独立最小复现：新建歌单后一次批量加入两首尚未入库、track id 不同的歌曲，5.507 秒后返回 `OperationalError: database is locked`。
- 现有 `test_batch_preview_and_add_deduplicates` 与 API 测试都传入同一首歌两次；去重后 `to_add` 只有一条，只触发一次嵌套 `upsert_track()`，因此没有覆盖第二条新 track 导致的自锁。
- 本轮未修改业务代码，只新增并更新本分析文档。

## 十二、五项优先级的白话说明

### 1. 修复批量歌单 SQLite 自锁

现在一次往歌单加入多首新歌时，程序先拿着一个数据库写锁，又从内部打开第二个连接申请写锁。第二个连接只能等待自己释放锁，最终约 5 秒后失败。这不是“偶尔有点慢”，而是确定性代码错误。

正确做法：一次批量加歌只使用一个数据库连接和一个事务，全部写完后统一提交。

### 2. 删除无效请求和重复初始化

播放器开始播放后，前端每秒请求一次流量统计；暂停后仍可能继续。应用启动时 recent、likes、playlists 正常情况下也会各拉取两遍。初始化尚未完成时马上点击播放，还可能重复创建播放器和 Socket 连接。

这些请求没有给用户带来功能，却持续占用浏览器、Flask、日志和数据库。应删除无用统计轮询、取消无条件第二轮拉取，并保证初始化同时只执行一次。当前 Socket.IO 没有参与 HTTP 音频播放，确认没有其他实时依赖后可以直接移除。

### 3. 缩短“点击播放到出声”的等待链

当前用户点击歌曲后，程序会依次等待播放器初始化、封面补全、统计重置、音频地址解析、代理连接 Bilibili CDN，最后浏览器才开始加载音频。其中封面和统计根本不需要挡住播放。

正确做法：播放主链只保留“取得音频地址 -> 收到首个音频字节 -> 播放”；封面、最近播放和分析事件放到旁路异步执行。同时短时缓存已经解析过的歌曲详情和音频地址，复用到 Bilibili 的网络连接。

### 4. 先测出慢在哪里，再更换生产运行方式

目前日志只知道接口成功或失败，不知道时间花在 SQLite、Bilibili、音频代理还是浏览器缓冲。没有分段数据就直接换框架，可能做很多工作却没有改善用户等待。

应先记录每一段耗时，再把 Docker 中的 Werkzeug 开发服务器换成受控的生产服务器。音频是长连接，后续并发量增大时应与普通 JSON API 分开承载。不能现在直接增加多个 Web worker，因为当前播放状态和缓存都保存在单个进程内，多进程后数据会彼此不一致。

### 5. AMEM 先修底层复杂度，再接音乐 Agent

当前 AMEM 的部分 ingest、retrieve、snapshot 会读取或哈希全部历史事件和记忆。数据少时看不出来，累计几万、几十万次播放后，每次操作都会越来越慢。所谓 async 和 `project_fast` 目前没有消除这些全量工作。

正确做法：播放事件请求只做一次很短的“写事件并入队”；worker 在后台增量更新统计；检索先利用索引筛出少量候选；问候、人格和久违歌曲候选提前计算。这样打开播放器时主要是读取现成结果，而不是临时扫描全部历史再调用 LLM。

### 指标名词

- `p95 < 2s`：测 100 次，大约至少 95 次在 2 秒内完成；它比只看平均值更能暴露偶发卡顿。
- `canplay`：浏览器已经取得足够音频数据，可以开始播放的事件。
- `TTFT / 首 token`：用户发出问题后，到 Agent 开始输出第一个字的等待时间。
- `single-flight`：同一件事同时被调用多次时，只真正执行一次，其余调用共享这个结果。
