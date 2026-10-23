# FE-SNIPPET-LIBRARY 代码解释：知识库方案片段管理最小页

## 1. 为什么有这个文件

解决当前系统导航中 `nav === 'knowledge'` 仍为 `PendingPage` 占位壳、用户无法查看与使用方案片段的核心产品阻断（PRD v1.8 P0-4 缺口）。通过在前端 `frontend/web/src/library/` 域目录下实现真实的方案片段管理最小页 `SnippetLibraryPage.tsx` 与纯业务逻辑模块 `snippet-library-core.ts`，打通 `/api/v1/snippet-publications` 真实调用与租户严格隔离展示。

## 2. 架构设计与目录划分

严格遵循八域架构规范与克制设计原则：
- **纯函数逻辑层**：`frontend/web/src/library/snippet-library-core.ts`
  - 职责：数据模型契约、标题推导算法、变量标记提取（`{{variable_name}}`）、等宽时间格式化、多维组合筛选、公司租户隔离过滤、统计指标汇总与 API 异步加载。
- **界面与交互层**：`frontend/web/src/library/SnippetLibraryPage.tsx`
  - 职责：践行 **Layout First** 原则，依托自解释的表格与侧抽屉交互流，杜绝说明书式文字堆砌；提供指标概览、组合检索过滤、行内正文高亮展开（`renderHighlightedBody`）、右侧全量元数据与版本抽屉、空状态友好引导。
- **路由延迟加载与挂接**：
  - `frontend/web/src/app/route-loaders.ts`：导出 `loadSnippetLibraryPage` 异步动态导入。
  - `frontend/web/src/app/lazy-routes.tsx`：导出 `LazySnippetLibraryPage` 供 React Suspense 代码分割。
  - `frontend/web/src/app/App.tsx`：在全局导航挂载区将 `nav === 'knowledge'` 替换为 `<SnippetLibraryPage token={token} user={user} session={applicationSession} />`。
- **共享数据模型**：`frontend/web/src/shared/types.ts`
  - 导出 `SnippetSyncStatus` 与 `SnippetPublication` 标准类型。
- **权威测试收敛**：`frontend/web/tests/unit/snippet-library-page.test.mjs`
  - 唯一权威单测套件，覆盖租户隔离红线、多维过滤、变量提取、标题推导、空状态与状态映射。

---

## 3. 核心功能与调用流

### 3.1 租户公司隔离（安全防线）
- 服务端：`/api/v1/snippet-publications` 基于 Bearer Token 校验的主体进行公司过滤。
- 前端防线：`filterSnippets(items, params, activeCompanyId)` 在渲染端进行二次安全检验：
  ```ts
  if (activeCompanyId && item.company_id && item.company_id !== activeCompanyId) {
    return false;
  }
  ```
  确保即便开发或离线缓存包含其他租户数据，也绝对不会发生跨租户泄露。

### 3.2 方案片段展示与标题智能推导
片段服务端数据结构包含 `product`、`snippet_type`、`boilerplate_group`、`source_group`，但未设立冗余的独立标题字段。
`resolveSnippetTitle` 算法：
1. 优先采用自身的 `title`（若存在）；
2. 组合 `product · boilerplate_group`（如：“智慧应急监测系统 · 核心架构与冗余设计”）；
3. 组合 `product · getSnippetTypeLabel(snippet_type)`（如：“物联网数据中台 · 技术方案”）；
4. 回退为 `方案片段 #{id}`。

### 3.3 变量提取与高亮渲染 (`renderHighlightedBody`)
- 正文中形如 `{{variable_name}}` 的占位符通过正则 `/\{\{([A-Za-z0-9_.-]+)\}\}/g` 自动捕获。
- `renderHighlightedBody` 将普通文本与变量拆分，变量统一渲染为青底深青字的等宽轻量 Tag，与普通文本形成清晰视觉对比，一目了然提示编写人该处可在生成时动态注入。

### 3.4 知识库同步与版本状态
- `kb_sync_status`：
  - `synced`：已同步知识库（绿色 Badge）
  - `unsynced`：未同步知识库（金色 Badge）
  - `sync_failed`：同步失败（红色 Badge）
- 版本：
  - 已发布版本展示为 `v{published_revision}`；
  - 若处于草稿态则显示 `草稿 v{draft_revision}`；
  - 抽屉内若 `draft_body` 与 `published_body` 存在差异，提供清晰的未发布草稿对比区。

### 3.5 Layout First 克制设计
- 页面顶部：紧凑的标题与租户标识，右侧紧凑卡片展示指标（已发布片段数、已同步知识库数、声明变量总数），不写大段业务使用手册；
- 过滤行：输入框、分类选择、同步状态选择、仅已发布开关与刷新按钮在单行水平排列；
- 列表区：Ant Design 表格自适应宽度，支持点击标题或“查看正文”唤出抽屉，支持每行展开快速阅读高亮正文；
- 空状态：区分“无匹配搜索结果”（带有一键清空筛选按钮）与“企业知识库暂无片段”引导。

---

## 4. 关键接口与依赖

- 接口路径：`GET /api/v1/snippet-publications`（`loadSnippetPublications` 封装兼容 `/api/v1/snippet_publications` 降级回退）。
- 权限与路由：
  - 路由标号：`knowledge`（映射至 `/knowledge`）；
  - 平台管理员由 `PLATFORM_ADMIN_FORBIDDEN_ROUTES` 拦截；其余 7 个企业级角色（`project_lead`, `bid_writer`, `company_admin`, `data_admin`, `viewer`, `auditor`, `group_admin`）均被允许访问。
