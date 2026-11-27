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
5. 健康检查：`curl http://127.0.0.1:8710/health`；`persistent` 必须为 `true`。注意健康端点是 `/health`，`/api/v1` 下没有健康路由；compose 健康检查会同时断言 `persistent`，内存态一律视为 unhealthy。

## 3.1 端口暴露安全默认（反向代理 HTTPS）

`docker-compose.yml` 默认把应用端口绑定在 `127.0.0.1:8710`：容器明文 HTTP 只监听回环地址，不暴露到任何网卡，登录接口与 Access Token 不会以明文形式出现在局域网/公网链路上。

对外提供访问时，必须在宿主机用反向代理以 HTTPS 终止后转发到回环端口，推荐 Nginx 最小示例：

```nginx
server {
    listen 443 ssl;
    server_name bid.example.internal;

    ssl_certificate     /etc/nginx/certs/bid.example.internal.crt;
    ssl_certificate_key /etc/nginx/certs/bid.example.internal.key;

    location / {
        proxy_pass http://127.0.0.1:8710;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300s;
        client_max_body_size 100m;
    }
}
```

要点：

- 代理与应用同机，转发目标固定 `127.0.0.1:8710`，不要指向容器网桥地址；
- 生成接口流式响应耗时较长，`proxy_read_timeout` 不小于 300s，上传招标文件需要放宽 `client_max_body_size`；
- 严禁为了省事把 `ICG_BIND_HOST` 改为 `0.0.0.0` 直接对外暴露明文 HTTP；仅在内网调试且确无代理时，才可在 `.env` 显式设置 `ICG_BIND_HOST` 放开绑定，并在结束后立即收回；
- MySQL 3306 与 RAGFlow 端口同样只允许内网服务器间互通，不暴露公网。

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
