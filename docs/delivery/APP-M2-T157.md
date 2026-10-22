为什么有这个文件：记录 APP-M2-T157 (A-06 审计日志页) 与 APP-M2-T026 (A-01 公司管理) 的交付状态、实现内容与验收证据。

它解决什么问题：集中呈现 A-06 审计日志中心与 A-01 企业租户管理页的核心实现、脱敏数据调阅记录（含调阅人、时间、>=5字调阅理由）、章节排他编辑锁抢占/释放、模型密钥变更事件、只读不可篡改安全防护、脱敏强规则生效标识、本地模型强制开关、密码安全策略（只能调严）、编辑锁心跳三元校验、集团管理员/公司管理员权限感知按钮隐匿、停用二次确认安全保护、路由级按需加载与专属单测验收证据，严禁私自标 done，供质量审计与任务验收。

# APP-M2-T157：A-06 审计日志中心与 A-01 企业租户管理交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T157（协同覆盖 APP-M2-T026） |
| 代码解释 | [docs/code/APP-M2-T157.md](../code/APP-M2-T157.md) |
| 验收 | 8 项专属自动化单测通过；全量 326 项前端单测通过；生产构建 build 成功且体积按需分包受控（AuditLogPage 131.88 kB, CompanyManagePage 27.46 kB）；工程治理通过 |
| 项目进度 | 前端 M2 阶段推进，APP-M2-T157 与 APP-M2-T026 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T157](../tasks/APP-M2.md#app-m2-t157)、[APP-M2-T026](../tasks/APP-M2.md#app-m2-t026)
- 依赖任务：[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)、[APP-M2-T016](../tasks/APP-M2.md#app-m2-t016)
- 分支：`feat/opencode-ICG`
- 本地验收状态：**in-review**（严禁私自标 done）
- 合入 / 发布状态：未合入主干，未发布

---

## 完成内容与变更文件

### 1. 核心产出
1. **A-06 审计日志中心组件 (`frontend/web/src/AuditLogPage.tsx` 与 `audit-log-core.ts`)**：
   - 展现敏感数据脱敏调阅记录，展示调阅人、时间、>=5字调阅理由，并提供 `理由合规 (≥5字)` 状态 Badge；
   - 展现章节排他独占编辑锁全生命周期调度（获取锁、主动释放、超时释放、强制接管及接管理由）；
   - 展现模型密钥安全变更事件（创建、更新、轮换、吊销），严禁回显密钥明文，强制使用脱敏指纹（如 `sk-****8f92`）；
   - 支持时间范围、操作人、操作类别、具体动作类型、项目 ID/名称、执行结果等多维检索过滤；
   - 纯只读保护机制：系统级只读断言，阻断修改、编辑、删除与清空接口，提供只读存证抽屉。
2. **A-01 企业租户管理组件 (`frontend/web/src/CompanyManagePage.tsx` 与 `company-manage-core.ts`)**：
   - 展现多租户基本资料、统一社会信用代码、法人代表、租户资料库隔离空间与 RAGFlow 向量库空间状态；
   - 落实脱敏强合规规则不可关闭标识（`mask_strict_mode_enabled`，PRD §6.9）；
   - 落实涉密与敏感项目强制本地模型开关（`force_local_model`，PRD §6.4）；
   - 落实密码安全策略只严不松约束：最少位数 >= 8（可调高至 12 或以上），字符类别 >= 3（PRD §5.10.2）；
   - 落实编辑锁与自动保存心跳三元数学约束校验（`autosave <= heartbeat` 且 `heartbeat * 10 <= timeout * 60` 且 `timeout > 5`）；
   - 落实集团管理员（`group_admin`）与公司管理员（`company_admin`）权限感知：集团管理员视角显示全局监管只读提示条，非公司管理员角色所有敏感管理保存按钮彻底隐藏；
   - 落实停用公司租户二次确认防线：强制输入完整公司名称进行二次比对确认（PRD §5.10.1）。
3. **物理文件隔离与按需加载 (`route-loaders.ts`, `lazy-routes.tsx`, `App.tsx`)**：
   - 严格隔离：绝对未修改 `EditorPage.tsx` 与 `ProjectPages.tsx`；
   - 路由级按需加载（Route-level Code Splitting），将审计日志中心与公司管理页拆解为独立异步 Chunk，包体积受控。

### 2. 变更文件清单
- `frontend/web/src/audit-log-core.ts` (新增): 审计数据契约模型、多维过滤算法、理由校验与密钥指纹脱敏
- `frontend/web/src/AuditLogPage.tsx` (新增): A-06 审计日志中心页面组件
- `frontend/web/src/company-manage-core.ts` (新增): 企业租户模型、安全参数校验、权限感知判定与停用核验
- `frontend/web/src/CompanyManagePage.tsx` (新增): A-01 企业租户管理页面组件
- `frontend/web/src/route-loaders.ts` (修改): 注册 `loadAuditLog` 与 `loadCompanyManage` 动态加载器
- `frontend/web/src/lazy-routes.tsx` (修改): 导出 `LazyAuditLogPage` 与 `LazyCompanyManagePage` 异步路由组件
- `frontend/web/src/App.tsx` (修改): 在管理规则区域挂载审计日志与公司管理选项卡，保持按需加载
- `tests/frontend/audit-company-pages.test.mjs` (新增): 8 项覆盖调阅理由、排他锁、密钥脱敏、只读保护、多维检索、合规基线、权限感知与停用二次确认的前端测试
- `docs/code/APP-M2-T157.md` (新增): 详尽代码解释文档
- `docs/delivery/APP-M2-T157.md` (新增): 交付记录文档

---

## 验收证据

### 1. 自动化单元测试验证
执行命令：
```bash
node --test tests/frontend/audit-company-pages.test.mjs
```
执行结果：
```text
✔ APP-M2-T157: 敏感数据调阅理由合规门禁校验 (>= 5 字规则) (1.0921ms)
✔ APP-M2-T157: 操作类型元信息映射与事件分类准确性 (0.3476ms)
✔ APP-M2-T157: 模型密钥脱敏指纹格式化与明文防泄漏断言 (0.3805ms)
✔ APP-M2-T157: 只读保护契约断言：严禁前端提供删除与篡改接口 (0.8066ms)
✔ APP-M2-T157: 审计日志多维检索过滤测试 (1.9604ms)
✔ APP-M2-T026: 企业合规参数基线校验与门禁拦截 (0.3619ms)
✔ APP-M2-T026: 权限感知判定：区分集团管理员、公司管理员、平台管理员与只读人员 (0.2487ms)
✔ APP-M2-T026: 停用公司租户二次确认输入校验 (PRD §5.10.1 约束) (0.1102ms)
ℹ tests 8
ℹ suites 0
ℹ pass 8
ℹ fail 0
ℹ duration_ms 172.455
```

全量前端单元测试：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
执行结果：
```text
ℹ tests 326
ℹ suites 0
ℹ pass 326
ℹ fail 0
ℹ duration_ms 2959.5295
```

### 2. 构建产物与体积审计
执行命令：
```bash
pnpm --dir frontend/web build
```
执行结果：
```text
$ tsc -b && vite build
✓ 3371 modules transformed.
rendering chunks...
dist/assets/AuditLogPage-CJVqjPx2.js         131.88 kB │ gzip:  41.76 kB
dist/assets/CompanyManagePage-Cb4I4sDN.js     27.46 kB │ gzip:  10.48 kB
✓ built in 825ms
```
成功实现路由级按需加载（Route-level Code Splitting），未引入额外体积包袱。
