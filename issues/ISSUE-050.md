为什么有这个文件：登记历史标书与资料库解析设计，避免没有 Issue 就改入库管道。

它解决什么问题：把已确认的方案、补充决定和本次实现范围固定下来。解析代码已写在当前分支，尚未部署到 RAGFlow，也未标完成。

# ISSUE-050：历史标书与资料库按入库管道重新解析

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-050 |
| 类型 | decision |
| 优先级 | P0 |
| 状态 | in-progress |
| 登记日期 | 2026-11-05 |
| 最后更新日期 | 2026-11-05 |
| revision | kb-ingestion-implemented-1 |
| 关联 Task | 未拆卡。实现按已确认的计划直接落在当前分支，未写入任务看板 |
| 关联 PR | 未创建 |
| 本地验收 | 干净检出 `19e8e4d` 上，`test_kb_admin.py`、`test_knowledge_base.py`、`test_technical_sources.py`、`test_history_commitment.py`、`test_outline_generation_start.py` 为 56 passed、1 skipped。未跑全库。未连接 RAGFlow |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 无单独任务交付文档。实现提交见本文件处理记录 |
| 代码 / 流程解释 | 管道、两类数据集、知识库页、写作分组、技术分册出处和历史承诺提示已写入当前分支。设计见 [历史标书与资料库解析设计](../docs/superpowers/specs/2026-11-05-history-bid-ingestion-design.md)，计划见 [实现计划](../docs/superpowers/plans/2026-11-05-history-bid-ingestion.md) |
| 验证记录 | 2026-11-05 干净检出测试如上。假 RAGFlow 测试不能当作真实解析质量 |

## 现象与证据

知识库页目前只上传历史标书。后台还维护资料与方案片段、资质证书两类数据集。历史标书管道会生成招标式问法，并抽取采购人、行业和项目类型。用户确认按历史标书解析方案重做这条管道，并增加资料库数据集。对话里的决定只作为该方案的补充。

## 影响与分流

- 影响后续的入库管道、知识库页、正文检索和技术分册矩阵。关联 [ISSUE-043](ISSUE-043.md) 的知识库管控，以及 [ISSUE-047](ISSUE-047.md) 的历史标书做法。招标文件的 `tender` 管道不在本次范围。
- 实现已落在分支 `feat/iss-047-technical-volume-mvp`，止于提交 `19e8e4d`。未调用本机或虚拟机 RAGFlow，未把分块或向量拷去虚拟机，未改任务看板计数，未标 done。
- 真实 Recall@5 / MRR@10 仍要等用户明确要求部署后再测。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| 未拆卡 | 用户确认设计说明后再拆 | 见设计说明第 6 节 | 设计说明中的六条代码完成条件 | 未建卡 |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 设计说明写明方案正文和补充决定，并标明补充覆盖方案的位置 | 已写入设计说明。用户尚未审阅文件 |
| AC-02 | 设计说明中的六条代码完成条件有测试证据 | 干净检出 `19e8e4d`：上述五份后端测试 56 passed、1 skipped。前端 `kb-admin-core` 单测在更早的干净文件上 5 passed。未跑全库，未连接真实 RAGFlow |
| AC-03 | 不把假 RAGFlow 测试写成真实解析已验收 | 保持。本次没有调用 RAGFlow |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 待评估。解析代码已在分支，本次仍不改 PRD 正文 | `docs/PRD.md` | kb-ingestion-implemented-1 / ISSUE-050 / 2026-11-05 | 已核对，未改正文 |
| ROADMAP | 待评估。同上 | `docs/ROADMAP.md` | 同上 | 已核对，未改正文 |
| ARCHITECTURE | 待评估。同上 | `docs/ARCHITECTURE.md` | 同上 | 已核对，未改正文 |
| TASK_BOARD | 无影响。未拆任务卡，看板计数不变 | `docs/TASK_BOARD.md` | 同上 | 已核对，未改 |
| PROJECT_STATUS | 有影响。工作区里该文件另有未提交修改，本提交不并入 | `docs/PROJECT_STATUS.md` | 同上 | 待与其他工作区修改一起提交 |
| DOCUMENT_INDEX | 有影响。设计与计划已登记。索引文件另有未提交修改，本提交不并入 | `docs/DOCUMENT_INDEX.md` | 同上 | 待与其他工作区修改一起提交 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-11-05 | kb-ingestion-design-1 / new | 用户确认设计口径。已写设计说明。下一步：用户审阅该文件，通过后再写实现计划 | 对话确认 |
| 2026-11-05 | kb-ingestion-plan-1 / new | 用户确认设计说明。已写实现计划。管道键定为 materials。尚未执行 | [实现计划](../docs/superpowers/plans/2026-11-05-history-bid-ingestion.md) |
| 2026-11-05 | kb-ingestion-implemented-1 / in-progress | 计划六段已写入分支，后续提交补上写作路径接线，并把承诺提示的快照 id 固定到当前生成结果。干净检出测试 56 passed、1 skipped。未部署 | 提交 `69f9c07` 至 `19e8e4d` |
| 2026-11-05 | kb-ingestion-parse-fix-1 / in-progress | 对照四份原件后，表格正文没有进入切块，问法仍被画布打开。工作区已把历史标书和资料库的 PDF、DOC、DOCX 改为表格并入正文、去掉目录，并显式关闭问法。本机 RAGFlow 画布已更新，四份文件已开始重新解析。解析质量尚未复测，未标完成 | 设计说明 §2.1、§2.3 |

## 本地验收与后续合入发布

- 本地验收结论与日期：2026-11-05，分支内实现已测通上述文件。未部署，未标完成。
- 验证方式：设计登记不运行解析测试。
- 六份基线同步：PRD、ROADMAP、ARCHITECTURE、TASK_BOARD 未改，原因见上表。PROJECT_STATUS 与 DOCUMENT_INDEX 已更新。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
