# 为什么有这个文件：记录 APP-M2-T182 直查未命中与常规回答回退机制的交付成果、测试证据与验收结论。
# 它解决什么问题：汇总代码实现、回退降级表格驱动测试结果、知识库关闭常驻提示与安全门禁验证，供主 Agent 与 QA 团队复核验收。

# APP-M2-T182 智能对话助手直查未命中与常规回答回退交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务目标 | APP-M2-T182 智能对话助手直查未命中与常规回答回退 |
| 关联 Issue | [ISSUE-007](../../issues/ISSUE-007.md) |
| 代码说明 | [APP-M2-T182 代码解释](../code/APP-M2-T182.md) |
| 专属测试套件 | `tests/backend/test_direct_query_fallback.py`（12 项全部通过） |
| 联合验证套件 | `tests/backend/test_answer_cards.py` + `tests/backend/test_direct_query_fallback.py`（25 项全部通过） |
| 后端全量回归 | 510 passed, 23 skipped (0 failed) in 326.72s |
| 当前状态 | in-review（待主 Agent / QA 复核，绝不私自标 done，绝不私自关闭 Issue） |
<!-- task-delivery:end -->

---

## 1. 核心交付内容清单

1. **直查未命中优雅降级与常规回答回退**：
   - 当用户提问命中直查意图（`direct_query`），但经精准匹配后在本项目结构化数据或公司资料库中查无记录时（`len(card.records) == 0`），触发优雅降级（`fallback_to_general=True`）；
   - **绝不编造虚假卡片**：响应中 `answer_card` 字段绝对置为 `None`，不返回带默认值或伪造字段的空结构卡片。

2. **区分意图类别与开关态的回退路由及提示规范**：
   - **本项目结构化数据未命中**：
     - 知识库开启时：路由转为 `query_route="kb_retrieval"`，提示“本项目结构化数据中未查询到对应条目，已转入常规助手解答”，`library_query_skipped=False`；
     - 知识库关闭时：路由转为 `query_route="no_retrieval"`，提示“本项目结构化数据中未查询到对应条目，已转入常规助手解答。知识库已关闭，未查询公司资料库”，`library_query_skipped=False`。
   - **本公司资料库未命中**：
     - 知识库开启时：路由转为 `query_route="kb_retrieval"`，提示“本公司资料库中未查询到对应结构化记录，已转入知识库检索解答”，`library_query_skipped=False`；
     - 知识库关闭时：跳过查询置 `library_query_skipped=True`，路由转为 `query_route="no_retrieval"`，提示“知识库已关闭，未查询公司资料库”。

3. **知识库关闭常驻说明一致性保障**：
   - 只要知识库处于关闭状态（`knowledge_base_enabled=False`），无论普通无意图提问，还是项目数据未命中降级，或公司资料跳过查询，回复均持久携带统一常驻提示：“知识库已关闭，未查询公司资料库”；
   - 本项目数据正常直查命中时，卡片照常注“知识库已关闭，本卡来自本项目结构化数据”，不出现“无知识库来源”。

4. **实体级针对性精准过滤装配**：
   - **项目事实**：提取具体事实键（“服务期限”、“最高限价”、“交付地点”等），对未在事实表中声明的项目事实（如交付地点）返回空记录；
   - **招标文件**：提取条款核心关键词（“投标保证金”、“开标时间”等），对未录入的招标文件条款（如开标时间）返回空记录；
   - **公司资料**：针对具体人名（如赵六）、特定证书类型（如CISP）、特定资质等级（如CMMI5）、特定业绩领域（如三甲医院）及 SLA 等级进行匹配，未命中即产生空记录以安全触发降级。

5. **租户安全与 143 错误码集守卫**：
   - 跨公司跨租户访问项目严格通过 `Principal` 鉴权并返回标准的 `DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")`；
   - 受限资料严格执行人员授权校验，无权用户静默过滤且不泄露其存在。

---

## 2. 变更文件清单

- **业务逻辑优化**：
  - `backend/bid-core/icg_demo/answer_card.py`：完善 `process_query` 未命中降级裁决、常驻说明一致性追加，以及 `_assemble_project_card` / `_assemble_company_card` 的实体级精准过滤逻辑。
  - `backend/bid-core/icg_demo/workflow.py`：保持 `assistant_query` 对 `AnswerCardService` 的统一委派与透传。
- **专属契约测试套件**：
  - `tests/backend/test_direct_query_fallback.py`：新建 12 项专属单元测试用例，覆盖项目数据未命中降级、公司资料未命中降级、知识库关闭常驻提示一致性、防编造卡片断言与跨租户安全门禁。
- **交付与设计文档**：
  - `docs/code/APP-M2-T182.md`：代码实现机制与回退数据流文档。
  - `docs/delivery/APP-M2-T182.md`：本交付验收报告。

---

## 3. 自动化测试验证结果

专属未命中回退测试套件运行记录：
```bash
$ pytest tests/backend/test_direct_query_fallback.py -v
============================= test session starts =============================
tests/backend/test_direct_query_fallback.py::test_project_fact_unhit_fallback_kb_on PASSED [  8%]
tests/backend/test_direct_query_fallback.py::test_project_fact_unhit_fallback_kb_off PASSED [ 16%]
tests/backend/test_direct_query_fallback.py::test_tender_requirement_unhit_fallback PASSED [ 25%]
tests/backend/test_direct_query_fallback.py::test_company_library_person_unhit_fallback_kb_on PASSED [ 33%]
tests/backend/test_direct_query_fallback.py::test_company_library_cert_unhit_fallback_kb_on PASSED [ 41%]
tests/backend/test_direct_query_fallback.py::test_company_library_qualification_unhit_fallback_kb_on PASSED [ 50%]
tests/backend/test_direct_query_fallback.py::test_company_library_contract_unhit_fallback_kb_on PASSED [ 58%]
tests/backend/test_direct_query_fallback.py::test_company_library_sla_unhit_fallback_kb_on PASSED [ 66%]
tests/backend/test_direct_query_fallback.py::test_company_library_query_kb_off_skipped PASSED [ 75%]
tests/backend/test_direct_query_fallback.py::test_kb_disabled_persistent_notice_consistency PASSED [ 83%]
tests/backend/test_direct_query_fallback.py::test_workflow_service_fallback_delegation PASSED [ 91%]
tests/backend/test_direct_query_fallback.py::test_cross_tenant_access_rejection PASSED [100%]

============================= 12 passed in 0.16s ==============================
```

答案卡全套契约联合测试记录：
```bash
$ pytest tests/backend/test_answer_cards.py tests/backend/test_direct_query_fallback.py -v
============================= 25 passed in 0.14s ==============================
```

后端全量回归测试记录（100% 离线纯洁性）：
```bash
$ pytest tests/backend/
============================== 510 passed, 23 skipped, 32 warnings in 326.72s (0:05:26) ==============================
```

---

## 4. 限制与边界

1. 本任务仅负责智能对话助手直查未命中的检测、优雅降级及常规回答回退路由与提示组装；后续答案卡作为引用的正文插入交互由 [APP-M2-T183](../tasks/APP-M2.md#app-m2-t183) 承接；
2. 直查词表当前版本为平台内置版本 1（`DIRECT_QUERY_INTENT_VERSION = 1`），根据 PRD 规划，企业级自定义同义词维护留待二期建设；
3. 本任务完全保持离线纯洁性，所有测试用例均为内存级离线验证；
4. 任务状态按工作流规范标为 `in-review`，等待主 Agent 与测试团队验收。
