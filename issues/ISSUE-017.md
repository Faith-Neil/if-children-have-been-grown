为什么有这个文件：登记一份只存在于文档中的内网部署草案。

它解决什么问题：避免在数据库驱动和模型都还没接上时，把部署说明写成已经上线的环境。

# ISSUE-017：内网部署草案

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-017 |
| 类型 | decision |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | intranet-plan-1 |
| 关联 Task | [OPS-M0-T02](../docs/tasks/OPS-M0.md#ops-m0-t02) |
| 关联 PR | 未创建。沿用既有 PR #3 的分支，本轮不新建 PR |
| 本地验收 | 草案已提交复核。开发者停在 in-review，done 待项目经理 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [OPS-M0-T02 交付](../docs/delivery/OPS-M0-T02.md) |
| 代码 / 流程解释 | 无代码影响。没有改运行代码、Dockerfile 或工作流。流程说明即 [部署草案](../docs/operations/intranet-deployment-plan.md) |
| 验证记录 | [草案核对](../docs/testing/2026-10-12-intranet-deploy-plan.md) |

## 现象与证据

合作分支上的后台是 FastAPI/uvicorn 单进程，前端生产形态是 `frontend/web` 的 Vite 构建，由同一进程提供 `dist`。仓库没有内网部署说明。业务库按本轮决定采用 MySQL 8；对话模型、嵌入、重排和向量库仍未选定。

## 影响与分流

- 影响：新增草案、本 Issue、任务卡、交付、核对记录和同步表。
- 不涉及：不创建环境、容器、反向代理配置、密钥或 GitHub Actions 步骤。不把 MySQL service container 加进 `offline-check.yml`。
- 依赖：应用形态以 `backend/bid-core` 与 `frontend/web` 的现有入口为准。ORM、驱动和迁移工具等 ISSUE-018，该编号尚未建档。向量库、对话模型、嵌入和重排继续 blocked 在 [ISSUE-010](ISSUE-010.md)。
- 与 ISSUE-010 的关系：ISSUE-010 已记录业务库为 MySQL 8。本草案按该记录写数据库节，不改 ISSUE-010，也不关闭 AI-01。向量库、对话模型、嵌入和重排仍待决。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| OPS-M0-T02 | 写出内网部署草案，数据库节按 MySQL 8，其余模型项保持未决 | `docs/operations/intranet-deployment-plan.md` | AC-01～AC-04 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 草案按现有 uvicorn、静态 `dist` 和 Vite 构建说明放置方式，并写反向代理、环回端口、健康检查和单进程限制。会话与幂等回执为进程内内存；在 ISSUE-018 落地前只能一个 worker、一个副本，重启即丢失，多 worker 和多副本 blocked 在 ISSUE-018 | 已写入草案第 1～2 节。未实际拉起服务 |
| AC-02 | 配置与密钥只来自环境，仓库不保存密钥；自建 runner 的方向、隔离和作业划分已写明，且没有新工作流 | 已写入第 3～4 节。未安装 runner |
| AC-03 | 备份、回滚和 MySQL 8（utf8mb4、内网、mysqldump 或 XtraBackup 加 binlog 时间点恢复、迁移与回滚的关系）已写明；ORM/驱动/迁移工具指向尚未建档的 ISSUE-018 | 已写入第 5～6 节。没有迁移文件 |
| AC-04 | 向量库只列 Milvus、Qdrant 或公司现有 Elasticsearch；对话模型、嵌入、重排与向量库仍 blocked 在 ISSUE-010。不新增 MySQL service container | 已写入第 6～7 节。`offline-check.yml` 未改 |

未执行的运行验收不能写成通过。本 Issue 因此保持 in-review。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。未改页面、规则或验收口径 | 不改 `docs/PRD.md` | intranet-plan-1 / ISSUE-017 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。未改阶段、依赖或发布顺序。任务计数以看板为准，本轮不改路线图计数字句 | 不改 `docs/ROADMAP.md` | intranet-plan-1 / ISSUE-017 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。草案未改变已实现的模块或接口。运行中的仓库仍是内存 | 不改 `docs/ARCHITECTURE.md` | intranet-plan-1 / ISSUE-017 / 2026-10-12 | 已核对 |
| PROJECT_BRIEF | 无影响。接手快照不改；进度以任务看板为准 | 不改 `docs/PROJECT_BRIEF.md` | intranet-plan-1 / ISSUE-017 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。新增 OPS-M0-T02，状态 in-review | `docs/TASK_BOARD.md`、`docs/tasks/OPS-M0.md` | intranet-plan-1 / ISSUE-017 / 2026-10-12 | 已同步 |
| PROJECT_STATUS | 有影响。记录草案未部署，完成数随看板更新 | `docs/PROJECT_STATUS.md` | intranet-plan-1 / ISSUE-017 / 2026-10-12 | 已同步 |
| DOCUMENT_INDEX | 有影响。登记草案、Issue、交付、核对和同步表 | `docs/DOCUMENT_INDEX.md` | intranet-plan-1 / ISSUE-017 / 2026-10-12 | 已同步 |

治理块保持 g1.1 / 2026-10-11 / ISSUE-007。`docs/reference/` 未改。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | intranet-plan-1 / in-review | 草案写完。没有环境。数据库节跟随 ISSUE-010 已登记的 MySQL 8。向量、模型、嵌入和重排仍待决。done 待项目经理 | [草案](../docs/operations/intranet-deployment-plan.md) |
| 2026-10-12 | intranet-plan-1 / in-review | 按 QA 补上约束：会话和幂等回执是进程内内存。ISSUE-018 的 MySQL 持久化落地前，只能一个 uvicorn worker、一个副本。重启丢失这两类状态。多 worker 和多副本 blocked 在尚未建档的 ISSUE-018 | [草案](../docs/operations/intranet-deployment-plan.md) 第 1～2 节 |

## 本地验收与后续合入发布

- 本地验收结论与日期：2026-10-12 提交 in-review。未标 done。
- 验证方式：对照现有入口核对文档，并运行治理检查。没有连接内网、MySQL 或模型。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
