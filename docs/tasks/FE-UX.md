为什么有这个文件：登记 ISSUE-057 前端体验、视觉与响应式收口任务卡。

它解决什么问题：把主链路体验修复、设计 Token、响应式重构和 Playwright 巡检拆成可验收任务，避免只做视觉表面改动。

# FE-UX：前端体验视觉响应式收口

<a id="fe-ux-mainflow-copy"></a>

## FE-UX-MAINFLOW-COPY · 主链路体验修复与大白话转译

| 字段 | 内容 |
|---|---|
| 状态 | done |
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
| 状态 | done |
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
| 状态 | done |
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
| 状态 | done |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-057](../../issues/ISSUE-057.md) |
| 依赖 | 前三张卡完成初版 |
| 完成时交付 | `docs/delivery/FE-UX-PLAYWRIGHT-VIEWPORTS.md` |
| 代码解释 | `docs/code/FE-UX-PLAYWRIGHT-VIEWPORTS.md` |

范围：headless Chromium 覆盖工作台、项目覆盖视图、编辑台、知识库、平台/公司后台；1920×1080、1440×900、1280×720、960×720；横向溢出、交互元素遮挡、Console 错误和 Antd deprecation 检测；截图自审迭代。

验收：四视口程序化检测全部通过，关键截图留档并在 PR 描述引用。

<a id="fe-ux-streaming-render"></a>

## FE-UX-STREAMING-RENDER · 流式阶段胶囊与专属渲染画布

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-058](../../issues/ISSUE-058.md) |
| 依赖 | ISSUE-057 已合入 main |
| 完成时交付 | `docs/delivery/FE-UX-STREAMING-RENDER.md` |
| 代码解释 | `docs/code/FE-UX-STREAMING-RENDER.md` |

范围：移除 `.paper-wait` 不透明遮罩；等待首字显示 AI 阶段呼吸胶囊与 shimmer 骨架；首字后切换 `StreamingPaperView`，与 TipTap 共用纸面排版；实现稳定 key 的柔和渐显 chunk 与呼吸光标。

验收：`retrieve` / `deviate` / `write_section` 文案正确；无遮罩盖字；旧片段不重挂载；兼容 `prefers-reduced-motion`。

<a id="fe-ux-streaming-markdown"></a>

## FE-UX-STREAMING-MARKDOWN · 流式安全 Markdown 中间态

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 3小时 |
| 关联 Issue | [ISSUE-058](../../issues/ISSUE-058.md) |
| 依赖 | FE-UX-STREAMING-RENDER |
| 完成时交付 | `docs/delivery/FE-UX-STREAMING-MARKDOWN.md` |
| 代码解释 | `docs/code/FE-UX-STREAMING-MARKDOWN.md` |

范围：新增 `frontend/web/src/editor/streaming-markdown.ts` 纯函数，处理尾部未闭合 `**`、`<u>`、孤立 `#` 与未成型表格；未成型表格以柔和微光占位过渡。

验收：未闭合加粗/下划线不裸露原始符号；表格分隔行到达前不整块跳动；孤立 `#` 暂缓渲染；单元测试覆盖中间态与正式态。

<a id="fe-ux-streaming-handoff"></a>

## FE-UX-STREAMING-HANDOFF · 智能跟随滚动与完成无缝交接

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-058](../../issues/ISSUE-058.md) |
| 依赖 | FE-UX-STREAMING-RENDER、FE-UX-STREAMING-MARKDOWN |
| 完成时交付 | `docs/delivery/FE-UX-STREAMING-HANDOFF.md` |
| 代码解释 | `docs/code/FE-UX-STREAMING-HANDOFF.md` |

范围：保留 24px 自动光标跟随与用户上翻不拉回；离开底部显示半透明“定位到正在撰写”；`volume.done` 且 reveal settled 后静默写入 TipTap 并恢复 scrollTop；取消/失败回滚过渡清晰。

验收：长文滚动不强行拉回；点击定位到正在撰写平滑回底；完成后无白屏闪烁、整页回弹或 scrollTop 跳动；取消/失败正文回滚且提示明确。

<a id="fe-ux-streaming-verification"></a>

## FE-UX-STREAMING-VERIFICATION · 流式单元测试与 Playwright SSE 验收

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-058](../../issues/ISSUE-058.md) |
| 依赖 | 前三张流式体验卡完成初版 |
| 完成时交付 | `docs/delivery/FE-UX-STREAMING-VERIFICATION.md` |
| 代码解释 | `docs/code/FE-UX-STREAMING-VERIFICATION.md` |

范围：补齐 streaming-markdown、chunk key、text-reveal 速率与阶段映射单测；新增 Playwright SSE 模拟流验证普通段落、加粗、表格、长文滚动、完成收口、取消/失败提示。

验收：前端权威测试、TypeScript、生产构建、Playwright 流式场景与治理检查按实际结果记录；不伪造真机模型验收。
