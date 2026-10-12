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
| 产品代码 | 无运行时变化 | 不改 `generation_context.py`、检索、页面或 `Repository.read` / `transaction`。只在 OpenAPI 中追加带草案标记的路径 | 契约状态 draft, pending backend review |

开发者把 Issue 标到 in-review 只表示草案可以复核。这不是任务 done，不是 Issue closed，也不是模型输入已经包含评分行。
