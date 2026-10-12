为什么有这个文件：记录 T124 开工前的只读依赖核对。

它解决什么问题：避免把看板状态或计划中的片段、评分行写成已经进入模型输入。

# 2026-10-12 T124 依赖核对

日期：2026-10-12。关联 [ISSUE-022](../../issues/ISSUE-022.md) / [APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)。先做了只读依赖核对，随后只加了 OpenAPI 草案和契约测试。

## 结论

T15 满足。T114 已 done（QA f521950，PM 17:13 确认）。T078 仍 in-review 未 done，所以 T124 仍不满足开工。三个 operationId 已写入契约，状态为 frozen，运行时没有这些路由。T124 不能标 ready，仍是 blocked。ISSUE-022 已依据 QA 0254102（REV-M0-T20），PM 15:36 确认 closed。剩余范围对应 REF-08，不对应 REF-07。下表里 T114 为 planned、没有抽屉，是开工核对当时的快照。

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
| 契约名 | `spec/openapi/demo-v1.json` | operationId 为 `getOutlinePlan`、`confirmOutlinePlan`、`startGeneration`、`getJob`。`x-contract-status` 为 frozen，`x-implemented` 为 false。已实现的生成入口仍是 `generate_api_v1_projects__project_id__generate_post` |
| 模型输入 | `generation_context.py` 第 194、203、213–217 行 | `whole_chapter`。只拼标题、写作要点和字数目标 |
| 差异 | `docs/decisions/icg-reference-deviations.md` 第 16–17 行 | 第 16 行是 REF-07，第 17 行是 REF-08 |

## 契约测试

命令：`python3 -m pytest tests/backend/test_outline_contract_draft.py tests/backend/test_error_idempotency.py::test_openapi_declares_v1_error_body_status_table_and_retry -q`

复核后的核对：operationId 为 camelCase；`JobStatus` 不继承 `Job`，status 含 queued、running、completed、failed、cancelled；`JobEvent` 含 seq、id、occurred_at，type 为枚举；GET 不列 413、423、428，`getJob` 不列 409，502 只在 `startGeneration`；`getOutlinePlan` 有 ETag；三个旧 POST 在文件里为 `deprecated: true`。去掉草案标记和这三处废弃说明后，与 `create_app().openapi()` 一致。没有新增错误码。

这些测试不向新路径发请求。应用里没有对应路由。

并入远程之前 `python3 -m pytest tests/backend -q` 为 313 项通过。该结果只说明当时的后台和契约形状，不说明新路由已经可调用。当时 `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：183 份 Markdown、356 项任务、22 项 Issue。」检查程序未修改。

并入 `b364cd1`（含 `a844a17` 与 `98c5129`）之后，同一命令为 320 项通过、2 项跳过。跳过的是未设置 `ICG_DATABASE_URL` 的 MySQL 门禁。随后的文档提交不改后台代码。治理检查通过，输出为「治理检查通过：196 份 Markdown、361 项任务、23 项 Issue。」检查程序未修改。这些数字不说明新路由已经可调用。

## 复审补充（outline-contract-draft-3）

按已采纳的对 `046f8e5` / `fe9582c` 的复审改草案，仍不调用新路由。`startGeneration` 列 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 与 503 `SECRET_KEY_UNAVAILABLE`，两码不在 `V1Error` 枚举和 `x-error-status` 里。503 的响应说明写明不是瞬时故障，客户端不要自动重试，与 `MODEL_UNAVAILABLE` 相同。任务开始时的模型配置快照提供 `job.model_call` 的 `provider` 和 `model`。`confirmOutlinePlan` 与 `startGeneration` 列 423。`JobEvent.type` 增加状态变化、进度和三种终态，payload 注明由 BE-M0-T06 实现。`JobStatus` 增加 `recoverable`。`cancelJob` 成功响应没有 Location。`getJob` 与 SSE 没有 403。

命令：`python3 -m pytest tests/backend/test_outline_contract_draft.py tests/backend/test_error_idempotency.py::test_openapi_declares_v1_error_body_status_table_and_retry -q`

结果：5 passed。没有因此重跑全部后台测试：本轮不改 `backend/bid-core`。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。并入 `bde8e9e` 后 `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：223 份 Markdown、364 项任务、28 项 Issue。」

## 契约冻结（outline-contract-frozen-1）

第三轮复审批准后冻结文本。`x-contract-status` 改为 `frozen`。已实现路径没有这个字段，过滤仍按该值去掉尚未实现的路径和模型。全局 `info.description`、`x-idempotency.retry` 和每条 `Idempotency-Key` 描述都包含：`502 MODEL_UNAVAILABLE 与 503 SECRET_KEY_UNAVAILABLE 不是瞬时故障，客户端不要自动重试，后端不发送 Retry-After。` `confirmOutlinePlan` 的 423，以及 `startGeneration` 的 423 与 503，响应头里没有 `Idempotent-Replayed`。`JobEvent.required` 未按事件类型拆开，N8 留到 BE-M0-T06。

命令：`python3 -m pytest tests/backend/test_outline_contract_draft.py tests/backend/test_error_idempotency.py::test_openapi_declares_v1_error_body_status_table_and_retry -q`

结果：7 passed，1 warning。

随后 `python3 -m pytest tests/backend -q`：351 passed、6 skipped、1 warning。6 项跳过都是 `ICG_DATABASE_URL is unset`。这些测试不向新路径发请求。并入 `6c09121` 后 `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：247 份 Markdown、371 项任务、29 项 Issue。」检查程序未修改。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。

## QA 重试说明

`spec/openapi/README.md` 写明客户端只对网络错误、502 和 503 用同一把 `Idempotency-Key` 重试，并补上 N7：`502 MODEL_UNAVAILABLE 与 503 SECRET_KEY_UNAVAILABLE 不是瞬时故障，客户端不要自动重试，后端不发送 Retry-After。` 同文件“同标记重试返回原结果”是成功重放，未改。

`spec/openapi/demo-v1.json` 的 `components.x-idempotency.retry` 在这句 N7 之后追加：`没有 Idempotency-Key 的写入不自动重试。` 全局描述和每条 `Idempotency-Key` 描述不追加这句。`errors.py` 未改，错误码计数未改。契约测试在与运行中 OpenAPI 比较前去掉这句。

命令：`python3 -m pytest tests/backend/test_outline_contract_draft.py tests/backend/test_error_idempotency.py::test_openapi_declares_v1_error_body_status_table_and_retry -q`

结果：7 passed，1 warning。

随后 `python3 -m pytest tests/backend -q`：351 passed、8 skipped、1 warning。8 项跳过都是 `ICG_DATABASE_URL is unset`。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：260 份 Markdown、372 项任务、31 项 Issue。」检查程序未修改。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。

## 局限

没有连接 MySQL，没有调用模型，也没有把内存检索接到生成。草案不是可恢复任务已经实现，也不是发布。T078 计划没有对应测试，因为没有代码。

