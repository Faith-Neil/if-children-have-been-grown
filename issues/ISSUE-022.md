为什么有这个文件：登记 APP-M2-T124 还不能改模型输入的原因，以及已经提交复核的接口草案。

它解决什么问题：避免在片段发布和证据抽屉还不存在时改模型输入，也避免把尚未实现的大纲接口写成已经接通。

# ISSUE-022：T124 依赖未满足，大纲契约草案待复核

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-022 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | outline-contract-draft-3 |
| 关联 Task | [APP-M2-T124](../docs/tasks/APP-M2.md#app-m2-t124) |
| 关联 PR | 未创建 |
| 本地验收 | 契约形状已核对。运行时未实现，模型输入未改。见 [记录](../docs/testing/2026-10-12-t124-dependencies.md) |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [APP-M2-T124 交付](../docs/delivery/APP-M2-T124.md) |
| 代码 / 流程解释 | [契约草案说明](../docs/code/APP-M2-T124.md) |
| 验证记录 | [2026-10-12 依赖核对](../docs/testing/2026-10-12-t124-dependencies.md) |

## 现象与证据

项目经理要求完成 T124 的剩余部分：把评分行、片段写作计划和逐得分要点小标题送入模型输入，并使用替身模型和内存检索。开工前按 WORKFLOW 核对任务卡依赖。没有接口或其他必要输入时不能标 ready。

本卡列出的依赖是 APP-M1-T15、APP-M2-T078、APP-M2-T114。任务卡还要求开工前在 OpenAPI 写明 `getOutlinePlan`、`confirmOutlinePlan`、`startGeneration`。复用项 APP-M1-T12、APP-M1-T13 已本地 done，不是缺口。

适用差异是 REF-08，不是 REF-07。REF-08 登记的是整章 `input_snapshot` / `source_scope`，不是逐段证据或检索快照，见 `docs/decisions/icg-reference-deviations.md` 第 17 行。REF-07 是经理批量确认，见同文件第 16 行；T15 已在代码里按章确认，本轮剩余范围不靠它解除。

## 依赖核对

| 依赖 | 是否满足 ready | 证据 |
|---|---|---|
| APP-M1-T15 | 满足。逐章确认已在代码里 | 看板 `docs/TASK_BOARD.md` 第 151 行状态 done。确认函数 `backend/bid-core/icg_demo/workflow.py` 第 637–672 行。当前性判断 `backend/bid-core/icg_demo/generation_context.py` 第 83–91 行 |
| APP-M2-T078 | 仍不满足 T124 开工。内存发布已提交 in-review，未标 done，页面未做 | 任务卡 `docs/tasks/APP-M2.md` 的 T078 为 in-review。看板同一行。`kb_sync_status` 在片段接口上。`generation_context.py` 仍不读已发布片段 |
| APP-M2-T114 | 不满足。EvidenceDrawer 仍是 planned | 任务卡 `docs/tasks/APP-M2.md` 第 1736 行。看板 `docs/TASK_BOARD.md` 第 266 行。`frontend/web` 没有 `EvidenceDrawer`。矩阵只在 `frontend/web/src/ProjectPages.tsx` 第 129 行把 `evidence_ids` 写回条款 |
| 契约入口 | 草案已写入，待后台复核，运行时仍没有 | `spec/openapi/demo-v1.json` 第 11203、11408、11690 行是 `getOutlinePlan`、`confirmOutlinePlan`、`startGeneration`，状态为 draft, pending backend review。第 6679 行的 `generate_api_v1_projects__project_id__generate_post` 仍是唯一已实现的生成入口 |

模型输入仍是整章。`generation_context.py` 第 194 行 `scope` 为 `whole_chapter`，第 203 行 `source_scope` 同值，第 213–217 行只拼章节标题、写作要点和字数目标。`workflow_schemas.py` 第 279 行和第 302 行把 `source_scope` 固定为 `whole_chapter`。这里没有评分行、片段计划或逐要点小标题。

内存检索（ISSUE-016 / AI-03）不在本卡依赖列表里，也不提供已发布片段或评分行证据版本，不能代替 T078 或 T114。

## 契约草案

operationId 已写入 `spec/openapi/demo-v1.json`，契约状态为 **draft, pending backend review**。本 Issue 为 in-review。后台已复核 `16e0b9e` 并接受，草案仍无运行时。APP-M2-T124 仍是 blocked：T078 的内存发布为 in-review 但未标 done，T114 仍 planned，模型输入仍是整章。

| 操作 | 路径 | 约定 |
|---|---|---|
| `getOutlinePlan` | `GET /api/v1/projects/{project_id}/outline/plan` | 评分行、片段写作计划、逐得分要点小标题。成功响应带 ETag，值是整份计划的 revision。没有 fingerprint 字段 |
| `confirmOutlinePlan` | `POST /api/v1/projects/{project_id}/outline/plan/confirm` | If-Match 核对整份计划的 revision，不符为 409 `VERSION_CONFLICT`。章或来源变化按该章 `expected_revision` 返回 409 `PLAN_STALE`。章节被锁为 423 `LOCK_HELD`，锁丢失为 423 `LOCK_LOST` |
| `startGeneration` | `POST /api/v1/projects/{project_id}/generation/start` | 长任务。If-Match 核对已确认计划的 revision。返回 202，`Location` 指向 `GET /api/v1/jobs/{job_id}`。同一幂等键重放同一个 job id、同一个 Location 和 202。任务开始时对模型配置做快照。另列 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 与 503 `SECRET_KEY_UNAVAILABLE`，只引用 ISSUE-024，不在本文件定义。503 不是瞬时故障，不自动重试，与 `MODEL_UNAVAILABLE` 相同。423 与确认接口相同 |
| `getJob` | `GET /api/v1/jobs/{job_id}` | 独立的 `JobStatus`，含 `recoverable`。不属于本公司或本项目返回 404 `NOT_FOUND`。不列 403 |
| `streamJobEvents` | `GET /api/v1/jobs/{job_id}/events` | 未来的 SSE 草案，支持 `Last-Event-ID`。事件 id 为 `<job_id>:<seq>`。不列 403 |
| `cancelJob` | `POST /api/v1/jobs/{job_id}/cancel` | 带 `Idempotency-Key`。状态可变为 `cancelled`。成功响应不强制带 Location |

`JobStatus.status` 为 `queued`、`running`、`completed`、`failed`、`cancelled`，并有自己的 `recoverable` 布尔字段。已实现 `Job.recoverable` 仍是 `const false`。`JobEvent.type` 为 `job.model_call`、`job.status_changed`、`job.progress`、`job.completed`、`job.failed`、`job.cancelled`。后三类的 payload 由 BE-M0-T06 实现。`job.model_call` 的 `provider` 与 `model` 取自任务开始时的配置快照。403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 与 503 `SECRET_KEY_UNAVAILABLE` 只引用 ISSUE-024 的冻结错误码表，不写入本文件的枚举。503 不是瞬时故障，客户端不要自动重试，与 `MODEL_UNAVAILABLE` 相同。GET 不列 413、423、428；`getJob` 与 SSE 不列 403，也不列 409；502 与 503 只列在 `startGeneration`。`confirmOutlinePlan` 与 `startGeneration` 列 423。

旧的 `POST /api/v1/projects/{project_id}/plan`、`POST /api/v1/projects/{project_id}/generate`、`POST /api/v1/projects/{project_id}/chapters/{chapter_id}/plan/confirm` 在说明里标了 `deprecated: true`，与新入口并存。运行时还没标出这个标记。前端切换之后由后续 Issue 删除。草案路径仍带 `x-contract-status: draft, pending backend review`，对比运行中的接口时按这个标记滤掉。

## T078 计划

内存实现已提交复查，任务为 in-review，未标 done。新状态在独立内存存储，不改 `Repository.read` 与 `Repository.transaction`。文件、路径和字段见 [T078 内存方案](../docs/governance/ISSUE-022-t078-plan.md)。两条 GET 返回 ETag，供随后的 If-Match 使用。被拦截的发布仍算成功，必须记下幂等回执。页面未做。T124 仍 blocked。

## 影响与分流

- 影响范围：ISSUE-022 为 in-review，复核对象是契约草案。T124 保持 blocked，不进入 ready 或 in-progress。不改模型输入、检索服务、页面或仓库读写。
- 不涉及：REF-07 的确认权限、ISSUE-010 的选型。ISSUE-018 的 MySQL 8 方案已批准，Issue 为 in-progress；T078 计划不改 `Repository.read` 与 `Repository.transaction`，以免挡在第 7 节的按聚合拆分前面。
- 解除条件：后台接受草案并在运行时导出这三个 operationId，T078 提供可引用的已发布片段版本，T114 提供评分行上的当前证据版本。满足后再把 T124 从 blocked 改回可开工状态。开发者不把本 Issue 标 closed，也不把 T124 标 done。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| APP-M2-T124 | 评分行、片段计划、逐要点小标题进入模型输入 | 本轮只增加 OpenAPI 草案和契约测试。模型输入未改 | AC-01～AC-02 | blocked |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 依赖满足后，得分要点小标题、证据版本/片段计划和字数事实要点进入实际模型输入 | 未执行。T078 未标 done，T114 仍 planned。契约只是草案 |
| AC-02 | 确认继续复用 T15，不把 REF-07 当成剩余缺口 | 已核对。T15 的按章确认在 `workflow.py` 第 637–672 行。剩余缺口对应 REF-08 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。没有改需求或验收口径 | `docs/PRD.md` 未改 | outline-contract-draft-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| ROADMAP | 无任务增减。rebase 后与看板同为 356 项：23 done、6 in-review、7 in-progress、266 planned、50 blocked、4 ready。正文补一句草案待复核 | `docs/ROADMAP.md` 当前计数段 | outline-contract-draft-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。草案和 T078 计划都未实现，不改架构正文 | `docs/ARCHITECTURE.md` 未改。整章 `source_scope` 句子保持 | outline-contract-draft-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。T124 仍 blocked；Issue 改为 in-review。任务卡写明草案未实现 | `docs/TASK_BOARD.md`、`docs/tasks/APP-M2.md` | outline-contract-draft-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| PROJECT_STATUS | 有影响。进度写明契约待复核，T124 仍未实现 | `docs/PROJECT_STATUS.md` | outline-contract-draft-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| DOCUMENT_INDEX | 有影响。更新本 Issue 条目，并登记 T078 计划 | `docs/DOCUMENT_INDEX.md` | outline-contract-draft-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| PROJECT_BRIEF | 无任务增减。排期句补上草案待复核，计数与看板同为 356 项 | `docs/PROJECT_BRIEF.md` 排期行 | outline-contract-draft-1 / ISSUE-022 / 2026-10-12 | 已核对 |

治理块保持 g1.1 / 2026-10-11 / ISSUE-007。`docs/reference/` 未改。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | t124-blocked-1 / blocked | 只登记阻塞。T15 已具备；T078、T114 和三个具名 operationId 当时不具备。未改产品代码 | [依赖核对](../docs/testing/2026-10-12-t124-dependencies.md) |
| 2026-10-12 | outline-contract-draft-1 / in-review | 写入三个 operationId 与 `getJob` 的草案。`startGeneration` 为 202，对齐尚未实现的 BE-M0-T06。T078 只留下独立存储计划。未改运行时 | [契约核对](../docs/testing/2026-10-12-t124-dependencies.md) |
| 2026-10-12 | outline-contract-draft-2 / in-review | 按后台对 `16e0b9e` 的复核改草案：独立 `JobStatus`、SSE 与 `cancelJob`、按操作列出错误、ETag 与整份计划版本。T078 计划改为独立前缀。仍无运行时 | [契约核对](../docs/testing/2026-10-12-t124-dependencies.md) |
| 2026-10-12 | outline-contract-draft-3 / in-review | 按对 `046f8e5` / `fe9582c` 的复审补草案：快照与两个引用码、423、事件 type 与 payload、`recoverable`、取消响应不强制 Location、查询与 SSE 去掉 403。503 `SECRET_KEY_UNAVAILABLE` 不自动重试。仍无运行时。不改任务计数 | [契约核对](../docs/testing/2026-10-12-t124-dependencies.md) |
| 2026-10-12 | t078-plan-etag-receipt / in-review | 只补方案两句：GET 返回 ETag；被拦截的发布仍算成功并记下幂等回执。不写代码。T078 仍 planned | [T078 内存方案](../docs/governance/ISSUE-022-t078-plan.md) |
| 2026-10-12 | t078-memory-1 / in-review | 按方案实现进程内片段发布。T078 改为 in-review，未标 done。T124 仍 blocked。不改三份基线的任务计数 | [交付](../docs/delivery/APP-M2-T078.md) |

## 本地验收与后续合入发布

- 本地验收结论与日期：2026-10-12 只接受契约形状。实现验收未执行。
- 未覆盖：评分行、片段计划和逐要点小标题都没有进入模型输入。新路由没有运行时。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。只有依赖解除并且项目经理在 QA 签署后，才能把 T124 标为 done。
