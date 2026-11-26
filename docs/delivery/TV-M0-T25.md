为什么有这个文件：记录检索意图拆解、四库并发配额召回与 Metadata 强过滤交付。

# TV-M0-T25 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 代码 | [TV-M0-T25](../code/TV-M0-T25.md) |

## 实际变更

- 新增 `technical_query_plan.py`：基于节面包屑、挂载评分点与 `target_models` 拆解差异化检索子 Query——历史标书搜写法（自动排除 `reusability=not_reusable` 与 `content_role=buyer_requirement`）、产品/手册/故障案例搜干货（按型号锁定 `metadata_condition`）；真实本地模型可用时走结构化拆解，超时/替身毫秒级回落确定性规则。
- `retrieve_dual` 升级为并发多路检索：历史库 + 已配置的资料三子库并发召回，意图子 Query 零命中时回落本节基础 Query；按库配额截断（历史 ≤3 条 / 各子库 ≤3 条）。
- `retrieve_for_section`：本标切片补充召回（≤3 槽）+ 四库合并；`_chunks_for_prompt` 按预算装配上下文（本标 ~20% / 资料库 ~55% / 历史标书 ~25%），资料库事实源优先于历史写法参考。
- `knowledge_base.search()` 透传 `metadata_condition` 与 `max_chunks_per_doc`；检索命中携带 `meta_fields`（型号/故障分类）并在 Prompt 中标注 `[来源：kb_products | 型号：…]`。
- 审计行扩展 `product_hits / manual_hits / fault_case_hits / query_plan_source / section_type`；覆盖视图检索列显示「历史 n · 资料 n(产x/手y/案z)」。
- 外实体词典扩充（委办局、公司全称、高校医院等）并跳过「我公司/招标」类泛称；历史命中的 `meta_fields` 专名纳入串标检测。

## 验收证据

- `tests/backend/test_tv_m0_t25_query_plan_rag.py`：2 passed（LLM 拆解+规则回落的 metadata 过滤断言；四库并发召回过滤 not_reusable 与错误型号，配额与来源徽标断言）。
- `test_technical_rag.py`、`test_technical_coverage_view.py`、`test_draft_one_section_stages.py` 全绿；前端 `coverage-live.test.mjs` 7 passed。

## 局限

- 意图拆解的 LLM 路径只在真实 OpenAICompatibleModelProvider 下启用，替身环境走规则拆解。
- 配额为字符预算近似值，非严格 token 计数。

## 同步

PRD、ROADMAP、ARCHITECTURE：无改动，按 [ISSUE-054](../../issues/ISSUE-054.md) 的 Wave 4 设计执行。
