为什么有这个文件：说明 MySQL 8 工作流状态（demo_workflow）与异步任务（demo_job）聚合持久化、JSON 结构存储、状态推进流转、原子进度更新与并发乐观锁的代码实现与数据流。

它解决什么问题：将项目编制六阶段推进状态、增量复查队列及长耗时异步任务（文件解析、章节批量生成、合规复查、标书导出等）从内存推进持久化至 MySQL 8，落地两张核心表结构，基于 revision 提供强一致乐观并发锁（防止并发脏写冲突），支持跨进程共享与任务进度断点恢复，并确保未配置数据库时透明降级至纯内存模式。

# MySQL 8 工作流与异步任务聚合持久化代码说明

- **对应任务**：BE-WORKFLOW-JOB-PERSISTENCE（[ISSUE-018](../../issues/ISSUE-018.md) 持久化推进阶段）
- **交付文档**：[BE-WORKFLOW-JOB-PERSISTENCE.md](../delivery/BE-WORKFLOW-JOB-PERSISTENCE.md)
- **依赖基线**：BE-LIBRARY-SLA-PERSISTENCE（资料与承诺入库）、BE-CHECKS-EXPORTS-PERSISTENCE（检查与导出入库）
- **关键源文件**：
  - 迁移脚本：[0009_workflow_and_jobs.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/alembic/versions/0009_workflow_and_jobs.py)
  - 存储实现：[database.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/database.py)
  - 内存适配器：[adapters.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/adapters.py)
  - 自动化测试：[test_workflow_job_persistence.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/tests/backend/test_workflow_job_persistence.py)
  - 契约连接测试：[test_mysql_connection.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/tests/backend/test_mysql_connection.py)

---

## 1. 架构与数据表设计

依据 [《MySQL 8 持久化方案》](file:///c:/Users/徐佳馨/if-children-have-been-grown/docs/architecture/mysql-8-persistence-plan.md) 第 6 节，工作流与任务聚合包含项目六阶段推进主线、增量合规复查队列与跨进程异步执行任务。Alembic 迁移脚本 `0009_workflow_and_jobs.py` 建立了下列两张表，向下依赖 `0008_library_and_sla`：

### 1.1 `demo_workflow`（工作流主表）
| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `project_id` | VARCHAR(120) | NOT NULL, PRIMARY KEY | 归属投标项目主键标识（`proj-<id>`） |
| `current_stage` | VARCHAR(50) | NOT NULL | 当前编制阶段（`parsing` 解析、`matrix` 响应矩阵、`outline` 大纲、`drafting` 编写、`checking` 复查、`exporting` 导出） |
| `stages_json` | JSON | NOT NULL | 各阶段状态、准入准出检查与统计明细 JSON |
| `incremental_checks_json` | JSON | NOT NULL | 增量合规复查检查项队列明细 JSON |
| `revision` | INT | NOT NULL, DEFAULT 1 | 版本序号（用于乐观并发锁校验） |
| `updated_at` | DATETIME(6) | NOT NULL | 最后更新时间戳（微秒精度，UTC） |

- **存储引擎与编码**：`ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci`。

### 1.2 `demo_job`（异步任务主表）
| 列名 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | VARCHAR(120) | NOT NULL, PRIMARY KEY | 异步任务全局唯一标识（`job-<uuid4>`） |
| `job_type` | VARCHAR(50) | NOT NULL | 任务类型（`parse_tender`、`generate_chapter`、`compliance_check`、`export_document` 等） |
| `project_id` | VARCHAR(120) | NOT NULL, KEY `idx_job_project` | 关联项目标识（支持按项目检索索引） |
| `status` | VARCHAR(50) | NOT NULL | 任务生命周期状态（`pending`、`running`、`completed`、`failed`、`cancelled`） |
| `progress` | INT | NOT NULL, DEFAULT 0 | 任务进度百分比（0～100 整数） |
| `step_name` | VARCHAR(100) | NULL | 当前执行步骤/子阶段说明文本 |
| `error_json` | JSON | NULL | 失败异常详情 JSON（包含错误码、错误提示、是否可重试） |
| `result_json` | JSON | NULL | 执行成功产出物明细 JSON（文档标识、token消耗、指纹等） |
| `created_by` | VARCHAR(120) | NOT NULL | 创建人账号标识 |
| `created_at` | DATETIME(6) | NOT NULL | 创建时间戳（微秒精度，UTC） |
| `updated_at` | DATETIME(6) | NOT NULL | 最后更新时间戳（微秒精度，UTC） |

- **双向迁移支持**：`upgrade()` 依次创建两表，`downgrade()` 逆序安全删除，支持降级回滚至 `0008_library_and_sla`。

---

## 2. 工作流与异步任务持久化核心机制

在 [database.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/database.py) 中，提供窄接口持久化方法与仓库多态扩展：

### 2.1 工作流操作接口
1. **保存工作流** `save_workflow(target, workflow_data, expected_revision=None, updated_at=None)`：
   - 插入新记录或执行乐观并发更新。
   - 当传入 `expected_revision` 时，执行带乐观锁的更新：
     ```sql
     UPDATE demo_workflow
     SET current_stage = :current_stage,
         stages_json = CAST(:stages_json AS JSON),
         incremental_checks_json = CAST(:incremental_checks_json AS JSON),
         revision = :revision,
         updated_at = :updated_at
     WHERE project_id = :project_id AND revision = :expected_revision
     ```
     若受影响行数不为 1，立即抛出 HTTP 409 `DomainError(409, "REVISION_CONFLICT", "工作流已被其他会话更新，请刷新并核对最新版本。")`，彻底杜绝并发脏写。
2. **读取工作流详情** `read_workflow(target, project_id)`：
   - 按项目主键查询，自动将 `stages_json` 与 `incremental_checks_json` 反序列化为 Python 原生对象。
3. **删除工作流** `delete_workflow(target, project_id)`：
   - 按项目主键删除工作流记录。

### 2.2 异步任务操作接口
1. **保存异步任务** `save_job(target, job_data, updated_at=None)`：
   - 采用 `INSERT ... ON DUPLICATE KEY UPDATE` 原语原子创建或更新异步任务记录。
   - 支持结构化存储 `error_json` 与 `result_json`。
2. **读取异步任务详情** `read_job(target, job_id)`：
   - 按任务主键查询，反序列化结构化结果与错误数据。
3. **原子更新进度与状态** `update_job_progress(target, job_id, progress, status=None, step_name=None, error_json=None, result_json=None, updated_at=None)`：
   - 单次原子 SQL 更新执行进度的百分比（0..100），并可选择性推进生命周期状态（`running`/`completed`/`failed`）、当前步骤描述 `step_name` 以及挂载 `error_json` 或 `result_json`。
4. **按项目分页查询任务** `list_jobs_by_project(target, project_id, job_type=None, status=None, limit=50, offset=0)`：
   - 强制按 `project_id` 过滤，支持按 `job_type` 与 `status` 多维组合过滤。
   - 结果按 `updated_at DESC` 倒序排列，返回 `(jobs, total)` 分页元组。
5. **删除异步任务** `delete_job(target, job_id)`：
   - 按任务主键安全删除。

---

## 3. 内存仓库多态实现（MemoryRepository）

在 [adapters.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/adapters.py) 中，`MemoryRepository` 实现了与 MySQL 完全对称的接口方法：
- `save_workflow`：基于内存字典记录 `_workflow_records`，严格核对 `expected_revision`，不匹配抛出 409 `REVISION_CONFLICT`。
- `read_workflow` / `delete_workflow`：深拷贝快照返回，杜绝引用泄露。
- `save_job` / `read_job` / `update_job_progress` / `list_jobs_by_project` / `delete_job`：支持任务全生命周期流转、倒序排序与分页截断。
- 在无外部 MySQL 环境或 `ICG_DATABASE_URL` 缺失时，后端服务与自动化测试透明降级至纯内存多态运行。

---

## 4. 异常与边界处理

1. **并发版本冲突（409 REVISION_CONFLICT）**：
   - 任意试图跨版本更新 `demo_workflow` 的操作（如两名管理员同时推进阶段），均由行级乐观锁阻断，返回标准的 409 错误，要求客户端刷新后重试。
2. **任务失败安全捕获（error_json 记录）**：
   - 当任务在异步流式生成中因网关超时（`MODEL_TIMEOUT`）或模型不可用（`MODEL_UNAVAILABLE`）失败时，错误信息安全序列化存入 `error_json`，`status` 标记为 `failed`，提供可追溯诊断信息。
3. **字符集与 Emoji 支持**：
   - 全部文本与 JSON 字段均采用 `utf8mb4` 字符集，完整支持投标文件中的特殊符号、Emoji 与数学公式。
