为什么有这个文件：交付路由级分包这一轮的结果和证据。

它解决什么问题：避免把首屏变小写成整张底座已经完成。

# ISSUE-020 交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T001 |
| 代码解释 | [路由分包](../code/ISSUE-020.md) |
| 验收 | 首屏主块 315.94 kB，低于 1334.42 kB。[复核记录](../testing/2026-10-12-route-chunks.md)。状态为 in-review，项目经理尚未标 done |
| 项目进度 | 不新增任务。350项中20 done、4 in-review、7 in-progress、266 planned、49 blocked、4 ready。APP-M2-T001、ISSUE-009、ISSUE-014、ISSUE-016、ISSUE-020 为 in-review。AI-02 与 T008 已由项目经理标 done。BE-M0-T02、BE-M0-T03 与 ISSUE-005 的 in-review 属于另一张卡 |
<!-- task-delivery:end -->

日期 2026-10-12；ISSUE-020；分支 codex/repository-foundation；[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 为草稿待合入，未发布。此文提交复核，不把任务或 Issue 标成 done/closed。

## 完成内容与变更文件

`frontend/web/src/route-loaders.ts` 用动态 `import()` 加载外壳、编辑台、项目设置、项目页和支撑页，并缓存进行中的请求。`lazy-routes.tsx` 把它们包成 `React.lazy`。`App.tsx` 在登录后的外壳和各页面外加 `Suspense`。登录页仍在入口里。离开确认、`beforeunload` 和 History API 仍在 `App.tsx`，没有改判断。

没有改 `package.json`、锁文件、`backend/` 或 `tests/backend/`。

## 验收结果

分包前主块 `index-BmV8EgUZ.js` 为 1,564.53 kB / gzip 486.19 kB。分包后入口 `index-BXy7CunM.js` 为 315.94 kB / gzip 101.00 kB。首屏预加载 JS 合计 1,080.17 kB / gzip 345.08 kB。全部产物见验证记录。

`node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`：78 pass、0 fail。没有浏览器点击复核。

## 文档同步

| 文档 | 本轮处理 |
|---|---|
| PRD / ROADMAP / ARCHITECTURE / PROJECT_BRIEF | 正文未改。句子见 [ISSUE-020](../../issues/ISSUE-020.md) 同步表 |
| TASK_BOARD / PROJECT_STATUS | 补 ISSUE-020 为 in-review，任务计数不变 |
| DOCUMENT_INDEX | 登记本交付、代码解释、验证和同步表 |
| 后台 | 未改 |
