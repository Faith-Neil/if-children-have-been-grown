为什么有这个文件：记录八角色权限矩阵、项目/分册/章节三级授权与跨公司隔离鉴权守卫的交付结果。

它解决什么问题：证实后端已完整落地 PRD v1.8 §2.2 与 §2.3 所述的八角色权限规范，提供向后兼容、只读阻断、分册隔离与撤权即时失效保障。

# BE-8ROLES-RBAC：八角色权限矩阵与鉴权守卫交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-8ROLES-RBAC |
| 代码解释 | 详见 [代码解释](../code/BE-8ROLES-RBAC.md) |
| 验收 | `pytest tests/backend/test_eight_roles_access.py`：10 passed；全量后端单测 `pytest tests/backend`：478 passed，17 skipped（仅跳过未启动的真实 MySQL 用例）。 |
| 项目进度 | BE-8ROLES-RBAC 标为 in-review，绝不私自标 done；关联 ISSUE-005 / ISSUE-007 保持 in-progress。 |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-21。
- 业务标准：[PRD v1.8 §2.2 与 §2.3](../reference/product/prd-mvp-v1.8.md)。
- 关联问题：[ISSUE-005](../governance/ISSUE-005-sync.md)、[ISSUE-007](../governance/ISSUE-007-sync.md)。
- 交付状态：**in-review**（待主 Agent 与 QA 审查签署，严禁私自标 done 或关闭 Issue）。

## 2. 交付成果与变更文件清单

1. **八角色体系与细粒度守卫**（`backend/bid-core/icg_demo/project_access.py`）：
   - 定义 8 类标准系统角色：`platform_admin`、`group_admin`、`company_admin`、`data_admin`、`project_lead`、`bid_writer`、`auditor`、`viewer`。
   - 建立双向向后兼容映射：`manager` -> `project_lead`，`editor` -> `bid_writer`，`viewer`/`readonly` -> `viewer`，`auditor`/`reviewer` -> `auditor`。
   - 升级 `writable(state, project_id, user_id)`，严格阻断只读角色（`group_admin`, `viewer`, `auditor`, `platform_admin`）。
   - 增强 `require_lead`、`require_chapter`、`require_volume_owner`、`require_project_writer`、`require_data_admin` 与 `require_same_company`。
2. **领域业务写拦截与新建项目资质**（`backend/bid-core/icg_demo/domain.py`）：
   - `_writer` 统一使用 `normalize_role` 与 `READONLY_SYSTEM_ROLES` 拦截。
   - `create_project` 严格限定仅 `LEAD_COMPANY_ROLES`（`project_lead`、`manager`、`company_admin`）可建项目，非负责人抛出 HTTP 403 `PROJECT_CREATE_FORBIDDEN`。
3. **团队管理资质拦截**（`backend/bid-core/icg_demo/project_team.py`）：
   - 拦截只读角色提升为负责人或编写人（抛出 HTTP 422 `MEMBER_ROLE_NOT_WRITABLE`）。
   - 拦截普通编写人或资料管理员担任项目负责人（抛出 HTTP 422 `PROJECT_LEAD_COMPANY_ROLE_REQUIRED`）。
4. **适配器演示账号拓展**（`backend/bid-core/icg_demo/adapters.py`）：
   - 增补 `alpha-company-admin` 与 `alpha-data-admin` 合成账号种子。
5. **契约与 OpenAPI 完整性**（`spec/openapi/demo-v1.json`）：
   - 维护契约与 `create_app().openapi()` 100% 吻合，严格保留 143 个冻结错误码，未新增或变更错误码名称。
6. **自动化回归测试**（`tests/backend/test_eight_roles_access.py`）：
   - 10 个测试用例覆盖角色规范化、只读拦截、项目创建、分册隔离、资料库专职、跨公司隔离、撤权即时失效及团队管理边界。

### 文件变更清单：
- `backend/bid-core/icg_demo/project_access.py`（修改）
- `backend/bid-core/icg_demo/domain.py`（修改）
- `backend/bid-core/icg_demo/project_team.py`（修改）
- `backend/bid-core/icg_demo/adapters.py`（修改）
- `spec/openapi/demo-v1.json`（维护同步）
- `tests/backend/test_eight_roles_access.py`（新增）
- `docs/code/BE-8ROLES-RBAC.md`（新增）
- `docs/delivery/BE-8ROLES-RBAC.md`（新增）
- `docs/DOCUMENT_INDEX.md`（更新登记）

## 3. 验收验证

- **专属单测**：`pytest tests/backend/test_eight_roles_access.py` -> **10 passed in 0.18s**。
- **关联套件**：`pytest tests/backend/test_project_assignments.py tests/backend/test_application_session.py tests/backend/test_demo.py tests/backend/test_v1_lease.py tests/backend/test_lease_review.py tests/backend/test_eight_roles_access.py` -> **129 passed in 57.86s**。
- **全量回归**：`pytest tests/backend` -> **478 passed, 17 skipped in 318.98s**（100% 通过）。
- **工程治理核查**：`node scripts/check-project-governance.cjs` -> 校验通过。
