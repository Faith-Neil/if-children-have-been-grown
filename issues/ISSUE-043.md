为什么有这个文件：登记公司知识库（RAGFlow）同步与检索未接入生产链路、片段同步结果伪造的问题。

它解决什么问题：防止把“AI-RAGFLOW-KB-SYNC done”当成知识库已可用；生产写作此前从未检索公司资料库，检索质量也从未度量。

# ISSUE-043：知识库同步与检索未接入生产链路

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-043 |
| 类型 | bug |
| 优先级 | P0 |
| 状态 | in-review |
| 登记日期 | 2026-10-28 |
| 最后更新日期 | 2026-10-28 |
| revision | 1 |
| 关联 Task | [AI-KB-RAG-PIPELINE](../docs/tasks/AI-M0.md#ai-kb-rag-pipeline)、[AI-KB-RAG-EVAL](../docs/tasks/AI-M0.md#ai-kb-rag-eval)；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) |
| 本地验收 | 开发自测通过（假服务）；真实 RAGFlow 评测待执行 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [交付](../docs/delivery/AI-KB-RAG-PIPELINE.md) |
| 代码 / 流程解释 | [代码说明](../docs/code/AI-KB-RAG-PIPELINE.md) |
| 验证记录 | [Wave 12 开发自测](../docs/testing/2026-10-28-wave-12-verification.md) |

## 现象与证据

- `main.py` 构造 `EvidenceCandidateService` 时不带数据集，`project.dataset_ids` 从未被设置，路径 B/C 永远跳过；问答卡、编辑器调用的 `evidence_service.search` 不存在（异常被吞掉）。
- `SnippetRetriever` 丢弃 RAGFlow 分块，且过滤掉 UUID 数据集。
- 资料确认、改版、过期、删除都不触发同步，也没有“资料 → 文档”映射，旧版本与已撤销资料会一直留在知识库里被召回。
- 片段 `/sync` 端点只改内存状态即返回 synced；生产代码含 `[[sync-fail]]` 测试钩子。
- 客户端按 RAGFlow 0.x 契约编写，对 1.0（实测 v1.0.0-rc2）建库缺 `parse_type`、状态字段为 `ingestion_status`。
- 前端片段筛选值 `sync_failed` 与后端 `failed` 不一致。

## 影响与分流

- 影响：PRD 要求的“基于公司资料写作”在生产中不成立；若直接接通而不做映射与实时复核，会召回过期或已撤销资料，违反原则 1。
- 处理：AI-KB-RAG-PIPELINE 已实现对账同步、索引过滤与实时复核检索并接入各调用方（in-review）；AI-KB-RAG-EVAL 在真实 RAGFlow 上评测并定参数（in-progress，等待用户恢复隧道）。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| AI-KB-RAG-PIPELINE | 同步、检索、接入、界面 | `icg/domain/knowledge_base.py`、`icg/api/knowledge_base.py`、前端资料库页 | `test_knowledge_base.py` 13 项 | in-review |
| AI-KB-RAG-EVAL | 真实 RAGFlow 评测与调参 | `scripts/rag_eval.py`、`tests/rag_eval/` | 报告落 `docs/testing/` | in-progress |

## 六份基线评估

| 基线 | 评估 | 理由与路径 |
|---|---|---|
| PRD | 无影响 | 实现缺口；“检索命中只是 [片] 候选”已在 PRD 原则 1 与 §5.7 内 |
| ROADMAP | 无影响 | 阶段不变 |
| ARCHITECTURE | 有影响 | 新增知识库同步/检索模块，见代码说明 |
| TASK_BOARD | 有影响 | 新增两张卡 |
| PROJECT_STATUS | 有影响 | 如实记录 |
| DOCUMENT_INDEX | 有影响 | 登记交付与本 Issue |
