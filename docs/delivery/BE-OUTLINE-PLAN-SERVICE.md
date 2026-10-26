为什么有这个文件：记录大纲写作方案服务（BE-OUTLINE-PLAN-SERVICE）的交付内容、测试结果与架构状态。

它解决什么问题：证实后端已实现基于【方向 B（大纲与章节树协同编辑）】的大纲写作方案服务与持久化接口，具备分册结构化大纲树读取、星号/废标条款标记不适用的绝对拦截红线（400 INVALID_ACTION）、八角色与分册负责人跨分册权限隔离（403 FORBIDDEN）、单事务章节与项目 revision 原子自增、以及纯内存多态透明降级。

# BE-OUTLINE-PLAN-SERVICE：大纲写作方案服务与持久化接口交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-OUTLINE-PLAN-SERVICE |
| 代码解释 | 详见 [代码解释](../code/BE-OUTLINE-PLAN-SERVICE.md) |
| 验收 | 自动化测试套件 `pytest tests/backend/test_outline_plan_service.py` 覆盖结构化大纲树生成、星号/废标条款禁止标记不适用安全门禁（400 INVALID_ACTION）、八角色三级授权与分册负责人越界拦截（403 FORBIDDEN）、单事务原子版本推进（chapter revision += 1, project revision += 1）、分册批量确认与纯内存仓库透明多态；核心契约与全量测试 100% 通过。 |
| 项目进度 | BE-OUTLINE-PLAN-SERVICE 标为 in-review，绝不私自标 done；关联 ISSUE-007 / ISSUE-018 保持 in-progress。 |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-22。
- 业务标准：PRD v1.8 §5.7 大纲写作方案、架构决策：方向 B（大纲与章节树协同编辑）。
- 关联问题：[ISSUE-007](../../issues/ISSUE-007.md)（项目主流程）、[ISSUE-018](../../issues/ISSUE-018.md)（数据持久化与工作流）。
- 依赖前置：BE-WORKFLOW-JOB-PERSISTENCE（工作流持久化）、BE-8ROLES-RBAC（八角色权限校验）。
- 交付状态：**in-review**（待主 Agent 与 QA 审查签署，严禁私自标 done 或关闭 Issue）。

## 2. 交付成果与变更清单

1. **大纲写作方案服务核心实现**（`backend/bid-core/icg_demo/outline_service.py`）：
   - `OutlinePlanError`：继承自 `DomainError`，提供 `status=400` 与 `code="INVALID_ACTION"` 专属业务异常，严格保持 143 个冻结错误码完备无漂移。
   - `infer_chapter_type`：实现章节分类推断算法，将章节识别为 `general`（通用）、`specialized`（专项）或 `system`（系统生成）。
   - `get_outline_plan`：读取项目结构化大纲树，支持 `technical` / `business` 分册过滤与节点扩展（包含 `section_number`、`level`、`chapter_type`、`value_added_reason`、`associated_clause_ids`、`has_asterisk`、`has_disqualified`、`is_mandatory`、`assignee_id`、`assignee_name`、`confirmation_status`、`revision`）。
   - `confirm_outline_plan`：
     - **安全门禁**：星号条款（★）与废标条款绝对禁止被标记为“不适用”（`applicable=False` 或 `action="mark_not_applicable"`），强行拦截并抛出 400 `INVALID_ACTION`；
     - **权限门禁**：系统只读角色与项目只读成员拦截 403 `FORBIDDEN`；分册负责人仅限确认所辖分册，跨分册操作拦截 403 `FORBIDDEN`；项目负责人放行全部分册；
     - **原子事务**：单事务内完成章节 `revision` 自增（`revision += 1`）、版本快照归档、项目 `revision` 自增及 `workflow["outline_plans"]` 持久化联动。
2. **工作流门面集成**（`backend/bid-core/icg_demo/workflow.py`）：
   - 在 `WorkflowService.__init__` 中挂载 `self.outline = OutlinePlanService(demo)`；
   - 暴露 `get_outline_plan` 与 `confirm_outline_plan` 快捷方法。
3. **自动化测试套件**（`tests/backend/test_outline_plan_service.py`）：
   - 编写 6 项全方位自动化测试：大纲树与元数据读取、星号/废标条款禁止不适用红线、八角色与分册隔离权限门禁、原子版本号递增、分册批量确认、纯内存多态透明降级。
4. **文档与治理**：
   - 编写代码架构文档 `docs/code/BE-OUTLINE-PLAN-SERVICE.md`；
   - 编写交付文档 `docs/delivery/BE-OUTLINE-PLAN-SERVICE.md`；
   - 索引更新登记至 `docs/DOCUMENT_INDEX.md`。

### 文件变更清单：
- `backend/bid-core/icg_demo/outline_service.py`（新增）
- `backend/bid-core/icg_demo/workflow.py`（修改）
- `tests/backend/test_outline_plan_service.py`（新增）
- `docs/code/BE-OUTLINE-PLAN-SERVICE.md`（新增）
- `docs/delivery/BE-OUTLINE-PLAN-SERVICE.md`（新增）
- `docs/DOCUMENT_INDEX.md`（更新登记）

## 3. 验收验证

- **大纲写作方案专属单测**：
  - `pytest tests/backend/test_outline_plan_service.py` -> **6 passed in 0.10s** (100% 通过)。
- **核心契约与冻结错误码验证**：
  - `pytest tests/backend/test_error_idempotency.py` -> **9 passed**（143 个冻结错误码完全一致，无任何新增或删除）。
  - `pytest tests/backend/test_outline_contract_draft.py` -> **6 passed**。
- **权限与异步任务基线回归**：
  - `pytest tests/backend/test_eight_roles_access.py` -> **10 passed**。
  - `pytest tests/backend/test_recoverable_jobs.py` -> **5 passed**。
- **纯内存多态离线保证**：
  - 在未设置 `ICG_DATABASE_URL` 时，服务通过 `MemoryRepository` 保证全功能离线可用与事务安全。
- **项目治理检查**：
  - `node scripts/check-project-governance.cjs`。
