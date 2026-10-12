为什么有这个文件：登记项目经理已批准的四个 MySQL 依赖。

它解决什么问题：把版本引入和业务表实施分开，避免未登记就改 `requirements.txt`。

# ISSUE-023：引入 SQLAlchemy、PyMySQL、cryptography 和 Alembic

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-023 |
| 类型 | version |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | deps-1 |
| 关联 Task | [BE-M0-T10](../docs/tasks/BE-M0.md#be-m0-t10) |
| 关联 PR | 未创建。随既有分支提交，不新开 PR |
| 本地验收 | 2026-10-12 已安装并完成连接与迁移冒烟。等待项目经理 QA 签收 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [BE-M0-T10](../docs/delivery/BE-M0-T10.md) |
| 代码 / 流程解释 | [BE-M0-T10](../docs/code/BE-M0-T10.md) |
| 验证记录 | [2026-10-12 连接与迁移](../docs/testing/2026-10-12-mysql-connection.md) |

## 现象与证据

ISSUE-018 的方案列出四个待批准包。项目经理已批准 SQLAlchemy 2.0、PyMySQL 1.1、cryptography 和 Alembic 1.14，并要求锁在对应次版本。写入时的兼容发行是 `sqlalchemy~=2.0.54`、`PyMySQL~=1.1.3`、`cryptography~=50.0.2`、`alembic~=1.14.1`。`~=2.0.54` 表示不低于 2.0.54 且仍在 2.0。cryptography 取写入时的当前稳定次版本 50.0。

安装还带出 Mako 1.4.3、greenlet 3.5.6、cffi 2.1.1、pycparser 3.11。它们是这四项的安装依赖，按本仓库锁文件的精确版本写入，不另作选型。

## 影响与分流

- 只改 `backend/bid-core/requirements.txt` 的运行依赖。不改前端依赖，不加公网 CI 的 MySQL 服务。
- 连接和空基线迁移在 BE-M0-T10。回执、会话、租约和聚合表不在本 Issue。
- 密码不进仓库。连接串只来自 `ICG_DATABASE_URL`。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T10 | 写入四个已批准依赖，并接上连接与空迁移 | `backend/bid-core/requirements.txt` | AC-01～AC-03 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 四个包以兼容发行锁在批准的次版本，只出现在后台运行依赖 | 已写入。见验证记录 |
| AC-02 | 仓库中没有数据库密码 | 已核对 `requirements.txt`、`alembic.ini` 和迁移脚本 |
| AC-03 | 现有公网离线工作流不增加 MySQL 服务 | 未改 `.github/workflows/offline-check.yml` |

未做发布验收。in-review 不是 closed。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。未改页面或业务规则 | 不改 `docs/PRD.md` | deps-1 / ISSUE-023 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。不改路线图正文 | 不改 `docs/ROADMAP.md` | deps-1 / ISSUE-023 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。ISSUE-005 已写入的那一句仍描述当时未加驱动的复查范围。本轮不改架构正文 | 不改 `docs/ARCHITECTURE.md` | deps-1 / ISSUE-023 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。BE-M0-T10 为 in-review，T11～T13 为 planned | `docs/TASK_BOARD.md`、`docs/tasks/BE-M0.md` | deps-1 / ISSUE-023 / 2026-10-12 | 已改 |
| PROJECT_STATUS | 有影响。进度改为 360 项，并写明已有连接和空迁移 | `docs/PROJECT_STATUS.md` | deps-1 / ISSUE-023 / 2026-10-12 | 已改 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、交付、说明、验证和同步表 | `docs/DOCUMENT_INDEX.md` | deps-1 / ISSUE-023 / 2026-10-12 | 已改 |

PROJECT_BRIEF 排期行改为 360 项，记在同步表。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | deps-1 / in-review | 四个包已加入并完成本地连接冒烟。done 与 closed 等待项目经理在 QA 后设置 | [验证](../docs/testing/2026-10-12-mysql-connection.md) |

## 本地验收与后续合入发布

- 本地验收：2026-10-12，见验证记录。镜像 `mysql:8.4`。
- 未覆盖：公网 CI 不跑 MySQL。回执跨进程仍未实现。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-023-sync.md)。
- PR：未新开。合入与发布均未发生。
