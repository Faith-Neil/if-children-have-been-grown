为什么有这个文件：记录路由分包核对了哪些基线。

它解决什么问题：避免只改加载方式，却不说明哪些基线故意没改。

# ISSUE-020 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。业务标识 route-chunks-1。ISSUE-020 与 APP-M2-T001 均为 in-review，不标 done 或 closed。任务仍是 350 项：20 done、4 in-review、7 in-progress、266 planned、49 blocked、4 ready。本轮不新增任务卡。AI-02 与 APP-M2-T008 已由项目经理标为 done，本轮不改回。BE-M0-T02、BE-M0-T03 与 ISSUE-005 的 in-review 属于错误体与幂等那一轮，本轮不改。

| 对象 | 实际处理 |
|---|---|
| PRD | 无正文修改。第19行仍写 T001 已开工、其余 258 卡 planned。第21行仍写整个 T001 未完成 |
| ROADMAP | 无正文修改。第17行仍写 344 项、20 done、7 in-progress、2 in-review。第19行仍写接下来补 ProLayout。看板已是 350 项，本轮不回头改路线图 |
| ARCHITECTURE | 无正文修改。第21行仍写布局和路由继续本卡。第27行的 ISSUE-016 内存检索是另一张卡，本轮不改 |
| PROJECT_BRIEF | 无正文修改。第30行现为 350 项：20 done、4 in-review、7 in-progress、266 planned、49 blocked、4 ready。第68行仍写接下来补布局组件。该排期行由错误体与幂等那一轮写入 |
| Issue 看板/详情 | ISSUE-020 新建为 change / in-review。ISSUE-011 与 ISSUE-012 保持项目经理已 closed。ISSUE-016 保持检索骨架 in-review。ISSUE-017 至 ISSUE-019 在本仓库尚无详情文件 |
| TASK_BOARD | 不新增任务，不改 350 项计数。补充 ISSUE-020 为 in-review |
| PROJECT_STATUS | 记录首屏主块已降到 315.94 kB，未写 done，未写已发布。保留 AI-02 与 T008 的 done |
| DOCUMENT_INDEX | 登记本同步表、Issue、交付、代码解释和验证记录 |
| WORKFLOW | 无规则变化，治理块不升版 |
| 参考原文 | 不改 `docs/reference/` |
| 后台 | 不改 `backend/` 与 `tests/backend/` |

PR #3 仍待合入。本轮不新建 PR，不合并，不发布。

## 项目经理关闭

QA 签署提交 `dcca509`，记录为 REV-M0-T15。项目经理授权后，ISSUE-020 标为 closed。关联卡 APP-M2-T001 已为 done。不新增任务卡。不改后台，不改 `docs/reference/`，不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。
