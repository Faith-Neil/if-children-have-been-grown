为什么有这个文件：记录QA对ISSUE-026基线快照规则的独立复核。

它解决什么问题：确认三份基线写成里程碑快照、以任务看板为准，且检查程序在之后签卡时不会因计数不等而报错。

# ISSUE-026 基线快照规则 QA 签署

日期 2026-10-12（UTC+8）。签署卡 REV-M0-T13，归入 ISSUE-013。分支 `codex/repository-foundation`，被验提交 `c9a3cd5`（基于 `3bb311a`），核对到 `631d4c9`。

## 结论

**通过。** ISSUE-026 保持 in-review，done 由项目经理设置。

## 逐条核对

| 项 | 结果 | 证据 |
|---|---|---|
| 三份基线快照 | 通过 | `docs/PRD.md` 第19行、`docs/ROADMAP.md` 第17行、`docs/PROJECT_BRIEF.md` 第30行均写 366 项：32 done、6 in-review、7 in-progress、268 planned、49 blocked、4 ready（as of commit `3bb311ad3ab8…`，计入 T001/T002 done），并写“任务看板是准绳”“只在里程碑更新” |
| 看板独立重数 | 通过 | 在 `c9a3cd5` 按 TASK_BOARD 表格状态列计数：done 32、in-review 6、in-progress 7、planned 268、blocked 49、ready 4，合计 366 |
| T001/T002 done 依据 | 通过 | QA 签署 `d55d507`（REV-M0-T11），项目经理群内确认 |
| 规则落点 | 通过 | `issues/ISSUE-026.md` AC-01 与变更记录、`docs/governance/ISSUE-026-sync.md`、`docs/governance/WORKFLOW.md` 第4节第82行 |
| 检查程序 | 通过 | `scripts/check-project-governance.cjs` 只校验治理块、链接、索引、任务/Issue 状态取值和 done 卡交付块；`baselineDocuments` 只用于治理头与链接，无与看板计数相等的比较 |
| 模拟签收 | 通过 | 在 `e6215d4` 把 AI-03 临时改为 done（33 done），`node scripts/check-project-governance.cjs` 输出“治理检查通过：231 份 Markdown、366 项任务、28 项 Issue”，随后 `git checkout` 还原。另：HEAD 上 T078 已使看板变为 32/7/7/267，检查照样通过，规则在真实变动下已生效 |
| CI | 通过 | run 38211999576（`c9a3cd5`）因同分支新推送被并发取消（cancelled）；包含该提交的后继 run 38212117391（`e6215d4`）backend、frontend、governance、e2e、backend-mysql 全部 success |

## 观察项

- O-1（P3，前端）：TASK_BOARD 第11行摘要句仍需随卡片变动手工更新，检查程序不校验它；建议后续在里程碑同步时一并核对。
