# APP-M2-T025：扩展字段与公司设置键表单框架交付报告

为什么有这个文件：记录 APP-M2-T025 扩展字段与公司设置键表单框架（CompanySettingsPage 与 company-settings-core）的交付状态、实现内容与质量验证证据。

它解决什么问题：
1. 落地管理后台「A-05 扩展字段与公司设置」真实业务界面与领域逻辑，替换原有 `admin.rules` 下的 `PendingPage` 占位壳；
2. 严格落实 PRD MVP v1.8 §5.10.3、§6.9 与交接约束 M1-P09-F3 核心红线：“**越界提示平台上下限，公司设置只能调严不能调宽**”（如密码最小长度不低于 8 位，字符种类不低于 3 种，整本导出门禁强制启用）；
3. 严格落实规范 9.11 排他编辑锁三元数学约束（`自动保存 <= 心跳续期`、`心跳 * 10 <= 租约超时`、`租约超时 >= 5 分钟`），防止并发冲突与防抖死锁；
4. 全面覆盖 5 大设置维度（账号安全策略、编辑协同与排他锁、导出交付与合规红线、大纲规划与 AI 预算、自定义扩展字段）；
5. 落实标准 8 角色 RBAC 权限感知：平台管理员与公司管理员享有完整编辑/保存与字段维护权，业务角色严格只读并提示；
6. 践行 **Layout First** 交互设计原则：采用卡片概览 + 5 维选项卡分类布局，以清晰视觉流与内联上下限标签自然表达规范，杜绝说明书式冗余长文案。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T025 |
| 代码解释 | [APP-M2-T025 代码说明](../code/APP-M2-T025.md) |
| 文档登记 | [D-808](../DOCUMENT_INDEX.md) |
| 验收 | 1. **5 大设置维度覆盖**：账号安全、编辑锁三元协同、导出门禁与本地模型、大纲与 Token 预算、自定义扩展字段；<br>2. **只能调严不能调宽红线**：密码长度 >= 8、字符种类 >= 3，低于平台基线严格校验拦截；整本导出门禁强制启用置灰锁定；<br>3. **9.11 编辑锁三元约束**：`editor_autosave_seconds <= edit_lock_heartbeat_seconds`、`edit_lock_heartbeat_seconds * 10 <= edit_lock_timeout_minutes * 60`、`edit_lock_timeout_minutes >= 5`；<br>4. **8 角色 RBAC 权限感知**：平台/公司管理员可编辑保存，其他角色严格只读，提示条明确标示只读权限；<br>5. **自定义扩展字段管理**：支持查看预置扩展字段，弹窗安全录入 `custom_*` 键、字段名称、数据类型与适用范围；<br>6. **无占位壳真实挂载**：在 `GlobalPagesContent.tsx` 动态挂载，彻底清除 `settings` 页签下的 `PendingPage`；<br>7. **全套自动化测试全绿**：专属单测 7 项全绿，全量 433 项前端单测 100% 通过，TypeScript 0 error，Vite 生产构建 1.31s 通过。 |
| 项目进度 | 本地已完成实现与权威质量验证，测试与构建 100% 绿灯，按规范推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 业务背景与规范红线

依据 PRD MVP v1.8 §5.10.3、§6.9、交接约束 §6.2 M1-P09-F3 以及技术规范 9.11：
- **公司安全只能调严不能调宽**：
  平台设立了系统全局安全底线（如密码长度至少 8 位、字符类型至少 3 类、废标红线整本递交阻断强制开启）。租户公司可以结合自身内控需求提高标准（如要求 12 位、4 类字符），但绝不允许将配置调低至平台基线以下。
- **9.11 排他锁协同三元约束**：
  为避免编辑正文时因网络抖动造成租约意外释放导致双人覆写，排他锁相关配置必须满足三个前置互锁数学公式：
  1. `自动保存间隔 <= 心跳续期间隔`：避免在续期未达成前提前刷盘；
  2. `心跳续期 * 10 <= 租约超时时间（秒）`：保证租约超时至少容纳 10 次心跳重试周期，平抑瞬时网络抖动；
  3. `租约超时时间 >= 5 分钟`：确保撰写人员在租约释放前至少获得足够的超时预警缓冲时间。
- **杜绝 Pending 占位壳**：
  管理后台“规则与设置”中的“公司设置”必须提供真实落地页面与保存重置闭环，杜绝空壳冒充交付。

---

## 2. 核心交付内容清单

### 2.1 纯逻辑与校验层 (`frontend/web/src/admin/company-settings-core.ts`)
1. **平台上下限元数据定义 (`PLATFORM_SETTING_BOUNDS`)**：
   - 明确每个设置项的平台基线值、允许调严方向（`higher_is_tighter` / `lower_is_tighter` / `mandatory_true`）；
2. **初始化配置工厂 (`buildInitialCompanySettings`)**：
   - 预置平台标准默认值与 3 项初始自定义扩展字段（`custom_sla_grade`、`custom_tender_budget_code`、`custom_lead_reviewer`）；
3. **8 角色权限判定 (`checkCompanySettingsPermission`)**：
   - `platform_admin` 与 `company_admin` 享有读写与新增字段权限；
   - `project_lead`、`bid_writer`、`auditor`、`viewer`、`data_admin`、`reviewer`、`readonly` 等角色判定为只读；
4. **严格表单校验器 (`validateCompanySettings`)**：
   - 账号密码策略调严下限检查（`PASSWORD_MIN_LENGTH_TOO_LOW`, `PASSWORD_CHAR_CLASSES_TOO_LOW`）；
   - 9.11 编辑锁三元约束检查（`AUTOSAVE_EXCEEDS_HEARTBEAT`, `HEARTBEAT_RATIO_TOO_LARGE`, `TIMEOUT_BELOW_MINIMUM`）；
   - 导出门禁强制启用检查（`REDLINE_BLOCKING_MUST_BE_TRUE`）；
   - 各数值项边界校验（`SESSION_TIMEOUT_OUT_OF_BOUNDS`, `OUTLINE_DEPTH_OUT_OF_BOUNDS` 等）；
   - 自定义字段重复 key 校验（`CUSTOM_FIELD_KEY_DUPLICATED`）。

### 2.2 呈现层组件 (`frontend/web/src/admin/CompanySettingsPage.tsx`)
1. **Layout First 结构与统计概览卡片 (`company-settings-overview`)**：
   - 顶栏展示：当前租户公司、密码安全等级、排他锁超时租约、已配置扩展字段数，以及当前用户角色权限状态 Badge；
2. **5 大设置维度 Tab 卡片 (`company-settings-tabs`)**：
   - **Tab 1: 账号安全策略 (`security`)**：密码最小长度（内联“平台底线 8 位”Tag）、字符种类数（内联“平台底线 3 类”Tag）、密码轮换过期天数、无操作会话超时时间；
   - **Tab 2: 编辑协同与排他锁 (`collaboration`)**：自动保存周期（秒）、心跳续期间隔（秒）、锁定超时时间（分钟），附带 9.11 互锁计算说明与实时校验提示；
   - **Tab 3: 导出交付与合规红线 (`export`)**：废标红线递交导出门禁（强制开启并锁定，标注“平台强制项不可关闭”）、涉密项目强制使用内网本地模型开关、文档导出动态水印开关与自定义水印文本输入；
   - **Tab 4: 大纲规划与 AI 预算 (`outline`)**：投标大纲最大层级深度限制、章节默认建议字数、单章节 AI 生成上下文 Token 预算上限；
   - **Tab 5: 自定义扩展字段 (`custom_fields`)**：扩展字段定义表格，支持新增自定义字段 Modal 弹窗（字段键 `custom_*`、显示名称、字段类型、适用实体、是否必填），支持删除自定义字段。
3. **操作交互控制**：
   - 底部保存按钮 (`company-settings-save-btn`) 与重置按钮 (`company-settings-reset-btn`)；
   - 只读模式下操作按钮自动禁用，顶部展示友好的只读模式警示条 (`company-settings-readonly-alert`)；
   - 校验异常时顶部醒目展示错误警示列表 (`company-settings-validation-alert`)。

### 2.3 路由与分包集成
- `frontend/web/src/app/route-loaders.ts`：添加 `loadCompanySettings` 异步分包加载函数；
- `frontend/web/src/app/lazy-routes.tsx`：导出 `LazyCompanySettingsPage`；
- `frontend/web/src/app/GlobalPagesContent.tsx`：在 `admin.rules` 下的 Tab `settings`（【A-05 扩展字段与公司设置】）直接挂载 `LazyCompanySettingsPage`，彻底消除原 `PendingPage` 占位壳。

---

## 3. 测试与质量门禁证据

### 3.1 专属单元测试（7 passed, 0 failed）
运行命令：
```bash
node --test frontend/web/tests/unit/company-settings-form.test.mjs
```

测试执行结果：
```
✔ 1. 公司设置初始值构建与平台基线上下限完整性验证 (1.2001ms)
✔ 2. “只能调严不能调宽”核心红线：密码安全策略调宽拦截与调严放行 (0.4285ms)
✔ 3. 9.11 编辑锁三元协同数学约束校验（自动保存 <= 心跳，心跳*10 <= 租期，租期 >= 5分钟） (0.402ms)
✔ 4. 导出合规门禁强制开启约束与数值上下限校验 (0.4246ms)
✔ 5. 8角色RBAC权限感知：平台/公司管理员可编辑，业务角色只读 (0.3592ms)
✔ 6. CompanySettingsPage.tsx AST 静态契约与 testid 布局断言 (16.9205ms)
✔ 7. GlobalPagesContent.tsx 路由装配契约断言：消除 PendingPage 挂载真实设置页 (10.9632ms)
ℹ tests 7
ℹ suites 0
ℹ pass 7
ℹ fail 0
```

### 3.2 全量前端单测保持 100% 全绿（433 passed, 0 failed）
运行命令：
```bash
pnpm --dir frontend/web test
```
执行结果：433 项单元测试全部通过（433 passed, 0 failed），无任何回归破坏。

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
执行结果：
- `✓ built in 1.31s`；
- 异步拆包：`CompanySettingsPage-*.js` 独立生成，体积仅 22.99 kB（gzip 6.78 kB），未对首屏包造成负担。

---

## 4. 交付影响核对

| 检查项 | 判定 | 说明 |
|---|---|---|
| PRD MVP v1.8 §5.10.3 公司设置 | 对齐 | 覆盖安全、排他锁、导出门禁、AI预算与扩展字段全维度 |
| 交接约束 M1-P09-F3 “只能调严” | 对齐 | 平台基线设为不可破底线，越界提供即时错误与平台下限标示 |
| 规范 9.11 编辑锁三元协同公式 | 对齐 | 自动保存、心跳与租期三者互锁校验严密落盘 |
| UI Layout First 原则 | 遵从 | 卡片概览 + 5 维 Tab，内联 Tag 标明平台基线，拒绝长文案堆砌 |
| 前端八域边界规范 | 遵从 | 代码严格置于 `src/admin/` 域内，无平铺根目录文件 |
| 拒绝空壳冒充交付 | 遵从 | 彻底替换 `GlobalPagesContent.tsx` 中 `admin.rules` 的 `PendingPage` |
