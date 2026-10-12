为什么有这个文件：记录连接配置和空迁移这张卡实际交了什么。

它解决什么问题：把已连上的 MySQL 和尚未入库的业务数据分开。

# BE-M0-T10：连接配置与迁移骨架交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T10 |
| 代码解释 | [BE-M0-T10](../code/BE-M0-T10.md) |
| 验收 | 2026-10-12：未设连接串时 316 通过、2 跳过；`mysql:8.4` 上 `-m mysql` 2 通过。`ICG_REQUIRE_MYSQL=1` 且缺少 `ICG_DATABASE_URL` 时 2 failed、不是 skipped。uvicorn 仅凭该环境变量启动，`/health` 的 repository 为 mysql。见 [验证](../testing/2026-10-12-mysql-connection.md) |
| 项目进度 | 360 项：23 done、7 in-review、7 in-progress、269 planned、50 blocked、4 ready。本卡 in-review。T11～T13 planned。ISSUE-018 为 in-progress，不关闭 |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-018](../../issues/ISSUE-018.md)，[ISSUE-023](../../issues/ISSUE-023.md)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收已做。等待项目经理 QA 签收后才能标 done。

## 完成内容与变更文件

- `backend/bid-core/requirements.txt`：`sqlalchemy~=2.0.54`、`PyMySQL~=1.1.3`、`cryptography~=50.0.2`、`alembic~=1.14.1`。安装依赖另锁 `Mako==1.4.3`、`greenlet==3.5.6`、`cffi==2.1.1`、`pycparser==3.11`。
- `backend/bid-core/icg_demo/database.py`、`main.py` 的 `create_app`。
- `backend/bid-core/alembic.ini`、`alembic/env.py`、`alembic/versions/0001_baseline.py`。
- `pytest.ini` 登记标记 `mysql`。`tests/backend/conftest.py` 在调用阶段执行失败或跳过。
- 未改 `.github/workflows/offline-check.yml`。未建业务表。

## 代码解释

见 [代码解释](../code/BE-M0-T10.md)。

## 验收结果

- 镜像 `mysql:8.4`。密码只在执行机环境中，未写入仓库或 uvicorn 日志。
- 迁移命令 `alembic -c backend/bid-core/alembic.ini upgrade head` 成功，库里只有 `alembic_version`。
- 字符集 `utf8mb4`，排序规则 `utf8mb4_0900_ai_ci`。
- uvicorn 只设置 `ICG_DATABASE_URL` 后，`GET /health` 返回 `repository=mysql`、`status=ok`。业务状态仍不是持久的。

## 项目进度

BE-M0 共 13 项：T01～T03 done，T08 与 T10 in-review，T04～T07 ready，T09 与 T11～T13 planned。下一张实施卡是回执和会话入库，本卡不自动开始。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 未改。未改业务规则 |
| ROADMAP | 未改 |
| ARCHITECTURE | 未改。ISSUE-005 的那一句保持原样 |
| Issue 看板/详情 | ISSUE-023 为 in-review。ISSUE-018 改为 in-progress |
| TASK_BOARD / PROJECT_STATUS | 已改为 360 项 |
| DOCUMENT_INDEX | 已登记本交付、代码说明、验证和同步表 |

## 风险与后续

多进程回执、重启后的会话和租约仍未共享。`persistent` 保持 false。公网 CI 不会因为缺库而失败，内网作业必须自己设置 `ICG_REQUIRE_MYSQL=1`。
