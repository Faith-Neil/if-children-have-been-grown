为什么有这个文件：记录QA对ISSUE-020路由分包的正式签署。

它解决什么问题：在当前HEAD重新构建，确认首屏主块仍低于引入ProLayout前的基线，且离开保护与既有测试仍通过。

# ISSUE-020 路由分包 QA 签署

日期 2026-10-12（UTC+8）。签署卡 REV-M0-T15，归入 ISSUE-013。分支 `codex/repository-foundation`，核对到 `173c39f`（含 T078 `e6215d4` 与 `631d4c9`）。Node v24.9.0，pnpm 11.25.0。前次复核见 [T001/T002/T020复核](2026-10-12-qa-t001-t002-t020-recheck.md)（入口 317.64 kB / gzip 101.60 kB）。

## 结论

**通过。** AC-01～AC-03 满足；ISSUE-020 状态为 in-review，done 由项目经理设置。无缺陷。

## 逐条核对

| 编号 | 结果 | 证据 |
|---|---|---|
| AC-01 | 通过 | `pnpm build`：入口 `index-j6tq2-So.js` 317.71 kB / gzip 101.64 kB，远低于 1,334.42 kB。`index.html` 加载与预加载的 JS 共 5 个（index、rolldown-runtime、jsx-runtime、project-team、zh_CN），合计 1,081,971 字节（约 1081.97 kB），仍低于基线。较前次 +0.07 kB，来自 T078 新增代码 |
| AC-02 | 通过 | 本次全部产物：AppShell 221.58/73.00、EditorPage 82.36/26.66、ProjectPages 110.69/33.28、SlaPages 36.52/12.06、ProjectSettingsPage 22.57/8.92、SupportPages 11.32/4.53、project-team 301.24/91.87、jsx-runtime 431.47/142.66、zh_CN 30.72/9.08、collapse 10.50/3.84、sla-form 2.78/1.42、runtime 0.80/0.47、CSS 22.08/5.23（kB / gzip kB）。路由页面均为独立懒加载块 |
| AC-03 | 通过 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` 92 pass、0 fail；`tsc -b` 通过；CI run 38212117391 e2e（Playwright，含离开保护与前进/后退）13 passed |
| AC-04 | 流程 | 待项目经理设置 done |
