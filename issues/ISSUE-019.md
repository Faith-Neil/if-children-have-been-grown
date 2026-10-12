为什么有这个文件：登记引入Playwright作为仅测试用依赖并建立浏览器端到端检查。

它解决什么问题：布局断点、浏览器前进后退、刷新和离开确认此前只有函数测试，没有真实浏览器证据。

# ISSUE-019：Playwright浏览器端到端检查（仅测试依赖）

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-019 |
| 类型 | version |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | e2e-1 |
| 关联 Task | [REV-M0-T06](../docs/tasks/REV-M0.md#rev-m0-t06)；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)，待合入 |
| 本地验收 | 待项目经理确认；QA本机11项通过（含4项已知缺陷以test.fail标记） |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [REV-M0-T06交付](../docs/delivery/REV-M0-T06.md) |
| 代码 / 流程解释 | [REV-M0-T06代码解释](../docs/code/REV-M0-T06.md) |
| 验证记录 | [E2E与T001签署](../docs/testing/2026-10-12-e2e-t001-signoff.md) |

## 现象与证据

项目经理批准引入Playwright（仅Chromium）。依赖只进`frontend/web`的devDependencies：`@playwright/test@1.64.0`（精确版本），`pnpm-lock.yaml`同步；运行时依赖不变，产物包不含它。

## 影响与分流

- 新增`frontend/web/e2e/`与`pnpm e2e`脚本；不改应用代码。
- Chromium浏览器需`pnpm --dir frontend/web exec playwright install chromium`单独下载，不入库。
- 依赖：无。CI接入由DevOps另行执行，本Issue只给建议。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| REV-M0-T06 | Playwright端到端检查 | `frontend/web/e2e/`、`frontend/web/package.json`、`frontend/web/pnpm-lock.yaml` | AC-01～04 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 仅测试依赖，运行时依赖不变，锁文件同步，`--frozen-lockfile`可装 | 通过 |
| AC-02 | 一条命令自启内存后台与构建页面，<5分钟 | 通过；`pnpm --dir frontend/web e2e`约40秒 |
| AC-03 | 1280/1440/1680核心页截图；应用内/后退/前进/刷新离开确认取消与确认；前进后退路由 | 通过；7项正向全部通过 |
| AC-04 | 发现的缺陷以可复现用例记录 | 通过；E2E-D1～D4以test.fail记录 |

## 六份基线 impact 与同步表

| 基线 | impact | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响：不改需求 | 无 | — / ISSUE-019 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响：不改阶段或顺序 | 无 | — / ISSUE-019 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响：只加测试依赖，运行结构不变 | 无 | — / ISSUE-019 / 2026-10-12 | 已核对 |
| PROJECT_BRIEF | 无影响：不改范围与排期结论 | 无 | — / ISSUE-019 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响：新增REV-M0-T06 in-review | `docs/TASK_BOARD.md` | — / ISSUE-019 / 2026-10-12 | 已同步 |
| PROJECT_STATUS | 有影响：计数与E2E说明 | `docs/PROJECT_STATUS.md` | — / ISSUE-019 / 2026-10-12 | 已同步 |
| DOCUMENT_INDEX | 有影响：登记新增文件 | `docs/DOCUMENT_INDEX.md` | g1.1 / ISSUE-019 / 2026-10-12 | 已同步 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | e2e-1 / in-review | 依赖与11项用例提交；待项目经理确认done | 成长测试QA |
