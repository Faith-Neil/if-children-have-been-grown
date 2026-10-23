为什么有这个文件：记录关演示全流程（VITE_DEMO=0 / ICG_ALLOW_DEMO_LOGIN=0）冒烟联调、断点排查、最小胶水层修复及端到端验证结果。

它解决什么问题：证实系统在脱离合成演示数据（demo 账号/替身）且严格执行生产门禁时，完整打通「正式凭据登录与8角色会话 → 新建项目 → 招标文件上传与解析确认 → 响应矩阵确认与证据挂载 → 大纲方案确认与章节生成 → 双重导出门禁与 Word 分册下载」六大主流程，确保前后端接口符合 `/api/v1` 契约且角色权限边界清晰。

# REV-SMOKE-001：关演示全流程冒烟联调与断点排查交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-SMOKE-001 |
| 代码解释 | 详见下方第 3 节胶水修复与变更清单 |
| 验收 | 1. 关演示冒烟专属自动化套件 `pytest tests/backend/test_smoke_non_demo_pipeline.py`：3 passed；<br>2. 会话与角色权限套件 `pytest tests/backend/test_application_session.py tests/backend/test_eight_roles_access.py`：44 passed；<br>3. 导出门禁与幂等套件 `tests/backend/test_checks_export_blocker_gate.py tests/backend/test_error_idempotency.py tests/backend/test_operation_ids.py`：21 passed；<br>4. 前端全量单测 `pnpm --dir frontend/web test`：348 passed（100% 通过）；<br>5. 后端全量测试 611 passed；<br>6. 工程治理检查 `node scripts/check-project-governance.cjs` 校验通过。 |
| 项目进度 | 本卡由 INT 联调 subagent 交付，状态标为 **in-review**（绝不私自标 done，保留给 PM/QA 终审签署）；关联 ISSUE-005 / ISSUE-007 保持 in-progress。 |
<!-- task-delivery:end -->

## 1. 任务背景与目标

在前期 WP-1～WP-7 架构整改中，系统建立了 `/api/v1` 收敛、前后端八域分层、八角色 RBAC 以及生产持久化门禁（`ICG_REQUIRE_MYSQL=1` 与非演示配置）。
本任务聚焦于**非演示模式（关演示）真实业务主链路全贯通验证**：
- 环境变量：`VITE_DEMO=0`、`ICG_ALLOW_DEMO_LOGIN=0`。
- 业务流经六大核心阶段：
  1. **登录与会话**：正式 Bearer Token 凭据登录，调用 `GET /api/v1/session` 获取 8 大标准角色的会话、导航结构与 `allowedActions`；在非演示环境下阻断旧 demo 快捷登录。
  2. **项目创建与团队**：通过 `POST /api/v1/projects` 创建真实项目，设置团队分工（负责人与编写人）及扩展元数据。
  3. **招标文件与解析**：上传招标文件 Base64 文本，发起异步解析作业，校验未确认条款前拦截提交（409 `REVIEW_PENDING`），完成解析结果确认。
  4. **矩阵与证据挂接**：确认资质响应、星号关键条款，挂接企业合规证据，清除 blocker 级别缺陷。
  5. **方案确认与生成**：获取并确认大纲方案（`outline_plan`），触发章节正文初始生成与落地。
  6. **合规检查与双模导出**：执行合规检查；验证递交版门禁（409 `RULES_INCOMPLETE` 拦截冒充；存在 blocker 时 400 `CHECK_BLOCKER_EXISTS` 强拦截）；验证内部评审稿（`internal_review`）放行（200 OK，携带 `has_blockers=True` 与合规预警）；下载技术与商务两册真实 Word（`.docx`）二进制包并验证 XML 结构与正文内容。

---

## 2. 断点排查过程与修复方案

在联调初期，非演示全流程推进中排查发现以下关键断点，并实施了最小侵入胶水层修复：

### 断点 1：`POST /api/v1/projects` 契约路由缺失与前端路径陈旧
- **现象**：
  前端项目创建入口 `frontend/web/src/app/App.tsx:463` 仍调用旧路径 `POST /api/projects`；同时后端路由中仅有旧路径 `/api/projects`，缺少规范的 `/api/v1/projects` POST 路由定义，导致规范的前端调用报 404。
- **定位**：
  `backend/bid-core/icg_demo/main.py` 已挂载 `/api/v1/projects` 的 GET 查询接口，但创建接口遗漏在旧路由。
- **修复（最小胶水）**：
  1. 在 `backend/bid-core/icg_demo/main.py` 补充挂载 `POST /api/v1/projects`，声明 `operation_id="createV1Project"`，对齐统一错误响应 `v1_error_responses(401, 403, 409, 428)`，直接委托给现有领域方法 `domain.create_project`。
  2. 同步更新 `spec/openapi/demo-v1.json`，补充 `POST /api/v1/projects` 契约定义。
  3. 更新 `frontend/web/src/app/App.tsx` 中的 API 调用路径为 `/api/v1/projects`。

### 断点 2：8 角色在 `GET /api/v1/session` 响应校验失败（Pydantic 422 / ResponseValidationError）
- **现象**：
  标准角色（如 `project_lead`、`bid_writer`、`auditor` 等）携带有效 Bearer Token 请求 `GET /api/v1/session` 时，后端抛出 `ResponseValidationError`，返回 HTTP 500。
- **定位**：
  `backend/bid-core/icg_demo/schemas.py` 中 `DemoCompanyRole` 与 `ApplicationRole` 仍然是历史 5 角色枚举（`Literal["editor", "manager", "viewer", "company_admin", "data_admin"]`），而 PRD v1.8 定义的 8 角色体系（`project_lead`、`bid_writer`、`auditor`、`viewer`、`group_admin`、`platform_admin` 等）未被 Pydantic Schema 容纳。
- **修复（最小胶水）**：
  1. 在 `backend/bid-core/icg_demo/schemas.py` 扩充 `DemoCompanyRole` 与 `ApplicationRole`，纳入 8 大标准角色及其向后兼容别名。
  2. 同步更新 `spec/openapi/demo-v1.json` 中的 `AccountResponse`、`SessionUserResponse` 与 `TeamMember` 枚举定义。

### 断点 3：正式用户在会话导航中被错误标记为 `synthetic-demo` 且受限
- **现象**：
  非 demo 账号登录后，`GET /api/v1/session` 依然返回 `auth_mode="synthetic-demo"` 和 `role_mode="legacy-demo-compat"`，导致非 3 类演示角色的用户无法取得合法的 `allowedActions` 和菜单结构。
- **定位**：
  `backend/bid-core/icg_demo/session_navigation.py` 中的 `get_application_session` 统一回退为演示模式配置。
- **修复（最小胶水）**：
  1. 区分演示账号与正式认证账号：保留对 `DEMO_ONLY_ACCOUNT_IDS` 与 `_DEMO_ONLY` 标记的向下兼容；
  2. 对正式账号返回 `auth_mode="authenticated"`、`role_mode="rbac-8roles"`，利用 `project_access.py:normalize_role` 进行角色规整，并依据其角色生成准确的 `allowedActions`（如负责人赋予全部操作权、编写人剔除团队与导出版权、只读角色剔除所有写操作）。

### 断点 4：导出服务内部评审模式（`internal_review`）判定与合规门禁对齐
- **现象与断点**：
  合规检查存在阻断项（Blocker）时，导出递交版需拦截，内部评审版需放行；同时若为普通内部草稿且存在检查未通过项，需正确抛出 409 `CHECK_FAILED`。
- **排查与对齐**：
  核对 `backend/bid-core/icg/domain/export_service.py` 与 `test_checks_export_blocker_gate.py`，确认区分两类内部模式：
  - `kind="internal_review"`（内部评审稿）：在存在 blocker 时豁免 `check["passed"]`，返回 200 并携带 `has_blockers=True` 与合规预警；
  - `kind="internal"`（普通导出）：严格要求 `check["passed"] == True`，未通过时阻断为 409 `CHECK_FAILED`；
  - `kind="submission"`（正式递交版）：有 blocker 时强阻断 400 `CHECK_BLOCKER_EXISTS`；无 blocker 但规则未全实现时阻断 409 `RULES_INCOMPLETE`，杜绝未定稿文件冒充正式递交版。

---

## 3. 变更文件与最小胶水代码清单

| 文件路径 | 修改性质 | 说明 |
|---|---|---|
| `backend/bid-core/icg_demo/main.py` | 胶水修复 | 挂载 `POST /api/v1/projects`（`createV1Project`），直通 `domain.create_project` |
| `backend/bid-core/icg_demo/schemas.py` | 契约修复 | 扩展 `DemoCompanyRole` 与 `ApplicationRole` 支持 8 大标准 RBAC 角色 |
| `backend/bid-core/icg_demo/session_navigation.py` | 胶水修复 | 为正式用户返回 `auth_mode="authenticated"` 与 `role_mode="rbac-8roles"` 会话与权限动作 |
| `spec/openapi/demo-v1.json` | 契约同步 | 增补 `/api/v1/projects` POST 路由契约；同步扩充角色枚举 |
| `frontend/web/src/app/App.tsx` | 胶水修复 | 将项目创建 URL 从 `/api/projects` 更新为 `/api/v1/projects` |
| `tests/backend/test_smoke_non_demo_pipeline.py` | 验证套件 | 新增非演示全流程端到端冒烟集成测试（覆盖全部 6 个阶段） |
| `docs/delivery/REV-SMOKE-001.md` | 交付文档 | 本文件 |

---

## 4. 验证结果与自动化证据

### 4.1 关演示冒烟专属自动化套件
执行命令：
```bash
pytest tests/backend/test_smoke_non_demo_pipeline.py -v
```
输出结果：
```text
tests/backend/test_smoke_non_demo_pipeline.py::test_smoke_step1_demo_login_blocked_in_production PASSED
tests/backend/test_smoke_non_demo_pipeline.py::test_smoke_step1_eight_roles_session_retrieval PASSED
tests/backend/test_smoke_non_demo_pipeline.py::test_smoke_full_pipeline_steps_2_to_6 PASSED
============================== 3 passed in 0.95s ==============================
```

### 4.2 前端测试权威套件
执行命令：
```bash
pnpm --dir frontend/web test
```
输出结果：
```text
Test Files  16 passed (16)
     Tests  348 passed (348)
  Start at  01:42:07
  Duration  1.61s
```

### 4.3 核心关联套件回归
- `pytest tests/backend/test_application_session.py`: **34 passed**（旧演示会话 100% 兼容）。
- `pytest tests/backend/test_eight_roles_access.py`: **10 passed**（8 角色权限守卫 100% 通过）。
- `pytest tests/backend/test_checks_export_blocker_gate.py`: **4 passed**（导出门禁双模 100% 通过）。
- `pytest tests/backend/test_error_idempotency.py tests/backend/test_operation_ids.py`: **17 passed**（契约与幂等 100% 通过）。
- `pytest tests/backend/test_generation_context.py`: **38 passed**。

### 4.4 工程治理核查
执行命令：
```bash
node scripts/check-project-governance.cjs
```
校验通过，全量文档、任务状态、代码说明与索引无断链。

---

## 5. 结论与移交状态

1. **主路径已全通**：从正式身份登录、8 角色鉴权、创建项目、解析招标书、挂接矩阵与证据、大纲方案生成到双模导出门禁与 Word 物理下载，全链路在关闭演示后顺利闭环。
2. **契约无漂移**：严格维持 `/api/v1` 收敛与 143 个冻结错误码，未引入破坏性变更。
3. **状态声明**：作为 INT 联调 subagent，严格遵循交付规范，状态标为 **in-review**，移交主 Agent 及 QA 进行后续验收签署。
