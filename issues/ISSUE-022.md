为什么有这个文件：登记 APP-M2-T124 剩余范围不能开工的原因。

它解决什么问题：避免在片段发布和证据抽屉还不存在时，把评分行、片段计划和得分要点小标题写进模型输入。

# ISSUE-022：T124 因依赖未满足而阻塞

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-022 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | blocked |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | t124-blocked-1 |
| 关联 Task | [APP-M2-T124](../docs/tasks/APP-M2.md#app-m2-t124) |
| 关联 PR | 未创建 |
| 本地验收 | 未执行。2026-10-12 只核对依赖，没有改产品代码 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [APP-M2-T124 交付](../docs/delivery/APP-M2-T124.md) |
| 代码 / 流程解释 | [无代码说明](../docs/code/APP-M2-T124.md) |
| 验证记录 | [2026-10-12 依赖核对](../docs/testing/2026-10-12-t124-dependencies.md) |

## 现象与证据

项目经理要求完成 T124 的剩余部分：把评分行、片段写作计划和逐得分要点小标题送入模型输入，并使用替身模型和内存检索。开工前按 WORKFLOW 核对任务卡依赖。没有接口或其他必要输入时不能标 ready。

本卡列出的依赖是 APP-M1-T15、APP-M2-T078、APP-M2-T114。任务卡还要求开工前在 OpenAPI 写明 `getOutlinePlan`、`confirmOutlinePlan`、`startGeneration`。复用项 APP-M1-T12、APP-M1-T13 已本地 done，不是缺口。

适用差异是 REF-08，不是 REF-07。REF-08 登记的是整章 `input_snapshot` / `source_scope`，不是逐段证据或检索快照，见 `docs/decisions/icg-reference-deviations.md` 第 17 行。REF-07 是经理批量确认，见同文件第 16 行；T15 已在代码里按章确认，本轮剩余范围不靠它解除。

## 依赖核对

| 依赖 | 是否满足 ready | 证据 |
|---|---|---|
| APP-M1-T15 | 满足。逐章确认已在代码里 | 看板 `docs/TASK_BOARD.md` 第 151 行状态 done。确认函数 `backend/bid-core/icg_demo/workflow.py` 第 637–672 行。当前性判断 `backend/bid-core/icg_demo/generation_context.py` 第 83–91 行 |
| APP-M2-T078 | 不满足。片段版本对比与发布仍是 planned | 任务卡 `docs/tasks/APP-M2.md` 第 1193 行。看板 `docs/TASK_BOARD.md` 第 230 行。`backend/bid-core` 与 `frontend/web` 没有 `kb_sync_status`。`workflow_schemas.py` 第 13 行的 `snippet` 只是资料类型，不是已发布片段版本 |
| APP-M2-T114 | 不满足。EvidenceDrawer 仍是 planned | 任务卡 `docs/tasks/APP-M2.md` 第 1736 行。看板 `docs/TASK_BOARD.md` 第 266 行。`frontend/web` 没有 `EvidenceDrawer`。矩阵只在 `frontend/web/src/ProjectPages.tsx` 第 129 行把 `evidence_ids` 写回条款 |
| 契约入口 | 不满足。三个具名 operationId 不在约定里 | `spec/openapi/demo-v1.json` 没有 `getOutlinePlan`、`confirmOutlinePlan`、`startGeneration`。现有生成入口是第 6679 行的 `generate_api_v1_projects__project_id__generate_post` |

模型输入仍是整章。`generation_context.py` 第 194 行 `scope` 为 `whole_chapter`，第 203 行 `source_scope` 同值，第 213–217 行只拼章节标题、写作要点和字数目标。`workflow_schemas.py` 第 279 行和第 302 行把 `source_scope` 固定为 `whole_chapter`。这里没有评分行、片段计划或逐要点小标题。

内存检索（ISSUE-016 / AI-03）不在本卡依赖列表里，也不提供已发布片段或评分行证据版本，不能代替 T078 或 T114。

## 影响与分流

- 影响范围：T124 保持 blocked，不进入 ready 或 in-progress。不改模型输入、检索服务、OpenAPI 或页面。
- 不涉及：REF-07 的确认权限、ISSUE-010 的选型、ISSUE-018 的持久化。
- 解除条件：T078 提供可引用的已发布片段版本，T114 提供评分行上的当前证据版本，并且上述三个 operationId 已写入 `spec/openapi`。满足后再把 T124 从 blocked 改回可开工状态。开发者不把本 Issue 标 closed，也不把 T124 标 done。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| APP-M2-T124 | 评分行、片段计划、逐要点小标题进入模型输入 | 本轮无产品代码。证据见上表 | AC-01～AC-02 | blocked |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 依赖满足后，得分要点小标题、证据版本/片段计划和字数事实要点进入实际模型输入 | 未执行。依赖未满足，没有改代码 |
| AC-02 | 确认继续复用 T15，不把 REF-07 当成剩余缺口 | 已核对。T15 的按章确认在 `workflow.py` 第 637–672 行。剩余缺口对应 REF-08 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。没有改需求或验收口径 | `docs/PRD.md` 未改 | t124-blocked-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| ROADMAP | 有影响。一张 planned 卡改为 blocked，计数跟着变 | `docs/ROADMAP.md` 当前计数 | t124-blocked-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。模型输入和模块边界都没有改 | `docs/ARCHITECTURE.md` 未改。现有整章 `source_scope` 句子保持 | t124-blocked-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。T124 改为 blocked | `docs/TASK_BOARD.md`、`docs/tasks/APP-M2.md` | t124-blocked-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| PROJECT_STATUS | 有影响。进度要写出阻塞，不能写成已经实现 | `docs/PROJECT_STATUS.md` | t124-blocked-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、交付、说明和核对记录 | `docs/DOCUMENT_INDEX.md` | t124-blocked-1 / ISSUE-022 / 2026-10-12 | 已核对 |
| PROJECT_BRIEF | 有影响。排期计数少一张 planned、多一张 blocked | `docs/PROJECT_BRIEF.md` 排期行 | t124-blocked-1 / ISSUE-022 / 2026-10-12 | 已核对 |

治理块保持 g1.1 / 2026-10-11 / ISSUE-007。`docs/reference/` 未改。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | t124-blocked-1 / blocked | 只登记阻塞。T15 已具备；T078、T114 和三个具名 operationId 不具备。未改产品代码 | [依赖核对](../docs/testing/2026-10-12-t124-dependencies.md) |

## 本地验收与后续合入发布

- 本地验收结论与日期：未执行实现验收。2026-10-12 的结论只是依赖未满足。
- 未覆盖：评分行、片段计划和逐要点小标题都没有进入模型输入。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。只有依赖解除并且项目经理在 QA 签署后，才能把 T124 标为 done。
