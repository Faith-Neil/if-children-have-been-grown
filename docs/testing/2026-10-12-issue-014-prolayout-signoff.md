为什么有这个文件：记录QA对ISSUE-014引入ProLayout及体积记录的独立复核。

它解决什么问题：确认只新增了批准的布局依赖，且引入前后体积可复现。

# ISSUE-014 ProLayout 依赖与体积 QA 签署

日期 2026-10-12（UTC+8）。签署卡 REV-M0-T14，归入 ISSUE-013。分支 `codex/repository-foundation`，引入提交 `29fce7b`，核对到 `9bcde17`。Node v24.9.0（与 CI 一致），pnpm 11.25.0。

## 结论

**通过。** AC-01、AC-02 满足；AC-03 为流程条目，ISSUE-014 保持 in-review，done 由项目经理设置。无缺陷。

## 逐条核对

| 编号 | 结果 | 证据 |
|---|---|---|
| AC-01 | 通过 | `git diff 29fce7b^ HEAD -- frontend/web/package.json`：dependencies 只新增 `@ant-design/pro-layout` 7.22.7（批准二选一之一），未加 pro-components、react-router。devDependencies 的 `@playwright/test` 属 ISSUE-019 / REV-M0-T06，不在本 Issue 范围。源码只在 `frontend/web/src/shell/AppShell.tsx` 引用该包 |
| AC-02 | 通过 | 用 worktree 在 `29fce7b^` 与 `29fce7b` 各自 `pnpm install --frozen-lockfile && vite build`：`index-BqghTeOl.js` 1,334.42 kB / gzip 409.62 kB → `index-BmV8EgUZ.js` 1,564.53 kB / gzip 486.19 kB，与记录逐字一致（文件名哈希也一致） |
| 现状 | 通过 | 当前 HEAD 经 ISSUE-020 分包后入口 317.71 kB / gzip 101.64 kB；AppShell（含 ProLayout）为懒加载块 221.58 kB，不在 index.html 预加载内 |
| AC-03 | 流程 | 待项目经理设置 done |
