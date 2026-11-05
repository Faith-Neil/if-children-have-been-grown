为什么有这个文件：说明产品启动和虚拟机镜像从哪里进入。

它解决什么问题：避免以后分不清内存脚本和必须连库的入口。

# OPS-M0-T03 代码说明

日期 2026-11-04。Issue：[ISSUE-049](../../issues/ISSUE-049.md)。交付：[OPS-M0-T03](../delivery/OPS-M0-T03.md)。

本机入口是 `backend/bid-core/Start-Product.ps1`。它读取已有的 `ICG_DATABASE_URL`，否则读取被忽略的 `deploy/.env`，再否则使用本机 `icg-mysql` 的 `127.0.0.1:3307`。然后调用 `mysql_gate()`。门禁不是 `pass` 就退出。通过后设置 `ICG_REQUIRE_MYSQL=1` 和 `ICG_ALLOW_DEMO_LOGIN=0`，执行 Alembic，再以一个 worker 监听 `127.0.0.1`。

`Start-Demo.ps1` 现在要显式 `-AllowMemory` 才继续。未加该开关时不会创建内存进程。

虚拟机入口是 `deploy/docker-compose.yml`。`mysql` 使用 `mysql:8.0`，库不映射到宿主机。`icg` 按 `deploy/Dockerfile` 构建：Node 阶段以 `VITE_DEMO=0` 构建页面，Python 阶段安装 `backend/bid-core/requirements.txt`。`deploy/entrypoint.sh` 在连接串、MySQL 门禁、生产主密钥或管理员初始口令缺失时退出，然后迁移并启动 uvicorn。页面目录仍按 `icg/app/main.py` 的仓库相对路径放到 `/opt/icg/frontend/web/dist`。

单元测试不走这两个入口。未设置 `ICG_DATABASE_URL` 时，测试进程仍可以使用内存仓库。
