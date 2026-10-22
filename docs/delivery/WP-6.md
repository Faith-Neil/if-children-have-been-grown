为什么有这个文件：记录质量整改路线图 WP-6（去演示身份 + 八角色前端收口、字典单源驱动与会话解耦）的实际完成内容、测试验收与规范落实说明。

它解决什么问题：解耦前端对合成演示会话与三角色的强制依赖，建立基于 PRD v1.8 §2.2 与数据字典 v1.9 §4.16 的前端八角色码表 roles.ts 与状态字典 codes.ts 单源驱动，支持正式路径 /api/v1/session 凭据会话与演示模式（VITE_DEMO）可关闭，并落实 Layout First 去说明化界面原则。

# WP-6：去演示身份与八角色前端收口交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | WP-6 |
| 代码解释 | 新增 shared/roles.ts 与 shared/codes.ts 单源收口八角色定义、权限集合与数据字典代码；拓展 types.ts 支持 AuthMode('synthetic-demo'\|'authenticated') 与 RoleMode('legacy-demo-compat'\|'rbac-8roles')；放宽 session-navigation.ts 信任核验，支持正式账号与八角色会话；重构 LoginScreen.tsx（落实 Layout First 去除说明文字，支持凭据登录与 VITE_DEMO 开关）；App.tsx 接入 loginWithToken 并在非演示模式下免调 demo 端点；同步 schemas.py 与 openapi 契约；详见第 2、3 节。 |
| 验收 | 新增前端专属单测 tests/unit/roles-codes-convergence.test.mjs 4 项全绿；前端权威测试套件 348 项全绿（344 原测 + 4 新测）；生产构建（tsc + vite build）成功通过（1.20s，0 错误）；后端核心测试 91 项全绿（八角色矩阵 10 项、v1 接口 4 项、会话导航 34 项、幂等契约 12 项、演示流程 31 项）；工程治理检查 486 份 Markdown 0 错误。 |
| 项目进度 | WP-6 顺利闭环；下一阶段进入 WP-7（OpenAPI 生成化与全量回归终审）。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 分支与提交：`feat/opencode-ICG`
- 关联规划：`docs/delivery/2026-10-22-quality-remediation-plan.md`（阶段 E / WP-6）
- 关联规则：`AGENTS.md`（质量整改与结构冻结规则 - 前端按域分层、UI 与界面设计克制 Layout First）
- 本地验收状态：已通过（前端 348 passed；构建绿灯；后端 91 passed；治理脚本通过）
- 合入 / 发布状态：分支持续演进，与远程保持同步

---

## 完成内容与变更文件

### 1. 角色与数据字典单源化收口

1. **八角色码表单源驱动（[`frontend/web/src/shared/roles.ts`](file:///frontend/web/src/shared/roles.ts)）**：
   - 严格依据 PRD v1.8 §2.2 与数据字典 v1.9 §4.16，集中定义 8 类标准系统角色：`platform_admin`（平台管理员）、`group_admin`（集团管理员）、`company_admin`（公司管理员）、`data_admin`（资料管理员）、`project_lead`（项目负责人）、`bid_writer`（投标编写人）、`auditor`（审核人）、`viewer`（只读成员）。
   - 建立双向历史别名归一化映射表 `ROLE_NORMALIZATION_MAP`，完全对齐后端 `project_access.py`。
   - 抽象只读角色集 `READONLY_SYSTEM_ROLES`、项目创建资质集 `PROJECT_CREATOR_ROLES`、编写资质集 `PROJECT_WRITER_ROLES`、项目领导资质集 `LEAD_COMPANY_ROLES` 以及平台管理员隔离路由集 `PLATFORM_ADMIN_FORBIDDEN_ROUTES`。
   - 提供 `isKnownRole`、`isReadonlyRole`、`normalizeSystemRole`、`getSystemRoleLabel` 工具函数，并导出 `isDemoMode()` 环境判断函数（读取 `VITE_DEMO`）。
2. **字典驱动状态与错误代码（[`frontend/web/src/shared/codes.ts`](file:///frontend/web/src/shared/codes.ts)）**：
   - 依据数据字典 v1.9 §4.16，集中定义 `PROJECT_STATUSES`（11 种项目流转状态及中文映射）、`VOLUME_TYPES`（技术标与商务标）、`TENDER_PARSE_STATUSES`、`REQUIREMENT_CATEGORIES`（10 大抽取分类及友好标签）、`REQUIREMENT_STATUSES`、`FACT_STATUSES`、`JOB_STATUSES`、`RULE_LEVELS`。
   - 统一定义与后端 `frozen_error_codes.py` 严格对齐的 `ERROR_CODES` 常量，杜绝魔法字符串散落。

### 2. 会话协议扩展与前端守卫对齐

1. **会话契约扩展（[`frontend/web/src/shared/types.ts`](file:///frontend/web/src/shared/types.ts)）**：
   - 扩展 `AuthMode = 'synthetic-demo' | 'authenticated'`。
   - 扩展 `RoleMode = 'legacy-demo-compat' | 'rbac-8roles'`。
   - 扩展 `AccountRole = SystemRole | 'editor' | 'manager' | 'viewer' | ...`。
2. **可信会话核验放宽（[`frontend/web/src/app/session-navigation.ts`](file:///frontend/web/src/app/session-navigation.ts)）**：
   - `trustedApplicationSession` 在兼容旧演示会话的同时，正式放行 `auth_mode: 'authenticated'` 与标准八角色会话，支持正式企业账号与会话接入。
3. **后门与契约保持（[`backend/bid-core/icg_demo/schemas.py`](file:///backend/bid-core/icg_demo/schemas.py) 与 [`spec/openapi/demo-v1.json`](file:///spec/openapi/demo-v1.json)）**：
   - 后端 OpenAPI 契约中 `ApplicationSessionResponse` 的 `auth_mode` 与 `role_mode` 声明更新为包含 `'authenticated'` 与 `'rbac-8roles'` 的联合枚举，契约校验通过。

### 3. 登录屏重构与 Layout First 落地

1. **登录组件（[`frontend/web/src/app/LoginScreen.tsx`](file:///frontend/web/src/app/LoginScreen.tsx)）**：
   - 严格遵循 **Layout First** 约束，移除侵入式的黄色提示框与冗长说明文字，依靠清晰的分组与排版表达交互意图。
   - 支持多模式登录：在演示模式下提供「体验账号」与「账号凭据」清晰切换；在生产或关闭演示模式（`VITE_DEMO=0`）下，仅展示正式凭据输入，杜绝合成演示账号露出。
2. **全局编排（[`frontend/web/src/app/App.tsx`](file:///frontend/web/src/app/App.tsx)）**：
   - 引入 `loginWithToken` 走通真实会话初始化链路（直接发起可信会话读取并挂接全局数据）。
   - 在非演示模式下跳过对 `/api/demo/accounts` 的冗余请求，实现真正意义上的「去演示化运行」。

---

## 验收结果

1. **前端八角色与单源码表专属单测**：
   - 命令：`node --test frontend/web/tests/unit/roles-codes-convergence.test.mjs`
   - 结果：**4 passed, 0 failed**（八角色归一化、资质集合、字典代码表、真实会话核验全部通过）。
2. **全量前端权威单测套件**：
   - 命令：`pnpm --dir frontend/web test`
   - 结果：**348 passed, 0 failed**（耗时 4.27s）。
3. **生产构建检验**：
   - 命令：`pnpm --dir frontend/web build`
   - 结果：**构建耗时 1.20s，0 错误，0 警告**，产物分布健康。
4. **后端核心权限与契约测试**：
   - 命令：`pytest tests/backend/test_eight_roles_access.py tests/backend/test_api_v1_convergence.py tests/backend/test_application_session.py tests/backend/test_error_idempotency.py tests/backend/test_demo.py`
   - 结果：**91 passed in 29.35s**（八角色访问矩阵、v1 API 收敛、会话核验、OpenAPI 契约、演示全链路 100% 绿灯）。
5. **工程治理检查**：
   - 命令：`node scripts/check-project-governance.cjs`
   - 结果：**486 份 Markdown、399 项任务、37 项 Issue 100% 通过**。
