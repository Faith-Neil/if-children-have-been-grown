为什么有这个文件：记录内网部署草案实际写了什么，以及它还没有变成环境。

它解决什么问题：避免把一份计划说成服务已经在内网运行。

# OPS-M0-T02：内网部署草案

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | OPS-M0-T02 |
| 代码解释 | 无。本卡只新增文档，不改运行代码、Dockerfile 或工作流 |
| 验收 | [草案核对](../testing/2026-10-12-intranet-deploy-plan.md)：对照现有入口写完放置、密钥、runner、备份和 MySQL 8，并补 RAGFlow 连通。单 worker、单副本约束仍在。未启动服务，未加 MySQL 容器，未连接 RAGFlow。卡片为 in-review |
| 项目进度 | 本卡 in-review。计数以任务看板为准，本轮不改看板。done 待项目经理 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-10-12；OPS-M0；[ISSUE-017](../../issues/ISSUE-017.md)；[任务卡](../tasks/OPS-M0.md#ops-m0-t02)。
- 分支、提交、PR：`codex/repository-foundation`。不新建 PR。
- 本地验收状态：in-review。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

新增 [内网部署草案](../operations/intranet-deployment-plan.md)。它按当前 `uvicorn` 单进程和 `frontend/web` 的 Vite 构建说明内网放置、环境变量、自建 runner、备份回滚，以及 MySQL 8 的字符集、备份和时间点恢复。深链接由同一进程回到 `index.html`。

2026-10-12 补上 RAGFlow：单独的内网服务，版本和资源规格待 AI/RAG 计划确认。后台访问 RAGFlow API，RAGFlow 访问本地模型与嵌入，浏览器不直连。生产生成服务不出网。占位变量是 `ICG_RAGFLOW_BASE_URL` 和 `ICG_RAGFLOW_API_KEY`。模型配置密钥用 Fernet，主密钥为环境变量 `ICG_SECRET_KEY`，不进仓库和数据库。CI 不连接真实 RAGFlow 或真实模型。没有发明 RAGFlow 的 API 路径或版本。ISSUE-010 正文未改。重排未选定。

按 QA 补上约束：`DemoState.sessions` 和 `workflow_receipts` 都在单个进程的内存里。ISSUE-018 把它们写入 MySQL 之前，只能一个 uvicorn worker、一个副本。重启丢掉会话和幂等回执。多 worker 和多副本部署 blocked 在 ISSUE-018。该 Issue 已建档且为 in-progress。

没有本卡的运行代码变更。连接与空迁移已由 ISSUE-018 / ISSUE-023 落地；业务表、回执和会话仍未入库。设置 `ICG_DATABASE_URL` 时进程可以连上 MySQL，读写仍在内存。

## 代码解释

无运行时代码。草案说明的是现有入口将来怎么放，不增加新的启动方式。

## 验收结果

核对方式见 [测试记录](../testing/2026-10-12-intranet-deploy-plan.md)。治理检查在提交前执行。没有内网机器、MySQL 或模型端点。

## 项目进度

本卡保持 in-review。看板计数以 `docs/TASK_BOARD.md` 为准。AI-01 已改为 in-review。PR 未合入，未发布。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。页面和验收口径未改。本轮不改 |
| ROADMAP | 无影响。阶段和发布顺序未改。计数字句不在本卡改正 |
| ARCHITECTURE | 无影响。已实现的模块仍是内存单进程。本轮不改 |
| PROJECT_BRIEF | 无影响。接手快照不改 |
| Issue 看板/详情 | ISSUE-017 保持 in-review，补 RAGFlow 记录。不改 ISSUE-010。不改 ISSUE-018 状态 |
| TASK_BOARD / PROJECT_STATUS | 本轮不改。二者仍可能写着向量库待决，留给项目经理 |
| DOCUMENT_INDEX | 本轮不改。D-238 尚未写 RAGFlow |
| icg-task-mapping | 无影响。本轮不改 |

同步表见 [ISSUE-017-sync](../governance/ISSUE-017-sync.md)。

## 风险与后续

起草时 ISSUE-010 仍写未决定。该 Issue 现已关闭。本卡只在草案中记录 RAGFlow 放置，不实现适配器。健康检查继续报告 `persistent: false`。
