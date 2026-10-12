为什么有这个文件：记录离线 CI 的命令、版本和 Actions 运行结果。

它解决什么问题：把运行器上的通过与未执行的主题检查分开，避免用跳过掩盖失败。

# APP-M2-T008 离线 CI 验证

日期 2026-10-12。ISSUE-012 / APP-M2-T008。分支 `codex/repository-foundation`。关联 [ISSUE-013 复跑](2026-10-12-qa-rerun.md)。

## 工作流

文件：`.github/workflows/offline-check.yml`。触发：`push` 与 `pull_request`，分支 `codex/repository-foundation`。作业并行，运行器 `ubuntu-24.04`。Python 3.13.5，Node 24.9.0，pnpm 11.25.0。动作主版本：checkout v7、setup-python v7、setup-node v7、pnpm/action-setup v6，均声明 `node24`。pip 缓存 `backend/bid-core/requirements.txt`，pnpm 缓存 `frontend/web/pnpm-lock.yaml`。无密钥。

| 作业 | 命令 | 本轮 Actions 结果 |
|---|---|---|
| backend | `python -m pip install -r backend/bid-core/requirements.txt`；`python -m pytest tests/backend -q`；`python tests/backend/session_live_http.py`；`cd backend/bid-core && python smoke_t06.py` | success。262 passed，1 条既有警告，0 失败；TOTAL 15 PASS 15；smoke_t06 `passed: true`，12 项检查 |
| frontend | `pnpm install --frozen-lockfile`；`pnpm build`；`node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | success。构建通过，`index-BqghTeOl.js` 1334.42 kB / gzip 409.62 kB；72 pass，0 fail |
| governance | `node --test tests/governance/*.test.cjs tests/prototype/*.test.cjs tests/workspace-sync/*.test.cjs tests/backend/demo-page.test.cjs`；`node scripts/check-project-governance.cjs` | success。35 pass，0 fail；治理检查通过：129 份 Markdown、340 项任务、12 项 Issue |

运行：[38200746746](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38200746746)。提交 `cf2c2a1`。三个作业 conclusion 均为 success。没有 skip。

QA 在同一命令上的已记录结果，作为推送前基线，不是本次 Actions 运行：pytest 262 passed；前端函数 72/72；构建通过；治理 12/12；原型 6/6；工作区同步 10/10；旧页 7/7；会话脚本 TOTAL 15 PASS 15；治理检查通过。见 [QA复跑](2026-10-12-qa-rerun.md)。

## 未执行

- `buildTheme` 换主色后锁定令牌不变：仓库没有该函数。本任务按离线门禁交付，此项不算通过。
- 应用构建产物的主题令牌扫描：未新增扫描脚本。`pnpm build` 只做类型检查和生产构建。
- GUI、Word 版式、生产部署：不在本门禁。`smoke_t06.py` 只核对接口与 Word 包内容，CI 不调用 soffice，也不新增渲染步骤。

## 已知环境限制

Node v20.19.2 运行 `frontend/web/tests/*.test.mjs` 会因直接导入 `.ts` 而全部失败（`ERR_UNKNOWN_FILE_EXTENSION`）。这是运行器版本问题，不是套件跳过。CI 固定 Node 24.9.0。

此前运行器提示 `actions/checkout`、`actions/setup-node`、`pnpm/action-setup` 的 v4 仍声明 Node 20。本轮已换成上面的 Node 24 主版本，并固定 `ubuntu-24.04`。测试进程仍是 Node 24.9.0。没有套件失败。独立 `actions/cache` 最新主版本是 v6（`node24`）；缓存由 setup 动作完成，没有另加步骤。
