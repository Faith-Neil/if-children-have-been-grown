# FE-WRITING-ARCHIVE 代码解释：写作档案与风格规范最小页

## 1. 为什么有这个文件

解决当前系统导航中 `nav === 'writing'` 仍为 `PendingPage` 占位壳的问题，彻底消灭全局导航中的最后一个空壳（PRD v1.8 §5.6 写作档案）。
通过在 `frontend/web/src/library/` 域目录下实现 `WritingArchivePage.tsx` 与业务核心 `writing-archive-core.ts`，为各公司提供统一的自称规范、语气偏好、禁用词库管理、国家公文标书排版格式准则以及标杆样章参考。

## 2. 架构设计与目录划分

严格遵循八域架构规范与克制设计原则：
- **纯函数逻辑层**：`frontend/web/src/library/writing-archive-core.ts`
  - 职责：
    1. 租户强隔离：根据登录会话 `company_id` 获取对应的公司专属写作档案，隔离 Alpha 与 Beta 的自称口径与样章；
    2. 禁用词库过滤算法：支持按类别（夸大绝对词、采购人口吻、行业套话）、严重度（阻断、警告、建议）与关键词搜索；
    3. 标杆样章库过滤算法：支持按分册（技术/商务）、评分维度与关键词检索；
    4. 草稿段落合规扫描诊断纯函数（`scanDraftText`）：实时检查自称是否错用（如“我行”、“我局”）、是否命中禁用词及严重度统计；
    5. 标准排版准则（全角标点、半角西文/数字、法定度量单位、公文层级编号）。
- **界面交互层**：`frontend/web/src/library/WritingArchivePage.tsx`
  - 职责：
    1. **Layout First** 克制设计：三栏紧凑 Tabs（风格与排版规范、禁用词库与合规扫描、典型标杆样章库）；
    2. 顶部指标栏：实时统计当前公司的禁用词条数、排版规范项数与样章数；
    3. 交互式草稿诊断工具：支持投标编写人在界面直接粘贴草稿段落，一键秒级诊断自称口径与合规风险；
    4. 样章详情抽屉：支持展开完整查阅标杆章节全文。
- **路由按需加载**：
  - `frontend/web/src/app/route-loaders.ts`：导出 `loadWritingArchivePage`；
  - `frontend/web/src/app/lazy-routes.tsx`：导出 `LazyWritingArchivePage`；
  - `frontend/web/src/app/App.tsx`：将 `nav === 'writing'` 占位壳替换为 `<WritingArchivePage user={user} session={applicationSession} />`。
- **共享数据模型**：`frontend/web/src/shared/types.ts`
  - 导出 `CompanyWritingProfile`、`ForbiddenWord`、`TypographyRule`、`QualitySample` 等类型。
- **权威测试收敛**：`frontend/web/tests/unit/writing-archive-page.test.mjs`
  - 8 项单测覆盖租户隔离红线、类别与严重度映射、自称错用检测、禁用词多维检索与排版规范清单完整性。

---

## 3. 核心业务规则与实现

### 3.1 租户公司强隔离
- `getWritingProfile(companyId)`：
  - Alpha 公司：自称为“本投标人”，招标人称谓为“招标人”，专属应急监测与数据中台样章；
  - Beta 公司：自称为“我方”，招标人称谓为“业主单位”，专属机电深化与钢结构施工样章；
  - 跨租户绝对无法读取彼此的自称设定与优质范本。

### 3.2 自称口径审查（PRD R35 规则）
- 依据编写规范，投标人不得在正文中使用采购人口吻的自称（如“我行”、“我局”、“我院”、“我校”）；
- `scanDraftText` 自动提取段落中与 `profile.self_reference` 矛盾的口吻并高亮报警。

### 3.3 禁用词库与 R43 AI 腔调审查
- 夸大词（业界第一、绝对保证、零缺陷）直接赋予 `blocker` 级别；
- 采购人口吻误用（我行、我局）直接赋予 `blocker` 级别；
- 空泛套话（全方位无死角、保姆式、颠覆性）赋予 `warning` 或 `suggestion`；
- 每条禁用词均配有法治审查依据与推荐合规替代词。

### 3.4 标杆样章（Few-Shot 引导）
- 提供经过评审的标杆范本，标注分册类型、评分维度、字数体量与正文；
- 供后续章节循环生成与人工编写时对齐高分范例文风。
