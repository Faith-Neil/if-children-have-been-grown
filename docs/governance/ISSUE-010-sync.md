# ISSUE-010 基线同步记录

日期：2026-10-12。治理版本：g1.1。任务：AI-01。范围：登记待决项，并记录用户已作出的业务库决定。开发者不因此把 Issue 标为 closed。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无。页面、规则和验收没有变化 | 不改业务正文，避免把未选技术写进需求 | 维持现有实施视图 |
| ROADMAP.md | 有。任务计数和业务库决定需要可见 | 写明业务库为 MySQL 8，向量库与模型仍待决，页面顺序不变 | model-choice-2 / 2026-10-12 |
| ARCHITECTURE.md | 有。架构约束改为已选 MySQL 8，向量库未选 | 当前实施段写明 MySQL 8 无向量检索，pgvector 不再同库，测试仍用内存 | model-choice-2 / 2026-10-12 |
| issues/index.md / ISSUE-010.md | 有。新的 blocked 决定 | 登记选项、项目经理建议和 15 个未决问题 | blocked；未合入、未发布 |
| ISSUE-005 | 有回链，无门禁结论变化 | 写明业务库已决定为 MySQL 8，建议未采纳；DG-01～06 与本门禁仍未关闭 | 仍 blocked |
| TASK_BOARD.md / tasks/AI-M0.md | 有。新增 AI-01 | 状态 blocked，交付记录已存在并说明未完成原因 | 等待用户 |
| PROJECT_STATUS.md | 有。进度不能隐藏这项等待 | 单列待用户决定，不把它写成已选型 | 2026-10-12 |
| DOCUMENT_INDEX.md | 有。新增维护文档 | 登记 Issue、任务、交付和本同步记录 | 2026-10-12 |
| 产品参考 PRD/字典 | 无。参考原文不因待决项改写 | 未修改 `docs/reference/` | 保持原文 |
| 生产数据库和真实模型 | 业务库已决定，向量库和模型未实现 | 用户于 2026-10-12 决定业务库为 MySQL 8（user decision, relayed by PM）。MySQL 8 无向量检索，向量库不再与业务库同库，pgvector 不再作为同库选项。向量库、对话模型、嵌入和重排仍待决。本记录不引入驱动或迁移，单元测试仍用内存 | 决定已登记；Issue 整体仍 blocked |
| PROJECT_BRIEF.md | 有。2026-10-12 的排期行原先未登记 | 提交 0c60842 把排期从 340 项（18 done、8 in-progress、266 planned、48 blocked）改为 342 项（19 done、8 in-progress、266 planned、49 blocked），并写上 AI-01 等待、AI-02 已本地验收。原因是接手 brief 的计数要和任务看板一致，且不回退该句。本行补登该变更。随后改为 343 项中 18 done、8 in-progress、2 in-review、266 planned、49 blocked：AI-02 与 T008 均为 in-review，并保留 REV-M0-T05；业务库写明为 MySQL 8 | 2026-10-12；已登记，不回退 |

以上只代表 2026-10-12 的核对。业务库决定不关闭本 Issue。向量库、对话模型、嵌入、重排和内网验证仍须用户决定。
