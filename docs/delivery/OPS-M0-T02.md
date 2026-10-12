为什么有这个文件：记录内网部署草案实际写了什么，以及它还没有变成环境。

它解决什么问题：避免把一份计划说成服务已经在内网运行。

# OPS-M0-T02：内网部署草案

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | OPS-M0-T02 |
| 代码解释 | 无。本卡只新增文档，不改运行代码、Dockerfile 或工作流 |
| 验收 | [草案核对](../testing/2026-10-12-intranet-deploy-plan.md)：对照现有 uvicorn 与 Vite 构建写完五类内容，并写明单 worker、单副本约束。治理检查通过：171 份 Markdown、354 项任务、19 项 Issue。未启动服务，未加 MySQL 容器。卡片为 in-review |
| 项目进度 | 本卡 in-review。354 项中 done 21、in-review 7、in-progress 7、planned 266、blocked 49、ready 4。done 待项目经理 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-10-12；OPS-M0；[ISSUE-017](../../issues/ISSUE-017.md)；[任务卡](../tasks/OPS-M0.md#ops-m0-t02)。
- 分支、提交、PR：`codex/repository-foundation`。不新建 PR。
- 本地验收状态：in-review。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

新增 [内网部署草案](../operations/intranet-deployment-plan.md)。它按当前 `uvicorn` 单进程和 `frontend/web` 的 Vite 构建说明内网放置、环境变量、自建 runner、备份回滚，以及 MySQL 8 的字符集、备份和时间点恢复。深链接由同一进程回到 `index.html`。向量库、对话模型、嵌入和重排仍指向 ISSUE-010。AI-03 的内存检索不代替向量库决定。

按 QA 补上约束：`DemoState.sessions` 和 `workflow_receipts` 都在单个进程的内存里。ISSUE-018 把它们写入 MySQL 之前，只能一个 uvicorn worker、一个副本。重启丢掉会话和幂等回执。多 worker 和多副本部署 blocked 在尚未建档的 ISSUE-018。

没有代码变更。ORM、驱动和迁移工具留给尚未建档的 ISSUE-018。

## 代码解释

无运行时代码。草案说明的是现有入口将来怎么放，不增加新的启动方式。

## 验收结果

核对方式见 [测试记录](../testing/2026-10-12-intranet-deploy-plan.md)。治理检查在提交前执行。没有内网机器、MySQL 或模型端点。

## 项目进度

354 项：done 21、in-review 7（APP-M2-T001、AI-03、BE-M0-T02、BE-M0-T03、REV-M0-T06、REV-M0-T08 与本卡）、in-progress 7、planned 266、blocked 49、ready 4。AI-01 仍 blocked。AI-02 与 APP-M2-T008 保持 done。PR 未合入，未发布。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。页面和验收口径未改。本轮不改 |
| ROADMAP | 无影响。阶段和发布顺序未改。计数字句不在本卡改正 |
| ARCHITECTURE | 无影响。已实现的模块仍是内存单进程。本轮不改 |
| PROJECT_BRIEF | 无影响。接手快照不改 |
| Issue 看板/详情 | 新增 ISSUE-017，状态 in-review。ISSUE-018 不建档。不改 ISSUE-007、ISSUE-010、ISSUE-011 |
| TASK_BOARD / PROJECT_STATUS | OPS-M0-T02 仍为 in-review。354 项：21 done、7 in-review、7 in-progress、266 planned、49 blocked、4 ready |
| DOCUMENT_INDEX | 新增 D-238～D-242。既有条目里的 T008 用词不改 |
| icg-task-mapping | 无影响。本轮不改 |

同步表见 [ISSUE-017-sync](../governance/ISSUE-017-sync.md)。

## 风险与后续

ISSUE-010 已记录业务库为 MySQL 8，向量库、对话模型、嵌入和重排仍未决定，该 Issue 保持 blocked。在驱动落地前，健康检查会继续报告 `persistent: false`。
