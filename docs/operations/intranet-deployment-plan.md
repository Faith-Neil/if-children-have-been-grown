为什么有这个文件：把内网部署写成一份可评审的草案，并标明哪些选择已经决定、哪些仍被挡住。

它解决什么问题：避免在还没有环境、容器或工作流时，把本地单进程演示说成已经可以上内网。

# 内网部署草案

日期 2026-10-12。关联 [ISSUE-017](../../issues/ISSUE-017.md) / [OPS-M0-T02](../tasks/OPS-M0.md#ops-m0-t02)。状态：用户 10-12 14:34 确认，卡片为 done，Issue 为 closed。未创建环境、Dockerfile、systemd 单元或新的 GitHub Actions 工作流，也没有改运行代码。确认不等于已经部署。

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
5. 健康检查请求 `GET /health`。`status=ok` 只说明进程在应答。未设置 `ICG_DATABASE_URL` 时看到 `persistent: false` 和 `repository: memory`。设置之后 `repository` 可以是 `mysql`，但 `persistent` 仍是 `false`，因为业务读写还在进程内存里。不能把这次检查当成数据已经持久。
6. 每个响应目前带 `Cache-Control: no-store`。不要假设静态资源可以被代理长期缓存。
7. `/api/demo/accounts` 会列出演示账号。在演示登录被替换之前，不要把这个入口暴露到比开发验证更宽的网络。

**当前约束（2026-10-12，ISSUE-034复核纠正）：** 后台仍必须是一个uvicorn worker、一个副本，`--workers`只能是1。未设置`ICG_DATABASE_URL`时全部数据在内存，重启清空。设置MySQL后，BE-M0-T11/T12/T13已实现共享会话、回执、编辑租约以及项目基本信息和成员分工；正文、草稿、版本、检查、导出、资料、工作流和片段等仍在进程内存。多worker、多副本和滚动发布继续等待[ISSUE-018](../../issues/ISSUE-018.md)的其余聚合迁移及整体验收，不能仅凭共享会话和项目列表就放开部署。

MySQL模式下重启后会话、回执及项目基本信息可以保留，正文等业务内容却不能恢复；保留的回执不能代替已丢失的内容。一台应用机、一个进程仍是当前部署上限。ISSUE-018保持in-progress，T12已由PM确认done；T11/T13仍in-review；本草案不把局部持久化写成完整交付，也不改原QA签署历史。

## 3. 配置和密钥

密钥、内网地址和客户正文不进 Git。`.venv`、`node_modules`、上传、日志和运行数据也不进 Git。

应用进程今天从环境读取模型开关，见第 1 节。目标形态是前端配置页填写对话端点、模型名和 API 密钥，并可在本地与云端之间切换。该页面还没有实现。密钥放在应用机的环境或公司密钥库，由服务管理器注入，文件放在仓库外。`ICG_MODEL_API_KEY_ENV` 里写的是变量名，不是密钥本身。

配置页上的模型 API 密钥用 Fernet 加密后再保存。主密钥只来自环境变量 `ICG_SECRET_KEY`。该值不写入仓库，不写入数据库，不写入日志。当前代码还没有读取 `ICG_SECRET_KEY`，仓库里也不放示例值。

数据库连接使用已经落地的变量名 `ICG_DATABASE_URL` 和 `ICG_REQUIRE_MYSQL`。连接串只存在于仓库外的环境。

RAGFlow 的基址和调用密钥使用占位名 `ICG_RAGFLOW_BASE_URL`、`ICG_RAGFLOW_API_KEY`。后者只从环境或公司密钥库注入，不进仓库，不进数据库。运行代码还没有读取这两个名字。具体接口路径不在本草案发明，见第 7 节。

提示词和密钥是否允许进日志，仍是 ISSUE-010 正文里的未决问题。本草案不改该 Issue。在有结论前，日志不记录密钥、`ICG_SECRET_KEY`、Authorization 头和模型全文。

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

有了 MySQL 之后，回滚要同时看库和程序，见下一节。RAGFlow 的索引和它自带的向量数据不在 MySQL 备份里。它们的备份方式、版本和容量留给 AI/RAG 计划确认，见第 7 节。回滚应用进程不会把 RAGFlow 索引一起退回。

## 6. 业务数据库：MySQL 8

业务库采用 MySQL 8。该决定已记在 [ISSUE-010](../../issues/ISSUE-010.md)（2026-10-12，user decision, relayed by PM）。字符集 `utf8mb4`。MySQL 8 的默认 Unicode 排序规则是 `utf8mb4_0900_ai_ci`；若公司规范指定另一种 `utf8mb4` 排序规则，以规范为准，但不要退回不能覆盖四字节字符的字符集。库只部署在内网，监听地址不对公网开放，应用机用专用账号连接，权限限于本业务库。

本卡不改写 ISSUE-010，也不关闭 AI-01。MySQL 8 没有向量检索，向量不放进业务库，pgvector 不再作为同库选项。嵌入和向量库按第 7 节改记为 RAGFlow 自带能力。起草时 ISSUE-010 正文仍写着这些项待决。随后该 Issue 已关闭，AI-01 改为 in-review。现行决定以 ISSUE-010 为准。

未设置`ICG_DATABASE_URL`时使用`MemoryRepository`。设置后，`MysqlConnectionRepository`报告`mode: mysql`，加载并保存MySQL会话、回执、编辑租约以及项目基本信息和成员分工，其他业务数据仍委托内存仓库。`requirements.txt`已有PyMySQL、SQLAlchemy、Alembic和cryptography（[ISSUE-023](../../issues/ISSUE-023.md)）；已有空基线、共享数据及项目表迁移。下面是备份和回滚要求，正文等业务聚合表尚未实现，不能据此宣称项目正文已有数据库备份。

备份同时做两层：

- 全量：`mysqldump`（InnoDB 使用一致性快照，例如单事务导出）或物理备份工具 XtraBackup。二者择一作为全量手段即可，本草案不指定必须买哪一个包装。
- 增量到某个时刻：打开二进制日志，保留覆盖最近一次全量之后的 binlog。需要回到两次全量之间的时刻时，用全量加上 binlog 做时间点恢复。

回滚和表结构迁移是两件事：

- 只回滚程序、不回滚库：仅当新迁移对旧程序兼容（先加字段或表，旧程序可以忽略）时才安全。
- 迁移删列、改类型或改含义时，旧程序不能指着新库启动。这时要把库恢复到迁移前的全量或对应的 binlog 位置，再启动旧程序。时间点恢复会丢掉该位置之后的写入，恢复前先停写。
- 不假设存在自动的向下迁移。ORM 是 SQLAlchemy，驱动是 PyMySQL，迁移工具是 Alembic。会话和幂等回执的持久化仍等 ISSUE-018 的 BE-M0-T11。在那之前，未设置 `ICG_DATABASE_URL` 的单元测试继续用内存仓库，运行形态保持一个 worker、一个副本。

ISSUE-025 已在托管 runner 上增加 `backend-mysql`：步骤内启动 `mysql:8.4`，只跑空迁移和 mysql 标记测试。原 `backend` 作业仍用内存和演示模型，不设置 `ICG_DATABASE_URL`。

## 7. RAGFlow：单独的内网服务

2026-10-12，项目经理转达 ISSUE-010 的用户决定，当时只写入本草案，不改 ISSUE-010 正文，不关闭 AI-01。随后的关闭记录在 ISSUE-010，不回写本段的起草事实。

- 对话模型的端点、模型名和 API 密钥放在前端配置页，本地与云端可切换。该页面尚未实现。今天仍是第 1 节的环境变量；未配置时保持演示替身。
- 嵌入模型和向量库使用 RAGFlow 自带能力，在 RAGFlow 里面配置，不放进 MySQL，也不再从 Milvus、Qdrant 或 Elasticsearch 里选一个。
- 检索层以后通过适配器调用 RAGFlow。ISSUE-016 / AI-03 的内存检索仍是 in-review 的骨架，不连接 RAGFlow。重启后这份内存检索和业务数据一起消失。
- 生产环境的生成服务全部留在内网。开发和测试可以使用互联网。
- 重排使用 RAGFlow 自带的重排器。重排模型在 RAGFlow 里面配置，不在本应用里另选产品，也不写入 MySQL。用户 10-12 14:34 确认。

RAGFlow 单独部署，不跟 uvicorn 进程挤在同一个工作进程里。它自带自己的组件和数据。版本号、CPU、内存和磁盘容量都标为「待 AI/RAG 计划确认」。本草案不写 RAGFlow 的版本，也不发明它的 API 路径、端口或请求字段。

### 网络拓扑

```text
浏览器 --> 内网反向代理 --> uvicorn（127.0.0.1:8710，一个 worker）
                              |
                              +--> MySQL 8（内网，可选；业务表尚未迁入）
                              |
                              +--> RAGFlow API（内网，另一套服务）
                                        |
                                        +--> RAGFlow 内配置的本地对话 / 嵌入 / 重排

浏览器 -x-> RAGFlow
生产环境的生成服务 -x-> 互联网
```

| 从 | 到 | 生产 | 开发 / 测试 |
|---|---|---|---|
| 浏览器 | 反向代理后的应用 | 仅公司内网 | 本机即可 |
| 浏览器 | RAGFlow | 不允许。页面只调本应用的 `/api` | 同样不允许直连 |
| 后台 | RAGFlow API | 内网，使用 `ICG_RAGFLOW_BASE_URL` | 可指向内网，或指向测试替身 |
| RAGFlow | 本地对话模型、嵌入与重排 | 内网。这三项都在 RAGFlow 内配置 | 该环境可以出网 |
| 配置页上的对话模型 | 所选端点 | 留在内网。页面可以填云端地址，生产网络没有出站 | 可以出网 |
| 后台 | MySQL 8 | 内网 | 仅当设置了 `ICG_DATABASE_URL` |
| 托管 CI | 真实 RAGFlow 或真实模型 | 不连接 | 不连接。见下文 |

生产环境的生成服务没有到互联网的出站。开发和测试可以出网。敏感项目现有门禁仍会拒绝未标明为本地的真实模型，本草案不放松这道门禁。

### 连通性检查

这些检查使用合成数据，不发送客户原文，不把密钥写进仓库。

1. 应用自身：`GET /health`。只证明进程在应答。`persistent: false` 仍然成立。
2. 后台到 RAGFlow：以后的适配器用配置的基址做一次合成探活。探活正文用固定的假文本，不用真实标书。本草案不规定探活的路径。基址缺失、拒绝连接或返回非成功时，检索必须失败并留下原因，不能把空结果说成检索成功。
3. RAGFlow 到本地模型：在 RAGFlow 自己的管理界面里用合成句子做连通测试。该项由 AI/RAG 计划写具体步骤。
4. 浏览器：确认页面网络里没有发往 RAGFlow 基址的请求。检索只经过本应用。

当前代码没有 RAGFlow 客户端，所以上面第 2、3 步还不能执行。

### 失败与回滚

- RAGFlow 不可用时，应用进程仍可启动并提供已有的内存演示。已经接上适配器之后，检索失败要显式失败，不能改写成演示成功，也不能改道去公网模型。
- 回滚应用是回到上一个 Git 提交并重启那一个进程。这不回滚 RAGFlow 的索引。RAGFlow 的升级或回退单独进行，版本仍待 AI/RAG 计划确认。
- 换 `ICG_SECRET_KEY` 之后，用旧主密钥加密的模型 API 密钥无法解密。更换前先在仓库外重新加密或重新录入。不要把新旧主密钥提交进 Git。
- 多副本和多worker仍然不做。MySQL模式已共享会话、回执、租约及项目基本信息，但一个进程仍看不到另一个进程的正文和片段，必须等其余业务聚合迁移及整体验收。

### CI

`.github/workflows/offline-check.yml` 不连接真实 RAGFlow，也不连接真实对话或嵌入模型。契约测试使用假的 OpenAI 兼容服务和假的 RAGFlow 测试替身。针对真实服务的测试必须显式打开，默认跳过。本轮不修改该工作流，也不加入这些替身的新作业；现有假 HTTP 只覆盖已经落地的对话适配器。

## 8. 这份草案没有做的事

- 没有创建机器、容器、反向代理配置或密钥。
- 没有部署 RAGFlow，没有写入它的版本、资源规格或 API 路径。
- 没有把 MySQL、RAGFlow、模型或自建 runner 写进 GitHub Actions。
- 没有实现前端模型配置页，也没有实现 `ICG_SECRET_KEY` 的 Fernet 加密。
- 没有实现 RAGFlow 适配器。健康检查也不会变成 `persistent: true`。
- 产品上的「部署与服务状态」页仍是 APP-M2-T042，不由本草案代替。
- FE-M8 的发布门禁仍 blocked。
