# AI-OUTLINE-GENERATE-EXPAND 交付报告：章节写作方案多段落结构化批量生成引擎

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-OUTLINE-GENERATE-EXPAND |
| 代码解释 | [docs/code/AI-OUTLINE-GENERATE-EXPAND.md](../code/AI-OUTLINE-GENERATE-EXPAND.md) |
| 验收 | 11 项专属自动化测试全绿（11 passed in 1.15s）；全量 AI 与 RAG 联合套件全绿（156 passed, 2 skipped in 54.86s）；OpenAPI 契约零漂移；工程治理检查通过（零死链） |
| 项目进度 | 本卡已完成全部功能开发与全量测试闭环，状态转为 in-review，建议由 QA 与 PD 终验后由 PM 标 done |
<!-- task-delivery:end -->

## 1. 交付目标对照

依据任务派发要求与系统规范（PRD MVP v1.8 §5.7.2《章节写作方案生成》与 §5.7.8《多段落结构化批量生成引擎》）：
- **目标**：在 `backend/bid-core/icg/domain/chapter_generation.py`、`domain.py`、`generation_orchestrator.py` 与 `backend/bid-core/icg/api/workflow.py` 中，落地章节写作方案多段落结构化批量生成引擎。
- **交付要点对照**：
  1. **结构化段落分块与要点小标题映射（parse_structured_paragraphs）**：
     - 将大模型生成的原始正文精准解析为带有 `[P1]`~`[Pn]` 编号、段落标签、小标题与引用绑定的结构化段落列表；
     - 每一段携带独立 `id`、`paragraph_id`、`order`、`label`（`[P1]`）、`subheading`（Markdown 标题行）、`title`（清洗后的标题纯文本）、`text`（干净正文）、`content`（带标签格式）、`scoring_point`（对齐的评分要点）、`variables`（抽取的变量名列表，如 `fact:fact-rto`）与 `char_length`（字符数统计）；
     - 当大模型生成未携带显式 `[Pn]` 标签时，引擎自适应按段落顺序分配标签并与写作要点对齐；
  2. **引用标记提取与幻觉校验（extract_paragraph_citations）**：
     - 从段落正文中精准识别行内 `[证:xxx]`（公司证据）与 `[片:xxx]`（知识库/招标文件切片）标记；
     - 严格对照入参允许的 `allowed_evidence_ids` 与 `allowed_snippet_ids` 白名单进行校验，对于白名单外的虚构引用直接标注 `valid=False`，防止模型幻觉虚构证据或切片；
  3. **结构化 Markdown 章节正文格式化回写（format_structured_chapter_content）**：
     - 将结构化段落列表逆向还原为干净规范的 Markdown 章节正文，支持小标题按层级聚合呈现，避免重复输出标题；
  4. **单章同步生成产物增强（start_chapter_generation enriches candidate）**：
     - 在 `start_chapter_generation(sync_execute=True)` 链路中，自动对模型生成正文执行结构化解析，将 `paragraphs`、`structured_content`、`scoring_subheadings` 存入候选产物 `candidate` 及结果字典；
  5. **跨章节独立批量生成（batch_generate_chapters）**：
     - 支持对项目下指定的多个章节一次性批量启动生成；
     - **PRD §5.7.8 关键红线**：未确认分册或未确认章节绝对不阻塞已确认章节的独立启动。批量执行循环中，未确认方案或方案过期的章节独立记入 `failed_chapters[cid]`（错误码 `PLAN_NOT_CONFIRMED`），其余已确认方案的章节正常启动生成并生成独立任务；
     - 自动汇聚各章节的异步任务 `jobs`、上下文防伪指纹 `fingerprints` 及全局 Token 预算消耗统计 `token_budget_usage_summary`；
  6. **内网物理隔离与涉密项目硬门禁（Airgap Boundary）**：
     - 涉密项目（`sensitive=True`）强制使用本地离线模型配置，企图调用云端模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
  7. **角色权限与租户隔离**：
     - 系统只读角色（`viewer`、`auditor` 等）与只读项目成员拦截 403 `FORBIDDEN` / `PROJECT_WRITER_REQUIRED`；
     - 跨租户项目请求拦截 404 `NOT_FOUND`；
  8. **API 端点集成与 OpenAPI 零漂移**：
     - 在 `backend/bid-core/icg/api/workflow.py` 中注册 `POST /api/v1/projects/{project_id}/chapters/batch-generate` 端点，配置 `include_in_schema=False`，严格维护既有 143 个错误码与契约文本 100% 零漂移。

---

## 2. 交付物清单

### 2.1 核心代码
- `backend/bid-core/icg/domain/chapter_generation.py`：
  - 新增 `parse_scoring_points(writing_points)`：支持字符串与列表形式评分要点的规范化清洗；
  - 新增 `extract_paragraph_citations(text, allowed_evidence_ids, allowed_snippet_ids)`：行内引用胶囊提取与白名单防幻觉核验；
  - 新增 `parse_structured_paragraphs(raw_content, scoring_points, allowed_evidence_ids, allowed_snippet_ids)`：`[P1]`~`[Pn]` 多段落结构化解析引擎；
  - 新增 `format_structured_chapter_content(paragraphs)`：结构化段落 Markdown 格式化引擎；
  - 更新 `ChapterGenerationService.start_chapter_generation`：同步执行模式下自动注入 `paragraphs`、`structured_content`、`scoring_subheadings`；
  - 新增 `ChapterGenerationService.batch_generate_chapters`：批量章节生成编排入口，支持多章独立并行容错、门禁过滤、预算与指纹汇聚；
  - 提供模块级快捷入口 `batch_generate_chapters`；
- `backend/bid-core/icg/domain/domain.py`：在 `DemoService` 暴露 `batch_generate_chapters` 顶层统一门面；
- `backend/bid-core/icg/domain/generation_orchestrator.py`：在 `GenerationOrchestratorMixin` 暴露 `start_chapter_generation` 与 `batch_generate_chapters`；修复 `WorkflowService` MRO 继承顺序；
- `backend/bid-core/icg/domain/generation_context.py`：增强 `refuse_source_change` 与检索查询对列表型 `writing_points` 的自适应支持；
- `backend/bid-core/icg/domain/workflow_schemas.py`：新增 `BatchGenerateChaptersRequest` 请求模型；
- `backend/bid-core/icg/api/workflow.py`：注册 `POST /api/v1/projects/{project_id}/chapters/batch-generate`（`include_in_schema=False`）。

### 2.2 自动化测试
- `tests/backend/test_ai_outline_generation_expand.py`：11 项专属自动化测试，全绿通过。

---

## 3. 验证命令与结果

### 3.1 专属自动化测试套件
```powershell
pytest tests/backend/test_ai_outline_generation_expand.py -v
```
**运行结果**：
```text
tests/backend/test_ai_outline_generation_expand.py::test_parse_structured_paragraphs_with_explicit_labels PASSED [  9%]
tests/backend/test_ai_outline_generation_expand.py::test_parse_structured_paragraphs_without_labels_auto_assigns PASSED [ 18%]
tests/backend/test_ai_outline_generation_expand.py::test_extract_paragraph_citations_and_detect_unverified PASSED [ 27%]
tests/backend/test_ai_outline_generation_expand.py::test_format_structured_chapter_content_roundtrip PASSED [ 36%]
tests/backend/test_ai_outline_generation_expand.py::test_start_chapter_generation_sync_enriches_candidate_paragraphs PASSED [ 45%]
tests/backend/test_ai_outline_generation_expand.py::test_batch_generate_chapters_all_confirmed_success PASSED [ 54%]
tests/backend/test_ai_outline_generation_expand.py::test_batch_generate_chapters_unconfirmed_does_not_block_confirmed PASSED [ 63%]
tests/backend/test_ai_outline_generation_expand.py::test_batch_generate_chapters_sensitive_project_blocks_cloud_model PASSED [ 72%]
tests/backend/test_ai_outline_generation_expand.py::test_batch_generate_chapters_readonly_role_interception PASSED [ 81%]
tests/backend/test_ai_outline_generation_expand.py::test_batch_generate_chapters_cross_tenant_isolation PASSED [ 90%]
tests/backend/test_ai_outline_generation_expand.py::test_http_batch_generate_chapters_endpoint PASSED [100%]

============================= 11 passed in 1.15s ==============================
```

### 3.2 全量 AI 与 RAG 联合测试套件
```powershell
pytest tests/backend/test_accept_ai_suggestion.py tests/backend/test_ai_compliance_cross_check.py tests/backend/test_ai_outline_generation_expand.py tests/backend/test_ai_prompt_budget.py tests/backend/test_ai_snippet_retrieval.py tests/backend/test_editor_ai_context.py tests/backend/test_model_config_glue.py tests/backend/test_model_config_provider.py tests/backend/test_model_config_storage.py tests/backend/test_openai_compatible_model.py tests/backend/test_outline_contract_draft.py tests/backend/test_outline_generation_start.py tests/backend/test_outline_plan_service.py tests/backend/test_tender_document_retrieval.py -q
```
**运行结果**：
```text
156 passed, 2 skipped in 54.86s
```

### 3.3 OpenAPI 契约零漂移核验
```powershell
python backend/bid-core/export_openapi.py --check
```
**运行结果**：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

### 3.4 工程治理与超链接检查
```powershell
node scripts/check-project-governance.cjs
```
**运行结果**：
```text
治理检查通过：574 份 Markdown、423 项任务、38 项 Issue。
```

---

## 4. 真实性、局限性与后续跟进

1. **真实环境与离线解耦**：
   - 生产环境中大模型需使用内网本地部署的 Qwen（如 `qwen2.5-72b`）通过内网 API 驱动；在测试中，自动化单测通过 `MockModelProvider` 与内存仓储模拟模型响应，保证离线 CI 纯净快速运行；
   - 涉密项目与本地模型强绑定门禁（`SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）已在领域层与 API 层严格拦截；
2. **状态流转纪律**：
   - 本卡作为 AI subagent 交付，状态严格标记为 `in-review`，绝不私自标记 `done`；
   - 建议由 QA 进行独立复测签署、PD 进行产品业务对照核准后，向人类 PM 推荐并由 PM 正式标 `done`。
