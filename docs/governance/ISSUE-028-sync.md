# ISSUE-028 基线同步记录

日期：2026-10-12。治理版本：g1.1。范围：配置驱动的对话模型设计。状态 in-review。无运行代码。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无。不新增验收，不改任务计数 | 不改正文 | 2026-10-12 |
| ROADMAP.md | 决定用词随 ISSUE-010。计数不改 | 不改数字 | 2026-10-12 |
| ARCHITECTURE.md | 有 | 指向设计，写明未实现 | model-config-design-1 |
| TASK_BOARD.md | 无新任务 | AI-01 状态随 ISSUE-010 | 2026-10-12 |
| PROJECT_STATUS.md | 有 | 写明设计在复核 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有 | 登记本文件与设计 | 2026-10-12 |
| PROJECT_BRIEF.md | 计数不改 | 不改数字 | 2026-10-12 |
| spec/openapi/demo-v1.json | 无 | 新错误码不写入 | 后台拥有契约草案 |
| requirements.txt | 无 | 不加依赖 | httpx 与 cryptography 已在 |

未合入，未发布。以上是 model-config-design-1 的核对，保留不回写。

## model-config-design-2

日期：2026-10-12。PM 分工：本 Issue 只保留 Provider 侧。配置的存储、字段定义、API、加密、If-Match 和幂等归后端 ISSUE-024。字段提案已交后台，以 ISSUE-024 为准。本仓库没有 ISSUE-024 详情，只在 ISSUE-028 与设计文档中引用该编号，不创建该文件。不改任务计数。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改任务计数，不改正文 | 2026-10-12 |
| ROADMAP.md | 无 | 不改任务计数，不改正文 | 2026-10-12 |
| PROJECT_BRIEF.md | 无 | 不改任务计数，不改正文 | 2026-10-12 |
| ARCHITECTURE.md | 无正文变化 | 仍指向设计文件。范围以该文件的 design-2 为准 | 2026-10-12 |
| TASK_BOARD.md | 无 | 不改任务计数，不改 AI-01 状态 | 2026-10-12 |
| PROJECT_STATUS.md | 无 | 不改任务计数 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有 | D-293、D-296、D-298 改为 Provider 侧说明。不改计数行 | model-config-design-2 |
| issues/index.md | 有 | ISSUE-028 行改为 Provider 侧，并写明不建 ISSUE-024 | in-review |
| issues/ISSUE-028.md | 有 | revision 改为 model-config-design-2 | in-review |
| model-config-provider.md | 有 | 删去字段表、测试连接、加密和 If-Match。保留读取、快照、路由、敏感约束、流式/JSON、错误映射、`job.model_call` | in-review |
| spec/openapi/demo-v1.json | 无 | 不改 | 契约归 ISSUE-024 |
| requirements.txt | 无 | 不加依赖 | 2026-10-12 |
| issues/ISSUE-024.md | 不创建 | 文件不存在，故不能从 024 回链 | 仅 028 侧引用 |
| issues/ISSUE-027.md | 无 | 已是 Word 版式卡，本轮不改 | in-review |

未合入，未发布。不标 closed，不标 done。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：219 份 Markdown、363 项任务、28 项 Issue。」检查程序未修改。没有重跑 pytest：本轮不改后台代码。

2026-10-12 随后登记了 [ISSUE-024](../../issues/ISSUE-024.md)，状态 new。上面 design-2 的“不创建该文件”只描述当时。Provider 字段仍不抄回本设计。

## QA P3（REV-M0-T17）

日期：2026-10-12。来源提交 f5af6db。只改文档。ISSUE-028 与 AI-01 仍为 in-review。不标 closed，不标 done。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改正文，不改任务计数 | 2026-10-12 |
| ROADMAP.md | 无 | 不改正文，不改任务计数 | 2026-10-12 |
| PROJECT_BRIEF.md | 无 | 不改正文，不改任务计数 | 2026-10-12 |
| ARCHITECTURE.md | 无 | 不改正文 | 2026-10-12 |
| TASK_BOARD.md | 无状态变化 | 不改任务计数，不改 AI-01 状态 | 2026-10-12 |
| PROJECT_STATUS.md | 无 | 不改任务计数 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有 | 更新 D-294、D-295、D-296、D-298、D-299 说明，并追加变更记录。不改历史行，不改计数行 | 2026-10-12 |
| 决定记录 | 有 | 局限改为 ISSUE-024 已由后台建档并拥有模型配置字段。流式与 JSON 模式开关的字段名归 ISSUE-024（D-1），028 只引用 | 2026-10-12 |
| issues/ISSUE-028.md | 有 | 增加未实现的 AC-04 与一条历史。状态仍 in-review | model-config-design-2 |
| docs/tasks/AI-M0.md | 有 | AI-01 增加未勾选验收：敏感项目使用非本地模型返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`（由 409 改为 403） | in-review |
| ragflow-retrieval-adapter.md | 有 | 记下 ISSUE-016 QA P3：路径 C 不按查询词过滤，实现适配器时再改 | in-review |
| spec/openapi/demo-v1.json | 无 | 不改 | 2026-10-12 |
| backend/bid-core | 无 | 不改 domain.py 与 errors.py | 2026-10-12 |
| issues/ISSUE-010-sync.md | 无 | 该段是当时的同步段落，不回写 | 2026-10-12 |

未合入，未发布。没有重跑 pytest：本轮不改后台代码。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：247 份 Markdown、371 项任务、29 项 Issue。」检查程序未修改。

## D-1 字段引用

日期：2026-10-12。`issues/ISSUE-024.md` 已在分支上，故 ISSUE-028 文档链接该文件。ISSUE-028 与 AI-01 仍为 in-review。不标 closed，不标 done。不改 ISSUE-024 正文。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改正文，不改任务计数 | 2026-10-12 |
| ROADMAP.md | 无 | 不改正文，不改任务计数 | 2026-10-12 |
| PROJECT_BRIEF.md | 无 | 不改正文，不改任务计数 | 2026-10-12 |
| ARCHITECTURE.md | 无 | 不改正文 | 2026-10-12 |
| TASK_BOARD.md | 无 | 不改任务计数，不改 AI-01 状态 | 2026-10-12 |
| PROJECT_STATUS.md | 无 | 不改任务计数 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有 | 更新 D-295、D-296、D-298 说明，并追加变更记录。不改历史行，不改计数行 | 2026-10-12 |
| 决定记录 | 有 | 引用 ISSUE-024 的 `stream_enabled`（布尔，默认 true）和 `json_mode_enabled`（布尔，默认 false）。二者纳入 `revision` 乐观锁，并在任务开始时随配置快照。028 不重定义 | 2026-10-12 |
| issues/ISSUE-028.md | 有 | 正文与新历史只引用这两个名字。定义留在 ISSUE-024。状态仍 in-review | model-config-design-2 |
| model-config-provider.md | 有 | 同上，只引用，不重定义 | in-review |
| issues/ISSUE-024.md | 无 | 文件已存在。本轮不改 | new |
| spec/openapi/demo-v1.json | 无 | 不改 | 2026-10-12 |
| backend/bid-core | 无 | 不改 | 2026-10-12 |

未合入，未发布。没有重跑 pytest：本轮不改后台代码。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：247 份 Markdown、371 项任务、29 项 Issue。」检查程序未修改。

## 只链接 D-1 字段名

日期：2026-10-12。`3e1445e` 已在 `issues/ISSUE-024.md` 定义 `stream_enabled` 与 `json_mode_enabled`。ISSUE-028 文档只链接这两个名字，不抄类型、默认值、乐观锁或快照。ISSUE-028 仍为 in-review。不改 ISSUE-024 正文。不改任务计数。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| 决定记录 | 有 | 两个字段名改为指向 ISSUE-024 的链接 | 2026-10-12 |
| issues/ISSUE-028.md | 有 | 正文与新历史只放链接。状态仍 in-review | model-config-design-2 |
| model-config-provider.md | 有 | 同上 | in-review |
| DOCUMENT_INDEX.md | 有 | 更新 D-295、D-296、D-298，并追加变更记录。不改历史行 | 2026-10-12 |
| issues/ISSUE-024.md | 无 | 不改 | new |
| PRD.md / ROADMAP.md / PROJECT_BRIEF.md | 无 | 不改正文，不改计数 | 2026-10-12 |
| spec 与 backend | 无 | 不改 | 2026-10-12 |

未合入，未发布。没有重跑 pytest。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：247 份 Markdown、371 项任务、29 项 Issue。」检查程序未修改。

## CI 假服务

日期：2026-10-12。revision model-config-fixture-1。ISSUE-028 与 AI-01 仍为 in-review。ISSUE-010 仍为 closed。不标 closed，不标 done。不改 `backend/bid-core`，不改 OpenAPI，不加依赖，不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改正文，不改任务计数 | 2026-10-12 |
| ROADMAP.md | 无 | 不改正文，不改任务计数 | 2026-10-12 |
| PROJECT_BRIEF.md | 无 | 不改正文，不改任务计数 | 2026-10-12 |
| ARCHITECTURE.md | 无正文变化 | 不改正文。假服务说明在 model-config-provider.md | 2026-10-12 |
| model-config-provider.md | 有 | CI 一节改为已落地的假服务和 `ICG_RUN_REAL_MODEL_TESTS` | in-review |
| TASK_BOARD.md | 有说明 | 不改任务计数，不改 AI-01 状态。写明假服务已落地 | 2026-10-12 |
| PROJECT_STATUS.md | 有说明 | 不改任务计数。写明假服务与默认跳过 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有 | 更新 D-293、D-296、D-298，登记核对与代码解释，追加变更记录 | model-config-fixture-1 |
| issues/ISSUE-028.md | 有 | AC-02 改为已编码。状态仍 in-review | model-config-fixture-1 |
| docs/tasks/AI-M0.md | 有 | 勾选假服务验收。真实端点与 403 仍未勾选。状态仍 in-review | in-review |
| docs/delivery/AI-01.md | 有 | 补假服务一节。不标 done | in-review |
| docs/code/AI-01.md | 有 | 说明夹具与 opt-in。不改运行适配器 | 当前 |
| tests/backend | 有 | `fake_openai_chat.py`、夹具、`live_model` 标记 | 2026-10-12 |
| spec/openapi/demo-v1.json | 无 | 不改 | 2026-10-12 |
| frozen_error_codes.py | 无 | 不改 | 2026-10-12 |
| issues/ISSUE-010.md | 无 | 保持 closed | closed |

未合入，未发布。不标 done，不标 closed。`python3 -m pytest tests/backend/test_openai_compatible_model.py -q -rs` 为 34 passed、1 skipped、1 warning。跳过原因是 `real model endpoint tests require ICG_RUN_REAL_MODEL_TESTS=1`。`python3 -m pytest tests/backend -q -rs` 为 355 passed、13 skipped、1 warning。12 项跳过是 `ICG_DATABASE_URL is unset`，另 1 项是同一真实端点开关。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：296 份 Markdown、383 项任务、34 项 Issue。」检查程序未修改。
