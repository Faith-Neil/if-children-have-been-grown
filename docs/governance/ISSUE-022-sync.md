# ISSUE-022 基线同步记录

日期：2026-10-12。治理版本：g1.1。任务：APP-M2-T124。范围：依赖未满足，不改产品代码。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无。没有新的用户操作或验收口径 | 不改需求正文 | 维持现有实施视图 |
| ROADMAP.md | 有。一张卡从 planned 改为 blocked | 当前计数改为 354 项：21 done、7 in-review、7 in-progress、265 planned、50 blocked、4 ready。页面顺序不变 | 2026-10-12 |
| ARCHITECTURE.md | 无。整章输入没有改 | 不改架构正文。REF-08 仍是现状 | 未改 |
| issues/index.md / ISSUE-022.md | 有。新阻塞已登记 | 状态为 blocked。ISSUE-018 仍预留，ISSUE-021 仍无文件 | blocked；未合入、未发布 |
| TASK_BOARD.md / tasks/APP-M2.md | 有。T124 改状态 | 看板和任务卡为 blocked，并链到本 Issue。交付和代码说明写明无代码 | blocked |
| PROJECT_STATUS.md | 有。必须写出未实现 | 进度中写明 T124 blocked，planned 265、blocked 50 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有。Issue、交付、说明和核对都要能找到 | 登记 D-250～D-254 | 2026-10-12 |
| PROJECT_BRIEF.md | 有。排期计数变了 | 排期改为 354 项、265 planned、50 blocked。原因是 T124 从 planned 改为 blocked | 2026-10-12；已登记 |
| 产品代码 | 无。依赖未满足 | 不改 `generation_context.py`、检索、OpenAPI 或页面 | 保持整章输入 |

开发者登记的阻塞不能当作任务 done、Issue closed、PR 已合入或模型输入已经包含评分行。
