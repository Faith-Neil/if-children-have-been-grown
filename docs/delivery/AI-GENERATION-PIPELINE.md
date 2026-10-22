# 为什么有这个文件：记录章节 AI 检索生成端到端闭环（ISSUE-037 / ISSUE-028 贯通）的交付成果、测试证据与验收结论。
# 它解决什么问题：汇总代码实现、自动化测试结果与安全门禁验证，供主 Agent 与 QA 团队复核验收。

# 章节 AI 检索生成端到端闭环交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务目标 | AI-M0 真实大模型接入与 RAGFlow 检索闭环（章节生成与建议端到端） |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-028](../../issues/ISSUE-028.md) |
| 代码说明 | [AI-GENERATION-PIPELINE 代码说明](../code/AI-GENERATION-PIPELINE.md) |
| 专属测试套件 | `tests/backend/test_chapter_generation_rag_flow.py`（7 项全部通过） |
| 回归测试结果 | 75 passed, 2 skipped (0 failed) |
| 当前状态 | in-review（待主 Agent / QA 复核，绝不私自标 done，绝不私自关闭 Issue） |
<!-- task-delivery:end -->

---

## 1. 核心交付内容清单

1. **RAGFlow 候选检索链路接入（路径 B/C）**：
   - 在 `EvidenceCandidate` 中新增 `document_id` 与 `chunk_id` 字段，实现片段级精细化 Provenance 追溯。
   - `_path_b_ragflow`（方案切片）与 `_path_c_ragflow`（历史投标案例）提取并挂载真实的 `document_id` 与 `chunk_id`。
   - `build_generation_context` 在组装上下文时自动聚合章节标题、写作要点与条款文本，调用 `EvidenceCandidateService.collect`，并将路径 B/C 切片沉淀至 `input_snapshot.retrieved_evidence`。

2. **统一 Prompt 快照组装与业务标签规范对齐**：
   - 严格遵循 `business-tags.ts` 规范：
     - 已确认资料库记录标注为 `[证]`；
     - 检索候选切片标注为 `[片]`，并在 Prompt 中明确展示出处 `（chunk_id: ..., document_id: ...）`；
     - 路径 C 补充 `【仅供参考，不得作为正式附着证据】` 标识。
   - Prompt 完整保真保留招标条款、响应内容、经核对的事实变量 `{{fact:...}}` 与服务承诺变量 `{{sla:...}}`。

3. **配置驱动模型提供者与建议/生成闭环**：
   - 在 `DemoService.suggest` 与 `WorkflowService.generate` 中打通 `resolve_model_provider`，支持项目专属绑定模型与公司默认模型动态解析及 API Key 安全注入。
   - 保持两处链路使用同一套 `input_snapshot`，杜绝改写建议与正文生成输入不一致的问题。

4. **严格安全门禁与完整性防篡改拦截**：
   - **敏感项目隔离门禁**：敏感项目配置为云端模型时，在调用大模型前拦截并返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，模型端点零网络外泄。
   - **事实变量防篡改**：模型若遗漏正式正文中的事实变量占位符，触发 409 `FACT_VARIABLE_LOST`；若将事实变量改成手写字面取值，触发 409 `FACT_LITERAL_REPLACEMENT`。
   - **上游故障安全隔离**：模型服务返回 500 或连接超时，转换为 502 `MODEL_UNAVAILABLE`，正式正文绝对不被修改或污染。
   - **知识库关闭门禁**：`knowledge_base_enabled=False` 时，完全跳过 RAGFlow 网络调用，平滑退化为仅依靠已确认证据和事实。

---

## 2. 变更文件清单

- **业务逻辑代码**：
  - `backend/bid-core/icg_demo/retrieval.py`：扩展 `EvidenceCandidate` 增加 `document_id` 和 `chunk_id` 并在路径 B/C 中透传。
  - `backend/bid-core/icg_demo/workflow_schemas.py`：在 `WritingEvidence` 中增加 `tag="[证]"`，在 `WritingInputSnapshot` 中正式声明 `retrieved_evidence` 字段。
  - `backend/bid-core/icg_demo/generation_context.py`：在 `build_generation_context` 中集成 `EvidenceCandidateService`，并在 `render_model_input` 中完成 `[证]`、`[片]` 标签与出处的 Prompt 渲染。
  - `backend/bid-core/icg_demo/domain.py`：`DemoService` 接收并维护 `evidence_service`，并在 `suggest` 中透传至 `build_generation_context`。
  - `backend/bid-core/icg_demo/workflow.py`：`WorkflowService.generate` 与 `writing_input_preview` 透传 `evidence_service`。
  - `backend/bid-core/icg_demo/main.py`：`create_app` 增加 `evidence_service` 参数并在环境检测到 `ICG_RAGFLOW_BASE_URL` 时自动回退装配。
- **测试夹具与测试集**：
  - `tests/backend/fake_openai_chat.py`：扩展支持 `assistant_text` 自定义注入与 200 自定义响应。
  - `tests/backend/test_chapter_generation_rag_flow.py`：新建全流程契约与集成测试套件，涵盖端到端生成、建议、零命中降级、知识库关闭、敏感拦截、防篡改及 502 映射。
- **文档沉淀**：
  - `docs/code/AI-GENERATION-PIPELINE.md`：端到端闭环技术架构与代码设计文档。
  - `docs/delivery/AI-GENERATION-PIPELINE.md`：本交付验收报告。

---

## 3. 自动化测试执行证据

### 3.1 专属端到端测试套件 (`test_chapter_generation_rag_flow.py`)
```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
plugins: anyio-4.14.2
collected 7 items

tests/backend/test_chapter_generation_rag_flow.py::test_end_to_end_chapter_generation_with_ragflow_chunks PASSED [ 14%]
tests/backend/test_chapter_generation_rag_flow.py::test_end_to_end_chapter_suggestion_with_ragflow_chunks PASSED [ 28%]
tests/backend/test_chapter_generation_rag_flow.py::test_zero_hit_ragflow_graceful_fallback PASSED [ 42%]
tests/backend/test_chapter_generation_rag_flow.py::test_knowledge_base_disabled_skips_ragflow_completely PASSED [ 57%]
tests/backend/test_chapter_generation_rag_flow.py::test_sensitive_project_blocks_cloud_model_with_403 PASSED [ 71%]
tests/backend/test_chapter_generation_rag_flow.py::test_model_variable_tampering_blocks_and_preserves_content PASSED [ 85%]
tests/backend/test_chapter_generation_rag_flow.py::test_upstream_model_error_maps_to_502_without_corrupting_official_content PASSED [100%]

============================= 7 passed in 30.92s ==============================
```

### 3.2 跨模块全量回归测试集
包含 `test_chapter_generation_rag_flow.py`、`test_model_config_provider.py`、`test_evidence_ragflow.py`、`test_generation_context.py` 与 `test_recoverable_jobs.py`：
```text
================== 75 passed, 2 skipped in 111.19s (0:01:51) ==================
```
所有测试均遵循离线 CI 纯洁性准则，无外部网络依赖，测试通过率 100%。
