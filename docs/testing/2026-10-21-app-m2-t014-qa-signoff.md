为什么有这个文件：记录QA对APP-M2-T014（路由守卫与 403 页面：结合八角色与项目分工，REV-M0-T53）的独立复测与签署结论。

它解决什么问题：不轻信前端自报结果，亲手执行路由守卫专项单测、前端全量单测、生产构建打包与包体积门禁审计（<= 295 kB），针对性核查 8 类标准系统角色（platform_admin, group_admin, company_admin, data_admin, project_lead, bid_writer, auditor, viewer）的路由准入校验、切页入口前置守卫与零越权 API 外呼保证、项目空间内细粒度分工鉴权（项目负责人全权、分册负责人本分册、编写人指派章节）、平台管理员业务数据强隔离以及 403 页面语义化呈现与快捷导航动作（【返回工作台】【切换身份】）。

# APP-M2-T014 路由守卫与 403 页面独立复测与 QA 签署（REV-M0-T53）

- 被验任务：[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014) · 路由守卫与 403 页面（结合八角色与项目分工）
- 关联审查任务：REV-M0-T53
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T014 交付](../delivery/APP-M2-T014.md)、[代码解释](../code/APP-M2-T014.md)
- 被验核心文件：`frontend/web/src/route-guard.ts`、`frontend/web/src/RouteGuard.tsx`、`frontend/web/src/StatusViews.tsx`、`frontend/web/src/status-views.ts`、`frontend/web/src/App.tsx`、`tests/frontend/route-guard.test.mjs`、`frontend/web/tests/route-guard.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T014 保持 in-review，严禁标 done；关联 Issue 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 八角色路由准入表格驱动判定 | 通过 | `route-guard.ts` 定义 8 类标准系统角色枚举与历史别名双向归一；单测表格驱动严密核验：`platform_admin` 严格阻断公司业务路由（返回 `PLATFORM_ADMIN_NO_BUSINESS_ACCESS`）；`group_admin`、`viewer`、`auditor` 严格阻断写路由与项目创建（返回 `WRITE_PERMISSION_REQUIRED` / `PROJECT_CREATE_FORBIDDEN`）；`company_admin` 与 `project_lead` 全功能放行 |
| AC-02 切页入口前置守卫与零越权 API 外呼 | 通过 | `App.tsx` 在 `followPath`、`openProject`、`loadNav`、`loadTab` 所有切页入口执行前置 `checkRoutePermission` 校验；单测 `pre-flight blocking guarantees zero backend API calls on forbidden routes` 确认阻断时 `fetchCalls === 0`，未发起任何受保护数据的网络请求，彻底杜绝越权 API 外呼 |
| AC-03 细粒度项目分工鉴权三级判定 | 通过 | `checkChapterEditPermission`：① 项目负责人（`project_role: 'lead'`）拥有技术与商务全部分册全部章节编辑权；② 分册负责人（`volumes.owner_id === userId`）拥有本分册所有章节编辑权，跨分册被阻断；③ 编写人（`assignee_id === userId`）仅限编辑被明确分配的章节，未分配章节被拦截（返回 `CHAPTER_NOT_ASSIGNED`）；④ 只读成员一律阻断编辑 |
| AC-04 跨公司多租户数据隔离 | 通过 | `cross-company project access is strictly forbidden before data fetch`：当工作区 `company_id` 与会话 `active_company_id` 不一致时，守卫前置拦截并返回 `SCOPE_FORBIDDEN`，提示“跨公司访问受限”，保护多租户数据安全 |
| AC-05 语义化 403 页面与快捷切换动作 | 通过 | `StatusViews.tsx` 的 `Forbidden403` 组件统一渲染标题、角色受限明确解释、上下文标签（当前项目/当前角色/目标路径）；提供【返回工作台 / 返回可访问首页】按钮与【切换身份】（`data-testid="forbidden-switch-role-button"`）按钮，点击触发安全登出重登；编辑台权限失效时激活 `showRetainedNotice` 保留未保存文字 |
| AC-06 生产构建打包与包体积门禁 | 通过 | `pnpm --dir frontend/web build` 顺利通过（`tsc -b && vite build` 耗时 1.64s，0 错误 0 告警）；首屏主包 `index-DjT1RwqS.js` 为 **287.78 kB**（Gzip 后 **91.93 kB**），完全满足 **<= 295 kB** 门禁红线（余量 7.22 kB） |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 路由守卫专项测试套件 | `node --test tests/frontend/route-guard.test.mjs frontend/web/tests/route-guard.test.mjs` | **13 passed, 0 failed** (纯逻辑 9 项 + AST 结构断言 4 项) | 0.81s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **206 passed, 0 failed** (包含 13 项路由守卫专项单测) | 3.18s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build` 耗时 1.64s) | 1.64s |
| 首屏主包体积审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-DjT1RwqS.js` **287.78 kB**（gzip: 91.93 kB），**完全达标 <= 295 kB 门禁** | — |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **零越权 API 外呼前置防御机制可靠**：传统 SPA 常见在页面载入甚至发包失败后才呈现 403，本项目通过在路由入口处前置调用纯函数 `checkRoutePermission`，在发包前即可短路返回，彻底切断了恶意枚举 URL 触发后端越权查库的风险。
2. **切换身份交互路径顺畅**：在 403 界面提供直接关联登出的 `onSwitchRole` 快捷操作，解决了企业演示或多身份测试时因权限受阻而卡在死胡同页面的痛点。
3. **VM 测试沙箱兼容性保护完备**：在 `App.tsx` 提取源码运行于轻量 `node:vm` 单测环境时，全局函数调用守卫方法均包含 `typeof` 安全保护，杜绝了无 DOM 或 mock 上下文中的未定义报错。

## 签署状态

APP-M2-T014 / REV-M0-T53 保持 **in-review**，**严禁标 done**。
