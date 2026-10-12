为什么有这个文件：提供最新分支复核的实际验证入口和执行记录。

它解决什么问题：让审阅者能重跑反例，区分本地测试、浏览器验证和真实数据库验收。

# 最新分支复核验证

2026-10-12；ISSUE-033 / REV-M0-T22。初次基线73fde1e，最终快照9c178782，完整保留新提交。具体反例、修复和剩余边界见[复核记录](../reviews/2026-10-12-foundation-review.md)，实现见[代码解释](../code/REV-M0-T22.md)。

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
