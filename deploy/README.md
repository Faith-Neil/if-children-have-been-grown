# 三机内网部署底座

目标架构：MySQL 服务器、RAGFlow 服务器、应用服务器分离。应用容器只连内网服务；不引入 Redis，固定单 worker + 应用内线程池。

## 1. MySQL 服务器

1. 安装 MySQL 8，创建 utf8mb4 数据库与账号：

```sql
CREATE DATABASE icg CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'icg'@'%' IDENTIFIED BY '替换为应用密码';
GRANT ALL PRIVILEGES ON icg.* TO 'icg'@'%';
FLUSH PRIVILEGES;
```

2. 放行应用服务器到 3306；不要把 3306 暴露到公网。

## 2. RAGFlow 服务器

1. 部署内网 RAGFlow 1.0，并配置本地 embedding / chat 模型。
2. 创建 API Key，确认应用服务器可访问：`curl http://RAGFLOW_HOST:9380/api/v1/models`（按实例认证方式带 Bearer Key）。
3. 首次启动产品后，用公司管理员进入知识库管控，执行四库初始化/部署管道。自检清单：
   - `history`、`materials` 及资料子库数据集均带 `${company_id}::` 命名空间；
   - 管道绑定成功且 embedding 模型为内网模型；
   - 上传一份合成 `.doc` 后能转成 PDF 并完成解析；
   - 检索测试只召回本公司数据。

## 3. 应用服务器

1. 安装 Docker 与 Docker Compose 插件。
2. 拉取仓库，进入 `deploy/`：`cp .env.example .env`，填写 MySQL、RAGFlow 与首次管理员密码。
3. 构建并启动：`docker compose --env-file .env up -d --build`。
4. 容器启动命令会先执行 `python -m alembic -c alembic.ini upgrade head`，再以 `--workers 1` 启动 uvicorn。
5. 健康检查：`curl http://127.0.0.1:8710/api/v1/health`；`persistent` 必须为 `true`。

## 4. LibreOffice 转换探针

镜像已安装 `libreoffice-writer` 与 `fonts-noto-cjk`。在应用服务器执行：

```bash
docker compose exec icg sh -lc 'which soffice && fc-list :lang=zh | head -3'
docker compose exec icg sh -lc 'mkdir -p /tmp/lo-probe && printf test > /tmp/lo-probe/a.doc && soffice --headless --convert-to pdf --outdir /tmp/lo-probe /tmp/lo-probe/a.doc && test -s /tmp/lo-probe/a.pdf'
```

第一条必须输出 soffice 路径和中文字体；第二条必须生成非空 `a.pdf`。失败时不要上线四库 Word 上传。

## 5. 运维边界

- 单 worker 是有意约束；不要调大 `--workers`。
- `ICG_SECTION_CONCURRENCY` 默认 2，只在内网模型压力验证后调整，范围 1~4。
- 内网 HTTP 客户端固定 `trust_env=False`；不要在宿主机用代理变量旁路该边界。
- `.env`、真实客户文件、运行日志和凭据不得提交仓库。
