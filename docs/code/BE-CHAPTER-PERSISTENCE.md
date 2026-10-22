为什么有这个文件：说明 MySQL 8 章节聚合持久化、章节版本历史存储以及乐观锁并发控制的代码实现与数据流。

它解决什么问题：将章节正文与版本历史从内存存储推进持久化到 MySQL 8，采用乐观并发控制阻止并发覆盖，并在同一事务内提交版本与正文，失败原子回滚；同时确保未配置数据库时透明降级至纯内存模式。

# MySQL 8 章节聚合持久化与版本乐观锁代码说明

- **对应任务**：BE-CHAPTER-PERSISTENCE（[ISSUE-018](../../issues/ISSUE-018.md) 持久化推进阶段）
- **交付文档**：[BE-CHAPTER-PERSISTENCE.md](../delivery/BE-CHAPTER-PERSISTENCE.md)
- **依赖基线**：BE-M0-T13（项目聚合入库）、BE-M0-T12（编辑租约入库）
- **关键源文件**：
  - 迁移脚本：[0006_chapters.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/alembic/versions/0006_chapters.py)
  - 存储实现：[database.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/database.py)
  - 内存适配器：[adapters.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/adapters.py)
  - 自动化测试：[test_chapter_persistence.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/tests/backend/test_chapter_persistence.py)
  - 契约连接测试：[test_mysql_connection.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/tests/backend/test_mysql_connection.py)

---

## 1. 架构与数据表设计

依据 [《MySQL 8 持久化方案》](file:///c:/Users/徐佳馨/if-children-have-been-grown/docs/architecture/mysql-8-persistence-plan.md) 第 6 节，章节聚合包含章节最新状态和历史版本记录。Alembic 迁移脚本 `0006_chapters.py` 建立了下列两张表，向下依赖 `0005_model_config`：

### 1.1 `demo_chapter`（章节主表）
| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(120) | NOT NULL, PRIMARY KEY | 章节标识 |
| `project_id` | VARCHAR(120) | NOT NULL, KEY `idx_demo_chapter_project` | 所属项目标识 |
| `volume` | VARCHAR(30) | NOT NULL | 分册类型（`technical` / `business`） |
| `title` | VARCHAR(300) | NOT NULL | 章节标题 |
| `content` | LONGTEXT | NOT NULL | 章节当前最新正文 |
| `revision` | INT | NOT NULL, DEFAULT 1 | 章节版本号（用于乐观锁校验） |
| `assignee_id` | VARCHAR(120) | NULL | 当前被指派的编写人账号标识 |
| `updated_at` | DATETIME(6) | NOT NULL | 最后更新时间戳（微秒精度，UTC） |

- **存储引擎与编码**：`ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci`。
- **外键约束**：依据架构方案约定，MVP 阶段暂不添加指向 `demo_project` 或 `chapter` 的物理外键，避免跨聚合级联锁与装配干扰。

### 1.2 `demo_chapter_version`（章节历史版本表）
| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(120) | NOT NULL, PRIMARY KEY | 版本记录标识（`ver-<uuid4>`） |
| `chapter_id` | VARCHAR(120) | NOT NULL, KEY `idx_demo_chapter_version_chapter` | 关联章节标识 |
| `version_number` | INT | NOT NULL | 版本序号（递增，对应 revision） |
| `content` | LONGTEXT | NOT NULL | 该历史版本的快照正文 |
| `created_by` | VARCHAR(120) | NOT NULL | 提交该版本的账号标识 |
| `created_at` | DATETIME(6) | NOT NULL | 版本创建时间戳（微秒精度，UTC） |

- **支持操作**：完整的 `upgrade()` 与 `downgrade()` 支持（降级时先删除 `demo_chapter_version`，再删除 `demo_chapter`）。

---

## 2. 章节聚合持久化核心机制

在 [database.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/database.py) 中，提供窄接口持久化方法与仓库多态扩展：

### 2.1 章节读取 `read_chapter(target, chapter_id)`
- 从 `demo_chapter` 读取章节基本信息与最新正文。
- 从 `demo_chapter_version` 按 `version_number ASC` 级联查询出所有版本历史快照。
- 若不存在返回 `None`；若存在返回包含 `id`, `project_id`, `volume`, `title`, `content`, `revision`, `assignee_id`, `updated_at`, `versions` 的完整字典。

### 2.2 章节写入 `save_chapter(target, chapter, expected_revision=None, updated_at=None)`
- 接受 `Chapter` 领域实体或字典。
- 章节不存在时，执行 `INSERT INTO demo_chapter`。
- 章节已存在时：
  - 若传入 `expected_revision`，执行带乐观锁校验的更新：
    ```sql
    UPDATE demo_chapter
    SET project_id = :project_id, volume = :volume, title = :title,
        content = :content, revision = :revision, assignee_id = :assignee_id,
        updated_at = :updated_at
    WHERE id = :id AND revision = :expected_revision
    ```
    受影响行数不为 1 时，立即抛出 HTTP 409 `DomainError(409, "REVISION_CONFLICT", "章节已被其他会话更新，请刷新并核对最新版本。")`。
  - 若未传入 `expected_revision`，直接更新当前记录。
- 幂等同步章节随带的 `versions` 到 `demo_chapter_version` 表中未写入的历史版本。

### 2.3 版本并发提交与乐观锁 `commit_chapter_version`
针对正文提交新版本场景，在单一数据库事务内完成：
```python
def commit_chapter_version(target, chapter_id: str, content: str, expected_revision: int,
                           new_revision: int, created_by: str, updated_at: datetime | None = None) -> dict:
    ...
    # 1. 执行乐观锁原子更新
    result = connection.execute(
        text(
            "UPDATE demo_chapter SET content = :content, revision = :new_rev, updated_at = :updated_at "
            "WHERE id = :id AND revision = :old_rev"
        ),
        {"id": chapter_id, "content": content, "new_rev": int(new_revision), "old_rev": int(expected_revision), "updated_at": now},
    )
    if result.rowcount != 1:
        raise DomainError(409, "REVISION_CONFLICT", "章节已被其他会话更新，请刷新并核对最新版本。")

    # 2. 在同一事务中插入版本历史快照
    version_id = f"ver-{uuid4().hex}"
    connection.execute(
        text(
            "INSERT INTO demo_chapter_version (id, chapter_id, version_number, content, created_by, created_at) "
            "VALUES (:id, :chapter_id, :version_number, :content, :created_by, :created_at)"
        ),
        {"id": version_id, "chapter_id": chapter_id, "version_number": int(new_revision),
         "content": content, "created_by": created_by, "created_at": now},
    )
    return {...}
```
- **原子性保障**：若版本插入失败或外层事务发生异常，数据库事务自动回滚，`demo_chapter` 正文与版本号均不受脏写污染。
- **并发冲突拦截**：当两个工作进程持有相同 `expected_revision` 并发提交时，后到的事务受影响行数为 0，立即触发 409 `REVISION_CONFLICT`，彻底阻止静默覆盖。

---

## 3. 内存模式多态纯洁性保障

系统必须保证在未配置 `ICG_DATABASE_URL` 时，默认以纯内存模式正常工作：
- [adapters.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/adapters.py) 中的 `MemoryRepository` 实现了与 `MysqlConnectionRepository` 相同的接口规范：
  - `read_chapter(chapter_id)`
  - `save_chapter(chapter, expected_revision=None, updated_at=None)`
  - `commit_chapter_version(chapter_id, content, expected_revision, new_revision, created_by, updated_at=None)`
- 内存模式同样实现乐观锁校验：在并发调用 `commit_chapter_version` 时，检查 `chapter.revision != expected_revision` 并抛出 `DomainError(409, "REVISION_CONFLICT")`。
- 本地与 CI 环境在未连接数据库时，所有 498 项后端单元测试全部顺利通过，零外部数据库依赖。

---

## 4. 跨进程状态装配与共享

在 [database.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/database.py) 的 `_load_shared` 中增加章节及版本装配：
- 任何工作进程在执行 `read()` 或 `transaction()` 时，自动查询 `demo_chapter` 与 `demo_chapter_version`，将数据库中已持久化的章节叠加到内存工作状态中。
- 保留未改动种子章节的就地机制，保持与项目聚合相同的轻量设计，避免空启动时将整个演示状态刷入数据库。

---

## 5. 验证与回归覆盖

在 [test_chapter_persistence.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/tests/backend/test_chapter_persistence.py) 中覆盖：
1. `test_chapter_save_and_read`：章节保存与读取，字段与编码严格核对。
2. `test_chapter_version_commit_in_same_transaction`：在同一事务中提交版本，正文更新与历史版本行同时落库。
3. `test_optimistic_locking_prevents_stale_revision_overwrite`：乐观并发更新拦截，旧版本覆盖被拒并抛出 409 `REVISION_CONFLICT`。
4. `test_transaction_failure_rolls_back_chapter_and_versions`：事务发生异常时，原子回滚章节正文及版本历史，不留孤儿数据。
5. `test_alembic_downgrade_base_and_upgrade_head_roundtrip`：Alembic 迁移脚本回滚至 base 后完整升回 head，验证表结构与排序规则 `utf8mb4_0900_ai_ci`。
6. `test_memory_repository_polymorphism_and_optimistic_locking`：验证内存模式多态纯洁性与乐观锁一致性。
