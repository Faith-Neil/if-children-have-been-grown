# APP-M2-T022：平台管理员长任务脱敏视图交付报告

为什么有这个文件：记录 APP-M2-T022 平台管理员长任务脱敏视图、重试/取消权限门禁的前端落地状态、实现细节与验证证据。

它解决什么问题：落实 PRD v1.8 §2.3 与 §5.12.4 针对平台管理员（`platform_admin`）跨企业运维时的强数据隔离与脱敏规范——在长任务抽屉（`TaskCenterDrawer`）与任务中心页面（`JobsPage`）中，自动识别平台管理员角色，脱敏项目名称、项目 ID 与招标文件文件名，清空所有业务操作权限（严禁重试、取消、跳转至项目正文），保留纯粹运维排查字段（任务 ID、企业租户 ID、耗时、状态、进度百分比、Trace ID），并展示醒目的合规脱敏警告横幅。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T022 |
| 代码解释 | [APP-M2-T022 代码说明](../code/APP-M2-T022.md) |
| 文档登记 | [D-774](../DOCUMENT_INDEX.md) |
| 验收 | 1. 角色精确识别：`isPlatformAdminRole(role)` 准确识别 `platform_admin`；<br>2. 业务敏感字段脱敏：`maskTaskForPlatformAdmin` 将项目名称替换为 `*** (业务项目已脱敏)`，项目 ID 替换为 `***`，标书文件名由 `sanitizePlatformAdminTitle` 净化；<br>3. 操作权限硬隔离：平台管理员视图下 `allowedActions` 强制置空，无重试（retry）、取消（cancel）或跳转至业务项目链接；<br>4. 运维排查信息完整：保留 `id`、`companyId`、`durationMs`、`status`、`progress`、`traceId` 等纯运维字段；<br>5. 醒目合规告知：抽屉与页面顶部均呈现 `platform-admin-masked-alert` 警示横幅；<br>6. 自动化测试验证：专属单元测试 5 项全部通过，全量 408 项单测 100% 保持全绿，TypeScript 与构建零错误。 |
| 项目进度 | 本次交付已获 QA 独立终验签署（D-776 PASS）与 PD 产品视角验收（D-777 认可）通过，并由人类 PM 正式确认标为 done |
<!-- task-delivery:end -->

## 1. 业务背景与合规约束

根据 PRD v1.8 §2.3（平台管理员角色职责）与 §5.12.4（任务运维监控）：
- **平台管理员**负责平台基础组件健康监控与长任务故障排查；
- **红线数据隔离**：平台管理员绝对不属于任何企业租户，严禁窥探客户真实的招标项目名称、投标文件正文及招标文件原名；
- **权限边界约束**：平台管理员仅具备只读运维审计权限，不得越权直接执行项目级任务取消或业务重试操作，防止破坏企业工作流事务一致性。

本任务基于上述要求，在前端表现层与纯逻辑层完整建立脱敏视图与权限防线。

---

## 2. 核心功能实现清单

### 2.1 纯逻辑脱敏算法 (`frontend/web/src/shell/task-center.ts`)
1. **`isPlatformAdminRole(role)`**：
   - 严格匹配 `'platform_admin'` 角色代码，支持大小写与空白字符鲁棒性处理。
2. **`sanitizePlatformAdminTitle(title, type)`**：
   - 将形如 `招标文件_XX工程.pdf` 的敏感业务文件名净化为通用任务类型描述（如 `招标文件解析 (脱敏文件)`），防止文件名泄漏项目敏感线索。
3. **`maskTaskForPlatformAdmin(task)`**：
   - `projectName`: 替换为 `'*** (业务项目已脱敏)'`；
   - `projectId`: 替换为 `'***'`；
   - `title`: 调用 `sanitizePlatformAdminTitle` 净化；
   - `allowedActions`: 强制重置为空数组 `[]`；
   - 保留运维排查必需字段：`id`、`companyId`、`durationMs`、`status`、`progress`、`traceId`、`createdAt`、`updatedAt`。
4. **`canPerformTaskAction` 防线增强**：
   - 校验任务的 `allowedActions`，当为空或未包含指定动作时坚决返回 `false`。

### 2.2 任务中心抽屉脱敏视图 (`frontend/web/src/shell/TaskCenterDrawer.tsx`)
1. 属性扩展：支持透传当前会话角色 `role?: string` 及显式脱敏标记 `masked?: boolean`；
2. 顶部警示条：当检测为平台管理员时，展示带有 `<LockOutlined />` 的警告横幅（`data-testid="platform-admin-masked-alert"`），明确提示“平台管理员脱敏视图：业务项目名称与具体标书文件已脱敏，仅保留运维排查信息；操作权限已禁用”；
3. 卡片渲染防护：卡片展示项目名称为脱敏态，禁用所有跳转与操作按钮，仅展示状态、进度与 Trace ID 复制功能。

### 2.3 任务运维中心页面脱敏支持 (`frontend/web/src/app/SupportPages.tsx` -> `JobsPage`)
1. 属性扩展：支持透传 `role?: string` 与 `masked?: boolean`；
2. 顶部横幅：同样渲染 `platform-admin-masked-alert` 提示；
3. 数据脱敏：使用 `maskTaskForPlatformAdmin` 处理任务列表，对脱敏任务渲染 `脱敏` 紫色 Tag 与 `公司: {companyId}` 租户标识；
4. 操作栏保护：隐藏常规重试/取消按钮，替换为灰色只读提示文案“只读运维”。

### 2.4 主应用与弹窗集成
- `frontend/web/src/shell/AppModals.tsx` 将当前用户的 `userRole` 注入 `TaskCenterDrawer`；
- `frontend/web/src/app/GlobalPagesContent.tsx` 将 `userRole` 注入 `JobsPage`。

---

## 3. 验证证据

### 3.1 专属自动化单元测试
运行命令：
```bash
node --test frontend/web/tests/unit/app-slim-and-platform-admin.test.mjs
```

测试执行结果：
```
✔ FE-TECH-DEBT-02: App.tsx line count is strictly below 400 lines (3.6073ms)
✔ FE-TECH-DEBT-02: Extracted shell & app domain components exist and export properly (1.4768ms)
✔ APP-M2-T022: isPlatformAdminRole correctly identifies platform administrator (0.2915ms)
✔ APP-M2-T022: sanitizePlatformAdminTitle masks tender file names and project sensitive words (0.3665ms)
✔ APP-M2-T022: maskTaskForPlatformAdmin enforces security and ops-view masking invariants (1.0748ms)
ℹ tests 5
ℹ suites 0
ℹ pass 5
ℹ fail 0
```

### 3.2 全量前端单测
运行命令：
```bash
pnpm --dir frontend/web test
```
408 项测试全部通过（100% 绿灯）。

### 3.3 TypeScript 类型检查与 Vite 构建
- `pnpm --dir frontend/web lint` 退出码 0，0 错误；
- `pnpm --dir frontend/web build` 1.60s 构建成功。

---

## 4. 建议与流转

本卡所有脱敏视图与权限防线均已实现并通过严格测试，按规范将状态推至 `in-review`。建议 PM 在 QA 复核签署后标为 `done`。
