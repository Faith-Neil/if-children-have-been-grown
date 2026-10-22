为什么有这个文件：说明 chapter_lease 租约数据结构与数据字典 v1.9 edit_lock 对齐的技术实现、数据库迁移与向下兼容保留理由。

它解决什么问题：对齐编辑锁数据字典规范，补充审计列、公司隔离标识、锁获取时间戳、心跳时间戳、接管原因与释放信息，同时确保迁移绝对保留已有租约记录，并保留 token 与 session_token 兼容演示前端。

# BE-M0-T17：chapter_lease 对齐字典 edit_lock 代码说明

## 1. 业务上下文与改动背景
在系统早期演进中，章节编辑锁在内存与数据库中使用了简化的租约结构 `chapter_lease`（BE-M0-T04、BE-M0-T12）。对照项目知识库数据字典 v1.9 的 `edit_lock` 定义，该表缺乏企业级多租户审计与生命周期跟踪字段（如取得时间、心跳时间、持锁理由、接管历史、释放原因、A 组系统审计字段、公司隔离标识与版本号）。

本任务（关联 ISSUE-032、ISSUE-018）对租约表及底层数据结构进行标准化对齐，同时严格遵循迁移规范：禁止清空或删除旧租约行，并提供向下兼容设计。

## 2. 核心代码变更与模型演进

### 2.1 领域模型 (Domain Model) 扩展
- **代码文件**：`backend/bid-core/icg_demo/domain.py`
- **模型定义**：
  ```python
  @dataclass
  class Lease:
      token: str
      owner_id: str = ""
      session_token: str = ""
      expires_at: float = 0.0
      acquired_at: float | None = None
      heartbeat_at: float | None = None
      lock_reason: str | None = None
      taken_over_from_user_id: str | None = None
      takeover_reason: str | None = None
      released_at: float | None = None
      release_reason: str | None = None
      company_id: str | None = None
      record_version: int = 1
      user_id: str | None = None

      def __post_init__(self):
          if self.user_id is not None and not self.owner_id:
              self.owner_id = self.user_id
          elif self.owner_id and self.user_id is None:
              self.user_id = self.owner_id
  ```
- **关键设计**：
  - 补充 `acquired_at`（锁获取时间戳）、`heartbeat_at`（最新心跳时间戳）、`lock_reason`、`taken_over_from_user_id`（前任持锁人）、`takeover_reason`（接管原因）、`released_at`（释放时间）、`release_reason`（释放原因）、`company_id`（公司隔离租户标识）、`record_version`（乐观锁版本号）。
  - `owner_id` 与 `user_id` 互为别名，保持与历史代码及字典命名的无缝兼容。
  - `_lease_response` 输出结构增强，向前端透出 `acquired_at` 与 `heartbeat_at` ISO 时间串，方便编辑器心跳感知。

### 2.2 数据库存储与快照对齐
- **代码文件**：`backend/bid-core/icg_demo/database.py`
- **实现细节**：
  - `_load_state`: 从 `chapter_lease` 读取记录时，动态判断列数，支持加载历史 4 列旧数据及对齐后的完整新列；时间型字段经 `_as_timestamp` 统一反序列化为 float 秒级时间戳。
  - `_save_leases`: 采用事务原子写入，构建包含全部对齐列的更新字典，并注入 A 组审计列（`created_by`, `created_at`, `updated_by`, `updated_at`, `record_version`, `is_deleted`）。若底层环境尚处于旧列结构，具备自动降级兼容能力。
  - `_lease_snapshot`: 生成包含 13 项元组属性的租约快照，支持精准脏检查与跨事务比对。

### 2.3 Alembic 增量迁移脚本
- **代码文件**：`backend/bid-core/alembic/versions/0010_edit_lock_alignment.py`
- **Revision 链条**：`0009_workflow_and_jobs` -> `0010_edit_lock_alignment`
- **迁移逻辑**：
  - `upgrade()`: 执行 `ALTER TABLE chapter_lease ADD COLUMN ...`，增量添加 `id`, `company_id`, `acquired_at`, `heartbeat_at`, `lock_reason`, `taken_over_from_user_id`, `takeover_reason`, `released_at`, `release_reason`, `created_by`, `created_at`, `updated_by`, `updated_at`, `record_version`, `is_deleted`。
  - 核心约束保证：绝不执行 `DROP TABLE`、`TRUNCATE` 或 `DELETE`，历史租约行 100% 完整保留。
  - `downgrade()`: 具备逆向 `DROP COLUMN` 撤销能力，支持迁移回退。

## 3. token 与 session_token 保留理由说明
字典 v1.9 原型设计偏向关系型外键约束，未定义客户端持锁凭据。但在分布式无状态 Web 服务与长连接心跳场景中：
1. **防跨端串锁与安全隔离**：用户在多端或同一浏览器多 Tab 打开同一章节时，必须使用唯一的 `lease_token` 进行鉴权；仅靠 `user_id` 无法防止用户自身另一标签页覆盖正在编辑的内容。
2. **多端前端兼容性**：现存前端模块（`frontend/web/src/editor/EditorPage.tsx`、`/demo` 交互页及单元测试）均以 `lease_token` 作为请求头或载荷发送续期与释放指令。
因此，保留 `token` 与 `session_token` 字段并在底层持久化，兼具字典审计规范与实际运行稳定性。

## 4. 自动化测试覆盖
- `tests/backend/test_error_idempotency.py` -> `test_chapter_lease_alignment_fields_and_persistence`:
  - 验证 `Lease` 领域模型全量对齐字段的赋值与属性别名机制；
  - 验证 `database._lease_snapshot` 对齐元组快照生成。
- `tests/backend/test_v1_lease.py` & `tests/backend/test_lease_review.py`:
  - 验证加锁、心跳续期、接管与释放的全流程回归，全部通过。
