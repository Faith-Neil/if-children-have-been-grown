为什么有这个文件：记录QA对APP-M2-T182（智能对话助手直查未命中与常规回答回退）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手执行专属未命中降级契约单测与答案卡联合测试，深度审计四大核心门禁：直查未命中时绝对不编造假卡片（answer_card 严格为 None，fallback_to_general=True）、意图领域 × 知识库开关 4 种组合与常驻说明文案一致性、实体级精准匹配与空记录过滤以及跨租户 404 NOT_FOUND 鉴权隔离与受限脱敏安全。

# APP-M2-T182 智能对话助手直查未命中与常规回答回退独立复测与 QA 签署

- 被验任务：[APP-M2-T182](../tasks/APP-M2.md#app-m2-t182) · 智能对话助手直查未命中与常规回答回退
- 关联审查任务：REV-M0-T55
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T182 交付](../delivery/APP-M2-T182.md)、[代码解释](../code/APP-M2-T182.md)
- 被验核心文件：`backend/bid-core/icg_demo/answer_card.py`、`backend/bid-core/icg_demo/workflow.py`、`tests/backend/test_direct_query_fallback.py`、`tests/backend/test_answer_cards.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**APP-M2-T182 保持 in-review，严禁标 done；关联 ISSUE-007 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 直查未命中绝对不编造假卡片 | 通过 | `test_project_fact_unhit_fallback_kb_on`、`test_tender_requirement_unhit_fallback` 与各资料未命中测试：当命中直查意图但在项目结构化数据或公司资料库中查无记录时，`fallback_to_general` 严格为 `True`，且 `answer_card` 绝对为 `None`，杜绝任何携带默认值或空占位符的虚假卡片返回 |
| AC-02 意图分类 × 开关态回退路由判定 | 通过 | ① 项目事实未命中：KB开启路由转 `kb_retrieval`，KB关闭转 `no_retrieval`；② 招标要求未命中：KB开启转 `kb_retrieval`，KB关闭转 `no_retrieval`；③ 公司人员/证书/资质/合同/SLA未命中：KB开启转 `kb_retrieval`；KB关闭跳过直查置 `library_query_skipped=True` 且路由转 `no_retrieval` |
| AC-03 知识库关闭常驻说明一致性 | 通过 | `test_kb_disabled_persistent_notice_consistency`：只要 `knowledge_base_enabled=False`，无论无意图常规提问、项目数据未命中降级、还是公司资料跳过查询，回复均持久携带统一提示“知识库已关闭，未查询公司资料库”；本项目数据正常直查命中时，卡片照常注“知识库已关闭，本卡来自本项目结构化数据” |
| AC-04 实体级精准过滤装配 | 通过 | 针对具体人名（如赵六）、特定证书类型（如CISP）、特定资质等级（如CMMI5）、特定业绩领域（如三甲医院）及 SLA 等级实施严格精确过滤，未命中时产生空记录（`len(records) == 0`）以安全短路触发降级流程，无越权泛化匹配 |
| AC-05 跨公司租户隔离与 404 鉴权门禁 | 通过 | `test_cross_tenant_access_rejection`：乙公司人员跨租户访问甲公司项目提问时，严格通过 `Principal` 鉴权并返回标准的 `DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")`，多租户隔离防线稳固 |
| AC-06 敏感身份证号与受限资料防护 | 通过 | 递归脱敏掩码与受限资料静默过滤机制在未命中及回退链路中全程生效，无任何脱敏旁路穿透隐患 |
| AC-07 业务层委托集成 | 通过 | `test_workflow_service_fallback_delegation`：`WorkflowService.assistant_query` 正常透传回退数据与通知，保持统一服务入口 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 直查未命中降级专属单测 | `python -m pytest tests/backend/test_direct_query_fallback.py -v` | **12 passed, 0 failed** | 0.07s |
| 答案卡全套契约联合测试 | `python -m pytest tests/backend/test_answer_cards.py tests/backend/test_direct_query_fallback.py -v` | **25 passed, 0 failed** | 0.13s |
| 错误码与幂等契约回归 | `python -m pytest tests/backend/test_error_idempotency.py -v -rs` | **9 passed, 0 failed** (143 错误码全量吻合) | 6.67s |
| 后端全量测试回归 | `python -m pytest tests/backend/ -rs` | **510 passed, 23 skipped, 0 failed** (100% 通过) | 361.65s |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **零虚假卡片硬性门禁**：大模型生成类应用容易在没有找到真实依据时“无中生有”创造空卡片或编造字段。APP-M2-T182 在底层强行约束只要记录为空则 `answer_card = None`，前端只展现纯文本回答并标注转入常规检索，完全杜绝了幻觉答案卡的生成。
2. **知识库关闭状态提示标准化**：通过常驻追加逻辑，确保了无论用户以何种形式提问，只要当前工作区处于“离线/关闭知识库”状态，均能获得清晰且确定性的“知识库已关闭，未查询公司资料库”告知，完全符合合规审计与 PRD §5.11.15 规范。

## 签署状态

APP-M2-T182 保持 **in-review**，**严禁标 done**。
