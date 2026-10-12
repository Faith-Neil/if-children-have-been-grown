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
