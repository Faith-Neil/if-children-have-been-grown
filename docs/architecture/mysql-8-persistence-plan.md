为什么有这个文件：把已决定的 MySQL 8 业务库写成可复查的持久化方案。

它解决什么问题：在批准驱动和迁移之前，先定存储、事务和测试边界，避免直接把整份内存状态搬进数据库。

# MySQL 8 持久化方案

日期：2026-10-12。关联 [ISSUE-018](../../issues/ISSUE-018.md)、任务 [BE-M0-T08](../tasks/BE-M0.md#be-m0-t08)。状态 in-review。下文第 1～8 节仍是方案。项目经理已批准四项依赖。连接配置和空基线迁移由 [BE-M0-T10](../tasks/BE-M0.md#be-m0-t10) 实施。回执和会话由 [BE-M0-T11](../tasks/BE-M0.md#be-m0-t11) 提交复查。编辑租约由 [BE-M0-T12](../tasks/BE-M0.md#be-m0-t12) 提交复查，字段对照在第 5 节。聚合表仍未做。业务数据以 [PRD v1.8](../reference/product/prd-mvp-v1.8.md) 和 [字典 v1.9](../reference/product/kb-data-dictionary-v1.9.md) 为准，这两份只读，不改 `docs/reference/`。

业务库已决定为 MySQL 8。向量库、对话模型、嵌入和重排仍随 ISSUE-010，不放进 MySQL。现有入口是 `Repository.read()` 与 `Repository.transaction(operation)`，回调收到整份 `DemoState`。`MemoryRepository` 在锁内深拷贝整份状态，失败不提交。幂等回执在 `DemoState.workflow_receipts`，键为 `(scope_id, user_id, key)`，保留 24 小时，内存最多 2048 条。编辑租约在 `Chapter.lock`，`LEASE_SECONDS = 120`。

## 1. 选型

| 角色 | 选择 | 理由 | 不选 |
|---|---|---|---|
| ORM | SQLAlchemy 2.0 | 与现有同步调用方式一致。2.0 的 `Session` 事务可以包住一次业务写入和回执插入。类型化查询能按聚合取行，不必先装出整份 `DemoState` | SQLModel：再包一层，当前领域已经是 dataclass。Django ORM：要换应用框架 |
| 驱动 | PyMySQL | 纯 Python，内网构建机不需要编译 C 扩展。连接串使用 `charset=utf8mb4` | mysqlclient：要系统编译库。mysql-connector-python：额外的 Oracle 客户端包，当前不需要 |
| 异步驱动 | 本方案不用 | 现有 `transaction` 是同步的，路由也按同步仓库调用。先保持同步，避免再引入事件循环依赖 | asyncmy、aiomysql、asyncpg |
| 迁移 | Alembic | 与 SQLAlchemy 元数据对应，可以生成可复查的 SQL。升级命令固定为 `alembic upgrade head` | 手写散落 SQL 文件：难和模型对照。应用启动时自动建表：生产和测试的结构会分叉 |

MySQL 8.4 默认账号认证是 `caching_sha2_password`。PyMySQL 处理这种认证需要单独的 `cryptography` 包，所以它单独列出，不并进驱动。

## 2. 依赖

项目经理已批准下列四项，并要求用兼容发行锁在次版本上。登记见 [ISSUE-023](../../issues/ISSUE-023.md)。安装它们带出的 Mako、greenlet、cffi、pycparser 按仓库既有锁文件方式写上精确版本，不另作选型。

| 包 | 锁定 | 用途 | 状态 |
|---|---|---|---|
| SQLAlchemy | `sqlalchemy~=2.0.54` | 会话、事务和聚合映射 | 已写入 `backend/bid-core/requirements.txt` |
| PyMySQL | `PyMySQL~=1.1.3` | MySQL 8 协议驱动 | 已写入 |
| cryptography | `cryptography~=50.0.2` | PyMySQL 连接 MySQL 8.4 的 `caching_sha2_password` | 已写入。50.0 是写入时的当前稳定次版本 |
| Alembic | `alembic~=1.14.1` | 迁移脚本和 `upgrade head` | 已写入 |

不引入 testcontainers、SQLModel、asyncmy、aiomysql、mysqlclient。集成测试使用 CI 的数据库容器，不在测试进程里再拉一层容器库。

## 3. 字符集与排序规则

库和表默认：

```sql
CREATE DATABASE icg_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

`utf8mb4` 覆盖正文里的汉字和四字节字符。`utf8mb4_0900_ai_ci` 是 MySQL 8 的默认 Unicode 排序，用于标题和正文。

幂等键、租约令牌和会话令牌使用 `utf8mb4_bin`。这些值大小写敏感；若用 `utf8mb4_0900_ai_ci`，`Ab` 与 `ab` 会被当成同一键，重放和冲突都会判错。键的格式仍是 `^[A-Za-z0-9_-]{8,120}$`。

连接参数固定 `charset=utf8mb4`。迁移里不使用 `utf8`（它在 MySQL 里是三字节的旧字符集）。

## 4. 表：幂等回执

对应现在的 `workflow_receipts`。一次成功写入和它的回执在同一事务里提交；失败回滚，不留回执。过期或失败结果不占用键，同一键可以再试。

```sql
CREATE TABLE idempotency_receipt (
  scope_id VARCHAR(160) NOT NULL,
  user_id VARCHAR(120) NOT NULL,
  idempotency_key VARCHAR(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  fingerprint CHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  result_json JSON NOT NULL,
  created_at DATETIME(6) NOT NULL,
  expires_at DATETIME(6) NOT NULL,
  PRIMARY KEY (scope_id, user_id, idempotency_key),
  KEY idx_idempotency_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

- `scope_id`：项目写为 `project_id`，公司资料和公司模板写为 `library:{company_id}`。
- `fingerprint`：`action`、规范化 payload、`If-Match` 的哈希，与现有 `fingerprint()` 相同。
- `expires_at`：`created_at` 加 24 小时。比较使用数据库的 `NOW(6)`，不使用应用机器时钟。
- 查找时先删过期行，再按主键读取。指纹相同且未过期则重放并设 `Idempotent-Replayed: true`。指纹不同返回 409 `IDEMPOTENCY_CONFLICT`。
- 内存里的 2048 条上限只留在 `MemoryRepository`。MySQL 不按条数删除未过期回执，否则 24 小时语义会被提前打断。过期删除在事务内做，不依赖事件调度器。
- 回执必须对多个进程和 worker 可见。任一进程提交的成功回执，其他进程用同一 scope、账号和键都能读到。进程退出再启动后，未过期回执仍在，重放结果不变。这是方案的验收条件。当前内存实现做不到，所以 ISSUE-017 在本方案实施前仍限制为一个 worker、一个副本。本轮不改那个限制。

## 5. 表：编辑租约

对应 `Lease`：`token`、`owner_id`、`session_token`、`expires_at`。时长 120 秒。一章一行。

```sql
CREATE TABLE chapter_lease (
  chapter_id VARCHAR(120) NOT NULL,
  token VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  owner_id VARCHAR(120) NOT NULL,
  session_token VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  expires_at DATETIME(6) NOT NULL,
  PRIMARY KEY (chapter_id),
  CONSTRAINT fk_chapter_lease_chapter FOREIGN KEY (chapter_id) REFERENCES chapter (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

- 续期：同一事务里 `SELECT chapter, chapter_lease FOR UPDATE`。仅当令牌、所有者和会话都匹配且 `expires_at > NOW(6)` 时，把 `expires_at` 改为 `NOW(6) + INTERVAL 120 SECOND`。
- 接管：租约已过期，或调用方提供接管原因时，在同一事务替换该行，审计记录原因和上一所有者。未过期且无原因时保持现有拒绝行为。
- 释放：匹配的未过期租约删除该行并写审计。保存草稿和提交版本继续要求持有未过期租约。

BE-M0-T12 的迁移建立上表，但不加 `chapter` 外键：`chapter` 表属于 BE-M0-T13，现在还没有。

### 字典 v1.9 字段对照表

对照 [字典 v1.9](../reference/product/kb-data-dictionary-v1.9.md) 3.10.4.6 `edit_lock`，以及 3.0 节 A 组、C 组。PRD v1.8 第 5.7.12 节的 `edit_lock` 行与字典冲突时以字典 3.10 节为准。本卡只把演示里的当前租约写入 `chapter_lease`，不是字典全表。下表每一行偏差都需要项目经理批准；未批准前不改表、不补列。

| 表 | 字段 | 类型 | 必填 | 枚举 | 字典条目 | 对照 |
|---|---|---|---|---|---|---|
| `chapter_lease` | `chapter_id` | VARCHAR(120) | 是 | 无 | `edit_lock.node_id`，引用→`bid_outline_node`，必填 | 偏差。字典指向大纲节点。本表存演示章节 id，并作为主键，一章只留一行。字典是部分唯一：每个 `node_id` 只有一条 `released_at` 为空的记录。需要项目经理批准 |
| `chapter_lease` | `token` | VARCHAR(200)，`utf8mb4_bin` | 是 | 无 | 无对应列 | 偏差。演示租约令牌，用来续期和校验。字典 `edit_lock` 没有此列。需要项目经理批准 |
| `chapter_lease` | `owner_id` | VARCHAR(120) | 是 | 无 | `edit_lock.user_id`，引用→`sys_user`，可空 | 偏差。字典可空，空表示系统持锁。本表必填，存演示账号 id，没有 `sys_user`。需要项目经理批准 |
| `chapter_lease` | `session_token` | VARCHAR(200)，`utf8mb4_bin` | 是 | 无 | 无对应列 | 偏差。把租约绑到登录会话。字典没有此列。需要项目经理批准 |
| `chapter_lease` | `expires_at` | DATETIME(6) | 是 | 无 | `edit_lock.expires_at`，时间，系统填写 | 偏差。字典等于最近心跳加公司设置 `edit_lock_timeout_minutes`。本表在取得或续期时用应用时钟加 120 秒，没有心跳。需要项目经理批准 |
| `chapter_lease` | （未建） | — | — | 无 | `edit_lock.acquired_at`，时间，系统 | 偏差。取得时间没有单独的列。需要项目经理批准 |
| `chapter_lease` | （未建） | — | — | `loop_status`：`not_started` 未开始、`plan_pending` 大纲待确认、`ready` 待生成、`generating` 生成中、`checking` 检查中、`fixing` 修正中、`completed` 已完成、`pending_human` 待人工处理、`human_handled` 人工已处理、`interrupted` 异常中断 | `edit_lock.lock_reason`，代码〈`loop_status`〉，可空 | 偏差。系统持锁原因未入库。需要项目经理批准 |
| `chapter_lease` | （未建） | — | — | 无 | `edit_lock.heartbeat_at`，时间，系统 | 偏差。没有心跳列。心跳间隔见字典 `edit_lock_heartbeat_seconds`（示例 60 秒）。需要项目经理批准 |
| `chapter_lease` | （未建） | — | — | 无 | `edit_lock.taken_over_from_user_id`，引用→`sys_user`，条件必填 | 偏差。接管时的上一持有人写在内存审计里，不写本表。需要项目经理批准 |
| `chapter_lease` | （未建） | — | — | 无 | `edit_lock.takeover_reason`，文本(300)，条件必填 | 偏差。接管原因写在内存审计里，不写本表。需要项目经理批准 |
| `chapter_lease` | （未建） | — | — | 无 | `edit_lock.released_at`，时间，系统 | 偏差。释放是删行，不保留历史。需要项目经理批准 |
| `chapter_lease` | （未建） | — | — | `lock_release_reason`：`manual` 主动离开、`timeout` 超时、`taken_over` 被接管、`system` 系统持锁 | `edit_lock.release_reason`，代码〈`lock_release_reason`〉，系统 | 偏差。释放原因未入库。需要项目经理批准 |
| `chapter_lease` | （未建） | — | — | 无 | A 组 `id`、`created_by`、`created_at`、`updated_by`、`updated_at`、`record_version`、`is_deleted` | 偏差。演示租约没有审计列，也没有逻辑删除。需要项目经理批准 |
| `chapter_lease` | （未建） | — | — | 无 | C 组 `company_id`，引用→`company`，公司级表必填 | 偏差。演示数据没有公司隔离列。需要项目经理批准 |

原因：本卡只让现有 120 秒租约在另一个进程里仍能续期，过期后仍能被其他会话接管。字典里的历史锁、心跳、公司隔离和两套枚举留给后续聚合，不在本卡补列。

## 6. 其他聚合

这些表在实现轮次再写迁移。本方案只定边界，避免一次事务继续拷贝全部状态。

| 聚合 | 来源字段 | 写入范围 |
|---|---|---|
| 身份 | `accounts`、`sessions` | 登录会话写入 MySQL。任一 worker 都能用同一 token 认证；进程重启后 token 仍有效，直到被显式删除。现有演示登录没有过期时间，本方案不另加 |
| 项目 | `projects`、`project_teams` | 项目与成员 |
| 章节 | `chapters`、草稿、版本、`chapter_lease` | 正文、版本和租约 |
| 检查与导出 | `checks`、`exports` | 检查结果和导出快照 |
| 资料与承诺 | `library`、`sla_templates`、`library_revisions` | 公司资料和模板 |
| 工作流与任务 | `workflows`、`jobs` | 项目流程和异步任务 |
| 审计 | `audit` | 只追加 |
| 幂等 | `workflow_receipts` | 见第 4 节 |

登录会话对应现在的 `DemoState.sessions`：token 映射到 `user_id`。它和回执一样不能只活在一个进程里。

```sql
CREATE TABLE user_session (
  token VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  user_id VARCHAR(120) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (token),
  KEY idx_session_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

章节和项目保留 `revision`。更新使用 `UPDATE ... WHERE id = ? AND revision = ?`，受影响行数为 0 时返回现有版本冲突，不覆盖。

## 7. 从整份仓库拆到按聚合仓库

当前回调可以改 `DemoState` 的任意字段。不能第一步就换成 SQL，否则一次请求仍会读出全部表。

1. 列出每个 `transaction` 回调实际读写的字段。入口在 `domain.py`、`workflow.py`、`sla.py`。
2. 为第 6 节的每个聚合定义窄接口：按主键读取、按条件查询、在已打开的事务里保存。`MemoryRepository` 仍保存整份 `DemoState`，窄接口只是它上面的视图。
3. 一次只改一个聚合的回调，让它使用窄接口。单元测试继续走内存，行为保持不变。
4. 全部回调不再直接改整份状态之后，再增加 `MysqlRepository`。它实现同一组窄接口，在一个 SQLAlchemy `Session` 里提交。
5. `create_app` 仍默认内存仓库。只有显式配置内网连接时才使用 MySQL。该切换不属于本方案的实施范围。

## 8. 事务与并发

- 隔离级别使用 MySQL 默认的 `REPEATABLE READ`。
- 一次业务成功和对应回执插入要么一起提交，要么一起回滚。失败结果不插入回执。
- 同一幂等键并发时由主键挡住第二行。后到的事务读已提交行：指纹相同则重放，不同则 409。
- 同一章节的租约、草稿和提交使用 `SELECT ... FOR UPDATE` 锁住该章，避免两个会话同时接管。
- 应用不在事务外先读再写后假设没有别人改过。版本列和租约行锁是并发条件。
- SQL 日志默认关闭。不把正文、回执 JSON 或令牌打到日志。

## 9. 测试

单元测试继续使用 `MemoryRepository`，不需要数据库。原 `backend` 离线作业保持不连 MySQL。

集成测试使用镜像 `mysql:8.4`，库内只放合成种子数据。公司内网执行机仍可按下面的命令自行启动。ISSUE-025 另在托管运行器上启动同一镜像，只覆盖空迁移和现有 mysql 标记测试。

内网执行机在容器健康检查通过后执行：

```text
alembic -c backend/bid-core/alembic.ini upgrade head
```

连接只来自环境变量 `ICG_DATABASE_URL`，例如 `mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/icg_demo?charset=utf8mb4`。密码不进仓库。然后运行：

```text
ICG_REQUIRE_MYSQL=1 python -m pytest tests/backend -m mysql
```

`ICG_REQUIRE_MYSQL=1` 时，标记为 `mysql` 的测试在 `ICG_DATABASE_URL` 缺失或数据库连不上时失败，不能跳过。未设置该变量且没有连接串时，这些测试跳过，原 `backend` 作业仍然通过。ISSUE-025 另加并行作业 `backend-mysql`，在托管运行器上启动 `mysql:8.4` 并执行上述迁移和 pytest。该作业的密码运行时生成，不写入仓库。它不代替公司内网的集成测试。

实施后的集成测试还要覆盖：两个进程连接同一库时，一个进程写入的回执能被另一个进程重放；停掉进程再启动后，未过期回执仍可重放，已登录 token 仍可认证。本轮不跑这些测试。

## 10. 数据不出内网

- 不使用托管数据库、外部备份或驱动遥测。
- 连接地址只来自内网环境变量。
- 集成测试不携带真实投标、账号或正文。
- 原 `backend` 作业不设置连接串。ISSUE-025 的 `backend-mysql` 在托管运行器上使用 `mysql:8.4` 容器和合成库 `icg_demo`，不连接公司内网，也不使用托管数据库服务。
- 向量和模型调用仍按 ISSUE-010，不因业务库落地而改道到外网。

## 11. 仍未做

BE-M0-T11 为 in-review：幂等回执和登录会话已写入 MySQL，多个进程可见，重启后未过期数据仍在。BE-M0-T12 为 in-review：`chapter_lease` 已写入 MySQL，续期后占用者不变，过期后其他会话可以接管。迁移能 `downgrade base` 再 `upgrade head`。没有章节外键，字段与字典 v1.9 `edit_lock` 的偏差列在第 5 节，都需要项目经理批准。按聚合迁移（BE-M0-T13）仍未做。`MemoryRepository` 仍是未设置连接串时的仓库，也仍是已连接时的业务读写委托。旧 `/api` 错误体见 [ISSUE-021](../../issues/ISSUE-021.md)，本轮不实施。
