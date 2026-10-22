为什么有这个文件：说明编辑台章节详情读取与段落结构接口（BE-CHAPTER-EDIT-DETAIL）的架构设计、接口契约、段落与引用关联算法、持锁状态感知与八角色权限控制。

它解决什么问题：配合前端 OutlineTreeView 与 EditorPage 章节正文加载，提供结构化、包含完备段落对象（带编号、引用列表、时间戳）与 OCC 乐观并发版本号的章节详情读取接口，并在服务端实现无锁/持锁状态感知、星号与废标门禁识别、只读角色准入与跨项目隔离。

# BE-CHAPTER-EDIT-DETAIL：编辑台章节详情读取与段落结构接口代码说明

- **对应任务**：BE-CHAPTER-EDIT-DETAIL（编辑台章节详情读取与段落结构接口）
- **交付文档**：[BE-CHAPTER-EDIT-DETAIL.md](../delivery/BE-CHAPTER-EDIT-DETAIL.md)
- **依赖基线**：BE-CHAPTER-PERSISTENCE（章节聚合持久化）、BE-OUTLINE-PLAN-SERVICE（大纲写作方案服务）、BE-8ROLES-RBAC（八角色权限）
- **关键源文件**：
  - 路由定义：[workflow_routes.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/workflow_routes.py)
  - 契约模型：[workflow_schemas.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/workflow_schemas.py)
  - 业务编排：[workflow.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/workflow.py)
  - 持久化辅助：[database.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/database.py)
  - 自动化测试：[test_chapter_edit_detail.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/tests/backend/test_chapter_edit_detail.py)

---

## 1. 业务背景与架构定位

在招投标文档协同编制中，前端编辑台（`EditorPage`）与大纲协同树（`OutlineTreeView`）需要实时展示当前选中章节的正文内容、段落细节结构、引用依据、当前持锁人状态以及版本号。

本接口作为编辑台章节加载的核心入口：
1. 统一接入 `/api/v1/projects/{project_id}/chapters/{chapter_id}` 规范路由；
2. 承载 OCC（Optimistic Concurrency Control）乐观锁基准版本号（`revision`）；
3. 结构化解析段落（`paragraphs`）与依据引用（`citations`）；
4. 提供持锁人与锁租约到期时间感知；
5. 实施只读角色（`viewer` / `auditor`）放行 GET 但阻断写入的权限矩阵，以及跨项目和跨公司的数据隔离。

---

## 2. 接口契约与数据模型

### 2.1 路由契约
- **请求方式**：`GET`
- **路径**：`/api/v1/projects/{project_id}/chapters/{chapter_id}`
- **OperationId**：`getChapterEditDetail`
- **认证**：Bearer Token 会话鉴权（`Principal`）

### 2.2 响应字段明细（`ChapterEditDetail`）
| 字段名 | 类型 | 说明 |
|---|---|---|
| `id` | `str` | 章节唯一标识符（chapter_id） |
| `project_id` | `str` | 所属项目 ID |
| `title` | `str` | 章节标题 |
| `chapter_number` | `str` | 规范化章节编号（如 `1.0`, `2.1`），优先读取大纲方案 section_number |
| `outline_type` | `str` | 大纲章节类型（`specialized` 专项 / `general` 通用 / `system` 系统生成） |
| `is_mandatory` | `bool` | 是否包含星号条款（★）或废标一票否决条款 |
| `locked_by` | `str \| None` | 当前持有有效编辑锁的用户 ID（若未加锁或锁已过期则为 `None`） |
| `lock_expires_at` | `str \| None` | 编辑锁到期时间戳（ISO 格式字符串，无锁时为 `None`） |
| `revision` | `int` | 当前章节版本号（OCC 并发控制基准，提交保存与版本固化时校验） |
| `paragraphs` | `list[ParagraphDetail]` | 结构化段落对象列表 |
| `volume` | `str \| None` | 归属分册（`technical` / `business`） |
| `can_edit` | `bool` | 当前登录用户对本章节是否具备编辑权限 |
| `permissions` | `dict[str, bool]` | 细粒度操作权限（`edit`, `confirm_plan`, `generate` 等） |

### 2.3 段落对象模型（`ParagraphDetail`）
| 字段名 | 类型 | 说明 |
|---|---|---|
| `id` | `str` | 段落唯一标识符（如 `{chapter_id}-p{order}`） |
| `order` | `int` | 段落序号（从 1 开始递增） |
| `text` | `str` | 段落纯文本正文内容 |
| `citations` | `list[dict]` | 该段落引用的依据资料/证书/业绩条款列表 |
| `created_at` | `str` | 段落初次创建时间戳（ISO 格式） |
| `updated_at` | `str` | 段落最近修订时间戳（ISO 格式） |

---

## 3. 段落切分与引用关联算法

在 [database.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/database.py) 与 [workflow.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/backend/bid-core/icg_demo/workflow.py) 中实现双层段落解析机制：

1. **优先读取已持久化结构化段落**：
   若工作流中存在用户或生成服务自定义持久化的 `workflow["chapter_paragraphs"][chapter_id]`，则保持其原子定义完整输出。
2. **正文动态解析与依据命中匹配（`decompose_paragraphs`）**：
   - 将 `chapter.content` 标准化换行并提取非空段落块；
   - 汇集该章节所有历史版本快照中的 `citation` 与对应招标文件条款关联的 `evidence_ids`；
   - 根据段落中出现的引用标识（如 `[证:cert-01]`）、证据条目 ID、条目名称或引用文本进行精准子串命中归属；
   - 保留首个版本与最新版本的审计时间戳（`created_at` 与 `updated_at`）。

---

## 4. 持锁状态感知机制

编辑锁感知结合章节级（`ChapterLock`）与项目级（`ProjectLock`）状态：
1. 校验当前章节上的租约 `chapter.lock` 是否存在且 `expires_at > now`；
2. 若处于有效持锁期内：
   - `locked_by` 回填 `chapter.lock.owner_id`；
   - `lock_expires_at` 回填 `iso_time(chapter.lock.expires_at)`；
3. 若无章节锁或章节锁已过期，则进一步检查工作流级 `project_lock`；若项目级锁有效，回填项目持锁人；
4. 若均无有效锁，`locked_by` 与 `lock_expires_at` 严格置为 `None`。

---

## 5. 数据权限与涉密隔离

1. **八角色权限规范（PRD v1.8 §2.2 & §2.3）**：
   - 系统只读角色（`viewer`, `auditor`, `group_admin`, `platform_admin`）以及项目内 `readonly` 成员**允许调用 GET 获取章节详情**；
   - 在返回结果中明确声明 `can_edit=False` 与 `permissions["edit"]=False`；
   - 只读角色任何试图发起加锁（`acquire_lock`）、草稿保存（`saveDraft`）或提交版本（`commitVersion`）的请求均被阻断拦截并抛出 403 `FORBIDDEN`。
2. **涉密项目隔离（Project Sensitivity）**：
   - 敏感项目（`project.sensitive=True`）成员正常调阅正文；若涉及外部云端模型则按已有门禁强阻断。
3. **租户与项目越权阻断**：
   - 跨公司访问：若登录账号所属公司与项目归属公司不一致，直接抛出 404 `NOT_FOUND`；
   - 跨项目隔离：若指定 `chapter_id` 不属于 URL 中的 `project_id`，直接抛出 404 `NOT_FOUND`（"章节不属于当前项目。"）；
   - 资源不存在：章节或项目不存在时统一抛出 404 `NOT_FOUND`。

---

## 6. 自动化测试验证矩阵

在 [test_chapter_edit_detail.py](file:///c:/Users/徐佳馨/if-children-have-been-grown/tests/backend/test_chapter_edit_detail.py) 中包含 8 项核心自动化测试：
1. `test_get_chapter_edit_detail_success`：正常获取章节详情、完整顶级元数据与段落数组；
2. `test_get_chapter_edit_detail_paragraphs_and_citations`：正文多段落切分、星号条款 `is_mandatory` 识别、段落 order/id/时间戳与 citations 引用匹配；
3. `test_unauthenticated_returns_401`：未携带 Token 拦截 401 UNAUTHENTICATED；
4. `test_non_existent_chapter_and_project_returns_404`：不存在章节与不存在项目 404 NOT_FOUND 拦截；
5. `test_cross_project_and_company_isolation`：跨项目与跨公司调阅隔离 404 NOT_FOUND 拦截；
6. `test_lock_status_sensing_unlocked_and_locked`：未锁 -> 加锁持锁元数据回显 -> 释放后置空感知全流程；
7. `test_eight_roles_read_only_viewer_can_get_but_cannot_write`：只读角色（viewer）GET 成功，`can_edit=False`，写操作拦截 403 FORBIDDEN；
8. `test_stored_structured_paragraphs_takes_precedence`：存储中已存在结构化段落时优先使用。
