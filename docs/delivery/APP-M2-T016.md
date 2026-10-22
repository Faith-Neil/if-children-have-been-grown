为什么有这个文件：记录 APP-M2-T016 数据权限的前端表现：只读态切换（项目 / 分册 / 章节）的交付状态、实现内容与验收证据。

它解决什么问题：集中呈现多粒度数据权限判定算法、只读纯文本排版表现、首屏 Bundle 体积控制（<= 295 kB）与自动化单测证据，不提前标 done，供任务验收与质量审计。

# APP-M2-T016：数据权限的前端表现：只读态切换交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T016 |
| 代码解释 | [docs/code/APP-M2-T016.md](../code/APP-M2-T016.md) |
| 验收 | 12 项专属自动化单测通过；全量 233 项前端单测通过；生产构建首屏产物 294.86 kB <= 295 kB 门禁达标；工程治理通过 |
| 项目进度 | 前端 M2 阶段推进，APP-M2-T016 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T016](../tasks/APP-M2.md#app-m2-t016)
- 依赖任务：[APP-M2-T010](../tasks/APP-M2.md#app-m2-t010)、[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)、[APP-M2-T015](../tasks/APP-M2.md#app-m2-t015)
- 分支：`feat/opencode-ICG`
- 本地验收状态：**in-review**（严禁私自标 done）
- 合入 / 发布状态：未合入主干，未发布

---

## 完成内容与变更文件

### 1. 核心产出
1. **多粒度数据权限判定层 (`frontend/web/src/shell/data-permission.ts`)**：
   - 实现了纯函数 `resolveDataPermission(context)`，支持根据系统角色、项目团队角色、主管分册与章节指派综合判定；
   - 输出包括 `readOnly: boolean`、`canEdit: boolean`、`scope: 'project' | 'volume' | 'chapter' | 'none'`、`scopeName: string`、`readOnlyReason: string`、`reasonType`、`role` 与 `roleLabel`；
   - 严格覆盖系统级只读角色（集团管理员/只读成员/审计员/平台管理员）、项目内只读成员、分册主管跨分册浏览、普通编写人跨章节浏览等场景。
2. **React Hook 封装 (`frontend/web/src/shell/useDataPermission.ts`)**：
   - 提取 `CanContext` 与 `ProjectContext`，无缝响应角色与分工变动，动态返回数据权限状态。
3. **只读表现组件与纯文本渲染 (`frontend/web/src/shell/ReadOnlyGate.tsx`)**：
   - `<ReadOnlyGate>`：容器级只读控制网关，集成 `ReadonlyBanner` 横幅与 `readOnlyView` 纯文本插槽；
   - `<ReadOnlyField>` / `<ReadOnlyText>`：字段级组件，当处于只读模式时，**直接在 DOM 中渲染排版语义 `<span>` 纯文本，完全不渲染 `<input>` 或 `<textarea>` 再 disabled**，严格落实 PRD v1.8 §5.11.9 验收约束。
4. **编辑台与表单页面落地 (`frontend/web/src/editor/EditorPage.tsx`, `frontend/web/src/library/MetadataForm.tsx`)**：
   - `EditorPage`：接入 `useDataPermission`，在无编辑权或只读态时，正文区自动切换为带浅底边框的高对比度纯文本段落（`<div className="chapter-editor-readonly-view"><div className="chapter-editor-readonly-text" data-testid="readonly-editor-text"><pre>...`），顶部呈现带具体范围与原因的 `ReadonlyBanner`；
   - `MetadataForm`：新增 `readOnly?: boolean` 选项，开启时表单各项切换为 `ReadOnlyField` 纯文本输出，并自动隐藏底部提交操作条；
   - `styles.css`：定义高对比度只读排版样式。

### 2. 变更文件清单
- `frontend/web/src/shell/data-permission.ts` (新增): 多粒度数据权限判定核心算法与类型定义
- `frontend/web/src/shell/useDataPermission.ts` (新增): React Hook 封装
- `frontend/web/src/shell/ReadOnlyGate.tsx` (新增): `ReadOnlyGate` 与 `ReadOnlyField` 表现层组件
- `frontend/web/src/editor/EditorPage.tsx` (修改): 编辑台接入只读态纯文本渲染与只读横幅
- `frontend/web/src/library/MetadataForm.tsx` (修改): 支持 `readOnly` 纯文本排版与操作条自动隐藏
- `frontend/web/src/shared/styles.css` (修改): 增加只读视图与文本样式
- `tests/frontend/data-permission.test.mjs` (新增): 6 项表格驱动多粒度数据权限单元测试
- `frontend/web/tests/data-permission.test.mjs` (新增): 6 项 AST 契约与纯文本零控件断言测试
- `docs/code/APP-M2-T016.md` (新增): 代码解释文档
- `docs/delivery/APP-M2-T016.md` (新增): 交付记录文档

---

## 验收证据

### 1. 自动化单元测试（100% 通过）
运行命令：
```powershell
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
测试输出：
```text
ℹ tests 233
ℹ suites 0
ℹ pass 233
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2523.2164
```
全量 233 项测试全部绿色通过（包含新增的 12 项多粒度数据权限专属测试）。

### 2. 构建产物体积审计（<= 295 kB 门禁达标）
运行命令：
```powershell
pnpm --dir frontend/web build
```
构建输出：
```text
dist/index.html                                0.94 kB │ gzip:   0.57 kB
dist/assets/index-DxiuVLoO.css                30.10 kB │ gzip:   6.82 kB
dist/assets/rolldown-runtime-8BhlS34s.js       0.80 kB │ gzip:   0.47 kB
dist/assets/sla-form-a6AqMBie.js               2.78 kB │ gzip:   1.42 kB
dist/assets/popover-Dy7Y8T45.js                5.30 kB │ gzip:   2.18 kB
dist/assets/collapse-BH52iPNU.js              10.50 kB │ gzip:   3.85 kB
dist/assets/SupportPages-DqWKE_n6.js          11.32 kB │ gzip:   4.52 kB
dist/assets/ProjectSettingsPage--1v7SuLB.js   22.57 kB │ gzip:   8.92 kB
dist/assets/result-BJ4tHomv.js                33.86 kB │ gzip:  10.39 kB
dist/assets/SlaPages-Aj8HgBbd.js              36.52 kB │ gzip:  12.05 kB
dist/assets/zh_CN-vK_Yfa8y.js                 39.18 kB │ gzip:  11.28 kB
dist/assets/EditorPage-Dqyc6Hf0.js            98.74 kB │ gzip:  32.03 kB
dist/assets/ProjectPages-fK2lnAZv.js         116.10 kB │ gzip:  34.97 kB
dist/assets/AppShell-5zcXhWSv.js             223.69 kB │ gzip:  73.43 kB
dist/assets/project-team-DJIscAnz.js         294.79 kB │ gzip:  90.01 kB
dist/assets/index-fu3kmuVM.js                294.86 kB │ gzip:  93.90 kB
dist/assets/jsx-runtime-DNp14iXa.js          437.98 kB │ gzip: 144.54 kB
✓ built in 632ms
```
首屏主包 `index-fu3kmuVM.js` 体积为 **294.86 kB**（gzip 93.90 kB），严格保持在 **295.00 kB 红线以内**，无重型外部依赖泄漏。

### 3. 工程治理检查
运行命令：
```powershell
node scripts/check-project-governance.cjs
```
检查输出：
```text
治理检查通过：399 份 Markdown、397 项任务、37 项 Issue。
```

---

## 结论与待决事项
- `APP-M2-T016` 前端开发、排版文本展示与测试断言全部完成，提交代码审查；
- 状态更新为 **in-review**，关联 ISSUE-007 保持开启，等待 QA 与主 Agent 联合评审。
