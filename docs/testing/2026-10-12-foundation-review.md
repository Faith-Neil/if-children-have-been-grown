为什么有这个文件：提供最新分支复核的实际验证入口和执行记录。

它解决什么问题：让审阅者能重跑反例，区分本地测试、浏览器验证和真实数据库验收。

# 最新分支复核验证

2026-10-12；ISSUE-032 / REV-M0-T21。初次基线73fde1e，已保留并整合ae6fd10。具体反例、修复和剩余边界见[复核记录](../reviews/2026-10-12-foundation-review.md)，实现见[代码解释](../code/REV-M0-T21.md)。

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
| 前端实际函数 | 104/104通过，含9项实际App/Editor闭包回归 |
| 类型与正式构建 | 通过；入口318.33kB，gzip101.81kB |
| 真实浏览器 | 整套15/15通过，33.4秒；含新增失败切页重试和旧账号迟到401两项 |
| 后端 | 最新整合后的最终结果待补；第一次整合运行发现3个新增SQL探针未适配上游租约参数，已修正测试调用后继续验证 |
| 治理与旧原型等 | 先前35/35通过，最终记录一致性待补 |

新片段3项修复前全部失败；新回执5项修复前4失败、1通过。SQL探针执行生产仓储方法，使用SQLite来判断读写条件。未设置`ICG_DATABASE_URL`，真实MySQL验收未在本机执行；不能用SQLite或跳过结果冒充MySQL通过。浏览器最初缺对应引擎，安装官方测试引擎后实际执行；选择器修正没有删减产品断言。

这是局部修复验证，不表示正式登录、完整持久化、真实模型、生产部署或整套ICG产品已经验收。
