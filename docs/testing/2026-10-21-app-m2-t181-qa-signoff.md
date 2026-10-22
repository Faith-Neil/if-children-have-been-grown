为什么有这个文件：记录QA对APP-M2-T181（智能对话助手答案卡：结构化直查与意图分流，REV-M0-T52）的独立复测与签署结论。

它解决什么问题：不轻信自报结果，亲手执行答案卡专项契约单测与全套检索生成回归，针对性深度核查意图类别 × 知识库开关 4 种组合表格驱动判定、知识库关闭时本项目数据正常直出与公司资料跳过检索标记（library_query_skipped=True）、18 位身份证号码深度递归脱敏掩码（如 110101********1234）、答案卡防篡改与插入门禁（本项目数据一律 can_insert=False、公司资料仅有效且已确认记录 can_insert=True）、项目事实抽取冲突并列展示以及受限资料权限过滤与跨公司租户隔离。

# APP-M2-T181 智能对话助手答案卡独立复测与 QA 签署（REV-M0-T52）

- 被验任务：[APP-M2-T181](../tasks/APP-M2.md#app-m2-t181) · 智能对话助手答案卡（结构化直查与意图分流）
- 关联审查任务：REV-M0-T52
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T181 交付](../delivery/APP-M2-T181.md)、[代码解释](../code/APP-M2-T181.md)
- 被验核心文件：`backend/bid-core/icg_demo/answer_card.py`、`backend/bid-core/icg_demo/workflow.py`、`tests/backend/test_answer_cards.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**APP-M2-T181 保持 in-review，严禁标 done；关联 Issue 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 意图类别 × 知识库开关 4 组合表格驱动判定 | 通过 | `test_intent_category_and_kb_switch_matrix`：① 项目类+开启：`direct_query`，`can_insert=False`；② 项目类+关闭：`direct_query`，`can_insert=False`，注明“本卡来自本项目结构化数据”；③ 公司类+开启：`direct_query`，有效已确认记录 `can_insert=True`；④ 公司类+关闭：`no_retrieval`，`library_query_skipped=True`，提示“知识库已关闭，未查询公司资料库”；常规提问开启走 `kb_retrieval`，关闭走 `no_retrieval` |
| AC-02 知识库关闭时本项目数据直出与公司资料跳过 | 通过 | `test_kb_disabled_project_data_available_and_library_skipped`：问服务期限等项目事实，即使 `knowledge_base_enabled=False`，依然返回结构化答案卡（来源标注清晰）；问公司资质时，资料库查询明确被跳过，不生成答案卡并置 `library_query_skipped=True` |
| AC-03 18 位身份证号码深度递归脱敏掩码 | 通过 | `test_id_card_masking_function` 与 `test_id_card_masking_in_answer_card`：身份证号码匹配严格断言前后非字母数字字符，中间 8 位出生年月日精确掩码（如 `110101199003071234` -> `110101********1234`）；`mask_sensitive_payload` 对卡片所有嵌套字典、列表与文本实施全覆盖深度遍历脱敏，卡片中明文身份证号码 0 泄露 |
| AC-04 答案卡防篡改与插入门禁 (`can_insert`) | 通过 | `test_can_insert_gates_for_project_and_company_records`：招标要求与检查结果等本项目结构化数据一律 `can_insert=False`，原因注明“本项目数据不插入正文”；公司资料记录：未确认（`pending`）标注“未确认”且 `can_insert=False`，已过期（早于项目截止时间）标注“已过期”且 `can_insert=False`，仅已确认且有效记录放行 `can_insert=True` |
| AC-05 项目事实抽取冲突并列展示 | 通过 | `test_project_fact_conflict_display`：当项目事实存在抽取冲突（如服务期限 12 个月 vs 24 个月）时，答案卡确认状态标记为“有冲突，待项目负责人选定”，并在记录中清晰并列列出各候选取值及原文页码（第 5 页 vs 第 18 页） |
| AC-06 受限资料权限隔离与跨公司租户隔离 | 通过 | `test_restricted_evidence_and_cross_company_isolation`：`is_restricted=True` 的涉密资质对无权限普通编写人完全静默过滤，不出现亦不泄露存在；公司管理员正常可见；乙公司账号访问甲公司项目直查答案卡抛出 404 彻底阻断 |
| AC-07 业务层委托集成与服务连通 | 通过 | `test_workflow_service_assistant_query_delegation`：`WorkflowService.assistant_query` 无缝委托至 `AnswerCardService.process_query`，参数与返回值结构完全吻合契约 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 对话助手答案卡专属契约单测 | `python -m pytest tests/backend/test_answer_cards.py -v -rs` | **13 passed, 0 failed** | 0.11s |
| 章节生成端到端闭环与关联回归 | `python -m pytest tests/backend/test_chapter_generation_rag_flow.py tests/backend/test_model_config_provider.py tests/backend/test_evidence_ragflow.py tests/backend/test_generation_context.py -rs` | **70 passed, 2 skipped** (外网守护跳过) | 87.82s |
| 关联单测套件全量汇总 | 5 套件联合执行 | **83 passed, 2 skipped, 0 failed** (100% 通过) | 87.93s |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **表格驱动设计覆盖完备**：测试套件采用 `@pytest.mark.parametrize` 严密覆盖了意图领域（项目 vs 公司 vs 常规）与知识库开关（开 vs 关）的矩阵式组合，尤其对“知识库关闭但本项目数据依然可直出”的细微业务规范（PRD §5.11.15）提供了确定性的自动化防护。
2. **身份证脱敏前后边界断言严密**：`mask_id_card` 采用了 `(?<![0-9A-Za-z])` 与 `(?![0-9A-Za-z])` 环视断言，防止将长数字订单号或哈希字符串错误误伤篡改为星号，算法鲁棒。
3. **插入门禁逐条与整卡双重校验**：卡片顶层的 `can_insert` 布尔值与每条具体记录的 `can_insert` 保持逻辑一致（只有当至少包含一条有效已确认记录时顶层才为 True），防止前端在多条混合结果下出现误插入。

## 签署状态

APP-M2-T181 / REV-M0-T52 保持 **in-review**，**严禁标 done**。
