# AMEM 优先加固决策

- 日期：2026-07-21
- 决策：先加固 AMEM，再接音乐陪伴 Agent；但不把 AMEM 扩成完整 Agent 框架
- 范围：架构边界和实施顺序，不涉及代码修改

## 一句话结论

先用 1-2 个迭代把 AMEM 做成可靠、可扩展、可发布的记忆内核，发布固定版本后立即接入播放器。不要等 AMEM “什么都有了”才开始业务集成，也不要把音乐规则、推荐算法或 Planner 塞进 AMEM。

## AMEM 应该负责

1. 事件、记忆、来源和 tombstone 的通用领域模型；
2. 可插拔 Derivation、Retrieval、Tokenizer、Scorer 和 Filter；
3. SQLite 持久化、事务、幂等和 migration；
4. 有 lease、超时回收、重试和 DLQ 的可靠 worker queue；
5. `tenant_id/user_id` 与 `agent_id` 分离的访问控制；
6. 持久 Human Review store；
7. PII/Vault 接口和生产级可替换实现，不负责猜测所有语义敏感内容；
8. export、真实备份/恢复、shadow replay 和一致性检查；
9. 可扩展 Eval case、Recall@K/MRR、安全断言和失败退出码；
10. 审计、指标和稳定的 public API。

## AMEM 不应该负责

1. `track.played` 等音乐领域规则；
2. B 站曲目、artist、曲风和标签归一；
3. 久违歌曲 SQL、推荐排序和推荐漏斗；
4. 私人评价 UI 和音乐评价字段；
5. 播放器控制工具；
6. 音乐问候 Prompt；
7. 完整 Planner / Function Calling 状态机；
8. 音乐聊天界面。

完整 Planner 属于播放器应用层。若以后确实需要通用 Planner，可以另建可选的 `amem-agent` 或 `integrations/planner` 包，不能让 memory core 反向依赖 LLM、MCP 或业务工具。

## 推荐的包边界

```text
amem-core
  domain / stores / queue / derivation / retrieval
  access / governance / audit / replay / evals

amem-integrations（可选）
  openai / cli / mcp adapter

bilibili-radio
  MusicAgentService / ReviewService
  playback events / music profile / recommendation
  player tools / prompts / Vue UI
```

## AMEM 第一批必须完成的 P0

1. 补 LICENSE、版本、changelog、CI 和可安装 package；
2. 固定 public API，并给 breaking change 建版本策略；
3. 事件幂等：重复 `event_id` 返回相同结果，不重复派生；
4. SQLite 增加 `busy_timeout`、读写事务区分和双进程并发测试；
5. Queue 增加 `worker_id`、`lease_until`、stale recovery、backoff 和 DLQ；
6. Human Review 改为持久 store 接口；
7. Access Principal 增加用户/租户边界，不能只靠 `agent_id`；
8. Retrieval 提供 tokenizer/scorer/filter 插件点，支持中文和结构化字段；
9. snapshot 明确改名或补真实 export/restore，避免被误当备份；
10. replay 支持 shadow store，不原地清空生产 memory；
11. Eval 支持可扩展断言、排名指标、敏感 `must_not_select` 和非零失败退出；
12. 删除/tombstone 在 replay 后仍然有效。

## 可以后置的能力

- 向量数据库；
- 分布式 queue；
- 多 worker 水平扩展；
- 通用 Planner；
- MCP server；
- 语义 PII 分类模型；
- Web/File 等通用工具；
- 复杂管理后台。

这些能力没有当前业务验证，提前实现容易把 AMEM 做成边界模糊的大框架。

## 实施顺序

### A0：冻结定位和接口

写清 AMEM 是“事件源记忆运行时”，确定 public interfaces、兼容策略和接纳测试。

### A1：可靠存储和 worker

先完成幂等、SQLite 并发、lease/recovery、DLQ、migration 和 crash tests。这是播放器独立 worker 的硬依赖。

### A2：隔离、检索和治理

完成 tenant principal、持久 review、可插拔 tokenizer/scorer/filter、tombstone 和安全 Eval。

### A3：回放和发布

完成 export/restore、shadow replay、CI，发布固定版本，例如 `v0.2.0`，播放器按 tag/commit 使用。

### A4：立即回到播放器

先接真实 playback events、outbox 和独立 worker。用音乐业务暴露下一批真实缺口，再反向改进 AMEM，避免闭门造通用框架。

## AMEM 加固完成的判断

以下测试全部通过才进入播放器正式接入：

- Flask 和 worker 任意重启，事件最终零丢失；
- worker claim 后被杀，lease 到期可恢复；
- 同一 event 重复投递不重复派生；
- Flask 读取与 worker 写入并发时没有永久锁和未处理 busy；
- 两个 tenant 使用同一 agent ID 时不能互相检索；
- 中文 query 能按插件 tokenizer 正常召回；
- sensitive memory 能被 `must_not_select` Eval 阻止；
- 删除后 replay 不复活；
- shadow replay 不修改生产库；
- package 可由干净环境按固定版本复现安装。

## 最终建议

先改 AMEM 是对的，但目标不是“更全面”，而是“边界更稳、扩展点更清楚、失败可恢复”。建议给 AMEM 加固设置明确时间盒；完成 P0 并发布版本后立刻回到音乐播放器，不继续无限扩框架。

