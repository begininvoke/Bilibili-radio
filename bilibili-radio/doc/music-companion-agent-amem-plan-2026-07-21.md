# 音乐陪伴 Agent + AMEM 接入评审与任务拆解

- 日期：2026-07-21
- 状态：架构评审草案，等待 M0 接纳验证
- 范围：产品、数据、架构、隐私、任务和验收标准
- 本轮变更：仅新增本文档，不修改业务代码

## 1. 结论

这个方向值得做，但不能按“先接一个聊天 Agent，再把播放记录喂给记忆”的顺序推进。

真正有价值的产品不是播放器旁边多一个聊天框，而是一个能够：

1. 基于真实收听行为形成可解释的音乐画像；
2. 在合适时间给出克制、准确的问候和推荐；
3. 记住用户主动表达的评分、标签和感受；
4. 允许用户查看、纠正、撤回和遗忘这些记忆；
5. 每一条判断都能追溯到具体事实。

建议对项目作出 **“有条件推进”** 的决策。M0 的接纳门槛未通过前，不把 AMEM 当成已完成的生产组件，也不开始构建完整聊天界面。

### 1.1 四个最高优先级问题

| 优先级 | 问题 | 直接后果 | 决策 |
|---|---|---|---|
| P0 | 前端没有上报真实播放事件 | 当前播放次数接近“发起播放请求次数”，画像和跳过率会失真 | 先完成事件事实层 |
| P0 | 当前应用没有真正的用户/租户隔离 | PRIVATE 评价和记忆无法在联网部署中得到保证 | V1 明确限定单用户自托管；多用户另立项目 |
| P0 | AMEM 没有 Planner Tool Loop、MCP 和生产级隐私存储 | 用户设想的若干调用链不能直接实现 | 建应用侧 Planner、Tool Gateway 和隐私边界 |
| P0 | “Flask 守护线程到 M5 再拆”与独立 worker 目标矛盾 | 重载、多 WSGI 进程和 Flask 重启会重复执行或中断任务 | 从首个异步里程碑起使用独立进程 |

### 1.2 产品定位

对外建议使用“音乐画像”或“聆听画像”，不要使用可能暗示心理诊断的“人格分析”。系统只能根据音乐行为描述偏好和习惯，不能推断抑郁、疾病、人格障碍、家庭关系等敏感结论。

V1 的差异化应是 **“有证据、可纠正、不会越界的音乐陪伴”**。

## 2. 当前仓库事实

### 2.1 已有基础

| 能力 | 当前实现 | 证据 |
|---|---|---|
| 播放会话和事件表 | 已有 `playback_sessions`、`playback_recent`、`playback_events` | `py-radio/database.py:88-121` |
| 播放事件 API | 已有 `/api/playback/events` | `py-radio/app.py:401-415` |
| 有效收听、完成和短跳过规则 | 已在 `PlaybackService` 中实现 | `py-radio/playback_service.py:21-112` |
| 收藏、最近播放和歌单 | 已持久化到 SQLite | `py-radio/database.py:34-87` |
| 首页问候位置 | 已有按时段问候 | `bilibili-player/src/views/HomeView.vue:3-6,66-73` |
| 推荐位置 | 首页已有“为你推荐”占位区 | `bilibili-player/src/views/HomeView.vue:24-27` |
| 全局播放器 | `AppShell` 已常驻唯一 `PlayerBar` | `bilibili-player/src/components/layout/AppShell.vue:1-14` |
| AMEM 源码 | 已放在 `agent/agent_memory_runtime` | 当前仓库目录 |

### 2.2 必须先修的事实层缺口

1. 前端 API client 没有 `/api/playback/events` 的调用方法。现有 client 只有 recent、like 和通用 analysis marker，见 `bilibili-player/src/api/client.ts:209-247,338-344`。
2. `HTMLAudioElement` 的 `timeupdate`、`ended`、`pause` 等回调只更新前端状态，没有写入播放事件，见 `bilibili-player/src/stores/playerStore.ts:289-317`。
3. 请求到音频流后立即调用 `addRecent`，见 `bilibili-player/src/stores/playerStore.ts:411-440`。这会把点击或加载成功误当成有效收听。
4. `next`、`pause`、`stop` 和曲目自然结束没有形成完整、可去重的服务端事件链，见 `bilibili-player/src/stores/playerStore.ts:568-643`。
5. 当前 `PlaybackService` 把 `pause` 视为 session 的结束事件，恢复后 `ended_at` 也不会清空。正式建模时必须重新定义 pause、resume、stop、skip 和 natural end 的语义。

在这些问题修复前，不能上线“连续三天听钢琴曲”“一个月没听周杰伦”等断言。

### 2.3 当前隐私和部署边界

1. 所有业务表都没有 `user_id/profile_id`，见 `py-radio/database.py:34-171`。
2. B 站认证以固定 provider 为主键，只保存一份账号状态，见 `py-radio/database.py:129-138`。
3. Flask 和 Socket.IO 当前允许任意来源，业务 API 没有应用用户鉴权，见 `py-radio/app.py:27-38`。
4. B 站登录是访问 B 站资源的凭据，不等于本应用的用户认证。
5. 后端仍以 `socketio.run(... allow_unsafe_werkzeug=True)` 启动，见 `py-radio/app.py:739-752`。
6. Compose 当前只有 backend/frontend，没有 worker，见 `docker-compose.yml:1-21`。
7. `agent/` 是裸源码副本；后端 requirements、Docker build context 和版本锁都没有接入它。

因此，V1 最合理的范围是 **单用户、自托管、单机、单 worker**。这仍然需要最小应用鉴权，例如本地账号会话或部署访问令牌；“自托管”不能等价为“任何能访问端口的人都能读取私人评价”。如果目标是公网多用户服务，必须先完成用户认证、所有表的租户字段、查询隔离、每用户密钥和越权测试；这不应隐含在本次 AMEM 接入工作中。

## 3. AMEM 能力真值表

上游项目：[ourhome-macro/amem-agent-memory-framework](https://github.com/ourhome-macro/amem-agent-memory-framework)。截至本评审日期，GitHub 页面显示项目仅有 9 次提交、无 release/package，根目录未展示 LICENSE。若两个仓库由同一所有者维护，也应先补许可证、版本标签和固定依赖方式。

| 用户设想中的能力 | 源码实际状态 | 本项目决策 |
|---|---|---|
| `ingest` / `ingest_async` | 存在 | 可作为事件入口，但必须加幂等适配 |
| `run_derivation_once` / SQLite queue | 存在 | 可复用核心思路，必须补 lease、重领和可观测性 |
| `retrieve` | 存在；返回 `(list[MemoryRecord], RuntimeTrace)` | 六维得分从 trace 读取，不按错误签名开发 |
| `project_fast` | 存在，但 fallback 仍读取 snapshot 和当前 memory DB | 不能当高可用缓存；问候需要应用级物化缓存 |
| `respond_fast` / `respond_stream` | 存在，仅文本生成 | 可用于无工具的表达层，不是 Planner |
| `ToolExecutor` / `ToolPolicy` | 存在，但只有同步调用、allow/block/side-effect | 作为审计参考；应用侧补 schema、超时、确认和权限 |
| LLM Function Calling loop | 不存在 | 新建 `MusicAgentService` 状态机 |
| MCP | 不存在 | M7 再加 adapter，不阻塞 MVP |
| ScoreBreakdown 六维评分 | 存在 | 可保留概念，但需要中文和结构化检索改造 |
| 中文关键词检索 | 不可用；tokenizer 只匹配 `[A-Za-z0-9_]` | M0 必测，M3 前替换 |
| `days_since_last_play > 30` | Query 不支持范围/元数据表达式 | 用播放器 SQL 计算候选，不伪装成 memory retrieval |
| Compression | 只按 token budget 选择记录 | 音乐聚合和摘要由本项目实现 |
| PRIVATE 访问控制 | principal 只有 `agent_id` | 不能承担多用户租户隔离 |
| Human Review | 默认关闭，队列仅内存 | M6 做持久化审核中心 |
| PII Vault | 明确是 tests/demos 的内存 XOR 实现 | 不进入生产；评价原文由应用层认证加密 |
| 语义敏感内容识别 | 仅邮件、银行卡和敏感字段名等规则 | “父亲去世”等内容不会被可靠识别 |
| `approve_review_item` | 审批候选记忆 | 不能用于查看或解密用户评价原文 |
| snapshot | 只有 rule/config/sequence/hash/count/hot IDs | 不是数据备份，不能回滚 baseline |
| replay | 先清空 memory 再重建 | 生产升级只能 shadow replay 后切换 |
| Eval | 只校验指定 memory ID 是否被召回 | 音乐 Eval DSL 和指标需扩展 |
| `caused_by_event_id` | 只有 Event 字段和序列化 | 因果查询、链路校验和效果分析需自行实现 |

### 3.1 额外的生产风险

1. AMEM CLI 的 worker bootstrap 使用 JSONL stores，不会自动使用 `SQLiteStoreBundle`。
2. SQLite job 被 claim 后变为 `running`；进程若此时崩溃，没有 lease/reaper 将其恢复为 pending。
3. SQLite 没有 `busy_timeout` 和锁冲突重试。
4. 当前 store 的普通 connection 也进入 `BEGIN IMMEDIATE`，读取可能争用写锁；必须做双进程读写并发 spike。
5. `ingest_async` 仍会保存 snapshot，而 snapshot 会扫描事件和记忆；数据增长后的写放大需要基准测试。
6. Human Review 和 PII Vault 都没有进入 `SQLiteStoreBundle`。
7. `project_fast` 的 fallback 本身需要读数据库；数据库卡住时它也可能卡住，executor 中已运行的超时任务也无法真正取消。
8. 内建派生规则只识别通用 EventKind。`track.played`、`profile.snapshot` 等音乐事件不会自动产生任何记忆。

AMEM 的正确定位是 **“可借鉴和扩展的事件源记忆内核”**，不是现成的 Agent、MCP、推荐或隐私平台。

## 4. V1 产品范围

### 4.1 核心体验

#### 场景一：可信问候

用户晚上打开播放器：

> 欢迎回来。你最近三天有 7 次有效收听来自钢琴相关曲目。今晚继续，还是换一种风格？

这个结论必须满足：

- “三天”“7 次”“钢琴相关”都有结构化证据；
- 样本不足时只说普通问候；
- 画像过期或 worker 不可用时使用确定性 fallback；
- 用户可以查看“为什么这样说”。

#### 场景二：久违歌曲推荐

系统从真实候选中找到超过 30 天未有效收听、当前仍可播放、近期没有连续快速跳过的曲目，再给出两首推荐。LLM 只能在候选内排序和写理由，不能凭空生成曲名。

#### 场景三：私人评价

播放详情提供一个轻量评价区：

- 1-5 分或等价的紧凑评分控件；
- 可选心情/场景标签；
- 可选留言和感想；
- “允许用于个性化”开关；
- 编辑、删除和查看历史评价。

没有留言也可以在数秒内完成评价。评价列表作为 Library 下的独立视图，支持曲目、评分、标签和时间筛选。

#### 场景四：单 Planner 聊天

聊天页放在现有 `AppShell` 内，复用全局唯一 `PlayerBar`、`playerStore` 和 `HTMLAudioElement`。不要再创建第二套音频实例。Agent 可以搜索、推荐、查看安全摘要，并在用户明确表达意图时播放或加入队列。

### 4.2 V1 非目标

- 多 Agent；
- 心理健康、疾病或人格障碍推断；
- 跨用户全局趋势；
- 原始私密留言默认进入 prompt；
- 自动删除用户内容；
- 自动播放或后台打断用户；
- 向量数据库和大规模语义检索；
- 分布式、多主机、多 worker；
- 模型微调；
- MCP 先于内部工具契约落地。

## 5. 目标架构

```text
Vue 3
  - 首页问候 / 推荐
  - Agent Chat
  - 评价编辑 / 评价列表
  - 全局唯一 PlayerBar + playerStore
        |
        | REST + SSE；播放 UI action 走白名单 dispatcher
        v
Flask 应用进程
  - 领域 API
  - ReviewService
  - RecommendationService
  - MusicAgentService / Tool Gateway
  - MemoryPort（隔离 AMEM 内部 API）
        |
        | 同一业务事务
        v
bili_radio.sqlite3
  - track / playback / like / review
  - music_profile_snapshots
  - recommendation_impressions
  - agent_outbox
        |
        | lease + at-least-once
        v
独立 music-agent-worker（从 M1 开始）
  - outbox relay
  - AMEM ingest / derivation
  - nightly profile job
  - retention / retry / DLQ
        |
        v
amem.sqlite3
  - events / memories / derivation_jobs
  - audit / logical snapshots
```

### 5.1 不变原则

1. `bili_radio.sqlite3` 是用户行为、评价和推荐结果的事实源。
2. AMEM 是派生读模型，不是播放历史、评价原文或推荐候选的事实源。
3. HTTP 请求只做短事务写入事实和 outbox，不等待 LLM 或大聚合。
4. worker 和 Flask 任一进程故障都不能影响基本播放。
5. Agent 不直接写 memory；领域动作先形成事件，再由规则派生。
6. LLM 负责语言表达、有限重排和受约束反思，不负责决定事实。
7. 所有跨进程投递采用确定性 `event_id`，按 at-least-once 设计。

### 5.2 为什么从 M1 就独立 worker

“M1-M4 放 Flask 守护线程，M5 再拆”应从方案中删除，原因如下：

- Flask debug reloader 可能启动两次线程；
- 多个 WSGI worker 会各启一份后台循环；
- Flask 重启会中断派生，直接违背隔离目标；
- daemon thread 没有可靠的优雅退出、lease 和崩溃恢复；
- 现有 Compose 已经是多服务部署，增加一个 worker service 的成本低于后期迁移。

单元测试可以在同进程调用 `run_once()`；实际开发和生产环境从 M1 起都应运行独立 worker。

## 6. 数据与事件设计

### 6.1 统一事件信封

每个领域事件至少包含：

| 字段 | 含义 |
|---|---|
| `event_id` | 全局稳定 UUID；重试不改变 |
| `schema_version` | 事件 schema 版本 |
| `profile_id` | 本地用户画像 ID |
| `kind` | 领域事件名 |
| `aggregate_type/id` | track、review、recommendation、session 等 |
| `session_id` | 播放或对话 session |
| `occurred_at` | 服务端归一后的发生时间 |
| `correlation_id` | 一次推荐/对话/操作链路 |
| `caused_by_event_id` | 直接因果父事件，可空 |
| `payload` | 最小化结构化数据 |
| `privacy_class` | public/private/sensitive |

浏览器是 `HTMLAudioElement` 播放状态的观测方，但它不是可信事实源。Flask 必须校验 session、曲目、时间单调性、最大 listen 增量、幂等键和上报频率。

### 6.2 事件清单

| 事件 | 触发条件 | 是否进入长期记忆 | 备注 |
|---|---|---|---|
| `playback.started` | 音频实际触发 play | 否 | 分析和 session 起点 |
| `playback.progressed` | 节流 heartbeat | 否 | 更新 session，不为每次 heartbeat 建 memory |
| `playback.paused` | 用户暂停 | 否 | 不结束 session |
| `playback.resumed` | 同一 session 恢复 | 否 | 与 pause 配对 |
| `playback.qualified` | 首次达到有效收听阈值 | 是，低/中信号 | 每 session 只发一次 |
| `playback.completed` | 达到完成规则或自然结束 | 是，中信号 | 记录完成率 |
| `playback.skipped` | 用户切歌且低于阈值 | 是，低信号 | 需要 skip reason |
| `track.liked/unliked` | 喜欢状态变化 | 是，高信号 | 撤回必须传播 tombstone |
| `track.reviewed` | 新建或更新评价 | 是，高信号 | 默认只传评分/标签/安全摘要 |
| `track.review_deleted` | 删除评价 | 是，删除信号 | replay 不得复活 |
| `profile.snapshot_created` | 聚合任务生成新画像 | 是，派生记忆 | 包含规则版本和来源 |
| `recommendation.impression` | 推荐真正展示 | 否 | 不能用“生成了”代替“展示了” |
| `recommendation.enqueued` | 用户加入队列 | 是，反馈信号 | 保留 recommendation ID |
| `recommendation.play_started` | 推荐曲目开始播放 | 是，反馈信号 | 建立因果链 |
| `recommendation.qualified/completed/skipped` | 推荐后的实际结果 | 是，反馈信号 | 用于评估推荐质量 |
| `agent.greeting_shown` | 问候真正展示 | 否 | 只保留模板/内容 hash 与来源 ID |

`agent.recommendation_adopted` 太含混，无法区分展示、点击、入队、开始播放、听满阈值和完成。应改为完整漏斗事件。

### 6.3 Outbox 和幂等

业务写入与 `agent_outbox` 必须使用同一个 `bili_radio.sqlite3` 事务。worker 使用 lease 认领，投递到 AMEM 后再标记完成。

必须处理这个崩溃窗口：AMEM 已提交，但 outbox 尚未标记完成。下一次重试会再次投递同一个 `event_id`。当前 AMEM 对重复 event 会触发唯一约束，因此 `MemoryPort` 必须把“相同 event_id 已存在”视为成功，并保证派生 upsert 幂等。

worker 队列需要：

- `worker_id`；
- `lease_until`；
- `available_at`；
- 指数退避；
- 最大尝试次数；
- stale lease 回收；
- dead-letter 状态和人工重放；
- queue lag、失败率和 SQLite busy 指标。

任何 LLM 调用或 7/30/90 日统计都不得发生在 SQLite 写事务内。

## 7. 私人评价与隐私

### 7.1 评价事实模型

建议的 canonical review 记录包含：

- `review_id`；
- `profile_id`；
- `track_id`；
- `rating`；
- `mood_tags` / `scene_tags`；
- `note_ciphertext`；
- `note_nonce` / `key_version`；
- `allow_personalization`；
- `safe_summary`；
- `created_at` / `updated_at` / `deleted_at`。

原文使用成熟库提供的认证加密，例如 AES-GCM；密钥不放在同一数据库中。不要复用自制 XOR 方案，也不要把 AMEM demo vault 当生产加密。

### 7.2 Agent 可见性

默认情况下，Planner 只获得：

- 评分；
- 用户选择的标签；
- 是否为强情感连接；
- 用户明确允许个性化后生成的安全摘要；
- 评价 ID 和 track ID，用于溯源。

原始留言默认不进入 AMEM、prompt、audit 或日志。

对于“这歌是我爸去世那天循环的”这类内容：

1. 原文只进入加密 review store；
2. 默认不交给普通 Planner；
3. 若用户允许个性化，只派生诸如“用户对此曲有强烈情感连接”的受限结构化信号；
4. 用户主动查看原评价时，由鉴权 `ReviewService` 返回给 UI 卡片，不经过 LLM；
5. `approve_review_item` 只用于审批 Agent 推断的候选记忆，不承担原文解密授权。

### 7.3 删除和遗忘

删除评价不能只删列表行。必须同时：

- 写 `track.review_deleted` tombstone；
- 清理或封存原文密文；
- 使派生记忆失效；
- 使推荐和画像不再引用该评价；
- 保证 replay 不会复活已删除内容；
- 审计只保留不含原文的删除证明。

同样，“清空播放历史”必须覆盖 raw playback、聚合表、outbox、AMEM 派生和画像，而不是只删除 `recent`/`playback_recent`。

## 8. 音乐画像与推荐

### 8.1 元数据先于画像

B 站 `owner` 是 UP 主，不等于歌手；视频标题也不一定是规范曲名。当前 Track 模型没有可信的歌手、曲风、乐器和语言字段。

V1 应先建立保守的元数据归一层：

- `canonical_title`；
- `canonical_artist`；
- `genre_tags`；
- `instrument_tags`；
- `language_tags`；
- `metadata_source`；
- `metadata_confidence`。

置信度不足时只能说“标题/标签中多次出现钢琴相关内容”，不能断言用户连续三天听了钢琴曲。没有可信 artist 归一时，也不能断言“一个月没听周杰伦”。

### 8.2 画像快照

画像应由确定性 SQL/规则先生成结构化快照，至少包含：

- 7/30/90 日窗口；
- 有效收听次数和总时长；
- 完成率、快速跳过率；
- 重复收听率和新颖度倾向；
- 常见 UP/可信 artist/标签；
- 时段分布；
- 最近偏好变化；
- `algorithm_version`；
- `sample_size`；
- 每个结论的 `confidence`；
- `source_event_ids` 或可解析的证据范围。

LLM 可以把这些字段改写成自然语言，但不能直接扫描全量播放记录后自由归纳。低样本、矛盾信号和低置信度必须显式降级。

### 8.3 久违歌曲推荐

推荐候选由 SQL 产生，而不是由 AMEM retrieval 产生。基础约束：

- 最后一次有效收听超过阈值，例如 30 天；
- 曲目仍能解析和播放；
- 用户没有明确不喜欢或删除；
- 近期没有连续快速跳过；
- 同一作品/artist 去重；
- 与当前画像至少有一个可解释关联；
- 适当加入探索候选，避免只推荐旧循环。

LLM 的权限限定为：在给定候选中选择、排序、写理由。输出必须带 `track_id`、候选 rank、source IDs 和 recommendation ID，服务端再次校验后才能展示。

## 9. 单 Planner 与工具边界

### 9.1 Planner 不在 AMEM 中

当前 `respond_stream` 只向模型传 system/user messages 并读取文本 token，没有 `tools`、`tool_calls` 或多轮 Tool Loop。需要新增应用层 `MusicAgentService`：

```text
用户消息
  -> 加载会话、画像、AMEM 安全投影和当前播放器状态
  -> 调用支持 Function Calling 的模型
  -> 校验 ToolCall schema / policy / confirmation
  -> ToolExecutor 执行
  -> 将规范化 ToolResult 返回模型
  -> 最多 N 步后输出文本 + UI actions + source IDs
```

必须设置最大步数、单工具超时、总超时、输出上限、幂等键和取消机制。Reflection 是无工具权限的后台 job，不算第二个 Agent。

### 9.2 工具清单

#### 自动允许的读取工具

| 工具 | 作用 |
|---|---|
| `catalog.search_tracks` | 搜索和解析曲目 |
| `player.get_state` | 当前曲目、状态、位置和队列摘要 |
| `library.list_recent` | 查询可信有效收听历史 |
| `library.list_likes` | 查询喜欢曲目 |
| `reviews.list_safe` | 查询评分、标签和安全摘要 |
| `analytics.get_listening_summary` | 获取结构化统计 |
| `profile.get_snapshot` | 获取当前音乐画像 |
| `recommendation.get_candidates` | 获取服务端已约束候选 |
| `memory.explain` | 返回来源 ID 和可展示解释 |

#### 用户本轮明确表达意图后允许的可逆操作

| 工具 | 执行方式 |
|---|---|
| `player.play` | 返回白名单 UI action，由前端 `playerStore` 执行 |
| `player.pause/resume/next` | 返回白名单 UI action |
| `queue.enqueue` | 幂等加入队列 |
| `library.like/unlike` | 写业务库和 outbox |
| `playlist.add_track` | 写业务库和 outbox |

#### 必须二次确认的操作

- 清空或替换整个队列；
- 删除评价；
- 清空历史；
- 遗忘记忆；
- 展示原始私密留言；
- 批量取消喜欢或删除歌单。

Agent 不获得任意 SQL、文件读写、shell 或默认 Web Search 权限。AMEM 自带的通用 file/web tools 不应注册到音乐 Agent。

### 9.3 浏览器播放器控制

Python 后端不能直接控制浏览器内的 `HTMLAudioElement`。播放类工具应返回结构化 UI action，例如 action type、track、idempotency key 和 expiry；前端白名单 dispatcher 校验后调用现有 `playerStore`。

聊天页复用现有全局 PlayerBar。移动端可以让 PlayerBar 进入 compact variant，但不能创建第二个 audio 实例。

### 9.4 MCP 顺序

先实现与传输无关的 domain tool handlers，再让内部 Function Calling 使用同一 handlers。M7 才增加 MCP adapter，并只暴露经过认证、scope 限制和版本化 schema 的安全子集。

## 10. 典型场景的修正版调用链

| 场景 | 推荐调用链 | 对原设想的修正 |
|---|---|---|
| 打开播放器问候 | 读取物化 greeting/profile -> 可选 AMEM projection -> 模板或 LLM 表达 -> 写 greeting impression hash | `project_fast` 不是高可用缓存，必须有应用缓存和 fallback |
| Agent 对话 | `MusicAgentService` Tool Loop -> domain tools -> UI actions -> 流式输出 | `respond_stream` 本身不会 ToolCall |
| 用户写评价 | `ReviewService` 同事务写 review + outbox -> worker 派生结构化信号 | 不直接把原文 `ingest`；查看原文不走 Human Review |
| 每晚画像派生 | worker 查询 player DB -> 写 versioned snapshot + outbox -> AMEM 派生 | 内建 derivation 不认识音乐事件，必须自定义规则 |
| 推荐久违歌曲 | SQL candidate generator -> 画像/安全记忆 -> 规则 rank -> 可选 LLM 重排/解释 | `days_since_last_play` 不由 retrieval 过滤 |
| 派生算法升级 | 备份 -> 新 `amem-shadow.sqlite3` replay -> Eval/一致性比较 -> 原子切换 | runtime snapshot 不是 baseline 备份，禁止原地试跑生产库 |

## 11. 里程碑与任务拆解

以下工作量是单名熟悉代码库的工程师投入，不是日历承诺。M2 与 M3 可以并行；关键路径是 `M0 -> M1 -> M3 -> M4 -> M5`。

### M0：AMEM 接纳审查与契约冻结（3-5 人日）

#### 任务

- M0-01：确认 V1 为单用户自托管，生成稳定 `profile_id`，确定本地会话/访问令牌，记录多用户非目标。
- M0-02：确认上游许可证/授权；固定 commit SHA；决定维护 fork、内部 wheel 或 Git dependency，禁止继续裸拷贝漂移。
- M0-03：建立 `MemoryPort` 接口，业务层不直接依赖 AMEM store/runtime 内部类。
- M0-04：冻结 event envelope、review privacy、tool schema、source provenance 和 deletion 语义。
- M0-05：完成双进程 SQLite 读写、重复 event、worker claim 后 kill、中文检索、敏感评价、delete+replay 六个 spike。
- M0-06：验证 `project_fast` 超时和 DB lock 行为；决定应用级 greeting/profile cache。
- M0-07：建立数据库 migration 机制，停止只在 `init_db()` 中无限追加 DDL。

#### DoD

- 上游来源、版本、许可证和升级策略有书面记录；
- 未授权请求不能读取评价、画像、对话、记忆或执行播放器工具；B 站 Cookie 不作为应用会话；
- 六个 spike 均有可重复测试和结果；
- 所有失败能力形成明确 patch 清单和 owner；
- 证明 AMEM 可被替换而不会重写 Review/Recommendation/Planner 业务层；
- 若授权、幂等、双进程锁或敏感内容测试不过，接入状态保持 HOLD。

### M1：真实事件、Outbox 与独立 Worker（6-9 人日）

#### 任务

- M1-01：前端播放 session 状态机和节流 heartbeat。
- M1-02：补齐 started/paused/resumed/qualified/completed/skipped 上报及 idempotency key。
- M1-03：修正“加载即 recent”和 pause 即 ended 的语义。
- M1-04：在 like、playlist、playback 等领域事务中写 `agent_outbox`。
- M1-05：实现 lease、stale recovery、retry/backoff、DLQ 和人工 replay。
- M1-06：新增独立 `music-agent-worker` 入口和 Compose service，共享持久数据卷。
- M1-07：以固定 event ID 接入 AMEM SQLite bundle，补重复投递成功语义。
- M1-08：增加 worker health、queue lag、attempts、DLQ、SQLite busy 指标。
- M1-09：为现有播放数据提供一次性 backfill 方案，并明确无法重建的字段。

#### DoD

- Flask 和 worker 可按任意顺序重启；
- worker 在 claim 后被强制终止，lease 到期后任务可恢复；
- 相同 event 投递多次只产生一次业务效果和一份有效派生；
- 有效播放、完成、快速跳过的浏览器到数据库 E2E 测试通过；
- 模型、AMEM 或 worker 不可用时，播放器功能保持正常；
- 本地与 Compose 环境都不在 Flask 内启动后台守护线程。

### M2：私人评价闭环（5-8 人日，可与 M3 并行）

#### 任务

- M2-01：review migration、repository、service 和鉴权边界。
- M2-02：评分、标签、可选留言、个性化同意、编辑和删除 API。
- M2-03：使用成熟认证加密保存留言原文，设计 key rotation/version。
- M2-04：播放详情评价区和独立评价列表。
- M2-05：只将评分/标签/获准安全摘要写入 outbox。
- M2-06：实现 review tombstone、派生失效和 replay 防复活。
- M2-07：增加 raw note 不进入 log/audit/prompt/amem 的自动化泄漏测试。

#### DoD

- 无留言也能快速提交评价；
- 重启后只有授权用户能读取原始评价；
- “这歌是我爸去世那天循环的”原文不出现在 AMEM、event、audit、日志和普通 Agent prompt；
- 删除后 UI、推荐、画像和 replay 均不再出现该内容；
- Agent 默认只能调用 `reviews.list_safe`。

### M3：音乐元数据、画像与记忆派生（8-12 人日）

#### 任务

- M3-01：设计 canonical work/artist/tag 模型和置信度。
- M3-02：构建 7/30/90 日确定性统计与画像 snapshot schema。
- M3-03：实现低样本阈值、冲突信号和置信度规则。
- M3-04：实现音乐专用 `DerivationRegistry`，保留真实领域 event kind。
- M3-05：实现用户/画像 scope、source ID 和 rule version。
- M3-06：替换中文 tokenizer，加入结构化 artist/tag/type 过滤。
- M3-07：评估 O(n) JSON record 扫描；为当前规模定义容量上限和迁移阈值。
- M3-08：建立 nightly/incremental profile job 和物化缓存。

#### DoD

- 固定 event fixtures 对应的统计和 snapshot 可重复生成；
- 每个画像结论都有窗口、样本量、置信度、算法版本和来源；
- 低样本不下强结论；
- B 站 owner 不被默认当成 artist；
- 心理、医疗和人格障碍推断被规则阻断；
- 中文“周杰伦”“钢琴”等检索用例通过，且敏感 memory 有 `must_not_select` 测试。

### M4：问候与推荐纵向切片（7-10 人日）

#### 任务

- M4-01：首页 greeting API、缓存、过期策略和确定性 fallback。
- M4-02：久违歌曲 SQL candidate generator。
- M4-03：排除近期快速跳过、明确不喜欢、不可播放和重复作品。
- M4-04：确定性基础 rank；LLM 仅做候选内有限重排和理由生成。
- M4-05：首页推荐卡片、播放/入队动作和“为什么推荐”。
- M4-06：记录 impression、enqueue、play started、qualified、completed、skipped 全漏斗。
- M4-07：通过 recommendation/correlation/caused-by IDs 连接推荐与播放结果。

#### DoD

- “超过 30 天”按有效收听计算，边界测试 100% 通过；
- LLM 不可能输出候选之外的 track ID；
- 无历史、低置信度、LLM 失败和 worker 延迟均有正常 UI；
- 问候和推荐都可展示来源解释；
- 推荐效果可按完整漏斗计算，不再依赖单一 `adopted` 事件。

### M5：单 Planner、Function Calling 与聊天 UI（10-15 人日）

#### 任务

- M5-01：实现 `MusicAgentService` 显式状态机和模型 adapter。
- M5-02：定义 read/write/destructive 工具 schema、scope 和确认策略。
- M5-03：让 ToolExecutor 支持 timeout、output limit、idempotency、trace 和取消。
- M5-04：实现 SSE 流式 chat API、conversation/thread 数据和 retention。
- M5-05：新增 Agent chat view，复用全局 PlayerBar 和 playerStore。
- M5-06：实现后端 `UIAction` 到前端白名单 dispatcher。
- M5-07：加入 prompt injection、越权 tool call、模型乱参、重复 action 和断流恢复测试。
- M5-08：记录 token、first token latency、tool latency、失败类型和 source IDs，不记录私密原文。

#### DoD

- Planner 最大步数、总超时、单工具超时和输出大小受限；
- 写操作幂等，破坏性操作必须确认；
- 模型不能绕过工具层直接写 DB 或 memory；
- 聊天页只有一套播放器状态和 audio 实例；
- 模型或工具故障不影响播放，且 UI 给出可恢复状态；
- 所有事实性回答携带可追溯 source IDs。

### M6：治理、解释、遗忘与安全回放（7-10 人日）

#### 任务

- M6-01：持久化 Human Review store 和待审 UI。
- M6-02：记忆中心：查看、解释、纠正、禁止用于个性化、遗忘。
- M6-03：音乐专用风险评分器，默认阻断心理/医疗/家庭敏感推断。
- M6-04：按墙钟和事件类型实现 retention，而不是只按 sequence age。
- M6-05：建立删除传播、tombstone 和 audit proof。
- M6-06：真实 SQLite 备份、restore drill 和 shadow replay。
- M6-07：算法版本对比和切换/回退 runbook。

#### DoD

- 用户能回答“为什么 Agent 说我喜欢钢琴曲”；
- 用户纠正后，新画像和推荐使用纠正结果；
- 敏感候选默认不进入 MemoryStore；
- 遗忘后 replay 不会复活；
- 影子库 replay、Eval、切换和备份恢复演练通过。

### M7：MCP 与生产发布门禁（8-12 人日）

#### 任务

- M7-01：为同一 domain tool handlers 增加 MCP adapter。
- M7-02：MCP auth、profile scope、schema version、速率限制和审计。
- M7-03：默认只开放安全读取工具和有限播放控制。
- M7-04：CI 接入 derivation/retrieval/recommendation/safety/ops Eval。
- M7-05：双进程 SQLite 锁、长历史、worker crash 和 LLM latency 压测。
- M7-06：生产 WSGI、healthcheck、backup、migration、secret 和 rollback runbook。
- M7-07：明确 SQLite 容量和并发退出条件；超过条件迁移数据库/队列，不继续堆锁补丁。

#### DoD

- MCP 与内部 Function Calling 通过同一 contract tests；
- MCP 默认不暴露 raw review、删除、任意文件、SQL 或 Web Search；
- 安全、隐私、队列、检索和推荐 Eval 是发布硬门禁；
- worker、Flask、LLM 和数据库故障演练有可验证恢复结果；
- 发布包使用固定 AMEM 版本/commit，能复现构建。

## 12. Eval 体系

### 12.1 当前内置格式

AMEM 官方样例实际格式是：

```yaml
cases:
  - id: refund_strategy
    agent: support_agent
    session_id: support-001
    query: refund status
    expected_memory_ids:
      - strategy:support-001:support_agent:refund_status
```

来源：[examples/evals/retrieval_cases.yml](https://raw.githubusercontent.com/ourhome-macro/amem-agent-memory-framework/main/examples/evals/retrieval_cases.yml)。

它只检查 expected IDs 是否包含在 selected IDs 中。用户草案中的 `expect_memories.kind`、`tags`、`filter` 和 `recency_boost` 当前都不受支持，CLI 也只是打印结果，不足以直接作为 CI 失败门禁。

### 12.2 音乐项目需要的五套 Eval

| 套件 | 目标 | 核心指标 |
|---|---|---|
| Event contract | 确保事实可靠 | 丢失率、重复效果、顺序、边界语义 |
| Derivation golden | 确保画像可复现 | snapshot equality、confidence、source coverage |
| Retrieval | 确保召回正确且不泄密 | Recall@K、MRR、freshness、must-not-select |
| Recommendation | 确保候选和理由受约束 | gap days、排除规则、可播放率、多样性、grounding |
| Safety/Ops | 确保生产行为 | 越权、原文泄漏、worker crash、delete+replay、SQLite busy |

问候还需要单独的 truthfulness 测试：所有数字、日期、artist/tag 和趋势必须能从 source facts 重新计算。

### 12.3 建议的扩展方向

音乐 Eval v2 可以支持：

- seed events / fixtures；
- `expected_memory_types/tags/source_ids`；
- `must_not_select`；
- ranking 指标和阈值；
- recommendation candidate assertions；
- profile JSON assertions；
- privacy assertions；
- worker failure scripts。

`days_since_last_play > 30` 应放在 Recommendation Eval，不应伪装成通用 memory retrieval filter。

## 13. 发布指标和硬门槛

### 13.1 数据正确性

- 服务端接收的有效播放 session 无重复业务效果；
- worker crash/restart 测试中事件最终零丢失；
- 每个画像结论 source coverage 为 100%；
- 删除后 replay 复活率为 0。

### 13.2 隐私与安全

- raw private note 出现在普通 prompt/audit/log/amem 的次数为 0；
- 跨 profile 读取成功次数为 0；
- destructive tool 未确认执行次数为 0；
- 敏感心理/医疗推断默认进入用户上下文的次数为 0。

### 13.3 体验与可靠性

- 无 LLM 时播放器、评价、画像统计和确定性推荐仍可用；
- 首页问候命中物化缓存时不依赖 AMEM 全库检索；
- 模型首 token、完整问候、tool call 和 recommendation 各自有独立 SLO；
- queue lag、DLQ、worker heartbeat 和 SQLite busy 可观测。

### 13.4 推荐质量

V1 不预设虚假的 adoption 目标。先完整记录 impression 到实际收听结果的漏斗，再建立基线。发布前的硬指标应是候选正确率、可播放率、事实约束和安全；采用率、完成率和跳过率用于后续迭代。

## 14. 建议的首个纵向切片

不要先做完整聊天。首个可验证版本按以下顺序交付：

1. 真实 playback event E2E；
2. 独立 worker + outbox + crash recovery；
3. 评价评分/标签/可选加密留言；
4. 30 日结构化音乐画像；
5. 首页一句有来源的问候；
6. 两首久违歌曲推荐及完整反馈漏斗；
7. “为什么推荐”解释。

这个切片不依赖 Function Calling 或 MCP，已经可以验证用户是否真的需要“被音乐记住”。只有这个闭环的数据正确、隐私可控且用户有持续使用意愿，才进入 M5 聊天 Planner。

## 15. 最终决策摘要

1. 保留“唯一 Planner”，但把 Planner 放在应用层，不误认为 AMEM 已提供。
2. 保留长期 Memory、异步 Reflection、事件流、私人评价、画像和推荐。
3. worker 从 M1 起就是独立 Compose 进程，删除 Flask 守护线程过渡方案。
4. raw facts 留在 player DB，AMEM 只存可重建的派生记忆。
5. 私人评价原文由应用层加密和鉴权；AMEM 只接收最小化结构化信号。
6. 久违歌曲由 SQL 计算，LLM 只做受约束表达。
7. `snapshot()` 不用于回滚；算法升级使用备份 + shadow replay + Eval + 切换。
8. MCP 后置到 M7，复用同一领域工具，不另起一套实现。
9. V1 明确为单用户自托管；公网多用户必须先完成完整租户安全改造。
10. AMEM 在 M0 通过授权、幂等、SQLite、中文、隐私和 replay 验证后才进入 ACCEPT 状态。

## 16. 参考

- [AMEM GitHub 仓库](https://github.com/ourhome-macro/amem-agent-memory-framework)
- [AMEM 官方 Retrieval Eval 样例](https://raw.githubusercontent.com/ourhome-macro/amem-agent-memory-framework/main/examples/evals/retrieval_cases.yml)
- `agent/agent_memory_runtime/runtime.py`
- `agent/agent_memory_runtime/memory/stores/sqlite.py`
- `agent/agent_memory_runtime/governance/queue/sqlite.py`
- `agent/agent_memory_runtime/governance/pii/vault.py`
- `agent/agent_memory_runtime/governance/review/queue.py`
- `agent/agent_memory_runtime/memory/retrieval/scoring.py`
- `py-radio/database.py`
- `py-radio/playback_service.py`
- `bilibili-player/src/stores/playerStore.ts`
