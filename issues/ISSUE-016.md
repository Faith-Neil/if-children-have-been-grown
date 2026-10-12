为什么有这个文件：登记检索层的替换口和三条证据候选，并说明它们仍是内存实现。

它解决什么问题：避免在向量库未决定时把检索绑到 MySQL 或 pgvector，或把历史投标当成可附着证据。

# ISSUE-016：检索层内存骨架

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-016 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | retrieval-skeleton-1 |
| 关联 Task | [AI-03](../docs/tasks/AI-M0.md#ai-03) |
| 关联 PR | 未创建 |
| 本地验收 | 开发者已提交复核。2026-10-12 契约 7 项通过。v1 生成失败已是冻结错误体，另加 1 条测试。全后台次数见验证记录。开发者不标 done 或 closed |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [AI-03 交付](../docs/delivery/AI-03.md) |
| 代码 / 流程解释 | [AI-03 代码解释](../docs/code/AI-03.md) |
| 验证记录 | [2026-10-12 验证](../docs/testing/2026-10-12-evidence-candidates.md) |

## 现象与证据

[ISSUE-010](ISSUE-010.md) 已 closed。嵌入与向量库定为 RAGFlow 自带能力。本卡仍是内存实现，不连接 RAGFlow。适配器设计在 [ISSUE-029](ISSUE-029.md)，状态 in-review。

本变更由项目经理指定，只增加可替换的检索口和内存实现。它不连接 MySQL，不引入驱动或迁移，也不选定向量库。

## 影响与分流

- 影响范围：证据候选的三条路径。页面、HTTP 和 `create_app` 不调用本服务。
- 协议在 `ports.py`：`EmbeddingProvider.embed(texts)`、`RerankProvider.rerank(query, docs)`、`VectorStore.upsert` 与 `search`（过滤 `company_id`、`status`、`type`）。
- 内存实现和 `EvidenceCandidateService` 在 `retrieval.py`。路径 A 是已确认资料上的规则；路径 B 先嵌入、再按公司检索、再重排；路径 C 是历史投标，`reference_only` 且不可附着。
- B 或 C 失败，或知识库关闭时，保留 A，并记录跳过原因。失败原因不含资料正文。
- 不新增依赖。测试数据是合成的。
- 状态是 in-review。开发者不把本 Issue 标为 closed，也不把 AI-03 标为 done。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| AI-03 | 检索口与三条证据候选，仅内存实现 | `backend/bid-core/icg_demo/ports.py`、`retrieval.py`、契约测试 | AC-01～AC-05 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 三个协议及按公司、状态、类型过滤的搜索已定义，并各有内存实现 | 见代码解释与契约测试 |
| AC-02 | 不连接 MySQL 或任何向量库，不新增依赖 | `requirements.txt` 未改；服务未挂到 `create_app` |
| AC-03 | A/B/C 三条路径；B 或 C 失败或知识库关闭时回退到 A 并记录原因 | 契约测试覆盖关闭、B 失败和 C 失败 |
| AC-04 | 合成数据覆盖跨公司隔离，历史投标不可附着 | 同公司以外的库、片段和历史不出现；路径 C 的 `attachable` 为 false |
| AC-05 | 现有后台测试，包括 `test_reference_boundaries.py`，仍然通过 | 全后台 309 项通过，见验证记录。本卡不新增错误码 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。没有新的用户可见操作或验收口径 | `docs/PRD.md` 未改 | retrieval-skeleton-1 / ISSUE-016 / 2026-10-12 | 已核对 |
| ROADMAP | 有影响。新增 AI-03，计数从 343 改为 344，页面顺序不变 | `docs/ROADMAP.md` 当前计数与 AI 说明 | retrieval-skeleton-1 / ISSUE-016 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 有影响。写明内存检索口，且不连接已决定的 MySQL 8，向量库仍未选 | `docs/ARCHITECTURE.md` 当前实施段 | retrieval-skeleton-1 / ISSUE-016 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。AI-03 为 in-review，AI-M0 变为 3 项 | `docs/TASK_BOARD.md`、`docs/tasks/AI-M0.md` | retrieval-skeleton-1 / ISSUE-016 / 2026-10-12 | 已核对 |
| PROJECT_STATUS | 有影响。写明检索骨架已提交复核，向量库仍未选 | `docs/PROJECT_STATUS.md` | retrieval-skeleton-1 / ISSUE-016 / 2026-10-12 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、代码、测试、交付和验证 | `docs/DOCUMENT_INDEX.md` | retrieval-skeleton-1 / ISSUE-016 / 2026-10-12 | 已核对 |
| PROJECT_BRIEF | 有影响。排期计数因新增一张 in-review 卡从 343 改为 344 | `docs/PROJECT_BRIEF.md` 排期行。先前 0c60842 与 S2 的句子不回退；本行只追加 AI-03 | retrieval-skeleton-1 / ISSUE-016 / 2026-10-12 | 已核对 |

治理块保持 g1.1 / 2026-10-11 / ISSUE-007。`docs/reference/` 未改。ISSUE-010 已 closed。本卡仍不连接 RAGFlow。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | retrieval-skeleton-1 / in-review | 内存检索口和三条路径已提交复核。未连接 MySQL，未选定向量库。开发者不标完成 | [验证记录](../docs/testing/2026-10-12-evidence-candidates.md) |
| 2026-10-12 | retrieval-skeleton-1 / in-review | 旁路核对：OpenAI 兼容适配器在 `/api/v1` 生成失败时已返回 `{code, message, details, traceId}`，`MODEL_UNAVAILABLE` 为 502，`traceId` 等于 `X-Request-ID`。只加一条测试。本卡没有新错误码，不改码表，不改错误实现 | 同上 |

## 本地验收与后续合入发布

- 本地验收结论与日期：开发者已于 2026-10-12 提交复核。状态保持 in-review，不标 closed。
- 未覆盖：真实 MySQL、真实嵌入、重排和向量库，以及任何页面操作。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。只有项目经理在 QA 签字后可把 AI-03 标为 done。
