为什么有这个文件：交付八角色与项目分工路由守卫、无外呼前置拦截、语义化 403 页面与快捷切换动作的实现、单元测试与构建验证结果。

它解决什么问题：
1. 落地 PRD v1.8 §2.2 / §2.3 八角色系统（`platform_admin`, `group_admin`, `company_admin`, `data_admin`, `project_lead`, `bid_writer`, `auditor`, `viewer`）的前端路由准入判定；
2. 杜绝静默发送越权 API 请求：在路由切页入口（`followPath`, `openProject`, `loadNav`, `loadTab`）前置拦截未授权访问，不向后端发起受保护数据的 API 请求；
3. 落实项目内细粒度分工鉴权：项目负责人拥有全项目权限；分册负责人拥有本分册权限；编写人仅允许编辑被分配的章节正文；
4. 增强 403 页面呈现：呈现明确的角色受限原因解释、目标路径与项目上下文标签，并提供“返回工作台 / 返回可访问首页”与“切换身份”快捷按钮，保留未保存内容提示。

# APP-M2-T014：路由守卫与 403 页交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T014 |
| 代码解释 | [代码解释](../code/APP-M2-T014.md) |
| 验收 | 前端全量 206 项单测全部通过（含 13 项八角色守卫与 AST 契约专项测试）、`pnpm --dir frontend/web build` 生产构建成功（首屏主包 `index-DjT1RwqS.js` 287.78 kB <= 295 kB 门禁，gzip 91.93 kB）；表格驱动 8 角色路由准入、写操作拦截、项目细粒度分工与前置零外呼保证均通过自动化验证 |
| 项目进度 | 标至 in-review。关联 ISSUE-007。依赖 BE-M0-T01（done）、APP-M2-T001（done）、APP-M2-T009（in-review）、BE-8ROLES-RBAC（in-review）。下一任务：按看板推进 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)
- 前置依赖：[BE-M0-T01](../tasks/BE-M0.md#be-m0-t01)（done）、[APP-M2-T001](../tasks/APP-M2.md#app-m2-t001)（done）、[APP-M2-T009](../tasks/APP-M2.md#app-m2-t009)（in-review）、[BE-8ROLES-RBAC](BE-8ROLES-RBAC.md)（in-review）
- 契约接口：PRD v1.8 §2.2、§2.3、§5.11.9 与 `spec/openapi/demo-v1.json`
- 分支：`feat/opencode-ICG`
- 本地验收状态：本地自动化测试与生产构建全部通过，已按流程标至 `in-review`，等待主 Agent、QA 与项目经理评审，严禁私自标 `done`
- 合入 / 发布状态：未合入生产分支，未发布

## 完成内容与变更文件

1. **`frontend/web/src/shell/route-guard.ts`（新增）**：
   - 定义 8 类标准系统角色枚举与常量；
   - 实现 `normalizeSystemRole(roleOrRoles)`：双向兼容历史 `manager` $\rightarrow$ `project_lead`，`editor` $\rightarrow$ `bid_writer`，`readonly` $\rightarrow$ `viewer`，`reviewer` $\rightarrow$ `auditor`；
   - 角色资质判定：`isReadonlyRole`、`canCreateProject`；
   - 细粒度分工鉴权：`checkChapterEditPermission` 判定项目负责人（全册）、分册负责人（本册）、编写人（被分配章节）与只读成员；
   - 核心路由守卫：`checkRoutePermission`，前置判定全局路由准入、平台管理员隔离、跨公司数据隔离、项目 Tab 权限与章节编辑权限；
   - 语义化拦截原因：`formatForbiddenReason` 友好输出具体角色受限原因。

2. **`frontend/web/src/shell/RouteGuard.tsx`（新增）**：
   - 封装声明式路由守卫组件，前置调用 `checkRoutePermission`；
   - 校验未通过时渲染语义化 403 页面，提供“返回可访问首页”与“切换身份”快捷按钮。

3. **`frontend/web/src/status/StatusViews.tsx` 与 `status-views.ts`（修改）**：
   - `Forbidden403` 组件扩充 `onSwitchRole` 与 `switchRoleText` 属性；
   - 在操作按钮区统一渲染带有 `data-testid="forbidden-switch-role-button"` 的快捷按钮；
   - `resolveForbidden` 补齐对应字段解析。

4. **`frontend/web/src/app/App.tsx`（修改）**：
   - 在切页与导航入口（`followPath`, `openProject`, `loadNav`, `loadTab`）调用 `checkRoutePermission` 前置核验；
   - 校验失败时直接设置 `denied` 与 `deniedDetails`，立即阻断，不调用 `readAuthorizedProject` 或 `request`，确保零越权外呼；
   - 新建项目时调用 `canCreateProject` 进行前置资质校验；
   - 403 页面提供当前角色、目标路径、项目上下文标签以及【切换身份】与【返回可访问首页】按钮。

5. **`frontend/web/tests/app-orchestration.test.mjs`（修改）**：
   - 为 VM 沙箱环境扩展注入 `route-guard` 导出符号与 `setDeniedDetails`，保证 VM 单测平稳通过。

6. **测试套件（新增）**：
   - `tests/frontend/route-guard.test.mjs`：表格驱动 8 角色路由准入、写拦截、项目细粒度分工、零外呼保证与 403 状态解析；
   - `frontend/web/tests/route-guard.test.mjs`：静态 AST 结构断言与守卫模块契约完整性测试。

## 验收验证结果

### 1. 前端自动化测试全量通过
执行命令：
```powershell
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
测试结果：
- **206 passed, 0 failed**（100% 通过，耗时约 2.18s）。
- 包含 9 项表格驱动路由守卫单元测试与 4 项 AST 结构契约断言，全部通过。

### 2. 生产构建与包体积门禁验证
执行命令：
```powershell
pnpm --dir frontend/web build
```
产物指标：
```
dist/assets/index-DjT1RwqS.js                287.78 kB │ gzip:  91.93 kB
dist/assets/project-team-DJIscAnz.js         294.79 kB │ gzip:  90.01 kB
dist/assets/AppShell-GdL2sO9o.js             223.69 kB │ gzip:  73.43 kB
dist/assets/ProjectPages-vdEqTiqm.js         116.10 kB │ gzip:  34.97 kB
dist/assets/EditorPage-DipTdhtU.js            94.75 kB │ gzip:  30.80 kB
```
- **首屏主包指标**：`dist/assets/index-DjT1RwqS.js` 体积为 **287.78 kB**，严格控制在 **<= 295 kB** 红线门禁之内，结余 7.22 kB 预算。

### 3. 工程治理合规检查
执行命令：
```powershell
node scripts/check-project-governance.cjs
```
检查结果：
- 治理检查通过，Markdown、任务看板与 Issue 状态完全一致。
