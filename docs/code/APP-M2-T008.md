为什么有这个文件：说明离线 CI 工作流实际怎么跑。

它解决什么问题：避免只看到文件名，却不知道每个作业安装什么、跑哪条命令、为什么会话脚本要单独一步。

# APP-M2-T008：代码解释

- 对应任务、Issue、交付文档：[APP-M2-T008](../tasks/APP-M2.md#app-m2-t008)、[ISSUE-012](../../issues/ISSUE-012.md)、[交付](../delivery/APP-M2-T008.md)。
- 日期、实际代码路径、提交 / PR：2026-10-12；`.github/workflows/offline-check.yml`；分支 `codex/repository-foundation`；[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 待合入。

## 改了什么以及为什么

原仓库没有 Actions。本文件在该分支的 `push` 和 `pull_request` 上启动三个互不依赖的作业。版本按 QA 已复跑的环境固定：Python 3.13.5、Node 24.9.0、pnpm 11.25.0。Node 20 不能执行直接导入 `.ts` 的前端测试，所以不使用 Node 20。

## 入口和调用顺序

1. backend 用 `actions/setup-python` 安装 Python 3.13.5，并按 `backend/bid-core/requirements.txt` 缓存 pip。然后 `python -m pip install -r backend/bid-core/requirements.txt`，`python -m pytest tests/backend -q`。pytest 只收集 `test_*.py`，因此下一步单独执行 `python tests/backend/session_live_http.py`。该脚本自己在 `127.0.0.1` 的空闲端口启动 uvicorn，使用合成种子数据，15 项全部通过时退出码为 0。再在 `backend/bid-core` 执行 `python smoke_t06.py`。它同样自启本机后台，做 12 项端到端核对，失败时退出码非 0。CI 不安装 soffice，也不增加 Word 渲染步骤。
2. frontend 先安装 pnpm 11.25.0，再用 Node 24.9.0，缓存 `frontend/web/pnpm-lock.yaml`。在 `frontend/web` 执行 `pnpm install --frozen-lockfile` 和 `pnpm build`。`package.json` 的 `build` 是 `tsc -b && vite build`。然后在仓库根运行 `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`。
3. governance 安装同一个 Node 24.9.0，运行 `tests/governance`、`tests/prototype`、`tests/workspace-sync` 和 `tests/backend/demo-page.test.cjs`，再运行 `node scripts/check-project-governance.cjs`。

三个作业没有 `needs`，因此并行，都在 `ubuntu-24.04`。`permissions` 只有 `contents: read`。文件中没有密钥、模型地址或内网地址。checkout、setup-node、setup-python 使用 v7，pnpm/action-setup 使用 v6。核对过这些标签的 `action.yml`，`using` 都是 `node24`。pip 与 pnpm 缓存由这两个 setup 动作写入；独立 actions/cache 的当前主版本是 v6，也是 `node24`，这里不单独调用。

## 数据与状态

CI 不写入业务数据库。后台测试和会话脚本使用现有内存仓库与模型替身；进程结束即丢弃。前端构建产物留在运行器的 `frontend/web/dist`，不提交。缓存只保存 pip 与 pnpm 依赖。

## 关键判断与异常

会话脚本失败时退出码为 1，backend 作业失败。pytest、`pnpm build`、`node --test` 和治理检查同样以非零退出码失败。没有 `continue-on-error`，也没有跳过。`cancel-in-progress` 为 false，避免后一次推送取消正在记录的运行。

## 验证与限制

验证见 [离线 CI 验证](../testing/2026-10-12-offline-ci.md)。本工作流不扫描主题令牌，也不实现 `buildTheme`。它不代替 GUI、Word 版式或生产部署验收。
