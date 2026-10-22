为什么有这个文件：交付元数据驱动表格组件（MetadataTable / ProTableWrapper）的封装实现、单元测试与构建验证结果。

它解决什么问题：实现字段元数据自动推导 Ant Design Table 的列配置、支持 rowSpan 动态行合并、在 1280px 标准桌面视口下落实“无横向滚动优先”原则，集成通用状态组件（StatusViews）与业务小组件（BusinessTags），并严格落地合规批量操作限制（星号/废标/资格禁止批量确认）与风险行高亮。

# APP-M2-T005：元数据驱动表格封装交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T005 |
| 代码解释 | [代码解释](../code/APP-M2-T005.md) |
| 验收 | 前端 155 项测试全部通过（含 14 项元数据表格专项测试）、`pnpm --dir frontend/web build` 成功通过且产物体积无膨胀（index 289.99 kB），1280px 宽度预算优先无横滚验证通过，合规批量门禁拦截通过；后端 `getFieldMetadata` 契约端点全量落地，`tests/backend/test_field_metadata.py` 6 项测试全绿，全量 457 项后端单测回归全绿 |
| 项目进度 | 标至 in-review。关联 ISSUE-007。依赖 BE-M0-T01（已 done）、APP-M2-T003（in-review）、APP-M2-T004（in-review）。下一表单任务：APP-M2-T006 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T005](../tasks/APP-M2.md#app-m2-t005)
- 前置依赖：[BE-M0-T01](../tasks/BE-M0.md#be-m0-t01)（done）、[APP-M2-T003](../tasks/APP-M2.md#app-m2-t003)（in-review）、[APP-M2-T004](../tasks/APP-M2.md#app-m2-t004)（in-review）
- 契约接口：`GET /api/v1/metadata/fields/{category}`（operationId: `getFieldMetadata`）
- 分支：`feat/opencode-ICG`
- 本地验收状态：本地前后端自动化测试与生产构建全部通过，已按流程标至 `in-review`，等待主 Agent、QA 与项目经理评审，严禁私自标 `done`
- 合入 / 发布状态：未合入生产分支，未发布

## 完成内容与变更文件

本次任务在 `frontend/web/` 下完成了元数据驱动表格组件的全面封装，覆盖设计规范 §9.1、§9.2、交接清单 M1-P08-F5 及任务要求的所有关键项：

1. **`frontend/web/src/library/metadata-table.ts`（新增）**：
   - 纯函数逻辑与类型层，定义 `FieldMeta`、`TableMeta`、`ColumnBudgetResult`、`BatchConfirmValidation`；
   - 实现了 `calculateColumnWidthBudget`：在 1280px 标准桌面视口（减去侧边栏与页边距后的安全内容可用宽 1040px）下计算列宽，长文本列自动弹性自适应并启用省略保护，保证首选无横向滚动条；当列宽显著超标时平滑降级开启滚动并锁定首列与操作列（规范 9.1 规则 2）；
   - 实现了 `calculateRowSpans`：对相邻同分组值的单元格计算 rowSpan 合并（首行计数 N，后续置 0）；
   - 实现了 `canBatchConfirm`：依据合规规范 §5.2.2 与设计规范 9.1 规则 6，严禁对星号条款（★）、废标/阻断条款、资格审查条款执行批量确认，必须逐项单独人工核对；
   - 实现了 `isRiskRow`（浅红底 `#FFF5F5`，`.row-danger`，规范 9.1 规则 4）与 `isUrgentRow`（3 天内截止项目急迫高亮）；
   - 实现了 `formatDateTimeMonospace`（等宽字体时间排版，规范 9.1 规则 3）；
   - 提供了 `REQUIREMENTS_MATRIX_SCHEMA`、`LIBRARY_RECORDS_SCHEMA`、`FACTS_MATRIX_SCHEMA` 内置 Schema 及异步 mock 解析函数。

2. **`frontend/web/src/library/MetadataTable.tsx`（新增）**：
   - 封装 Ant Design Table，导出 `MetadataTable` 与 `ProTableWrapper`；
   - 动态推导列配置，自动支持双行表头（`icg-two-line-header`，中文名 + 等宽系统键，规范 9.2 规则 2）；
   - 深度集成通用状态组件：加载无数据时渲染 5 行表格骨架屏（`SkeletonView`）、接口失败渲染带 traceId 复制的错误态（`ErrorView`）、无数据时自适应切换搜索或空列表空态（`EmptyState`）；
   - 深度集成业务小组件：单元格无缝渲染 `LevelTag`、`Cite`、`SourceBar`、`AiTag`、`DirectTag`；
   - 侧边抽屉详情查看（Detail Drawer）：长文本单元格提供“查看”按钮，在 560px 宽抽屉中展示完整原文、条款级别、引用证据与来源指纹，保障紧凑排版下信息零丢失；
   - 顶部工具栏（搜索输入、密度切换、刷新操作）与底部批量操作浮动栏（实时门禁校验与拦截警示）。

3. **`frontend/web/src/shared/styles.css`（修改）**：
   - 补充 `.icg-metadata-table-wrapper`、`.icg-table-toolbar`、`.icg-batch-bar`、`.icg-batch-warning`、`.icg-two-line-header`、`.icg-monospace-time`、`.row-danger > td` 与 `.row-urgent` 等样式类。

4. **`tests/frontend/metadata-table.test.mjs` 与 `frontend/web/tests/metadata-table.test.mjs`（新增）**：
   - 新增 14 项完整测试，覆盖行合并算法、1280px 宽度预算、合规批量门禁拦截、风险与急迫行判定、等宽时间格式化、Schema 兜底、AST 导出声明、StatusViews 与 BusinessTags 深度集成。

5. **`backend/bid-core/icg_demo/field_metadata.py`（新增）**：
   - 依据 `kb-data-dictionary v1.9` 构建四大分类字段元数据定义（`project`、`tender`、`kb_record`、`sla`）；
   - 定义 `FieldOption`、`FieldMetadataItem`、`FieldMetadataListResponse`；
   - 实现 `FieldMetadataService` 与 `resolve_category` 别名容错解析；
   - 暴露 `GET /api/v1/metadata/fields/{category}`，设置 `operationId="getFieldMetadata"`。

6. **`backend/bid-core/icg_demo/main.py`（修改）**：
   - 挂载 `include_field_metadata_routes`。

7. **`spec/openapi/demo-v1.json`（修改）**：
   - 同步 OpenAPI 契约端点与 Schema 定义。

8. **`tests/backend/test_field_metadata.py`（新增）**：
   - 6 项后端单测，覆盖 401 拦截、404 未知分类、四大核心分类读取与多角色权限验证。

## 代码解释

详细调用链、时序图、算法原理与异常分支处理参见 [APP-M2-T005 代码解释](../code/APP-M2-T005.md)。

## 验收结果

### 1. 后端自动化测试套件执行
在仓库根目录执行：
```bash
pytest tests/backend/test_field_metadata.py
```
执行输出：
```
collected 6 items
tests\backend\test_field_metadata.py ......                              [100%]
============================== 6 passed in 3.81s ==============================
```
后端全量回归验证：
```bash
pytest tests/backend
```
执行输出：
```
============================== warnings summary ===============================
========== 457 passed, 16 skipped, 32 warnings in 229.11s (0:03:49) ===========
```

### 2. 前端自动化测试套件执行
在仓库根目录执行：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
执行输出：
- 总测试数：155 项（新增 14 项测试：算法与纯函数 7 项，组件 AST 与结构 7 项）
- 结果：**155 pass, 0 fail, 0 skipped**，全量绿灯通过。

### 2. 前端生产构建验证
在仓库根目录执行：
```bash
pnpm --dir frontend/web build
```
执行输出：
```
$ tsc -b && vite build
✓ 3338 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                0.94 kB │ gzip:   0.57 kB
dist/assets/index-Dt2baKHo.css                26.70 kB │ gzip:   6.19 kB
dist/assets/index-D8Isnz1Z.js                289.99 kB │ gzip:  92.21 kB
✓ built in 1.13s
```
- TypeScript 类型检查：0 error。
- Bundle 体积：主入口 JS 体积稳定在 289.99 kB，无冗余第三方依赖引入，路由级代码分割完全保留。

### 3. 设计规范落地对照表

| 规范条目 | 规范要求 | 本单元落实情况 | 验证手段 |
|---|---|---|---|
| **9.1 表格 ①** | 一律 ProTable 规范，矩阵/合规/资料用 small，默认 middle | 默认取 schema.defaultSize 或 middle，工具栏支持动态切换 | 单测 + AST 验证 |
| **9.1 表格 ②** | 不出现横向滚动是首选，1280px 优先无横滚 | calculateColumnWidthBudget 在 1040px 内自动分配弹性宽度，长文本 ellipsis + 侧边抽屉 | `calculateColumnWidthBudget` 单测通过 |
| **9.1 表格 ③** | 列顺序与对齐：数值右对齐，时间等宽字体 | `dataType: 'number'` 自动 `align: 'right'`，时间格式化为等宽排版 | 单测 + 样式验证 |
| **9.1 表格 ④** | 风险行浅红底 `#FFF5F5`（`.row-danger`） | `isRiskRow` 判定阻断/负偏离/待核条目，自动注入 `.row-danger` 类名 | 单测 + CSS 规则 |
| **9.1 表格 ⑥** | 星号、废标、资格三类抽取条目不提供批量确认（§5.2.2） | `canBatchConfirm` 门禁检测，勾选包含不可批量项时禁用按钮并报警 | `canBatchConfirm` 单测通过 |
| **9.2 表单 ②** | 系统字段标签两行：中文名 + 等宽小字系统键 | `icg-two-line-header` 渲染 `label` 与 `secondaryLabel` | AST 验证 |
| **通用状态集成** | 加载骨架屏、空态与带 traceId 错误态 | 深度集成 `SkeletonView`（5 行）、`EmptyState`、`ErrorView`（一键复制 traceId） | AST 验证 |
| **业务小组件集成** | 单元格渲染业务标准小组件 | 自动将 `level`、`cite`、`source`、`ai`、`direct` 映射到专属组件 | AST 验证 |
