# 代码说明：APP-M2-T260 口令登录

为什么有这个文件：说明登录判定顺序、须改密的拦截点、密码规则来源与公司停用的生效方式。

它解决什么问题：以后新增接口、换登录方式或做品牌页、平台设置页时，知道在哪里改、哪些顺序不能动。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T260 |
| 交付文件 | `docs/delivery/APP-M2-T260.md` |
| 影响模块 | `icg/domain/password_login.py`、`icg/domain/company_registry.py`、`icg/domain/domain.py`、`icg/domain/auth_service.py`、`icg/domain/user_management.py`、`icg/api/session.py`、`icg/api/companies.py`、`icg/app/main.py`、`frontend/web/src/app/password-change-core.ts`、`PasswordChangeScreen.tsx`、`login-auth-core.ts`、`LoginScreen.tsx`、`App.tsx`、`src/admin/CompanyManagePage.tsx`、`company-manage-core.ts` |
<!-- code-explanation:end -->

## 登录判定顺序（`DemoService.auth_login`）
1. 账号不存在、生产环境下的合成种子账号、账号停用：一律 401 INVALID_CREDENTIALS，提示 `LOGIN_FAILED_MESSAGE`，原因（`unknown_account` / `synthetic_account` / `account_disabled`）只写审计 `user.login_failed`。
2. 已锁定：`lock_expired` 判断 `locked_at` 是否已满 `login_lock_minutes()`；未满返回 423 ACCOUNT_LOCKED 并写剩余分钟；已满则在事务里解锁（审计 `user.unlock`，operator 为 `system`），继续往下。
3. 核对密码；错误时失败次数加一，达到 `max_login_failures`（公司设置 `max_login_attempts`，默认 5）即锁定并记 `locked_at`，否则 401 统一提示。不再提示剩余次数。
4. 密码正确后才看公司是否停用（`company_disabled`），停用返回 403 COMPANY_DISABLED。顺序不能提前：提前会让“密码随便填”就能知道账号属于停用公司，等于暴露账号存在。
5. 成功：清零失败次数、发令牌、审计 `user.login`；响应带 `must_change_password` 与 `password_policy`。

`authenticate` 每次请求还会检查公司是否停用；停用时 `set_company_status` 已删掉该公司全部会话，这里是第二道。

## 须改密的拦截
`icg/app/main.py` 的 `current_user` 依赖在 `authenticate` 之后调用 `require_password_changed(principal, method, path)`。所有使用登录身份的接口都经过这个依赖（`include_*_routes` 都传入同一个 `current_user`），所以新增接口自动受拦截，不需要逐个加判断。放行名单 `PASSWORD_CHANGE_ALLOWED` 只有 `POST /api/v1/auth/password`、`GET /api/v1/auth/password-policy`、`POST /api/v1/auth/logout`。`/api/v1/session` 不在名单里：前端在须改密时不调用它，直接显示改密页。

须改密标记的来源：`create_user` 新建账号、`reset_password` 管理员重置、生产模式下首次初始化的 `admin`。`change_own_password` 成功后清除，同时删掉本人其他会话（保留当前令牌），审计 `user.change_password`（`forced` 表示是否为强制改密）。

## 密码规则
`policy_for(state, account)`：平台级账号（公司为 `system` 或角色为平台管理员、集团管理员）用平台默认 8 位 3 类；公司账号读 `service_stores["company_settings"][company_id]` 的 `password_min_length`、`password_min_char_classes`，并夹在平台上下限内。只在设置新密码时校验，已有账号的旧密码不受影响（PRD 验收⑦）。

`auth_service.password_problems` 与前端 `password-change-core.passwordProblems` 是同一口径、同一措辞：只认 ASCII `A-Z`、`a-z`、`0-9` 和 `!`～`~` 范围内其他可打印字符；空格、中文、全角字符允许但不计类。长度按码位数（Python `len`、前端 `[...s].length`）。改任何一边都要改另一边，`tests/unit/password-change.test.mjs` 与 `tests/backend/test_password_login.py` 用同一组样例。

`require_strong_password` 抛 422 PASSWORD_WEAK，`details.problems` 为逐项问题，`details.policy` 为适用规则；本人改密时另加“不能与当前密码相同”。

## 公司状态
存 `service_stores["companies"][company_id] = {status, status_changed_at, status_changed_by}`，随其他服务存储进 MySQL（`demo_state_entry`，范围 `service_store`）。没有记录即为启用。公司列表由账号、项目、公司设置与公司状态四处出现过的公司编号合并得出（不含 `system` 与平台级账号）。`set_company_status` 仅平台管理员；停用要求 `confirm_name` 与公司显示名（`company_display_name`）一致，复用 422 CONFIRMATION_REQUIRED。

## 前端
- `App.loginWithPassword` 调 `passwordLogin`；须改密时把令牌放进 `pendingChange` 并渲染 `PasswordChangeScreen`，不调用 `loginWithToken`、不加载会话。改密成功后再走 `loginWithToken`；点“退出登录”时注销该令牌。
- 用户主动退出（顶栏“退出”、403 页“切换身份”）调用 `signOut`：先 `revokeSession` 再本地 `logout`。401 引起的被动退出仍只走本地 `logout`，避免对已失效令牌再发请求（`app-orchestration.test.mjs` 在虚拟上下文中执行 `logout`，不能在其中发请求）。
- `LoginScreen` 挂载时读 `/api/v1/branding`；读不到用“智能投标系统”。
- `CompanyManagePage` 只读 `GET /api/v1/companies`，`can_change_status` 为真才显示“停用/启用”。

## 安全审计
`icg/domain/security_audit.record(state, action, operator=..., **fields)` 在当前事务里写一条 `{id: sec-…, action, operator, timestamp, at, …}` 到 `DemoState.security_audit`（字典，键为事件编号）。MySQL 由 `state_entries.SCOPES["security_audit"]` 逐条存入 `demo_state_entry`。动作：`user.login`、`user.login_failed`（`reason`：unknown_account / synthetic_account / account_disabled / wrong_password / company_disabled）、`user.locked`、`user.unlock`（管理员或 `reason=lock_expired`）、`user.change_password`、`user.logout`、`user.reset_password`、`user.change_role`、`user.deactivate_and_transfer`、`company.disable`、`company.enable`。章节审计 `state.audit` 不再混入这些事件；章节审计接口改用 `event.get("chapter_id")`。A-06 审计日志页尚未读取任何后台数据（仍为页面内示例），接上时从这里读。

## 平台超级管理员的会话
后台 `session_navigation` 给 `admin` 的会话 `scope.kind=system`、`active_company_id=system`。前端 `trustedApplicationSession` 只在 `user.company_id === 'system'` 且 `primary_role === 'platform_admin'` 时接受 system，其余仍要求 company。其他 `platform_admin` 角色账号的会话仍是 company 范围、首页 `/platform`，前端没有该页面（已有缺口）。

## 依赖与限制
无新依赖。锁定时长读部署变量 `ICG_LOGIN_LOCK_MINUTES`（1～1440，默认 15），平台设置页建好后应改为从平台设置读取。
