# 任务交付：App.tsx 巨石组件二次瘦身与路由解耦（FE-TECH-DEBT-02）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-TECH-DEBT-02 |
| 代码解释 | [App.tsx 巨石二次瘦身与路由解耦代码说明](../code/FE-TECH-DEBT-02.md) |
| 文档登记 | [D-772](../DOCUMENT_INDEX.md) |
| 验收 | 1. 架构瘦身达标：`frontend/web/src/app/App.tsx` 从 695 行二次拆解瘦身至 **394 行**（净缩减 301 行，缩减率 43.3%），单文件行数严格控制在 **400 行** 阈值以内；<br>2. 领域模块解耦：抽离 `AppHeaderActions.tsx`（顶栏环境标识、搜索框、任务角标与用户信息）、`AppModals.tsx`（新建项目、任务中心、模型配置与 RAGFlow 配置四大全局弹窗）、`ProjectWorkspaceContent.tsx`（项目工作台顶栏、上下文与 10 大业务 Tab 路由）、`GlobalPagesContent.tsx`（项目列表、企业资料库、任务中心、规则审计与方案片段/写作规范全局页面）；<br>3. 前端全量单测保持 100% 全绿：`pnpm --dir frontend/web test` 408 passed, 0 failed（新增专属单测 5 项全部通过）；<br>4. TypeScript 严格类型检查：`pnpm --dir frontend/web lint` 0 错误、0 警告（`tsc -b --noEmit` 顺利退出）；<br>5. 生产构建验证：`pnpm --dir frontend/web build` 1.60s 顺利完成，分包体积健康受控；<br>6. 工程治理脚本核验：`node scripts/check-project-governance.cjs` 校验通过。 |
| 项目进度 | 本地已完成实现与多维质量验证，测试与构建 100% 绿灯，按规范推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

根据 2026-10-26 架构质量治理约定与 `AGENTS.md`「前端按域分层与代码健康度约束（<400 行精神）」规范，原 `frontend/web/src/app/App.tsx` 在早期多轮演化后膨胀至 695 行，集中堆叠了：
1. 顶栏右侧全套环境指示器、全局搜索条、任务中心角标、企业租户标签、用户头像登出与配置按钮；
2. 全局浮层与弹窗（创建项目弹窗、任务中心抽屉、大模型配置弹窗、RAGFlow 知识库配置弹窗）；
3. 项目内部 10 个业务 Tab（概览、招标文件、解析确认、响应矩阵、项目事实、章节编辑台、合规检查、导出交付、项目设置、操作指南）的巨型 JSX 分支；
4. 全局导航 6 大页面（项目列表、资料库、长任务运维、系统管理、方案片段库、写作规范档案）的路由渲染。

这导致 `App.tsx` 职责过于繁重，维护成本高。

本任务核心目标：
- 严格遵循八域架构（在 `frontend/web/src/shell/` 与 `frontend/web/src/app/` 下组织代码，严禁在 `src` 根目录平铺）；
- 将 `App.tsx` 单文件行数压缩至 **400 行以内**（实测达到 **394 行**）；
- 完整保留历史单测（`tests/app-orchestration.test.mjs` 与 `tests/evidence-orchestration.test.mjs`）所需的 AST 函数声明契约与事件监听；
- 保持既有路由与交互行为零回归，确保全量单元测试与 TypeScript 编译 100% 绿灯。

---

## 2. 架构分包与模块解耦清单

所有拆分文件均严格收敛在 `shell/` 与 `app/` 领域子目录中，未对外部域及 `backend/` 产生任何破坏性改动：

| 文件路径 | 变更类型 | 行数 | 职责说明 |
|---|---|---|---|
| `frontend/web/src/shell/AppHeaderActions.tsx` | 新增 | 108 行 | 顶栏右侧功能操作组：封装开发环境 Tag、全局搜索 Input、任务中心徽标 `TaskBadge`、消息通知 Bell、企业租户 Label、用户头像与登出 Popconfirm、模型配置与 RAGFlow 配置入口按钮 |
| `frontend/web/src/shell/AppModals.tsx` | 新增 | 90 行 | 全局浮层与弹窗管理组件：统一装配 `CreateProjectModal`、`TaskCenterDrawer`（注入平台管理员脱敏角色）、`ModelConfigModal`、`RagflowConfigModal`，收敛弹层开闭状态契约 |
| `frontend/web/src/app/ProjectWorkspaceContent.tsx` | 新增 | 134 行 | 项目工作台容器与路由：封装项目顶栏 `ProjectHeader`、`ProjectContext.Provider`、只读横幅 `ReadonlyBanner` 以及 10 大项目业务页签的条件渲染分支 |
| `frontend/web/src/app/GlobalPagesContent.tsx` | 新增 | 132 行 | 全局页面容器与路由：封装项目列表页 `ProjectListPage`（支持 `<Can>` 新建按钮注入）、企业资料库 `LibraryPage`、长任务运维 `JobsPage`（支持脱敏视图）、审计日志与公司管理后台、方案片段库与写作档案页 |
| `frontend/web/src/app/App.tsx` | 重构 | **394 行** | 主应用入口编排容器：从 695 行压缩至 394 行（缩减率 43.3%），严格满足 `< 400` 行红线，保留全部导航状态函数与 AST 测试契约 |

---

## 3. 测试与治理验证证据

### 3.1 专属单元测试（5 passed, 0 failed）

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

### 3.2 前端全量单测保持 100% 全绿（408 passed, 0 failed）

运行命令：
```bash
pnpm --dir frontend/web test
```

测试输出：
```
ℹ tests 408
ℹ suites 0
ℹ pass 408
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 6579.9025
```

### 3.3 TypeScript 严格类型检查通过（0 error）

运行命令：
```bash
pnpm --dir frontend/web lint
```

输出：
```
$ tsc -b --noEmit
```
退出码 0，无任何类型错误。

### 3.4 生产构建验证通过

运行命令：
```bash
pnpm --dir frontend/web build
```

输出：
```
✓ 3412 modules transformed.
✓ built in 1.60s
```

---

## 4. 建议与流转

本卡代码重构与解耦已全部达标，质量证据齐全，当前状态标记为 `in-review`。建议 PM 在 QA 复核签署后标为 `done`。
