# FE-SNIPPET-LIBRARY：知识库方案片段管理最小页交付归档

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-SNIPPET-LIBRARY |
| 代码解释 | [方案片段管理最小页实现说明](../code/FE-SNIPPET-LIBRARY.md) |
| 验收 | 1. 方案片段核心业务逻辑与安全隔离专属单测：`frontend/web/tests/unit/snippet-library-page.test.mjs`：9 passed；<br>2. 前端全量单测回归：`pnpm --dir frontend/web test`：357 passed（100% 保持绿色）；<br>3. TypeScript 编译与类型检查：`pnpm --dir frontend/web lint`：0 error；<br>4. 项目工程治理脚本检查：`node scripts/check-project-governance.cjs`：校验通过。 |
| 项目进度 | 本卡由 FE 成长前端 subagent 交付，状态标为 **in-review**（严禁自行标 done，等待主 Agent / PM / QA 验收审核）；闭环 PRD v1.8 P0-4 核心功能缺口。 |
<!-- task-delivery:end -->

## 1. 任务背景与目标

当前系统全局导航中 `nav === 'knowledge'`（知识库）长期处于 `PendingPage` 占位壳状态，用户无法查阅、检索与复用经过审核的方案片段，阻碍了投标编写人引用标准化业务技术方案并动态注入变量（PRD v1.8 §5.5，缺陷清单 P0-4）。

本任务目标：
1. 在 `frontend/web/src/library/` 域目录下，实现真实的方案片段列表与详情查看组件 `SnippetLibraryPage.tsx` 以及纯业务核心 `snippet-library-core.ts`；
2. 严守八域分层规范，严禁触碰 `backend/` 与 `FE-M0-T04～T10`；
3. 接通后端已有 `/api/v1/snippet-publications` 接口获取已发布片段；
4. 严格按照当前登录会话的 `company_id` 进行租户隔离展示，支持查看片段标题、分类/产品、套话组、版本与更新时间，点击可展开查看正文及变量；
5. 践行 **Layout First** 克制设计原则，无堆砌次级标签和说明书文字；
6. 完善空状态（无片段引导）与加载中状态；
7. 编写权威单测并保持前端测试 100% 绿色。

---

## 2. 完成内容与变更清单

| 文件路径 | 变更类型 | 说明 |
|---|---|---|
| `frontend/web/src/library/snippet-library-core.ts` | 新增 | 方案片段数据模型、标题推导算法、变量占位符提取（`{{var}}`）、租户公司隔离筛选、统计汇总与接口加载器 |
| `frontend/web/src/library/SnippetLibraryPage.tsx` | 新增 | 方案片段管理主页面组件，含指标卡、组合搜索过滤条、展开高亮正文表格与详情右侧抽屉 |
| `frontend/web/src/shared/types.ts` | 修改 | 扩展统一类型定义，导出 `SnippetSyncStatus` 与 `SnippetPublication` |
| `frontend/web/src/app/route-loaders.ts` | 修改 | 新增 `loadSnippetLibraryPage` 动态模块加载器 |
| `frontend/web/src/app/lazy-routes.tsx` | 修改 | 导出 `LazySnippetLibraryPage` 实现按需代码分割 |
| `frontend/web/src/app/App.tsx` | 修改 | 将 `nav === 'knowledge'` 的占位壳替换为真实的 `<SnippetLibraryPage />` 组件路由 |
| `frontend/web/tests/unit/snippet-library-page.test.mjs` | 新增 | 覆盖租户隔离门禁、多维筛选、变量提取、标题推导、空状态与状态映射的 9 项权威单测 |
| `docs/code/FE-SNIPPET-LIBRARY.md` | 新增 | 专属代码解释与数据流设计文档 |
| `docs/delivery/FE-SNIPPET-LIBRARY.md` | 新增 | 本交付归档文档 |
| `docs/TASK_BOARD.md` | 修改 | 登记本任务卡并推至 `in-review` |

---

## 3. 核心设计与验收依据

### 3.1 严格租户隔离（安全门禁）
在 `filterSnippets` 中实现了严格的双向租户隔离校验：
- Alpha 公司用户只能查阅 `company_id === 'alpha'` 的方案片段；
- Beta 公司用户只能查阅 `company_id === 'beta'` 的方案片段；
- 严防跨租户数据串扰与机密方案泄露。

### 3.2 变量提取与高亮排版
- 通过正则提取所有 `{{variable_name}}` 占位符；
- 正文通过 `renderHighlightedBody` 自动将变量以青底深青字 Tag 高亮展示，直观呈现变量位置，符合 Layout First 原则，无需用户翻看操作说明。

### 3.3 布局与交互流（Layout First）
- 顶部指标区仅展示已发布、已同步与变量数三个核心数字，无任何冗长教程段落；
- 过滤行支持关键词（跨标题、产品、套话组、来源组、正文与变量全字段检索）、分类下拉、同步状态下拉与“仅已发布”快速开关；
- 支持表格行内展开直接阅读正文，以及点击标题打开包含完整版本记录与变量列表的右侧抽屉。

---

## 4. 验证命令与结果

### 4.1 专属单元测试
运行命令：
```powershell
node --test frontend/web/tests/unit/snippet-library-page.test.mjs
```
测试结果：
- `SNIPPET_TYPE_MAP & getSnippetTypeLabel: 标准分类与友好回退`：通过
- `getSnippetSyncStatusMeta: 同步状态标签与徽标状态`：通过
- `resolveSnippetTitle: 智能推导方案片段标题`：通过
- `extractSnippetVariables: 从正文中准确提取与去重变量占位符`：通过
- `formatMonospaceTime: 格式化为等宽标准时间`：通过
- `filterSnippets: 租户公司隔离红线验证 (严格杜绝跨租户数据可见)`：通过
- `filterSnippets: 关键字、分类、同步状态与仅已发布门禁`：通过
- `computeSnippetStats: 准确计算租户内的片段统计指标`：通过
- `loadSnippetPublications: 函数接口完整且可调用`：通过
- **全部 9 项测试通过**。

### 4.2 前端权威全量测试
运行命令：
```powershell
pnpm --dir frontend/web test
```
测试结果：
```text
ℹ tests 357
ℹ suites 0
ℹ pass 357
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 5953.0344
```
**全量 357 项单测 100% 保持绿色通过。**

### 4.3 前端 TypeScript 编译检查
运行命令：
```powershell
pnpm --dir frontend/web lint
```
测试结果：
`tsc -b --noEmit` 0 警告、0 错误退出。

### 4.4 工程治理一致性检查
运行命令：
```powershell
node scripts/check-project-governance.cjs
```
测试结果：
`治理检查通过：501 份 Markdown、405 项任务、38 项 Issue。`

---

## 5. 项目进度与同步记录

- 任务看板：在 `docs/TASK_BOARD.md` 登记 `FE-SNIPPET-LIBRARY` 任务卡，状态推至 `in-review`。
- PRD 缺口对照：闭环 PRD v1.8 §5.5 中关于方案片段管理最小页（P0-4）的前端主要实现。
- 后续建议：待 PM / QA 审查并在完成验收后合并更新；后续可继续推进 `FE-WRITING-ARCHIVE` 写作档案产品页以彻底消除占位壳。
