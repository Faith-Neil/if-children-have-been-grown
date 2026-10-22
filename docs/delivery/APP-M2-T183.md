# 为什么有这个文件：记录 APP-M2-T183 插入为引用功能闭环的交付成果、测试证据与验收结论。
# 它解决什么问题：汇总代码实现、四道门禁流水线、追加与替换写入、引用标记与版本审计、增量复查标记与全量回归验证，供主 Agent 与 QA 团队复核验收。

# APP-M2-T183 插入为引用：差异视图、写入、引用标记交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务目标 | APP-M2-T183 插入为引用：差异视图、写入、引用标记 |
| 关联 Issue | [ISSUE-007](../../issues/ISSUE-007.md) |
| 规范出处 | [PRD v1.8 §5.11.15 规则 4、§5.11.6、§5.11.9](../../docs/reference/product/prd-mvp-v1.8.md) |
| 代码说明 | [APP-M2-T183 代码解释](../code/APP-M2-T183.md) |
| 专属测试套件 | `tests/backend/test_insert_answer_card.py`（12 项全部通过） |
| 联合验证套件 | `tests/backend/test_answer_cards.py` + `tests/backend/test_direct_query_fallback.py` + `tests/backend/test_insert_answer_card.py`（37 项全部通过） |
| 后端全量回归 | 522 passed, 31 skipped (0 failed) in 346.93s |
| 离线纯洁性 | 100% 离线测试，无任何外部网络外呼与不可靠依赖 |
| 当前状态 | in-review（待主 Agent / QA 复核，绝不私自标 done，绝不私自关闭 Issue） |
<!-- task-delivery:end -->

---

## 1. 核心交付内容清单

1. **门禁 1（编辑锁守卫）**：
   - 调用方执行插入操作前，必须持有目标章节的有效独占编辑租约（`lease_token`）；
   - 验证租约存在性、有效期、令牌匹配、会话拥有者一致性；
   - 缺少租约、租约过期、令牌伪造或跨用户/跨会话冲突，严格拦截并抛出标准的 `423 LOCK_LOST`（“编辑权已失效，请重新取得编辑权后再操作”）。

2. **门禁 2（卡片类型与资格拦截）**：
   - **卡片类型白名单**：仅 `source_type="company_library"` 且 `can_insert=True` 的合格公司资料卡允许执行插入；
   - **本项目数据严格禁插**：严禁将本项目结构化数据卡（招标要求、项目事实、响应矩阵、检查结果）插入正文，前置强拦截并抛出 `403 FORBIDDEN`；
   - **资料实体资格双重校验**：查验底层数据库中条目的真实状态，对已过期条目抛出 `409 EVIDENCE_EXPIRED`，未确认条目抛出 `409 EVIDENCE_NOT_USABLE`，受限无权条目抛出 `403 FORBIDDEN`，彻底防止前端篡改入参绕过。

3. **门禁 3（引用标记格式化与正文写入）**：
   - **溯源引用标记**：将资料内容规范化为带可追溯标识的引用节点 `[证:{item_id}]`；
   - **业务场景格式化**：
     - 人员证书：`[证:ID] {人员证书描述}（有效期至 {valid_until}）`
     - 公司资质：`[证:ID] 公司持有{资质名称}（有效期至 {valid_until}）。`
     - 业绩合同：`[证:ID] 公司具备同类业绩：{合同名称}（{合同描述}）。`
     - SLA承诺：`[证:ID] 公司提供 SLA 服务承诺：{模板名}（一级响应时限...）。`
   - **写入模式**：支持 `replace` 精准替换指定段落占位符，支持 `append` 追加至段落后或章节末尾；
   - **版本原子自增**：在仓储事务内将 `chapter.revision` 与 `project.revision` 原子 +1。

4. **门禁 4（增量复查标记与版本审计历史）**：
   - **增量复查触发**：章节标记为 `chapter.incremental_check_status = "pending"`，工作流章节状态流转为 `"人工已处理"`；并在 `workflow["incremental_checks"][chapter.id]` 记录当前最新修订号、引用 ID 与操作类型 `insert_answer_card`；
   - **版本历史变更记录**：向 `chapter.versions` 记录修订版本条目，标记 `edit_mode="insert_answer_card"`、`version_origin="assistant_edit"` 并包含完整 `citation` 结构；
   - **草稿清理与审计**：自动清除当前用户在章节中的本地未提交草稿，写入 `answer_card.insert` 审计日志。

5. **统一门面委派**：
   - 在 `WorkflowService` 顶层统一暴露 `insert_answer_card` 方法，透明委派给 `AnswerCardService`，保持整洁统一的架构外观。

---

## 2. 变更文件清单

- **核心业务逻辑**：
  - `backend/bid-core/icg_demo/answer_card.py`：扩展 `AnswerCard` 声明 `source_type`，在装配中标记 `project_data` 与 `company_library`，实现具备 4 道门禁的 `insert_answer_card` 核心方法。
  - `backend/bid-core/icg_demo/workflow.py`：在 `WorkflowService` 增加 `insert_answer_card` 门面委派方法。
- **专属测试套件**：
  - `tests/backend/test_insert_answer_card.py`：新建 12 项专属单元测试用例，全方位覆盖 4 道门禁、模式分支、SLA 格式化、错误码守卫与跨租户隔离。
- **交付与设计文档**：
  - `docs/code/APP-M2-T183.md`：代码实现机制与门禁流转架构文档。
  - `docs/delivery/APP-M2-T183.md`：本交付验收报告。

---

## 3. 验收测试执行证据

### 3.1 专属单元测试（12 项全部通过）

```bash
pytest tests/backend/test_insert_answer_card.py -v
```

执行结果：
```
tests/backend/test_insert_answer_card.py::test_insert_answer_card_success_append PASSED [  8%]
tests/backend/test_insert_answer_card.py::test_insert_answer_card_success_replace PASSED [ 16%]
tests/backend/test_insert_answer_card.py::test_insert_answer_card_sla_template PASSED [ 25%]
tests/backend/test_insert_answer_card.py::test_gate_1_missing_or_empty_lease PASSED [ 33%]
tests/backend/test_insert_answer_card.py::test_gate_1_expired_lease PASSED [ 41%]
tests/backend/test_insert_answer_card.py::test_gate_1_mismatched_token_or_other_user_lease PASSED [ 50%]
tests/backend/test_insert_answer_card.py::test_gate_2_project_data_strictly_forbidden PASSED [ 58%]
tests/backend/test_insert_answer_card.py::test_gate_2_expired_evidence_blocked PASSED [ 66%]
tests/backend/test_insert_answer_card.py::test_gate_2_unconfirmed_evidence_blocked PASSED [ 75%]
tests/backend/test_insert_answer_card.py::test_gate_2_restricted_evidence_unauthorized_blocked PASSED [ 83%]
tests/backend/test_insert_answer_card.py::test_cross_tenant_and_not_found_isolation PASSED [ 91%]
tests/backend/test_insert_answer_card.py::test_workflow_service_delegation PASSED [100%]

============================= 12 passed in 0.13s ==============================
```

### 3.2 答案卡全链路联合测试（37 项全部通过）

```bash
pytest tests/backend/test_answer_cards.py tests/backend/test_direct_query_fallback.py tests/backend/test_insert_answer_card.py -v
```

执行结果：
```
============================= 37 passed in 0.17s ==============================
```

### 3.3 后端全量回归测试

```bash
pytest tests/backend/ -q
```

执行结果：
```
522 passed, 31 skipped, 32 warnings in 346.93s (0:05:46)
```

---

## 4. 交付物合规自查

- [x] 代码与测试完全满足离线 CI 纯洁性，绝不直连外部端点；
- [x] 错误码完全遵循 `frozen_error_codes.py` 与 `errors.py`，无新增未冻结状态码；
- [x] 严格遵循 `AGENTS.md` 约束，状态标为 `in-review`，绝不私自标 `done`，绝不私自关闭 Issue；
- [x] 遵循 PRD v1.8 §5.11.15 规则 4、§5.11.6、§5.11.9 规范要求。
