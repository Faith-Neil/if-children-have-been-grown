# APP-M2-T027：A-02 用户列表、新增与停用前转交安全表单交付报告

为什么有这个文件：记录 APP-M2-T027（A-02 用户管理、新增与停用前转交安全表单）的交付状态、实现内容与质量验证证据。

它解决什么问题：
1. 落地管理后台「A-02 用户与角色管理」现代企业级业务页面与纯逻辑领域层，挂载于 `admin.rules` 选项卡；
2. 呈现多租户环境下的用户与 8 大标准 RBAC 角色列表（用户名、姓名、8 大角色、所属企业、账号状态、负责资产、创建时间）；
3. 落地新增用户表单，严格对齐 8 大标准角色与公司当前密码安全策略（长度 >= 8 位，大写、小写、数字、符号至少 3 类）；
4. 严格落实交接约束 **M1-P10-F2** 核心红线：“**停用前未转交不能停用**”。当待停用用户担任项目负责人、分册主编或负责资料时，系统自动拦截直接停用，引导打开「停用前业务资产强制交接」抽屉，指定同公司正常在职接收人并填写不少于 5 字交接理由后才允许停用；
5. 提供“账号安全设置”面板，严格贯彻 PRD §5.10.2 / Q28 决策定案：“**公司设置只能调严不能调宽**”，低于平台默认值（8 位 / 3 类）严格校验拦截；
6. 落实 8 角色 RBAC 细粒度权限感知：平台超管与公司管理员具备完整操作权限，业务角色严格只读并提示；
7. 践行 **Layout First** 交互设计原则：采用指标统计概览 + 紧凑检索过滤 + 资产状态徽标 + 侧边交接抽屉，杜绝说明书式冗余文案堆砌。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T027 |
| 代码解释 | [APP-M2-T027 代码说明](../code/APP-M2-T027.md) |
| 文档登记 | [D-818](../DOCUMENT_INDEX.md) |
| 验收 | 1. **用户列表与资产呈现**：支持按姓名、账号、角色、状态多维检索，直观呈现负责项目、在编章节与资料资产标签；<br>2. **新增用户表单**：支持选择 8 大标准 RBAC 角色，即时动态校验密码强度（长度 >= 8，字符种类 >= 3），支持账号查重防线；<br>3. **停用前资产强制交接（M1-P10-F2）**：持有未完结资产的用户禁止直接停用；强制指定同公司接收人并填写 >=5 字理由，完成资产过户后方可停用；0 资产用户支持直接二次确认停用；<br>4. **密码策略只能调严不能调宽**：公司密码策略面板支持调高长度与字符种类，低于平台基线严格校验拦截；<br>5. **8 角色 RBAC 权限感知**：平台/公司管理员可操作，业务角色纯只读并显示友好说明条；<br>6. **无占位壳真实挂载**：在 `GlobalPagesContent.tsx` 的 `admin.rules` 下挂载 A-02 用户与角色 Tab，首屏异步分包受控（29.50 kB）；<br>7. **自动化测试 100% 全绿**：专属单测 8 项全绿，全量 445 项前端单测全绿，TypeScript 0 error，Vite 构建 1.25s 成功。 |
| 项目进度 | 本地已完成实现与权威质量验证，测试与构建 100% 绿灯，按规范推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 业务背景与交接规范红线

依据 PRD MVP v1.8 §2.3、§5.10.1、§5.10.2、交接约束 §6.2 M1-P10-F2 以及 Q28 定案：
- **停用前业务资产强制转交红线（M1-P10-F2）**：
  在投标编制过程中，项目总负责人或分册主编账号若在离职或调岗时被直接停用，会导致其名下正在进行的投标项目、在编章节或专属负责的资质业绩资料失去负责人，引发数据孤立和审批死锁。因此，系统设立了强制交接门禁：**名下持有未完结业务资产的用户在完成资产向同公司在职成员转交前，绝对禁止停用！**
- **密码策略“只能调严不能调宽”（Q28 定案）**：
  平台预设了密码安全底线（最少 8 位，包含大写、小写、数字、符号四类中的至少三类）。各公司管理员可以调高标准（如要求 12 位或四类全含），但绝不允许将配置调低至平台基线以下；
- **8 大标准系统角色与多租户强隔离**：
  严格支持 PRD §2.2 定义的 8 大角色（`platform_admin`, `group_admin`, `company_admin`, `data_admin`, `project_lead`, `bid_writer`, `auditor`, `viewer`）；非平台超管严格只展示本公司用户，跨公司资产转交物理阻断。

---

## 2. 核心交付内容清单

### 2.1 纯逻辑领域层 (`frontend/web/src/admin/user-management-core.ts`)
1. **用户与资产领域模型**：
   - `UserItem`、`UserAssignedAssets`（包含 `active_projects`、`active_chapters`、`kb_items`）；
   - `hasActiveAssets` 与 `countUserActiveAssets`：高效判定与统计待移交资产；
   - `formatAssetSummary`：语义化资产概览描述（如“2 个进行中项目 · 1 篇在编章节”）；
2. **密码策略与强度动态校验算法**：
   - `countPasswordCharClasses(password)`：实时检测大写、小写、数字、特殊符号 4 大类别命中数；
   - `validatePasswordStrength(password, policy)`：依据公司当前生效策略给出即时合规反馈；
   - `validateCompanyPasswordPolicy(policy)`：拦截任何低于平台基线（8 位 / 3 类 / 5 次失败）的策略调宽企图；
3. **新增用户防线 (`validateNewUserForm`)**：
   - 账号格式（3~32 位字母数字下划线）、账号唯一性查重、姓名防空、8 角色校验、密码一致性与策略校验；
4. **停用前资产转交校验与状态流转 (`validateHandoverBeforeDisable`, `executeUserHandoverAndDisable`)**：
   - 接收人防自选、防已停用成员、防跨租户企业穿透；
   - 强制交接理由不少于 5 个字；
   - 原子化资产转移：将源用户项目、章节与资料一次性转移合并至接收人，清空源用户资产并将状态置为 `disabled`，生成审计记录 `UserHandoverRecord`；
5. **权限判定与租户过滤 (`checkUserManagementPermission`, `filterUsersList`)**：
   - `platform_admin` 与 `company_admin` 享有读写与交接权，其余角色判定为只读；
   - 非超管严格按 `currentCompanyId` 过滤租户数据，杜绝越权探测。

### 2.2 呈现交互层 (`frontend/web/src/admin/UsersPage.tsx`)
1. **Layout First 结构与统计概览卡片 (`user-management-overview`)**：
   - 顶栏直观呈现：总用户数、正常在职、已停用、当前公司密码策略，以及当前登录角色的权限 Tag；
   - 顶部操作栏提供「新增用户」与「账号安全策略」入口；
2. **多维检索与筛选工具栏 (`user-filter-bar`)**：
   - 账号/姓名模糊搜索、8 大角色下拉筛选、账号状态筛选、超管企业切换及一键重置；
3. **用户列表 Table (`user-table`)**：
   - 账号、姓名、角色 Tag、所属企业、状态 Badge（正常在职/已停用）、负责资产 Tag（橙色醒目突出资产数）；
   - 操作列智能分流：
     - 若用户持有未完结资产：呈现「转交并停用」按钮，点击拉起交接抽屉；
     - 若用户无资产：呈现「停用」Popconfirm 二次确认弹窗，确认后直接停用；
     - 若用户已停用：呈现「启用」按钮，点击恢复正常在职；
     - 只读模式下操作按钮全局置灰；
4. **新增用户 Modal (`user-add-modal`)**：
   - 表单录入账号、姓名、角色、所属租户、初始密码与确认密码；
   - 输入密码时动态提示当前公司策略要求与命中字符类别数；
5. **停用前资产交接 Drawer (`user-handover-drawer`)**：
   - 顶部警告 Alert 宣示合规门禁红线；
   - 列表详细展示待交接的负责项目、在编章节与资料条目；
   - 下拉选择同公司在职接收人；
   - 录入不少于 5 个字的交接审计理由；
6. **公司密码安全策略 Drawer (`user-security-policy-drawer`)**：
   - 查看与配置 `password_min_length`（>= 8 位）、`password_min_char_classes`（>= 3 类）、`max_login_attempts`（<= 5 次）；
   - 内联 Tag 标示“平台底线（只能调严）”，低于平台基线时表单自动拦截并提示。

### 2.3 路由与分包集成
- `frontend/web/src/app/route-loaders.ts`：添加 `loadUsersPage` 动态加载函数；
- `frontend/web/src/app/lazy-routes.tsx`：导出 `LazyUsersPage`；
- `frontend/web/src/app/GlobalPagesContent.tsx`：在 `admin.rules` 下的 Tab `users`（【A-02 用户与角色】）正式挂载 `UsersPage`。

---

## 3. 测试与质量门禁证据

### 3.1 专属单元测试（8 passed, 0 failed）
运行命令：
```bash
node --test frontend/web/tests/unit/user-management-page.test.mjs
```

测试执行结果：
```
✔ 1. 用户初始数据集与业务资产统计完整性 (0.9965ms)
✔ 2. “公司设置只能调严不能调宽”密码策略合规校验 (0.4983ms)
✔ 3. 密码强度与字符类别动态核验算法 (0.4129ms)
✔ 4. 新增用户表单校验与查重防线 (0.7103ms)
✔ 5. 停用前业务资产强制交接合规红线校验（M1-P10-F2） (0.389ms)
✔ 6. 执行资产交接与状态停用领域逻辑断言 (2.2334ms)
✔ 7. 8 角色 RBAC 细粒度权限感知与多租户隔离过滤 (0.3818ms)
✔ 8. UsersPage.tsx 与 GlobalPagesContent.tsx AST 静态契约断言 (0.9384ms)
ℹ tests 8
ℹ suites 0
ℹ pass 8
ℹ fail 0
```

### 3.2 全量前端单测保持 100% 全绿（445 passed, 0 failed）
运行命令：
```bash
pnpm --dir frontend/web test
```
执行结果：445 项单元测试全部通过（445 passed, 0 failed），无任何回归破坏。

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
- `✓ built in 1.25s`；
- 独立分包：`UsersPage-*.js` 体积仅 29.50 kB（gzip 9.85 kB），按需分包受控。

---

## 4. 交付影响核对

| 检查项 | 判定 | 说明 |
|---|---|---|
| PRD MVP v1.8 §5.10.2 A-02 用户与角色 | 对齐 | 覆盖用户列表、角色分配、资产转交与密码策略全流程 |
| 交接约束 M1-P10-F2 “停用前未转交不能停用” | 对齐 | 强校验持有资产用户必须走交接抽屉，阻断直接停用 |
| PRD §5.10.2 / Q28 定案 “密码策略只能调严” | 对齐 | 平台基线设为不可破底线（>=8位、>=3类），调宽强制拦截 |
| UI Layout First 原则 | 遵从 | 概览卡片 + 表格 + 侧边抽屉，内联基线 Tag，杜绝长文案堆砌 |
| 前端八域边界规范 | 遵从 | 代码严格置于 `src/admin/` 域内，无平铺根目录文件 |
| 拒绝空壳冒充交付 | 遵从 | 真实落地 A-02 业务界面并挂载于 `GlobalPagesContent.tsx` |
