为什么有这个文件：说明八角色权限体系、项目/分册/章节三级授权及跨公司隔离鉴权守卫的实现细节与架构设计。

它解决什么问题：落实 PRD v1.8 §2.2 与 §2.3 权限矩阵，防止只读角色冒充写入，杜绝跨分册与跨公司越权，确保撤权与角色变更即时生效。

# 八角色权限矩阵与鉴权守卫代码说明

- 对应任务：八角色权限体系、[ISSUE-005](../../docs/governance/ISSUE-005-sync.md)、[ISSUE-007](../../docs/governance/ISSUE-007-sync.md)、[交付文档](../delivery/BE-8ROLES-RBAC.md)。
- 关键源文件：
  - [project_access.py](../../backend/bid-core/icg_demo/project_access.py)
  - [domain.py](../../backend/bid-core/icg_demo/domain.py)
  - [project_team.py](../../backend/bid-core/icg_demo/project_team.py)
  - [adapters.py](../../backend/bid-core/icg_demo/adapters.py)
  - [test_eight_roles_access.py](../../tests/backend/test_eight_roles_access.py)

---

## 1. 架构与角色体系定义

依据 [《智能投标系统第一期（MVP）PRD v1.8》](../reference/product/prd-mvp-v1.8.md) §2.2 与 §2.3，系统包含 3 个层级与 8 类系统角色：

| 层级 | 标准角色名 | 职责与权限边界 | 兼容历史别名 |
|---|---|---|---|
| **平台** | `platform_admin` | 平台级字典、模型与服务登记，查看系统运行与审计；默认不看公司业务正文 | - |
| **集团** | `group_admin` | 跨公司只读视角，可查看各公司项目与资料统计，严禁触发生成或写入 | - |
| **公司** | `company_admin` | 管理本公司用户与角色、Word 模板、模型开放，具备新建项目资质 | - |
| **公司** | `data_admin` | 专职维护公司资料库与知识库；非项目成员禁止操作项目章节与矩阵 | - |
| **公司** | `project_lead` | 新建项目、确认解析与矩阵、分配分册/编写人、批准导出递交版 | `manager` |
| **公司** | `bid_writer` | 编写与生成被分配章节、挂接证据、使用对话助手 | `editor` |
| **公司** | `auditor` | 资料与方案片段审核，只读视角 | `reviewer` |
| **公司** | `viewer` | 公司内部项目与资料只读，严禁任何写入或加锁修改 | `readonly` |

项目内分工独立于公司角色：
- **项目负责人 (`lead`)**：全面负责技术分册与商务分册全部章节、大纲调整、团队分工、矩阵确认与终稿导出。
- **分册负责人 (`volume_lead`)**：负责所管辖分册（`technical` 或 `business`），享有本分册所有章节的编辑、加锁接管、批量方案确认与分册检查/导出权限；**严禁越权编辑或接管另一分册的章节**。
- **本节编写人 (`bid_writer`)**：仅享有自身被分配章节的编辑权、草稿保存与加锁权限。

---

## 2. 核心鉴权守卫与逻辑实现

在 [project_access.py](../../backend/bid-core/icg_demo/project_access.py) 中沉淀了标准角色集合、归一化函数与细粒度守卫：

### 2.1 角色归一化与集合分类
```python
ROLE_NORMALIZATION_MAP = {
    "manager": ROLE_PROJECT_LEAD,
    "editor": ROLE_BID_WRITER,
    "viewer": ROLE_VIEWER,
    "readonly": ROLE_VIEWER,
    "auditor": ROLE_AUDITOR,
    "reviewer": ROLE_AUDITOR,
    ...
}

READONLY_SYSTEM_ROLES = {ROLE_GROUP_ADMIN, ROLE_VIEWER, ROLE_AUDITOR, ROLE_PLATFORM_ADMIN}
LEAD_COMPANY_ROLES = {ROLE_PROJECT_LEAD, ROLE_COMPANY_ADMIN}
WRITER_COMPANY_ROLES = {ROLE_BID_WRITER, ROLE_PROJECT_LEAD, ROLE_COMPANY_ADMIN, ROLE_DATA_ADMIN}
```

### 2.2 项目成员可写判定 `writable(state, project_id, user_id)`
1. **多租户隔离**：核验账号存在、项目存在且 `account.company_id == project.company_id`。
2. **只读拦截**：`normalize_role(account.role) in READONLY_SYSTEM_ROLES` 立即返回 `False`。
3. **成员分工校验**：
   - 项目成员角色为 `readonly` 时返回 `False`。
   - 公司管理员和资料管理员在作为成员加入项目后享有可写资质。
   - 普通角色须满足公司角色与项目角色匹配（编写人可写，项目负责人角色须具备公司项目经理/管理员资质）。

### 2.3 细粒度三级守卫函数
- **`require_lead(state, principal, project_id)`**：
  - 检查跨公司访问（不同公司立即抛出 HTTP 403 `FORBIDDEN`）。
  - 阻断只读角色（抛出 HTTP 403 `FORBIDDEN`）。
  - 核对项目负责人分工（非负责人抛出 HTTP 403 `PROJECT_LEAD_REQUIRED`）。
- **`require_chapter(state, principal, chapter)`**：
  - 检查跨公司章节（不同公司抛出 HTTP 403 `FORBIDDEN`）。
  - 检查只读角色（抛出 HTTP 403 `FORBIDDEN`）。
  - 满足下列任一条件方可编辑：① 项目负责人；② 该章节所属分册的分册负责人；③ 被明确分配该章节的编写人。否则抛出 HTTP 403 `CHAPTER_EDITOR_REQUIRED`。
- **`require_volume_owner(state, principal, project_id, volume)`**：
  - 限制仅该分册负责人或项目负责人可以调整/导出该分册；跨分册抛出 HTTP 403 `VOLUME_OWNER_REQUIRED`。
- **`require_project_writer(state, principal, project_id)`**：
  - 跨公司抛出 403 `FORBIDDEN`，只读角色抛出 403 `FORBIDDEN`，未授权可写成员抛出 403 `PROJECT_WRITER_REQUIRED`。
- **`require_data_admin(state, principal)`**：
  - 限制知识库与资料库管理操作仅限 `data_admin` 或 `company_admin`，否则抛出 HTTP 403 `FORBIDDEN`。

---

## 3. 跨模块联动

1. **新建项目权限门禁**（[domain.py](../../backend/bid-core/icg_demo/domain.py) `create_project`）：
   - 调用 `normalize_role(actual.role) in LEAD_COMPANY_ROLES`。
   - 允许 `project_lead`、`manager`、`company_admin` 新建项目；其余角色一律拦截并抛出 HTTP 403 `PROJECT_CREATE_FORBIDDEN`。
2. **知识库/通用写门禁**（[domain.py](../../backend/bid-core/icg_demo/domain.py) `_writer`）：
   - 过滤 `READONLY_SYSTEM_ROLES`，确保 `group_admin`、`viewer`、`auditor` 在所有通用写入入口被拦截为 403 `FORBIDDEN`。
3. **团队成员分配与提升门禁**（[project_team.py](../../backend/bid-core/icg_demo/project_team.py) `update`）：
   - 企图将只读角色提升为编写人或负责人：抛出 422 `MEMBER_ROLE_NOT_WRITABLE`。
   - 企图将普通编写人或资料管理员设为项目负责人：抛出 422 `PROJECT_LEAD_COMPANY_ROLE_REQUIRED`。
4. **撤权即时失效（Instant Revocation）**：
   - 权限判定在每次事务开始时重新从 `DemoState` 读取最新身份与团队成员记录，不沿用客户端传入身份或旧 Token。编写人降级或移出团队后，后续加锁、草稿提交立即被拒。

---

## 4. 自动化测试与覆盖

在 [test_eight_roles_access.py](../../tests/backend/test_eight_roles_access.py) 中落地 10 项严密单测：
- `test_role_normalization_and_aliases`：八角色常量、归一化映射与分类集合测试。
- `test_readonly_roles_forbidden_from_library_write`：只读角色写入拦截测试。
- `test_writable_roles_permitted_by_writer_guard`：可写角色通行测试。
- `test_project_create_permissions`：新建项目角色权限与越权阻断测试。
- `test_volume_lead_isolation_and_cross_volume_rejection`：技术/商务分册负责人跨册编辑与接管阻断测试。
- `test_data_admin_kb_dedicated_and_project_membership_gate`：资料管理员知识库专权与项目成员身份门禁测试。
- `test_cross_company_isolation`：跨公司访问、操作与编辑全面拦截测试。
- `test_revocation_immediately_invalidates_chapter_edit`：撤权即时失效与旧编辑锁拦截测试。
- `test_team_membership_update_role_eligibility`：团队调整角色资质校验测试。
- `test_require_project_writer_boundary`：项目可写边界综合校验测试。
