为什么有这个文件：说明 P0-DEPLOY-HOTFIX 容器健康检查与端口绑定部署配置的修改原因、运行过程与限制。

# P0-DEPLOY-HOTFIX：代码解释

- 对应任务、Issue、交付文档：[P0-DEPLOY-HOTFIX](../tasks/P0-HOTFIX.md#p0-deploy-hotfix)、[ISSUE-059](../../issues/ISSUE-059.md)、[交付说明](../delivery/P0-DEPLOY-HOTFIX.md)
- 日期、实际代码路径、提交 / PR：2026-11-27；`deploy/docker-compose.yml`、`deploy/README.md`；分支 `feat/iss-059-p0-security-export-deploy-hotfix`，PR 未创建。本卡无应用代码逻辑变化，按部署配置变更口径撰写。

## 改了什么以及为什么

原行为有两处 P0 缺陷：

1. `deploy/docker-compose.yml` 健康检查指向 `/api/v1/health`——该路由不存在（应用健康端点是 `/health`），正常运行的容器永远探测失败被报 unhealthy，编排系统误判并可能反复重启。
2. 端口绑定 `8710:8710` 默认暴露全部网卡：明文 HTTP 直接对局域网/全网卡开放，违反内网部署最小暴露面原则。

目标行为与实现：

- 健康检查改为探测 `http://127.0.0.1:8710/health`，且断言响应 JSON `status == 'ok'` 且 `persistent` 为真——内存态（非持久化）容器视为 unhealthy，异常容器如实 unhealthy。探针为 python 单行命令，经编译验证；compose YAML 经解析验证。
- 端口绑定改为 `${ICG_BIND_HOST:-127.0.0.1}:8710:8710`：默认只绑回环；`deploy/README.md` 新增「3.1 端口暴露安全默认（反向代理 HTTPS）」节，固化「只绑回环 + 宿主机反向代理（Nginx/Caddy）以 HTTPS 终止后转发」的安全默认，含 Nginx 示例、`proxy_read_timeout`（长任务/导出耗时）、`client_max_body_size`（100MB 上传）要点、严禁 `0.0.0.0` 明文直暴的警示，以及确需局域网直连时设 `ICG_BIND_HOST` 显式放开的方式；README 中健康检查 curl 路径同步修正为 `/health`。

## 入口和调用顺序

- 健康检查链：Docker 健康检查定时器 → 容器内执行 python 单行探针 → 请求 `127.0.0.1:8710/health` → 解析 JSON → `status=='ok' and persistent` 为真退出码 0（healthy），否则 1（unhealthy）。
- 外部访问链：客户端 HTTPS → 宿主机 Nginx/Caddy 443 终止 TLS → 明文转发 `127.0.0.1:8710`（回环，不出主机）→ 应用容器。

## 数据与状态

- 无应用状态变化；`persistent` 标志由应用 `/health` 端点按当前仓储模式（MySQL 持久化 vs 内存）如实输出。

## 关键判断与异常

- `persistent=false`（内存态）判 unhealthy 是止血语义：生产门禁 `ICG_REQUIRE_MYSQL=1` 下非持久化部署视为异常，编排重启策略据此处理。
- 默认回环绑定后，既有直接访问宿主机 IP 的局域网部署会断——有意为之，须显式 `ICG_BIND_HOST` 放开。

## 验证与限制

- python 单行探针经编译验证；compose YAML 经解析验证；`/health` 端点真实存在且语义与判据一致；`tests/backend/test_reference_flow.py` 21 passed 无回归；不引入 Redis、不增加 worker。
- 验证登记见 [iss-059-p0-hotfix-verification](../testing/iss-059-p0-hotfix-verification.md)。
- 限制：未在真实目标机执行 `docker compose up` 观察 healthy/unhealthy 状态翻转；Nginx 反代为文档示例，未在真实 HTTPS 终端验证。解释只对应当前实现。
