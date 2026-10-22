为什么有这个文件：记录QA对APP-M2-T006（元数据驱动表单封装：MetadataForm、metadata-form.ts，REV-M0-T47）的独立复测与签署结论。

它解决什么问题：不轻信前端自报结果，亲手执行表单专项单测回归、前端全量单测、生产打包构建与包体积门禁审计（<= 295 kB），针对性核查 ★ 关键字段修改提示（Alert 醒目横幅与项级黄色边框高亮，合规规范 §5.2.2 与 PRD §5.12 自动转入待确认状态提醒）、系统键双行排版规范、不支持/未启用字段（supported: false / 无权限）置灰禁用与 Tooltip 明确原因说明及免必填校验、多类型控件映射（文本、长文本、数值带单位、日期、布尔开关、枚举选择）与栅格布局。

# APP-M2-T006 元数据驱动表单封装独立复验与 QA 签署（REV-M0-T47）

- 被验任务：[APP-M2-T006](../tasks/APP-M2.md#app-m2-t006) · 元数据驱动表单封装
- 关联审查任务：REV-M0-T47
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T006 交付](../delivery/APP-M2-T006.md)、[代码解释](../code/APP-M2-T006.md)
- 被验核心文件：`frontend/web/src/MetadataForm.tsx`、`frontend/web/src/metadata-form.ts`、`frontend/web/src/styles.css`、`frontend/web/tests/metadata-form.test.mjs`、`tests/frontend/metadata-form.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T006 保持 in-review，严禁标 done**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 ★ 关键字段修改提示与合规横幅 | 通过 | `getModifiedStarredFields` 基于 `areValuesEquivalent` 算法精确捕获关键字段变动，忽略非关键字段；修改关键字段时，表单顶部展示 Ant Design `Alert` 醒目横幅（`.icg-starred-warning-banner`，type="warning"），严格落地合规规范（§5.2.2 与 PRD §5.12）关于“修改保存后自动转入待确认状态、须人工重新核对”的合规警示；变动字段项级追加 `.icg-form-item-starred-modified` 黄色边框高亮；恢复原值自动解除提示 |
| AC-02 系统键双行排版与 ★ 前缀 | 通过 | `resolveTwoLineLabel` 驱动表单标签双行渲染（`.icg-form-two-line-label`）：主标题 `.icg-label-primary` 包含业务中文名与关键字段 ★ 红色指示器（`.icg-starred-indicator`）；次标签 `.icg-label-secondary` 使用等宽字体（SFMono-Regular/Consolas）与次要色 `#4e5969`（WCAG AA 4.5:1 达标），在系统键与主标签同名时自动折叠避免冗余，严格符合设计规范 §9.2 规则 2 |
| AC-03 不支持/只读/无权字段置灰与 Tooltip 解释 | 通过 | `resolveFieldDisabledState` 精准识别 `supported: false`（版本未支持）、`editable: false`（系统只读）与 `userCanEdit: false`（无编辑权限）；置灰字段控件被 `Tooltip` 悬浮浮层包裹，明确解释禁用原因；表单项下方以 `.icg-field-disabled-hint` 伴随 `LockOutlined` 锁图标展示辅助文案；禁用项智能豁免必填校验（`field.required && !disabledState.disabled`），防止阻断表单保存 |
| AC-04 多数据类型控件分流映射 | 通过 | `MetadataForm` 完备分流：长文本 `textarea` 渲染 `Input.TextArea`（默认 3 行、占满 24 栅格）；数值型 `number` 渲染 `InputNumber`（支持 `addonAfter` 单位后缀）；日期与时间渲染原生 `Input type="date"` 与 `type="datetime-local"`；布尔型渲染 `Switch` 开关；枚举型渲染 `Select`；默认单行文本渲染标准 `Input` |
| AC-05 响应式栅格布局与 Schema 兜底 | 通过 | 支持 1 栏（span 24）、2 栏（span 12）、3 栏（span 8）响应式栅格排版，行间距采用标准 16px gutter；预置企业主体（`org_entity`）与项目（`project`）降级 Schema，未知分类安全生成兜底表单结构，组件绝不崩溃 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 元数据表单专项单测 | `node --test tests/frontend/metadata-form.test.mjs frontend/web/tests/metadata-form.test.mjs` | **12 passed, 0 failed** (纯逻辑 6 项 + AST 断言 6 项) | 0.46s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **167 passed, 0 failed** (含 12 项表单专项测试) | 1.88s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build`，0 错误 0 告警) | 1.10s |
| 主包体积门禁审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-CChtEApQ.js` **289.99 kB**（gzip: 92.21 kB），**严格满足 <= 295 kB 门禁要求** | — |
| 治理一致性核查 | `node scripts/check-project-governance.cjs` | **检查通过** (369 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与边界提示

1. **★ 字段修改拦截与提示高度严谨**：通过 `areValuesEquivalent` 处理空值等价性（如空串与 null / undefined）和两端空格，有效避免了由于表单初始化空值抖动引起的误报，只有真实值发生改变时才会激活 §5.2.2 待确认警示横幅。
2. **包体积控制极为优秀**：经过状态组件（T003）、业务小组件（T004）、元数据表格（T005）与元数据表单（T006）连续四轮功能封装，前端主入口 Bundle 始终保持在 289.99 kB，组件逻辑解耦与代码分割架构非常健康。

## 签署状态

APP-M2-T006 保持 **in-review**，**严禁标 done**。
