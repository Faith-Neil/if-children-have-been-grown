为什么有这个文件：记录编辑台章节详情读取与段落结构接口（BE-CHAPTER-EDIT-DETAIL）的交付内容、测试结果与架构状态。

它解决什么问题：证实后端已实现编辑台深度联动所需的章节正文详情读取接口 `GET /api/v1/projects/{project_id}/chapters/{chapter_id}`，具备段落结构切分、引用依据关联、持锁/非持锁状态感知、星号与废标门禁识别、只读角色安全准入以及跨租户与跨项目隔离。

# BE-CHAPTER-EDIT-DETAIL：编辑台章节详情读取与段落结构接口交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-CHAPTER-EDIT-DETAIL |
| 代码解释 | 详见 [代码解释](../code/BE-CHAPTER-EDIT-DETAIL.md) |
| 验收 | 自动化测试套件 `pytest tests/backend/test_chapter_edit_detail.py` 覆盖正常章节详情获取、段落结构与 citations 匹配、星号与废标条款 is_mandatory 识别、持锁人与过期时间状态感知、只读角色（viewer）GET 成功且写操作 403 拦截、跨项目与跨公司隔离 404；OpenAPI 契约与 143 错误码全量回归 100% 通过。 |
| 项目进度 | BE-CHAPTER-EDIT-DETAIL 标为 in-review，绝不私自标 done；关联 ISSUE-007 保持 in-progress。 |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-22。
- 业务标准：PRD v1.8 §5.11 编辑台正文编辑与联动、§5.7 大纲写作方案。
- 关联问题：[ISSUE-007](../../issues/ISSUE-007.md)（项目主流程与编辑台协同）。
- 依赖前置：BE-CHAPTER-PERSISTENCE（章节聚合持久化）、BE-OUTLINE-PLAN-SERVICE（大纲写作方案服务）、BE-8ROLES-RBAC（八角色权限）。
- 交付状态：**in-review**（待主 Agent 与 QA 审查签署，严禁私自标 done 或关闭 Issue）。

## 2. 交付成果与变更清单

1. **接口定义与契约模型**（`backend/bid-core/icg_demo/workflow_schemas.py` & `backend/bid-core/icg_demo/workflow_routes.py`）：
   - 新增 `ParagraphDetail` 与 `ChapterEditDetail` 响应模型，显式定义：
     - `id`（章节 ID）
     - `project_id`（项目 ID）
     - `title`（章节标题）
     - `chapter_number`（规范化章节编号，如 `1.0`）
     - `outline_type`（大纲类型：`specialized` 专项 / `general` 通用 / `system` 系统生成）
     - `is_mandatory`（星号 ★ 或废标条款硬性标记）
     - `locked_by`（当前持锁用户 ID，无锁为 None）
     - `lock_expires_at`（锁过期时间戳 ISO 格式，无锁为 None）
     - `revision`（OCC 并发版本号）
     - `paragraphs`（段落对象数组，每项包含 `id`, `order`, `text`, `citations`, `created_at`, `updated_at`）
   - 在 `workflow_routes.py` 挂载 `GET /projects/{project_id}/chapters/{chapter_id}`，设置 `operation_id="getChapterEditDetail"`。
2. **业务编排与段落持久化辅助**（`backend/bid-core/icg_demo/workflow.py` & `backend/bid-core/icg_demo/database.py`）：
   - 在 `WorkflowService` 实现 `chapter_edit_detail` 方法；
   - 接入持锁感知算法：结合 `ChapterLock` 与 `ProjectLock` 状态；
   - 在 `database.py` 实现 `decompose_paragraphs` 段落切分与依据引用（`citations`）精准关联算法；
   - 优先支持使用已持久化的结构化段落 `workflow["chapter_paragraphs"]`。
3. **OpenAPI 规范同步**（`spec/openapi/demo-v1.json`）：
   - 同步加入 `/api/v1/projects/{project_id}/chapters/{chapter_id}` 路径定义与 `ChapterEditDetail` / `ParagraphDetail` 契约结构；
   - 完好保留已有冻结契约属性与 143 个冻结错误码，`test_error_idempotency.py` 与 `test_operation_ids.py` 全绿通过。
4. **自动化测试套件**（`tests/backend/test_chapter_edit_detail.py`）：
   - 覆盖 8 大核心维度：正常获取、段落与引用匹配、未登录 401、不存在章节 404、跨项目隔离 404、持锁人与释放状态感知、只读角色（viewer）GET 成功且写操作拦截 403、已存储结构化段落优先覆盖。
5. **文档与治理**：
   - 编写代码架构文档 `docs/code/BE-CHAPTER-EDIT-DETAIL.md`；
   - 编写交付文档 `docs/delivery/BE-CHAPTER-EDIT-DETAIL.md`；
   - 索引登记至 `docs/DOCUMENT_INDEX.md`（D-625～D-627）。

### 文件变更清单：
- `backend/bid-core/icg_demo/workflow_schemas.py`（修改）
- `backend/bid-core/icg_demo/workflow_routes.py`（修改）
- `backend/bid-core/icg_demo/workflow.py`（修改）
- `backend/bid-core/icg_demo/database.py`（修改）
- `spec/openapi/demo-v1.json`（修改）
- `tests/backend/test_chapter_edit_detail.py`（新增）
- `docs/code/BE-CHAPTER-EDIT-DETAIL.md`（新增）
- `docs/delivery/BE-CHAPTER-EDIT-DETAIL.md`（新增）
- `docs/DOCUMENT_INDEX.md`（更新登记）

## 3. 验收验证

- **章节详情专属单测**：
  - `pytest tests/backend/test_chapter_edit_detail.py -v` -> **8 passed in 4.23s**（100% 通过）。
- **OpenAPI 契约与 OperationId 校验**：
  - `pytest tests/backend/test_error_idempotency.py tests/backend/test_operation_ids.py -v` -> **14 passed in 7.04s**（143 错误码无漂移，全局 operationId 保持严格 lowerCamelCase 无冗余前缀）。
- **核心后端链路联合回归**：
  - `pytest tests/backend/test_error_idempotency.py tests/backend/test_operation_ids.py tests/backend/test_chapter_edit_detail.py tests/backend/test_outline_plan_service.py tests/backend/test_eight_roles_access.py tests/backend/test_recoverable_jobs.py` -> **43 passed in 12.41s**。
- **项目治理检查**：
  - `node scripts/check-project-governance.cjs`。
