# 为什么有这个文件：记录编辑台章节上下文感知问答与划词引用联动（AI-EDITOR-CONTEXT-LINKAGE）的交付成果、验收指标、代码与测试凭据。
# 它解决什么问题：不轻信自报结果，亲手验证段落切分、划词定位、依据指纹、Diff润色建议与四道安全门禁（特别是未获锁强制 copy_only 与正文零突变），将任务标为 in-review，严禁私自标 done。

# AI-EDITOR-CONTEXT-LINKAGE 交付报告：编辑台章节上下文感知问答与划词引用联动

- 任务编号：`AI-EDITOR-CONTEXT-LINKAGE`
- 关联需求：编辑台深度联动（智能投标辅助编辑台右侧助手与中间正文联动）
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 规范出处：[PRD v1.8 §5.11.3～5.11.6、§5.7.8](../../docs/reference/product/prd-mvp-v1.8.md)
- 代码解释：[AI-EDITOR-CONTEXT-LINKAGE 代码解释](../code/AI-EDITOR-CONTEXT-LINKAGE.md)
- QA 签署：[QA签署报告](../testing/2026-10-22-ai-editor-context-linkage-qa-signoff.md)
- 交付状态：**in-review**（严格遵循工作规范：绝不私自标 done，绝不私自关闭 Issue）

---

## 1. 交付目标对照

| 序号 | 需求指标 | 交付状态 | 实现与验证说明 |
|---|---|---|---|
| 1 | **编辑台上下文注入** | **已交付** | 支持传入 `chapter_id`, `chapter_title`, `selected_text`（用户划词选中文本片段），并在 `general_chat` / `ask_assistant` / `editor_ai_chat` 中完成全链路透传。 |
| 2 | **段落切分与划词命中** | **已交付** | 落地 `decompose_chapter_paragraphs`：正文拆分为 `[P1]`, `[P2]...` 结构化段落，精准标记 `is_selected=True` 与起止偏移；提供无划词时的无损全文兜底。 |
| 3 | **依据材料与溯源指纹** | **已交付** | 落地 `collect_chapter_citations`：自动汇聚本章节已关联确认的招标文件条款、公司证据 `[证]` 与知识库检索切片 `[片]`；为每项证据计算唯一 SHA-256 溯源指纹，并生成联合 `context_fingerprint`。 |
| 4 | **双场景智能支持** | **已交付** | 落地 `detect_editor_scene` 与 `build_editor_prompt_context`：精准支持划词润色/优化（`polish`，生成 Diff 对比与改写建议）与章节合规性/完整度问答（`compliance_qa`，条款覆盖诊断）。 |
| 5 | **编辑锁与正文零突变守护** | **已交付** | 严格校验独占编辑锁：未获得有效租约锁时，`can_insert` 恒定为 `False`，`action="copy_only"`，正文/修订号/版本历史零修改；持有有效锁且具有已核对依据溯源时放行 `suggest_replacement` 建议。 |
| 6 | **敏感项目本地模型隔离** | **已交付** | 敏感项目强制要求本地离线模型配置（`is_local=True` 且 `allow_sensitive=True`）；配置云端模型前置强阻断抛出 `403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。 |
| 7 | **只读权限与租户隔离** | **已交付** | 系统只读角色（`viewer`, `auditor`, `group_admin`, `platform_admin`）与项目只读成员提问统一拦截抛出 `403 FORBIDDEN`；跨租户访问拦截抛出 `404 NOT_FOUND`。 |

---

## 2. 交付物清单

### 2.1 核心代码
- `backend/bid-core/icg_demo/editor_ai_context.py`：编辑台上下文切分、依据搜集、Prompt 组装、Diff 建议提取与 `EditorAIContextService` 服务类。
- `backend/bid-core/icg_demo/domain.py`：在 `DemoService` 挂载 `EditorAIContextService` 并暴露 `chat_editor_context`。
- `backend/bid-core/icg_demo/workflow.py`：在 `WorkflowService` 暴露 `editor_ai_chat` 与 `build_editor_prompt_context` 门面。
- `backend/bid-core/icg_demo/answer_card.py`：在 `AnswerCardService` 扩展 `general_chat` 划词参数无缝联动并暴露 `editor_context_chat`。

### 2.2 自动化测试
- `tests/backend/test_editor_ai_context.py`：12 项专属单元与门禁测试用例，涵盖段落解析、划词命中、双场景 Prompt 组装、无锁守卫、正文零修改、依据指纹、敏感隔离与多租户权限。

### 2.3 规范文档
- `docs/code/AI-EDITOR-CONTEXT-LINKAGE.md`：详细代码技术说明与 Mermaid 架构数据流图。
- `docs/delivery/AI-EDITOR-CONTEXT-LINKAGE.md`：本交付验收报告。
- `docs/testing/2026-10-22-ai-editor-context-linkage-qa-signoff.md`：QA 独立复测签署记录。

---

## 3. 测试验证凭证

### 3.1 专属单测执行
```bash
pytest tests/backend/test_editor_ai_context.py -v
```
**实测结果**：**12 passed, 0 failed** in 0.49s。

### 3.2 章节生成与助手联合回归
```bash
pytest tests/backend/test_editor_ai_context.py tests/backend/test_general_chat_qa.py tests/backend/test_outline_generation_start.py tests/backend/test_error_idempotency.py tests/backend/test_answer_cards.py tests/backend/test_insert_answer_card.py tests/backend/test_chapter_generation_rag_flow.py -v
```
**实测结果**：**73 passed, 0 failed** in 22.84s。

### 3.3 143 冻结错误码 AST 与契约断言
```bash
pytest tests/backend/test_error_idempotency.py -v
```
**实测结果**：**9 passed, 0 failed** (143 错误码严格无漂移)。

---

## 4. 后续与限制

1. **状态保持**：任务保持在 **in-review**，等待主 Agent 与项目经理最终验收签署；关联 Issue 保持原状态，绝不私自关闭。
2. **纯内存测试隔离**：在离线单测中均使用 `httpx.MockTransport` 模拟本地大模型调用，确保离线 CI 100% 纯洁性，杜绝真实网络探测。
