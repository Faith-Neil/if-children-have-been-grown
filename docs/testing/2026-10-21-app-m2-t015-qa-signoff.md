为什么有这个文件：记录QA对APP-M2-T015（权限指令 `<Can>` 与按钮隐藏）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手执行权限指令专属单测、前端全量单测套件、生产构建打包与包体积门禁审计（<= 295 kB），针对性核查 8 类标准系统角色的细粒度权限判定逻辑（can 纯函数与 useCan / useCanMap Hook）、未授权默认零 DOM 残留硬性安全门禁（杜绝 CSS display:none 绕过）、新建项目资质强校验、递交版 Word 导出严格归属 project_lead、查看完整身份证号严格限定 company_admin 与 data_admin、项目内章节与分册细粒度分工授权以及 passThrough 置灰禁用与 Tooltip 降级机制。

# APP-M2-T015 权限指令 `<Can>` 与按钮隐藏独立复测与 QA 签署

- 被验任务：[APP-M2-T015](../tasks/APP-M2.md#app-m2-t015) · 权限指令 `<Can>` 与按钮隐藏
- 关联审查任务：REV-M0-T54
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T015 交付](../delivery/APP-M2-T015.md)、[代码解释](../code/APP-M2-T015.md)
- 被验核心文件：`frontend/web/src/shell/can-directive.ts`、`frontend/web/src/shell/can-context.ts`、`frontend/web/src/shell/useCan.ts`、`frontend/web/src/shell/Can.tsx`、`frontend/web/src/app/App.tsx`、`frontend/web/src/shell/route-guard.ts`、`tests/frontend/can-directive.test.mjs`、`frontend/web/tests/can-directive.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T015 保持 in-review，严禁标 done；关联 ISSUE-007 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 未授权默认零 DOM 残留硬安全门禁 | 通过 | `Can.tsx` 组件在无权限且未指定 `fallback` 时直接返回 `null`；AST 与轻量 DOM 测试断言确认 unauthorized 元素在 DOM 树中没有任何节点输出（节点数为 0），从源头上彻底根除攻击者通过浏览器 DevTools 修改 `display: none` 或移除 `disabled` 属性越权触发 API 的安全隐患 |
| AC-02 八角色权限矩阵纯逻辑核验 | 通过 | `can-directive.ts` 纯函数 `can(perform, on, context)` 严格落地 PRD v1.8 §2.3 权限矩阵：① 只读角色（`group_admin`、`viewer`、`auditor`、`platform_admin`）执行任何写或修改操作一律被全局熔断返回 `false`；② `project:create` 严格限 `company_admin`、`project_lead`、`manager`；③ `project:confirm`、`parse:confirm`、`matrix:confirm` 限 `project_lead` 与 `company_admin` |
| AC-03 细粒度分工授权与章节编辑保护 | 通过 | 针对 `chapter:edit`、`chapter:submit` 实施三级细粒度授权：项目负责人（`lead`）全量放行；分册负责人（`volume_owner`）仅限本分册章节；编写人（`assignee`）仅限分配章节，未分配章节被拦截；`chapter:takeover` 锁接管严格限定项目负责人或本分册负责人，非负责人无权接管他人编辑锁 |
| AC-04 递交版 Word 导出与内部稿导出差异化边界 | 通过 | `submission:export`（递交版 Word 导出）严格限定 `project_lead`，其他所有角色（包括 `company_admin`）均无权导出递交版；`volume:export_internal`（内部稿导出）支持 `project_lead`、`company_admin`、`bid_writer` 导出内部校对稿，边界隔离清晰严密 |
| AC-05 敏感身份证号查看严格限权门禁 | 通过 | `id_card:view`（查看人员完整身份证号）严格限定仅 `company_admin` 与 `data_admin` 享有权限，其余角色（含 `project_lead`、`bid_writer`）一律返回 `false` 并提示“敏感身份信息仅限企业管理员与资料管理员查看”，杜绝敏感个人隐私泄露 |
| AC-06 passThrough 置灰禁用与 Tooltip 降级 | 通过 | 当 `<Can passThrough tooltipOnDisabled="无权限原因">` 开启时，组件通过 React.cloneElement 为子元素注入 `disabled: true`、`aria-disabled="true"`、`style={{ pointerEvents: 'none' }}`，并外包 Tooltip 呈现详细禁能原因；兼顾业务只读可感知性与操作阻断 |
| AC-07 App 全局上下文集成与工作台新建项目按钮保护 | 通过 | `App.tsx` 顶层统一挂载 `<CanProvider>` 注入当前会话身份上下文；工作台“新建项目”按钮由 `<Can perform="project:create">` 声明式指令包裹，经 AST 语法树遍历确认包裹结构完整，非授权角色访问工作台时该按钮彻底消失 |
| AC-08 生产构建打包与包体积门禁 | 通过 | `pnpm --dir frontend/web build` 顺利完成（`tsc -b && vite build` 耗时 613ms，0 错误 0 告警）；首屏主包 `index-C6HeJH1S.js` 体积为 **294.82 kB**（Gzip 后 **93.88 kB**），完全满足 **<= 295 kB** 预算红线要求 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 权限指令专项测试套件 | `node --test tests/frontend/can-directive.test.mjs frontend/web/tests/can-directive.test.mjs` | **15 passed, 0 failed** (表格驱动 10 项 + AST/契约断言 5 项) | 0.45s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **221 passed, 0 failed** (包含 15 项权限指令专项单测) | 2.16s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build` 耗时 613ms) | 0.61s |
| 首屏主包体积审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-C6HeJH1S.js` **294.82 kB**（gzip: 93.88 kB），**完全达标 <= 295 kB 门禁** | — |
| 后端八角色权限守卫回归 | `python -m pytest tests/backend/test_eight_roles_access.py -v` | **10 passed, 0 failed** (前后端八角色鉴权契约一致) | 0.28s |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **默认零 DOM 残留的纵深防御价值**：很多前端权限指令仅使用 `style={{ display: 'none' }}` 或 CSS class 隐藏按钮，内部包含的敏感操作属性、API 端点乃至提交数据依然暴露在客户端 DOM 中。APP-M2-T015 默认直接返回 `null`，配合前置路由守卫（APP-M2-T014）与后端守卫（BE-8ROLES-RBAC），构筑了完整的三层纵深防御体系。
2. **递交版 Word 导出专权边界**：PRD 明确强调递交版具有法律投标效力，仅限实际项目负责人导出；企业管理员只负责公司层面统筹，不应替代项目负责人导出正式标书。本模块在 `can-directive.ts` 中单独对 `submission:export` 实施专权约束，体现了对业务合规的高精度把控。
3. **包体积处于预算红线附近**：首屏主包 `index-C6HeJH1S.js` 体积为 294.82 kB，距离 295 kB 预算红线仅有 0.18 kB 裕量。建议后续继续推进分包拆分（如把项目团队抽屉或特定重型组件按需懒加载），以保证后续迭代不会超标。

## 签署状态

APP-M2-T015 保持 **in-review**，**严禁标 done**。
