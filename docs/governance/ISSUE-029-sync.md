# ISSUE-029 基线同步记录

日期：2026-10-12。治理版本：g1.1。范围：RAGFlow 检索适配器设计。状态 in-review。无运行代码。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无。不改任务计数 | 不改正文 | 2026-10-12 |
| ROADMAP.md | 决定用词随 ISSUE-010。计数不改 | 不改数字 | 2026-10-12 |
| ARCHITECTURE.md | 有 | 写明 RAGFlow，适配器未实现 | ragflow-adapter-design-1 |
| TASK_BOARD.md | 无新任务 | AI-03 仍 in-review | 2026-10-12 |
| PROJECT_STATUS.md | 有 | 写明检索仍是内存 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有 | 登记本文件与设计 | 2026-10-12 |
| PROJECT_BRIEF.md | 计数不改 | 不改数字 | 2026-10-12 |
| backend/bid-core | 无 | 不改 retrieval.py | 内存口保持 |
| requirements.txt | 无 | 不加依赖 | httpx==0.28.1 已在 |

未合入，未发布。

2026-10-12：适配器设计记下 ISSUE-016 QA P3。当前路径 C 不按查询词过滤，实现 RAGFlow 适配器时再改。不改检索代码。ISSUE-029 仍 in-review。未合入，未发布。

## 用户确认后关闭

日期：2026-10-12。依据：用户 10-12 14:34 确认。ISSUE-029 改为 closed。重排定为 RAGFlow 自带的重排器，重排模型在 RAGFlow 内配置。适配器未实现。不改 ISSUE-017 与 OPS-M0-T02。不改检索代码。ISSUE-028 仍 in-review。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改正文，不改里程碑计数 | 2026-10-12 |
| ROADMAP.md | 无 | 不改正文，不改里程碑计数 | 2026-10-12 |
| PROJECT_BRIEF.md | 无 | 不改正文，不改里程碑计数 | 2026-10-12 |
| ARCHITECTURE.md | 无新句 | 重排决定已在该文件。本轮只改 ISSUE-016 的状态句 | 2026-10-12 |
| ragflow-retrieval-adapter.md | 有 | 重排由提案改为已决定：RAGFlow 自带，模型在 RAGFlow 内配置 | closed |
| TASK_BOARD.md | 无新任务 | AI-03 的 done 记在 ISSUE-016。不改 OPS-M0-T02 | 2026-10-12 |
| issues/ISSUE-029.md | 有 | 状态改为 closed | closed |
| issues/ISSUE-017.md | 无 | 不改 | closed |
| backend/bid-core | 无 | 不改 retrieval.py | 2026-10-12 |

未合入，未发布。没有重跑 pytest：本轮不改后台代码。
