为什么有这个文件：记录内网部署草案核对了哪些基线。

它解决什么问题：避免一份部署说明悄悄改掉需求、路线或架构正文。

# ISSUE-017 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。业务标识 intranet-plan-1。

| 对象 | 实际处理 |
|---|---|
| PRD | 无影响。未改范围、页面、规则或验收 |
| ROADMAP | 无影响。未改阶段、依赖或发布顺序。不改计数字句，当前计数以任务看板为准 |
| ARCHITECTURE | 有影响。只把「重排产品未选定」改为 RAGFlow 自带，在 RAGFlow 内配置。已实现的内存仓库和单进程入口不改 |
| PROJECT_BRIEF | 无影响。不改接手快照 |
| Issue 看板/详情 | ISSUE-017 为 closed。依据：用户 10-12 14:34 确认。不改 ISSUE-007、ISSUE-010、ISSUE-011、ISSUE-029。不改 ISSUE-018 的状态 |
| TASK_BOARD | OPS-M0-T02 为 done。本提交后看板为 371 项：38 done、7 in-review、7 in-progress、266 planned、49 blocked、4 ready。之后以任务看板为准 |
| PROJECT_STATUS | 内网部署段改为已确认且未部署。重排改为 RAGFlow 自带。活计数改为 371 项、38 done、7 in-review |
| DOCUMENT_INDEX | 草案、Issue、交付改为 done / closed。D-238 记下 RAGFlow 自带重排 |
| icg-task-mapping | 不改 |
| 参考原文 | 不改 `docs/reference/` |

PR 未创建。未合入，未发布。数据库节跟随 ISSUE-010 已登记的 MySQL 8。2026-10-12 按 QA 补约束：会话和幂等回执为进程内内存，多 worker 和多副本 blocked 在 ISSUE-018。该 Issue 现已建档且为 in-progress，连接和空迁移已提交，回执与会话仍未入库。

2026-10-12 另补 RAGFlow 放置，只改草案、本同步表、ISSUE-017 和核对记录。嵌入和向量库按项目经理转达的用户决定记为 RAGFlow 自带；对话模型记为前端配置页可切换本地或云端；生产生成服务不出网。不关闭 ISSUE-010。

用户 10-12 14:34 确认本草案。ISSUE-017 改为 closed，OPS-M0-T02 改为 done。重排定为 RAGFlow 自带的重排器，重排模型在 RAGFlow 内配置。不改 ISSUE-029。未部署，未合入。

仍开放、本轮不改的事项：

- 重排已经决定：使用 RAGFlow 自带的重排器，重排模型在 RAGFlow 内配置。这不是待决项。不改 ISSUE-029。
- `issues/ISSUE-010.md` 不在本卡修改。它已 closed，并写明重排不在已关闭的三项决定里，检索设计的提议留在 ISSUE-029。本确认记在草案第 7 节。
- 手工内网联调还是内网自建 runner，草案第 4 节仍列为未选定。本确认不代替那个选择。
- RAGFlow 的版本、资源规格和 API 路径仍待 AI/RAG 计划确认。本草案不发明这些值。
- `docs/governance/WORKFLOW.md` 的 CI 说明未包含现有的错误/幂等探针和已改为必需的 e2e 作业，也没有「CI 不连接真实 RAGFlow」这句。
- `docs/PRD.md` 本轮无页面或规则变化；若产品基线要承认 RAGFlow 适配器和配置页，需另开同步。
- PRD、ROADMAP、PROJECT_BRIEF、icg-task-mapping 与 ISSUE-007 里仍可能有过时的 T008 用词。本轮不改这些文件。
