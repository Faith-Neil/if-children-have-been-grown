为什么有这个文件：说明 demo_project 项目表与数据字典 bid_project 对齐的技术实现、数据库迁移与接口兼容性设计。

它解决什么问题：对齐项目数据字典规范，补充招标类型、预算金额（分）、投标截止时间戳、保密等级、行业领域、归档标记及 A 组系统审计字段，确保增量 Alembic 迁移绝对保留已有历史项目数据，并保障 /api/v1/projects 与旧版接口向后兼容。

# BE-M0-T19：项目表 demo_project 对齐数据字典 bid_project 代码说明

## 1. 业务上下文与改动背景
在系统早期演进中，项目聚合在内存与 MySQL 中使用了精简结构 `demo_project`（BE-M0-T13）。对照项目知识库数据字典 v1.9 的 `bid_project` 定义，该表缺乏规范的业务属性字段（招标类型 `tender_type`、预算分 `budget_amount_cents`、投标截止时间戳 `deadline_at`、保密等级 `security_level`、行业领域 `industry`、归档状态 `is_archived`）以及企业级 A 组系统审计字段（`created_by`, `created_at`, `updated_by`, `updated_at`, `record_version`, `is_deleted`）。

本任务（关联 ISSUE-035、ISSUE-018，依赖 BE-M0-T13、BE-M0-T17）对项目表结构及领域模型进行标准化对齐，严格遵循无损迁移原则：**绝对保留已有历史项目记录，严禁清空旧数据**，并对对外接口提供完全向后兼容能力。

## 2. 核心代码变更与模型演进

### 2.1 领域模型 (Domain Model) 扩展
- **代码文件**：`backend/bid-core/icg_demo/domain.py`
- **模型定义**：
  ```python
  @dataclass
  class Project:
      id: str
      name: str
      company_id: str
      revision: int = 1
      tender_number: str = ""
      deadline: str = ""
      sensitive: bool = False
      tender_type: str = "comprehensive"
      budget_amount_cents: Optional[int] = None
      deadline_at: Optional[float] = None
      security_level: str = "internal"
      industry: str = "it"
      is_archived: bool = False
      created_by: Optional[str] = None
      created_at: Optional[float] = None
      updated_by: Optional[str] = None
      updated_at: Optional[float] = None
      record_version: int = 1
      is_deleted: bool = False

      @property
      def is_sensitive(self) -> bool:
          return self.sensitive

      @is_sensitive.setter
      def is_sensitive(self, value: bool) -> None:
          self.sensitive = bool(value)
  ```
- **关键设计**：
  - 新增 12 个规范字段并赋予合理默认值，确保历史仅使用 `Project(id, name, company_id)` 的实例化代码零破坏兼容。
  - 保留 `is_sensitive` 属性与 `sensitive` 属性的互通绑定，满足不同代码模块对敏感字段命名的诉求。
  - 在 `DemoService.create_project` 中，创建时自动记录 `created_by`、`created_at`（秒级时间戳）、`updated_by`、`updated_at` 和 `record_version=1`。
  - 在 `DemoService._project_response` 中，统一将浮点时间戳转换为 ISO 8601 标准字符串。
  - 在 `DemoService.projects` 和 `DemoService._project` 中加入 `not project.is_deleted` 校验，实现软删除隔离过滤。

### 2.2 Pydantic 响应契约 (Schemas) 扩展
- **代码文件**：`backend/bid-core/icg_demo/schemas.py`
- **模型定义**：
  ```python
  class ProjectResponse(BaseModel):
      id: str = Field(description="项目唯一ID")
      name: str = Field(description="项目名称")
      company_id: str = Field(description="所属公司ID")
      revision: int = Field(default=1, description="项目版本号")
      sensitive: bool = Field(default=False, description="是否涉密项目")
      is_sensitive: bool = Field(default=False, description="是否涉密项目（字典别名）")
      tender_number: str = Field(default="", description="招标编号")
      deadline: str = Field(default="", description="投标截止时间文本")
      tender_type: str = Field(default="comprehensive", description="招标类型：technical/business/comprehensive")
      budget_amount_cents: Optional[int] = Field(default=None, description="预算金额（分）")
      deadline_at: Optional[str] = Field(default=None, description="投标截止时间戳（ISO 8601）")
      security_level: str = Field(default="internal", description="保密级别：public/internal/secret")
      industry: str = Field(default="it", description="所属行业")
      is_archived: bool = Field(default=False, description="是否归档")
      created_by: Optional[str] = Field(default=None, description="创建人ID")
      created_at: Optional[str] = Field(default=None, description="创建时间")
      updated_by: Optional[str] = Field(default=None, description="更新人ID")
      updated_at: Optional[str] = Field(default=None, description="更新时间")
      record_version: int = Field(default=1, description="记录版本号")
      is_deleted: bool = Field(default=False, description="软删除标记")
  ```

### 2.3 数据库读写与双模式兼容持久化
- **代码文件**：`backend/bid-core/icg_demo/database.py`
- **实现细节**：
  - `_load_shared`: 执行 19 列 `SELECT id, name, ..., is_deleted FROM demo_project`，自动通过 `_parse_db_timestamp` 将 DATETIME(6) / 时间值转为 float。若底层环境处于未迁移旧版本，自动捕获异常并降级回历史 7 列查询。
  - `_project_snapshot`: 生成包含全部 18 列属性的元组快照，提供精准的脏检查和并发比对。
  - `_save_projects`: 支持解构 18 元组全量列和 <=6 元组旧快照；优先执行包含全部 19 列的 `INSERT` / `UPDATE`，失败时自动 fallback 到历史 7 列语句。
  - 提供 `_to_utc_naive` 帮助函数，兼容浮点时间戳与 naive UTC datetime 双向安全转换。

### 2.4 Alembic 增量无损迁移
- **代码文件**：`backend/bid-core/alembic/versions/0011_bid_project_alignment.py`
- **Revision 链条**：`0010_edit_lock_alignment` -> `0011_bid_project_alignment`
- **迁移逻辑**：
  - `upgrade()`: 执行 `ALTER TABLE demo_project ADD COLUMN ...`，为已有数据表增量添加 `tender_type`, `budget_amount_cents`, `deadline_at`, `security_level`, `industry`, `is_archived`, `created_by`, `created_at`, `updated_by`, `updated_at`, `record_version`, `is_deleted` 共 12 列。
  - 核心质量保证：不新建表名，不修改现有表的主键约束与表名基线（严格维持 `SHOW TABLES` 17 张表基线），绝不删除旧数据行。
  - `downgrade()`: 具备逆向 `DROP COLUMN` 撤销能力，保障迁移可安全回滚。

### 2.5 路由入口与契约同步
- **代码文件**：`backend/bid-core/icg_demo/main.py`
  - 挂载 `GET /api/v1/projects`（`operationId="listV1Projects"`，`v1_error_responses(401)`）。
  - 挂载 `GET /api/v1/projects/{project_id}`（`operationId="getV1Project"`，`v1_error_responses(401, 404)`）。
  - 挂载 `GET /api/projects/{project_id}`（`operationId="getProject"`，`error_responses(401, 404)`）。
  - 维持 `GET /api/projects`（`operationId="listProjects"`）与 `POST /api/projects`（`operationId="createProject"`）原有接口。
- **契约文件**：`spec/openapi/demo-v1.json`
  - 更新 paths 与 schemas，保留草案及已冻结状态，并通过 `implemented_contract(spec) == app.openapi()` 静态与运行时双重验证。

## 3. 自动化测试验证
- **测试文件**：`tests/backend/test_project_dictionary_alignment.py`
  1. `test_project_domain_model_defaults_and_properties`: 验证领域模型默认值、属性别名与向后兼容构造。
  2. `test_project_snapshot_and_database_persistence`: 验证 18 元组快照结构以及双模式写入能力。
  3. `test_alembic_migration_0011_file_structure`: 验证迁移版本链 `0010` -> `0011` 及 upgrade/downgrade 定义。
  4. `test_api_v1_and_legacy_projects_endpoints`: 验证 `GET /api/v1/projects`、`GET /api/v1/projects/{id}`、`GET /api/projects/{id}` 与旧版接口的数据返回与字段映射。
  5. `test_project_company_isolation_and_deleted_filtering`: 验证多租户跨公司访问 404 隔离与软删除过滤。
- **全量回归**：
  - `pytest tests/backend/test_project_dictionary_alignment.py tests/backend/test_operation_ids.py tests/backend/test_error_idempotency.py tests/backend/test_reference_flow.py`: 43 项测试全部通过（43 passed in 28.47s）。
