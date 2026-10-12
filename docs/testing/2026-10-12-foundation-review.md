为什么有这个文件：提供最新分支复核的实际验证入口和执行记录。

它解决什么问题：让审阅者能重跑反例，区分本地测试、浏览器验证和真实数据库验收。

# 最新分支复核验证

2026-10-12；ISSUE-034 / REV-M0-T27。初次基线73fde1e，复核快照9c178782，随后并入 foundation 9e3fcdd。ISSUE-033 与 REV-M0-T22 保持同伴原义。具体反例、修复和剩余边界见[复核记录](../reviews/2026-10-12-foundation-review.md)，实现见[代码解释](../code/REV-M0-T27.md)。

在仓库根执行：

```powershell
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
pnpm --dir frontend/web build
.venv\Scripts\python.exe -m pytest tests/backend -q --tb=short
node --test tests/governance/*.test.cjs tests/prototype/*.test.cjs tests/workspace-sync/*.test.cjs tests/backend/demo-page.test.cjs
node scripts/check-project-governance.cjs
```

浏览器配置使用独立本机端口8766、自启合成服务；`E2E_PYTHON`指向工作树虚拟环境。报告和截图在工作区外临时目录，测试会关闭自己启动的服务。

```powershell
pnpm --dir frontend/web exec playwright test --config e2e/playwright.config.ts
```

| 检查 | 实际结果 |
|---|---|
| 前端实际函数 | 113/113通过，含9项App/Editor和4项证据抽屉实际闭包回归 |
| 类型与正式构建 | 通过；入口318.42kB，gzip101.83kB |
| 真实浏览器 | 最终新构建整套16/16通过，47.1秒；含证据抽屉、失败切页重试及旧账号迟到401 |
| 后端 | 367通过、11个真实MySQL测试因未配连接跳过；105.62秒；33条既有或SQLite适配器弃用提示 |
| 治理与旧原型等 | 35/35通过；最终文档检查通过：282份Markdown、378项任务、33项Issue |

新片段3项修复前全部失败；新回执5项修复前4失败、1通过；新租约8项修复前5失败、3通过；新证据闭包4项修复前3失败、1通过。整合时3个SQL探针缺新参数，适配后完整重跑通过。SQL探针执行生产仓储方法，使用SQLite来判断读写条件。未设置`ICG_DATABASE_URL`，真实MySQL验收未在本机执行；不能用SQLite或跳过结果冒充MySQL通过。浏览器最初缺对应引擎，安装官方测试引擎后实际执行；选择器修正没有删减产品断言。

这是局部修复验证，不表示正式登录、完整持久化、真实模型、生产部署或整套ICG产品已经验收。

保留9a5533c并行更新后，前端113项及类型/构建通过，新构建整套浏览器16/16通过（47.1秒）。后端运行代码未改变，367项原完整通过结果仍适用。最新12项MySQL标记测试单独执行，全部因未配置连接跳过（367项非MySQL测试未在该命令重复执行）。原完整运行11项跳过是9c178时快照，不能混称实机验收。

## 并入 foundation 9e3fcdd 后的前端复跑

2026-10-12，合并 `9e3fcdd8f60ec4e751336c55154cbf9b9bae1e35` 并把复核卡改为 ISSUE-034 / REV-M0-T27 之后，在本机复跑前端。Node 24.9.0，pnpm 11.25.0。浏览器使用 Playwright Chromium，后台用 Python 3.12.3 的临时虚拟环境启动 uvicorn，未设置 `ICG_DATABASE_URL`。

| 检查 | 命令与结果 |
|---|---|
| 前端单测 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`：113/113 通过，约 0.86 秒。含迟到 401、失败切页后的离开确认、SECRET_KEY_UNAVAILABLE 只发一次、证据抽屉当前权限，以及资料补录走应用导航 |
| 类型与构建 | `pnpm --dir frontend/web build`：通过。入口仍为 318.42 kB，gzip 101.83 kB |
| 浏览器 | `pnpm --dir frontend/web exec playwright test --config e2e/playwright.config.ts`：16/16 通过，48.1 秒。含橙色标签 4.5:1、证据抽屉（冲突后刷新再保存）、失败切页重试、切账号后迟到 401 |
| 治理 | `node scripts/check-project-governance.cjs`：通过。301 份 Markdown、384 项任务、35 项 Issue |
| 后台全量 | 本轮没有重跑 pytest。R4、R6、R7 仍要真实 MySQL，不能用这次浏览器里的内存 uvicorn 代替 |

没有把任务或 Issue 标成 done 或 closed。没有声称 GitHub Actions 全绿。

## QA 正式签署（2026-10-12，tip `5eced4f`）

成长测试QA 在隔离工作树 `/workspace/qa-wt-pr4` 复跑并补真实 MySQL。结论：**R1～R9 通过**。详细对照见[QA签署](2026-10-12-issue-034-qa-signoff.md)。摘要：前端单测 113、构建入口 318.42kB/gzip 101.83kB、Playwright 16/16、治理 301/384/35、无库后台 371 passed / 13 skipped、`-m mysql` 12 passed、snippet/receipt/lease 回归 16 passed；真实 MySQL 上 R4 同键双 200 同 id 且有重放头，R6 条件 DELETE，R7 旧续期/释放 `423 LOCK_LOST`。本 tip 无 Actions 记录（workflow 只挂 foundation）。**不标 done，不合入。**
