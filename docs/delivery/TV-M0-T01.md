为什么有这个文件：记录 TV-M0-T01 实际改了什么，以及还没做完的部分。

它解决什么问题：避免把侧栏隐藏和固定技术分册写成整条技术分册路径已经完成。

# TV-M0-T01 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T01](../tasks/TV-M0.md#tv-m0-t01) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-03 |
| 状态 | in-review。不标 done |
| 代码解释 | [TV-M0-T01](../code/TV-M0-T01.md) |

## 实际变更

- `frontend/web/src/app/App.tsx`：侧栏只留工作台、知识库、管理规则。新建项目请求固定 `volume_mode: technical_only`。
- `frontend/web/src/project/CreateProjectModal.tsx`：去掉编写范围选项。
- `frontend/web/tests/unit/project-volumes.test.mjs`、`frontend/web/e2e/app-shell.spec.ts`：对应断言。

企业资料库和写作档案的页面文件还在。直接打开 `/library`、`/writing` 仍会进入原页面。已有 `both` 项目的分册判断没有改。

## 验证

`pnpm --dir frontend/web exec node --test tests/unit/project-volumes.test.mjs`：4 项通过。

没有在浏览器里点开新建项目。端到端用例 `app-shell.spec.ts` 已改断言，本机没有跑。

## 同步

PRD、路线图、架构、项目状态、任务看板和 ISSUE-047 已加上本决定的入口。T02～T07 仍是 planned。

## 剩余

历史标书上传、多文件、抽取、单章目录、矩阵、正文和偏离表都还没做。上面这句是本卡完成时的边界。后续卡在同一分支继续，本卡仍是 in-review。

## 集成

集成分支 `feat/iss-047-technical-volume-mvp` 从决定记录 `0b9d1d5` 拉出，父提交是 `origin/main` 的 `36b7e41`。产品提交只在这条分支，不合并进 main。PR #7 只有决定记录，不接收本卡代码，本轮关闭。2026-11-03 在关掉数据库连接的内存仓储里，`python -m pytest tests/backend/test_technical_sources.py` 为 12 项通过，`python backend/bid-core/export_openapi.py --check` 通过。
