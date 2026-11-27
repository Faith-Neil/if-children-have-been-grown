为什么有这个文件：登记前端主链路体验修复、现代视觉动效升级与多分辨率响应式精修。

它解决什么问题：编辑台加载误显“正在撰写”、项目列表未利用服务端排序筛选、状态与失败原因暴露技术黑话，全站视觉层级、圆角阴影和窄屏布局不一致。

# ISSUE-057：前端主链路体验修复、现代视觉与动效升级、多分辨率响应式精修

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-057 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | closed |
| 登记日期 | 2026-11-27 |
| 最后更新日期 | 2026-11-27 |
| revision | frontend-ux-visual-responsive-r1 |
| 关联 Task | [FE-UX-MAINFLOW-COPY](../docs/tasks/FE-UX.md#fe-ux-mainflow-copy)、[FE-UX-VISUAL-TOKENS](../docs/tasks/FE-UX.md#fe-ux-visual-tokens)、[FE-UX-RESPONSIVE-LAYOUT](../docs/tasks/FE-UX.md#fe-ux-responsive-layout)、[FE-UX-PLAYWRIGHT-VIEWPORTS](../docs/tasks/FE-UX.md#fe-ux-playwright-viewports) |
| 关联 PR | [PR #54](https://github.com/Faith-Neil/if-children-have-been-grown/pull/54) 已合入 |
| 本地验收 | 通过：tsc、生产构建、四视口 Playwright 巡检与治理检查通过；全量前端单测的既有失败已在 PR 中如实记录 |
| 合入 | 已合入 main：e978638 |
| 发布 | 未发布 |
| 交付说明 | [FE-UX-MAINFLOW-COPY](../docs/delivery/FE-UX-MAINFLOW-COPY.md)、[FE-UX-VISUAL-TOKENS](../docs/delivery/FE-UX-VISUAL-TOKENS.md)、[FE-UX-RESPONSIVE-LAYOUT](../docs/delivery/FE-UX-RESPONSIVE-LAYOUT.md)、[FE-UX-PLAYWRIGHT-VIEWPORTS](../docs/delivery/FE-UX-PLAYWRIGHT-VIEWPORTS.md) |
| 代码 / 流程解释 | [FE-UX-MAINFLOW-COPY](../docs/code/FE-UX-MAINFLOW-COPY.md)、[FE-UX-VISUAL-TOKENS](../docs/code/FE-UX-VISUAL-TOKENS.md)、[FE-UX-RESPONSIVE-LAYOUT](../docs/code/FE-UX-RESPONSIVE-LAYOUT.md)、[FE-UX-PLAYWRIGHT-VIEWPORTS](../docs/code/FE-UX-PLAYWRIGHT-VIEWPORTS.md) |
| 验证记录 | [PR #54](https://github.com/Faith-Neil/if-children-have-been-grown/pull/54) 验收记录与四视口 Playwright 结果 |

## 现象与证据

用户要求基于 PR #52/#53 后的最新 main 实施五步前端体验收口：根治编辑台加载误显“正在撰写”；项目工作台接入服务端排序、关键词和状态筛选；清零状态码、digest_id、failure_reason 等技术黑话并补齐门禁修复入口；建立统一 Design Tokens、圆角、色彩层级、阴影和轻量动效；修复 1280/960 宽度下三栏、表格、抽屉和后台页面挤压；用 Playwright 在 1920×1080、1440×900、1280×720、960×720 四视口做几何与 Console 巡检并截图自修。

## 影响与分流

- 只改前端体验、视觉和测试巡检，不改变后端业务契约。
- 遵守 Antd v5 零告警、大白话业务文案、`prefers-reduced-motion` 与 Layout First 规范。
- Playwright 结果是本轮核心门禁；截图证据入库前不得宣称完成。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| [FE-UX-MAINFLOW-COPY](../docs/tasks/FE-UX.md#fe-ux-mainflow-copy) | 编辑台加载/撰写状态解耦、项目排序筛选、黑话转译与拦截引导 | `editor/`、`project/`、`shared/status-registry.ts` | 只有活跃 SSE 撰写显示 AI 撰写；列表服务端筛选可用；无原始码外露 | done |
| [FE-UX-VISUAL-TOKENS](../docs/tasks/FE-UX.md#fe-ux-visual-tokens) | 圆角、色彩、阴影、动效 Token 收口 | `shared/styles.css`、`main.tsx`、shell/admin/project/editor | Token 统一，减少硬编码，兼容 reduced-motion | done |
| [FE-UX-RESPONSIVE-LAYOUT](../docs/tasks/FE-UX.md#fe-ux-responsive-layout) | 核心页面 1280/960 响应式精修 | 工作台、编辑台、覆盖视图、知识库、后台 | 无横向溢出，表格和抽屉不撑爆 | done |
| [FE-UX-PLAYWRIGHT-VIEWPORTS](../docs/tasks/FE-UX.md#fe-ux-playwright-viewports) | 四视口几何巡检、Console 零错误、截图自审 | `frontend/web/tests/`、临时截图证据 | 四视口全部通过并留存截图 | done |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 首次加载/切换章节显示骨架或加载文案；仅真实活跃 SSE 撰写任务显示“AI 正在撰写” | 通过；PR #54 已解耦加载与 SSE 撰写态 |
| AC-02 | 项目列表默认最近使用倒序，支持排序、关键词、状态筛选并走后端参数 | 通过；PR #54 已接入服务端参数 |
| AC-03 | 409、OCC、digest_id、filtered_empty、rule_fallback 等不再直接外露，拦截有修复入口 | 通过；PR #54 已完成大白话转译与引导 |
| AC-04 | 统一圆角/色彩/阴影/动效 Token，Antd v5 无 deprecation 告警 | 通过；PR #54 巡检无 Antd deprecation 告警 |
| AC-05 | 四视口无意外横向溢出、无交互元素遮挡、Console 零报错；截图自审通过 | 通过；Playwright 复跑 1 passed（31.0s），无 409 豁免 |
| AC-06 | tsc、build、前端单测、Playwright 巡检、治理检查通过；PR 不合并 | 用户已验收并合入 PR #54；tsc/build/巡检/治理通过，全量前端单测既有失败已在 PR 中如实记录 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响：不改变产品范围与业务规则，只修正既有前端体验 | `docs/PRD.md` | frontend-ux-visual-responsive-r1 / ISSUE-057 / 2026-11-27 | 已核对 |
| ROADMAP | 无影响：不改变里程碑顺序，只完成当前体验收口 | `docs/ROADMAP.md` | 同上 | 已核对 |
| ARCHITECTURE | 无影响：不新增接口或模块边界，仅前端样式、布局与巡检实现 | `docs/ARCHITECTURE.md` | 同上 | 已核对 |
| TASK_BOARD | 有影响：四张 FE-UX 卡终态为 done | `docs/TASK_BOARD.md` | 同上 | 已同步 |
| PROJECT_STATUS | 有影响：记录 ISSUE-057 closed 与 PR #54 合入 | `docs/PROJECT_STATUS.md` | 同上 | 已同步 |
| DOCUMENT_INDEX | 有影响：更新 Issue、任务卡、交付与代码说明状态 | `docs/DOCUMENT_INDEX.md` | 同上 | 已同步 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-11-27 | frontend-ux-visual-responsive-r1 / in-progress | 已基于最新 main 切出 `feat/iss-057-frontend-ux-visual-responsive` 并登记任务 | 用户指令 |
| 2026-11-27 | frontend-ux-visual-responsive-r1 / closed | PR #54 已合入 main（e978638）；用户指示本轮进行终态收口，四张任务卡标 done，Issue 标 closed；未发布 | 用户验收与 PR #54 |

## 本地验收与后续合入发布

- 本地验收结论与日期：2026-11-27 通过，证据见 PR #54；全量前端单测的既有失败没有冒充通过。
- 验证方式、通过及失败项、未覆盖范围：tsc、生产构建、Playwright 四视口巡检、治理检查；截图 artifacts 留在本机 Playwright 输出目录，不入库。
- 六份基线同步与互链复核：已同步。
- PR 状态：[PR #54](https://github.com/Faith-Neil/if-children-have-been-grown/pull/54) 已合入。
- 合入提交与日期：e978638，2026-11-27。
- 发布版本与日期：未发布。
