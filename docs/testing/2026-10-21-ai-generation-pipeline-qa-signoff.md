为什么有这个文件：记录QA对AI-GENERATION-PIPELINE / REV-M0-T50（章节 AI 检索生成端到端闭环）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手执行端到端检索与大模型生成套件及全套关联回归，深度复验核心门禁与闭环链路：RAGFlow 路径 B/C 检索切片接入（带 [片] 标识与 chunk_id/document_id 溯源元数据）、统一 Prompt 快照组装、动态配置驱动模型调用（OpenAI 兼容适配器）、零命中优雅降级、知识库关闭网络零外泄、敏感项目前置 403 强拦截门禁、事实变量防篡改（409 FACT_VARIABLE_LOST / 409 FACT_LITERAL_REPLACEMENT）以及 502 MODEL_UNAVAILABLE 上游故障安全隔离与正式正文无损保护。

# AI-GENERATION-PIPELINE 章节 AI 检索生成端到端闭环独立复测与 QA 签署（REV-M0-T50）

- 被验任务：[AI-GENERATION-PIPELINE](../delivery/AI-GENERATION-PIPELINE.md) · 章节 AI 检索生成端到端闭环
- 关联审查任务：REV-M0-T50
- 关联交付：[AI-GENERATION-PIPELINE 交付](../delivery/AI-GENERATION-PIPELINE.md)、[代码解释](../code/AI-GENERATION-PIPELINE.md)
- 关联 Issue：[ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-028](../../issues/ISSUE-028.md)
- 被验核心文件：`backend/bid-core/icg_demo/retrieval.py`、`backend/bid-core/icg_demo/workflow_schemas.py`、`backend/bid-core/icg_demo/generation_context.py`、`backend/bid-core/icg_demo/domain.py`、`backend/bid-core/icg_demo/workflow.py`、`backend/bid-core/icg_demo/main.py`、`tests/backend/test_chapter_generation_rag_flow.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**AI-GENERATION-PIPELINE 保持 in-review，严禁标 done；关联 Issue 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 RAGFlow 检索接入与切片溯源元数据 | 通过 | `test_end_to_end_chapter_generation_with_ragflow_chunks`：检索切片准确携带 `chunk_id` 与 `document_id`；`input_snapshot.retrieved_evidence` 正确持久化结构化切片；Prompt 渲染严格遵循规范标注 `[片]` 与出处 `（chunk_id: ..., document_id: ...）` |
| AC-02 章节生成与建议端到端贯通 | 通过 | `test_end_to_end_chapter_suggestion_with_ragflow_chunks`：`DemoService.suggest` 与 `WorkflowService.generate` 均通过 `resolve_model_provider` 动态解析配置，透传 API Key 与模型参数；Prompt 中已确认资料库标注 `[证]`、事实变量 `{{fact:...}}` 与服务承诺变量 `{{sla:...}}` 完备注入 |
| AC-03 零命中优雅降级容错 | 通过 | `test_zero_hit_ragflow_graceful_fallback`：RAGFlow 返回 0 个 chunks 时，`retrieved_evidence` 优雅置空，生成与建议流程不中断，Prompt 安全保留事实与 `[证]` 证据，排除 `[片]` 区域，平稳推进生成 |
| AC-04 知识库关闭网络零外泄 | 通过 | `test_knowledge_base_disabled_skips_ragflow_completely`：当 `knowledge_base_enabled=False` 时，系统完全跳过 RAGFlow 网络调用（外部 HTTP 调用为 0），仅依赖已确认证据和事实变量，平稳退化 |
| AC-05 敏感项目安全门禁前置强拦截 | 通过 | `test_sensitive_project_blocks_cloud_model_with_403`：当项目标记为敏感项目（`sensitive=true`）且绑定云端/非本地模型时，在章节建议与正文生成调用大模型前强制拦截，抛出 HTTP 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，模型端点实际网络请求为 0 次，彻底杜绝数据外泄 |
| AC-06 事实变量完整性与防篡改 | 通过 | `test_model_variable_tampering_blocks_and_preserves_content`：模型遗漏正式正文中的事实变量时抛出 HTTP 409 `FACT_VARIABLE_LOST`；模型将变量改写为字面值时抛出 HTTP 409 `FACT_LITERAL_REPLACEMENT`；两种情况下正式正文均保持原样未受篡改与破坏 |
| AC-07 上游模型故障安全映射与正文隔离 | 通过 | `test_upstream_model_error_maps_to_502_without_corrupting_official_content`：上游大模型端点返回 HTTP 500 或连接超时时，业务接口安全映射为 HTTP 502 `MODEL_UNAVAILABLE`，正式正文零污染 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 章节生成 RAGFlow 闭环专属测试 | `python -m pytest tests/backend/test_chapter_generation_rag_flow.py -v -rs` | **7 passed, 0 failed** | 35.31s |
| 模型配置与检索关联回归套件 | `python -m pytest tests/backend/test_model_config_provider.py tests/backend/test_evidence_ragflow.py tests/backend/test_generation_context.py tests/backend/test_recoverable_jobs.py -rs` | **68 passed, 2 skipped** (无外部端点依赖) | 83.90s |
| 端到端与关联套件全量汇总 | 合计 5 套件 | **75 passed, 2 skipped, 0 failed** (100% 通过) | 119.21s |
| 工程治理规范核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **统一上下文快照引擎保障两端一致**：`DemoService.suggest`（正文改写建议）与 `WorkflowService.generate`（章节大纲生成）底层完全统一通过 `build_generation_context` 装配上下文，消除了既有设计中改写建议与正文生成上下文分化可能引发的幻觉与事实出入。
2. **切片级别双标识元数据溯源**：在 `EvidenceCandidate` 中同时记录 `document_id` 与 `chunk_id`，使得前端展示 `Cite` 与 `SourceBar` 业务小组件时能够精准定位至具体知识库文档与切片段落，为合规审核提供确定性依据。
3. **敏感项目二次强校验机制稳固**：即便在数据库直接将敏感项目绑定了云端模型，在调用发起瞬间的前置守卫依然会强制抛出 403 阻断并终止网络发包，安全防御纵深可靠。

## 签署状态

AI-GENERATION-PIPELINE / REV-M0-T50 保持 **in-review**，**严禁标 done**。
