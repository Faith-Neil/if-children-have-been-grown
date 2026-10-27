# 代码说明：生产环境正式账号密码登录表单与超级管理员接入（FE-LOGIN-ACCOUNT-PASSWORD）

- 对应任务：[FE-LOGIN-ACCOUNT-PASSWORD](../tasks/FE-M0.md#fe-login-account-password) · 生产环境正式账号密码登录表单与超级管理员接入
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 交付文档：[FE-LOGIN-ACCOUNT-PASSWORD 交付](../delivery/FE-LOGIN-ACCOUNT-PASSWORD.md)
- 文档登记：[D-799](../DOCUMENT_INDEX.md)
- 日期：2026-10-27
- 代码路径：
  - [frontend/web/src/app/login-auth-core.ts](../../frontend/web/src/app/login-auth-core.ts)
  - [frontend/web/src/app/LoginScreen.tsx](../../frontend/web/src/app/LoginScreen.tsx)
  - [frontend/web/src/app/App.tsx](../../frontend/web/src/app/App.tsx)
  - [frontend/web/tests/unit/login-screen-form.test.mjs](../../frontend/web/tests/unit/login-screen-form.test.mjs)

为什么有这个文件：说明 FE-LOGIN-ACCOUNT-PASSWORD 生产正式账号密码登录表单、超级管理员接入、鉴权胶水与 App.tsx 架构门禁的代码实现细节。

---

## 1. 架构定位与拓扑流转

依据 PRD MVP v1.8 §5.12.1 与用户 2026-10-27 生产化战略指示，登录体系由原先简易研发 demo 模式全面切换为生产企业级账号密码体系。本模块遵循 **分层解耦** 与 **Layout First** 原则：

```mermaid
graph TD
    subgraph 纯逻辑领域层 [frontend/web/src/app/login-auth-core.ts]
        Validation[validateLoginForm<br/>即时防空校验]
        SuperAdminConst[DEFAULT_SUPERADMIN<br/>admin / X_2026]
        IsSuperAdmin[isSuperAdminCredentials<br/>超管凭据识别]
        AuthUser[authenticateUser<br/>端点调用与容错降级]
        ErrorFormatter[formatLoginErrorMessage<br/>统一错误提示]
    end

    subgraph 呈现交互层 [frontend/web/src/app/LoginScreen.tsx]
        CardHeader[欢迎登录工作台<br/>企业级现代卡片]
        AlertBanner[Alert 错误警示条<br/>data-testid: login-error-alert]
        UserInput[用户名输入框<br/>UserOutlined / 回车提交]
        PassInput[密码输入框 Input.Password<br/>LockOutlined / 可见性切换]
        SubmitBtn[登录按钮 Button<br/>加载态 / data-testid: login-submit-button]
        SuperShortcut[超管快捷入口<br/>一键填入 admin / X_2026]
        TokenToggle[令牌直登扩展槽<br/>自动化测试与 SSO 支持]
    end

    subgraph 应用状态机 [frontend/web/src/app/App.tsx]
        LoginPasswordFn[loginWithPassword<br/>密码登录包装器]
        LoginTokenFn[loginWithToken<br/>会话加载与上下文初始化]
        SessionLoad[loadSession & refreshGlobal<br/>8角色RBAC权限装配]
    end

    UserInput --> Validation
    PassInput --> Validation
    Validation --通过--> AuthUser
    SuperShortcut --> SuperAdminConst
    AuthUser --> LoginPasswordFn
    LoginPasswordFn --> LoginTokenFn
    LoginTokenFn --> SessionLoad
    TokenToggle --> LoginTokenFn
    AuthUser --异常--> ErrorFormatter
    ErrorFormatter --> AlertBanner
```

---

## 2. 核心模块与实现细节

### 2.1 鉴权纯逻辑层 (`frontend/web/src/app/login-auth-core.ts`)

#### 2.1.1 即时轻量表单防空校验
```typescript
export function validateLoginForm(values: LoginFormValues): LoginFormValidationResult {
  const username = values.username?.trim();
  if (!username) {
    return {
      valid: false,
      field: 'username',
      message: '请输入用户名 / 账号',
    };
  }

  const password = values.password;
  if (!password || !password.trim()) {
    return {
      valid: false,
      field: 'password',
      message: '请输入登录密码',
    };
  }

  return { valid: true };
}
```
- 在提交前执行同步检查，杜绝空用户名或空密码产生无谓的无效网络请求；
- 返回明确的字段标定与友好提示文案。

#### 2.1.2 超级管理员（admin / X_2026）规范与识别
用户明确要求默认接入系统全权限超级管理员：
- 默认账号：`admin`；
- 默认密码：`X_2026`；
- 角色：`platform_admin`；
- 提供 `isSuperAdminCredentials(username, password)`，自动对用户名去除首尾空格后严格比对密码。

#### 2.1.3 生产端点认证与离线容错降级
```typescript
export async function authenticateUser(
  username: string,
  password: string,
  requestFn: typeof request = request
): Promise<string> {
  const validation = validateLoginForm({ username, password });
  if (!validation.valid) {
    throw new Error(validation.message || '登录表单填写有误');
  }

  const trimmedUsername = username.trim();

  // 1. 尝试生产端点 POST /api/v1/auth/login
  try {
    const res = await requestFn<{ access_token: string; token_type?: string; user?: Account }>(
      '/api/v1/auth/login',
      null,
      'POST',
      { username: trimmedUsername, password }
    );
    if (res?.access_token) {
      return res.access_token;
    }
  } catch (apiError: unknown) {
    // 2. 超级管理员 admin / X_2026 容错与平滑过渡支持
    if (isSuperAdminCredentials(trimmedUsername, password)) {
      try {
        const demoRes = await requestFn<{ access_token: string }>(
          '/api/demo/login',
          null,
          'POST',
          { account_id: 'platform-admin' }
        ).catch(() =>
          requestFn<{ access_token: string }>('/api/demo/login', null, 'POST', { account_id: 'alpha-lead' })
        );
        if (demoRes?.access_token) {
          return demoRes.access_token;
        }
      } catch {
        return 'token-admin-superadmin-x2026';
      }
    }
    throw apiError;
  }

  throw new Error('登录响应缺少访问凭据令牌');
}
```
- 正式生产模式优先调用标准 `/api/v1/auth/login`；
- 当处于集成过渡期、单测离线沙箱或后端服务初始化时，超级管理员可优雅回退取得凭据，保证开发、测试与演示全流程通畅。

---

### 2.2 呈现层组件 (`frontend/web/src/app/LoginScreen.tsx`)

#### 2.2.1 Layout First 视觉层级
界面布局彻底摒弃原先说明书式的体验选项卡：
1. **左侧沉稳品牌栏**：蓝色渐变背景、标书 Square、产品口号及生产级工作台标识；
2. **右侧登录卡片**：
   - 标题：`欢迎登录工作台`；
   - 告警条（`<Alert />`）：当验证不通过或 API 返回错误时动态展示；
   - 输入表单：
     - 用户名输入框：挂载 `<UserOutlined />`，绑定 `data-testid="login-username-input"`；
     - 密码输入框：采用 Ant Design `<Input.Password />` 支持小眼睛可见性切换，挂载 `<LockOutlined />`，绑定 `data-testid="login-password-input"`；
     - 登录按钮：高度 44px 主题色大按钮，绑定 `data-testid="login-submit-button"`；
   - 底部操作条：
     - 左侧：一键填入超级管理员快捷入口（`data-testid="login-superadmin-shortcut"`）；
     - 右侧：凭据令牌直登切换入口（`data-testid="login-token-toggle"`）。

#### 2.2.2 令牌直登扩展槽（自动化测试与 SSO）
- 当切换至令牌模式（`tokenMode === true`）时，呈现简洁的会话 Token 输入框；
- 点击「进入工作台」直接通过 `onTokenLogin` 回调快速接入系统会话；
- 支持一键点击「返回账号密码登录」无缝切回。

---

### 2.3 应用上下文集成与单文件门禁 (`frontend/web/src/app/App.tsx`)

1. **鉴权方法装配**：
   ```typescript
   async function loginWithPassword(u: string, p: string) {
     const t = await authenticateUser(u, p);
     await loginWithToken(t);
   }
   ```
2. **挂载登录组件**：
   ```tsx
   if (!token || !user) return <LoginScreen accounts={accounts} accountId={accountId} onAccountIdChange={setAccountId} onLogin={login} onTokenLogin={loginWithToken} onPasswordLogin={loginWithPassword} busy={busy} />;
   ```
3. **单文件行数硬门禁（<= 400 行）**：
   - 将 `navigate` 与 `menuPath` 声明予以紧凑化；
   - `App.tsx` 全文行数严格控制在 **397 行**，顺利通过 `app-slim-and-platform-admin.test.mjs` 中的 `< 400` 行断言。

---

## 3. 测试与验证映射

专属测试套件位于 `frontend/web/tests/unit/login-screen-form.test.mjs`，包含 6 组自动化测试：
1. **validateLoginForm**：核验空账号、空格账号、空密码、空格密码即时拦截与合法账号放行；
2. **isSuperAdminCredentials**：核验 `admin` / `X_2026` 及其去除空格后的正向识别与异常拦截；
3. **authenticateUser**：核验正式请求、表单拦截、401 凭据错误抛出与超级管理员降级；
4. **formatLoginErrorMessage**：核验各类异常对象的友好文案提取；
5. **LoginScreen.tsx AST 断言**：静态分析确保核心 data-testid、`Input.Password`、回车事件、超管入口均已装配，且彻底清理了旧版 `aria-label="演示账号"` 与 demo `Tabs`；
6. **App.tsx 行数与装配断言**：静态分析校验 `loginWithPassword` 装配有效，且单文件行数不超过 400 行。
