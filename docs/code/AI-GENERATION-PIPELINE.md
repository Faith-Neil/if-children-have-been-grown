# 为什么有这个文件：说明章节 AI 检索生成端到端闭环的代码架构、组装链路与安全门禁。
# 它解决什么问题：详细记录如何将 RAGFlow 检索客户端与动态模型提供者在章节写作与建议中打通，组装带 [证] 证据、[片] 检索切片和事实变量的统一 Prompt 快照，并实施敏感门禁与防篡改保护。

# 章节 AI 检索生成端到端闭环代码说明

- 关联 Issue：[ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-028](../../issues/ISSUE-028.md)
- 交付报告：[AI-GENERATION-PIPELINE 交付](../delivery/AI-GENERATION-PIPELINE.md)
- 里程碑目标：AI-M0 真实大模型接入与 RAGFlow 检索闭环
- 核心代码路径：
  - `backend/bid-core/icg_demo/retrieval.py`
  - `backend/bid-core/icg_demo/generation_context.py`
  - `backend/bid-core/icg_demo/workflow_schemas.py`
  - `backend/bid-core/icg_demo/domain.py`
  - `backend/bid-core/icg_demo/workflow.py`
  - `backend/bid-core/icg_demo/main.py`
  - `tests/backend/fake_ragflow.py`
  - `tests/backend/fake_openai_chat.py`
  - `tests/backend/test_chapter_generation_rag_flow.py`

---

## 1. 架构总览与端到端闭环数据流

系统在执行章节候选生成（`WorkflowService.generate`）与章节建议（`DemoService.suggest`）时，通过 `build_generation_context` 完成统一事实、证据和检索切片的输入快照构建，数据流图如下：

```
                [客户端发起生成或建议请求]
              (generate / suggest / preview)
                            │
                            ▼
              [敏感项目安全门禁 require_allowed_model]
             敏感项目 & 非本地/敏感禁用 ──► 403 阻断并终止
                            │ (通过)
                            ▼
              [装配写作上下文 build_generation_context]
     ┌──────────────────────┼──────────────────────┐
     ▼                      ▼                      ▼
[招标条款与已确认事实]   [已确认资料证据]       [RAGFlow 候选检索]
- {{fact:...}} 变量     - 来源 library         (通过 EvidenceCandidateService)
- {{sla:...}} 服务承诺  - 校验有效性/公司隔离   - 组装 query (章节名+写作要点+条款)
- 来源原文页码/引用     - 标注 tag: [证]       - 调用 POST /api/v1/retrieval
                                               - 提取路径 B/C 候选
                                               - 标注 tag: [片]，带 chunk_id/doc_id
     │                      │                      │
     └──────────────────────┼──────────────────────┘
                            ▼
              [组装 WritingInputSnapshot]
              - requirements: 章节对应招标文件要求
              - evidence: [证] 已确认可附着证据
              - retrieved_evidence: [片] RAGFlow 检索候选切片（含 provenance 出处）
              - facts: 必须保留的占位符变量
              - plan: 写作要点与字数要求
                            │
                            ▼
              [渲染统一模型输入 render_model_input]
              - [证] 已确认可引用证据
              - [片] 检索证据片段（chunk_id: ..., document_id: ...）
              - 事实变量核对值与必须保留变量规则
                            │
                            ▼
              [动态解析模型 resolve_model_provider]
              (读取项目绑定配置或公司默认配置，注入密钥)
                            │
                            ▼
              [调用大模型 provider.suggest(instruction, context)]
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
        调用成功                      上游故障 (500/网络超时)
             │                             │
             ▼                             ▼
   [输出校验 validate_model_output]   转换为 502 MODEL_UNAVAILABLE
   - 变量遗漏 -> 409 FACT_VARIABLE_LOST      (正式正文不受破坏)
   - 字面值替换 -> 409 FACT_LITERAL_REPLACEMENT
             │ (通过)
             ▼
   [持久化章节候选 candidate 与 input_snapshot]
```

---

## 2. 关键设计与实现细节

### 2.1 候选证据扩展与 Provenance 溯源 (`retrieval.py`)
在 `EvidenceCandidate` 数据类中补充 `document_id` 与 `chunk_id` 字段，默认值为空字符串，向下完全兼容：
- `_path_a`：已确认资料上的规则，`document_id=""`，`chunk_id=""`。
- `_path_b_ragflow`：知识库方案切片（可附着，非仅供参考），注入 `chunk.id` 与 `chunk.document_id`。
- `_path_c_ragflow`：历史投标案例（不可附着，仅供参考），注入 `chunk.id` 与 `chunk.document_id`。

### 2.2 统一输入快照与 Prompt 渲染 (`generation_context.py`)
- **检索切片集成**：
  在 `build_generation_context` 中，由 `chapter.title`、`plan["writing_points"]` 和 `requirements.text` 构造多维检索 query。
  通过传入的 `evidence_service` 发起 `collect(cand_req)`，抽取路径 B/C 切片放入 `retrieved_evidence`。
- **业务标签与出处约定**：
  对齐前端设计系统规范 `business-tags.ts`：
  - 已确认资料库记录标注为 `[证]`；
  - 检索得到的切片标注为 `[片]`，并在 Prompt 中打印来源出处：
    `[片] 检索证据片段（chunk_id: <chunk_id>, document_id: <document_id>）：`
  - 对路径 C 增加提示：`【仅供参考，不得作为正式附着证据】`。
- **优雅降级**：
  当 RAGFlow 返回 0 个切片（`MODE_EMPTY`）或检索服务发生网络异常时，`retrieved_evidence` 记录为空列表 `[]`，不阻断主流程，正常依托已确认证据和事实推进生成。

### 2.3 契约模式对齐 (`workflow_schemas.py`)
在 `WritingInputSnapshot` 中正式声明 `retrieved_evidence` 字段：
```python
class WritingInputSnapshot(ResponseBody):
    ...
    retrieved_evidence: list[dict[str, Any]] = Field(default_factory=list)
```
由于 `ResponseBody` 配置了 `extra="allow"`，历史数据在反序列化时自然兼容，且在接口返回时具备明确的结构体类型声明。

### 2.4 安全门禁与防篡改机制
1. **敏感项目隔离门禁（403）**：
   在调用模型前，`require_allowed_model` 严格检查项目敏感性。敏感项目绑定或继承了云端模型（`is_local=False` 或 `allow_sensitive=False`）时，直接抛出 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，请求绝不流向外部模型端点。
2. **变量防篡改门禁（409）**：
   `validate_model_output` 对大模型生成的文本进行严格校验：
   - 若模型删除了正式正文中已有事实变量，抛出 409 `FACT_VARIABLE_LOST`；
   - 若模型将事实变量替换为手写取值（如把 `{{fact:...}}` 改写为 `服务期限：12个月`），抛出 409 `FACT_LITERAL_REPLACEMENT`。
3. **上游故障安全隔离（502）**：
   当大模型端点返回 500 内部错误或网络超时时，统一捕获并映射为 502 `MODEL_UNAVAILABLE`，保证项目已提交的正式正文不受污染。
4. **知识库停用门禁**：
   当 `knowledge_base_enabled=False` 时，`EvidenceCandidateService` 快速跳过路径 B/C，零网络请求发出。

---

## 3. 测试与验证策略

采用纯离线、零外部依赖的自动化测试体系：
- `fake_ragflow`：模拟 RAGFlow 检索端点，提供 `MODE_CHUNKS`、`MODE_EMPTY`、`MODE_HTTP_ERROR` 等多场景故障注入。
- `fake_openai_chat`：模拟内网兼容的大模型对话端点，验证请求头 `Authorization: Bearer <key>`、模型名、流式/JSON 模式透传及返回注入。
- `tests/backend/test_chapter_generation_rag_flow.py`：
  - `test_end_to_end_chapter_generation_with_ragflow_chunks`：端到端验证 RAGFlow 检索 -> Prompt 组装（`[证]`与`[片]`）-> 真实模型调用 -> 快照保存。
  - `test_end_to_end_chapter_suggestion_with_ragflow_chunks`：验证建议接口采用同一检索增强逻辑。
  - `test_zero_hit_ragflow_graceful_fallback`：零命中优雅降级。
  - `test_knowledge_base_disabled_skips_ragflow_completely`：知识库关闭时不调用 RAGFlow。
  - `test_sensitive_project_blocks_cloud_model_with_403`：敏感项目云端模型前置阻断。
  - `test_model_variable_tampering_blocks_and_preserves_content`：事实变量防篡改。
  - `test_upstream_model_error_maps_to_502_without_corrupting_official_content`：模型故障 502 映射与正文防污染。
