# 为什么有这个文件：记录QA对APP-M2-T183（插入为引用：差异视图、写入、引用标记）的独立复验与签署结论。

# 它解决什么问题：不轻信自报结果，亲手执行专属插入为引用契约单测与答案卡全套联合测试，深度审计四大安全门禁：门禁1编辑锁租约守卫（无锁/过期/非持有者 423 LOCK_LOST）、门禁2卡片类型与资格拦截（本项目数据禁止插入 403 FORBIDDEN、过期 409 EVIDENCE_EXPIRED、未确认 409 EVIDENCE_NOT_USABLE、受限无权 403 FORBIDDEN）、门禁3溯源标记与正文写入（追加/精准替换，生成 [证:ID] 标记，章节与项目 revision 自增）、门禁4增量复查标记与审计历史（incremental_check_status="pending"，章节状态"人工已处理"，版本历史记录 citation，清理草稿，记录审计日志）。

# APP-M2-T183 插入为引用独立复测与 QA 签署

- 被验任务：[APP-M2-T183](../tasks/APP-M2.md#app-m2-t183) · 插入为引用：差异视图、写入、引用标记
- 关联审查任务：REV-M0-T56
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T183 交付](../delivery/APP-M2-T183.md)、[代码解释](../code/APP-M2-T183.md)
- 被验核心文件：`backend/bid-core/icg_demo/answer_card.py`、`backend/bid-core/icg_demo/workflow.py`、`tests/backend/test_insert_answer_card.py`、`tests/backend/test_answer_cards.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**APP-M2-T183 保持 in-review，严禁标 done；关联 ISSUE-007 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 门禁 1 编辑锁租约守卫 | 通过 | `test_gate_1_missing_or_empty_lease`、`test_gate_1_expired_lease`、`test_gate_1_mismatched_token_or_other_user_lease`：无编辑锁、租约已超时、令牌伪造或非当前会话持有者，严格阻断并抛出 `DomainError(423, "LOCK_LOST")` |
| AC-02 门禁 2 本项目数据严格禁插 | 通过 | `test_gate_2_project_data_strictly_forbidden`：本项目结构化数据卡（招标要求、项目事实、响应矩阵、检查结果）无论前端如何传参，一律强行阻断并抛出 `DomainError(403, "FORBIDDEN")`（本项目结构化数据卡禁止插入正文） |
| AC-03 门禁 2 资料资格真实性校验 | 通过 | `test_gate_2_expired_evidence_blocked`（已过期抛出 409 EVIDENCE_EXPIRED）、`test_gate_2_unconfirmed_evidence_blocked`（未确认抛出 409 EVIDENCE_NOT_USABLE）：支持前端标志拦截，同时底层深入核验仓储实体状态，防止前端篡改入参绕过 |
| AC-04 门禁 2 受限资料与跨租户隔离 | 通过 | `test_gate_2_restricted_evidence_unauthorized_blocked`（受限资料普通用户抛出 403 FORBIDDEN）、`test_cross_tenant_and_not_found_isolation`（跨公司资料或跨项目章节抛出 404 NOT_FOUND） |
| AC-05 门禁 3 溯源引用标记与正文写入 | 通过 | `test_insert_answer_card_success_append` 与 `test_insert_answer_card_success_replace`：生成统一可追溯标签 `[证:{item_id}]`；支持 replace 精准替换占位段落与 append 追加；事务内 `chapter.revision` 与 `project.revision` 原子自增 |
| AC-06 门禁 3 SLA 服务承诺格式化 | 通过 | `test_insert_answer_card_sla_template`：SLA 服务承诺正确抽取模板名称与响应级别，生成合规正文与 `[证:ID]` 引用节点 |
| AC-07 门禁 4 增量复查标记与版本审计 | 通过 | 插入成功后，`chapter.incremental_check_status` 变为 `"pending"`，工作流状态流转为 `"人工已处理"`；`workflow["incremental_checks"]` 登记增量任务；`chapter.versions` 记录 `edit_mode="insert_answer_card"` 与 `citation` 明细；清理用户草稿，记录审计日志 |
| AC-08 服务层统一委派与离线纯洁性 | 通过 | `test_workflow_service_delegation`：`WorkflowService.insert_answer_card` 委派正常；全量单测内存级运行，无任何外部网络外呼 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 插入为引用专属单测 | `pytest tests/backend/test_insert_answer_card.py -v` | **12 passed, 0 failed** | 0.13s |
| 答案卡全链路契约联合测试 | `pytest tests/backend/test_answer_cards.py tests/backend/test_direct_query_fallback.py tests/backend/test_insert_answer_card.py -v` | **37 passed, 0 failed** | 0.17s |
| 后端全量测试回归 | `pytest tests/backend/ -q` | **522 passed, 31 skipped, 0 failed** (100% 通过) | 346.93s |

## 签署状态

APP-M2-T183 保持 **in-review**，**严禁标 done**。
