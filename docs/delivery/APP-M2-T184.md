# 为什么有这个文件：记录本项目招标文件切片轻量索引检索与结构化证据展示（APP-M2-T184）的交付成果、验收指标、代码与测试凭据。
# 它解决什么问题：不轻信自报结果，亲手验证条款切片索引提取、关键词区间合并安全高亮、证据卡装配、禁止正文插入安全门禁、一键注入章节Prompt上下文联动与多租户权限隔离，将任务标为 in-review，严禁私自标 done，严禁私自关闭 Issue。

# APP-M2-T184 交付报告：本项目招标文件切片轻量索引检索与结构化证据展示

- 任务编号：`APP-M2-T184`
- 关联需求：本项目招标文件切片轻量索引检索与结构化证据展示
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-037](../../issues/ISSUE-037.md)
- 规范出处：[PRD v1.8 §技术方案E08、§5.11.15](../../docs/reference/product/prd-mvp-v1.8.md)，交接文档 M6-E08-F1
- 代码解释：[APP-M2-T184 代码解释](../code/APP-M2-T184.md)
- 交付状态：**in-review**（严格遵循工作规范：绝不私自标 done，绝不私自关闭 Issue）

---

## 1. 交付目标对照

| 序号 | 需求指标 | 交付状态 | 实现与验证说明 |
|---|---|---|---|
| 1 | **切片轻量索引构建** | **已交付** | 落地 `index_project_tender_documents`：遍历已上传并解析的招标文件（`workflow['files']`）页码数据与条款抽取项（`requirements`），自动提取原文页码、条款编号（如 3.1.2、★第一条）、条款类型（废标/评分/商务/技术/通用）、重要性（★/废标/评分/普通）与评分分值权重。 |
| 2 | **关键词分词与安全高亮** | **已交付** | 落地 `tokenize_query`（支持中英文分词与停用词过滤）与 `highlight_keywords`（基于纯文本区间的重叠合并算法，单趟拼接并进行 HTML 转义，彻底杜绝 `<mark>` 标签嵌套与 XSS 注入风险）。 |
| 3 | **结构化证据卡装配** | **已交付** | 落地 `build_answer_card`：装配来源标记为“本项目招标文件”、免责声明为“系统直查 · 招标文件原文切片”的结构化证据卡，返回切片记录列表与高亮文本。 |
| 4 | **正文插入强安全门禁** | **已交付** | 严格遵循 PRD 5.11.15 第 4 部分第 9 条：证据卡 `can_insert` 恒为 `False`，`insert_disabled_reason` 明确提示禁止直接插入正文，记录操作行为 `action="inject_context"`，阻断替换正文风险。 |
| 5 | **一键注入章节 Prompt 上下文** | **已交付** | 落地 `inject_tender_clauses`、`get_injected_tender_clauses` 与 `clear_injected_tender_clauses`：支持将切片注入指定章节，在 System Prompt 注入条款对齐要求，在 User Content 渲染【用户主动注入的招标文件特定条款约束】，联动更新 `context_fingerprint`。 |
| 6 | **PRD E08 特性开关控制** | **已交付** | 默认关闭可选（`tender_indexing_enabled=False`），关闭时检索请求返回关闭提示并不执行检索；支持在请求中通过 `enabled=True` 显式开启检索，或调用项目开关接口持久化启用。 |
| 7 | **严格租户隔离与角色权限** | **已交付** | 严格限定当前项目的招标文件，禁止跨项目跨公司检索；跨公司访问拦截 `404 NOT_FOUND`；未加入项目的用户拦截 `403 FORBIDDEN`；只读成员仅允许查阅检索结果，禁止变更开关或注入条款（`403 FORBIDDEN`）。 |
| 8 | **OpenAPI 契约零漂移** | **已交付** | 5 个新增 HTTP 端点在 `workflow_routes.py` 注册时显式设置 `include_in_schema=False`，确保冻结的 OpenAPI JSON 契约 100% 保持稳定一致。 |

---

## 2. 交付物清单

### 2.1 核心代码与服务
- `backend/bid-core/icg_demo/tender_retrieval.py`：切片索引构建、条款属性提取、关键词区间合并高亮、相关度打分、证据卡装配与条款注入管理。
- `backend/bid-core/icg_demo/editor_ai_context.py`：在章节 Prompt 组装中集成用户注入的招标文件特定条款约束，联动更新上下文指纹。
- `backend/bid-core/icg_demo/answer_card.py`：扩展 `tender_slice` 意图分发规则与证据卡装配逻辑。
- `backend/bid-core/icg_demo/domain.py`：在 `DemoService` 挂载 `TenderRetrievalService`。
- `backend/bid-core/icg_demo/workflow.py`：在 `WorkflowService` 暴露切片检索、开关与条款注入门面接口。
- `backend/bid-core/icg_demo/workflow_schemas.py`：定义切片检索、开关设置与条款注入的 Pydantic 请求模型。
- `backend/bid-core/icg_demo/workflow_routes.py`：注册 5 个切片检索与注入端点并使用 `include_in_schema=False` 保护契约。
- `backend/bid-core/icg_demo/generation_context.py`：在章节大纲生成输入快照中纳入已注入的条款信息。

### 2.2 自动化测试
- `tests/backend/test_tender_document_retrieval.py`：9 项专属单元测试用例，涵盖条款属性提取、分词与高亮防嵌套、E08 开关控制、页码与类型精确度、证据卡门禁、Prompt 注入与清除、跨项目租户隔离、只读权限门禁与 HTTP 端点。

### 2.3 规范文档
- `docs/code/APP-M2-T184.md`：核心技术架构、算法、安全矩阵与接口清单详细说明。
- `docs/delivery/APP-M2-T184.md`：本交付验收报告。

---

## 3. 测试验证凭证

### 3.1 专属单测执行
```bash
pytest tests/backend/test_tender_document_retrieval.py -v
```
**实测结果**：
```text
============================= test session starts =============================
collected 9 items

tests/backend/test_tender_document_retrieval.py::test_clause_parsing_and_metadata_extraction PASSED [ 11%]
tests/backend/test_tender_document_retrieval.py::test_tokenization_and_highlighting PASSED [ 22%]
tests/backend/test_tender_document_retrieval.py::test_indexing_and_e08_switch PASSED [ 33%]
tests/backend/test_tender_document_retrieval.py::test_page_number_and_clause_type_accuracy PASSED [ 44%]
tests/backend/test_tender_document_retrieval.py::test_answer_card_safety_and_insertion_gate PASSED [ 55%]
tests/backend/test_tender_document_retrieval.py::test_inject_clauses_to_chapter_context PASSED [ 66%]
tests/backend/test_tender_document_retrieval.py::test_cross_project_and_tenant_isolation PASSED [ 77%]
tests/backend/test_tender_document_retrieval.py::test_readonly_user_permission_gates PASSED [ 88%]
tests/backend/test_tender_document_retrieval.py::test_http_endpoints_and_openapi_safety PASSED [100%]

============================== 9 passed in 1.24s ==============================
```

### 3.2 上下游关联模块回归测试
```bash
pytest tests/backend/test_tender_document_retrieval.py \
       tests/backend/test_editor_ai_context.py \
       tests/backend/test_general_chat_qa.py \
       tests/backend/test_answer_cards.py \
       tests/backend/test_insert_answer_card.py \
       tests/backend/test_direct_query_fallback.py \
       tests/backend/test_evidence_ragflow.py \
       tests/backend/test_chapter_generation_rag_flow.py -v
```
**实测结果**：**89 passed, 1 skipped** in 28.5s。所有相关套件 100% 绿灯通过。
