为什么有这个文件：记录QA对BE-8ROLES-RBAC / REV-M0-T49（八角色权限矩阵与鉴权守卫）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手执行八角色权限矩阵专项测试、权限回归套件与全量单测，核查 PRD v1.8 §2.2 与 §2.3 核心要求：八角色标准定义与历史别名兼容、只读角色写拦截（403 FORBIDDEN）、新建项目资质强校验（403 PROJECT_CREATE_FORBIDDEN）、技术与商务分册隔离与跨分册越权阻断（403 CHAPTER_EDITOR_REQUIRED / 403 VOLUME_OWNER_REQUIRED）、资料管理员专职化与项目成员准入、跨公司多租户隔离、撤权即时失效与团队成员资质更新校验。

# BE-8ROLES-RBAC 八角色权限矩阵与鉴权守卫独立复测与 QA 签署（REV-M0-T49）

- 被验任务：[BE-8ROLES-RBAC](../delivery/BE-8ROLES-RBAC.md) · 八角色权限矩阵与鉴权守卫
- 关联审查任务：REV-M0-T49
- 关联交付：[BE-8ROLES-RBAC 交付](../delivery/BE-8ROLES-RBAC.md)、[代码解释](../code/BE-8ROLES-RBAC.md)
- 关联 Issue：[ISSUE-005](../../issues/ISSUE-005.md)、[ISSUE-007](../../issues/ISSUE-007.md)
- 被验核心文件：`backend/bid-core/icg_demo/project_access.py`、`backend/bid-core/icg_demo/domain.py`、`backend/bid-core/icg_demo/project_team.py`、`backend/bid-core/icg_demo/adapters.py`、`spec/openapi/demo-v1.json`、`tests/backend/test_eight_roles_access.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**BE-8ROLES-RBAC 保持 in-review，严禁标 done；关联 Issue 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 八角色标准定义与别名归一化 | 通过 | `test_role_normalization_and_aliases`：8 类系统角色（`platform_admin`、`group_admin`、`company_admin`、`data_admin`、`project_lead`、`bid_writer`、`auditor`、`viewer`）准确归一；历史别名双向兼容（`manager`->`project_lead`、`editor`->`bid_writer`、`readonly`/`viewer`->`viewer`、`reviewer`/`auditor`->`auditor`） |
| AC-02 只读角色写操作全面阻断 | 通过 | `test_readonly_roles_forbidden_from_library_write`：`group_admin`、`viewer`、`auditor`、`platform_admin` 在 `_writer` 与 `ensure_not_readonly` 统一拦截，抛出 HTTP 403 `FORBIDDEN`；`test_writable_roles_permitted_by_writer_guard`：可写角色（负责人、编写人、管理员、资料员）平稳放行 |
| AC-03 新建投标项目资质强门禁 | 通过 | `test_project_create_permissions`：仅 `LEAD_COMPANY_ROLES`（`project_lead`、`company_admin`、`manager`）允许创建项目；编写人、资料员、只读与集团管理员新建均被强拦截，返回 HTTP 403 `PROJECT_CREATE_FORBIDDEN` |
| AC-04 技术与商务分册严格隔离 | 通过 | `test_volume_lead_isolation_and_cross_volume_rejection`：技术分册负责人对其分册内章节有编辑权；越权编辑商务分册章节抛出 HTTP 403 `CHAPTER_EDITOR_REQUIRED`；跨分册执行确认抛出 HTTP 403 `VOLUME_OWNER_REQUIRED`；项目负责人统管两册放行 |
| AC-05 资料管理员专职化与项目分工 | 通过 | `test_data_admin_kb_dedicated_and_project_membership_gate`：`data_admin` 专职负责知识库/资料库（`require_data_admin` 放行）；非项目成员禁止编辑项目章节（403 `CHAPTER_EDITOR_REQUIRED`）；加入项目并分配编写人角色后按分工授权放行 |
| AC-06 跨公司多租户隔离 | 通过 | `test_cross_company_isolation`：跨租户账号访问异企项目、章节或执行负责人操作时，`require_same_company`、`require_lead`、`require_chapter` 均强制抛出 HTTP 403 `FORBIDDEN` |
| AC-07 撤权即时失效与团队维护资质 | 通过 | `test_revocation_immediately_invalidates_chapter_edit`：编写人降级为只读成员后，即使持有未过期有效租约，再次提交草稿立即被拒（403 `CHAPTER_EDITOR_REQUIRED`）；`test_team_membership_update_role_eligibility`：拦截只读角色提升为编写人（422 `MEMBER_ROLE_NOT_WRITABLE`）、拦截非负责人角色担任项目负责人（422 `PROJECT_LEAD_COMPANY_ROLE_REQUIRED`） |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 八角色权限矩阵专属测试 | `python -m pytest tests/backend/test_eight_roles_access.py -v -rs` | **10 passed, 0 failed** | 0.18s |
| 权限关联回归测试套件 | `python -m pytest tests/backend/test_project_assignments.py tests/backend/test_application_session.py tests/backend/test_demo.py tests/backend/test_v1_lease.py tests/backend/test_lease_review.py -rs` | **119 passed, 0 failed** | 79.21s |
| 冻结错误码一致性核查 | `python -m pytest tests/backend/test_error_idempotency.py -v -rs` | **9 passed, 0 failed** (143 个冻结错误码全量吻合) | 5.66s |
| 项目工程治理核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **三级细粒度守卫层次清晰**：`project_access.py` 将权限清晰拆解为系统/公司级（`READONLY_SYSTEM_ROLES`、`LEAD_COMPANY_ROLES`）、项目级（`writable`、`require_lead`、`require_project_writer`）与分册/章节级（`chapter_edit`、`require_volume_owner`、`require_chapter`），防御纵深完备。
2. **租约与撤权联动即时生效**：编辑租约不仅在加锁时检查角色，在 `save_draft` 保存草稿的每一帧提交中均会动态调用 `require_chapter` 校验当前最新会话与团队分工，杜绝了持有合法租约后在被撤权期间继续篡改文档的漏洞。
3. **OpenAPI 与冻结错误码完全保真**：`spec/openapi/demo-v1.json` 与代码模型定义完全吻合，所有 143 个冻结错误码命名未受破坏，无未授权新增或重命名。

## 签署状态

BE-8ROLES-RBAC / REV-M0-T49 保持 **in-review**，**严禁标 done**。
