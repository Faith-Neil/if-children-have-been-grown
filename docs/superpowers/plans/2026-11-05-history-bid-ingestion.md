# 历史标书与资料库解析 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按已确认的设计，把历史标书和资料库做成两条 ICG 入库管道，并在写作与技术分册矩阵里分开使用。

**Architecture:** 管道 DSL 仍由 `ragflow_pipelines.py` 生成，部署到当前连接的 RAGFlow。数据集只保留 `history` 与 `materials`。写作提示词按数据集分成两组。历史承诺照写，未被子资料库同领域覆盖时，在章节正文上方给出可关闭的警告提示。

**Tech Stack:** Python 3、FastAPI、现有假 RAGFlow、React、Ant Design、node:test。

## Global Constraints

- 管道键：`history_bid` 与 `materials`。RAGFlow 标题 `icg:{key}:v1:{8位}` 不得超过 32 字符。
- 节点顺序：Parser → Title Chunker → Extractor → Indexer。不接 Token Chunker。
- `enable_vision_enhancement` 为 false。关键词 `top_n` 为 10。不开摘要、问法、标签。
- Title Chunker：`method=hierarchy`，`hierarchy=3`，`chunk_token_cap=1100`，`include_heading_content=true`，`root_chunk_as_heading=false`。
- 索引 `fields=text`，`search_method` 为 embedding 与 full_text，`filename_embd_weight=0.1`。
- 两条数据集只绑定 ICG 管道。部署失败不创建内置 general 数据集。
- 不自动重解析，不删除 RAGFlow 里已有的 `icg-library` 与 `icg-certificate`。
- 不实现待审核、已审核、推荐引用、禁止复用。
- 不调用真实 RAGFlow。假服务测试通过不等于生产解析已验收。
- `tender` 管道保持原样，不出现在知识库配置页。
- 历史上传只接受 `.pdf`、`.doc`、`.docx`。资料库另外接受 `.xls`、`.xlsx`、`.ppt`、`.pptx`。
- 提示文案固定为：「本节有内容来自历史投标承诺，尚未在企业权威资料中核到。历史承诺不代表公司当前一定具备该能力。」

---

### Task 1: 两条管道的 DSL

**Files:**
- Modify: `backend/bid-core/icg/infra/ragflow_pipelines.py`
- Test: `tests/backend/test_kb_admin.py`

**Interfaces:**
- Consumes: 现有 `build_dsl(profile, options) -> dict`
- Produces: `PROFILES["history_bid"]` 与 `PROFILES["materials"]`。Title Chunker 参数含 `chunk_token_cap` 与 `root_chunk_as_heading`。

- [ ] **Step 1: 写会失败的断言**

在 `test_deploy_creates_bid_pipelines_and_binds_datasets` 里，先只改历史管道断言，使它表达新 DSL。把下面三行换成新的断言：

```python
    assert {m["key"] for m in extractor["metadata"]["metadata"]} >= {"project_name", "bid_date", "content_role", "technical_domain"}
    assert "purchaser" not in {m["key"] for m in extractor["metadata"]["metadata"]}
    assert extractor["questions"]["top_n"] == 0
    assert extractor["keywords"]["top_n"] == 10
    assert "关键词提取专家" in extractor["keywords"]["system_prompt"]
    assert chunker["chunk_token_cap"] == 1100
    assert chunker["root_chunk_as_heading"] is False
    assert chunker["hierarchy"] == 3
```

- [ ] **Step 2: 运行并确认失败**

Run: `python -m pytest tests/backend/test_kb_admin.py::test_deploy_creates_bid_pipelines_and_binds_datasets -q`

Expected: FAIL，因为现有 DSL 仍有 `purchaser`、问法 `top_n` 为 2，且没有 `chunk_token_cap`。

- [ ] **Step 3: 改管道定义**

在 `PipelineProfile` 增加 `keywords_prompt: str = ""`。空字符串表示继续用模块级 `KEYWORDS_PROMPT`。

`build_dsl` 的 Title Chunker 参数改为：

```python
        chunker_params = {
            "hierarchy": profile.hierarchy,
            "include_heading_content": profile.include_heading_content,
            "root_chunk_as_heading": False,
            "chunk_token_cap": 1100,
            "levels": groups,
            "method": "hierarchy",
            "outputs": copy.deepcopy(_CHUNK_OUTPUTS),
        }
```

`chunker_form` 写入同样的 `root_chunk_as_heading` 与 `chunk_token_cap`。Extractor 的 keywords prompt 用 `profile.keywords_prompt or KEYWORDS_PROMPT`。`questions.top_n` 对这两条管道为 0。`summary.enabled` 保持 false。`tags.top_n` 保持 0。

把方案中的标题正则作为 `SCHEME_HEADING_GROUP`，放在 `history_bid.heading_groups` 与 `materials.heading_groups` 的第一组。后面仍接现有 `BID_HEADING_GROUPS[1:]`。

`history_bid.metadata_fields` 改为 `project_name`、`bid_date`、`document_type`、`section_type`、`knowledge_type`、`technical_domain`、`content_role`、`reusability`。字段说明里写上设计说明第 2.4 节的取值。删除 `purchaser`、`industry`、`project_type`。`questions_top_n=0`，`keywords_top_n=10`。

新增 `PROFILES["materials"]`：`knowledge_kind="materials"`，文件格式含 pdf、docx、doc、spreadsheet、slides。切块参数与历史标书相同。关键词提示词在历史提示词上把第一条改为「优先提取技术名称、技术参数、标准号和实施措施，不提取投标响应用语。」元数据不含 `project_name` 与 `bid_date`。`document_type` 只允许 product_manual、technical_specification、enterprise_capability、project_case、technical_standard、other。`content_role` 只允许 enterprise_fact、project_case_evidence、general_description、irrelevant_content、unknown。

分类系统提示词按设计说明第 2.4 节写入 Extractor metadata 的字段 description，不另加 RAGFlow 不支持的枚举类型。

`_PARSER_SETUPS` 保持现有 DeepDOC、`flatten_media_to_text=false`、`preprocess=main_content` 和空的 `vlm`。不要打开 `enable_vision_enhancement`。

同时把 `test_settings_change_updates_pipeline_and_requires_if_match` 里的 `questions_top_n: 4` 改成 `keywords_top_n: 10`，断言改为 `extractor["keywords"]["top_n"] == 10` 且 `extractor["questions"]["top_n"] == 0`。否则这份测试在 Task 1 结束后会失败。

- [ ] **Step 4: 再跑同一测试**

Run: `python -m pytest tests/backend/test_kb_admin.py::test_deploy_creates_bid_pipelines_and_binds_datasets -q`

Expected: 本测试里除数据集集合仍是三个以外的新断言通过。数据集集合留到 Task 2。若本测试仍因 `set(result["datasets"])` 失败，说明 Step 3 误改了 `DATASET_KINDS`，先撤回那一处。

- [ ] **Step 5: Commit**

```bash
git add backend/bid-core/icg/infra/ragflow_pipelines.py tests/backend/test_kb_admin.py
git commit -m "Define history and materials ingestion pipelines"
```

### Task 2: 只部署两类数据集，并停止旧同步

**Files:**
- Modify: `backend/bid-core/icg/domain/knowledge_base.py`
- Modify: `backend/bid-core/icg/domain/kb_admin.py`
- Modify: `backend/bid-core/icg/api/kb_admin.py`
- Modify: `tests/backend/test_kb_admin.py`
- Modify: `tests/backend/test_knowledge_base.py`

**Interfaces:**
- Consumes: `PROFILES["materials"]`、`KIND_PROFILE`
- Produces: `DATASET_KINDS == {"history": "icg-history", "materials": "icg-materials"}`。`sync_company` 不再上传。`ensure_dataset` 在管道失败时抛出 `DomainError(502, "PIPELINE_UNAVAILABLE", ...)`，不创建 builtin 数据集。

- [ ] **Step 1: 写会失败的部署断言**

把 `test_deploy_creates_bid_pipelines_and_binds_datasets` 的数据集集合改为：

```python
    assert set(result["datasets"]) == {"history", "materials"}
    assert len(fake.agents) == 2
```

把 `test_falls_back_to_builtin_parser_when_pipelines_unsupported` 改成：

```python
def test_deploy_does_not_bind_builtin_parser_when_pipelines_unsupported(client, fake):
    fake.supports_agents = False
    admin = login(client, ADMIN)
    result = client.post("/api/v1/kb-admin/pipelines/deploy", headers=admin, json={})
    assert result.status_code == 502
    assert result.json()["code"] == "PIPELINE_UNAVAILABLE"
    assert fake.datasets == {}
```

在 `test_knowledge_base.py` 把 `test_confirmed_library_item_is_synced_and_retrievable_by_source_id` 的成功同步断言换成：

```python
    entry, status = _entry(client, headers, "library:" + item["id"])
    assert entry is None
    assert fake.datasets == {}
    assert status["message"] == "资料与方案片段不再同步到知识库。"
```

- [ ] **Step 2: 运行并确认失败**

Run: `python -m pytest tests/backend/test_kb_admin.py::test_deploy_creates_bid_pipelines_and_binds_datasets tests/backend/test_kb_admin.py::test_deploy_does_not_bind_builtin_parser_when_pipelines_unsupported tests/backend/test_knowledge_base.py::test_confirmed_library_item_is_synced_and_retrievable_by_source_id -q`

Expected: FAIL。部署仍返回三类数据集；不支持画布时仍创建 builtin 数据集；确认资料仍被同步。

- [ ] **Step 3: 改数据集与同步**

```python
DATASET_KINDS = {"history": "icg-history", "materials": "icg-materials"}
KIND_PROFILE = {"history": "history_bid", "materials": "materials"}
FILE_KINDS = ("history", "materials")
```

`api/kb_admin.py` 的 `Kind` 与 `FileKind` 改为 `Literal["history", "materials"]`。

`kb_admin.py` 的上传后缀：

```python
UPLOAD_SUFFIXES = {
    "history": (".pdf", ".docx", ".doc"),
    "materials": (".pdf", ".docx", ".doc", ".xls", ".xlsx", ".ppt", ".pptx"),
}
```

`ensure_dataset` 删除 `create_dataset(... parser general ...)` 分支。管道异常时抛出 `DomainError(502, "PIPELINE_UNAVAILABLE", "摄入流程不可用，数据集未建立。")`。`deploy` 遇到该错误时把 502 返回给调用方，不继续创建别的数据集。

`sync_company` 在读到 client 之后立刻返回：

```python
        return {"enabled": True, "uploaded": 0, "deleted": 0, "failed": 0, "unchanged": 0,
                "message": "资料与方案片段不再同步到知识库。"}
```

不调用 `_ensure_dataset`。已有索引里的 library 文档留在 RAGFlow，本函数不删除它们。

`test_knowledge_base.py` 里下列测试改为断言「确认资料、历史类型资料、受限资料、片段发布都不会产生 RAGFlow 文档」：`test_revision_change_replaces_document_and_old_version_is_not_recalled`、`test_history_items_are_reference_only`、`test_restricted_items_need_permission`、`test_async_parsing_reports_parsing_until_refresh`、`test_parse_failure_and_upload_failure_are_recorded_and_retried`、`test_full_sync_repairs_drift_between_index_and_ragflow`、`test_snippet_publish_sync_reflects_real_status`、`test_generation_context_gets_knowledge_candidates_as_pian_not_zheng`。每个测试的检索结果不得包含刚写入的资料 id，`fake.documents` 不新增该资料。

`test_kb_admin.py` 里 `test_certificate_extraction_creates_pending_library_draft` 与对 `library` 种类的上传，改为断言 422，`code` 为 `VALIDATION_ERROR`。

上传 metadata 里如果有非空的 `submitted_on`，写入文档元数据的 `bid_date`，覆盖模型稍后抽出的同名字段。没有人填日期时，保留模型抽出的 `bid_date`。在 `test_history_bid_upload_is_reference_only_and_searchable` 增加一次带 `submitted_on: "2024-03-01"` 的上传，断言文档 `meta_fields["bid_date"] == "2024-03-01"`。

- [ ] **Step 4: 跑这两份测试**

Run: `python -m pytest tests/backend/test_kb_admin.py tests/backend/test_knowledge_base.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/bid-core/icg/domain/knowledge_base.py backend/bid-core/icg/domain/kb_admin.py backend/bid-core/icg/api/kb_admin.py tests/backend/test_kb_admin.py tests/backend/test_knowledge_base.py
git commit -m "Deploy only history and materials datasets"
```

### Task 3: 知识库三个标签页

**Files:**
- Modify: `frontend/web/src/library/kb-admin-core.ts`
- Modify: `frontend/web/src/library/KnowledgeBaseAdminPage.tsx`
- Test: `frontend/web/tests/unit/kb-admin-core.test.mjs`

**Interfaces:**
- Consumes: `KbKind = "history" | "materials"`
- Produces: `KB_UPLOAD_ACCEPT.materials`、`canUploadHistory` 对资料库同样为公司管理员可上传。

- [ ] **Step 1: 写会失败的单测**

在 `kb-admin-core.test.mjs` 增加：

```javascript
import { KB_KIND_LABEL, KB_UPLOAD_ACCEPT } from '../../src/library/kb-admin-core.ts';

test('knowledge page exposes history and materials only', () => {
  assert.deepEqual(Object.keys(KB_KIND_LABEL), ['history', 'materials']);
  assert.equal(KB_KIND_LABEL.history, '历史标书');
  assert.equal(KB_KIND_LABEL.materials, '资料库');
  assert.equal(KB_UPLOAD_ACCEPT.materials, '.pdf,.docx,.doc,.xls,.xlsx,.ppt,.pptx');
  assert.equal(KB_UPLOAD_ACCEPT.history, '.pdf,.docx,.doc');
});
```

- [ ] **Step 2: 运行并确认失败**

Run: `pnpm --dir frontend/web exec node --test tests/unit/kb-admin-core.test.mjs`

Expected: FAIL，`KB_KIND_LABEL` 仍含 library 与 certificate。

- [ ] **Step 3: 改页面**

`KbKind` 改为 `'history' | 'materials'`。标签文案按上面的测试。`KnowledgeBaseAdminPage` 在 `historyOnly` 时的标签顺序为：历史标书、资料库、数据集配置。资料库用 `lockKind="materials"`。设置页删除「使用 ICG 摄入流程」开关。流程表只渲染 `key` 为 `history_bid` 或 `materials` 的行。试查下拉只有「历史标书」和「资料库」，对应 kinds `history` 与 `materials`。

资料库页沿用 `DatasetsTab`：未建立时提示先配置，公司管理员可点「建立资料库数据集」和「上传资料」。

分块元数据用中文显示设计说明第 2.4 节的取值。在 `kb-admin-core.ts` 增加 `metadataValueLabel(key, value)`，未知值原样返回。单测断言 `metadataValueLabel("content_role", "bidder_response")` 为「投标响应」，`metadataValueLabel("technical_domain", "data_security")` 为「数据安全」。

- [ ] **Step 4: 再跑单测**

Run: `pnpm --dir frontend/web exec node --test tests/unit/kb-admin-core.test.mjs`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/web/src/library/kb-admin-core.ts frontend/web/src/library/KnowledgeBaseAdminPage.tsx frontend/web/tests/unit/kb-admin-core.test.mjs
git commit -m "Show history and materials tabs in the knowledge base"
```

### Task 4: 写作提示词分成两组

**Files:**
- Modify: `backend/bid-core/icg/domain/knowledge_base.py`
- Modify: `backend/bid-core/icg/domain/chapter_generation.py`
- Modify: `frontend/web/src/shared/types.ts`
- Modify: `frontend/web/src/editor/WritingInputPreview.tsx`
- Test: `tests/backend/test_knowledge_base.py`

**Interfaces:**
- Consumes: `KnowledgeHit`
- Produces: `KnowledgeHit.dataset_kind: str`、`content_role: str`、`technical_domain: str`。`to_public()` 带这三个字段。提示词标题为下面两个常量：

```python
HISTORY_HEADING = "历史技术方案参考：过去项目中的优秀技术表述和实施方法。"
MATERIALS_HEADING = "企业权威资料：产品说明书、技术参数、企业实际能力等事实依据。"
```

- [ ] **Step 1: 写会失败的测试**

在 `test_knowledge_base.py` 增加测试：上传一份历史 docx 和一份资料库 pdf 后，调用现有写作计划组装函数，断言提示词先出现 `HISTORY_HEADING`，再出现 `MATERIALS_HEADING`，且历史文件名只出现在第一段。

检索默认 kinds 改为 `{"history", "materials"}`。`evidence` 与 `snippet` 仍可传入，但不再有新文档命中。

- [ ] **Step 2: 运行并确认失败**

Run: `python -m pytest tests/backend/test_knowledge_base.py::test_writing_prompt_splits_history_and_materials -q`

Expected: FAIL，测试或函数尚不存在。

- [ ] **Step 3: 实现分组**

`KnowledgeHit` 增加三个带默认值的字段，避免旧构造调用破裂。`search()` 从文件索引的 `dataset_kind` 和文档 `meta_fields` 填入 `content_role`、`technical_domain`。历史文件即使 `content_role == "enterprise_fact"` 也保持 `dataset_kind == "history"`。

`chapter_generation.py` 里原「RAGFlow 检索证据候选切片」一段改为按 `dataset_kind` 输出两个标题。历史段在前。不要把历史片段写进权威资料段。

`RetrievedEvidence` 增加可选的 `dataset_kind`、`content_role`、`technical_domain`。`WritingInputPreview.tsx` 的「知识库候选」按这两个标题分成两组。

`tender_orchestrator.py` 的矩阵检索先不要改，留到 Task 5。写作搜索和编辑台问答的默认 kinds 改为 history 与 materials。

响应矩阵候选增加 route `materials`，标题「资料库（参考）」。`frontend/web/src/project/matrix-core.ts` 里该 route 不可勾选挂接。后端把 `dataset_kind == "materials"` 的命中放进这一组，不放进可挂接的规则匹配。规则匹配仍只读企业资料库已确认记录。

- [ ] **Step 4: 跑测试**

Run: `python -m pytest tests/backend/test_knowledge_base.py::test_writing_prompt_splits_history_and_materials -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/bid-core/icg/domain/knowledge_base.py backend/bid-core/icg/domain/chapter_generation.py frontend/web/src/shared/types.ts frontend/web/src/editor/WritingInputPreview.tsx tests/backend/test_knowledge_base.py
git commit -m "Split writing context into history and materials"
```

### Task 5: 技术分册矩阵同时带上两类出处

**Files:**
- Modify: `backend/bid-core/icg/domain/technical_matrix.py`
- Modify: `backend/bid-core/icg/domain/tender_orchestrator.py`
- Test: `tests/backend/test_technical_sources.py`

**Interfaces:**
- Consumes: `fill_technical_responses(state, workflow, *, model, search)`。`search(clause)` 返回 `list[dict]`，每项含 `score`、`filename`、`quote`、`source`。`source` 缺省时视为 `history`。
- Produces: 行上的 `history_filename`、`history_quote` 仍是最相近的历史做法。新增 `material_sources: list[{"filename": str, "quote": str}]`。

- [ ] **Step 1: 写会失败的测试**

在 `tests/backend/test_technical_sources.py` 增加：

```python
def test_technical_matrix_uses_closest_history_and_keeps_material_sources():
    from icg.domain.technical_matrix import fill_technical_responses
    workflow = {"requirements": {"r1": {"id": "r1", "text": "数据备份", "merged_into": "", "technical_clause": True}}}
    def search(_clause):
        return [
            {"score": 0.4, "filename": "旧标.docx", "quote": "每日增量备份", "source": "history"},
            {"score": 0.9, "filename": "说明书.pdf", "quote": "支持增量备份", "source": "materials"},
            {"score": 0.2, "filename": "更旧.docx", "quote": "每周全量", "source": "history"},
        ]
    fill_technical_responses(None, workflow, model=None, search=search)
    row = workflow["requirements"]["r1"]
    assert row["history_filename"] == "旧标.docx"
    assert row["material_sources"] == [{"filename": "说明书.pdf", "quote": "支持增量备份"}]
    assert row["response_origin"] == "history"
```

再增加一个只有资料库命中的测试：`response_origin == "no_evidence"`，`history_filename == ""`，`material_sources` 仍保存资料库出处。

- [ ] **Step 2: 运行并确认失败**

Run: `python -m pytest tests/backend/test_technical_sources.py::test_technical_matrix_uses_closest_history_and_keeps_material_sources -q`

Expected: FAIL，`material_sources` 不存在，且现有逻辑会把分数最高的资料库当成历史做法。

- [ ] **Step 3: 实现分流**

`fill_technical_responses` 把命中分成 history 与 materials。history 按分数取第一条，调用现有 `_apply_history`。materials 写入 `row["material_sources"]`，不参与偏离判断。没有 history 时调用 `_fail(row, "no_evidence")`，再写上 `material_sources`。

`tender_orchestrator.knowledge_search` 改为：

```python
                    hits, _skip = kb.search(company_id, clause, limit=5, kinds={"history", "materials"})
                    return [{"score": hit.score, "filename": hit.name, "quote": hit.content,
                             "source": hit.dataset_kind} for hit in hits]
```

- [ ] **Step 4: 跑技术分册测试**

Run: `python -m pytest tests/backend/test_technical_sources.py -q`

Expected: PASS。旧测试没有 `source` 字段，仍按历史做法处理。

- [ ] **Step 5: Commit**

```bash
git add backend/bid-core/icg/domain/technical_matrix.py backend/bid-core/icg/domain/tender_orchestrator.py tests/backend/test_technical_sources.py
git commit -m "Keep material sources beside the history approach"
```

### Task 6: 历史承诺警告提示

**Files:**
- Create: `backend/bid-core/icg/domain/history_commitment.py`
- Modify: `backend/bid-core/icg/domain/chapter_generation.py`
- Modify: `frontend/web/src/editor/EditorPage.tsx`
- Test: `tests/backend/test_history_commitment.py`

**Interfaces:**
- Consumes: 片段 dict，含 `dataset_kind`、`content_role`、`technical_domain`、`name`
- Produces: `commitment_notice(chunks: list[dict]) -> dict | None`，返回 `{"message": str, "filenames": list[str]}` 或 None。常量 `NOTICE_MESSAGE` 等于 Global Constraints 里的提示文案。

- [ ] **Step 1: 写会失败的测试**

```python
from icg.domain.history_commitment import NOTICE_MESSAGE, commitment_notice

def test_notice_when_history_commitment_domain_is_not_in_materials():
    notice = commitment_notice([
        {"dataset_kind": "history", "content_role": "project_specific_commitment",
         "technical_domain": "data_security", "name": "旧标.docx"},
        {"dataset_kind": "materials", "content_role": "enterprise_fact",
         "technical_domain": "operation_maintenance", "name": "说明书.pdf"},
    ])
    assert notice["message"] == NOTICE_MESSAGE
    assert notice["filenames"] == ["旧标.docx"]


def test_no_notice_for_wording_only_or_covered_domain():
    assert commitment_notice([
        {"dataset_kind": "history", "content_role": "general_description",
         "technical_domain": "data_security", "name": "旧标.docx"},
    ]) is None
    assert commitment_notice([
        {"dataset_kind": "history", "content_role": "enterprise_fact",
         "technical_domain": "data_security", "name": "旧标.docx"},
        {"dataset_kind": "materials", "content_role": "enterprise_fact",
         "technical_domain": "data_security", "name": "说明书.pdf"},
    ]) is None
```

- [ ] **Step 2: 运行并确认失败**

Run: `python -m pytest tests/backend/test_history_commitment.py -q`

Expected: FAIL，模块不存在。

- [ ] **Step 3: 实现提示**

`commitment_notice` 只查看 `dataset_kind == "history"` 且 `content_role` 属于 `bidder_response`、`project_specific_commitment`、`enterprise_fact` 的片段。资料库里相同 `technical_domain` 的片段算覆盖。没有未覆盖片段时返回 None。

写作快照增加 `history_commitment_notice`。编辑台在章节正文上方渲染一条可关闭的 Alert，文案用 `message`，并列出 `filenames`。关闭后把当前快照 id 记在章节上，同一快照不再显示。快照 id 变化后再次显示。Alert 不写入章节正文，导出不读取这个字段。

正文仍按历史片段生成，本任务不删除或改写历史承诺句子。

- [ ] **Step 4: 跑测试**

Run: `python -m pytest tests/backend/test_history_commitment.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add backend/bid-core/icg/domain/history_commitment.py backend/bid-core/icg/domain/chapter_generation.py frontend/web/src/editor/EditorPage.tsx tests/backend/test_history_commitment.py
git commit -m "Warn when a historical commitment is not covered"
```
