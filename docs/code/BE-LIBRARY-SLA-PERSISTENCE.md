为什么有这个文件：说明 MySQL 8 公司资料库（demo_library_item）、修订历史（demo_library_revision）与服务承诺模板（demo_sla_template）聚合持久化、JSON 结构存储、状态流转与并发乐观锁的代码实现与数据流。

它解决什么问题：将企业资质、人员、业绩等知识库资料、SLA服务承诺模板及不可变修订历史从内存推进持久化至 MySQL 8，落地三张核心表结构，基于 revision 提供强一致乐观并发锁（防止并发脏写冲突），在单一事务内原子提交修订履历，并确保未配置数据库时透明降级至纯内存模式。

# MySQL 8 公司资料与承诺聚合持久化代码说明

- **对应任务**：BE-LIBRARY-SLA-PERSISTENCE（[ISSUE-018](../../issues/ISSUE-018.md) 持久化推进阶段）
- **交付文档**：[BE-LIBRARY-SLA-PERSISTENCE.md](../delivery/BE-LIBRARY-SLA-PERSISTENCE.md)
- **依赖基线**：BE-CHECKS-EXPORTS-PERSISTENCE（检查与导出入库）、BE-CHAPTER-PERSISTENCE（章节聚合入库）
- **关键源文件**：
  - 迁移脚本：[0008_library_and_sla.py](../../backend/bid-core/alembic/versions/0008_library_and_sla.py)
  - 存储实现：[database.py](../../backend/bid-core/icg_demo/database.py)
  - 内存适配器：[adapters.py](../../backend/bid-core/icg_demo/adapters.py)
  - 自动化测试：[test_library_sla_persistence.py](../../tests/backend/test_library_sla_persistence.py)
  - 契约连接测试：[test_mysql_connection.py](../../tests/backend/test_mysql_connection.py)

---

## 1. 架构与数据表设计

依据 [《MySQL 8 持久化方案》](../architecture/mysql-8-persistence-plan.md) 第 6 节，资料与承诺聚合包含企业知识库资料条目、修订历史履历与 SLA 服务承诺模板。Alembic 迁移脚本 `0008_library_and_sla.py` 建立了下列三张表，向下依赖 `0007_checks_and_exports`：

### 1.1 `demo_library_item`（资料条目主表）
| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(120) | NOT NULL, PRIMARY KEY | 资料条目标识（`lib-<uuid4>`） |
| `company_id` | VARCHAR(120) | NOT NULL, KEY `idx_lib_company` | 归属公司多租户隔离标识 |
| `category` | VARCHAR(50) | NOT NULL | 分类（`qualification`, `person`, `case`, `financial`, `compliance`, `tools`, `attachments`） |
| `name` | VARCHAR(300) | NOT NULL | 资料名称/标题 |
| `status` | VARCHAR(50) | NOT NULL | 状态（`confirmed` 已确认 / `draft` 草稿 / `expired` 已过期 / `restricted` 受限） |
| `is_starred` | TINYINT(1) | NOT NULL, DEFAULT 0 | 是否标星核心关键条目 |
| `can_insert` | TINYINT(1) | NOT NULL, DEFAULT 1 | 是否允许直接插入标书正文 |
| `is_sensitive` | TINYINT(1) | NOT NULL, DEFAULT 0 | 是否包含涉密/敏感信息 |
| `payload_json` | JSON | NOT NULL | 结构化数据明细（证书编号、签发机构、有效期等） |
| `revision` | INT | NOT NULL, DEFAULT 1 | 版本序号（用于乐观并发锁校验） |
| `created_at` | DATETIME(6) | NOT NULL | 创建时间戳（微秒精度，UTC） |
| `updated_at` | DATETIME(6) | NOT NULL | 最后更新时间戳（微秒精度，UTC） |

- **存储引擎与编码**：`ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci`。

### 1.2 `demo_sla_template`（SLA服务承诺模板主表）
| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(120) | NOT NULL, PRIMARY KEY | 模板标识（`sla-<uuid4>`） |
| `company_id` | VARCHAR(120) | NOT NULL, KEY `idx_sla_company` | 归属公司标识 |
| `level` | VARCHAR(20) | NOT NULL | 保障等级（`gold` 金牌 / `silver` 银牌 / `standard` 标准） |
| `name` | VARCHAR(200) | NOT NULL | 模板名称 |
| `rules_json` | JSON | NOT NULL | 服务承诺指标规则与变量明细 JSON |
| `revision` | INT | NOT NULL, DEFAULT 1 | 版本号（乐观并发锁） |
| `created_at` | DATETIME(6) | NOT NULL | 创建时间戳（微秒精度，UTC） |
| `updated_at` | DATETIME(6) | NOT NULL | 最后更新时间戳（微秒精度，UTC） |

### 1.3 `demo_library_revision`（资料修订不可变历史表）
| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(120) | NOT NULL, PRIMARY KEY | 修订历史记录标识（`rev-<uuid4>`） |
| `item_id` | VARCHAR(120) | NOT NULL, KEY `idx_lib_rev_item` | 关联资料条目标识 |
| `version_number` | INT | NOT NULL | 修订版本序号（对应递增 revision） |
| `payload_json` | JSON | NOT NULL | 该版本快照明细 JSON |
| `changed_by` | VARCHAR(120) | NOT NULL | 提交修订的操作人账号标识 |
| `change_reason` | VARCHAR(500) | NULL | 本次核对/修订依据说明 |
| `created_at` | DATETIME(6) | NOT NULL | 修订提交时间戳（微秒精度，UTC） |

- **双向迁移支持**：`upgrade()` 依次创建三表，`downgrade()` 逆序安全删除，支持降级回滚至 `0007_checks_and_exports`。

---

## 2. 资料与承诺持久化核心机制

在 [database.py](../../backend/bid-core/icg_demo/database.py) 中，提供窄接口持久化方法与仓库多态扩展：

### 2.1 资料条目操作接口
1. **保存资料条目** `save_library_item(target, item_data, expected_revision=None, updated_at=None)`：
   - 插入新记录或执行乐观并发更新。
   - 当传入 `expected_revision` 时，执行带乐观锁的更新：
     ```sql
     UPDATE demo_library_item
     SET company_id = :company_id, category = :category, name = :name,
         status = :status, is_starred = :is_starred, can_insert = :can_insert,
         is_sensitive = :is_sensitive, payload_json = CAST(:payload_json AS JSON),
         revision = :revision, updated_at = :updated_at
     WHERE id = :id AND revision = :expected_revision
     ```
     若受影响行数不为 1，立即抛出 HTTP 409 `DomainError(409, "REVISION_CONFLICT", "资料已被其他会话更新，请刷新并核对最新版本。")`，彻底杜绝并发脏写。
2. **读取资料详情** `read_library_item(target, item_id)`：
   - 单条记录读取，自动将 `payload_json` 反序列化为 Python 字典。
3. **按公司与分类分页检索** `list_library_items(target, company_id, category=None, status=None, limit=50, offset=0)`：
   - 强制按 `company_id` 租户隔离，支持按 `category` 与 `status` 多条件过滤。
   - 结果按 `updated_at DESC` 排序，返回 `(items, total)` 元组。
4. **删除资料条目** `delete_library_item(target, item_id)`：
   - 级联删除该资料的修订履历 `demo_library_revision` 及主表记录。

### 2.2 资料修订版本原子提交 `commit_library_revision`
- 针对资料换证、年审或实质内容变更场景，在单一数据库事务内完成：
  1. 乐观锁更新 `demo_library_item` 的 `payload_json`、`revision`（推进至 `new_revision`）与 `updated_at`；检查受影响行数必须为 1，否则回滚并抛出 409 `REVISION_CONFLICT`。
  2. 向 `demo_library_revision` 插入不可变修订历史行，归档 `version_number`、`payload_json`、`changed_by`、`change_reason`。
- **查询修订历史** `list_library_revisions(target, item_id)`：按 `version_number ASC` 返回完整版本演进树。

### 2.3 SLA 服务承诺模板接口
1. **保存 SLA 模板** `save_sla_template(target, template_data, expected_revision=None, updated_at=None)`：
   - 录入金牌/银牌/标准承诺模板，支持基于 `expected_revision` 的乐观并发控制。
2. **读取 SLA 模板** `read_sla_template(target, template_id)`：
   - 读取模板元数据与 `rules_json` 指标。
3. **按公司与等级检索** `list_sla_templates(target, company_id, level=None)`：
   - 严格按公司隔离并按级别检索。
4. **删除 SLA 模板** `delete_sla_template(target, template_id)`：
   - 根据主键删除模板。

---

## 3. 内存降级与多态机制

在 [adapters.py](../../backend/bid-core/icg_demo/adapters.py) 的 `MemoryRepository` 中，以完全相同的签名和语义实现了上述 10 项 CRUD 接口：
- 内存模式下使用线程安全锁，并对 `expected_revision` 进行严格的比对校验（版本不匹配时抛出同样的 409 `REVISION_CONFLICT`）。
- 修订历史存储在内部的 `_lib_revisions_map` 中，保持完整版本追踪能力。
- 未设置 `ICG_DATABASE_URL` 时，系统 100% 透明运行在内存模式，确保开发与测试环境无缝平滑。
