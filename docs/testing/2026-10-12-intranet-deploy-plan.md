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
| 依赖清单已有 PyMySQL、SQLAlchemy、Alembic、cryptography；未设置 `ICG_DATABASE_URL` 时仍用内存仓库 | `backend/bid-core/requirements.txt`、`icg_demo/database.py` |
| 设置连接串后 `MysqlConnectionRepository` 只验证连接，读写仍委托内存 | `backend/bid-core/icg_demo/database.py` |
| `GET /health` 即使 `repository` 为 `mysql` 仍返回 `persistent: false` | `backend/bid-core/icg_demo/main.py` |
| 登录会话在 `DemoState.sessions`，幂等回执在 `DemoState.workflow_receipts`，都随内存仓库 | `backend/bid-core/icg_demo/domain.py`、`idempotency.py` |
| 运行代码不读取 `ICG_SECRET_KEY`、`ICG_RAGFLOW_BASE_URL`、`ICG_RAGFLOW_API_KEY` | `backend/`、`frontend/`、`.github/workflows/` 中没有这些名字 |

## 本轮核对的 RAGFlow 条款

| 条款 | 结果 |
|---|---|
| RAGFlow 写成单独的内网服务，版本和资源规格标为待 AI/RAG 计划确认 | 已写入草案第 7 节。没有填写版本号或机器规格 |
| 没有发明 RAGFlow 的 API 路径、端口或请求字段 | 草案只写「后台到 RAGFlow API」和占位环境变量名 |
| 连通矩阵：后台到 RAGFlow；RAGFlow 到本地模型与嵌入；浏览器不直连 RAGFlow；生产生成服务不出网；开发/测试可以出网 | 已写入第 7 节的拓扑和表 |
| 占位名 `ICG_RAGFLOW_BASE_URL`、`ICG_RAGFLOW_API_KEY` 只来自环境或密钥库；`ICG_SECRET_KEY` 是 Fernet 主密钥，不进仓库和数据库 | 已写入第 3 节和第 7 节。仓库中没有这些值 |
| 连通性检查使用合成探活，且标明当前代码还不能执行 RAGFlow 探活 | 已写入第 7 节 |
| 失败时检索不能伪装成功，也不能改道公网；回滚应用不回滚 RAGFlow 索引 | 已写入第 7 节 |
| CI 不连接真实 RAGFlow 或真实模型；真实服务测试须显式打开并默认跳过 | 已写入第 7 节。`.github/workflows/offline-check.yml` 本轮未改 |
| 单 worker、单副本约束仍然有效，直到 ISSUE-018 持久化会话和幂等回执 | 草案第 2 节保留该约束，并改为指向已建档的 ISSUE-018 |

## 执行过的检查

提交前运行 `node scripts/check-project-governance.cjs`，输出为：治理检查通过：196 份 Markdown、361 项任务、23 项 Issue。该检查只核对记录是否互相链接，不连接 MySQL，不连接 RAGFlow，也不启动 uvicorn。rebase 到 `98c5129` 之后复跑，数字随之更新。

## 未执行

- 没有创建内网机器、反向代理、系统服务或容器。
- 没有安装 MySQL 8，没有跑 `mysqldump`、XtraBackup 或 binlog 恢复。
- 没有部署 RAGFlow，没有调用真实对话模型、嵌入模型或 RAGFlow。
- 没有调用 vLLM、Xinference、Ollama、Milvus、Qdrant 或 Elasticsearch。
- 没有把 MySQL service container、真实 RAGFlow 或真实模型加进 GitHub Actions。
- 没有实现假 RAGFlow 测试替身。现有假 HTTP 只覆盖已经落地的对话适配器。
- 推送之后的 offline-check 只重复现有内存测试。它通过也不表示本草案已经部署。
