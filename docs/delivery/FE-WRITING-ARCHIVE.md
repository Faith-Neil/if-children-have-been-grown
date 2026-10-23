# FE-WRITING-ARCHIVE：写作档案与风格规范最小页交付归档

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-WRITING-ARCHIVE |
| 代码解释 | [写作档案与风格规范最小页实现说明](../code/FE-WRITING-ARCHIVE.md) |
| 验收 | 1. 写作档案核心业务逻辑与租户隔离专属单测：`frontend/web/tests/unit/writing-archive-page.test.mjs`：8 passed；<br>2. 前端全量单测回归：`pnpm --dir frontend/web test`：365 passed（100% 保持绿色）；<br>3. TypeScript 编译与类型检查：`pnpm --dir frontend/web lint`：0 error；<br>4. 项目工程治理脚本检查：`node scripts/check-project-governance.cjs`：校验通过。 |
| 项目进度 | 本卡由 FE 成长前端 subagent 交付，状态标为 **in-review**（严禁自行标 done，等待主 Agent / PM / QA 验收审核）；彻底消灭全局前端导航中的最后一个占位壳。 |
<!-- task-delivery:end -->

## 1. 任务背景与目标

此前前端全局导航中 `nav === 'writing'`（写作档案）仍停留在 `PendingPage` 占位壳状态，投标编写人无法查阅公司写作风格设定、自称规范、合规禁用词及标杆样章（PRD v1.8 §5.6）。

本任务目标：
1. 在 `frontend/web/src/library/` 域目录下实现真实的写作档案展示组件 `WritingArchivePage.tsx` 与纯业务逻辑模块 `writing-archive-core.ts`；
2. 严守八域分层规范，严禁触碰 `backend/` 与 `FE-M0-T04～T10`；
3. 支持展示公司专属写作档案：语气偏好、禁用词库（按严重级别与类别区分）、国家公文排版规范、标杆样章查阅；
4. 严格按照当前登录会话的 `company_id` 进行租户强隔离；
5. 践行 **Layout First** 克制设计原则，提供紧凑自解释的 Tabs 布局与交互式草稿快速合规诊断小工具；
6. 在 `App.tsx` 中接通路由，彻底消灭前端全局导航中的最后一个占位壳；
7. 编写权威单测并保持前端测试 100% 绿色。

---

## 2. 完成内容与变更清单

| 文件路径 | 变更类型 | 说明 |
|---|---|---|
| `frontend/web/src/library/writing-archive-core.ts` | 新增 | 写作档案业务核心，包含租户强隔离配置、禁用词与样章多维过滤、草稿合规扫描诊断算法与公文排版规范 |
| `frontend/web/src/library/WritingArchivePage.tsx` | 新增 | 写作档案主页面组件，含指标卡、三栏紧凑 Tabs、交互式草稿诊断、禁用词检索表与标杆样章查阅抽屉 |
| `frontend/web/src/shared/types.ts` | 修改 | 扩展统一类型定义，导出 `CompanyWritingProfile`、`ForbiddenWord`、`TypographyRule`、`QualitySample` |
| `frontend/web/src/app/route-loaders.ts` | 修改 | 新增 `loadWritingArchivePage` 动态模块加载器 |
| `frontend/web/src/app/lazy-routes.tsx` | 修改 | 导出 `LazyWritingArchivePage` 实现按需代码分割 |
| `frontend/web/src/app/App.tsx` | 修改 | 将 `nav === 'writing'` 接通至 `<WritingArchivePage />`，消灭最后占位壳 |
| `frontend/web/tests/unit/writing-archive-page.test.mjs` | 新增 | 覆盖租户隔离红线、类别严重度映射、自称错用检测、禁用词检索与排版规范完整性的 8 项权威单测 |
| `docs/code/FE-WRITING-ARCHIVE.md` | 新增 | 专属代码解释与数据流设计文档 |
| `docs/delivery/FE-WRITING-ARCHIVE.md` | 新增 | 本交付归档文档 |
| `docs/TASK_BOARD.md` | 修改 | 登记本任务卡并推至 `in-review` |
| `docs/DOCUMENT_INDEX.md` | 修改 | 登记 D-713 与 D-714 |

---

## 3. 核心设计与验收依据

### 3.1 租户强隔离与自称口径（R35）
- Alpha 公司自称设定为“本投标人”，招标人称谓为“招标人”，搭配专属应急监测高可用技术样章；
- Beta 公司自称设定为“我方”，招标人称谓为“业主单位”，搭配专属机电施工工法样章；
- 租户配置彼此隔离，杜绝跨租户串扰。

### 3.2 禁用词库与合规审查（R43）
- 细分“夸大与绝对化词”、“采购人口吻误用”、“空泛行业套话”三类；
- 标定 `blocker`（强阻断）、`warning`（警告）与 `suggestion`（建议）三级严重度；
- 明确推荐合规替代词与审查依据。

### 3.3 交互式草稿段落合规诊断
- 编写人可直接在界面粘贴正文草稿并点击“合规检测”；
- 纯前端算法（`scanDraftText`）秒级排查自称错用与禁用词命中，直观提示改写建议，落实 Layout First 原则。

---

## 4. 验证命令与结果

### 4.1 专属单元测试
运行命令：
```powershell
node --test frontend/web/tests/unit/writing-archive-page.test.mjs
```
测试结果：
- `FORBIDDEN_CATEGORY_MAP & getForbiddenCategoryLabel: 类别标签与友好回退`：通过
- `getSeverityMeta: 违规严重度级别映射`：通过
- `getVolumeLabel: 分册友好名称映射`：通过
- `getWritingProfile: 租户公司强隔离验证 (Alpha 与 Beta 独立配置)`：通过
- `filterForbiddenWords: 类别、严重度与多维搜索过滤`：通过
- `filterQualitySamples: 分册、评分维度与关键字检索`：通过
- `scanDraftText: 准确定位禁用词与自称口径错用`：通过
- `DEFAULT_TYPOGRAPHY_RULES: 包含国家公文与标书排版核心规范`：通过
- **全部 8 项测试通过**。

### 4.2 前端权威全量测试
运行命令：
```powershell
pnpm --dir frontend/web test
```
测试结果：
```text
ℹ tests 365
ℹ suites 0
ℹ pass 365
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 4879.4447
```
**全量 365 项单测 100% 保持绿色通过。**

### 4.3 前端 TypeScript 编译检查
运行命令：
```powershell
pnpm --dir frontend/web lint
```
测试结果：
`tsc -b --noEmit` 0 警告、0 错误退出。

---

## 5. 项目进度与同步记录

- 任务看板：在 `docs/TASK_BOARD.md` 登记 `FE-WRITING-ARCHIVE` 任务卡，状态推至 `in-review`。
- PRD 缺口闭环：PRD v1.8 §5.6 公司写作档案（含 P0 缺口）前端主要功能已全面落地。
- 全局导航状态：`workbench`、`library`、`knowledge`、`writing`、`admin.rules`、`jobs` 均已接通真实业务页面，系统导航占位壳彻底清零。
