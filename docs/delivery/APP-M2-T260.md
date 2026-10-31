为什么有这个文件：记录 APP-M2-T260 口令登录补齐的实际交付和测试证据。

它解决什么问题：说明首次登录强制改密、停用公司、统一错误提示、公司密码规则和登录页品牌各做到哪一步，以及还没做的部分。

# APP-M2-T260：口令登录（首次登录强制改密、公司停用、统一错误提示、登录页品牌）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T260 |
| 代码解释 | [APP-M2-T260](../code/APP-M2-T260.md) |
| 验收 | 2026-10-31：管理员新建或重置的账号登录后 `must_change_password=true`，页面进入“设置新密码”，改密前后端对除改密、读密码规则、注销外的所有接口返回 403 PASSWORD_CHANGE_REQUIRED；新密码按本人适用规则（公司账号取本公司安全设置，平台级账号取平台默认）校验，页面与服务端逐项提示同一句话；账号不存在、密码错误、账号停用都返回同一句“账号或密码错误，请核实后重试。”，不再提示剩余次数；连续失败锁定满 15 分钟（`ICG_LOGIN_LOCK_MINUTES`）自动解锁；公司状态存后台，只有平台管理员能停用或启用，停用后该公司账号登录返回 403 COMPANY_DISABLED（凭据正确时才说明），已有会话立即失效；登录页产品名与 Logo 读 `/api/v1/branding`；退出登录让服务端令牌作废。CI `294648d` 五个作业全部通过，见 [验证记录](../testing/2026-10-31-t260-password-login.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T260](../tasks/APP-M2.md#app-m2-t260)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)；PM 决定见 [一期范围的三项决定](../decisions/2026-10-30-phase-one-pm-decisions.md) P1
- 依据：PRD v1.8 §5.12.1 验收①②③④⑤⑦⑧、业务规则 2～4、Q28；字典 v1.9 `sys_user.must_change_password`
- 顺带纠正：[APP-M2-T026](APP-M2-T026.md) A-01 公司管理页原先是写死的示例数据（见下“发现并修复”）

## 实际文件
- 后端：`backend/bid-core/icg/domain/password_login.py`（新）、`company_registry.py`（新）、`security_audit.py`（新；`DemoState.security_audit`，`state_entries` 新增 `security_audit` 范围）；`domain.py`（`Account` 新增 `must_change_password`、`password_changed_at`、`locked_at`，`auth_login`、`authenticate` 重写判定顺序）；`auth_service.py`（字符分类与逐项问题）；`user_management.py`（新建与重置按公司规则校验并置须改密；修改资料改用 `replace`）；`schemas.py`；`errors.py`、`frozen_error_codes.py`（新增 PASSWORD_CHANGE_REQUIRED、COMPANY_DISABLED、OLD_PASSWORD_INCORRECT）；`icg/api/session.py`（`changeOwnPassword`、`getPasswordPolicy`、`authLogout`、`getBranding`）；`icg/api/companies.py`（`listCompanies`、`updateCompanyStatus`）；`icg/app/main.py`（`current_user` 内拦截须改密会话）
- 前端：`frontend/web/src/app/password-change-core.ts`（新）、`PasswordChangeScreen.tsx`（新）、`login-auth-core.ts`、`LoginScreen.tsx`、`App.tsx`、`GlobalPagesContent.tsx`、`session-navigation.ts`（平台超级管理员的 system 范围）、`shared/types.ts`；`src/admin/CompanyManagePage.tsx`（重写）、`company-manage-core.ts`（删除示例公司）
- CI：`.github/workflows/offline-check.yml` backend 作业上传从代码导出的 OpenAPI（`openapi-regenerated`），供不能装依赖的开发机核对契约
- `spec/openapi/demo-v1.json`

## 测试证据
- `tests/backend/test_password_login.py`（8 项，含平台超级管理员会话为 system 范围且启动时读取的五个接口都 200）：新账号须改密且业务接口被拒、原密码错、弱密码逐项问题、新旧相同被拒、改密后可用且审计；重置后须改密、修改资料不清标记；三类失败提示相同且审计记原因；公司调严密码规则后旧密码仍可登录、新建按新规则、低于平台默认的保存被拒、平台账号按平台默认；停用公司：列表权限、非平台管理员 403、未确认名称 422、停用后会话 401 与登录 403、密码错时仍是统一提示、他公司不受影响、启用恢复、审计；锁定 16 分钟后自动解锁；退出后令牌 401、品牌接口无需登录
- `frontend/web/tests/application-session.test.mjs` 新增：只有平台超级管理员可持 system 范围
- 改动的旧用例：`test_user_management_transfer.py`（停用转交审计改读 `security_audit`）、`test_user_security_ops.py`（不再断言“还剩 N 次”，锁定提示改为“账号已锁定，请 15 分钟后重试”）、`test_user_security_ops_glue.py`（重置后新令牌先 403，改密后 200）、`test_user_transfer_rbac_glue.py`（弱密码提示改为逐项措辞）
- `frontend/web/tests/unit/password-change.test.mjs`（6 项）：ASCII 分类、与服务端同一措辞、表单校验、登录与改密与退出只调 `/api/v1/auth/*`、App 须改密时进改密页、公司页不含示例数据；`audit-company-pages.test.mjs` 去掉对示例公司的引用
- `frontend/web/e2e/password-login.spec.ts`（2 项）：新账号登录 → 改密页 → 弱密码就近提示 → 改密进入工作台；平台管理员在公司管理页停用乙公司 → 乙公司登录 403 → 启用恢复（用例结束时无论成败都恢复）
- 本机（无外网，装不了 FastAPI 与前端依赖）只跑了：前端可在本机运行的单测 524 通过、5 项因缺 antd/react 失败（改前改后相同）；新单测 6 项通过；治理检查通过；Python 语法编译通过。后端全量、MySQL、前端类型检查与构建、浏览器用例以 CI 为准

## 发现并修复
- **A-01 公司管理页是空壳**：公司列表写死“华东数智科技有限公司”等两家示例公司（信用代码、法人、人数都是编的）；“停用公司”只改页面状态并提示“名下用户登录已被阻断”，后台没有公司状态，也没有任何接口。合规参数页签的“保存”回调没有接线。现改为读后台列表，停用与启用走后台；公司参数只在“企业设置”页维护
- **修改用户资料会解除锁定**：`update_user` 逐字段新建 `Account`，没带上 `is_locked`、`failed_login_attempts`，改个昵称就把被锁账号解锁了。改为 `replace`
- **退出登录只清前端**：没有注销接口，令牌在服务端一直有效。新增 `POST /api/v1/auth/logout`
- **失败提示暴露账号是否存在**：密码错误提示“还剩 N 次”，账号停用提示“该账号已被停用”，与不存在账号的提示不同
- **平台超级管理员网页登录不进去**：前端可信会话只接受 `scope.kind=company`，而后台给超级管理员的会话是 `system`，登录后会话被判为“无法核验”并退回登录页。现只对 `admin`（公司 `system`、主角色平台管理员）放行 `system` 范围
- **账号安全事件重启即丢**：锁定、重置、解锁、角色调整、停用转交的审计写进章节审计列表且没有事件编号，MySQL 只持久化带编号的章节审计。现单独存入 `security_audit`（按事件编号逐条入库），登录、登录失败、注销、改密、公司停用启用也记在这里
- **密码规则只用固定值**：新建、重置都按 8 位 3 类校验，没读公司的 `password_min_length`、`password_min_char_classes`；字符分类用 `isupper`/`isalnum`，中文算作“字母数字”，与 PRD 口径不一致

## 未实现项与限制
- 品牌设置页（T033/T034）还没有，`/api/v1/branding` 目前总是返回平台默认产品名“智能投标系统”、无 Logo；品牌页做好后写 `service_stores["branding"]["platform"]` 即生效
- `login_lock_minutes`、`login_max_failures` 在 PRD 中是平台设置（§6.9），平台设置页未建：锁定时长用部署变量 `ICG_LOGIN_LOCK_MINUTES`（默认 15），失败次数沿用公司设置 `max_login_attempts`
- 2026-10-31 之前锁定的账号没有锁定时间，不会自动解锁，仍需管理员解锁
- 引导管理员（`admin`）只在生产模式（`ICG_ENV=production`）首次登录时须改密；开发与测试环境的固定初始密码不强制，避免全部用例先改密
- 角色为 `platform_admin` 但账号不是 `admin` 的平台管理员，会话导航里没有管理页（`ROLE_NAVIGATION` 只给 platform 路由，而前端没有 platform 页面），看不到公司管理；这是已有缺口，未在本卡改
- 集团管理员目前看到全部公司（只读），没有按集团过滤：系统里还没有集团与公司的归属数据
- 公司停用后，后台作业、知识库同步等不经登录会话的任务不会被终止；数据保留
- 会话无操作超时（`session_timeout_minutes`）仍归 APP-M2-T011
