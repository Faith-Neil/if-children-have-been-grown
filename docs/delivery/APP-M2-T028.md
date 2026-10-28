# APP-M2-T028：A-02 用户角色分配、锁定/解锁与重置密码表单交付报告

为什么有这个文件：记录 APP-M2-T028（A-02 用户角色分配、锁定/解锁与重置密码表单）的交付状态、实现内容与质量验证证据。

它解决什么问题：
1. 落地管理后台「A-02 用户与角色管理」中的角色分配、密码重置与账号锁定/解锁全套业务交互与纯逻辑领域层；
2. **角色分配安全防线**：严格支持 PRD §2.2 定义的 8 大标准 RBAC 角色流转；系统级超级管理员（`admin`）角色受保护禁止修改；仅平台管理员与企业管理员具备角色分配权限；企业管理员禁止越权将用户提权为平台超管或集团管理员；当项目总负责人（`project_lead`）名下持有进行中项目时，降级角色将触发强预警提示，防止项目无人负责；
3. **密码合规重置表单**：管理员为用户重置初始密码时，严格遵循企业当前密码安全策略（长度 ≥ 8 位，大写、小写、数字、符号至少 3 类）；提供一键「随机生成合规强密码」工具（全 4 类字符全覆盖，长度 ≥ 10 位）；二次确认密码一致性核验；
4. **账号锁定与解锁闭环（交接约束 M1-P10-F3）**：严格遵循交接约束核心要求——**`user_status = locked` 显示“解锁”**；支持一键解锁连续登录失败超限被锁定的账号（恢复正常在职活跃状态并重置失败计数）；支持管理员对异常账号主动安全锁定（超管账号禁止锁定）；重置密码时若原账号处于锁定状态，自动联动解除锁定；
5. **践行 Layout First 交互设计原则**：表格操作列依据账号当前状态智能呈现动作按钮（锁定状态呈现「解锁」，活跃在职呈现「锁定」），角色分配与密码重置采用紧凑清晰的弹窗交互与内联实时强度反馈，杜绝说明书式冗余文案堆砌。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T028 |
| 代码解释 | [APP-M2-T028 代码说明](../code/APP-M2-T028.md) |
| 文档登记 | [D-828](../DOCUMENT_INDEX.md) |
| 验收 | 1. **角色分配安全流转**：支持 8 大标准 RBAC 角色切换，超管 `admin` 角色不可篡改，企业管理员越权提权（platform_admin/group_admin）被拦截，同一角色重复分配被拦截，项目负责人持有活动项目时降级触发强预警提示；<br>2. **密码合规重置**：即时动态校验密码强度（长度 ≥ 8，字符种类 ≥ 3），两次输入不一致拦截，提供全 4 类字符随机合规强密码生成器；<br>3. **账号解锁与锁定（M1-P10-F3）**：`user_status = locked` 状态在表格中以警示 Badge 标注并呈现「解锁」按钮，解锁后立即恢复为 `active`；活跃账号支持「锁定」二次确认；超管账号禁止锁定；重置密码自动解除锁定；<br>4. **8 角色权限感知**：平台与公司管理员可操作，业务角色纯只读置灰并阻断；<br>5. **自动化测试 100% 全绿**：专属单测 `user-role-reset-unlock.test.mjs` 8 项全绿，全量 455 项前端单测全绿，TypeScript 静态检查 0 error，Vite 生产构建 1.09s 成功。 |
| 项目进度 | done（已获 QA 签署 D-836 与 PD 验收 D-837，经 PM 批准正式标 done） |
<!-- task-delivery:end -->

## 1. 业务背景与规范依据

依据 PRD MVP v1.8 §2.3、§5.10.1、§5.10.2、交接约束 §6.2 M1-P10-F3 以及 Q28 定案：
- **交接约束 M1-P10-F3 核心红线**：
  系统在用户连续登录失败达到阈值（默认 5 次）后将账号状态置为 `locked`。在管理端用户列表中，**必须明确感知锁定状态并提供「解锁」动作**，点击后重置计数器并恢复账号正常使用。
- **角色分配权限边界与项目资产防失控**：
  8 大标准系统角色划分严明（`platform_admin`, `group_admin`, `company_admin`, `data_admin`, `project_lead`, `bid_writer`, `auditor`, `viewer`）。企业管理员只能在本企业内部调配角色，严禁越权给自己或他人分配平台级角色；当把项目总负责人降级为写手或访客时，系统必须核查其是否仍有未完结项目在身，给出明确风险预警，防止项目因负责人变更而脱幅脱节。
- **密码重置符合企业密码策略（Q28 定案）**：
  重置密码属于管理员代操作，密码必须同样遵循企业当前密码安全策略（长度 ≥ 8 位且字符种类 ≥ 3 类），杜绝弱密码代设漏洞。同时提供一键生成合规密码工具，提升安全运维效率。

---

## 2. 核心交付内容清单

### 2.1 纯逻辑领域层 (`frontend/web/src/admin/user-management-core.ts`)
1. **角色分配校验算法 (`validateRoleAssignment`)**：
   - 保护超管账号：`admin` 账号或角色为 `platform_admin` 禁止修改角色；
   - 操作者权限校验：非管理员角色（如 bid_writer、viewer）禁止调整角色；
   - 企业管理员越权拦截：`company_admin` 禁止将用户提权为 `platform_admin` 或 `group_admin`；
   - 目标角色查重：目标角色与原角色相同时拦截无需重复分配；
   - 项目负责人降级预警：检测 `sourceUser.assigned_assets.active_projects`，若原为 `project_lead` 且持有进行中项目，返回详细的项目数与交接建议预警信息。
2. **角色分配执行不可变更新 (`executeRoleAssignment`)**：
   - 不可变更新用户列表中目标用户的角色属性，返回新用户数组与更新后的实体。
3. **密码重置校验与生成算法 (`validatePasswordReset`, `generateCompliantPassword`)**：
   - `validatePasswordReset`：复用密码强度核验引擎，校验密码长度、命中字符类别数与二次确认一致性；
   - `generateCompliantPassword`：根据企业生效策略随机生成强密码，强制涵盖大写字母、小写字母、数字、特殊符号全部 4 类字符，且长度 ≥ 10 位（或 ≥ 策略要求），打乱随机顺序保证不可预测性。
4. **密码重置与联动解锁 (`executePasswordReset`)**：
   - 重置目标用户密码；
   - 若用户此前处于 `locked`（登录超限锁定）状态，重置密码后自动将其状态恢复为 `active`，实现安全闭环。
5. **账号解锁与锁定流转 (`executeUnlockUser`, `executeLockUser`)**：
   - `executeUnlockUser`：将 `locked` 状态的用户恢复为 `active`；
   - `executeLockUser`：将 `active` 状态的用户变更为 `locked`；超管账号 `admin` 受系统保护禁止锁定，抛出防御性异常。
6. **演示基线数据扩充**：
   - 在 `INITIAL_USERS` 中补充已锁定测试账号 `locked_chen`（陈敏，`status: 'locked'`），完备覆盖已锁定账号的展示、解锁与改密恢复场景。

### 2.2 呈现交互层 (`frontend/web/src/admin/UsersPage.tsx`)
1. **状态展示与操作列智能分流 (Layout First)**：
   - 状态列：当 `status === 'locked'` 时，采用警示黄色 Badge 渲染 `已锁定 (登录超限)`；
   - 操作列动作按钮依据用户当前状态自适应呈现：
     - 若 `record.status === 'locked'`：呈现高亮「解锁」按钮（`user-unlock-btn-${record.id}`），点击即调用 `executeUnlockUser` 恢复活跃；
     - 若 `record.status === 'active'`：呈现「锁定」按钮（`user-lock-btn-${record.id}`），附带 Popconfirm 二次安全确认；
     - 增加「分配角色」按钮（`user-role-btn-${record.id}`），点击拉起角色分配弹窗；
     - 增加「重置密码」按钮（`user-reset-pwd-btn-${record.id}`），点击拉起重置密码弹窗；
     - 超管账号 `admin` 与自身账号的安全保护（置灰禁用）。
2. **角色分配模态框 (`user-role-modal`)**：
   - 展示目标用户的当前信息（账号、姓名、当前角色 Tag、所属企业）；
   - 若选中角色触发降级且用户持有活动项目，即时渲染黄色 Alert 提醒卡片（`role-change-warning`）；
   - 目标角色下拉框（`role-select`）：若操作者为企业管理员，自动将 `platform_admin` 与 `group_admin` 选项置灰并标注 `(仅平台超管可分配)`；
   - 提交按钮具备明确契约 testid（`role-confirm-btn`）。
3. **密码重置模态框 (`user-reset-pwd-modal`)**：
   - 顶部呈现信息 Alert，明确新密码需符合的位数与字符类别底线；
   - 表单提供「随机生成合规强密码」便捷按钮（`reset-pwd-generate-btn`），点击自动生成全 4 类合规强密码并填充表单；
   - 输入框动态强度反馈（`Text type="success" / "danger"`），即时计算命中类别数；
   - 密码与确认密码一致性校验；
   - 提交按钮具备明确契约 testid（`reset-pwd-submit-btn`）。

---

## 3. 验收标准与交付物对照

| 验收项 | PRD / 交接约束依据 | 交付实现与断言 | 结论 |
|---|---|---|---|
| **角色分配与超管保护** | PRD §2.2 / §2.3 / §5.10.1 | `validateRoleAssignment` 严格保护超管 admin 不可篡改；企管提权 platform_admin 阻断；同一角色分配拦截；单测用例 1 通过 | **通过** |
| **项目负责人降级预警** | PRD §5.10.1 / 业务安全 | `validateRoleAssignment` 判定持有活动项目的项目负责人变更时返回警示文案，UsersPage 实时渲染 warning Alert；单测用例 2 通过 | **通过** |
| **密码重置与合规强度** | PRD §5.10.2 / Q28 定案 | `validatePasswordReset` 强制核验策略与确认一致性；`generateCompliantPassword` 随机生成全 4 类字符强密码；单测用例 4、5 通过 | **通过** |
| **锁定与解锁闭环** | 交接约束 M1-P10-F3 | `executeUnlockUser` 恢复活跃；`executeLockUser` 实施锁定；重置密码联动解除锁定；操作列自适应呈现解锁/锁定按钮；单测用例 6、7 通过 | **通过** |
| **8 角色权限感知** | PRD §2.2 / 系统安全 | 仅 platform_admin 与 company_admin 可调整角色/重置密码/锁定账号；只读角色按钮置灰并全局提示；单测用例 1.3 通过 | **通过** |
| **前端无占位壳与静态契约** | Layout First 原则 | `UsersPage.tsx` 全真实实现，零 PendingPage 占位；`user-role-reset-unlock.test.mjs` 测试 8 AST 静态断言通过 | **通过** |

---

## 4. 自动化测试与构建验证证据

### 4.1 专属单元测试（8/8 全部通过）
运行命令：
```bash
node --test frontend/web/tests/unit/user-role-reset-unlock.test.mjs
```
输出结果：
```text
✔ 1. 角色分配安全校验：超管保护、企业管理员越权提权拦截与同角色校验 (1.6308ms)
✔ 2. 降级项目负责人时的进行中项目强预警提示 (0.1794ms)
✔ 3. 角色分配执行不可变更新 (0.1689ms)
✔ 4. 重置密码合规校验：符合企业密码策略与确认一致性 (0.3484ms)
✔ 5. 随机合规密码生成器：必含全部4类字符且满足长度策略 (0.3733ms)
✔ 6. 重置密码执行与锁定账号自动恢复活跃（M1-P10-F3） (0.3764ms)
✔ 7. 账号手动锁定与解锁逻辑（M1-P10-F3：锁定状态显示解锁按钮） (0.7757ms)
✔ 8. UsersPage.tsx AST 静态契约断言：角色表单、重置密码、锁定/解锁交互元素 (0.867ms)
ℹ tests 8
ℹ suites 0
ℹ pass 8
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 178.7764
```

### 4.2 前端全量单测套件（455/455 全部通过）
运行命令：
```bash
pnpm --dir frontend/web test
```
输出结果：
```text
ℹ tests 455
ℹ suites 0
ℹ pass 455
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 5697.3139
```

### 4.3 TypeScript 静态类型检查（0 错误）
运行命令：
```bash
pnpm --dir frontend/web lint
```
输出结果：
```text
$ tsc -b --noEmit
Process exited with code 0.
```

### 4.4 生产构建（Vite 构建成功）
运行命令：
```bash
pnpm --dir frontend/web build
```
输出结果：
```text
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 3421 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                1.63 kB │ gzip:   0.71 kB
dist/assets/UsersPage-DJT3KA-y.js             38.73 kB │ gzip:  12.03 kB
✓ built in 1.09s
Process exited with code 0.
```

---

## 5. 状态流转建议

本任务代码、交互、纯逻辑领域层及完备自动化测试套件均已就绪，无破坏性变更，无空壳代码。

依据治理与交接约定：
- 本任务卡（`APP-M2-T028`）在 `docs/TASK_BOARD.md` 与 `docs/tasks/APP-M2.md` 中标为 **`in-review`**；
- 建议由 QA subagent 独立复测签署、PD subagent 业务核对后，向人类项目经理（PM）推荐标 **`done`**。
