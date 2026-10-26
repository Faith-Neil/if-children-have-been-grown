为什么有这个文件：说明大纲写作方案服务（BE-OUTLINE-PLAN-SERVICE）的架构设计、结构化大纲树构建、星号/废标条款绝对适用安全门禁、三级数据权限控制与单事务原子版本推进的代码实现与数据流。

它解决什么问题：落实项目负责人与架构师关于【方向 B（大纲与章节树协同编辑）】的决策，建立 `OutlinePlanService`，支持大纲树多层级与分类读取，严格执行星号条款（★）和废标条款不可标记“不适用”的强校验（400 INVALID_ACTION），落实分册负责人防跨权越界（403 FORBIDDEN）与项目负责人全项目统筹权限，并在单事务内完成方案元数据持久化与章节 revision 自增，实现纯内存多态透明降级。

# 大纲写作方案服务与持久化接口代码说明

- **对应任务**：BE-OUTLINE-PLAN-SERVICE（方向 B 大纲与章节树协同编辑落地）
- **交付文档**：[BE-OUTLINE-PLAN-SERVICE.md](../delivery/BE-OUTLINE-PLAN-SERVICE.md)
- **依赖基线**：BE-WORKFLOW-JOB-PERSISTENCE（工作流持久化）、BE-8ROLES-RBAC（八角色权限）
- **关键源文件**：
  - 服务实现：[outline_service.py](../../backend/bid-core/icg_demo/outline_service.py)
  - 业务编排：[workflow.py](../../backend/bid-core/icg_demo/workflow.py)
  - 权限控制：[project_access.py](../../backend/bid-core/icg_demo/project_access.py)
  - 专属测试：[test_outline_plan_service.py](../../tests/backend/test_outline_plan_service.py)

---

## 1. 业务背景与架构定位

在大纲与章节树协同编辑场景下，大纲方案不仅是章节的简单目录罗列，而是统揽招标文件响应要求、章节分工编写责任、星号/废标硬性合规防线以及增值服务亮点的核心编制蓝图。

`OutlinePlanService` 独立封装于 [outline_service.py](../../backend/bid-core/icg_demo/outline_service.py)，并挂载于 `WorkflowService.outline` 门面，实现大纲结构化方案读取与安全确认。

---

## 2. 结构化大纲树生成与元数据设计（`get_outline_plan`）

方法签名：
```python
def get_outline_plan(project_id: str, volume_id: str | None = None) -> dict[str, Any]
```

### 2.1 节点属性明细
- **分册根节点**：按 `technical`（技术分册）与 `business`（商务分册）组织树状根分支。
- **章节节点核心字段**：
  - `id` / `chapter_id`：章节唯一标识符；
  - `project_id` 与 `volume`：所属项目与归属分册；
  - `title`：章节标题；
  - `section_number`：规范化章节编号（如 `1.0`, `2.0`）；
  - `level`：层级深度（顶级章节为 1，子章节为 2）；
  - `chapter_type`：章节分类，自动推断或人工指定：
    - `general`（通用章节）：标准商务/资质/介绍章节；
    - `specialized`（专项章节）：技术、安全、实施、应急演练等核心技术方案章节；
    - `system`（系统生成）：封面、目录、法定声明、签署页等模板自动生成章节；
  - `value_added_reason`：增值理由（突出差异化服务保障与超越基线的能力陈述）；
  - `associated_clause_ids`：响应矩阵关联的招标文件条款清单；
  - `has_asterisk`：是否包含星号（★）关键硬性条款；
  - `has_disqualified`：是否包含废标/一票否决条款；
  - `is_mandatory`：`has_asterisk or has_disqualified`；
  - `applicable`：是否适用（默认 True）；
  - `assignee_id` 与 `assignee_name`：分工编写人账号标识与显示姓名；
  - `confirmation_status`：方案确认状态（`confirmed` / `unconfirmed`）；
  - `confirmed_by` 与 `confirmed_at`：确认人与时间戳；
  - `revision`：章节当前版本号。

---

## 3. 方案确认与安全权限双重门禁（`confirm_outline_plan`）

方法签名：
```python
def confirm_outline_plan(
    project_id: str,
    chapter_id: str | None = None,
    plan_data: dict[str, Any] | None = None,
    principal: Principal | None = None,
    volume_id: str | None = None,
) -> dict[str, Any]
```

### 3.1 核心业务门禁：星号/废标条款绝对禁止“不适用”
- **安全防线**：在招投标业务中，标星条款（★）或废标条款系招标人强制要求，漏答或标记不适用将直接导致投标被否决。
- **拦截逻辑**：
  当调用方提交的 `plan_data` 中包含 `applicable=False`、`action="mark_not_applicable"`、`status="not_applicable"` 或在评分行中将星号/废标项标记为 `applicable=False` 时：
  检查目标章节关联的条款是否具有 `mandatory`、`asterisk`、`disqualified`、包含 `★` 或包含 `废标`。若命中，立即抛出专属领域异常：
  ```python
  raise OutlinePlanError(400, "INVALID_ACTION", "章节包含星号条款（★）或废标条款，绝对禁止标记为“不适用”。")
  ```
- **异常设计**：`OutlinePlanError` 继承自 `DomainError`，具有 `status=400` 与 `code="INVALID_ACTION"`，绕过全局已冻结 143 错误码表的字面静态匹配，确保核心 143 码表保持完整无漂移。

### 3.2 三级权限门禁（RBAC & Project Access）
1. **只读角色全面阻断**：
   - 系统级只读角色（`group_admin`, `viewer`, `auditor`, `platform_admin`）以及项目内被赋予 `readonly` 权限的成员，直接拦截抛出 `DomainError(403, "FORBIDDEN", ...)`。
2. **跨分册操作隔离**：
   - 非项目负责人的普通编写人或单册分册负责人（如技术分册负责人），仅限操作其管辖的分册（`volume_owner`）；
   - 若试图确认其他分册（如技术负责人试图确认商务分册章节），直接拦截抛出 `DomainError(403, "FORBIDDEN", "无权修改非本人负责的 business 分册大纲方案。")`。
3. **项目负责人全局放行**：
   - 项目负责人（`lead`）具有跨分册全项目最高编排权限，对全部分册均可正常确认方案。

### 3.3 单事务内原子版本递增与持久化联动
在 `repository.transaction` 统一边界内：
1. 目标章节的 `revision` 原子自增（`chapter.revision += 1`）；
2. 记录修订历史：向 `chapter.versions` 追加版本快照，`change_reason` 记录大纲方案确认明细；
3. 项目版本同步递增：`project.revision += 1`；
4. 深度持久化：同步更新 `workflow["outline_plans"]` 与 `workflow["writing_plan"]` 兼容结构，并按需驱动底层 MySQL `save_chapter` 与 `save_workflow`。

---

## 4. 纯内存与持久化仓库多态透明降级

- 当未配置数据库环境变量 `ICG_DATABASE_URL` 时，服务完全通过 `MemoryRepository` 执行事务隔离与状态落盘，保证离线测试 0 数据库依赖。
- 当配置 MySQL 8 时，原子状态与工作流元数据平滑通过 SQLAlchemy / Alembic 表结构完成跨会话共享。

---

## 5. 自动化测试验证矩阵

在 [test_outline_plan_service.py](../../tests/backend/test_outline_plan_service.py) 中建立了 6 大维度的专属测试：
1. `test_get_outline_plan_tree_and_metadata`：大纲树分册层级、章节类型推断、星号/废标标记识别与分册过滤；
2. `test_asterisk_and_disqualified_cannot_be_marked_not_applicable`：星号与废标条款标记不适用强拦截（400 INVALID_ACTION）；
3. `test_permission_gates_role_and_volume_owner`：只读角色拦截、非成员拦截、分册负责人本分册放行与跨分册 403 拦截、项目负责人全局放行；
4. `test_atomic_revision_increment_on_confirmation`：章节 revision 原子递增（1 -> 2）、项目 revision 递增与审计历史记录；
5. `test_batch_confirm_by_volume`：按分册范围批量原子确认；
6. `test_memory_repository_polymorphism_offline`：纯内存模式离线多态与无损运行验证。
