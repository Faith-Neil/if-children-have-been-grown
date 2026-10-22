为什么有这个文件：记录QA对APP-M2-T007（表单通用交互能力：FormActionFooter、useUnsavedPrompt、服务端错误就近映射与平滑聚焦，REV-M0-T48）的独立复测与签署结论。

它解决什么问题：不轻信前端自报结果，亲手执行表单通用能力专项单测、前端全量单测、生产构建打包与包体积门禁审计（<= 295 kB），针对性核查吸底保存条 FormActionFooter（吸底效果、已修改项统计标签、★ 变动琥珀色高亮警示）、离开未保存双重保护（原生 beforeunload 与应用内 Modal.confirm 弹窗二次确认）、服务端字段级错误就近映射（FastAPI / Pydantic details、字典与嵌套 error 解析、平滑滚动居中聚焦与微动动画）以及 WCAG AA 4.5:1 对比度标准。

# APP-M2-T007 表单通用交互独立复测与 QA 签署（REV-M0-T48）

- 被验任务：[APP-M2-T007](../tasks/APP-M2.md#app-m2-t007) · 表单通用能力
- 关联审查任务：REV-M0-T48
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T007 交付](../delivery/APP-M2-T007.md)、[代码解释](../code/APP-M2-T007.md)
- 被验核心文件：`frontend/web/src/shared/FormActionFooter.tsx`、`frontend/web/src/shared/form-interactions.ts`、`frontend/web/src/shared/useUnsavedPrompt.ts`、`frontend/web/src/library/MetadataForm.tsx`、`frontend/web/src/shared/styles.css`、`frontend/web/tests/form-interactions.test.mjs`、`tests/frontend/form-interactions.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T007 保持 in-review，严禁标 done**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 固底吸附操作条 FormActionFooter | 通过 | `FormActionFooter.tsx` 导出具名与默认组件，样式类 `.icg-form-sticky-footer.is-sticky` 实现 `position: sticky; bottom: 0; z-index: 100` 毛玻璃吸附效果；左侧实时展示脏数据修改统计标签（`.icg-footer-modified-tag`），右侧排列取消、重置（无修改时禁用置灰）与保存（主按钮 Primary，支持 loading 态），长表单无需滚至底部即可随时保存 |
| AC-02 ★ 关键字段变更琥珀色警示 | 通过 | 当 `starredModifiedCount > 0` 时，吸底操作条修改标签自动追加 `.is-starred-modified` 类名，色彩转为琥珀色（文字 `#9a5608`，背景 `#fffbe6`，边框 `#ffe58f`，对比度 > 4.8:1 符合 WCAG AA 4.5:1），明确提示“含 N 项 ★ 关键字段变更，保存后需重新核对” |
| AC-03 离开未保存双重保护拦截 | 通过 | `useUnsavedPrompt.ts` 封装通用 Hook：原生层自动监听并清理 `window.addEventListener('beforeunload')`，阻止意外关闭/刷新标签页；应用内层提供 `confirmNavigation`，通过 Ant Design `Modal.confirm` 弹出模态危险确认框（“当前表单存在未保存的修改，离开将丢失已填内容”），点击取消继续编辑，点击确认才执行路由跳转 |
| AC-04 服务端字段错误就近映射 | 通过 | `mapServerFieldErrors` 支持 4 种错误格式解析：① 直出字段对象 `{ field: msg }`；② FastAPI / Pydantic details 数组 `[{ loc: ["body", field], msg: ... }]`；③ 字典结构 `{ details: { field: msg } }`；④ 嵌套 error 对象；提取的错误通过 `form.setFields` 精确下发至各个 Form.Item，呈现项级红框报错并展示错误信息文案 |
| AC-05 首错项平滑滚动与居中聚焦 | 通过 | `scrollFieldIntoView` 自动计算首个出错字段 DOM 节点，触发 `scrollIntoView({ behavior: 'smooth', block: 'center' })` 安全居中，自动添加 `@keyframes icg-field-error-pulse` 微动震颤高亮动画，并微延迟自动聚焦内部 input / textarea / select 控件；在 Node / SSR 无 DOM 环境下安全降级 |
| AC-06 MetadataForm 深度集成 | 通过 | `MetadataForm.tsx` 无缝接收 `stickyFooter`、`promptOnUnsaved`、`serverErrors` 与 `autoScrollToError` 属性，将脏数据比对、吸底操作栏、离开拦截与就近报错滚动定位全流程打通 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 表单交互专项单测 | `node --test tests/frontend/form-interactions.test.mjs frontend/web/tests/form-interactions.test.mjs` | **11 passed, 0 failed** (纯逻辑 7 项 + AST 断言 4 项) | 0.51s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **178 passed, 0 failed** (含 11 项通用交互专项测试) | 1.83s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build`，0 错误 0 告警) | 1.01s |
| 主包体积门禁审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-BYE3n_St.js` **289.99 kB**（gzip: 92.21 kB），**完全满足 <= 295 kB 门禁要求**，体积保持零增长 | — |
| 治理一致性核查 | `node scripts/check-project-governance.cjs` | **检查通过** (370 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与边界提示

1. **错误定位体验流畅**：`scrollFieldIntoView` 采用 `block: 'center'` 而非默认的 `block: 'start'`，有效避免了吸顶导航栏或表头遮挡错误字段标题的问题，且内置了 `icg-field-error-pulse` 脉冲高亮与自动聚焦，交互体验极佳。
2. **Bundle 控制完美守门**：自 APP-M2-T003（289.96 kB）、T004（289.99 kB）、T005（289.99 kB）、T006（289.99 kB）至 T007（289.99 kB），前端主包体积在增加大量状态、标签、元数据表格、元数据表单与交互逻辑后，依然精准压在 289.99 kB，组件模块化与按需引入治理非常扎实。

## 签署状态

APP-M2-T007 保持 **in-review**，**严禁标 done**。
