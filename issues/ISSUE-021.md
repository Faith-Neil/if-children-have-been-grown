为什么有这个文件：把旧 `/api` 错误体和幂等语义的后续工作单独登记，避免和 MySQL 方案混在一次实施里。

它解决什么问题：明确这项工作已经排队，但本轮不改旧路由。

# ISSUE-021：旧接口统一错误体与幂等

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-021 |
| 类型 | change |
| 优先级 | P2 |
| 状态 | blocked |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | queue-1 |
| 关联 Task | [BE-M0-T09](../docs/tasks/BE-M0.md#be-m0-t09) |
| 关联 PR | 未创建 |
| 本地验收 | 未执行 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 尚未建立。任务为 planned，交付路径留在任务卡，文件未创建 |
| 代码 / 流程解释 | 无。本轮不改代码 |
| 验证记录 | 未执行 |

项目经理要求本项按 planned 排队。Issue 看板的状态只有 new、triaged、ready、in-progress、in-review、closed、blocked，没有 planned。因此 Issue 记为 blocked，任务卡记为 planned。解除 blocked 的条件是 ISSUE-018 的方案被接受，并且项目经理另行批准开工。

## 现象与证据

`/api/v1` 的错误体是 `{code, message, details, traceId}`，并有 24 小时幂等回执。旧 `/api` 章节建议等路由仍返回 `{error: {code, message}, request_id}`，幂等字段仍可能来自正文。ISSUE-005 明确本轮不改这些旧路由。

QA 在 `200a105` 的 E2E-D5 记录：`product_page` 只用小写比较 `api` 和 `api/`。`/API/...` 这类大写或混合大小写路径因此返回页面壳，而不是 JSON 404。见[签署记录](../docs/testing/2026-10-12-e2e-t001-signoff.md)。将来的兜底要把 `/api` 前缀按大小写不敏感处理，使 `/API`、`/Api/v1/...` 与小写 `/api` 一样返回 JSON 404。本轮不改 `main.py`，也不加测试。

## 影响与分流

- 将来影响旧 `/api` 的错误 JSON、幂等入口，以及页面兜底对 `/api` 前缀的大小写判断。不改变已确认的小写 `/api/v1` 行为。
- 本次只登记，不改 `main.py`、错误处理或测试。E2E-D5 不在本轮修复。
- 排在 ISSUE-018 之后。不依赖向量库决定。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T09 | 旧 `/api` 改用统一错误体，统一幂等语义，并把页面兜底的 `/api` 前缀改为大小写不敏感 | 尚未开工，预计 `backend/bid-core/icg_demo/main.py` 与对应测试 | AC-01、AC-02 | planned |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 旧 `/api` 错误体与 `/api/v1` 一致，幂等语义一致，并有回归测试 | 未执行。本轮不实施 |
| AC-02 | `/API`、`/Api/...` 等大小写变体返回 JSON 404，不返回页面壳。依据 QA `200a105` 的 E2E-D5 | 未执行。本轮不实施 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。未开工 | 不改 | queue-1 / ISSUE-021 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。未开工 | 不改 | queue-1 / ISSUE-021 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。未开工 | 不改 | queue-1 / ISSUE-021 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。新增 planned 卡 BE-M0-T09 | `docs/TASK_BOARD.md` | queue-1 / ISSUE-021 / 2026-10-12 | 已改 |
| PROJECT_STATUS | 有影响。进度计数包含这张 planned 卡 | `docs/PROJECT_STATUS.md` | queue-1 / ISSUE-021 / 2026-10-12 | 已改 |
| DOCUMENT_INDEX | 有影响。登记本 Issue | `docs/DOCUMENT_INDEX.md` | queue-1 / ISSUE-021 / 2026-10-12 | 已改 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | queue-1 / blocked | 已登记并排队。任务 planned。不实施 | 本文件 |

## 本地验收与后续合入发布

- 未验收，未合入，未发布。
- 开工前先接受 ISSUE-018，再由项目经理把本 Issue 从 blocked 改到可实施状态。
