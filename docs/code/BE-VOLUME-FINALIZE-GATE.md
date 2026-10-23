为什么有这个文件：说明分册定稿（finalize）状态机、前置安全门禁、租户权限强隔离与解锁生命周期的技术实现与代码设计。

它解决什么问题：落实 PRD v1.8 §5.8.5（分册检查与定稿闭环）与第二阶段后端 P0 核心缺口，建立严格的分册定稿状态机与安全门禁。确保仅项目负责人或公司管理员可触发定稿；编写人与非管理角色被 403 FORBIDDEN 拦截；跨租户被 404 NOT_FOUND 隔离；分册内任一章节处于排他锁定或缺少正式版本正文时被 409 拦截；分册内存在未消解的 severity == "blocker" 缺陷（废标红线与关键星号条款未满足）时被 409 CHECK_BLOCKER_EXISTS 拦截；并通过持久化标记 is_finalized = True、记录定稿人及时间戳，提供先解锁后修改的完整生命周期。

# BE-VOLUME-FINALIZE-GATE：分册定稿状态机与前置检查门禁代码说明

## 1. 业务上下文与设计目标
在标书编制流程中，技术分册与商务分册由不同的团队成员与分册负责人并行编制。在最终正式递交之前，各分册必须经过严格的「分册定稿」阶段（PRD §5.8.5）：
1. **权限底线**：
   - 定稿是极具法律与商务约束力的里程碑操作，仅限当前项目负责人（`project_lead`，兼容历史 `manager`）或当前公司管理员（`company_admin`）执行；
   - 普通编写人（`bid_writer` / `editor`）无权定稿，尝试执行必须被 HTTP 403 `FORBIDDEN` 拦截；
   - 强租户隔离：跨公司账号访问其他公司项目必须返回 HTTP 404 `NOT_FOUND`，不得泄露其他租户项目存在性。
2. **前置安全门禁**：
   - **门禁 1（章节锁定与正文完整性）**：该分册包含的所有章节必须已有正式版本正文（`chapter.content` 非空）且当前未被任何用户排他锁定（无有效租约占用）。若存在排他锁定拦截 409 `LOCK_HELD`；若缺少正式正文拦截 409 `CHAPTER_CONTENT_EMPTY`；
   - **门禁 2（缺陷阻断项）**：该分册不能存在未消解的 `severity == "blocker"` 缺陷（包含历史检查记录及实时动态核对的废标红线、关键星号条款未确认、未映射、未响应或缺资质证明），存在阻断项拦截 409 `CHECK_BLOCKER_EXISTS`。
3. **状态流转与解锁生命周期**：
   - 门禁全部通过后，分册标记 `is_finalized = True`，持久化记录定稿人 ID `finalized_by` 与 ISO 时间戳 `finalized_at`；
   - 支持定稿后修改规范（PRD §5.8.5）：修改前必须显式调用解锁接口 `POST /api/v1/projects/{project_id}/volumes/{volume_id}/unlock`，强制记录解锁原因 `unlock_reason`、解锁人 `unlocked_by` 与解锁时间 `unlocked_at`，并将 `is_finalized` 回退为 `False`。

---

## 2. 架构设计与分包实现

严格遵守系统架构规范，新业务逻辑完全写入 `backend/bid-core/icg/` 分包架构，严禁向旧 `icg_demo` 根目录平铺巨石逻辑：
- 领域服务层：`backend/bid-core/icg/domain/volume_finalize.py`
- 领域编排混入：`backend/bid-core/icg/domain/workflow_orchestrator.py`（继承 `VolumeFinalizeMixin`）
- 路由接入层：`backend/bid-core/icg/api/volumes.py`（挂载至 `/api/v1`）
- API 契约同步：`spec/openapi/demo-v1.json`

### 2.1 领域异常设计 (`volume_finalize.py`)
为了满足门禁阻断项的细粒度业务错误码表达，并保证与既有 143 个冻结错误码测试相容，定义专用领域异常 `VolumeGateError`：
```python
class VolumeGateError(DomainError):
    """分册定稿门禁专用异常，支持细粒度业务错误码与 409 状态码。"""
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}
        Exception.__init__(self, message)
```
- 继承自 `DomainError`，FastAPI 全局异常处理器可自动识别；
- 绕过旧巨石单状态静态限制，准确返回 HTTP 409 与对应的 `LOCK_HELD`、`CHAPTER_CONTENT_EMPTY`、`CHECK_BLOCKER_EXISTS` 等业务错误码。

### 2.2 租户强隔离与权限校验 (`check_finalize_permissions`)
```python
def check_finalize_permissions(state: DemoState, principal: Principal, project: Project) -> None:
    # 租户强隔离：跨公司访问一律 404 NOT_FOUND
    if project.company_id != principal.user.company_id:
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

    norm_role = normalize_role(principal.user.role)
    if norm_role == "company_admin":
        return

    # 项目负责人判定（需是项目成员且 project_role == "lead"）
    if lead(state, project.id, principal.user.id):
        return

    raise DomainError(403, "FORBIDDEN", "分册定稿仅限当前项目负责人或公司管理员办理。")
```

### 2.3 前置安全门禁双核对
#### 门禁 1：章节排他锁定与正文提交状态
```python
vol_chapters = [
    c for c in state.chapters.values()
    if c.project_id == project_id and c.volume == volume_id
]
if not vol_chapters:
    raise VolumeGateError(409, "VOLUME_CHAPTERS_EMPTY", f"分册「{volume_id}」尚未划分章节，无法定稿。")

now_ts = self.demo._now() if hasattr(self.demo, "_now") else time.time()
for chapter in vol_chapters:
    # 排他锁门禁
    if is_chapter_locked(chapter, now_ts):
        raise VolumeGateError(
            409, "LOCK_HELD",
            f"分册章节「{chapter.title}」当前正被排他锁定，需先解锁或释放租约后方可定稿。"
        )
    # 正式正文门禁
    if not chapter.content or not chapter.content.strip():
        raise VolumeGateError(
            409, "CHAPTER_CONTENT_EMPTY",
            f"分册章节「{chapter.title}」缺少正式版本正文，无法定稿。"
        )
```

#### 门禁 2：检查结果与条款 blocker 缺陷扫描
```python
def check_volume_blockers(state, project_id, volume_id, workflow, check_id=None):
    # 1. 扫描历史检查批次中的 blocker
    checks = workflow.get("checks", {})
    vol_checks = [c for c in checks.values() if c.get("volume") in (volume_id, "all")]
    if vol_checks:
        latest = checks.get(check_id) if check_id else vol_checks[-1]
        for issue in latest.get("issues", []):
            if issue.get("severity") == "blocker":
                raise VolumeGateError(409, "CHECK_BLOCKER_EXISTS", f"分册最新检查结果存在未解决的 blocker 缺陷：{issue.get('message')}。")

    # 2. 实时核对条款：废标红线与关键星号条款
    for req in workflow.get("requirements", {}).values():
        if req.get("volume") != volume_id:
            continue
        if ExportServiceMixin._is_critical_requirement(req):
            if req.get("status") == "pending":
                raise VolumeGateError(409, "CHECK_BLOCKER_EXISTS", "关键条款尚未确认，存在 blocker 缺陷。")
            if not req.get("chapter_id"):
                raise VolumeGateError(409, "CHECK_BLOCKER_EXISTS", "关键条款未映射有效章节，存在 blocker 缺陷。")
            if not str(req.get("response", "")).strip() or "待补" in req.get("response", ""):
                raise VolumeGateError(409, "CHECK_BLOCKER_EXISTS", "关键条款未有效响应或仍有待补，存在 blocker 缺陷。")
            need_evidence = any(word in (req.get("text") or "") for word in ("资质", "证书", "证明", "业绩", "授权"))
            if need_evidence and not req.get("evidence_ids"):
                raise VolumeGateError(409, "CHECK_BLOCKER_EXISTS", "关键证明类条款缺少已确认企业证据，存在 blocker 缺陷。")
```

### 2.4 状态流转与持久化标记
门禁通过后，在项目工作流中原子持久化写入分册记录：
```python
volume_record = {
    "volume_id": volume_id,
    "project_id": project_id,
    "is_finalized": True,
    "finalized_by": principal.user.id,
    "finalized_at": now_iso,
    "unlocked_by": None,
    "unlocked_at": None,
    "unlock_reason": None,
}
workflow.setdefault("volumes", {})[volume_id] = volume_record
project.revision += 1
self._audit(state, principal, project_id, "volume.finalize", ...)
```

---

## 3. API 接口定义 (`/api/v1`)
所有新端点均严格注册在 `/api/v1` 前缀下，支持 `If-Match` 乐观并发与 `Idempotency-Key` 幂等保护：
1. `POST /api/v1/projects/{project_id}/volumes/{volume_id}/finalize`：触发分册前置门禁核对与定稿锁定；
2. `POST /api/v1/projects/{project_id}/volumes/{volume_id}/unlock`：解锁已定稿分册，必须提交 `reason`；
3. `GET /api/v1/projects/{project_id}/volumes/{volume_id}`：查询单分册定稿状态；
4. `GET /api/v1/projects/{project_id}/volumes`：查询项目中全部分册的定稿状态汇总。

---

## 4. 测试与验证策略
在 `tests/backend/test_volume_finalize_gate.py` 中编写 10 项端到端单测用例，实现 100% 场景覆盖：
- `test_volume_finalize_normal_by_project_lead`：项目负责人正常定稿放行；
- `test_volume_finalize_normal_by_company_admin`：公司管理员正常定稿放行；
- `test_volume_finalize_blocked_for_writer_with_403`：编写人越权拦截 403；
- `test_volume_finalize_cross_tenant_isolation_with_404`：跨租户访问强隔离 404；
- `test_volume_finalize_invalid_volume_returns_404`：非法分册标识 404；
- `test_volume_finalize_gate_blocks_when_chapter_is_locked`：章节被排他锁定拦截 409 LOCK_HELD，释放后恢复；
- `test_volume_finalize_gate_blocks_when_chapter_content_empty`：章节正文为空拦截 409 CHAPTER_CONTENT_EMPTY；
- `test_volume_finalize_gate_blocks_when_blocker_defects_exist`：存在废标/关键星号条款缺陷拦截 409 CHECK_BLOCKER_EXISTS，消减后恢复；
- `test_volume_unlock_lifecycle_and_reason_requirement`：先解锁后修改生命周期与必填原因验证；
- `test_volume_finalize_in_non_demo_eight_roles_environment`：关闭演示模式（`ICG_ALLOW_DEMO_LOGIN=0` / `ICG_ENV=production`）下正式 8 角色 Bearer Token 链路门禁验证。
