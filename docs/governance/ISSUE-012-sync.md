为什么有这个文件：记录离线 CI 这一变更核对了哪些基线。

它解决什么问题：避免只改工作流，却不说明需求、路线和架构为什么没有改正文。

# ISSUE-012 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。业务标识 offline-ci-1。

| 对象 | 实际处理 |
|---|---|
| PRD | 无影响。未改范围、页面、规则或验收。治理块不改 |
| ROADMAP | 无影响。未改阶段、优先级、依赖或发布顺序 |
| ARCHITECTURE | 无影响。未改模块、状态、接口或部署。CI 只调用现有离线命令 |
| Issue 看板/详情 | ISSUE-012 为 closed，APP-M2-T008 为 done。项目经理于 10-12 12:10 在 QA 签署后确认。合入状态仍是 PR #3 待合入。未改 ISSUE-010、ISSUE-011 |
| TASK_BOARD | APP-M2-T008 为 done。343 项中 done 20、in-review 1、in-progress 7、planned 266、blocked 49、ready 0。AI-02 的 done 保留 |
| PROJECT_STATUS | 保留离线 CI 运行证据。卡片为 done，ISSUE-012 为 closed，未部署、未合入。T001 仍为 in-review |
| PROJECT_BRIEF | 2026-10-12 曾把维护日期改为当天，关联加上 ISSUE-012 / APP-M2-T008，排期计数写成 340 项、18 done。原因是把离线 CI 计入接手说明。随后去掉排期格里重复的「T008离线CI已本地验收」，并把该卡改回 in-review。合入 AI-02 确认后，排期曾是 343 项 19 done、2 in-review、7 in-progress，T008 仍为 in-review，AI-02 已为 done。本次改为 20 done、1 in-review、7 in-progress，并把 T008 改为 done。原因：项目经理于 10-12 12:10 在 QA 签署后确认。剩下的 1 张 in-review 是 T001。不改 ISSUE-010 或 ISSUE-011 |
| DOCUMENT_INDEX | 此前已登记工作流、Issue、交付、代码解释、本同步表和验证记录。本轮不改索引；其中仍有 T008 / ISSUE-012 为 in-review 的条目 |
| WORKFLOW | 第 2 节第 6 步已写明开发者只标 in-review，项目经理已接受该句。治理块不升到 g1.2。依据是 WORKFLOW 开篇「`g1.1`是现有工程规则版本」，第 4 节「其治理块与本流程保持同一版本、日期和 Issue」以及「不能仅复制一个版本号便宣称需求、计划和架构已对齐」，第 1 节「版本更新包括软件、文档业务基线和依赖升级」 |
| ROADMAP | 此前只把 APP-M2-T008 的「已本地验收」改回 in-review。本轮不改。计数字句仍写 T008 为 in-review |
| 参考原文 | 不改 `docs/reference/` |

PR #3 仍待合入。本轮不新建 PR，不合并，不发布。ISSUE-012 的 closed 只表示本地验收，不表示已经合入或上线。
