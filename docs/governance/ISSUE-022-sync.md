# ISSUE-022 基线同步记录

日期：2026-10-12。治理版本：g1.1。任务：APP-M2-T124。范围：OpenAPI 草案待复核，T124 实现仍 blocked。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无。没有新的用户操作或验收口径 | 不改需求正文 | 维持现有实施视图 |
| ROADMAP.md | 无任务增减。需要说明草案不是实现，并跟上 rebase 后的看板 | 356 项：23 done、6 in-review、7 in-progress、266 planned、50 blocked、4 ready。补一句契约草案待复核，T124 仍 blocked | 2026-10-12 |
| ARCHITECTURE.md | 无。草案和 T078 计划都没有进入运行结构 | 不改架构正文。REF-08 的整章 `source_scope` 保持 | 未改 |
| issues/index.md / ISSUE-022.md | 有。Issue 从 blocked 改为 in-review | 复核对象是契约草案。T124 任务仍 blocked。保留已登记的 ISSUE-018 与 ISSUE-021 | in-review；未合入、未发布 |
| TASK_BOARD.md / tasks/APP-M2.md | 有。任务状态不变，说明要改 | 看板和任务卡中的 T124 仍为 blocked，并写明草案未实现 | blocked |
| PROJECT_STATUS.md | 有。进度不能把草案写成已接通 | 写明 ISSUE-022 为 in-review，T124 仍 blocked，计数不变 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有。计划文档要能找到 | 更新 ISSUE-022 条目，登记 T078 计划 | 2026-10-12 |
| PROJECT_BRIEF.md | 计数无变化。接手说明要提到草案 | 排期计数不变，补一句草案待复核 | 2026-10-12；已登记 |
| 产品代码 | 无运行时变化 | 不改 `generation_context.py`、检索、页面或 `Repository.read` / `transaction`。草案按 `x-contract-status` 滤出。三个旧 POST 的 `deprecated: true` 只写在说明文件里，运行时尚未标出 | outline-contract-draft-2；契约状态 draft, pending backend review |

开发者把 Issue 标到 in-review 只表示草案可以复核。这不是任务 done，不是 Issue closed，也不是模型输入已经包含评分行。

## outline-contract-draft-3

日期：2026-10-12。范围：按已采纳的复审补充草案。ISSUE-022 仍为 in-review。T124 仍 blocked。契约状态仍是 draft, pending backend review。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改正文，不改计数 | 2026-10-12 |
| ROADMAP.md | 无 | 不改正文，不改计数 | 2026-10-12 |
| PROJECT_BRIEF.md | 无 | 不改正文，不改计数 | 2026-10-12 |
| ARCHITECTURE.md | 无 | 草案仍未实现 | 2026-10-12 |
| TASK_BOARD.md | 无状态变化 | T124 仍 blocked，不改计数 | 2026-10-12 |
| PROJECT_STATUS.md | 无 | 不把草案写成已接通，不改计数 | 2026-10-12 |
| issues/ISSUE-022.md | 有 | revision 改为 outline-contract-draft-3。状态仍 in-review | in-review |
| issues/index.md | 有 | 下一步改为等待再次复核补充后的草案 | in-review |
| spec/openapi/demo-v1.json | 有 | startGeneration 列 403 与 503，两码只引用 ISSUE-024。503 写明不是瞬时故障、不要自动重试。确认与启动列 423。JobEvent 增加状态、进度、终态。JobStatus 增加 recoverable。cancelJob 不强制 Location。getJob 与 SSE 去掉 403 | draft, pending backend review |
| DOCUMENT_INDEX.md | 有 | 草案条目改为 draft-3。不改计数行 | 2026-10-12 |
| 运行代码 | 无 | 不改 `backend/bid-core`，不把两个新码写入 `errors.py` | 2026-10-12 |

未合入，未发布。不标 done，不标 closed。并入 `bde8e9e` 后 `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：223 份 Markdown、364 项任务、28 项 Issue。」检查程序未修改。

## t078-plan-etag-receipt

日期：2026-10-12。范围：只补 T078 计划的两句。不写代码。ISSUE-022 仍为 in-review。T124 仍 blocked。T078 仍 planned。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改正文，不改计数。计划没有新的用户验收口径 | 2026-10-12 |
| ROADMAP.md | 无 | 不改正文，不改计数。没有新任务或依赖变化 | 2026-10-12 |
| PROJECT_BRIEF.md | 无 | 不改正文，不改计数 | 2026-10-12 |
| ARCHITECTURE.md | 无 | 计划仍未进入运行结构 | 2026-10-12 |
| TASK_BOARD.md | 无状态变化 | T078 仍 planned，T124 仍 blocked | 2026-10-12 |
| PROJECT_STATUS.md | 无 | 不把计划写成已实现 | 2026-10-12 |
| issues/ISSUE-022.md | 有记录 | 状态仍 in-review。T078 节指向已补两句的方案，并加一条复核记录 | in-review |
| issues/index.md | 有记录 | 状态不变。证据格写明方案补了 ETag 与拦截发布的幂等回执 | in-review |
| docs/governance/ISSUE-022-t078-plan.md | 有 | GET 返回 ETag。被拦截的发布仍算成功，必须记下幂等回执。`records` 与 `audits` 仍不改 | 未实现 |
| DOCUMENT_INDEX.md | 有 | D-266 改为 t078-plan-etag-receipt | 2026-10-12 |
| 运行代码 | 无 | 不改 `backend/bid-core`，不新增测试 | 2026-10-12 |

未合入，未发布。不标 done，不标 closed。并入 `d55d507` 后 `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：225 份 Markdown、365 项任务、28 项 Issue。」检查程序未修改。
