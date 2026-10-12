为什么有这个文件：记录内网部署草案核对了哪些基线。

它解决什么问题：避免一份部署说明悄悄改掉需求、路线或架构正文。

# ISSUE-017 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。业务标识 intranet-plan-1。

| 对象 | 实际处理 |
|---|---|
| PRD | 无影响。未改范围、页面、规则或验收 |
| ROADMAP | 无影响。未改阶段、依赖或发布顺序。不改计数字句，当前计数以任务看板为准 |
| ARCHITECTURE | 无影响。草案不改变已实现的内存仓库和单进程入口 |
| PROJECT_BRIEF | 无影响。不改接手快照 |
| Issue 看板/详情 | ISSUE-017 保持 in-review，补 RAGFlow 变更记录。不改 ISSUE-007、ISSUE-010、ISSUE-011。不改 ISSUE-018 的状态 |
| TASK_BOARD | 本轮不改。OPS-M0-T02 仍为 in-review。计数以看板为准，不在本表重写旧的 354 项快照 |
| PROJECT_STATUS | 本轮不改。内网部署段仍写向量和模型待决，见下方待项目经理同步的基线 |
| DOCUMENT_INDEX | 本轮不改。D-238 仍只写 MySQL 8 与单副本，未写 RAGFlow |
| icg-task-mapping | 不改 |
| 参考原文 | 不改 `docs/reference/` |

PR 未创建。未合入，未发布。数据库节跟随 ISSUE-010 已登记的 MySQL 8。2026-10-12 按 QA 补约束：会话和幂等回执为进程内内存，多 worker 和多副本 blocked 在 ISSUE-018。该 Issue 现已建档且为 in-progress，连接和空迁移已提交，回执与会话仍未入库。

2026-10-12 另补 RAGFlow 放置，只改草案、本同步表、ISSUE-017 和核对记录。嵌入和向量库按项目经理转达的用户决定记为 RAGFlow 自带；对话模型记为前端配置页可切换本地或云端；生产生成服务不出网。不关闭 ISSUE-010。重排未选定。

留给项目经理的基线同步（本轮按要求未改这些文件）：

- `issues/ISSUE-010.md` 仍写嵌入、重排、向量库和对话模型待决。草案里的 RAGFlow、配置页、Fernet 与 `ICG_SECRET_KEY` 还没有回写到该 Issue。
- `docs/ARCHITECTURE.md`、`docs/ROADMAP.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_BRIEF.md` 仍写向量库和模型待决。
- `docs/DOCUMENT_INDEX.md` 的 D-238 未提及 RAGFlow。
- `docs/TASK_BOARD.md` 的 AI-M0 行仍写向量库和模型待决定。
- `docs/governance/WORKFLOW.md` 的 CI 说明未包含现有的错误/幂等探针、非阻塞 e2e 作业，也没有「CI 不连接真实 RAGFlow」这句。
- `docs/PRD.md` 本轮无页面或规则变化；若产品基线要承认 RAGFlow 适配器和配置页，需另开同步。
- PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF、icg-task-mapping 与 ISSUE-007 里仍可能有过时的 T008 用词。
