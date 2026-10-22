为什么有这个文件：记录QA对APP-M2-T005（元数据驱动表格封装：MetadataTable / ProTableWrapper、metadata-table.ts）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手执行前端单测全量回归、生产环境打包构建与体积审计，深度核查元数据驱动列推导、双行表头、动态 rowSpan 行合并算法、1280px 宽度预算引擎（1040px 无横滚优先与超宽左右列锁定）、560px 侧边抽屉查阅完整长文本、星号/废标/资格条款批量确认门禁拦截（§5.2.2）、风险红底（#FFF5F5）与急迫行判定。

# APP-M2-T005 元数据驱动表格封装独立复验与 QA 签署（REV-M0-T44）

- 被验任务：[APP-M2-T005](../tasks/APP-M2.md#app-m2-t005) · 元数据驱动表格封装
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T005 交付](../delivery/APP-M2-T005.md)、[代码解释](../code/APP-M2-T005.md)
- 被验核心文件：`frontend/web/src/MetadataTable.tsx`、`frontend/web/src/metadata-table.ts`、`frontend/web/src/styles.css`、`frontend/web/tests/metadata-table.test.mjs`、`tests/frontend/metadata-table.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T005 保持 in-review，严禁标 done**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 元数据驱动列推导与类型渲染 | 通过 | `resolveTableMeta` 解析预置要求矩阵、资料库、事实表 Schema 与通用兜底；`MetadataTable` 根据 `FieldDataType` 分流映射渲染，数值列自动右对齐，等宽时间格式化，深度集成 `LevelTag`、`AiTag`、`DirectTag`、`Cite` 与 `SourceBar` 业务组件 |
| AC-02 双行表头规范支持 | 通过 | 表头渲染 `.icg-two-line-header`，包含中文主标签 `.icg-header-primary`（支持星号条款 `★ ` 提示标记）与等宽小字系统键 `.icg-header-secondary`，严格契合设计规范 §9.2 规则 2 |
| AC-03 动态 rowSpan 跨行合并算法 | 通过 | `calculateRowSpans` 针对相邻连续相同值分组计算跨行数（首行返回 N，后续返回 0）；通过 Table 的 `onCell` 回调安全挂载 `{ rowSpan: span }`；覆盖空数据 `[]`、单行 `[1]`、连续分组 `[2, 0, 3, 0, 0, 1]` 与全独立 `[1, 1, 1]` |
| AC-04 1280px 宽度预算引擎（无横滚优先） | 通过 | `calculateColumnWidthBudget` 在安全内容宽度 1040px（1280px 扣除侧边栏 216px 与边距 48px）内自动为长文本列分配自适应弹性宽度，启用省略号截断；总宽 <= 1040px 时 `fitsWithoutScroll=true` 且 `scroll.x=undefined`，彻底消除非必要水平滚动条；超宽时平滑降级设置 `scroll.x` 并将首列锁定在左侧（`fixed: 'left'`）、操作列锁定在右侧（`fixed: 'right'`） |
| AC-05 560px 侧边抽屉查阅完整长文本 | 通过 | 单元格内提供“查看”按钮（`.icg-detail-trigger`），点击在 560px 宽度的 Ant Design `Drawer` 侧栏抽屉中展示完整原文（`whiteSpace: 'pre-wrap'`）、条款级别、引用证据与来源指纹，保障紧凑排版与长文本无障碍查阅两全 |
| AC-06 合规批量确认门禁拦截（§5.2.2 / 规范 9.1 ⑥） | 通过 | `canBatchConfirm` 严格识别星号条款（★）、废标/阻断条款（blocker / disqualification）、资格审查条款（qualification）及严重评分条款；当选区中包含上述条款时，返回 `allowed: false`，批量浮动栏（`.icg-batch-bar`）弹出红底合规警告，批量确认按钮置灰禁用并阻断 Popconfirm，强制逐项人工核对 |
| AC-07 风险红底与急迫行判定 | 通过 | `isRiskRow` 识别阻断条款、证据失效、待审核或负偏离行，自动添加 `.row-danger` 类名并渲染浅红底色 `#FFF5F5`（规范 9.1 规则 4）；`isUrgentRow` 识别 3 天内到期项目自动添加 `.row-urgent` 类名并渲染左侧红边提示（`box-shadow: inset 3px 0 0 #d9363e`） |
| AC-08 通用状态组件深度集成 | 通过 | 加载中且无数据时降级渲染 5 行表格骨架屏（`SkeletonView variant="table" rows={5}`）；接口报错时降级渲染带 traceId 一键复制的错误态（`ErrorView`）；搜索无结果或空数据时自适应切换 `EmptyState` |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 前端全量单测 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **155 passed, 0 failed** (含 14 项元数据表格专项断言) | 1.58s |
| 表格专项单测 | `node --test tests/frontend/metadata-table.test.mjs frontend/web/tests/metadata-table.test.mjs` | **14 passed, 0 failed** (算法与 AST 断言全绿) | 0.42s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build`，0 错误 0 告警) | 0.96s |
| 产物体积审计 | 检查 `frontend/web/dist/assets/` | `index.js` **289.99 kB** (gzip: 92.21 kB)，产物体积无膨胀，代码分割平稳 | — |
| 治理一致性核查 | `node scripts/check-project-governance.cjs` | **检查通过** (360 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与边界提示

1. **1280px 宽度预算策略设计卓越**：通过标准内容宽 1040px 预估与长文本动态剩余宽均分，保证了 Ant Design Table 在标准桌面下默认不带 `scroll.x`，避免了原生 Table 容易出现的无意义横向滚动阴影。
2. **合规批量确认硬约束有效**：星号、废标与资格三类关键条款的批量拦截机制直接嵌入在组件的逻辑判定中，无论外部如何勾选，底层门禁均能可靠拦截非法批量操作，直接杜绝重大合规废标事故隐患。
3. **560px 侧边抽屉完备性**：侧边抽屉内不仅展示了完整文本，还联动了 `LevelTag`、`Cite` 与 `SourceBar`，做到了单元格内紧凑、抽屉内全量溯源。

## 签署状态

APP-M2-T005 保持 **in-review**，**严禁标 done**。
