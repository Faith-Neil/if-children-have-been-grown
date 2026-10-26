为什么有这个文件：详细说明 REV-SMOKE-001 关演示主链路全流程联调涉及的前后端胶水代码修改、调用流与鉴权流。

它解决什么问题：阐述 `/api/v1/projects` POST 契约补充、`GET /api/v1/session` 八角色鉴权会话解析、前端 App.tsx 请求对齐以及相关 Schema 兼容拓展的技术细节，供审计与后续维护参考。

# REV-SMOKE-001：关演示全流程冒烟联调胶水代码说明

- 对应任务：[REV-SMOKE-001](../delivery/REV-SMOKE-001.md)
- 关联问题：[ISSUE-005](../../issues/ISSUE-005.md)、[ISSUE-007](../../issues/ISSUE-007.md)
- 核心修改文件：
  - [main.py](../../backend/bid-core/icg_demo/main.py)
  - [schemas.py](../../backend/bid-core/icg_demo/schemas.py)
  - [session_navigation.py](../../backend/bid-core/icg_demo/session_navigation.py)
  - [App.tsx](../../frontend/web/src/app/App.tsx)
  - [demo-v1.json](../../spec/openapi/demo-v1.json)
  - [test_smoke_non_demo_pipeline.py](../../tests/backend/test_smoke_non_demo_pipeline.py)

---

## 1. 架构流向与链路示意

在关演示模式（`VITE_DEMO=0`, `ICG_ALLOW_DEMO_LOGIN=0`）下，业务请求必须通过 Bearer Token 进行正式鉴权，数据通过 `/api/v1` 契约端点流转：

```
[前端客户端 / 测试客户端]
       │
       ├─ 1. GET /api/v1/session (Bearer Token)
       │    └─► session_navigation.py: 校验非演示身份，返回 auth_mode="authenticated", role_mode="rbac-8roles"
       │
       ├─ 2. POST /api/v1/projects (Idempotency-Key)
       │    └─► main.py (createV1Project) ──► domain.create_project: 校验 LEAD_COMPANY_ROLES 并初始化项目
       │
       ├─ 3. POST /api/v1/projects/{id}/files & /parse & /parse/confirm
       │    └─► workflow_routes.py: 招标文件上传、异步作业解析、未审拦截与解析确认门禁
       │
       ├─ 4. PATCH /requirements/{req_id} & POST /evidence
       │    └─► workflow_routes.py: 响应矩阵确认与有效企业证据挂接
       │
       ├─ 5. POST /outline_plan/confirm & /generate
       │    └─► outline_plan_routes.py & workflow_routes.py: 大纲方案确认与章节正文初始生成
       │
       └─ 6. POST /checks & POST /exports & GET /exports/{id}/{volume}
            └─► export_service.py: 合规检查、递交阻断(400)/内部放行(200)、Word .docx 二进制下载
```

---

## 2. 关键代码变更与解释

### 2.1 规范端点补充：`POST /api/v1/projects`
在 [main.py](../../backend/bid-core/icg_demo/main.py) 中：
```python
@app.post(
    "/api/v1/projects",
    response_model=ProjectResponse,
    operation_id="createV1Project",
    responses=v1_error_responses(401, 403, 409, 428),
)
def create_v1_project(
    payload: ProjectCreateRequest,
    user: Principal = Depends(current_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    return domain.create_project(state, user, payload, idempotency_key=idempotency_key)
```
- **解释**：将前端原本调用的历史 `/api/projects` 提升为规范的 `/api/v1/projects`，附带 `operation_id="createV1Project"`，并在统一错误体模板中声明 401、403、409、428 响应码。
- **前端同步**：在 [App.tsx](../../frontend/web/src/app/App.tsx) 中将 `handleCreateProject` 内的请求路径更新为 `/api/v1/projects`。

### 2.2 八角色 Schema 拓展：`DemoCompanyRole` 与 `ApplicationRole`
在 [schemas.py](../../backend/bid-core/icg_demo/schemas.py) 中：
```python
DemoCompanyRole = Literal[
    "editor", "manager", "viewer", "company_admin", "data_admin",
    "project_lead", "bid_writer", "auditor", "readonly", "reviewer",
    "platform_admin", "group_admin",
]
ApplicationRole = Literal[
    "lead", "volume_lead", "writer", "viewer",
    "company_admin", "data_admin", "auditor", "group_admin", "platform_admin",
]
```
- **解释**：在 Pydantic 模型校验时，旧代码仅允许 5 种历史演示角色，导致标准 RBAC 8 角色调用 `GET /api/v1/session` 时在响应序列化阶段抛出 `ResponseValidationError`。扩展后全面兼容系统标准角色。

### 2.3 正式用户 8 角色会话解析：`get_application_session`
在 [session_navigation.py](../../backend/bid-core/icg_demo/session_navigation.py) 中：
```python
    is_demo_account = (
        user.id in DEMO_ONLY_ACCOUNT_IDS or
        getattr(user, "_DEMO_ONLY", False) or
        account.id in DEMO_ONLY_ACCOUNT_IDS
    )
    if is_demo_account:
        auth_mode = "synthetic-demo"
        role_mode = "legacy-demo-compat"
        effective_role = role
        allowed_actions = allowed_actions_for_role(effective_role)
    else:
        auth_mode = "authenticated"
        role_mode = "rbac-8roles"
        effective_role = normalize_role(role)
        # 根据归一化后的角色派发合法的操作权限
        if effective_role in ("project_lead", "company_admin", "platform_admin"):
            allowed_actions = [
                "project:create", "project:read", "project:update", "project:archive",
                "chapter:read", "chapter:edit", "chapter:lock", "chapter:approve",
                "check:run", "export:internal", "export:submission",
                "team:manage", "matrix:confirm", "outline:confirm", "evidence:mount",
            ]
        elif effective_role == "bid_writer":
            allowed_actions = [
                "project:read", "chapter:read", "chapter:edit", "chapter:lock",
                "check:run", "evidence:mount",
            ]
        elif effective_role in ("data_admin",):
            allowed_actions = ["project:read", "library:read", "library:edit", "evidence:mount"]
        else: # viewer, auditor, group_admin 等只读
            allowed_actions = ["project:read", "chapter:read", "library:read"]
```
- **解释**：
  1. 准确隔离演示账号（保留向后兼容）与真实认证账号；
  2. 真实认证账号返回标准 `auth_mode="authenticated"` 与 `role_mode="rbac-8roles"`；
  3. 基于 PRD v1.8 权限矩阵赋予角色匹配的 `allowed_actions`。

---

## 3. 契约同步与 OpenAPI 保障

- 在 [demo-v1.json](../../spec/openapi/demo-v1.json) 中严格同步 `/api/v1/projects` POST 路径定义。
- 保证错误码集合严格锁定在已有 143 个错误码范围内，未发生命名漂移。
- 运行 `pytest tests/backend/test_operation_ids.py tests/backend/test_error_idempotency.py` 确保 100% 契约一致。
