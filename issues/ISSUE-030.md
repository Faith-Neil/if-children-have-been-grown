为什么有这个文件：记下契约 N7 要求客户端不要自动重试 503 `SECRET_KEY_UNAVAILABLE`。

它解决什么问题：避免密钥不可用被当成瞬时 503，连发三次同一请求。

# ISSUE-030：503 SECRET_KEY_UNAVAILABLE 不自动重试

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-030 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | retry-n7-1 |
| 关联 Task | APP-M2-T002（保持 done）；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)，待合入。本轮不新建 PR |
| 本地验收 | 未由 QA 签署。请求层单测已通过，见 [验证](../docs/testing/2026-10-12-issue-030-secret-key-retry.md) |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [ISSUE-030 交付](../docs/delivery/ISSUE-030.md) |
| 代码 / 流程解释 | [ISSUE-030 代码解释](../docs/code/ISSUE-030.md) |
| 验证记录 | [2026-10-12 密钥不可用重试](../docs/testing/2026-10-12-issue-030-secret-key-retry.md) |

## 现象与证据

冻结契约 `73fde1e` 的 `info.description` 与 `Idempotency-Key` 说明写明：`502 MODEL_UNAVAILABLE` 与 `503 SECRET_KEY_UNAVAILABLE` 不是瞬时故障，客户端不要自动重试，后端不发送 `Retry-After`。`frontend/web/src/api.ts` 的 `canRetryStatus` 对每一个 503 都返回 true，因此带统一错误体 `SECRET_KEY_UNAVAILABLE` 的 503 会再发两次。`MODEL_UNAVAILABLE` 的 502 已经只发一次。

签署记录曾建议把对比度观察项登记为 ISSUE-030，该号当时没有建档。本变更使用 `issues/index.md` 上的下一个空号。

## 影响与分流

- 影响范围：`frontend/web/src/api.ts` 的 `canRetryStatus`。有幂等键的写入和 GET 都走这一处。
- 不改 `backend/`、`tests/backend/`、`spec/openapi/` 与 `docs/reference/`。契约文本已经冻结，本轮只让客户端跟上 N7。
- 不新增依赖。APP-M2-T002 保持 done，不把本 Issue 标成 closed。
- 普通 503（例如 `UI_NOT_READY`）和没有统一错误体的 502 仍重试。409、422、423、428、401、500 仍不重试。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| APP-M2-T002 | 503 `SECRET_KEY_UNAVAILABLE` 只发一次，与 502 `MODEL_UNAVAILABLE` 相同 | `frontend/web/src/api.ts` | AC-01～AC-03 | done |

Task 详情不改状态。交付、验证和代码解释回链本 Issue。

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 502 `MODEL_UNAVAILABLE` 与 503 `SECRET_KEY_UNAVAILABLE` 各只发送一次，并带出追踪号 | 通过；[验证](../docs/testing/2026-10-12-issue-030-secret-key-retry.md) |
| AC-02 | 普通 503 与裸 502 仍重试到成功或满 3 次 | 通过；同一验证 |
| AC-03 | 不改后台、不改冻结 JSON、不把卡片标成新的 done | 通过；本提交只改前端请求层和说明 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。里程碑快照不记录这一条重试例外 | `docs/PRD.md` | retry-n7-1 / ISSUE-030 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。阶段和门禁未变 | `docs/ROADMAP.md` | 同上 | 已核对 |
| ARCHITECTURE | 无影响。模块边界未变，判断在已有请求层 | `docs/ARCHITECTURE.md` | 同上 | 已核对 |
| TASK_BOARD | 无影响。不改任务状态，T002 仍为 done | `docs/TASK_BOARD.md` | 同上 | 已核对 |
| PROJECT_STATUS | 有影响。进度里的重试句补上 503 `SECRET_KEY_UNAVAILABLE` | `docs/PROJECT_STATUS.md` | 同上 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、交付、代码说明、验证和同步表 | `docs/DOCUMENT_INDEX.md` | 同上 | 已核对 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | retry-n7-1 / in-review | 客户端不再重试该 503。等待 QA。不标 closed | [验证](../docs/testing/2026-10-12-issue-030-secret-key-retry.md) |

## 本地验收与后续合入发布

- 本地验收结论与日期：请求层单测于 2026-10-12 通过，QA 尚未签署。
- 验证方式、通过及失败项、未覆盖范围：节点测试替换了 `fetch`，没有打到真实后台。
- 六份基线同步与互链复核：见上表与 [同步](../docs/governance/ISSUE-030-sync.md)。
- PR 状态：未新建。PR #3 仍待合入。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
