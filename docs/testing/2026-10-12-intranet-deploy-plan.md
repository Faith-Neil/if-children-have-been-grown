为什么有这个文件：记录内网部署草案对照了哪些现有入口，以及哪些检查没有跑。

它解决什么问题：避免用文档存在代替一次真实的内网或数据库验收。

# OPS-M0-T02 内网部署草案核对

日期 2026-10-12。ISSUE-017 / OPS-M0-T02。分支 `codex/repository-foundation`。

## 对照过的代码

| 事实 | 来源 |
|---|---|
| uvicorn 单进程，`127.0.0.1:8710`，`--workers 1` | `backend/bid-core/README.md` |
| `GET /health` 的 `persistent: false`、`single_process: true`、`repository`、`model` | `backend/bid-core/icg_demo/main.py` |
| 页面来自 `frontend/web/dist`，`/assets` 挂在同一进程 | 同上 |
| `GET /{full_path}` 把深链接回到 `index.html`，避开 `api`、`static`、`assets` | 同上 |
| 开发端口 5173 只转发 `/api`；生产构建是 `tsc -b && vite build` | `frontend/web/vite.config.ts`、`frontend/web/package.json` |
| 模型开关与密钥环境变量 | `backend/bid-core/icg_demo/openai_model.py` |
| 内存检索骨架不连接数据库 | `backend/bid-core/icg_demo/retrieval.py` |
| 现有 CI 无密钥、无内网、无数据库服务 | `.github/workflows/offline-check.yml` |
| 依赖清单没有 MySQL 驱动 | `backend/bid-core/requirements.txt` |

## 执行过的检查

提交前运行 `node scripts/check-project-governance.cjs`，输出为：治理检查通过：164 份 Markdown、351 项任务、18 项 Issue。该检查只核对记录是否互相链接，不连接 MySQL，也不启动 uvicorn。该数字含同分支上已并入的错误体、幂等和路由分包记录。

## 未执行

- 没有创建内网机器、反向代理、系统服务或容器。
- 没有安装 MySQL 8，没有跑 `mysqldump`、XtraBackup 或 binlog 恢复。
- 没有调用 vLLM、Xinference、Ollama、Milvus、Qdrant 或 Elasticsearch。
- 没有把 MySQL service container 加进 GitHub Actions。
- 推送之后的 offline-check 只重复现有内存测试。它通过也不表示本草案已经部署。
