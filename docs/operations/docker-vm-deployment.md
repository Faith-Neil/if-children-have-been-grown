为什么有这个文件：把公司虚拟机上的 Docker 放置写成可以照着做的步骤。

它解决什么问题：避免在虚拟机上沿用内存启动，或把连接串和口令写进仓库。

# 公司虚拟机 Docker 部署

日期 2026-11-04。关联 [ISSUE-049](../../issues/ISSUE-049.md) / [OPS-M0-T03](../tasks/OPS-M0.md#ops-m0-t03)。

这份说明是给后续放到公司虚拟机时用的。本机工作站已经有容器 `icg-mysql`，用 [`Start-Product.ps1`](../../backend/bid-core/Start-Product.ps1) 连接它。不要在这台工作站再执行下面的 `docker compose up`，否则会和现有库抢端口或变成第二套空库。写完本文不等于虚拟机已经部署。

2026-10-12 的 [内网部署草案](intranet-deployment-plan.md) 仍是当时的决定记录。当时没有 Dockerfile。本文补上虚拟机要用的编排，不改那份草案的确认事实。

## 1. 这份部署包含什么

虚拟机上有两个容器，同一个 Docker 网络：

| 容器 | 镜像 | 作用 |
|---|---|---|
| `mysql` | `mysql:8.0` | 业务库 `icg`，字符集 `utf8mb4` |
| `icg` | 本仓库 `deploy/Dockerfile` | 关演示的页面和单进程后台 |

应用容器启动时先执行 Alembic `upgrade head`，再启动 uvicorn。`ICG_REQUIRE_MYSQL` 固定为 `1`。没有连接串、生产环境没有主密钥或管理员初始口令时，进程退出，不会改用内存仓库。

应用只把 `127.0.0.1:8710` 映射到虚拟机自己。MySQL 不映射到宿主机，其他机器不能直接连 3306。公司同事通过虚拟机上的反向代理访问页面，代理再转到 `127.0.0.1:8710`。

仍只能有一个应用进程。镜像里的 `--workers` 是 1。不要水平扩成多副本。后台作业锁还在进程内。

不包含 RAGFlow，也不包含本地对话模型。这两项仍是内网里另外的服务。本文不表示它们已经接通。生产生成不得把招标文件、投标正文或提示词发往公网模型。

应用镜像里有 LibreOffice 和中文字体。`.doc`、`.docx` 会先转成 PDF，再交给公司 RAGFlow 的 DeepDOC 按页识别。本机工作站没有 LibreOffice 时，改用已安装的 Microsoft Word 做同一步转换。

## 2. 虚拟机准备

- 操作系统能运行 Docker Engine 与 Docker Compose v2。
- 能加载 `mysql:8.0` 和 `python:3.12-slim-bookworm`、`node:24-bookworm-slim`。公司网络拉不动时，在能访问镜像源的机器上 `docker save`，再拷到虚拟机 `docker load`。不要为了拉镜像把虚拟机暴露到公网。
- 检出与要发布的提交一致的仓库。构建用该提交里的 `frontend/web` 和 `backend/bid-core`。
- 磁盘留给 MySQL 数据卷。卷名是 compose 项目 `icg` 下的 `icg-mysql`。

## 3. 只放在虚拟机上的配置

在虚拟机的 `deploy/` 目录把 [`env.example`](../../deploy/env.example) 复制为 `.env`。`.env` 已被忽略，不要提交，不要贴进工单。

需要替换的项：

| 变量 | 用途 |
|---|---|
| `MYSQL_ROOT_PASSWORD` | 库根口令，只给库管理员 |
| `MYSQL_PASSWORD` | 应用账号 `icg` 的口令 |
| `ICG_SECRET_KEY` | Fernet 主密钥，加密模型配置里的密钥。丢失后已加密的配置解不开 |
| `ICG_ADMIN_INITIAL_PASSWORD` | 空库第一次登录用的 `admin` 口令。首次登录后系统会要求修改 |
| `ICG_ENV` | 虚拟机保持 `production`。生产模式不加载合成公司和合成账号 |

主密钥在有 Python 的机器上生成一次，写入 `.env`，不要写进镜像：

```text
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`ICG_ENV=production` 时，入口脚本发现管理员初始口令为空会拒绝启动。

## 4. 启动与检查

在仓库根目录执行：

```text
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build
```

构建第一次会安装前端依赖并执行 `pnpm build`，`VITE_DEMO=0` 写进页面。之后改代码要重新 `--build`。

检查：

```text
docker compose --env-file deploy/.env -f deploy/docker-compose.yml ps
```

在虚拟机上请求 `http://127.0.0.1:8710/health`。通过时同时满足：

- `status` 为 `ok`
- `repository` 为 `mysql`
- `persistent` 为 `true`
- `mode` 为 `production`
- `single_process` 为 `true`

`repository` 若是 `memory`，这次部署不合格。先看应用日志里的迁移和连接错误，不要改回内存启动。

登录用 `POST /api/v1/auth/login`，账号 `admin`，口令是 `.env` 里的初始口令。登录后按页面要求修改口令，再建立公司和用户。

停止：

```text
docker compose --env-file deploy/.env -f deploy/docker-compose.yml stop
```

`stop` 不删除数据卷。`down -v` 会删掉业务库，只有确认要清空时才使用。

## 5. 反向代理

代理终止 TLS，只接受公司网络。把 `/`、`/assets`、`/api`、`/health` 转到 `127.0.0.1:8710`。页面刷新走同一进程回到 `index.html`。

不要把 8710 或 3306 发布到 `0.0.0.0`。不要把 `/demo` 暴露到比管理员更宽的网络。

## 6. 备份与回滚

备份业务库：

```text
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec mysql mysqldump --single-transaction -uicg -p icg
```

口令从 `.env` 读取，不要写进命令历史以外的仓库文件。需要时间点恢复时，再在 MySQL 配置中打开二进制日志。当前 compose 没有打开 binlog。

回滚程序是检出上一个提交并重新 `--build`。如果那个提交的迁移已经执行，而新迁移删了列或改了含义，旧程序不能对着新库启动。这时先停应用，用备份恢复库，再启动旧镜像。恢复会丢掉备份之后的写入。

RAGFlow 的索引不在这个 MySQL 备份里。回滚应用不会把知识库索引一起退回。

## 7. 本机工作站怎么启动

本机库是已经在跑的容器 `icg-mysql`，端口 `3307`，库名 `icg`。产品进程：

```powershell
& .\backend\bid-core\Start-Product.ps1
```

脚本探测 MySQL。探测失败就退出。默认环境是 `development`，沿用这台工作站上已有的合成账号，便于核对当前分支。虚拟机不要用 `development`。

`Start-Demo.ps1` 不加 `-AllowMemory` 不会启动。
