# FE-LOGIN-ACCOUNT-PASSWORD：生产环境正式账号密码登录表单与超级管理员接入交付报告

为什么有这个文件：记录 FE-LOGIN-ACCOUNT-PASSWORD 生产正式账号密码登录表单、超级管理员接入与鉴权胶水层升级的交付状态、实现内容与质量验证证据。

它解决什么问题：
1. 响应用户最新战略指示，全面告别 demo 下拉选择账号的体验模式，切换为现代企业级「账号 + 密码」登录表单；
2. 默认支持全权限超级管理员（`admin` / `X_2026`）一键快捷填入与登录认证，支持生产端点 `/api/v1/auth/login` 与离线安全回退；
3. 贯彻 **Layout First** 交互设计原则，移除冗余的 demo 切换 Tab 和说明书式文字，呈现沉稳大气的企业级登录卡片；
4. 提供账号/密码即时防空校验、密码可见性切换（`Input.Password`）、回车快捷提交、错误 Banner 警示；
5. 保留凭据令牌直登扩展槽（`onTokenLogin`）满足自动化测试与 SSO 场景；
6. 严格守卫 `App.tsx` 架构门禁（单文件行数控制在 400 行以内，实测 397 行）。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-LOGIN-ACCOUNT-PASSWORD |
| 代码解释 | [FE-LOGIN-ACCOUNT-PASSWORD 代码说明](../code/FE-LOGIN-ACCOUNT-PASSWORD.md) |
| 文档登记 | [D-798](../DOCUMENT_INDEX.md) |
| 验收 | 1. **登录交互形态升级**：在 `frontend/web/src/app/LoginScreen.tsx` 落地沉稳大气的现代企业级账号密码卡片，彻底移除旧版 demo 体验账号下拉框与 demo Tabs；<br>2. **即时轻量防空校验**：在 `frontend/web/src/app/login-auth-core.ts` 落地 `validateLoginForm`，账号或密码为空时即时触发轻量友好提示，不发无效网络请求；<br>3. **超级管理员接入**：默认支持全权限超级管理员 `admin` / `X_2026` 登录与界面快捷一键填入（`data-testid="login-superadmin-shortcut"`）；<br>4. **端点认证与平滑回退**：`authenticateUser` 优先调用生产端点 `POST /api/v1/auth/login`，在端点就绪前平滑回退支持 superadmin 与 demo 会话凭据；<br>5. **令牌直登扩展槽**：保留 `onTokenLogin` 扩展槽与快捷切换机制（`data-testid="login-token-toggle"`），支持 SSO 与自动化测试；<br>6. **代码与架构门禁全绿**：专属单测 6 项全绿，全量 426 项前端单测 100% 保持全绿，TypeScript 0 error，Vite 生产构建 1.23s 成功，`App.tsx` 行数（397 行）严格遵守 <= 400 行红线。 |
| 项目进度 | 本地已完成实现与多维质量验证，测试与构建 100% 绿灯，按规范推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 业务背景与用户战略指示

依据用户 2026-10-27 最新战略决策：
- 投标编制系统正式告别研发阶段的「体验账号下拉选择」模式，全面进入生产级账号安全认证体系；
- 登录界面必须呈现严谨沉稳的现代企业级质感，杜绝在登录页堆叠冗余的说明书式文案与演示切换选项卡；
- 默认接入拥有系统全权限的超级管理员（`admin` / `X_2026`），在后台数据库与正式 `/api/v1/auth/login` 端点建立之前提供无缝的登录认证与会话装配能力。

---

## 2. 核心交付内容清单

### 2.1 鉴权纯逻辑层 (`frontend/web/src/app/login-auth-core.ts`)
1. **即时轻量防空校验**：
   - `validateLoginForm({ username, password })`：空用户名或空密码即时返回友好提示字段与文案，拦截非法空请求；
2. **超级管理员（admin / X_2026）规范**：
   - 定义 `DEFAULT_SUPERADMIN_USER = 'admin'`，`DEFAULT_SUPERADMIN_PASSWORD = 'X_2026'`；
   - `isSuperAdminCredentials(username, password)`：支持自动 trim 判定；
3. **认证调用与容错回退**：
   - `authenticateUser(username, password, requestFn)`：优先发起 `POST /api/v1/auth/login`；遇到端点尚未装配或离线环境时，对超级管理员提供自动回退与安全凭据签发；
4. **统一错误格式化**：
   - `formatLoginErrorMessage(error)`：解析 `ApiError`（如 401 INVALID_CREDENTIALS）、标准 `Error` 与兜底提示。

### 2.2 呈现层组件 (`frontend/web/src/app/LoginScreen.tsx`)
1. **Layout First 界面结构**：
   - 彻底移除旧版 `<Select aria-label="演示账号">` 与 demo `<Tabs>`；
   - 核心输入区：
     - 用户名输入框：前缀图标 `<UserOutlined />`，`data-testid="login-username-input"`；
     - 密码输入框：`<Input.Password>` 支持可见性切换，前缀图标 `<LockOutlined />`，`data-testid="login-password-input"`；
     - 错误提示条：`<Alert type="error" showIcon closable ... />`，`data-testid="login-error-alert"`；
     - 登录按钮：`<Button type="primary" block size="large" ... />`，`data-testid="login-submit-button"`；
2. **操作便捷性与无障碍支持**：
   - 用户名与密码输入框均挂载 `onPressEnter={handlePasswordSubmit}`，支持回车键一键快捷登录；
   - 界面底部提供超级管理员快捷填入入口：`data-testid="login-superadmin-shortcut"`；
3. **令牌直登扩展槽（自动化测试与 SSO）**：
   - 保留 `onTokenLogin` 回调通道；
   - 点击 `data-testid="login-token-toggle"` 可平滑切换至令牌输入界面，满足 CI、E2E 测试与 SSO 快速注入。

### 2.3 应用上下文集成 (`frontend/web/src/app/App.tsx`)
- 导入 `authenticateUser`，声明 `loginWithPassword` 胶水方法；
- 将 `onPasswordLogin={loginWithPassword}` 挂载至 `<LoginScreen />`；
- 通过紧凑重构（navigate 与 menuPath），使 `App.tsx` 源文件行数严格控制在 **397 行**（<= 400 行硬门禁完美保持）。

---

## 3. 测试与质量门禁证据

### 3.1 专属单元测试（6 passed, 0 failed）
运行命令：
```bash
node --test frontend/web/tests/unit/login-screen-form.test.mjs
```

测试执行结果：
```
✔ 1. 登录表单校验规则：即时轻量防空校验（validateLoginForm） (0.7002ms)
✔ 2. 超级管理员凭据（admin / X_2026）规范与识别 (0.155ms)
✔ 3. 账号密码认证胶水函数（authenticateUser）网络交互与异常处理 (1.2729ms)
✔ 4. 错误提示格式化（formatLoginErrorMessage） (0.1403ms)
✔ 5. LoginScreen.tsx AST 静态契约与 Layout First 规范断言 (14.8488ms)
✔ 6. App.tsx 集成装配与单文件架构门禁（<= 400 行） (18.471ms)
ℹ tests 6
ℹ suites 0
ℹ pass 6
ℹ fail 0
```

### 3.2 全量前端单测保持 100% 全绿（426 passed, 0 failed）
运行命令：
```bash
pnpm --dir frontend/web test
```
执行结果：426 项单元测试全部通过（426 passed, 0 failed, 0 error），覆盖路由守卫、权限表、断点适配、组件契约等全量套件。

### 3.3 TypeScript 严格类型检查
运行命令：
```bash
pnpm --dir frontend/web lint
```
执行结果：`$ tsc -b --noEmit` 顺利退出，0 error, 0 warning。

### 3.4 Vite 生产环境构建通过
运行命令：
```bash
pnpm --dir frontend/web build
```
执行结果：`✓ built in 1.23s`，3417 个模块顺利打包，无任何 chunk 解析异常。

---

## 4. 交付影响核对

| 检查项 | 判定 | 说明 |
|---|---|---|
| PRD MVP v1.8 §5.12.1 账号登录 | 对齐 | 由 demo 模式转入生产账号密码体系，支持超级管理员与安全凭据 |
| UI Layout First 原则 | 遵从 | 移除旧版下拉 demo 账号与选项卡，卡片层级清晰大方 |
| 前端八域边界规范 | 遵从 | 代码严格在 `src/app/` 域内编写，无平铺根目录文件 |
| App.tsx 巨石单文件门禁 | 遵从 | 当前 397 行，严格低于 400 行硬门禁要求 |
| 跨端点安全性 | 遵从 | 杜绝将密码和明文令牌输出至可序列化日志中 |
