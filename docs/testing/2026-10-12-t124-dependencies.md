为什么有这个文件：记录 T124 开工前的只读依赖核对。

它解决什么问题：避免把看板状态或计划中的片段、评分行写成已经进入模型输入。

# 2026-10-12 T124 依赖核对

日期：2026-10-12。关联 [ISSUE-022](../../issues/ISSUE-022.md) / [APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)。没有改产品代码，因此没有运行后台 pytest。

## 结论

T15 满足。T078、T114 和任务卡写出的三个 operationId 不满足。T124 不能标 ready。剩余范围对应 REF-08，不对应 REF-07。

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
| 契约名 | `spec/openapi/demo-v1.json` | 没有 `getOutlinePlan`、`confirmOutlinePlan`、`startGeneration`。第 6679 行是现有 `generate_api_v1_projects__project_id__generate_post` |
| 模型输入 | `generation_context.py` 第 194、203、213–217 行 | `whole_chapter`。只拼标题、写作要点和字数目标 |
| 差异 | `docs/decisions/icg-reference-deviations.md` 第 16–17 行 | 第 16 行是 REF-07，第 17 行是 REF-08 |

## 局限

这次核对只读当前分支上的文件。没有连接 MySQL，没有调用模型，也没有把内存检索接到生成。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：176 份 Markdown、354 项任务、20 项 Issue。」检查程序未修改。blocked 不是实现通过，也不是发布。
