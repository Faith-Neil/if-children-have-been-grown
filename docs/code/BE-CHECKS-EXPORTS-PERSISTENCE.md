为什么有这个文件：说明 MySQL 8 检查与导出聚合持久化、JSON 快照与问题列表存储、状态机生命周期以及分页检索的代码实现与数据流。

它解决什么问题：将检查结果（合规与规范校验）和导出快照从单纯内存结构推进持久化至 MySQL 8，落地 `demo_check` 与 `demo_export` 表结构，支持阻塞项（blocking）强拦截、多维检索（按项目/分册/导出类型）、导出状态流转与文件元数据更新，并确保未配置数据库时透明降级至纯内存模式。

# MySQL 8 检查与导出聚合持久化代码说明

- **对应任务**：BE-CHECKS-EXPORTS-PERSISTENCE（[ISSUE-018](../../issues/ISSUE-018.md) 持久化推进阶段）
- **交付文档**：[BE-CHECKS-EXPORTS-PERSISTENCE.md](../delivery/BE-CHECKS-EXPORTS-PERSISTENCE.md)
- **依赖基线**：BE-CHAPTER-PERSISTENCE（章节聚合入库）、BE-M0-T13（项目聚合入库）
- **关键源文件**：
  - 迁移脚本：[0007_checks_and_exports.py](../../backend/bid-core/alembic/versions/0007_checks_and_exports.py)
  - 存储实现：[database.py](../../backend/bid-core/icg_demo/database.py)
  - 内存适配器：[adapters.py](../../backend/bid-core/icg_demo/adapters.py)
  - 自动化测试：[test_checks_exports_persistence.py](../../tests/backend/test_checks_exports_persistence.py)
  - 契约连接测试：[test_mysql_connection.py](../../tests/backend/test_mysql_connection.py)

---

## 1. 架构与数据表设计

依据 [《MySQL 8 持久化方案》](../architecture/mysql-8-persistence-plan.md) 第 6 节，检查与导出聚合包含合规性校验历史记录与投标文件生成导出快照。Alembic 迁移脚本 `0007_checks_and_exports.py` 建立了下列两张表，向下依赖 `0006_chapters`：

### 1.1 `demo_check`（检查结果主表）
| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(120) | NOT NULL, PRIMARY KEY | 检查批次标识（`chk-<uuid4>`） |
| `project_id` | VARCHAR(120) | NOT NULL, KEY `idx_check_project` | 所属项目标识 |
| `volume_id` | VARCHAR(120) | NULL | 关联分册标识（可空，空表示全项目综合检查） |
| `status` | VARCHAR(50) | NOT NULL | 状态（`passed` / `blocked` / `warning` / `pending`） |
| `blocking_count` | INT | NOT NULL, DEFAULT 0 | 阻断性严重问题数量 |
| `warning_count` | INT | NOT NULL, DEFAULT 0 | 告警性提示问题数量 |
| `issues_json` | JSON | NOT NULL | 结构化问题明细列表（JSON 数组） |
| `created_at` | DATETIME(6) | NOT NULL | 检查触发时间戳（微秒精度，UTC） |
| `updated_at` | DATETIME(6) | NOT NULL | 最后更新时间戳（微秒精度，UTC） |

- **存储引擎与编码**：`ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci`。
- **状态派生规则**：若调用方未显式指定 `status`，系统按严重程度自动派生：`blocking_count > 0` 派生为 `blocked`（拦截导出）；`warning_count > 0` 派生为 `warning`；否则为 `passed`。

### 1.2 `demo_export`（导出任务与快照主表）
| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(120) | NOT NULL, PRIMARY KEY | 导出任务标识（`exp-<uuid4>`） |
| `project_id` | VARCHAR(120) | NOT NULL, KEY `idx_export_project` | 所属项目标识 |
| `export_type` | VARCHAR(50) | NOT NULL | 导出类型（`submission` 递交版 / `internal` 内部审阅版） |
| `status` | VARCHAR(50) | NOT NULL | 任务状态（`pending` / `running` / `completed` / `failed`） |
| `format` | VARCHAR(20) | NOT NULL | 导出文件格式（`docx` / `pdf`） |
| `file_path` | VARCHAR(500) | NULL | 生成产物存储相对路径（完成后回填） |
| `file_size` | BIGINT | NULL | 产物字节大小（完成后回填） |
| `snapshot_json` | JSON | NULL | 导出时的项目与章节内容冰冻快照 |
| `created_by` | VARCHAR(120) | NOT NULL | 导出触发人账号标识 |
| `created_at` | DATETIME(6) | NOT NULL | 任务创建时间戳（微秒精度，UTC） |

- **支持操作**：完整的 `upgrade()` 与 `downgrade()` 支持（降级时删除 `demo_export` 与 `demo_check`，回退至 `0006_chapters`）。

---

## 2. 检查与导出持久化核心机制

在 [database.py](../../backend/bid-core/icg_demo/database.py) 中，提供窄接口持久化方法与仓库多态扩展：

### 2.1 检查批次操作接口
1. **保存检查结果** `save_check(target, check_data, updated_at=None)`：
   - 自动派生 `status`（若缺省）并序列化 `issues_json` 为 JSON 格式字符串。
   - 使用 MySQL `INSERT ... ON DUPLICATE KEY UPDATE` 实现原子 upsert，更新所有字段及 `updated_at`。
2. **读取检查详情** `read_check(target, check_id)`：
   - 单记录按主键读取，自动反序列化 `issues_json` 为 Python 结构化列表，若无则返回 `None`。
3. **按项目检索检查** `list_checks_by_project(target, project_id, volume_id=None, limit=50, offset=0)`：
   - 支持全项目查询及按 `volume_id`（如 `technical`、`business`）精确筛选。
   - 结果按 `created_at DESC` 降序排列，内置 `LIMIT` / `OFFSET` 分页控制。
4. **删除检查记录** `delete_check(target, check_id)`：
   - 根据主键删除记录，返回布尔值代表受影响行数是否大于 0。

### 2.2 导出任务操作接口
1. **创建导出任务** `save_export(target, export_data, updated_at=None)`：
   - 持久化导出任务初始元数据与冰冻快照 `snapshot_json`（含完整项目配置、分册、章节结构与版本）。
   - 使用 `INSERT ... ON DUPLICATE KEY UPDATE` 确保任务幂等创建与覆盖。
2. **读取导出任务** `read_export(target, export_id)`：
   - 获取导出任务信息，同时解出 `snapshot_json` 与 `snapshot` 供下游渲染使用。
3. **原子状态迁移** `update_export_status(target, export_id, status, file_path=None, file_size=None)`：
   - 动态构造更新语句，支持将状态流转至 `running`、`completed` 或 `failed`。
   - 当任务完成时，原子回填生成的 `file_path` 与 `file_size`。
4. **项目导出列表与分页** `list_exports_by_project(target, project_id, export_type=None, limit=50, offset=0)`：
   - 支持按 `export_type`（递交版 vs 内部稿）过滤。
   - 在单一逻辑中返回 `(items, total)` 元组，其中 `total` 代表匹配的总记录数，`items` 为分页结果。
5. **删除导出记录** `delete_export(target, export_id)`：
   - 根据主键删除导出记录，返回操作成功状态。

---

## 3. 内存降级与多态机制

为了保持与公网 CI、离线单元测试及本地开发环境的 100% 兼容：
- `backend/bid-core/icg_demo/adapters.py` 中的 [MemoryRepository](../../backend/bid-core/icg_demo/adapters.py) 实现了完全同名的 9 个 Check 与 Export CRUD 方法：
  - `save_check`、`read_check`、`list_checks_by_project`、`delete_check`
  - `save_export`、`read_export`、`update_export_status`、`list_exports_by_project`、`delete_export`
- 当未设置 `ICG_DATABASE_URL` 时，系统自动回退至纯内存运行，内部利用线程锁与深拷贝保障线程安全性与数据隔离，完全无需外部 MySQL 依赖。
