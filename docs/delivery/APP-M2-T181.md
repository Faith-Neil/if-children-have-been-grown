# 为什么有这个文件：记录 APP-M2-T181 对话助手答案卡（结构化直查与意图分流）的交付成果、测试证据与验收结论。
# 它解决什么问题：汇总代码实现、意图×开关4组合表格驱动测试结果与安全门禁验证，供主 Agent 与 QA 团队复核验收。

# APP-M2-T181 智能对话助手答案卡交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务目标 | APP-M2-T181 智能对话助手答案卡（结构化直查与意图分流） |
| 关联 Issue | [ISSUE-007](../../issues/ISSUE-007.md) |
| 代码说明 | [APP-M2-T181 代码解释](../code/APP-M2-T181.md) |
| 专属测试套件 | `tests/backend/test_answer_cards.py`（13 项全部通过） |
| 全量回归结果 | 83 passed, 2 skipped (0 failed) |
| 当前状态 | in-review（待主 Agent / QA 复核，绝不私自标 done，绝不私自关闭 Issue） |
<!-- task-delivery:end -->

---

## 1. 核心交付内容清单

1. **意图识别与实体抽取 (`classify_query_intent`)**：
   - 依照平台设置 `direct_query_intents`（版本 1），支持本项目数据类（`tender_requirement`, `project_fact`, `response_matrix`, `check_result`）与本公司资料类（`person_cert`, `qualification`, `contract`, `sla`）两大领域的精准识别；
   - 未命中直查意图时平滑回退至常规问答意图。

2. **知识库开关联动与取数路由裁决 (`resolve_assistant_query_route`)**：
   - **意图类别 × 知识库开关 4 种组合完整闭环**：
     - **项目类 + 知识库开启**：`query_route="direct_query"`, `library_query_skipped=False`，返回本项目数据卡，`can_insert=False`；
     - **项目类 + 知识库关闭**：`query_route="direct_query"`, `library_query_skipped=False`，正常直查返回项目数据卡，`can_insert=False`，卡片标注“知识库已关闭，本卡来自本项目结构化数据”；
     - **公司类 + 知识库开启**：`query_route="direct_query"`, `library_query_skipped=False`，直查本公司资料库，合法已确认记录标注 `can_insert=True`；
     - **公司类 + 知识库关闭**：`query_route="no_retrieval"`, `library_query_skipped=True`，跳过资料库查询，不产生答案卡，并给出提示“知识库已关闭，未查询公司资料库”；
     - **常规提问**：知识库开启走 `kb_retrieval`，关闭走 `no_retrieval`。

3. **敏感信息自动掩码脱敏**：
   - 实现居民身份证（18位）算法脱敏：`110101199003071234` ──► `110101********1234`；
   - `mask_sensitive_payload` 对所有嵌套字典、列表与文本实施全覆盖脱敏，杜绝明文身份证号码泄漏。

4. **答案卡防篡改与插入门禁 (`can_insert`)**：
   - **本项目结构化数据卡**：一律标记 `can_insert=False`，`insert_disabled_reason="本项目数据不插入正文"`；
   - **项目事实冲突并列显示**：若事实存在未决定的抽取冲突，确认状态标记为“有冲突，待项目负责人选定”，并列列出各方候选取值与原文页码；
   - **本公司资料卡门禁**：
     - 未确认记录（`pending`）：`can_insert=False`，注明“未确认”；
     - 已过期记录（早于项目投标截止时间）：`can_insert=False`，注明“已过期”；
     - 仅有效且已确认记录：`can_insert=True`。

5. **租户隔离与受限资源权限控制**：
   - 严格限定在当前用户所属公司（`company_id`）内查询，跨租户查询直接抛出 404；
   - `is_restricted=True` 的受限资料对无权限用户完全静默过滤，不出现亦不提示其存在。

---

## 2. 变更文件清单

- **新增业务模块**：
  - `backend/bid-core/icg_demo/answer_card.py`：实现意图识别、路由裁决、身份证脱敏掩码及答案卡数据装配服务。
- **服务对接修改**：
  - `backend/bid-core/icg_demo/workflow.py`：挂载 `AnswerCardService` 并提供 `assistant_query` 方法。
- **专属契约测试套件**：
  - `tests/backend/test_answer_cards.py`：包含 13 个测试项，覆盖意图×开关四组合表格驱动测试、脱敏掩码、门禁规则、冲突并列展示与受限隔离。
- **交付与设计文档**：
  - `docs/code/APP-M2-T181.md`：代码实现与架构数据流文档。
  - `docs/delivery/APP-M2-T181.md`：本交付验收报告。

---

## 3. 自动化测试验证结果

```bash
$ pytest tests/backend/test_answer_cards.py -v
============================= test session starts =============================
tests/backend/test_answer_cards.py::test_intent_category_and_kb_switch_matrix[请问本项目投标保证金是多少？-True-direct_query-False-True-False-None] PASSED
tests/backend/test_answer_cards.py::test_intent_category_and_kb_switch_matrix[请问本项目投标保证金是多少？-False-direct_query-False-True-False-知识库已关闭，本卡来自本项目结构化数据] PASSED
tests/backend/test_answer_cards.py::test_intent_category_and_kb_switch_matrix[张三有哪些Oracle证书？-True-direct_query-False-True-True-None] PASSED
tests/backend/test_answer_cards.py::test_intent_category_and_kb_switch_matrix[张三有哪些Oracle证书？-False-no_retrieval-True-False-False-知识库已关闭，未查询公司资料库] PASSED
tests/backend/test_answer_cards.py::test_intent_category_and_kb_switch_matrix[请问如何撰写数据库高可用方案？-True-kb_retrieval-False-False-False-None] PASSED
tests/backend/test_answer_cards.py::test_intent_category_and_kb_switch_matrix[请问如何撰写数据库高可用方案？-False-no_retrieval-False-False-False-None] PASSED
tests/backend/test_answer_cards.py::test_kb_disabled_project_data_available_and_library_skipped PASSED
tests/backend/test_answer_cards.py::test_id_card_masking_function PASSED
tests/backend/test_answer_cards.py::test_id_card_masking_in_answer_card PASSED
tests/backend/test_answer_cards.py::test_can_insert_gates_for_project_and_company_records PASSED
tests/backend/test_answer_cards.py::test_project_fact_conflict_display PASSED
tests/backend/test_answer_cards.py::test_restricted_evidence_and_cross_company_isolation PASSED
tests/backend/test_answer_cards.py::test_workflow_service_assistant_query_delegation PASSED
============================= 13 passed in 0.18s ==============================
```

关联模块全量回归测试结果：
```bash
$ pytest tests/backend/test_answer_cards.py tests/backend/test_chapter_generation_rag_flow.py tests/backend/test_model_config_provider.py tests/backend/test_evidence_ragflow.py tests/backend/test_generation_context.py -v
================== 83 passed, 2 skipped in 113.97s (0:01:53) ==================
```

---

## 4. 限制与边界

1. 本任务仅实现对话助手直查答案卡的意图分流、数据装配、脱敏与门禁规则；答案卡的正式插入正文交互（`insertAnswerCard`）由 [APP-M2-T183](../tasks/APP-M2.md#app-m2-t183) 承接；
2. 词表 `direct_query_intents` 当前由平台内置维护（版本 1），企业自定义同义词扩展依照 PRD 规划留待二期；
3. 本任务未修改任何数据库 Schema，未引入额外外部网络依赖，完全保持离线 CI 纯洁性；
4. 任务状态按规范标为 `in-review`，等待主 Agent 与 QA 团队签署。
