为什么有这个文件：记录 T124 开工前的只读依赖核对。

它解决什么问题：避免把看板状态或计划中的片段、评分行写成已经进入模型输入。

# 2026-10-12 T124 依赖核对

日期：2026-10-12。关联 [ISSUE-022](../../issues/ISSUE-022.md) / [APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)。先做了只读依赖核对，随后只加了 OpenAPI 草案和契约测试。

## 结论

T15 满足。T078 与 T114 仍不满足。三个 operationId 已写入草案，契约状态为 draft, pending backend review，运行时没有这些路由。T124 不能标 ready，仍是 blocked。ISSUE-022 为 in-review，只复核草案。剩余范围对应 REF-08，不对应 REF-07。

## 证据

| 项 | 文件与行 | 看到的事实 |
|---|---|---|
| T15 按章确认 | `backend/bid-core/icg_demo/workflow.py` 第 637–672 行 | `_confirm_chapter_plan` 与 `chapter_plan_confirm` 已存在 |
| T15 当前性 | `backend/bid-core/icg_demo/generation_context.py` 第 83–91 行 | `plan_is_current` 按单章判断 |
| T15 状态 | `docs/TASK_BOARD.md` 第 151 行 | done |
| T078 状态 | `docs/tasks/APP-M2.md` 第 1193 行；`docs/TASK_BOARD.md` 第 230 行 | planned |
| 片段发布 | `backend/bid-core` 与 `frontend/web` | 没有 `kb_sync_status`。`workflow_schemas.py` 第 13 行的 `snippet` 只是资料类型 |
| T114 状态 | `docs/tasks/APP-M2.md` 第 1736 行；`docs/TASK_BOARD.md` 第 266 行 | planned |
| 证据抽屉 | `frontend/web` | 没有 `EvidenceDrawer`。`ProjectPages.tsx` 第 129 行只保存条款的 `evidence_ids` |
| 契约名 | `spec/openapi/demo-v1.json` 第 11203、11408、11690、11979 行 | 草案 operationId 为 `getOutlinePlan`、`confirmOutlinePlan`、`startGeneration`、`getJob`。状态为 draft, pending backend review。第 6679 行仍是已实现的 `generate_api_v1_projects__project_id__generate_post` |
| 模型输入 | `generation_context.py` 第 194、203、213–217 行 | `whole_chapter`。只拼标题、写作要点和字数目标 |
| 差异 | `docs/decisions/icg-reference-deviations.md` 第 16–17 行 | 第 16 行是 REF-07，第 17 行是 REF-08 |

## 契约测试

命令：`python3 -m pytest tests/backend/test_outline_contract_draft.py tests/backend/test_error_idempotency.py::test_openapi_declares_v1_error_body_status_table_and_retry -q`

核对 operationId 为 camelCase，错误响应引用 `V1Error` 且必填 `code`、`message`、`details`、`traceId`，写操作带 `Idempotency-Key` 并写明 428 与 409，`startGeneration` 只有 202 且 `Location` 指向 `/api/v1/jobs/{id}`，`JobStatus` 复用 `Job`，`job.model_call` 含 `provider`、`model`、`is_real_model`、`is_local`、`duration_ms`、`error_code`。去掉草案后的说明与 `create_app().openapi()` 一致。没有新增错误码。

这些测试不向新路径发请求。应用里没有对应路由。

rebase 前 `python3 -m pytest tests/backend -q` 为 313 项通过。该结果只说明当时的后台和契约形状，不说明新路由已经可调用。冲突解开后 `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：183 份 Markdown、356 项任务、22 项 Issue。」检查程序未修改。

## 局限

没有连接 MySQL，没有调用模型，也没有把内存检索接到生成。草案不是可恢复任务已经实现，也不是发布。T078 计划没有对应测试，因为没有代码。

