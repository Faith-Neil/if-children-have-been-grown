为什么有这个文件：登记产品启动改为只连 MySQL，以及公司虚拟机的 Docker 放置。

它解决什么问题：避免没有 Issue 就改启动入口和部署方式。

# ISSUE-049：产品启动连接 MySQL，并写虚拟机 Docker 部署

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-049 |
| 类型 | decision |
| 优先级 | P0 |
| 状态 | in-review |
| 登记日期 | 2026-11-04 |
| 最后更新日期 | 2026-11-04 |
| revision | ops-product-start-1 |
| 关联 Task | [OPS-M0-T03](../docs/tasks/OPS-M0.md#ops-m0-t03) |
| 关联 PR | 未创建 |
| 本地验收 | 本机 `/health` 为 mysql。虚拟机未部署。见交付说明 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [docs/delivery/OPS-M0-T03.md](../docs/delivery/OPS-M0-T03.md) |
| 代码 / 流程解释 | [docs/code/OPS-M0-T03.md](../docs/code/OPS-M0-T03.md) |
| 验证记录 | 交付说明中的本机健康检查。虚拟机未执行 compose |

## 现象与证据

产品入口长期是 `Start-Demo.ps1`，数据在内存，重启即丢。`Start-L2.ps1` 能连 MySQL，但要事先自己导出连接串，而且说明仍把内存脚本写成推荐入口。公司虚拟机上还没有 Dockerfile 和 compose。用户要求按企业放置启动，连上数据库，并留下后续 Docker 部署说明。

本机已有容器 `icg-mysql`（mysql:8.0，端口 3307）。2026-11-04 用 `Start-Product.ps1` 探测该库后启动。

## 影响与分流

- 影响启动入口、本机进程和后续虚拟机放置。关联 [ISSUE-017](ISSUE-017.md) 的草案仍保留当时“没有 Dockerfile”的事实。关联 [ISSUE-018](ISSUE-018.md)：仍然一个应用进程，不把多副本标成可用。
- 本次做启动脚本、镜像、编排和部署说明。不改招标主流程，不把 RAGFlow 或本地模型写进这套 compose。
- 依赖：本机 MySQL 容器已在运行。虚拟机部署依赖镜像能在内网加载。没有其他阻塞。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| OPS-M0-T03 | 产品启动必须连上 MySQL；虚拟机有一份 Docker 说明 | `backend/bid-core/Start-Product.ps1`、`deploy/`、`docs/operations/docker-vm-deployment.md` | 本机 health 为 mysql；说明写明虚拟机步骤和未部署 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 产品启动连不上 MySQL 时退出，不启动内存仓库 | 脚本在探测失败时抛错。本机探测通过后才启动 |
| AC-02 | 本机 `/health` 的 `repository` 为 `mysql`，`persistent` 为 `true` | 见交付说明。日期 2026-11-04 |
| AC-03 | 虚拟机说明包含 compose、密钥位置、健康检查、备份和单进程限制 | [部署说明](../docs/operations/docker-vm-deployment.md) |
| AC-04 | 不把虚拟机写成已经部署，不声称 RAGFlow 或本地模型已接通 | 说明第 1 节和文首 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。投标页面和角色没有改验收口径 | 不改 `docs/PRD.md` | ops-product-start-1 / ISSUE-049 / 2026-11-04 | 已核对 |
| ROADMAP | 无影响。没有新增产品里程碑 | 不改 `docs/ROADMAP.md` | 同上 | 已核对 |
| ARCHITECTURE | 有影响。产品启动和虚拟机放置 | `docs/ARCHITECTURE.md` 当前实施后的 2026-11-04 段 | 同上 | 已更新 |
| TASK_BOARD | 有影响。新增 OPS-M0-T03 | `docs/TASK_BOARD.md` | 同上 | 已更新 |
| PROJECT_STATUS | 有影响。本机已改 MySQL 启动，虚拟机未部署 | `docs/PROJECT_STATUS.md` | 同上 | 已更新 |
| DOCUMENT_INDEX | 有影响。新增说明、交付和任务 | `docs/DOCUMENT_INDEX.md` | 同上 | 已更新 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-11-04 | ops-product-start-1 / in-review | 本机产品进程改为连 MySQL。虚拟机 compose 已入库但未在虚拟机执行 | 交付说明 |

## 本地验收与后续合入发布

- 本地验收：本机健康检查通过。虚拟机未部署，不能标 closed。
- 未覆盖：公司虚拟机上的 `docker compose up`、反向代理和备份恢复演练。
- PR：未创建。合入：未合入。发布：未发布。
