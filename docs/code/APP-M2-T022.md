# 代码说明：平台管理员长任务脱敏视图（APP-M2-T022）

- 对应任务：[APP-M2-T022](../tasks/APP-M2.md#app-m2-t022) · 平台管理员长任务脱敏视图
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 交付文档：[APP-M2-T022 交付](../delivery/APP-M2-T022.md)
- 文档登记：[D-775](../DOCUMENT_INDEX.md)
- 日期：2026-10-27
- 代码路径：
  - [frontend/web/src/shell/task-center.ts](../../frontend/web/src/shell/task-center.ts)
  - [frontend/web/src/shell/TaskCenterDrawer.tsx](../../frontend/web/src/shell/TaskCenterDrawer.tsx)
  - [frontend/web/src/app/SupportPages.tsx](../../frontend/web/src/app/SupportPages.tsx)
  - [frontend/web/src/status/job-progress.ts](../../frontend/web/src/status/job-progress.ts)
  - [frontend/web/src/shell/AppModals.tsx](../../frontend/web/src/shell/AppModals.tsx)
  - [frontend/web/src/app/GlobalPagesContent.tsx](../../frontend/web/src/app/GlobalPagesContent.tsx)
  - [frontend/web/tests/unit/app-slim-and-platform-admin.test.mjs](../../frontend/web/tests/unit/app-slim-and-platform-admin.test.mjs)

为什么有这个文件：说明 APP-M2-T022 平台管理员长任务脱敏视图、重试/取消权限门禁的前端模块架构、脱敏时序与安全保证。

---

## 1. 架构定位与安全防线

在系统多租户架构中，平台管理员（`platform_admin`）不属于任何具体的项目或企业租户，主要负责系统巡检与运维。为贯彻 PRD v1.8 §2.3 / §5.12.4 的隐私合规与防数据外泄红线，前端构建了脱敏展示与只读运维防线：

```mermaid
graph TD
    UserRole[当前会话用户角色] --> CheckRole{isPlatformAdminRole?}
    CheckRole -- 否 --> NormalView[常规租户视图<br/>完整项目名/文件/允许重试取消]
    CheckRole -- 是 --> MaskLogic[maskTaskForPlatformAdmin<br/>数据脱敏过滤]
    MaskLogic --> AlertBanner[呈现 platform-admin-masked-alert 横幅]
    MaskLogic --> MaskProject[项目名 -> '*** (业务项目已脱敏)'<br/>项目ID -> '***']
    MaskLogic --> MaskTitle[sanitizePlatformAdminTitle<br/>标书文件名净化]
    MaskLogic --> StripActions[allowedActions 强制清空<br/>禁用重试/取消/业务跳转]
    MaskLogic --> RetainOps[保留 id/companyId/durationMs/status/progress/traceId]
```

---

## 2. 核心模块与实现细节

### 2.1 纯逻辑脱敏层 (`frontend/web/src/shell/task-center.ts`)

#### 2.1.1 角色判定：`isPlatformAdminRole`
```typescript
export function isPlatformAdminRole(role?: string | null): boolean {
  if (!role) return false;
  return role.trim().toLowerCase() === 'platform_admin';
}
```

#### 2.1.2 标题净化：`sanitizePlatformAdminTitle`
针对任务标题中经常包含的具体文件名（如 `xxx招标文件.pdf`），根据任务类型映射为通用的脱敏描述：
```typescript
export function sanitizePlatformAdminTitle(title: string, type?: string): string {
  if (!title) return '未命名任务 (已脱敏)';
  if (type) {
    const typeLabel = getJobTypeLabel(type);
    return `${typeLabel} (脱敏文件)`;
  }
  return '业务处理任务 (已脱敏)';
}
```

#### 2.1.3 任务全量脱敏：`maskTaskForPlatformAdmin`
安全拦截器，生成隔离的脱敏副本：
```typescript
export function maskTaskForPlatformAdmin(task: TaskItem): TaskItem {
  return {
    ...task,
    projectName: '*** (业务项目已脱敏)',
    projectId: '***',
    title: sanitizePlatformAdminTitle(task.title, task.type),
    allowedActions: [], // 彻底清空所有操作权限
  };
}
```

### 2.2 任务中心抽屉脱敏实现 (`frontend/web/src/shell/TaskCenterDrawer.tsx`)

1. **属性拓展与自适应感知**：
   `TaskCenterDrawer` 接收 `role?: string`，内部通过 `const isPlatform = masked || isPlatformAdminRole(role)` 自动计算脱敏状态；
2. **警示横幅提示**：
   当 `isPlatform` 为 true 时，在抽屉顶部突出显示 `Alert` 横幅：
   ```tsx
   {isPlatform && (
     <Alert
       data-testid="platform-admin-masked-alert"
       type="warning"
       showIcon
       icon={<LockOutlined />}
       message="平台管理员脱敏视图"
       description="业务项目名称与具体标书文件已脱敏，仅保留运维排查信息；操作权限已禁用。"
       style={{ margin: '8px 16px', borderRadius: 4 }}
     />
   )}
   ```
3. **卡片受控渲染**：
   将 `masked={isPlatform}` 传递给每一个 `TaskCenterCard`，卡片内项目名称展示为脱敏文字，且不渲染任何业务重试/取消按钮。

### 2.3 任务中心完整页面实现 (`frontend/web/src/app/SupportPages.tsx` -> `JobsPage`)

1. **表格视图脱敏防护**：
   在 `JobsPage` 中，若检测到 `isPlatformAdminRole(role)`：
   - 顶部同样挂载 `platform-admin-masked-alert`；
   - 列表数据统一由 `maskTaskForPlatformAdmin` 预处理；
   - “所属项目”列标注紫色 `脱敏` 标签与 `公司: {task.companyId}` 租户标；
   - “操作”列隐藏所有按钮，展示文本 `只读运维`。

---

## 3. 权限与网络安全保障

- **只读操作安全**：即使在前端 DOM 中人为移除置灰或模拟点击，`canPerformTaskAction` 检测到 `allowedActions` 为空会坚决拦截调用；
- **Trace ID 保留**：运维排查所必须的 `id`、`traceId` 与 `companyId` 完整保留并支持一键复制，方便运维人员与后台日志对齐追踪，在保障安全的前提下维持高运维效率。
