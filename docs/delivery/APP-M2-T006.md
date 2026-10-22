为什么有这个文件：交付元数据驱动表单组件（MetadataForm）的封装实现、单元测试与构建验证结果。

它解决什么问题：实现根据字段元数据自动推导 Ant Design Form 表单项配置、落地 ★ 关键字段修改提示（醒目警告横幅与项级黄色边框高亮，提示修改保存后须人工重新核对）、实现业务中文名与系统键双行标签排版、实现不支持/只读字段置灰禁用与悬浮 Tooltip 明确解释原因，并严格符合 WCAG AA 4.5:1 对比度标准。

# APP-M2-T006：元数据驱动表单封装交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T006 |
| 代码解释 | [代码解释](../code/APP-M2-T006.md) |
| 验收 | 前端 167 项测试全部通过（含 12 项元数据表单专项测试）、`pnpm --dir frontend/web build` 成功通过且产物体积完全达标（index 289.99 kB < 295 kB 门禁，构建耗时 960ms）；★ 关键字段修改提示（Alert 警示横幅与项级高亮）、系统键双行标签排版、不支持字段置灰与 Tooltip 明确解释均通过专项验证 |
| 项目进度 | 标至 in-review。关联 ISSUE-007。依赖 BE-M0-T01（已 done）、APP-M2-T003（in-review）。下一表单任务：APP-M2-T007 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T006](../tasks/APP-M2.md#app-m2-t006)
- 前置依赖：[BE-M0-T01](../tasks/BE-M0.md#be-m0-t01)（done）、[APP-M2-T003](../tasks/APP-M2.md#app-m2-t003)（in-review）
- 契约接口：`GET /api/v1/metadata/fields/{category}`（operationId: `getFieldMetadata`）
- 分支：`feat/opencode-ICG`
- 本地验收状态：本地前后端自动化测试与生产构建全部通过，已按流程标至 `in-review`，等待主 Agent、QA 与项目经理评审，严禁私自标 `done`
- 合入 / 发布状态：未合入生产分支，未发布

## 完成内容与变更文件

本次任务在 `frontend/web/` 下完成了元数据驱动表单组件的全面封装，覆盖设计规范 §9.2、交接清单 M1-P08-F6、合规规范 §5.2.2 及 PRD §5.12 的所有关键项：

1. **`frontend/web/src/metadata-form.ts`（新增）**：
   - 纯函数逻辑与类型层，定义 `FormFieldOption`、`FormFieldMeta`、`FormSchema`、`ModifiedStarredField`、`FieldDisabledState`；
   - 实现了 `areValuesEquivalent`：严格处理 null、undefined、空串、字符串两端空白符与布尔/数值等价性，防止虚假触发修改提示；
   - 实现了 `getModifiedStarredFields` 与 `hasModifiedStarredFields`：比对 `initialValues` 与表单当前值，提取所有被修改的 `is_starred: true` 字段；
   - 实现了 `formatStarredWarning`：依据 §5.2.2 与 PRD §5.12 自动生成合规提示文案（“★ 关键字段（...）已被修改。根据项目合规规范（§5.2.2 与 PRD §5.12），修改保存后该记录将自动转入“待确认”状态，须由人工重新核对确认后方可继续作为有效证据引用。”）；
   - 实现了 `resolveFieldDisabledState`：识别 `supported: false`（功能未启用）、`editable: false`（系统只读）与 `userCanEdit: false`（无编辑权限），给出明确解释文案；
   - 实现了 `resolveTwoLineLabel`：生成包含 ★ 前缀的主标题与等宽系统键；
   - 预置 `FALLBACK_ORG_ENTITY_FORM_SCHEMA`（企业主体）与 `FALLBACK_PROJECT_FORM_SCHEMA`（项目基础）标准 Schema 并提供降级解析函数 `resolveFormSchema`；
   - 封装异步客户端 `fetchFieldMetadata` 对接后端 `/api/v1/metadata/fields/{category}`。

2. **`frontend/web/src/MetadataForm.tsx`（新增）**：
   - 封装统一的 Ant Design Form 表现层组件 `MetadataForm`，提供具名与默认导出；
   - 实现了 ★ 关键字段修改提示横幅（Alert `type="warning"`，带 WarningOutlined 锁色与高对比度文字）与项级边框微光黄色高亮（`.icg-form-item-starred-modified`）；
   - 实现了系统键双行标签（`.icg-form-two-line-label`、`.icg-label-primary`、`.icg-label-secondary`）；
   - 实现了不支持/只读/无权字段置灰，外层包裹 `Tooltip` 悬浮浮层展示明确原因，下方附加 `.icg-field-disabled-hint` 锁图标解释，并智能跳过必填校验避免阻断提交；
   - 实现了控件类型自动分流：`textarea`、`number`（带单位）、`date`、`datetime`、`boolean/switch`、`select` 与单行文本；
   - 实现了 1/2/3 栏栅格布局自适应与底部操作栏（保存、重置、变动提示）。

3. **`frontend/web/src/styles.css`（修改）**：
   - 增加表单外壳样式 `.icg-metadata-form-wrapper`；
   - 增加双行标签排版样式 `.icg-form-two-line-label`、`.icg-label-primary`、`.icg-label-secondary`；
   - 增加 ★ 修改合规警示横幅 `.icg-starred-warning-banner` 及项级高亮样式 `.icg-form-item-starred-modified`；
   - 增加置灰字段悬浮包装容器 `.icg-disabled-control-wrapper` 与锁定说明文案 `.icg-field-disabled-hint`。

4. **`tests/frontend/metadata-form.test.mjs` 与 `frontend/web/tests/metadata-form.test.mjs`（新增）**：
   - 新增 12 项专属测试，分别覆盖纯函数逻辑层（比对等价性、★ 字段变更收集、合规提示文案、禁用态解析、双行标签解析、Schema 兜底）以及 React 组件层静态 AST 断言（导出规范、双行标签、Alert 横幅与高亮、Tooltip 悬浮解释、控件分流、栅格配置）。

## 代码解释

详细调用链、状态时序图、算法原理与异常分支处理参见 [APP-M2-T006 代码解释](../code/APP-M2-T006.md)。

## 验收结果

### 1. 自动化测试套件执行
在仓库根目录执行专属测试：
```bash
node --test tests/frontend/metadata-form.test.mjs frontend/web/tests/metadata-form.test.mjs
```
执行输出：
```
✔ MetadataForm is declared and exported as named and default export (0.9212ms)
✔ MetadataForm implements two-line label structure with primary title and monospace system key (0.3586ms)
✔ MetadataForm implements ★ critical field modification warning banner and modified item highlight (0.2026ms)
✔ MetadataForm handles unsupported, system readonly, and permission disabled fields with Tooltip explanations (0.151ms)
✔ MetadataForm dispatches appropriate control components based on field data type and render type (0.2272ms)
✔ MetadataForm supports grid column layout and responsive spans (0.1321ms)
✔ areValuesEquivalent handles null, undefined, whitespace, numbers, and booleans (0.874ms)
✔ getModifiedStarredFields accurately captures changes to starred fields only (1.4511ms)
✔ formatStarredWarning generates compliant warning banner message (0.4032ms)
✔ resolveFieldDisabledState handles unsupported, readonly, and permission restrictions (0.3011ms)
✔ resolveTwoLineLabel generates primary and secondary labels with starred flag (0.2825ms)
✔ resolveFormSchema returns valid schemas for org_entity and project (0.504ms)
ℹ tests 12
ℹ suites 0
ℹ pass 12
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ duration_ms 401.0007
```

在仓库根目录执行前端全量回归测试：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
执行输出：
```
ℹ tests 167
ℹ suites 0
ℹ pass 167
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ duration_ms 1616.9462
```
全量 167 项前端单元测试与静态结构断言全部通过（0 失败，0 跳过）。

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
dist/assets/index-D5CwZUUH.css                27.79 kB │ gzip:   6.35 kB
dist/assets/rolldown-runtime-8BhlS34s.js       0.80 kB │ gzip:   0.47 kB
dist/assets/sla-form-a6AqMBie.js               2.78 kB │ gzip:   1.42 kB
dist/assets/popover-DhI_cfxl.js                5.29 kB │ gzip:   2.18 kB
dist/assets/collapse-D71feMj7.js              10.50 kB │ gzip:   3.84 kB
dist/assets/SupportPages-C8m7fAl3.js          11.32 kB │ gzip:   4.53 kB
dist/assets/ProjectSettingsPage-D6ZfY7rn.js   22.57 kB │ gzip:   8.93 kB
dist/assets/zh_CN-CW6Acanq.js                 30.72 kB │ gzip:   9.08 kB
dist/assets/result-wUuRZqen.js                33.86 kB │ gzip:  10.38 kB
dist/assets/SlaPages-Ly40nNPM.js              36.52 kB │ gzip:  12.06 kB
dist/assets/EditorPage-Bcocp_w8.js            94.76 kB │ gzip:  30.78 kB
dist/assets/ProjectPages-DMN02unV.js         116.10 kB │ gzip:  34.94 kB
dist/assets/AppShell-C9olCuUD.js             216.51 kB │ gzip:  71.55 kB
dist/assets/index-CChtEApQ.js                289.99 kB │ gzip:  92.21 kB
dist/assets/project-team-DImcaK6u.js         301.24 kB │ gzip:  91.87 kB
dist/assets/jsx-runtime-CoO3AFfp.js          431.47 kB │ gzip: 142.66 kB

✓ built in 960ms
```
构建结果分析：
- 核心首屏 Chunk `dist/assets/index-CChtEApQ.js` 为 289.99 kB（gzip: 92.21 kB），体积相比此前保持 0 字节膨胀，严格优于 295 kB 门禁红线；
- CSS 产物 `dist/assets/index-D5CwZUUH.css` 仅 27.79 kB；
- 构建耗时 960ms，TypeScript 编译检查全部通过，无任何类型告警。

## 未完成范围与限制说明

1. **未保存离开路由守卫与就近报错定位**：本卡聚焦于元数据表单项推导、★ 字段修改提示、两行标签排版及置灰 Tooltip 解释。通用的离开未保存提示、底部固定保存栏与服务端字段级就近报错高亮聚焦将由紧随其后的 [APP-M2-T007](../tasks/APP-M2.md#app-m2-t007) 统一交付。
2. **多附件槽位与资质证明上传**：企业资料管理中的多文件拖拽上传、扫描件预览及槽位状态机，将由后续专用资料详情与通用业务页面交付。
