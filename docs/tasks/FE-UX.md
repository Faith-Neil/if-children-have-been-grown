为什么有这个文件：登记 ISSUE-057 前端体验、视觉与响应式收口任务卡。

它解决什么问题：把主链路体验修复、设计 Token、响应式重构和 Playwright 巡检拆成可验收任务，避免只做视觉表面改动。

# FE-UX：前端体验视觉响应式收口

<a id="fe-ux-mainflow-copy"></a>

## FE-UX-MAINFLOW-COPY · 主链路体验修复与大白话转译

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 5小时 |
| 关联 Issue | [ISSUE-057](../../issues/ISSUE-057.md) |
| 依赖 | PR #52 项目列表服务端排序筛选；PR #53 后台权限收口 |
| 完成时交付 | `docs/delivery/FE-UX-MAINFLOW-COPY.md` |
| 代码解释 | `docs/code/FE-UX-MAINFLOW-COPY.md` |

范围：编辑台加载骨架与真实 SSE 撰写状态解耦；项目列表服务端排序/搜索/状态筛选；状态码、409、digest_id、failure_reason 白话映射；门禁拦截补定位或修复入口。

验收：仅真实活跃撰写任务显示“AI 正在撰写”；列表参数进请求；用户界面不见原始技术码。

<a id="fe-ux-visual-tokens"></a>

## FE-UX-VISUAL-TOKENS · 统一视觉 Token 与轻量动效

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-057](../../issues/ISSUE-057.md) |
| 依赖 | FE-UX-MAINFLOW-COPY 可并行 |
| 完成时交付 | `docs/delivery/FE-UX-VISUAL-TOKENS.md` |
| 代码解释 | `docs/code/FE-UX-VISUAL-TOKENS.md` |

范围：CSS 变量与 Antd theme Token；12/8/6px 圆角体系；浅灰画布、白色卡片、细腻边框和柔和阴影；150～240ms 微动效与 `prefers-reduced-motion`。

验收：主要卡片/按钮/输入/标签呈现统一圆角层次；无 Antd v5 告警；减少散落硬编码。

<a id="fe-ux-responsive-layout"></a>

## FE-UX-RESPONSIVE-LAYOUT · 多分辨率布局错位重构

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 6小时 |
| 关联 Issue | [ISSUE-057](../../issues/ISSUE-057.md) |
| 依赖 | FE-UX-VISUAL-TOKENS |
| 完成时交付 | `docs/delivery/FE-UX-RESPONSIVE-LAYOUT.md` |
| 代码解释 | `docs/code/FE-UX-RESPONSIVE-LAYOUT.md` |

范围：项目列表统计卡片断点和抽屉响应宽度；编辑台三栏窄屏折叠/抽屉化与弹层宽度上限；覆盖视图表格列宽、省略和横向滚动；知识库与后台工具栏/表格自适应。

验收：1280×720 与 960×720 无中栏挤压、横向溢出或工具栏撑爆。

<a id="fe-ux-playwright-viewports"></a>

## FE-UX-PLAYWRIGHT-VIEWPORTS · 四视口 Playwright 巡检与截图自修

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-057](../../issues/ISSUE-057.md) |
| 依赖 | 前三张卡完成初版 |
| 完成时交付 | `docs/delivery/FE-UX-PLAYWRIGHT-VIEWPORTS.md` |
| 代码解释 | `docs/code/FE-UX-PLAYWRIGHT-VIEWPORTS.md` |

范围：headless Chromium 覆盖工作台、项目覆盖视图、编辑台、知识库、平台/公司后台；1920×1080、1440×900、1280×720、960×720；横向溢出、交互元素遮挡、Console 错误和 Antd deprecation 检测；截图自审迭代。

验收：四视口程序化检测全部通过，关键截图留档并在 PR 描述引用。
