为什么有这个文件：记下挂证据抽屉这一轮实际跑过的命令和没覆盖的部分。

它解决什么问题：避免把单测里的缺协议、受限写成演示接口已经能造出这些资料。

# 2026-10-12 APP-M2-T114 挂证据抽屉核对

接口以 `73fde1e` 的 `spec/openapi/demo-v1.json` 为准。从该提交到本轮开工，`spec/openapi/` 没有差异。README 里仍有一句旧的重试说明，那一句不是接口字段，本轮不改。

## 命令

| 命令 | 结果 |
|---|---|
| `node --test frontend/web/tests/evidence-drawer.test.mjs` | 4 passed |
| `node --test frontend/web/tests/*.test.mjs tests/frontend/*.test.mjs` | 97 passed，0 failed |
| `pnpm --dir frontend/web build` | `tsc -b` 与 vite 8.3.4 通过。主块 `index-DH4jVf51.js` 317.74 kB。`ProjectPages-kuYaeFaL.js` 115.25 kB |
| `E2E_PYTHON=python3 pnpm --dir frontend/web exec playwright test --config e2e/playwright.config.ts` | 14 passed。本机没有 `python` 命令，所以指定 `python3`。CI 仍用作业里的 `E2E_PYTHON=python` |

`frontend/web/package.json` 没有 lint 脚本，所以没有另跑 lint。

## 浏览器里核对过的

合成账号 `alpha-manager`，项目 `alpha-project`，截止时间 `2026-12-31 17:00`。先只放入待确认资料和已确认历史标书：抽屉显示“资料库没有可引用的记录”和“去补录”；历史标书没有勾选框，可以查看原文；待确认勾选框禁用。补上已确认资质、方案片段和 2020-01-01 的已确认资质后，只有未过期的已确认资质能保存。矩阵显示资料名和版本，状态仍是“待确认”，当时没有“证据失效”。把该资料有效期改到 2020-01-01 并填写核对说明后，同一行同时出现“待确认”和“证据失效”。另一个会话先移除挂接并保存后，原抽屉第一次保存被拒绝且不关闭，第二次保存显示“本行已被他人修改，请刷新后再保存”。`alpha-viewer` 的“挂证据”禁用。

截图写在工作区外的临时目录，不入库。

## 只在单测里的

缺协议（`source_tier: partner` 且 `agreement_present` 不是 true）和受限（`restricted: true`）返回不可勾选。演示的资料创建请求不允许这两个字段，浏览器造不出来。后台对挂接也不按这两条拒绝，只拒绝历史标书和未确认资料。这一层拦截在页面上。

## 未做

与设计稿并排截图、真实 Excel、批量智能匹配、`matrix_evidence` 的挂接人和挂接时间。这些不是本轮抽屉能单独完成的。不把本地通过写成已合入或已发布。

## QA 复查

过期挂接出现“证据失效”时，抽屉内有“刷新”。它重新读取资料候选和本行已挂编号，不发送保存。已挂列表对过期资料显示“证据失效”；候选卡片仍显示“过期”。

| 命令 | 结果 |
|---|---|
| `node --test frontend/web/tests/evidence-drawer.test.mjs` | 5 passed |
| `node --test frontend/web/tests/*.test.mjs tests/frontend/*.test.mjs` | 98 passed，0 failed |
| `pnpm --dir frontend/web build` | `tsc -b` 与 vite 8.3.4 通过。主块 `index-D3T5fjlc.js` 317.76 kB。`ProjectPages-Be_yLdBL.js` 116.03 kB |
| `E2E_PYTHON=python3 pnpm --dir frontend/web exec playwright test --config e2e/playwright.config.ts` | 14 passed。本机没有 `python` 命令，所以指定 `python3`。CI 仍用作业里的 `E2E_PYTHON=python` |

仍未覆盖，并记在交付的后续里：

- 缺协议和受限依赖 `source_tier`、`agreement_present`、`restricted`。这些字段由后台 ISSUE-033 跟踪。本轮不新建该 Issue。
- 智能匹配按钮尚未接通。
- 规则 2「证据过期后该行回到待确认」没有端到端。

后两项先挂在 ISSUE-033 下，等后台字段落地后再测。ISSUE-033 已由后台登记，本轮不改它。`frontend/web` 仍没有 lint 脚本。

## QA 验收②

另一会话先保存本行后，原抽屉第二次保存出现“本行已被他人修改，请刷新后再保存”，保存按钮禁用。该提示旁的“刷新”重读本行已挂证据。冲突提示消失，保存按钮恢复。再次保存成功，抽屉关闭，矩阵仍是对方保存后的“尚未挂接”。过期挂接的“证据失效”和它自己的刷新仍在。

| 命令 | 结果 |
|---|---|
| `node --test frontend/web/tests/evidence-drawer.test.mjs` | 5 passed |
| `node --test frontend/web/tests/*.test.mjs tests/frontend/*.test.mjs` | 98 passed，0 failed |
| `pnpm --dir frontend/web build` | `tsc -b` 与 vite 8.3.4 通过。主块 `index-D9xOHS0T.js` 317.76 kB。`ProjectPages-D3PC1rUI.js` 116.12 kB |
| `E2E_PYTHON=python3 pnpm --dir frontend/web exec playwright test --config e2e/playwright.config.ts` | 14 passed。本机没有 `python` 命令，所以指定 `python3`。CI 仍用作业里的 `E2E_PYTHON=python` |

## QA 独立复签（REV-M0-T22 / e691405）

成长测试QA于恢复后独立复跑。签署记录见 [e691405复签](2026-10-12-app-m2-t114-e691405-signoff.md)。结论通过；**缺协议、受限依赖 ISSUE-033**。智能匹配与规则 2 端到端仍挂 ISSUE-033。APP-M2-T114 不标 done。

| 命令 | 结果 |
|---|---|
| `node --test frontend/web/tests/evidence-drawer.test.mjs` | 5 passed（Node 24.9.0） |
| `node --test frontend/web/tests/*.test.mjs tests/frontend/*.test.mjs` | 98 passed，0 failed |
| `pnpm --dir frontend/web build` | `tsc -b` 与 vite 8.3.4 通过。主块 `index-D9xOHS0T.js` 317.76 kB。`ProjectPages-D3PC1rUI.js` 116.12 kB |
| `E2E_PYTHON=<venv> E2E_PORT=8877 pnpm --dir frontend/web exec playwright test --config e2e/playwright.config.ts` | 14 passed |
| CI [run 38227446697](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38227446697) | 五个 job 全绿（head `e691405`） |
