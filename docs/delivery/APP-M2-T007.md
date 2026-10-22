为什么有这个文件：交付表单通用能力（吸底保存条 FormActionFooter、离开未保存拦截 useUnsavedPrompt、服务端字段级错误就近映射与滚动定位）的封装实现、单元测试与构建验证结果。

它解决什么问题：实现表单固底吸附操作条（Sticky Footer Bar），实时展示“已修改 N 项”脏数据状态与 ★ 关键字段变更警示；提供原生 beforeunload 与应用内 Modal 拦截双重未保存离开保护；解析服务端 400 / 422 字段级错误并就近映射至表单项，通过平滑滚动将首个出错项居中聚焦；Bundle 体积维持 289.99 kB 零膨胀，符合 WCAG AA 4.5:1 对比度标准。

# APP-M2-T007：表单通用能力交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T007 |
| 代码解释 | [代码解释](../code/APP-M2-T007.md) |
| 验收 | 前端 178 项测试全部通过（含 11 项表单通用交互专项测试）、`pnpm --dir frontend/web build` 成功通过且产物体积完全达标（index 289.99 kB < 295 kB 门禁，构建耗时 582ms）；固底操作条（FormActionFooter）、未保存离开拦截保护（useUnsavedPrompt）、服务端字段级错误就近映射与居中聚焦（mapServerFieldErrors + scrollFieldIntoView）均通过自动化验证 |
| 项目进度 | 标至 in-review。关联 ISSUE-007。依赖 BE-M0-T01（已 done）、APP-M2-T006（in-review）。下一任务：按看板推进 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T007](../tasks/APP-M2.md#app-m2-t007)
- 前置依赖：[BE-M0-T01](../tasks/BE-M0.md#be-m0-t01)（done）、[APP-M2-T006](../tasks/APP-M2.md#app-m2-t006)（in-review）
- 契约接口：通用前端交互规范与 HTTP 400/422 错误体
- 分支：`feat/opencode-ICG`
- 本地验收状态：本地自动化测试与生产构建全部通过，已按流程标至 `in-review`，等待主 Agent、QA 与项目经理评审，严禁私自标 `done`
- 合入 / 发布状态：未合入生产分支，未发布

## 完成内容与变更文件

本次任务在 `frontend/web/` 下完成了表单通用交互能力的全面实现，覆盖任务指派与设计规范中的所有核心要求：

1. **`frontend/web/src/shared/form-interactions.ts`（新增）**：
   - 纯函数逻辑层，定义 `FieldChangeSummary`、`ServerFieldError`、`AntFormFieldError`、`MappedServerErrors` 等契约；
   - 实现了 `detectDirtyFields`：比对初始值与实时值，计算已修改项数 `modifiedCount`、脏数据布尔值 `isDirty` 与 ★ 关键字段修改数 `starredModifiedCount`，生成易懂的修改摘要文案；
   - 实现了 `mapServerFieldErrors`：多格式错误体解析器，兼容 FastAPI / Pydantic details 数组（含 `loc` 路径）、字典映射、直接字段对象与嵌套 `error` 结构，提取出符合 Ant Design Form 规范的 `fieldErrors` 与首个出错字段 `firstErrorField`；
   - 实现了 `scrollFieldIntoView`：执行安全的平滑滚动（`behavior: 'smooth', block: 'center'`）将首错字段居中并微延迟聚焦输入框，在 Node/SSR 环境下安全降级；
   - 实现了 `shouldBlockNavigation` 与 `applyBeforeUnloadEvent` 离开拦截纯规则。

2. **`frontend/web/src/shared/FormActionFooter.tsx`（新增）**：
   - 封装吸底操作条组件 `FormActionFooter`；
   - 容器支持 `sticky` 固底吸附展示（`.icg-form-sticky-footer.is-sticky`），具有毛玻璃背景与微上阴影，长表单无需滚到底部即可保存；
   - 左侧实时呈现修改统计标签（`dirty-count-tag`），并在 ★ 关键字段变更时以琥珀色高亮警示；
   - 右侧排列取消、重置（无脏数据时禁用）、保存（Primary 提交按钮）与自定义扩展插槽，对比度符合 WCAG AA 4.5:1。

3. **`frontend/web/src/shared/useUnsavedPrompt.ts`（新增）**：
   - 封装通用 React Hook `useUnsavedPrompt`；
   - 自动绑定与解绑原生 `beforeunload` 事件；
   - 封装 `confirmNavigation`，通过 Ant Design `Modal.confirm` 弹出模态危险操作确认框（“当前页面有未保存的修改，离开将丢失已填内容”），点击取消继续编辑，点击确认才放行离开。

4. **`frontend/web/src/library/MetadataForm.tsx`（修改）**：
   - 增加 `stickyFooter`、`showCancelButton`、`cancelText`、`resetText`、`promptOnUnsaved`、`serverErrors`、`autoScrollToError`、`onReset`、`onCancel` 属性；
   - 接入 `detectDirtyFields` 与 `useUnsavedPrompt`；
   - 监听 `serverErrors`，自动通过 `form.setFields` 映射红框报错并调用 `scrollFieldIntoView` 居中聚焦；
   - 底部操作栏集成 `FormActionFooter`。

5. **`frontend/web/src/shared/styles.css`（修改）**：
   - 增加 `.icg-form-sticky-footer` 及 `.is-sticky` 吸底样式；
   - 增加 `.icg-footer-inner`、`.icg-footer-left-info`、`.icg-footer-modified-tag`、`.icg-footer-right-actions` 弹性排版样式；
   - 增加 `@keyframes icg-field-error-pulse` 错误字段高亮微动动画。

6. **`tests/frontend/form-interactions.test.mjs` 与 `frontend/web/tests/form-interactions.test.mjs`（新增）**：
   - 新增 11 项专属自动化测试，覆盖纯逻辑层（脏数据比对、FastAPI/Pydantic 错误映射、Node 环境 DOM 安全性、离开拦截规则）与组件/Hook 静态 AST 结构断言。

## 代码解释

详细调用链、状态时序图、算法原理与异常分支处理参见 [APP-M2-T007 代码解释](../code/APP-M2-T007.md)。

## 验收结果

### 1. 自动化测试套件执行
在仓库根目录执行专属测试：
```bash
node --test tests/frontend/form-interactions.test.mjs frontend/web/tests/form-interactions.test.mjs
```
执行输出：
```
✔ FormActionFooter is declared and exported as named and default export with sticky bar and tags (1.2291ms)
✔ useUnsavedPrompt implements beforeunload listener and modal confirm navigation (0.2457ms)
✔ MetadataForm deeply integrates FormActionFooter, useUnsavedPrompt, and serverErrors mapping (0.2013ms)
✔ styles.css contains sticky footer and error pulse animation styles (0.2682ms)
✔ areValuesEquivalent safely compares various scalar and array types (1.0923ms)
✔ detectDirtyFields accurately computes modified count and starred fields (1.3981ms)
✔ mapServerFieldErrors parses direct field error objects (0.4882ms)
✔ mapServerFieldErrors parses details array from FastAPI / Pydantic style errors (0.2468ms)
✔ mapServerFieldErrors parses dictionary details and nested error structures (0.2297ms)
✔ scrollFieldIntoView handles missing DOM environment gracefully (0.2131ms)
✔ shouldBlockNavigation and applyBeforeUnloadEvent enforce leave protection rules (0.1386ms)
ℹ tests 11
ℹ suites 0
ℹ pass 11
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ duration_ms 387.9403
```

在仓库根目录执行前端全量回归测试：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
执行输出：
```
ℹ tests 178
ℹ suites 0
ℹ pass 178
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ duration_ms 1873.4533
```
全量 178 项前端单测与结构断言全部通过（0 失败，0 跳过）。

### 2. 前端生产构建验证
在仓库根目录执行前端打包验证：
```bash
pnpm --dir frontend/web build
```
执行输出：
```
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 3338 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                0.94 kB │ gzip:   0.57 kB
dist/assets/index-DLYB0tV0.css                28.66 kB │ gzip:   6.54 kB
dist/assets/rolldown-runtime-8BhlS34s.js       0.80 kB │ gzip:   0.47 kB
dist/assets/sla-form-a6AqMBie.js               2.78 kB │ gzip:   1.42 kB
dist/assets/popover-DhI_cfxl.js                5.29 kB │ gzip:   2.18 kB
dist/assets/collapse-D71feMj7.js              10.50 kB │ gzip:   3.84 kB
dist/assets/SupportPages-CU7-0BQT.js          11.32 kB │ gzip:   4.53 kB
dist/assets/ProjectSettingsPage-BCm580zR.js   22.57 kB │ gzip:   8.93 kB
dist/assets/zh_CN-CW6Acanq.js                 30.72 kB │ gzip:   9.08 kB
dist/assets/result-wUuRZqen.js                33.86 kB │ gzip:  10.38 kB
dist/assets/SlaPages-OxsNcogZ.js              36.52 kB │ gzip:  12.06 kB
dist/assets/EditorPage-CgUzvh8s.js            94.76 kB │ gzip:  30.78 kB
dist/assets/ProjectPages-qrmHAeVI.js         116.10 kB │ gzip:  34.94 kB
dist/assets/AppShell-pNC8JYe5.js             216.51 kB │ gzip:  71.55 kB
dist/assets/index-BYE3n_St.js                289.99 kB │ gzip:  92.21 kB
dist/assets/project-team-DImcaK6u.js         301.24 kB │ gzip:  91.87 kB
dist/assets/jsx-runtime-CoO3AFfp.js          431.47 kB │ gzip: 142.66 kB

✓ built in 582ms
```
构建结果分析：
- 核心首屏 Chunk `dist/assets/index-BYE3n_St.js` 依然严格锁定在 289.99 kB（gzip: 92.21 kB），无任何多余依赖引入，相比之前保持 0 字节体积膨胀，严格优于 295 kB 门禁；
- CSS 产物 `dist/assets/index-DLYB0tV0.css` 仅 28.66 kB；
- 构建耗时 582ms，TypeScript 编译零错误零告警。

## 未完成范围与限制说明

本任务聚焦于长表单通用的吸底操作栏、脏数据已修改项统计、未保存离开保护与服务端字段错误就近居中平滑聚焦定位。复杂动态子表格列表（Form.List 级联嵌套）及定时草稿自动同步，将由对应专项业务模块按需扩展。
