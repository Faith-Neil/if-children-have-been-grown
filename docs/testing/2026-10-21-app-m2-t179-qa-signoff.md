为什么有这个文件：记录QA对APP-M2-T179（智能对话助手自由问答：只“复制”与安全隔离）的独立复验与签署结论。

它解决什么问题：不轻信开发自报结果，亲手执行智能助手自由提问专属单测套件、四道安全门禁流水线验证（禁止写入正文恒定 copy_only、知识库关闭零外呼与常驻说明、敏感项目强制本地离线模型拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL、4 类系统只读角色与项目只读成员提问拦截 403 FORBIDDEN）、跨租户数据隔离、502 大模型异常降级映射以及全量后端回归测试。

# APP-M2-T179 自由问答（只“复制”与安全隔离）独立复测与 QA 签署

- 被验任务：[APP-M2-T179](../tasks/APP-M2.md#app-m2-t179) · 自由问答（只“复制”与安全隔离）
- 关联审查任务：REV-M0-T60
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T179 交付](../delivery/APP-M2-T179.md)、[代码解释](../code/APP-M2-T179.md)
- 依赖任务：[APP-M2-T181](../tasks/APP-M2.md#app-m2-t181)、[APP-M2-T182](../tasks/APP-M2.md#app-m2-t182)、[APP-M2-T183](../tasks/APP-M2.md#app-m2-t183)
- 被验核心文件：
  - `backend/bid-core/icg_demo/answer_card.py`
  - `backend/bid-core/icg_demo/workflow.py`
  - `tests/backend/test_general_chat_qa.py`
  - `tests/backend/test_answer_cards.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**APP-M2-T179 保持 in-review，严禁标 done；关联 ISSUE-007 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 门禁 1：严格禁止写入正文（只“复制”） | 通过 | 自由提问返回响应中，`can_insert` 恒定为 `False`，`action="copy_only"`，`insert_disabled_reason="自由问答仅供参考与复制，不可直接插入正文"`；调用完成后章节正文（`content`）与修订序号（`revision`）保持 100% 绝对不变，不产生版本历史与草稿覆盖 |
| AC-02 门禁 2：知识库关闭常驻说明与零外呼 | 通过 | 当 `knowledge_base_enabled=False` 时：① 严格禁止外呼 RAGFlow 检索公司库（`library_query_skipped=True`, `query_route="no_retrieval"`, `citations=[]`）；② `notice` 提示与 `reply` 回答尾部持久注入常驻说明：“知识库已关闭，未查询公司资料库”；③ 系统 Prompt 强约束“禁止捏造虚假公司资质与业绩” |
| AC-03 门禁 3：敏感项目强制本地模型隔离 | 通过 | 若项目标记为敏感项目（`sensitive=True` 或 `is_sensitive=True`），强行核查绑定的模型配置：若绑定云端模型或非本地模型，立即拦截并抛出 `DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")`；仅允许本地且允许敏感处理的离线模型（`is_local=True, allow_sensitive=True`）放行 |
| AC-04 门禁 4：只读角色与只读成员提问前置拦截 | 通过 | 严格落实八角色矩阵：集团管理员（`group_admin`）、审计员（`auditor`）、只读成员（`viewer`）与平台管理员（`platform_admin`）4 类系统只读角色，以及在项目团队分工中被指定为 `viewer` 的只读成员，发起自由提问时统一在前置流水线拦截抛出 `DomainError(403, "FORBIDDEN", "只读角色不可使用智能助手提问。")` |
| AC-05 跨租户鉴权隔离与大模型故障映射 | 通过 | 跨租户非法访问项目抛出 `DomainError(404, "NOT_FOUND", ...)`；当后端大模型发生网络异常或不可用时，统一捕获并安全转换为标准的 `502 MODEL_UNAVAILABLE`，不泄漏内部异常堆栈 |
| AC-06 工作流服务 WorkflowService 统一门面委派 | 通过 | `WorkflowService.general_chat` 与 `WorkflowService.ask_assistant` 正确委派至 `AnswerCardService.general_chat`，与已有接口契约及前端交互保持完全兼容 |
| AC-07 OpenAPI 契约与冻结错误码一致性 | 通过 | 契约与权限套件（`test_error_idempotency.py`、`test_eight_roles_access.py`）19 项测试全过，全量 143 个冻结错误码保持 100% 完备无损 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 自由问答专属单测套件 | `python -m pytest tests/backend/test_general_chat_qa.py -v` | **10 passed, 0 failed** (四道安全门禁、跨租户与故障降级全过) | 0.42s |
| 智能助手全套联合单测 | `python -m pytest tests/backend/test_answer_cards.py tests/backend/test_direct_query_fallback.py tests/backend/test_insert_answer_card.py tests/backend/test_general_chat_qa.py -v` | **47 passed, 0 failed** (答案卡、直查回退、插入为引用、自由问答联合测试全绿) | 1.95s |
| 契约与八角色权限单测 | `python -m pytest tests/backend/test_error_idempotency.py tests/backend/test_eight_roles_access.py -v` | **19 passed, 0 failed** (143 冻结错误码完备) | 5.34s |
| 后端全量测试回归套件 | `python -m pytest tests/backend/ -rs` | **532 passed, 37 skipped, 0 failed** (100% 离线纯洁性) | 338.10s |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **“禁止写入正文”的根源性防护**：通过在返回模型中固化 `can_insert=False`、`action="copy_only"` 并在后端切断任何插入接口的合法性路径，彻底杜绝了模型随意自由发挥的回答被意外混入正式投标章节的问题。
2. **知识库关闭状态下的双重防编造机制**：一方面在代码层拦截 RAGFlow 网络外呼，另一方面在系统 Prompt 层注入严格不可编造事实的反虚构指令，确保企业投标的合规严谨性。
3. **敏感项目模型隔离门禁**：通过对项目敏感标志与模型绑定的逐级核验，确保涉密项目数据绝不流向任何外部云端大模型 API，保障国家或企业级保密要求。

## 签署状态

APP-M2-T179 保持 **in-review**，**严禁标 done**。
