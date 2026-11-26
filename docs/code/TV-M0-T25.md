为什么有这个文件：解释 TV-M0-T25 检索意图拆解、四库并发召回与 Metadata 强过滤的代码。

# TV-M0-T25 代码说明

| 文件 | 说明 |
|---|---|
| [technical_query_plan.py](../../backend/bid-core/icg/domain/technical_query_plan.py) | `plan_section_queries`：按节路径/挂载点/`target_models` 产出 `SectionQueryPlan`（tender/history/product/manual/fault_case 五路 Query + 各路 `metadata_condition`）；真实 OpenAICompatibleModelProvider 走结构化拆解，`EXTRACT_CALL` 轻量 profile，异常/替身回落 `_rule_plan` |
| [technical_rag.py](../../backend/bid-core/icg/domain/technical_rag.py) | `_configured_material_subkinds` 探测已配置子库；`retrieve_dual` 并发执行历史+子库路由（意图 Query 零命中回落基础 Query，型号过滤零命中回落不锁型号）；`_chunks_for_prompt` 按本标 ~20%/资料 ~55%/历史 ~25% 预算装配；`retrieve_for_section` 合并本标≤3 槽+公司库，审计扩展 `product_hits/manual_hits/fault_case_hits/query_plan_source/section_type` |
| [knowledge_base.py](../../backend/bid-core/icg/domain/knowledge_base.py) | `search()` 的 `metadata_condition`/`max_chunks_per_doc` 透传至 `client.retrieve`，命中 `meta_fields` 透传给 Prompt |
| [writing_knowledge_prompt.py](../../backend/bid-core/icg/domain/writing_knowledge_prompt.py) | 外实体词典扩充（委办局/公司全称）与泛称跳过；`allowed_identity_names` 纳入事实表与读标事实白名单；`history_foreign_names` 额外扫描命中 `meta_fields` 专名；片段标注 `[来源：kb_products | 型号：…]` 徽标 |
| [technical_assistant.py](../../backend/bid-core/icg/domain/technical_assistant.py) | 按节改写路径传递 breadcrumb/挂载点，启用规则意图拆解（不增加模型调用） |
| [types.ts](../../frontend/web/src/shared/types.ts) / [coverage-live.ts](../../frontend/web/src/project/coverage-live.ts) | `CoverageRag` 增加 `product_hits/manual_hits/fault_case_hits`；检索列显示「历史 n · 资料 n(产x/手y/案z)」 |
| [test_tv_m0_t25_query_plan_rag.py](../../tests/backend/test_tv_m0_t25_query_plan_rag.py) | LLM/规则双路径拆解与 metadata 条件断言；四库并发过滤 not_reusable 与错误型号的端到端断言 |
