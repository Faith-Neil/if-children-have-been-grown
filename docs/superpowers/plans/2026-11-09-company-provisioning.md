# 公司开通与账号归属 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 平台管理员可一次开通公司并创建首个公司管理员，点进公司管理该公司账号；顶栏对平台管理员隐藏公司名；各公司项目与双库数据集按 `company_id` 强隔离。

**Architecture:** 后端在 `company_registry` 增加原子 `create_company`（写 companies 记录、company_settings 显示名、首个 Account）；`CreateUserRequest` 暴露可选 `must_change_password`；前端公司管理页增加新建弹窗与 `/admin/companies/:companyId` 详情（列表用户 + 加人）。知识库仍走既有 `dataset_full_name(company_id, kind)`，本计划加回归测试锁死隔离。

**Tech Stack:** Python 3、FastAPI、现有 DemoService / repository.transaction、React、Ant Design、`node:test`、pytest。

## Global Constraints

- 规格：`docs/superpowers/specs/2026-11-09-company-provisioning-design.md`；Issue：`ISSUE-052`。
- 新 API 只加 `/api/v1`；禁止往 `/api/demo` 加端点。
- `company_id` 自动生成：`co-` + 8 位小写十六进制；不可手填。
- 双库全名：`${company_id}::icg-history`、`${company_id}::icg-material`；禁止跨公司混用。
- 项目按 `company_id` 隔离；跨公司 404。
- 强制改密勾选默认 true；缺省字段亦为 true。
- 最高把任务推到 `in-review`；不标 `done`；不合并 PR #8，除非人类 PM 另令。
- 关演示正式路径验收不得只靠 demo 账号。
- 提交信息用英文；不提交凭据与绝对盘符链接。
- 收尾跑 `node scripts/check-project-governance.cjs`。

## File map

| 文件 | 职责 |
|------|------|
| `backend/bid-core/icg/domain/company_registry.py` | `CreateCompanyRequest` / `CreateCompanyResponse`、`create_company` |
| `backend/bid-core/icg/api/companies.py` | `POST /api/v1/companies` |
| `backend/bid-core/icg/domain/user_management.py` | `must_change_password` 入参；列表按公司过滤保持隔离 |
| `frontend/web/src/shell/AppHeaderActions.tsx` | 平台管理员不渲染公司名 |
| `frontend/web/src/admin/company-manage-core.ts` | 创建公司请求类型与校验 |
| `frontend/web/src/admin/CompanyManagePage.tsx` | 新建公司弹窗；点进详情 |
| `frontend/web/src/admin/CompanyDetailPage.tsx` | 公司用户表与加人（新建） |
| `frontend/web/src/app/app-route.ts` | 解析 `/admin/companies/:companyId` |
| `frontend/web/src/app/GlobalPagesContent.tsx` / `App.tsx` | 深链到公司详情 |
| `tests/backend/test_company_provisioning.py` | 开通、权限、改密、隔离 |
| `tests/backend/test_kb_company_dataset_isolation.py` | 双库命名与索引不串公司 |
| `frontend/web/tests/unit/company-provisioning.test.mjs` | 表单与顶栏可见性纯函数 |
| `docs/tasks/ADMIN-PROVISION.md`、`TASK_BOARD.md`、`ISSUE-052`、delivery/code | 治理 |

---

### Task 1: 后端开通公司领域服务

**Files:**
- Modify: `backend/bid-core/icg/domain/company_registry.py`
- Create: `tests/backend/test_company_provisioning.py`
- Test: `tests/backend/test_company_provisioning.py`

**Interfaces:**
- Consumes: `Principal`、`DemoService.repository`、`hash_password`、`require_strong_password`、`company_display_name` 写入路径、`Account`、`security_audit.record`
- Produces:
  - `CreateCompanyRequest(name, admin_username, admin_name, admin_password, admin_display_name: str | None = None, must_change_password: bool = True)`
  - `CreateCompanyResponse(company: CompanySummary, admin: UserModel)` — `UserModel` 从 `user_management` 导入或用等价脱敏 dict；推荐复用 `account_to_user_model`
  - `create_company(service, principal, request) -> CreateCompanyResponse`

- [ ] **Step 1: 写失败测试**

创建 `tests/backend/test_company_provisioning.py`：

```python
# 为什么有这个文件：验收 ISSUE-052 公司开通与租户隔离。
from fastapi.testclient import TestClient
from test_reference_flow import client, login  # noqa: F401


def test_platform_admin_creates_company_and_first_admin(client: TestClient):
    headers = login(client, "platform-admin")
    res = client.post("/api/v1/companies", headers=headers, json={
        "name": "合成华北智造有限公司",
        "admin_username": "huabei-admin",
        "admin_name": "李开通",
        "admin_password": "Init_Pass_2026",
        "must_change_password": True,
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["company"]["name"] == "合成华北智造有限公司"
    assert body["company"]["status"] == "active"
    assert body["company"]["id"].startswith("co-")
    assert len(body["company"]["id"]) == 11  # co- + 8 hex
    assert body["admin"]["id"] == "huabei-admin"
    assert body["admin"]["role"] == "company_admin"
    assert body["admin"]["company_id"] == body["company"]["id"]
    assert body["admin"]["must_change_password"] is True


def test_company_admin_cannot_create_company(client: TestClient):
    headers = login(client, "alpha-company-admin")
    res = client.post("/api/v1/companies", headers=headers, json={
        "name": "不该出现的公司",
        "admin_username": "nope-admin",
        "admin_name": "无",
        "admin_password": "Init_Pass_2026",
    })
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/backend/test_company_provisioning.py::test_platform_admin_creates_company_and_first_admin -q`

Expected: FAIL（404 或 method not allowed / 路由不存在）。

- [ ] **Step 3: 实现 `create_company`**

在 `company_registry.py` 增加请求/响应模型与函数。要点：

```python
import secrets
from .auth_service import hash_password, is_super_admin
from .domain import Account, DomainError, Principal
from .password_login import require_strong_password
from .user_management import UserModel, account_to_user_model  # 若 account_to_user_model 未导出则导出之

class CreateCompanyRequest(RequestBody):
    name: str = Field(min_length=1, max_length=200)
    admin_username: str = Field(min_length=1, max_length=64)
    admin_name: str = Field(min_length=1, max_length=100)
    admin_password: str = Field(min_length=1, max_length=200)
    admin_display_name: str | None = Field(default=None, max_length=100)
    must_change_password: bool = True

class CreateCompanyResponse(ResponseBody):
    company: CompanySummary
    admin: UserModel

def _new_company_id(state) -> str:
    known = known_company_ids(state)
    for _ in range(16):
        cid = "co-" + secrets.token_hex(4)
        if cid not in known and cid not in state.accounts:
            return cid
    raise DomainError(500, "INTERNAL", "无法生成唯一公司标识，请重试。")

def create_company(service, principal: Principal, request: CreateCompanyRequest) -> CreateCompanyResponse:
    if not _platform_admin(principal):
        raise DomainError(403, "FORBIDDEN", "只有平台管理员可以开通公司。")
    name = (request.name or "").strip()
    if not name:
        raise DomainError(422, "VALIDATION_ERROR", "公司显示名不能为空。", details={"field": "name"})
    username = (request.admin_username or "").strip()
    admin_name = (request.admin_name or "").strip()
    if not username or not admin_name:
        raise DomainError(422, "VALIDATION_ERROR", "管理员账号与姓名不能为空。")

    state = service.repository.read()
    for cid in known_company_ids(state):
        if company_display_name(state, cid).strip() == name:
            raise DomainError(409, "COMPANY_NAME_DUPLICATED", f"公司名称「{name}」已存在。")
    if username in state.accounts:
        raise DomainError(409, "DICT_CODE_DUPLICATED", f"账号 {username} 已存在，请更换用户名。")

    # 密码强度：用即将写入的 company_id 临时 Account 调 require_strong_password
    company_id = _new_company_id(state)
    probe = Account(id=username, name=admin_name, company_id=company_id, role=ROLE_COMPANY_ADMIN)
    require_strong_password(state, probe, request.admin_password, field="admin_password")
    pwd_hash, salt = hash_password(request.admin_password)
    now = time.time()
    display = (request.admin_display_name or "").strip() or admin_name

    def write(s) -> None:
        companies = s.service_stores.setdefault("companies", {})
        companies[company_id] = {
            "status": "active",
            "created_at": now,
            "created_by": principal.user.id,
            "status_changed_at": now,
            "status_changed_by": principal.user.id,
        }
        settings = s.service_stores.setdefault("company_settings", {})
        settings[company_id] = {
            **(settings.get(company_id) or {}),
            "company_id": company_id,
            "company_name": name,
        }
        s.accounts[username] = Account(
            id=username, name=admin_name, company_id=company_id, role=ROLE_COMPANY_ADMIN,
            _DEMO_ONLY=False, password_hash=pwd_hash, salt=salt, display_name=display,
            status="active", created_at=now, updated_at=now,
            must_change_password=bool(request.must_change_password),
        )
        security_audit.record(s, "company.create", operator=principal.user.id,
                              company_id=company_id, admin_user_id=username)

    service.repository.transaction(write)
    fresh = service.repository.read()
    return CreateCompanyResponse(
        company=_summary(fresh, company_id),
        admin=account_to_user_model(fresh.accounts[username]),
    )
```

若 `Account` 构造参数或 `account_to_user_model` 名称与现网不一致，以 `domain.py` / `user_management.py` 现有定义为准，不得新造字段语义。

- [ ] **Step 4: 注册 API（可与本任务同提交）**

在 `icg/api/companies.py`：

```python
from icg.domain.company_registry import (
    CompanyListResponse, CompanySummary, UpdateCompanyStatusRequest,
    CreateCompanyRequest, CreateCompanyResponse, create_company,
)

@router.post(
    "/companies",
    response_model=CreateCompanyResponse,
    status_code=201,
    operation_id="createCompany",
    summary="开通公司并创建首个公司管理员",
    tags=["companies"],
)
def create_company_endpoint(body: CreateCompanyRequest, user: Principal = Depends(current_user)):
    return create_company(service, user, body)
```

把 `POST /companies` 放在 `/{company_id}/status` 之前或确保路径不冲突（静态 `/companies` POST 与 `/{id}/status` 无冲突）。

- [ ] **Step 5: 跑测试至通过**

Run: `python -m pytest tests/backend/test_company_provisioning.py -q`

Expected: 上述两例 PASS。再补同文件内：

- 显示名冲突 → 409 `COMPANY_NAME_DUPLICATED`
- 弱密码 → 422 `PASSWORD_WEAK`
- `must_change_password: false` 时管理员登录后可调 `/api/v1/projects`（无 `PASSWORD_CHANGE_REQUIRED`）

- [ ] **Step 6: Commit**

```bash
git add backend/bid-core/icg/domain/company_registry.py backend/bid-core/icg/api/companies.py tests/backend/test_company_provisioning.py
git commit -m "$(cat <<'EOF'
feat: add POST /api/v1/companies to provision tenant and first admin

EOF
)"
```

---

### Task 2: 创建用户可选强制改密 + OpenAPI

**Files:**
- Modify: `backend/bid-core/icg/domain/user_management.py`（`CreateUserRequest` 与 `create_user`）
- Modify: `tests/backend/test_password_login.py`（保持默认 true 的旧断言）
- Modify: OpenAPI 生成/检查所用脚本（仓库惯例：`backend/bid-core` 下 `export_openapi.py --check` 或项目文档写明的命令）
- Test: `tests/backend/test_company_provisioning.py`（追加）

**Interfaces:**
- Consumes: Task 1 已开通的公司 id
- Produces: `CreateUserRequest.must_change_password: bool = True`；`create_user` 写入该值

- [ ] **Step 1: 写失败测试**

```python
def test_create_user_respects_must_change_password_false(client: TestClient):
    admin = login(client, "platform-admin")
    created_co = client.post("/api/v1/companies", headers=admin, json={
        "name": "合成改密可选公司",
        "admin_username": "opt-admin",
        "admin_name": "管",
        "admin_password": "Init_Pass_2026",
        "must_change_password": False,
    })
    assert created_co.status_code == 201
    cid = created_co.json()["company"]["id"]
    res = client.post("/api/v1/users", headers=admin, json={
        "username": "opt-member",
        "name": "员",
        "company_id": cid,
        "role": "member",
        "password": "Init_Pass_2026",
        "must_change_password": False,
    })
    assert res.status_code in (200, 201)
    assert res.json()["must_change_password"] is False
    login_res = client.post("/api/v1/auth/login", json={"username": "opt-member", "password": "Init_Pass_2026"})
    assert login_res.status_code == 200
    assert login_res.json()["must_change_password"] is False
    projects = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {login_res.json()['access_token']}"})
    assert projects.status_code == 200
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/backend/test_company_provisioning.py::test_create_user_respects_must_change_password_false -q`

Expected: FAIL（字段被忽略，仍为 true）。

- [ ] **Step 3: 改 `CreateUserRequest` 与 `create_user`**

```python
class CreateUserRequest(BaseModel):
    username: str = Field(description="登录账号 / 用户ID")
    name: str = Field(description="用户真实姓名")
    company_id: str = Field(description="所属企业租户ID")
    role: str = Field(description="分配的标准系统角色")
    password: str = Field(description="初始登录密码")
    display_name: str | None = Field(default=None, description="展示昵称")
    must_change_password: bool = Field(default=True, description="新建后是否须本人改密")
```

把 `create_user` 里 `must_change_password=True` 改为 `must_change_password=bool(request.must_change_password)`。

- [ ] **Step 4: 回归旧测试并同步 OpenAPI**

Run: `python -m pytest tests/backend/test_password_login.py tests/backend/test_company_provisioning.py -q`

Expected: PASS（旧用例未传字段仍为 true）。

按仓库惯例更新 OpenAPI（若有 `export_openapi.py` 先生成再 `--check`）。

- [ ] **Step 5: Commit**

```bash
git add backend/bid-core/icg/domain/user_management.py tests/backend/test_company_provisioning.py
# 若有 openapi 产物一并 add
git commit -m "$(cat <<'EOF'
feat: honor must_change_password on user create

EOF
)"
```

---

### Task 3: 顶栏隐藏平台管理员公司名

**Files:**
- Modify: `frontend/web/src/shell/AppHeaderActions.tsx`
- Create or modify: `frontend/web/tests/unit/company-provisioning.test.mjs`
- Optional helper: `frontend/web/src/admin/company-provision-core.ts`（纯函数 `shouldShowCompanyLabel(role)`）

**Interfaces:**
- Consumes: `normalizeSystemRole` / 会话 `primary_role`
- Produces: `shouldShowCompanyLabel(role: string | undefined): boolean` — `platform_admin` 为 false，其余 true

- [ ] **Step 1: 写失败单测**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { shouldShowCompanyLabel } from '../../src/admin/company-provision-core.ts';

test('platform_admin does not show company label', () => {
  assert.equal(shouldShowCompanyLabel('platform_admin'), false);
  assert.equal(shouldShowCompanyLabel('company_admin'), true);
  assert.equal(shouldShowCompanyLabel('member'), true);
});
```

- [ ] **Step 2: 运行确认失败**

Run: `pnpm --dir frontend/web exec node --test tests/unit/company-provisioning.test.mjs`

Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现并改顶栏**

`company-provision-core.ts`：

```ts
import { normalizeSystemRole } from '../shell/route-guard.ts';

export function shouldShowCompanyLabel(role?: string | null): boolean {
  return normalizeSystemRole(role) !== 'platform_admin';
}
```

`AppHeaderActions.tsx`：仅当 `shouldShowCompanyLabel(user.role 或 primary_role)` 为 true 时渲染 `<span className="company-label">…</span>`。

- [ ] **Step 4: 跑单测**

Run: `pnpm --dir frontend/web exec node --test tests/unit/company-provisioning.test.mjs`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/web/src/shell/AppHeaderActions.tsx frontend/web/src/admin/company-provision-core.ts frontend/web/tests/unit/company-provisioning.test.mjs
git commit -m "$(cat <<'EOF'
fix: hide company label for platform admin header

EOF
)"
```

---

### Task 4: 公司管理「新建公司」弹窗

**Files:**
- Modify: `frontend/web/src/admin/company-manage-core.ts`（或 `company-provision-core.ts`）
- Modify: `frontend/web/src/admin/CompanyManagePage.tsx`
- Test: `frontend/web/tests/unit/company-provisioning.test.mjs`

**Interfaces:**
- Consumes: `POST /api/v1/companies`；`list.can_change_status`（平台管理员）作为「可新建」信号，或 `role === 'platform_admin'`
- Produces:
  - `validateCreateCompanyForm(values) -> { valid, issues }`
  - `createCompany(requestFn, token, body) -> Promise<CreateCompanyResponse>`

- [ ] **Step 1: 写校验单测**

```js
test('create company form requires name, admin username, name, password', () => {
  const bad = validateCreateCompanyForm({
    name: '  ', admin_username: '', admin_name: '', admin_password: '', must_change_password: true,
  });
  assert.equal(bad.valid, false);
  const good = validateCreateCompanyForm({
    name: '合成公司', admin_username: 'c1', admin_name: '甲', admin_password: 'Init_Pass_2026', must_change_password: true,
  });
  assert.equal(good.valid, true);
});
```

- [ ] **Step 2: 运行确认失败 → Step 3 实现校验与 API 封装 → Step 4 再跑通过**

- [ ] **Step 5: 改 `CompanyManagePage`**

- 平台管理员显示「新建公司」按钮（`data-testid="company-create-open"`）。
- Modal 字段：公司显示名、管理员用户名、姓名、显示名（可选）、初始密码、Checkbox「首次登录强制改密」默认勾选。
- 提交调用 `POST /api/v1/companies`；成功 `message.success` 含 `company_id` 与管理员用户名；关闭弹窗；`load()` 刷新。
- Layout First：不堆说明文案。

- [ ] **Step 6: Commit**

```bash
git add frontend/web/src/admin/CompanyManagePage.tsx frontend/web/src/admin/company-manage-core.ts frontend/web/src/admin/company-provision-core.ts frontend/web/tests/unit/company-provisioning.test.mjs
git commit -m "$(cat <<'EOF'
feat: add create-company dialog on company manage page

EOF
)"
```

---

### Task 5: 公司详情路由与用户管理 UI

**Files:**
- Create: `frontend/web/src/admin/CompanyDetailPage.tsx`
- Modify: `frontend/web/src/app/app-route.ts`
- Modify: `frontend/web/src/app/GlobalPagesContent.tsx`、`App.tsx`（把 `companyId` 传入管理区）
- Modify: `frontend/web/src/admin/CompanyManagePage.tsx`（公司名可点）
- Test: `frontend/web/tests/unit/company-provisioning.test.mjs`；必要时 `tests/frontend` 转发不新增业务测

**Interfaces:**
- Consumes: `GET /api/v1/users?company_id=`、`POST /api/v1/users`
- Produces: 路径 `/admin/companies/:companyId` → 打开详情；返回列表路径 `/admin` 或原公司管理 tab

- [ ] **Step 1: 扩展 `parseAppPath`**

在 `app-route.ts`：

```ts
export type AppRoute =
  | { kind: 'home'; path: '/' }
  | { kind: 'login'; path: '/login' }
  | { kind: 'global'; routeId: string; path: string }
  | { kind: 'company_detail'; companyId: string; path: string }
  | { kind: 'project'; projectId: string; tab: string; path: string; chapterId?: string }
  | { kind: 'unknown'; path: string };

export function companyDetailPath(companyId: string): string {
  return `/admin/companies/${encodeURIComponent(companyId)}`;
}

// 在 parseAppPath 中，global 匹配之后、project 匹配之前：
const companyDetailMatch = /^\/admin\/companies\/([^/]+)$/.exec(path);
if (companyDetailMatch) {
  const companyId = decodeURIComponent(companyDetailMatch[1]);
  if (companyId && companyId !== '.' && companyId !== '..') {
    return { kind: 'company_detail', companyId, path: companyDetailPath(companyId) };
  }
}
```

`menuPathFor`：`company_detail` 返回 `applicationPaths['admin.rules']`（侧栏仍高亮「管理」）。

- [ ] **Step 2: 写路由单测（若已有 app-route 测试则追加；否则在 company-provisioning 测 path 辅助函数）**

- [ ] **Step 3: 实现 `CompanyDetailPage`**

- Props: `companyId`, `session`, `token`, `onBack`
- 加载：`listCompanies` 找当前行作页头；`GET /api/v1/users?company_id=`
- 表列：账号、姓名、角色、状态、`must_change_password`
- 「添加账号」：`platform_admin` 角色可选 `company_admin|member`；`company_admin` 固定 `member`；`must_change_password` 默认 true
- 非授权：展示错误，不泄漏他司用户

- [ ] **Step 4: 接线**

- `CompanyManagePage` 公司名 `Button type="link"` → `onNavigate(companyDetailPath(row.id))`（从 props 传入 `onNavigate`）
- `App.tsx` / `GlobalPagesContent`：当 `parseAppPath` 为 `company_detail` 时渲染 `CompanyDetailPage`（仍要求会话可进管理）
- `company_admin` 只能打开本公司 id；否则显示未找到

- [ ] **Step 5: 前端测试与 lint**

Run: `pnpm --dir frontend/web test`（或至少 unit 相关文件）  
Run: `pnpm --dir frontend/web lint`（若任务环境惯例要求）

Expected: 相关单测 PASS；无新增 TS 错误。

- [ ] **Step 6: Commit**

```bash
git add frontend/web/src/admin/CompanyDetailPage.tsx frontend/web/src/admin/CompanyManagePage.tsx frontend/web/src/app/app-route.ts frontend/web/src/app/GlobalPagesContent.tsx frontend/web/src/app/App.tsx frontend/web/tests/unit/company-provisioning.test.mjs
git commit -m "$(cat <<'EOF'
feat: add company detail page for per-tenant user management

EOF
)"
```

---

### Task 6: 项目与双库数据集隔离回归

**Files:**
- Create: `tests/backend/test_kb_company_dataset_isolation.py`
- Modify: `tests/backend/test_company_provisioning.py`（跨公司项目不可见）
- 只读核对：`backend/bid-core/icg/domain/knowledge_base.py` 的 `dataset_full_name`（无回归则不改代码）

**Interfaces:**
- Consumes: `dataset_full_name`、`KnowledgeBaseService.ensure_dataset` 或 kb-admin ensure；`POST /api/v1/projects`
- Produces: 锁死两公司双库全名不同且索引不交叉

- [ ] **Step 1: 写隔离测试**

```python
from icg.domain.knowledge_base import dataset_full_name

def test_dataset_full_names_are_per_company():
    assert dataset_full_name("co-aaa11111", "history") == "co-aaa11111::icg-history"
    assert dataset_full_name("co-bbb22222", "materials") == "co-bbb22222::icg-material"
    assert dataset_full_name("co-aaa11111", "history") != dataset_full_name("co-bbb22222", "history")


def test_two_provisioned_companies_cannot_see_each_others_projects(client: TestClient):
    admin = login(client, "platform-admin")
    a = client.post("/api/v1/companies", headers=admin, json={
        "name": "隔离公司甲", "admin_username": "iso-a-admin", "admin_name": "甲",
        "admin_password": "Init_Pass_2026", "must_change_password": False,
    }).json()
    b = client.post("/api/v1/companies", headers=admin, json={
        "name": "隔离公司乙", "admin_username": "iso-b-admin", "admin_name": "乙",
        "admin_password": "Init_Pass_2026", "must_change_password": False,
    }).json()
    token_a = client.post("/api/v1/auth/login", json={"username": "iso-a-admin", "password": "Init_Pass_2026"}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", json={"username": "iso-b-admin", "password": "Init_Pass_2026"}).json()["access_token"]
    created = client.post("/api/v1/projects", headers={"Authorization": f"Bearer {token_a}"},
                          json={"name": "甲公司机密项目"})
    assert created.status_code in (200, 201), created.text
    pid = created.json()["id"]
    list_b = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200
    assert all(p["id"] != pid for p in list_b.json().get("items", list_b.json() if isinstance(list_b.json(), list) else []))
    other = client.get(f"/api/v1/projects/{pid}", headers={"Authorization": f"Bearer {token_b}"})
    assert other.status_code == 404
```

若项目列表响应结构不是 `items`，按现网 `GET /api/v1/projects` 实际 JSON 调整断言，不得放宽成「找不到字段就算过」。

- [ ] **Step 2: kb-admin ensure 隔离（假客户端）**

用现有 kb-admin / fake ragflow 夹具：分别以两公司管理员会话调用 ensure；断言返回的 `name` 为各自 `company_id::icg-history` / `::icg-material`，且写入的 dataset id 映射互不引用。若现有测试已覆盖，本步改为扩展断言而非复制整套假服务。

- [ ] **Step 3: 跑测试**

Run: `python -m pytest tests/backend/test_company_provisioning.py tests/backend/test_kb_company_dataset_isolation.py -q`

Expected: PASS。

- [ ] **Step 4: Commit**

```bash
git add tests/backend/test_company_provisioning.py tests/backend/test_kb_company_dataset_isolation.py
git commit -m "$(cat <<'EOF'
test: lock company project and KB dataset isolation

EOF
)"
```

---

### Task 7: 治理登记与交付壳

**Files:**
- Create: `docs/tasks/ADMIN-PROVISION.md`（任务卡 `ADMIN-PROVISION-T01`～`T04` 或与本计划 Task 1～6 映射表）
- Modify: `docs/TASK_BOARD.md`、`docs/PROJECT_STATUS.md`、`issues/ISSUE-052.md`、`issues/index.md`、`docs/DOCUMENT_INDEX.md`
- Create: `docs/delivery/ADMIN-PROVISION-T01.md` 等（实现完成后填；本任务可先建骨架并在各实现任务收尾补齐）
- 对照：`docs/PRD.md` / `ARCHITECTURE.md` 增加「公司开通」短注或在 Issue 六份基线写明无结构变更理由

**Interfaces:**
- Consumes: 本计划全部任务结果
- Produces: 看板行指向 `tasks/ADMIN-PROVISION.md#admin-provision-t0N`；状态最高 `in-review`

- [ ] **Step 1: 写任务卡文件**，每卡含范围、依赖、验收、delivery/code 链接；`<a id="admin-provision-t01"></a>` 等锚点。

建议映射：

| 卡 ID | 覆盖本计划 |
|-------|------------|
| ADMIN-PROVISION-T01 | Task 1～2 |
| ADMIN-PROVISION-T02 | Task 3～4 |
| ADMIN-PROVISION-T03 | Task 5 |
| ADMIN-PROVISION-T04 | Task 6 |

- [ ] **Step 2: 更新 ISSUE-052 实施任务表与状态 `in-progress`**

- [ ] **Step 3: TASK_BOARD / PROJECT_STATUS / DOCUMENT_INDEX**（计划本文登记为设计配套计划文档）

- [ ] **Step 4: 各卡完成后写 delivery（含验收证据）与 code 说明；建议 PM 标 done，不自行标 done**

- [ ] **Step 5: 治理检查**

Run: `node scripts/check-project-governance.cjs`

Expected: 通过（或仅剩与本变更无关的既有告警并在 delivery 诚实记录）。

- [ ] **Step 6: Commit**

```bash
git add docs/tasks/ADMIN-PROVISION.md docs/TASK_BOARD.md docs/PROJECT_STATUS.md issues/ISSUE-052.md issues/index.md docs/DOCUMENT_INDEX.md docs/delivery docs/code docs/superpowers/plans/2026-11-09-company-provisioning.md
git commit -m "$(cat <<'EOF'
docs: register company provisioning tasks and plan

EOF
)"
```

---

## Spec coverage checklist

| 规格条目 | 任务 |
|----------|------|
| 顶栏平台管理员无公司名 | Task 3 |
| 同弹窗开通公司+首个管理员、自动 `company_id`、强制改密勾选 | Task 1、4 |
| 公司详情用户列表与加人（平台可加两种角色；公司管理员仅 member） | Task 5 |
| 多公司管理员 | Task 1、5（不限制唯一） |
| `POST /companies` 与错误码 | Task 1 |
| `must_change_password` 可选 | Task 2 |
| 项目隔离 | Task 6 |
| 双库 `${company_id}::` 不混用 | Task 6 |
| 治理 / 不标 done | Task 7 |
| UsersPage 不强制删除 | 非目标，无任务 |

## Self-review notes

- 已去掉「实现时再选」的错误码歧义，与规格 409 `COMPANY_NAME_DUPLICATED` 对齐。
- 详情路由按规格 `/admin/companies/:companyId`，经 `parseAppPath` 接入现有壳层，避免假路径。
- 开通 API 不自动建 RAGFlow 数据集；建库仍走该公司上下文的 ensure（规格 §5.2）。
