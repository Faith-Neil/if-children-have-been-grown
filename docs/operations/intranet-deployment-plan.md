为什么有这个文件：把内网部署写成一份可评审的草案，并标明哪些选择已经决定、哪些仍被挡住。

它解决什么问题：避免在还没有环境、容器或工作流时，把本地单进程演示说成已经可以上内网。

# 内网部署草案

日期 2026-10-12。关联 [ISSUE-017](../../issues/ISSUE-017.md) / [OPS-M0-T02](../tasks/OPS-M0.md#ops-m0-t02)。状态：草案，in-review。未创建环境、Dockerfile、systemd 单元或新的 GitHub Actions 工作流，也没有改运行代码。done 由项目经理在 QA 签署后设置。

本文件描述的是目标放置方式。当前进程仍是内存仓库和演示登录。把这份草案提交入库不等于服务已经部署。

## 1. 今天代码实际怎么跑

后台入口是 `backend/bid-core/icg_demo/main.py` 的 `create_app()`。进程入口是：

```text
python -m uvicorn icg_demo.main:app --app-dir backend/bid-core --host 127.0.0.1 --port 8710 --workers 1
```

说明见 `backend/bid-core/README.md`。必须单进程。`GET /health` 返回 `status: ok`、`mode: local-demo`、`repository`（默认 `memory`）、`model`（`mock` 或 `real`）、`persistent: false`、`single_process: true`。

同一个进程提供接口和静态资源：

- `GET /` 读取 `frontend/web/dist/index.html`。路径由 `main.py` 从仓库根下的 `frontend/web/dist` 计算。未构建时返回 503 `UI_NOT_READY`。
- `/assets` 提供该构建目录里的静态文件。
- `/static` 与 `/demo` 是旧验证页，资源在 `icg_demo/static/`。
- 页面地址使用浏览器历史路径，任务仍是 APP-M2-T001 / ISSUE-009，状态 in-review。ISSUE-020 把外壳和项目页改成按路由加载，同样是 in-review，不改变下面的回退。同一进程对 `api`、`static`、`assets` 以外的路径用 `GET /{full_path}` 回到 `index.html`，这样刷新和深链接仍是这一张页面。未构建时返回 503 `UI_NOT_READY`。

前端生产构建在 `frontend/web`：`pnpm install --frozen-lockfile`，然后 `pnpm build`（`tsc -b && vite build`），输出 `dist`。`packageManager` 是 pnpm 11.25.0。开发时 `pnpm dev` 在 `127.0.0.1:5173`，只把 `/api` 转发到 `8710`。内网放置使用构建结果，不运行 Vite 开发服务器。

CI 固定 Python 3.13.5、Node 24.9.0。README 里的本机说明仍写过 Python 3.12.10；内网机器应跟已通过的 CI 版本，而不是另选一个未验证组合。

数据在 `MemoryRepository` 持有的 `DemoState` 里。登录会话在 `sessions`，幂等回执在 `workflow_receipts`。两者都只属于这一个进程。重启丢掉会话和幂等回执，也丢掉项目、锁、草稿、版本和导出。另一个 worker 或另一台副本看不到这份内存，所以同一次幂等标记不会在进程之间重放，已登录的令牌也不会被另一进程认出来。上传在请求里以 Base64 进入内存，单文件上限 5MB，没有独立文件卷。Word 由进程内生成，当前门禁不调用 soffice。

登录是 `POST /api/demo/login` 选择预置合成账号，凭证只留在页面内存。这不是公司身份系统。

模型默认是演示替身。只有 `ICG_MODEL_PROVIDER=openai-compatible`，并且同时提供 `ICG_MODEL_BASE_URL`、`ICG_MODEL_NAME`、`ICG_MODEL_IS_LOCAL` 时，才使用 `openai_model.py` 的兼容适配器。可选变量：`ICG_MODEL_API_KEY_ENV`（默认名字是 `ICG_MODEL_API_KEY`）、`ICG_MODEL_TIMEOUT_SECONDS`、`ICG_MODEL_MAX_TOKENS`、`ICG_MODEL_RETRIES`。未设置或值为 `demo` 时保持替身。配置不完整时进程拒绝启动，不回退成假成功。密钥在调用时读取，地址不允许把账号密码写进 URL。

## 2. 应用、页面和静态资源放在内网

数据留在公司网络内。应用机不直接对公网提供 8710。

建议的放置，仍是草案：

1. 内网反向代理终止 TLS，只接受公司网络的访问。
2. 代理把页面路径、`/assets`、`/static`、`/demo`、`/api`、`/health`、`/openapi.json` 转到本机 `127.0.0.1:8710`。深链接由该进程回退到 `index.html`。uvicorn 只绑定环回地址，并且只有一个 worker。
3. 发布物是某个 Git 提交上的 `frontend/web/dist` 加上同一提交的后台代码。先构建，再启动进程。
4. 进程可以由系统服务或容器托管。仓库里两种都还没有，本草案不新增文件。
5. 健康检查请求 `GET /health`。`status=ok` 只说明进程在应答。今天还会看到 `persistent: false` 和 `repository: memory`，不能把这次检查当成数据已经持久。以后仓库换成 MySQL 后，检查还应核对 `persistent` 与 `repository`。
6. 每个响应目前带 `Cache-Control: no-store`。不要假设静态资源可以被代理长期缓存。
7. `/api/demo/accounts` 会列出演示账号。在演示登录被替换之前，不要把这个入口暴露到比开发验证更宽的网络。

**约束（QA，2026-10-12）：** 会话和幂等回执仍是进程内内存。在 ISSUE-018 把它们持久化到 MySQL 之前，后台必须是一个 uvicorn worker、一个副本。`--workers` 只能是 1，不能再加进程，也不能再加应用副本。多 worker 和多副本部署 blocked 在尚未建档的 ISSUE-018。重启后已登录会话失效，已登记的幂等回执消失，客户端不能用旧标记重放重启前的成功结果。

滚动发布和共享会话同样等这个持久化。在那之前，一台应用机、一个进程就是与代码一致的上限。本草案不创建 ISSUE-018。

## 3. 配置和密钥

密钥、内网地址和客户正文不进 Git。`.venv`、`node_modules`、上传、日志和运行数据也不进 Git。

应用进程从环境读取模型开关，见第 1 节。密钥放在应用机的环境或公司密钥库，由服务管理器注入，文件放在仓库外。`ICG_MODEL_API_KEY_ENV` 里写的是变量名，不是密钥本身。

数据库账号将同样只存在于仓库外的环境。变量名等 ISSUE-018 选定驱动后再冻结。该编号尚未建档，本草案不发明连接串字段，也不创建该 Issue。

提示词和密钥是否允许进日志，仍是 ISSUE-010 的未决问题。在有结论前，草案要求日志不记录密钥、Authorization 头和模型全文。

## 4. 内网自建 runner 怎样连到 GitHub Actions

现有 `.github/workflows/offline-check.yml` 跑在 GitHub 托管的 `ubuntu-24.04` 上。它使用内存仓库和演示模型，不读密钥，也不访问内网。pytest、会话脚本、`smoke_t06.py`、前端构建与测试、治理检查继续留在托管 runner。

托管 runner 进不了公司内网。若以后要跑真实模型或真实库的检查，runner 应装在内网：

- 方向是 runner 主动向外连接 GitHub，领取作业。不要求 GitHub 连入内网。
- 用独立机器或虚拟机，不和对外的应用进程混在同一管理员账号下。标签例如 `intranet`，作业用 `runs-on` 显式选择，避免普通推送落到这台机器。
- 真实模型联调、以及以后针对 MySQL 的集成测试，才使用这个标签。密钥放在该 runner 的环境或仅对该环境可见的密钥库，不写入仓库。
- ISSUE-010 仍把「手工内网联调」和「内网自建 runner」列为未选定的访问方式。本节只说明连法，不代替那个选择，也不往工作流里加作业。

## 5. 备份、制品和回滚

今天没有可备份的业务库。回滚应用就是回到上一个 Git 提交并重启那一个进程；内存数据不会跟着回来。

可以版本化的是：

- 代码提交或发布标签。
- 该提交构建出的 `frontend/web/dist`。
- 仓库外的环境文件，由公司配置库单独保存，和代码版本一起记下对应关系。

发布记录至少包含提交 SHA、Python/Node/pnpm 版本和构建是否来自该 SHA。当前没有已发布版本。

有了 MySQL 之后，回滚要同时看库和程序，见下一节。向量库、模型权重和嵌入索引不在这次备份范围内，因为它们还没选定。

## 6. 业务数据库：MySQL 8

业务库采用 MySQL 8。该决定已记在 [ISSUE-010](../../issues/ISSUE-010.md)（2026-10-12，user decision, relayed by PM）。字符集 `utf8mb4`。MySQL 8 的默认 Unicode 排序规则是 `utf8mb4_0900_ai_ci`；若公司规范指定另一种 `utf8mb4` 排序规则，以规范为准，但不要退回不能覆盖四字节字符的字符集。库只部署在内网，监听地址不对公网开放，应用机用专用账号连接，权限限于本业务库。

本卡不改写 ISSUE-010，也不关闭 AI-01。MySQL 8 没有向量检索，向量不放进业务库，pgvector 不再作为同库选项。嵌入、重排、向量库和对话模型仍由 ISSUE-010 挡住。

当前代码没有 MySQL 驱动，也没有迁移。`MemoryRepository` 仍是运行中的仓库。下面是库就位之后的备份和回滚要求，不是已经接上的行为。

备份同时做两层：

- 全量：`mysqldump`（InnoDB 使用一致性快照，例如单事务导出）或物理备份工具 XtraBackup。二者择一作为全量手段即可，本草案不指定必须买哪一个包装。
- 增量到某个时刻：打开二进制日志，保留覆盖最近一次全量之后的 binlog。需要回到两次全量之间的时刻时，用全量加上 binlog 做时间点恢复。

回滚和表结构迁移是两件事：

- 只回滚程序、不回滚库：仅当新迁移对旧程序兼容（先加字段或表，旧程序可以忽略）时才安全。
- 迁移删列、改类型或改含义时，旧程序不能指着新库启动。这时要把库恢复到迁移前的全量或对应的 binlog 位置，再启动旧程序。时间点恢复会丢掉该位置之后的写入，恢复前先停写。
- 不假设存在自动的向下迁移。ORM、数据库驱动和迁移工具都还没选，等后台的 ISSUE-018。会话和幂等回执的持久化也等这一项。在那之前不引入迁移文件，单元测试继续用内存仓库，运行形态保持一个 worker、一个副本。

以后的集成测试可以在托管 runner 上加一个 MySQL 8 service container。现在不加。`offline-check.yml` 保持内存和演示模型。

## 7. 向量库、对话模型、嵌入和重排

这四项仍 blocked 在 ISSUE-010。本草案不选择它们。ISSUE-016 / AI-03 已有一份内存检索骨架，状态 in-review。它不连接 MySQL，也不在下面三个向量库里选定任何一项。重启后这份内存检索和业务数据一起消失。

| 项 | 可选项 | 状态 |
|---|---|---|
| 向量库 | Milvus、Qdrant，或公司已经在用的 Elasticsearch | 未决定。不放进 MySQL，也不假设有 pgvector |
| 对话模型 | 内网本地 Qwen，由 vLLM、Xinference 或 Ollama 提供现有代码已经调用的 OpenAI 兼容 `POST {base_url}/v1/chat/completions` | 未决定。端点和密钥不入库。未配置时仍是演示替身 |
| 嵌入 | 名称和维度都未定 | 未决定 |
| 重排 | 可暂不启用、本地模型或兼容接口 | 未决定 |

云端模型是否允许，仍是 ISSUE-010 的未决问题。敏感项目现有门禁会拒绝未标明为本地的真实模型。

## 8. 这份草案没有做的事

- 没有创建机器、容器、反向代理配置或密钥。
- 没有把 MySQL、模型或自建 runner 写进 GitHub Actions。
- 没有实现 `Repository` 的数据库版本，健康检查也不会变成 `persistent: true`。
- 产品上的「部署与服务状态」页仍是 APP-M2-T042，不由本草案代替。
- FE-M8 的发布门禁仍 blocked。
