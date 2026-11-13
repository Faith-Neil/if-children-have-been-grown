为什么有这个文件：登记技术分册收口这件已确认的产品决定。

它解决什么问题：后续开发有一个固定入口，避免未登记就改目录、矩阵、正文和偏离表。

# ISSUE-047：技术分册 MVP

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-047 |
| 类型 | decision |
| 优先级 | P0 |
| 状态 | in-progress |
| 登记日期 | 2026-11-03 |
| 最后更新日期 | 2026-11-05 |
| revision | tech-volume-shortest-1 |
| 关联 Task | [TV-M0-T00～T14](../docs/tasks/TV-M0.md)；T00/T08～T14 in-review。下午拍板见 [最短主路径](../docs/decisions/2026-11-05-technical-volume-shortest-path.md) |
| 关联 PR | 不合入 main。[PR #7](https://github.com/Faith-Neil/if-children-have-been-grown/pull/7) 只有决定记录，已关闭。产品线在 `feat/iss-047-technical-volume-mvp`。[PR #8](https://github.com/Faith-Neil/if-children-have-been-grown/pull/8) 是指向 main 的草稿，只为触发检查，禁止合并 |
| 本地验收 | 2026-11-05：§15 工单 0～7 均已实现待签；质量八条/双库/编辑台 UI 单测与 lint 绿；OpenAPI check OK。未标 done |
| 合入 | 不合入 main。集成目标是 `feat/iss-047-technical-volume-mvp` |
| 发布 | 未发布 |
| 交付说明 | `docs/delivery/TV-M0-T01.md` 至 `docs/delivery/TV-M0-T07.md` |
| 代码 / 流程解释 | `docs/code/TV-M0-T01.md` 至 `docs/code/TV-M0-T07.md`。决定见 [技术分册 MVP](../docs/decisions/2026-11-03-technical-volume-mvp.md) |
| 验证记录 | 见各卡交付。旧 `tests/backend/test_technical_only.py` 有 3 项失败，因为技术分册不再接受 txt |

## 现象与证据

新建项目目前会生成「技术方案」「商务响应」等章节，响应矩阵要逐条手选响应方式，编辑台按多章生成。2026-11-03 确认改为只做技术分册：历史标书进本公司 RAGFlow，目录和正文按公司技术人员的两份教程制作，并按招标样表导出技术偏离表。

教程原文：

- [服务方案目录制作教程](../docs/reference/writing/01-服务方案目录制作教程.md)
- [技术标响应教程](../docs/reference/writing/02-技术标响应教程.md)

## 影响与分流

- 影响新建项目的文件、抽取、目录、矩阵、正文、偏离表和内部稿导出。企业资料库与写作档案侧栏隐藏，源码保留。已有两册项目不迁移。
- 产品实现只在 `feat/iss-047-technical-volume-mvp`。main 继续保留两册路径。不把本 Issue 的产品提交合并进 main。
- 依赖已确认的决定正文。没有未关闭的产品问题。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| [TV-M0-T00](../docs/tasks/TV-M0.md#tv-m0-t00) | RAGFlow 招标解析打通（工单 0） | `tender_remote.py`、`tender_orchestrator.py` | 真文件解析成功；失败可见可重试 | in-review |
| [TV-M0-T08](../docs/tasks/TV-M0.md#tv-m0-t08) | 管道去闸门（工单 1） | `tender_orchestrator.py`、`TenderTab.tsx`、`ParseTab.tsx` | 上传后自动解析拟目录；无抽取/矩阵主闸门 | in-review |
| [TV-M0-T09](../docs/tasks/TV-M0.md#tv-m0-t09) | 动态目录唯一确认（工单 2） | `technical_outline.py`、`technical_volume.py`、`OutlineTreeView.tsx` | 1～4 级目录；确认目录唯一闸门；删六段硬模板 | in-review |
| [TV-M0-T10](../docs/tasks/TV-M0.md#tv-m0-t10) | 矩阵后台化 + 覆盖视图（工单 3） | `matrix-core.ts`、`ProjectPages.tsx`、`ProjectHeader.tsx` | 覆盖视图；无整表确认主路径 | in-review |
| [TV-M0-T11](../docs/tasks/TV-M0.md#tv-m0-t11) | 双库 RAG + 审计（工单 4） | `knowledge_base.py`、`technical_rag.py`、`technical_volume.py` | 双库检索审计；缺库提示 | in-review |
| [TV-M0-T12](../docs/tasks/TV-M0.md#tv-m0-t12) | 一键全文 + 质量八条（工单 5） | `technical_quality.py`、`EditorPage.tsx` | 八条抽检；需核对警告；可导出 | in-review |
| [TV-M0-T13](../docs/tasks/TV-M0.md#tv-m0-t13) | 编辑台 UI 精简（工单 6） | `EditorPage.tsx`、`OutlineTreeView.tsx` | 主路径条；工具栏白名单；节状态 | in-review |
| [TV-M0-T14](../docs/tasks/TV-M0.md#tv-m0-t14) | 写作助手双模式（工单 7） | `EditorAssistantPanel.tsx` | 问答写作 / 标书修改；初稿后门控 | in-review |
| [TV-M0-T01](../docs/tasks/TV-M0.md#tv-m0-t01) | 隐藏资料库与写作档案，新建项目固定技术分册 | `frontend/web/src/app/App.tsx`、`CreateProjectModal.tsx` | 侧栏与创建请求 | in-review |
| [TV-M0-T02](../docs/tasks/TV-M0.md#tv-m0-t02) | 知识库只上传历史标书 | `frontend/web/src/library/KnowledgeBaseAdminPage.tsx`、`kb_admin.py` | 历史标书上传 | in-review |
| [TV-M0-T03](../docs/tasks/TV-M0.md#tv-m0-t03) | 招标文件与辅助文件 | `TenderTab.tsx`、`technical_sources.py` | 三种文件与再次抽取 | in-review |
| [TV-M0-T04](../docs/tasks/TV-M0.md#tv-m0-t04) | 按教程抽取技术条款 | `technical_clause_extract.py` | 主观分拆条与空结果说明 | in-review |
| [TV-M0-T05](../docs/tasks/TV-M0.md#tv-m0-t05) | 单章服务方案目录 | `technical_outline.py` | 一章内的二级、三级标题 | in-review |
| [TV-M0-T06](../docs/tasks/TV-M0.md#tv-m0-t06) | 矩阵响应来自历史做法 | `technical_matrix.py` | 本地模型判断偏离，未命中逐条确认 | in-review |
| [TV-M0-T07](../docs/tasks/TV-M0.md#tv-m0-t07) | 按节生成正文并导出技术偏离表 | `technical_volume.py` | 六段正文与样表偏离表 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 决定正文与 2026-11-03 确认口径一致，并链到两份教程 | 已写入决定文件。代码验收未执行 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 有影响。新建项目的主路径改为技术分册。正文仍是两册描述，文首加了决定指针 | `docs/PRD.md` | tech-volume-mvp-1 / ISSUE-047 / 2026-11-03 | 已在集成分支注明，未改两册正文 |
| ROADMAP | 有影响。实施顺序改到 TV-M0。路线图其余段落未改 | `docs/ROADMAP.md` | 同上 | 已在集成分支注明 |
| ARCHITECTURE | 有影响。文首说明新建项目固定技术分册，其余结构未改写 | `docs/ARCHITECTURE.md` | 同上 | 已在集成分支注明 |
| TASK_BOARD | 有影响。T01～T07 已列，状态 in-review | `docs/TASK_BOARD.md` | 同上 | 已核对 |
| PROJECT_STATUS | 有影响。进度写明集成目标不是 main | `docs/PROJECT_STATUS.md` | 同上 | 已核对 |
| DOCUMENT_INDEX | 有影响 | `docs/DOCUMENT_INDEX.md` 的 D-941～D-960 | 同上 | 已核对 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-11-03 | tech-volume-mvp-1 / new | 产品口径已确认并写入决定。代码未改，任务未拆 | 用户确认 |
| 2026-11-03 | tech-volume-mvp-1 / in-progress | T01、T02 为 in-review。T03～T07 仍是 planned。不标 done | 本轮实现 |
| 2026-11-03 | tech-volume-mvp-1 / in-progress | T03 为 in-review。T04～T07 仍是 planned。不标 done | 本轮实现 |
| 2026-11-03 | tech-volume-mvp-1 / in-progress | T04 为 in-review。T05～T07 仍是 planned。不标 done | 本轮实现 |
| 2026-11-03 | tech-volume-mvp-1 / in-progress | T05 为 in-review。T06～T07 仍是 planned。不标 done | 本轮实现 |
| 2026-11-03 | tech-volume-mvp-1 / in-progress | T06 为 in-review。T07 仍是 planned。不标 done | 本轮实现 |
| 2026-11-03 | tech-volume-mvp-1 / in-progress | 历史做法不再默认无偏离。本地模型判断正偏离、负偏离或无偏离。不标 done | 本轮更正 |
| 2026-11-03 | tech-volume-mvp-1 / in-progress | T07 为 in-review。正文六段和样表偏离表已接到导出。不标 done | 本轮实现 |
| 2026-11-05 | tech-volume-shortest-1 / in-progress | 下午拍板最短路径入库。工单 0：招标临时库强制内网嵌入并重建；真 `.doc` 解析成功。不标 done；T05～T07 六段/矩阵闸门口径作废待工单 1～7 修订 | 本轮实现 |
| 2026-11-05 | tech-volume-shortest-1 / in-progress | 工单 1（TV-M0-T08）管道去闸门：自动解析拟目录、自动 parse_confirmed、去掉抽取/进矩阵主闸门。不标 done | 本轮实现 |
| 2026-11-05 | tech-volume-shortest-1 / in-progress | 工单 2（TV-M0-T09）动态目录 1～4 级；删六段/教程六块硬编码；矩阵确认不挡生成。不标 done | 本轮实现 |
| 2026-11-05 | tech-volume-shortest-1 / in-progress | 工单 3（TV-M0-T10）覆盖视图；去掉整表确认主路径。不标 done | 本轮实现 |
| 2026-11-05 | tech-volume-shortest-1 / in-progress | 工单 4（TV-M0-T11）双库 RAG + 审计；工单 5（TV-M0-T12）质量八条。不标 done | 本轮实现 |
| 2026-11-05 | tech-volume-shortest-1 / in-progress | 工单 6（TV-M0-T13）编辑台 UI；工单 7（TV-M0-T14）写作助手双模式。§15 0～7 待签，不标 done | 本轮实现 |
| 2026-11-03 | tech-volume-mvp-1 / in-progress | 集成目标改为 `feat/iss-047-technical-volume-mvp`，不合并 main。PR #7 已关闭。PR #8 是禁止合并的草稿。T01～T07 仍为 in-review | 本轮分支策略 |

## 本地验收与后续合入发布

- 本地验收结论与日期：2026-11-03，内存测试通过，不能当作已上线。
- 验证方式、通过及失败项、未覆盖范围：`tests/backend/test_technical_sources.py` 12 项通过；`export_openapi.py --check` 通过。浏览器未点。公司 RAGFlow 和本地 Qwen 未接。`tests/backend/test_technical_only.py` 3 项失败（仍上传 txt）。治理检查仍有 37 条既有断链。
- 六份基线同步与互链复核：PRD、路线图、架构只加了指向决定的句子。看板、项目状态、文档索引和本 Issue 已写明集成分支。
- PR 状态：PR #7 已关闭，不合并。产品在 `feat/iss-047-technical-volume-mvp`。[PR #8](https://github.com/Faith-Neil/if-children-have-been-grown/pull/8) 是草稿，只触发检查，禁止合并。
- 合入提交与日期：不合入 main。
- 发布版本与日期：未发布。
