# ISSUE-011 基线同步记录

日期：2026-10-12。治理版本：g1.1。任务：AI-02。范围：OpenAI 兼容对话适配器的本地契约，不含真实端点和数据库。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无。没有新的用户操作或验收口径 | 默认建议仍是演示文本，不改需求正文 | 维持现有实施视图 |
| ROADMAP.md | 有。适配器应出现在进度里，但不能标成 done | 说明 AI-02 为 in-review，不关闭 ISSUE-010。开发者不把任务标 done | 2026-10-12 进度说明 |
| ARCHITECTURE.md | 有。模型口有了第二个实现和显式开关 | 写明失败仍是 502，默认仍是替身 | 2026-10-12 说明 |
| issues/index.md / ISSUE-011.md | 有。项目经理已确认 | 曾从 closed 改回 in-review。2026-10-12 12:10 项目经理在 QA 签署后确认，Issue 改为 closed，合入和发布仍未发生 | closed；未合入、未发布 |
| TASK_BOARD.md / tasks/AI-M0.md | 有。AI-02 现为 done | 看板和任务卡改为 done。项目经理于 10-12 12:10 在 QA 签署后确认。交付和代码解释仍链接 | done |
| PROJECT_STATUS.md | 有。必须区分项目经理确认和内网未接通 | 进度写明 closed / done，真实端点仍未接通。ISSUE-010 不在本次 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有。代码、测试、交付和验证都要能找到 | 登记新增与更新条目 | 2026-10-12 |
| 产品参考 PRD/字典 | 无。适配器不修改参考原文 | 未修改 `docs/reference/` | 保持原文 |
| 业务数据库 | 无实现。选库记录在 ISSUE-010，本适配器不连接数据库 | 不新增数据库依赖或迁移 | 内存实现保留 |
| PROJECT_BRIEF.md | 有。2026-10-12 的排期行原先未登记；本确认再次改写该行 | 提交 0c60842 把排期从 340 项（18 done、8 in-progress、266 planned、48 blocked）改为 342 项（19 done、8 in-progress、266 planned、49 blocked），并写上 AI-02 已本地验收。原因是接手 brief 的计数要和任务看板一致，且不回退该句。随后曾把 AI-02 改回 in-review，排期写成 343 项中 18 done、2 in-review、8 in-progress。项目经理于 10-12 12:10 在 QA 签署后确认后，AI-02 改为 done。排期改为 343 项中 19 done、2 in-review、7 in-progress、266 planned、49 blocked：AI-02 计入 done；T001 已在看板上为 in-review，本句与看板对齐。先前句子不回退 | 2026-10-12；已登记 |

项目经理于 10-12 12:10 在 QA 签署后确认，AI-02 为 done，ISSUE-011 为 closed。这只表示本地验收，不是 PR 已合入或服务已发布。真实端点仍等 ISSUE-010，该 Issue 本次未改，仍 blocked。PRD、ROADMAP、ARCHITECTURE 和 DOCUMENT_INDEX 本次未改。
