为什么有这个文件：登记项目经理指定的路由级代码分包，并留下首屏体积。

它解决什么问题：避免 ProLayout 和未打开的页面继续挤在第一次打开时下载的主包里。

# ISSUE-020：路由级懒加载与代码分包

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-020 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | closed |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | route-chunks-1 |
| 关联 Task | APP-M2-T001；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)，待合入。本轮不新建 PR |
| 本地验收 | QA 签署 dcca509（REV-M0-T15）。项目经理授权后本 Issue 标为 closed。关联卡 APP-M2-T001 已为 done。见 [签署](../docs/testing/2026-10-12-issue-020-route-split-signoff.md) |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [ISSUE-020 交付](../docs/delivery/ISSUE-020.md) |
| 代码 / 流程解释 | [ISSUE-020 代码解释](../docs/code/ISSUE-020.md) |
| 验证记录 | [2026-10-12 路由分包](../docs/testing/2026-10-12-route-chunks.md) |

## 现象与证据

ISSUE-014 引入 `@ant-design/pro-layout@7.22.7` 后，`pnpm build` 只有一个脚本块 `index-BmV8EgUZ.js`，1,564.53 kB / gzip 486.19 kB。引入前的主包是 1,334.42 kB / gzip 409.62 kB。登录页因此要先下载外壳和全部项目页。

## 影响与分流

- 影响范围：`frontend/web` 的入口和页面加载。离开保护和 History 路由仍在 `App.tsx`。
- 本次不改 `backend/` 与 `tests/backend/`。页面回退仍由后台现有 catch-all 提供，不需要新接口。
- 不新增依赖。使用 React 18 的 `lazy` / `Suspense` 和 Vite 对 `import()` 的分包。
- 提交当时不把卡片或本 Issue 标成 done / closed。QA 签署 dcca509（REV-M0-T15）后，项目经理确认本 Issue 为 closed。关联卡 APP-M2-T001 已为 done。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| APP-M2-T001 | 按路由延迟加载外壳和页面，使首屏主块低于 1334.42 kB | `frontend/web/src` | AC-01～AC-03 | done |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 首屏主块原始体积低于引入 ProLayout 前的 1334.42 kB | 已提交复核。入口 `index-BXy7CunM.js` 为 315.94 kB / gzip 101.00 kB。`index.html` 预加载的 JS 合计 1080.17 kB / gzip 345.08 kB |
| AC-02 | 记录分包前后每一个产物的原始体积和 gzip | 已提交复核。见验证记录中的两张表 |
| AC-03 | 离开保护、历史路由和既有前端测试仍通过 | 已提交复核。`node --test` 为 78 pass、0 fail。未改后台文件 |
| AC-04 | 项目经理 QA 签收后才能 done | 已执行。QA 签署 dcca509（REV-M0-T15）。项目经理确认后本 Issue 为 closed，关联卡 APP-M2-T001 已为 done |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无正文修改。第19行仍写 T001 已开工、其余 258 卡 planned。第21行仍写整个 T001 未完成。分包不改变需求 | `docs/PRD.md` 第19行、第21行 | route-chunks-1 / ISSUE-020 / 2026-10-12 | 已核对，未改 |
| ROADMAP | 无正文修改。第17行仍写 344 项、20 done、7 in-progress、2 in-review，并写 AI-03 与 T001 为 in-review。第19行仍写接下来补 ProLayout。看板已是 350 项，本轮不回头改路线图 | `docs/ROADMAP.md` 第17行、第19行 | 同上 | 已核对，未改 |
| ARCHITECTURE | 无正文修改。第21行仍写布局和路由继续本卡。分包不改接口 | `docs/ARCHITECTURE.md` 第21行 | 同上 | 已核对，未改 |
| TASK_BOARD | 有影响。不新增任务。ISSUE-020 记为 in-review。计数保持 350 项：20 done、4 in-review、7 in-progress、266 planned、49 blocked、4 ready | `docs/TASK_BOARD.md` | 同上 | 已提交复核 |
| PROJECT_STATUS | 有影响。共同底座补上路由分包已提交复核，不写 done | `docs/PROJECT_STATUS.md` | 同上 | 已提交复核 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、交付、代码解释、验证和同步表 | `docs/DOCUMENT_INDEX.md` | 同上 | 已提交复核 |
| PROJECT_BRIEF | 无正文修改。第30行现为 350 项：20 done、4 in-review、7 in-progress、266 planned、49 blocked、4 ready，并写 T001、AI-03、错误体与幂等为 in-review。第68行仍写接下来补布局组件。该排期行由错误体与幂等那一轮写入 | `docs/PROJECT_BRIEF.md` 第30行、第68行 | 同上 | 已核对，未改 |

治理块保持 g1.1 / 2026-10-11 / ISSUE-007。参考原文不改。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | route-chunks-1 / in-review | 外壳和项目页改为动态 import。等待项目经理 QA 签收，不标 done | [验证](../docs/testing/2026-10-12-route-chunks.md) |
| 2026-10-12 | route-chunks-1 / closed | 项目经理在 QA 签署 dcca509（REV-M0-T15）后确认 closed。关联卡 APP-M2-T001 已为 done。未合入、未发布 | [签署](../docs/testing/2026-10-12-issue-020-route-split-signoff.md) |

## 本地验收与后续合入发布

- 本地复核材料已提交，日期 2026-10-12。这不是项目经理签收。
- 前端 78 项通过。没有在浏览器里逐页点开每个延迟块。三断点截图仍未做。
- 六份基线已按上表核对。PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF 未改正文。
- PR 状态：不新建 PR。PR #3 仍待合入。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
