为什么有这个文件：登记全站性能根治、招标检索项目隔离、四库老格式 `.doc` 补齐与公司三机内网部署底座的工程变更。

它解决什么问题：高频接口在 MySQL 模式下沿事务边界全库加载项目、章节正文与历史版本，导致会话、项目列表、公司设置和项目详情随数据量变慢；共享招标数据集若未按本项目 `document_ids` 过滤会产生同公司项目串检索风险；四库上传不接收 `.doc`；现有部署文件未完整固化三机生产底座。

# ISSUE-055：全站性能根治、隔离与四库 .doc 补齐、公司服务器部署底座

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-055 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | in-progress |
| 登记日期 | 2026-11-26 |
| 最后更新日期 | 2026-11-26 |
| revision | perf-isolation-deploy-r1 |
| 关联 Task | [BE-PERF-HOTPATH-MYSQL](../docs/tasks/BE-M0.md#be-perf-hotpath-mysql)、[BE-PROJECT-LIST-PAGING](../docs/tasks/BE-M0.md#be-project-list-paging)、[AI-TENDER-ISOLATION-DOC](../docs/tasks/AI-M0.md#ai-tender-isolation-doc)、[OPS-M0-T04](../docs/tasks/OPS-M0.md#ops-m0-t04) |
| 关联 PR | 未创建 |
| 本地验收 | 未执行 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 待补：`docs/delivery/BE-PERF-HOTPATH-MYSQL.md`、`docs/delivery/BE-PROJECT-LIST-PAGING.md`、`docs/delivery/AI-TENDER-ISOLATION-DOC.md`、`docs/delivery/OPS-M0-T04.md` |
| 代码 / 流程解释 | 待补：对应 `docs/code/` 代码说明 |
| 验证记录 | 待补：改造前后真实 MySQL 接口耗时、聚焦回归、OpenAPI、前端类型检查与治理检查 |

## 现象与证据

用户 2026-11-26 明确要求基于 `milestone/issue-054-tv-mvp` 切出 `feat/iss-055-perf-isolation-deploy`：本轮不引入 Redis，保持单 worker + 线程池 + MySQL 架构；先采集改前基线并核实招标检索与二级索引，再实施性能、隔离、`.doc` 转换与三机部署底座，最后真机复测并提 PR 不合并。

待核实重点：

1. `backend/bid-core/icg/api/session.py` 的 `/api/v1/session` 在 `async def` 中同步读取完整仓储快照。
2. `backend/bid-core/icg/infra/repositories/mysql_repository.py` 的 `_load_shared` 每次读取全部 `demo_project`、`demo_chapter.content`、`demo_chapter_version.content` 与 `demo_state_entry` 元数据，热路径缺少按作用域读取。
3. `backend/bid-core/icg/domain/technical_tender_index.py` 复用 `${company_id}::tender` 时检索是否始终传入当前项目 `document_ids`。
4. `backend/bid-core/icg/domain/kb_admin.py` 四库 `.doc` 上传是否接入 `office_pdf.py` 的 LibreOffice 无头转换。
5. `deploy/` 已有早期 Docker 文件，但需要核对是否满足三机生产架构、LibreOffice 中文字体、健康检查与外部 MySQL/RAGFlow 配置。

## 影响与分流

- 影响范围：后端会话/鉴权、项目列表与详情、MySQL 仓储和迁移、招标检索隔离、知识库四库上传预处理、部署底座、OpenAPI 契约与前端类型。
- 不引入 Redis，不增加 worker，不改变单进程后台作业模型；不伪造真实 RAGFlow 或真实模型验证。
- 涉密与租户隔离红线不变；知识库测试不往生产 RAGFlow 留脏文档。
- 依赖：本机真实 MySQL 可达；真实 RAGFlow 验证仅按既有门控与既有配置执行。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| [BE-PERF-HOTPATH-MYSQL](../docs/tasks/BE-M0.md#be-perf-hotpath-mysql) | 改前基准、会话阻塞修复、热路径按作用域精确查表、二级索引迁移实跑 | `icg/api/session.py`、`icg/infra/repositories/mysql_repository.py`、`alembic/versions/` | 改前/改后四接口毫秒对比；索引迁移在真实 MySQL 通过；列表/设置/鉴权不加载章节正文与历史版本 | in-progress |
| [BE-PROJECT-LIST-PAGING](../docs/tasks/BE-M0.md#be-project-list-paging) | `last_accessed_at`、项目列表分页排序筛选与载荷裁剪 | `demo_project`、项目 schema/API、前端调用兼容 | 默认最近访问倒序；page/page_size/sort/keyword/status 可用；旧客户端兼容 | ready |
| [AI-TENDER-ISOLATION-DOC](../docs/tasks/AI-M0.md#ai-tender-isolation-doc) | 招标检索强制项目 `document_ids`；四库 `.doc` LibreOffice 转换 | `technical_tender_index.py`、`kb_admin.py`、`office_pdf.py` | A/B 项目绝不串检索单测；`.doc` 转换调用链单测 | ready |
| [OPS-M0-T04](../docs/tasks/OPS-M0.md#ops-m0-t04) | 三机生产部署底座 | `deploy/Dockerfile`、`deploy/docker-compose.yml`、`deploy/.env.example`、`deploy/README.md` | LibreOffice headless 与中文字体；单 worker、MySQL 门禁、并发 2、trust_env=False、健康检查与上线清单完整 | ready |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 改前采集 `GET /api/v1/session`、`GET /api/v1/projects`、`GET /api/v1/companies/{id}/settings`、单项目工作台/编辑台详情接口真实 MySQL 耗时与查询行为 | 未执行 |
| AC-02 | `/api/v1/session` 不再在事件循环中同步全库扫描；高频读取按作用域精确查表，不加载全部章节正文和历史版本 | 未执行 |
| AC-03 | 新增 Alembic 二级索引迁移并在真实 MySQL `alembic upgrade head` 实跑通过 | 未执行 |
| AC-04 | 项目列表支持 `page`、`page_size`、`sort`、`keyword`、`status`，默认 `last_accessed_at` 倒序且向后兼容 | 未执行 |
| AC-05 | 招标检索强制按当前项目 `document_ids` 过滤；同公司 A/B 项目隔离单测通过 | 未执行 |
| AC-06 | 四库 `.doc` 上传经 LibreOffice headless 转换为 DeepDoc 支持格式后再推 RAGFlow，调用链单测通过 | 未执行 |
| AC-07 | `deploy/` 固化三机生产底座、健康检查、迁移命令、转换探针与四库初始化自检清单 | 未执行 |
| AC-08 | 改后真实 MySQL 复测并贴出改前/改后对比；聚焦回归、`export_openapi.py --check`、前端 `tsc`、治理检查通过 | 未执行 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 待评估：本轮主要是工程性能、隔离与部署底座，需核对是否改变产品范围或验收口径 | `docs/PRD.md` | perf-isolation-deploy-r1 / ISSUE-055 / 2026-11-26 | 待处理 |
| ROADMAP | 待评估：需核对是否改变里程碑或上线顺序 | `docs/ROADMAP.md` | 同上 | 待处理 |
| ARCHITECTURE | 有影响：MySQL 访问路径、索引、LibreOffice 转换与三机部署约束变化 | `docs/ARCHITECTURE.md` | 同上 | 待处理 |
| TASK_BOARD | 有影响：新增四张任务卡 | `docs/TASK_BOARD.md` | 同上 | 已登记，持续同步 |
| PROJECT_STATUS | 有影响：记录本轮性能与部署开工状态 | `docs/PROJECT_STATUS.md` | 同上 | 已登记，持续同步 |
| DOCUMENT_INDEX | 有影响：新增 Issue、任务交付、代码说明、验证与部署文档条目 | `docs/DOCUMENT_INDEX.md` | 同上 | 已登记，持续同步 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-11-26 | perf-isolation-deploy-r1 / in-progress | 已按用户要求从 `milestone/issue-054-tv-mvp` 对应 main 切出分支并登记 Issue/任务；下一步执行第 0 步核实与改前基准采集 | 用户本轮指令 |

## 本地验收与后续合入发布

- 本地验收结论与日期：待执行。
- 验证方式、通过及失败项、未覆盖范围：待填写。
- 六份基线同步与互链复核：待执行。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
