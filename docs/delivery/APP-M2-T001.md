为什么有这个文件：交付共同页面底座第一阶段的代码、证据及完整剩余范围。

它解决什么问题：防止一个会话接口或菜单通过就被当成整个布局、路由和权限底座完成。

# APP-M2-T001阶段交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T001 |
| 代码解释 | [会话、布局与离开保护](../code/APP-M2-T001.md) |
| 验收 | QA 于 200a105 签署不通过。D1–D4 与 D6 已再交。E2E-D7 展开按钮已移出 logo，仍 in-review，项目经理尚未标 done。[浏览器复核](../testing/2026-10-12-t001-layout-history.md)。阶段一[262后台、72前端、16真实会话及GUI](../testing/2026-10-11-application-session.md)仍是历史证据 |
| 项目进度 | 本卡 in-review。看板 363 项：26 done、9 in-review、7 in-progress、268 planned、49 blocked、4 ready。APP-M2：T001 与 T002 in-review、T008 done、T124 blocked、其余 255 planned。本轮不改计数 |
<!-- task-delivery:end -->

日期2026-10-11，布局补充2026-10-12；ISSUE-009 / ISSUE-014；分支codex/repository-foundation；[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)为草稿待合入，未发布。此文提交复核，不把任务或 Issue 标成 done/closed。

## 已实现的阶段内容

真实getSession读取当前账号、公司范围、导航/动作和最小项目/章节权限；页面先核对会话再读取获准数据。三种演示角色明确兼容映射，manager未映射company_admin，也没有admin公司管理入口；旧资料/模板粗写权限仍保留，完整负责人/审核/字段范围未完成。未知或无权入口拒绝。公司资料/模板继续绑定对应读取的内容和版本；保存和导出仍经过同一后台授权。

新增后台session_navigation.py、前端session-navigation.ts及专项测试；改main.py、schemas.py、App.tsx、types.ts，导出实际OpenAPI。实际入口、调用顺序和限制见代码解释。独立审查发现的工作区撤权、迟到读取和页签竞态均已补修并复核；最终GUI还纠正了无权页提示，保留原内容与文字。

## 验收与当前进度

全后台262项通过，含33专项；前端72项、独立复核、最终类型/构建通过。真实会话16项和GUI经理/只读导航、快捷403、同后台项目与两册内部稿页面通过，4张截图登记。真实两册文件包和正文检查通过且不含个人未提交稿；Word页面版式未验收。网络/角色降级竞态仅函数回归及实际调用复核，没有在GUI注入，不由初次66项通过替代最终证据。

阶段一写到此处时，ProLayout、页面地址和全页离开保护尚未开始。2026-10-12 已把这三项提交 in-review，见下一节。OIDC 仍按 T010 另验。完整资料列表/详情仍依赖元数据表格、表单及敏感展示任务，不计 ready。原任务及 ICG 功能未缩减。

## 文档同步

| 文档 | 本阶段处理 |
|---|---|
| PRD | 原角色矩阵及完整页面目标保留，演示兼容边界明确 |
| ROADMAP | 先完整T001，再按资料库真实前置推进 |
| ARCHITECTURE / OpenAPI | 可信会话契约与实际49路径57操作 |
| Issue / TASK_BOARD | 新009和T001进行中，007完整产品继续，尚无整卡关闭 |
| PROJECT_STATUS / BRIEF | 同一产品协同、阶段结果与未完成范围分列 |
| DOCUMENT_INDEX | 登记契约、实际模块/专项和阶段交付 |
| WORKFLOW | 无治理规则变更，保持g1.1 / ISSUE-007治理块一致 |

人工Git操作前自动同步已停止；后续正常提交/推送与恢复以真实Git及工作区外运行状态核对，不重置或强推。原ICG材料保持原文，合同原件、凭据、运行输出及合成下载不提交。

## 布局、路由与离开保护（in-review）

直接依赖只增加 `@ant-design/pro-layout@7.22.7`。设计规范写 `@ant-design/pro-components`；该包会再带上 ProTable、ProForm，所以改用它所依赖的同一版 ProLayout。没有加入 react-router。引入前 `pnpm build` 为 `index-BqghTeOl.js` 1334.42 kB / gzip 409.62 kB；引入后为 `index-BmV8EgUZ.js` 1564.53 kB / gzip 486.19 kB。CSS 从 20.77 kB / gzip 5.00 kB 变为 21.02 kB / gzip 5.04 kB。

`AppShell.tsx` 放侧栏和顶栏。`app-route.ts` 解析 `/workbench` 等全局路径和 `/projects/:projectId/:tab`。`leave-guard.ts` 决定未保存时是否离开。`App.tsx` 用 History API 写地址，并用确认框挡住站内切换和浏览器后退；取消时地址留在原页。刷新和关闭由 `beforeunload` 拦截。编辑台内部的换章确认仍在 `EditorPage.tsx`。后台对非接口路径返回 `dist/index.html`，未知 `/api` 仍是 JSON。

2026-10-12 在 Node v24.21.0、pnpm 11.25.0 上，`node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` 为 77 pass、0 fail。Python 3.12.3 上 `python3 -m pytest tests/backend -q` 为 293 passed、1 warning。没有做三断点浏览器截图。T002、T007、T009、T010 和八角色迁移未做。PR #3 未合入，未发布。

| 文档 | 本轮处理 |
|---|---|
| PRD / ROADMAP / ARCHITECTURE / PROJECT_BRIEF | 正文未改。句子和原因见 [ISSUE-009](../../issues/ISSUE-009.md) 同步表 |
| 会话契约 | 补上实际首页和深链接，仍标明 in-review |
| Issue / TASK_BOARD | ISSUE-009、ISSUE-014、T001 均为 in-review |
| PROJECT_STATUS | 改为 in-review，不写 done |
| DOCUMENT_INDEX | 登记 ISSUE-014、本轮验证、同步表和新前端模块 |

ISSUE-020 在同一张任务上补了路由分包，首屏主块降到 315.94 kB。该 Issue 单独为 in-review，不把本卡标 done。见[分包交付](ISSUE-020.md)。

## QA 退回后的布局与历史修复（仍 in-review）

QA 在 `200a105` 签署本切片不通过，见[签署记录](../testing/2026-10-12-e2e-t001-signoff.md)。本轮只改前端外壳和浏览器历史，不改后台。

- D3：`navTheme` 从 `realDark` 改为 `light`。内容区卡片不再使用 `#141414`，正文保持深色字，页面底为 `#F5F7FA`。
- D4：桌面端 `layout="side"` 不渲染顶栏，公司、用户和退出被放进 64px 侧栏。现改为 `layout="mix"`，并用样式把深色侧栏拉满高度，白顶栏留在内容列。退出按钮回到页面顶部。
- D1 / D2：取消前进不再 `pushState`。每条应用历史带 `{ app: true, idx }`。未保存的前进或后退先按序号差 `history.go` 回到原页，确认后再按同一序号差走回去。取消不截断前进记录。
- D6：演示会话只在内存。刷新会丢掉登录态，必须重新登录；登录后 `routeAfterLogin` 回到刷新前的地址。确认刷新后，尚未保存的文字会丢失，这是预期。已保存的草稿仍可在重新登录后从后台读回。D5（`/API/...` 返回页面壳）是后台行为，本轮不改。

2026-10-12 在 Node v24.21.0、pnpm 11.25.0、Playwright 1.64.0 上，`pnpm --dir frontend/web e2e` 为 11 passed。前端函数测试 78 pass、0 fail。代表截图：[工作台 1680](../testing/assets/t001-fixed-workbench-1680.png)、[编辑台 1280](../testing/assets/t001-fixed-editor-1280.png)、[概览 1440](../testing/assets/t001-fixed-overview-1440.png)。QA 的失败截图未覆盖。PR #3 未合入，未发布，本卡不标 done。

## E2E-D7：展开按钮不再被 logo 挡住（仍 in-review）

QA 重签记录 [T001 重签](../testing/2026-10-12-qa-t001-t002-t020-recheck.md) 新增 E2E-D7：侧栏默认收起，顶栏「收起或展开导航」被收起侧栏的 logo 挡住，三宽度和两种主题都点不到。本轮不改默认收起。顶栏起始位置让出侧栏宽度，按钮出现在 logo 右侧。端到端新增：点击后菜单文字可见。证据写在 [布局与历史修复](../testing/2026-10-12-t001-layout-history.md)。T001 仍 in-review，不标 done。D5 仍不改。

## E2E-D8：次要文字至少 4.5:1（仍 in-review）

同一份重签把概览步骤号、「○」和编辑台元信息记为 2.68:1 到 2.91:1。次要文字改为 `#4e5969`，待办圆圈和橙色正文改为 `#9a5608`。端到端读取计算对比度，13 项通过。仍 in-review，不标 done。
