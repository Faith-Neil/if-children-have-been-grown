为什么有这个文件：记录 RAGFlow 检索实现这轮改了哪些记录，以及哪些基线故意不改。

它解决什么问题：避免把测试夹具写成运行时已经接通，或回头改里程碑快照里的任务计数。

# ISSUE-037 同步

日期：2026-10-13。revision ragflow-fixture-1。状态 in-progress。AI-04 为 in-review。AI-05 与 AI-06 为 planned。ISSUE-029 保持 closed。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改正文，不改任务计数 | 2026-10-13 |
| ROADMAP.md | 无 | 不改正文，不改任务计数 | 2026-10-13 |
| PROJECT_BRIEF.md | 无 | 不改正文，不改任务计数 | 2026-10-13 |
| ARCHITECTURE.md | 无 | 适配器客户端仍未实现，不改正文 | 2026-10-13 |
| TASK_BOARD.md | 有 | 新增 AI-04 in-review、AI-05 planned、AI-06 planned。活计数改为 397 项：52 done、21 in-review、7 in-progress、267 planned、48 blocked、2 ready。并入 REV-M0-T36 之后 | 2026-10-13 |
| docs/tasks/AI-M0.md | 有 | 增加三张卡。AI-M0 为 6 项，2 项 done | 2026-10-13 |
| PROJECT_STATUS.md | 有 | 写明假服务已提交，客户端未写。活计数同上 | 2026-10-13 |
| DOCUMENT_INDEX.md | 有 | 登记本文件、Issue、交付、代码解释、核对和测试 | 2026-10-13 |
| issues/index.md | 有 | 新增 ISSUE-037，状态 in-progress | 2026-10-13 |
| issues/ISSUE-029.md | 无 | 设计保持 closed，不回写 | 2026-10-13 |
| docs/architecture/ragflow-retrieval-adapter.md | 无 | 设计保持 closed，实现不改这份设计 | 2026-10-13 |
| docs/reference/ | 无 | 不改 PRD v1.8 与字典 v1.9 | 2026-10-13 |
| backend/bid-core | 无 | 不改 `retrieval.py`，不实现客户端 | 2026-10-13 |
| requirements.txt | 无 | 不加依赖。httpx 已在 | 2026-10-13 |
| spec/openapi/demo-v1.json | 无 | 不改契约 | 2026-10-13 |

未合入，未发布。不标 closed，不把 AI-04 标 done。零命中记为跳过写在 Issue 验收里，映射留给 AI-05。数据集生命周期与 `kb_sync` 不在本 Issue。

`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：340 份 Markdown、397 项任务、37 项 Issue。」检查程序未修改。计数含已并入的 REV-M0-T36。`python3 -m pytest tests/backend/test_fake_ragflow.py -q -rs`：9 passed，1 skipped。
