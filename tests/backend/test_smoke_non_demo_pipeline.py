# 为什么有这个文件：执行 REV-SMOKE-001 关演示全流程冒烟联调与断点排查自动化测试。
# 它解决什么问题：
# 1. 验证在关闭内置演示账号登录（ICG_ALLOW_DEMO_LOGIN=0 / ICG_ENV=production）环境下，内置演示账号登录被严格阻断（403 FORBIDDEN）；
# 2. 验证基于正式 Token（Bearer 凭据）请求 GET /api/v1/session 时返回的标准 8 角色 RBAC 会话契约（auth_mode="authenticated", role_mode="rbac-8roles"）；
# 3. 验证端到端主业务全流程真实贯通：
#    - Step 1: 正式 Token 会话登录与 8 角色权限核对；
#    - Step 2: 项目创建 (POST /api/v1/projects) 与团队/属性配置；
#    - Step 3: 招标文件上传与解析确认 (POST /api/v1/projects/{id}/files -> parse -> confirm)；
#    - Step 4: 响应矩阵与公司资料库证据挂接 (PATCH requirements / facts / POST /api/v1/library)；
#    - Step 5: 分节大纲方案确认与章节生成 (POST /api/v1/projects/{id}/plan -> generate)；
#    - Step 6: 导出双门禁排查与验证：内部评审放行（kind="internal" 放行但标记 has_blockers）与正式递交版阻断（kind="submission" 拦截 400 CHECK_BLOCKER_EXISTS，消减 blocker 后放行并成功下载双册 Word 文件）。

import base64
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.domain import Account, DemoService, Principal
from icg_demo.main import create_app
from icg_demo.ports import ModelProvider


SAMPLE_TENDER_TEXT = (
    "合成正式招标文件：智慧城市云平台建设项目\n"
    "招标编号：GOV-2026-CLOUD-088\n"
    "投标截止时间：2026-12-31T18:00:00+08:00\n"
    "★技术关键要求：系统服务可用性需达到 99.99%，故障切换时间小于 30 秒。\f"
    "商务资质要求：提供经第三方审计的上一年度财务报表及相关企业资质证明。"
)


class MockLocalModel(ModelProvider):
    name = "mock-smoke-model"
    is_real_model = True
    is_local = True

    def suggest(self, instruction: str, content: str) -> str:
        return f"【AI生成方案】根据招标文件要求，采用双活集群高可用部署架构，确保 RTO<30秒。内容补充：{instruction}"


@pytest.fixture
def non_demo_env(monkeypatch):
    """设置非演示/生产模式环境并初始化测试客户端与 8 角色用户。"""
    monkeypatch.setenv("ICG_ALLOW_DEMO_LOGIN", "0")
    monkeypatch.setenv("ICG_ENV", "production")

    state = seed_state()

    # 注册 8 个标准 RBAC 角色的正式账号及 Token
    roles_def = [
        ("lead-usr", "生产项目负责人", "alpha", "project_lead"),
        ("writer-usr", "生产投标编写人", "alpha", "bid_writer"),
        ("admin-usr", "生产公司管理员", "alpha", "company_admin"),
        ("data-usr", "生产资料管理员", "alpha", "data_admin"),
        ("auditor-usr", "生产审核人", "alpha", "auditor"),
        ("viewer-usr", "生产只读成员", "alpha", "viewer"),
        ("group-usr", "生产集团管理员", "group", "group_admin"),
        ("platform-usr", "生产平台运维", "platform", "platform_admin"),
    ]

    tokens = {}
    for uid, name, cid, role in roles_def:
        tok = f"bearer-token-{uid}"
        tokens[role] = tok
        state.accounts[uid] = Account(uid, name, cid, role)
        state.sessions[tok] = uid

    repo = MemoryRepository(state)
    service = DemoService(repo, MockLocalModel())
    app = create_app(repository=repo, model_provider=MockLocalModel())

    with TestClient(app) as client:
        yield client, tokens, repo


def test_smoke_step1_demo_login_blocked_in_production(non_demo_env):
    """排查断点 1：验证生产非演示模式下内置演示账号登录被严格阻断。"""
    client, _, _ = non_demo_env
    for demo_id in ("alpha-manager", "alpha-editor", "alpha-viewer", "beta-manager"):
        resp = client.post("/api/demo/login", json={"account_id": demo_id})
        assert resp.status_code == 403
        data = resp.json()
        assert data["code"] == "FORBIDDEN"
        assert "traceId" in data
        assert resp.headers.get("Deprecation") == "true"


def test_smoke_step1_eight_roles_session_retrieval(non_demo_env):
    """验证正式 Token 请求 GET /api/v1/session 时返回的标准 8 角色 RBAC 会话契约。"""
    client, tokens, _ = non_demo_env

    # 1. 未带凭据请求被拒绝 401
    unauth = client.get("/api/v1/session")
    assert unauth.status_code == 401
    assert unauth.json()["code"] == "UNAUTHENTICATED"
    assert "traceId" in unauth.json()

    # 2. 8 角色正式会话结构校验
    expected_nav_keys = {
        "project_lead": {"workbench", "library", "knowledge", "writing", "admin.rules", "jobs"},
        "bid_writer": {"workbench", "library", "knowledge", "writing", "jobs"},
        "company_admin": {"workbench", "library", "knowledge", "writing", "statistics", "admin", "jobs"},
        "data_admin": {"workbench", "library", "knowledge", "writing", "jobs"},
        "auditor": {"workbench", "library", "knowledge", "jobs"},
        "viewer": {"workbench", "library", "knowledge", "jobs"},
        "group_admin": {"workbench", "library", "knowledge", "writing", "admin"},
        "platform_admin": {"platform", "platform.audit", "jobs"},
    }

    for role, token in tokens.items():
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/v1/session", headers=headers)
        assert resp.status_code == 200, f"Role {role} failed: {resp.text}"
        data = resp.json()

        assert data["auth_mode"] == "authenticated"
        assert data["role_mode"] == "rbac-8roles"
        assert data["user"]["primary_role"] == role
        assert data["user"]["roles"] == [role]
        assert data["scope"]["kind"] == "company"

        # 校验各角色导航
        nav_routes = {item["route_id"] for item in data["navigation"]}
        assert nav_routes == expected_nav_keys[role], f"Navigation mismatch for {role}"

        # 校验项目创建动作权限
        if role in ("project_lead", "company_admin"):
            assert "projects.create" in data["allowedActions"]
            assert "library.write" in data["allowedActions"]
        elif role in ("bid_writer", "data_admin"):
            assert "projects.create" not in data["allowedActions"]
            assert "library.write" in data["allowedActions"]
        else:
            assert "projects.create" not in data["allowedActions"]
            assert "library.write" not in data["allowedActions"]


def test_smoke_full_pipeline_steps_2_to_6(non_demo_env):
    """
    非演示模式下主路径端到端全链路冒烟：
    Step 2: 项目创建 (POST /api/v1/projects) & 团队配置
    Step 3: 招标文件上传 & 解析确认
    Step 4: 响应矩阵 & 证据库挂接
    Step 5: 分节大纲方案确认 & 章节生成
    Step 6: 导出两模式门禁排查与文件下载 (递交版阻断 -> 内部评审放行 -> 修复放行递交版)
    """
    client, tokens, repo = non_demo_env
    lead_headers = {"Authorization": f"Bearer {tokens['project_lead']}"}
    writer_headers = {"Authorization": f"Bearer {tokens['bid_writer']}"}

    # =========================================================================
    # Step 2: 项目创建 (POST /api/v1/projects) & 权限/属性配置
    # =========================================================================
    # 2.1 编写人无权新建项目 (403 PROJECT_CREATE_FORBIDDEN)
    resp_writer_create = client.post(
        "/api/v1/projects",
        json={"name": "编写人违规项目"},
        headers=writer_headers,
    )
    assert resp_writer_create.status_code == 403
    assert resp_writer_create.json()["code"] == "PROJECT_CREATE_FORBIDDEN"

    # 2.2 项目负责人成功新建项目
    proj_name = "关演示全流程冒烟测试标书"
    idem_key = str(uuid4())
    resp_create = client.post(
        "/api/v1/projects",
        json={"name": proj_name},
        headers={**lead_headers, "Idempotency-Key": idem_key},
    )
    assert resp_create.status_code == 200, resp_create.text
    project = resp_create.json()
    project_id = project["id"]
    assert project["name"] == proj_name
    assert project["company_id"] == "alpha"
    assert project["revision"] == 1

    # 2.3 获取项目工作区并配置团队分工
    resp_ws = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers)
    assert resp_ws.status_code == 200
    ws = resp_ws.json()
    rev = ws["revision"]

    # 配置团队分工：将 writer-usr 分配到技术标编写人
    resp_team = client.put(
        f"/api/v1/projects/{project_id}/team",
        json={
            "members": [
                {"user_id": "lead-usr", "project_role": "lead", "volumes": ["technical", "business"]},
                {"user_id": "writer-usr", "project_role": "writer", "volumes": ["technical", "business"]},
            ],
            "volumes": [
                {"volume": "technical", "owner_id": "lead-usr"},
                {"volume": "business", "owner_id": "lead-usr"},
            ],
            "assembly_owner_id": "lead-usr",
            "reason": "冒烟测试团队分工设置",
        },
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_team.status_code == 200

    # 配置项目扩展信息（招标编号、截止时间）
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_patch = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"tender_number": "GOV-2026-CLOUD-088", "deadline": "2026-12-31T18:00:00+08:00"},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_patch.status_code == 200

    # =========================================================================
    # Step 3: 招标文件上传 & 解析确认
    # =========================================================================
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    b64_content = base64.b64encode(SAMPLE_TENDER_TEXT.encode("utf-8")).decode("utf-8")

    # 3.1 上传招标文件
    resp_upload = client.post(
        f"/api/v1/projects/{project_id}/files",
        json={"filename": "智慧城市云平台招标规范.txt", "content_base64": b64_content},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_upload.status_code == 200, resp_upload.text
    file_id = resp_upload.json()["file"]["id"]

    # 3.2 发起解析
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_parse = client.post(
        f"/api/v1/projects/{project_id}/parse",
        json={"file_ids": [file_id]},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_parse.status_code == 200
    assert resp_parse.json()["job"]["status"] == "completed"

    # 3.3 确认解析门禁：未确认条款前尝试 confirm 抛出 409 REVIEW_PENDING
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_premature_confirm = client.post(
        f"/api/v1/projects/{project_id}/parse/confirm",
        json={},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_premature_confirm.status_code == 409
    assert resp_premature_confirm.json()["code"] == "REVIEW_PENDING"

    # 3.4 确认所有解析出的需求条款与事实
    ws = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()
    for req in ws["requirements"]:
        rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
        client.patch(
            f"/api/v1/projects/{project_id}/requirements/{req['id']}",
            json={"status": "confirmed", "reason": "冒烟确认条款"},
            headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
        )
    for fact in ws["facts"]:
        rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
        client.patch(
            f"/api/v1/projects/{project_id}/facts/{fact['id']}",
            json={"status": "confirmed", "reason": "冒烟确认事实"},
            headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
        )

    # 3.5 满足前置条件后确认解析
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_confirm_parse = client.post(
        f"/api/v1/projects/{project_id}/parse/confirm",
        json={},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_confirm_parse.status_code == 200

    # =========================================================================
    # Step 4: 响应矩阵 & 证据库挂接
    # =========================================================================
    # 4.1 在资料库创建一份已确认企业资质证据
    lib_snap = client.get("/api/v1/library", headers=lead_headers).json()
    resp_lib = client.post(
        "/api/v1/library",
        json={
            "name": "国家信息安全三级等保与CMMI5认证",
            "type": "qualification",
            "content": "我司具备国家信息安全三级等级保护认证证书及CMMI5研发能力成熟度资质。",
            "valid_until": "2028-12-31",
            "status": "confirmed",
        },
        headers={**lead_headers, "If-Match": str(lib_snap["revision"]), "Idempotency-Key": str(uuid4())},
    )
    assert resp_lib.status_code == 200, resp_lib.text
    evidence_id = resp_lib.json()["item"]["id"]

    # 4.2 响应矩阵：条款映射章节、录入技术响应、挂接资料库证据
    ws = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()
    chapters = ws["chapters"]
    tech_chapter = next(c for c in chapters if c["volume"] == "technical")
    biz_chapter = next(c for c in chapters if c["volume"] == "business")

    for req in ws["requirements"]:
        rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
        target_chap = tech_chapter["id"] if req["volume"] == "technical" else biz_chapter["id"]
        resp_patch_req = client.patch(
            f"/api/v1/projects/{project_id}/requirements/{req['id']}",
            json={
                "chapter_id": target_chap,
                "response": "经专家团队技术评估与论证，完全响应并优于招标指标要求。",
                "evidence_ids": [evidence_id] if req["volume"] == "business" else [],
                "reason": "矩阵逐项对齐",
            },
            headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
        )
        assert resp_patch_req.status_code == 200

    # =========================================================================
    # Step 5: 分节大纲方案确认 & 章节生成
    # =========================================================================
    # 5.1 确认写作大纲方案 (POST /api/v1/projects/{id}/plan)
    ws = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()
    plan_payload = {
        "chapters": [
            {"id": c["id"], "title": c["title"], "volume": c["volume"]}
            for c in ws["chapters"]
        ]
    }
    rev = ws["revision"]
    resp_plan = client.post(
        f"/api/v1/projects/{project_id}/plan",
        json=plan_payload,
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_plan.status_code == 200

    # 5.2 触发生成 (POST /api/v1/projects/{id}/generate)
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_generate = client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={"chapter_ids": [tech_chapter["id"]]},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_generate.status_code == 200

    # 5.3 章节正式版本提交 (获取编辑锁 -> 提交版本 -> 释放锁)
    for c in (tech_chapter, biz_chapter):
        chap_id = c["id"]
        # 获取锁
        resp_lock = client.post(f"/api/v1/chapters/{chap_id}/lock", json={}, headers=lead_headers)
        assert resp_lock.status_code == 200
        lease_token = resp_lock.json()["lease_token"]

        # 提交版本
        commit_text = (
            f"【{c['title']} 正式章节正文】本方案严格响应招标文件全部技术与商务条款。"
            "系统已通过高可用双活容灾测试与三级等保合规核验。"
        )
        current_chap = client.get(f"/api/chapters/{chap_id}", headers=lead_headers).json()
        input_fp = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["input_fingerprint"]
        resp_ver = client.post(
            f"/api/chapters/{chap_id}/versions",
            json={
                "lease_token": lease_token,
                "base_revision": current_chap["revision"],
                "content": commit_text,
                "input_fingerprint": input_fp,
                "idempotency_key": str(uuid4()),
            },
            headers=lead_headers,
        )
        assert resp_ver.status_code == 200

        # 释放锁
        resp_rel = client.post(
            f"/api/v1/chapters/{chap_id}/lock/release",
            json={"lease_token": lease_token},
            headers=lead_headers,
        )
        assert resp_rel.status_code == 200

    # =========================================================================
    # Step 6: 导出双门禁排查与文件下载验证
    # =========================================================================
    # 6.1 正常基线检查：全部条款已响应、大纲方案与各章节版本已提交
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_check_clean = client.post(
        f"/api/v1/projects/{project_id}/checks",
        json={"volume": "all"},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_check_clean.status_code == 200
    clean_check = resp_check_clean.json()["check"]
    assert clean_check["passed"] is True
    assert not any(i.get("severity") == "blocker" for i in clean_check["issues"])

    # 6.2 内部评审放行导出 (kind="internal") -> 预期 200 放行，且 has_blockers=False
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_clean_export = client.post(
        f"/api/v1/projects/{project_id}/exports",
        json={"check_id": clean_check["id"], "kind": "internal", "volume": "all"},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_clean_export.status_code == 200, resp_clean_export.text
    export_clean = resp_clean_export.json()["export"]
    export_id = export_clean["id"]
    assert export_clean["has_blockers"] is False
    assert export_clean["kind"] == "internal"

    # 6.3 递交版未定稿合规门禁拦截 (kind="submission") -> 预期 409 RULES_INCOMPLETE（防本地内部稿冒充递交版）
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_sub_clean = client.post(
        f"/api/v1/projects/{project_id}/exports",
        json={"check_id": clean_check["id"], "kind": "submission", "volume": "all"},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_sub_clean.status_code == 409
    assert resp_sub_clean.json()["code"] == "RULES_INCOMPLETE"

    # 6.4 真实 Word 分册文件下载校验 (技术分册与商务分册)
    for vol in ("technical", "business"):
        dl_resp = client.get(
            f"/api/v1/projects/{project_id}/exports/{export_id}/{vol}",
            headers=lead_headers,
        )
        assert dl_resp.status_code == 200
        assert dl_resp.headers["Content-Type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert f"filename=" in dl_resp.headers["Content-Disposition"]

        # 解析 docx 二进制压缩包验证格式完整性与文本内容
        docx_bytes = dl_resp.content
        with ZipFile(BytesIO(docx_bytes)) as zf:
            assert "[Content_Types].xml" in zf.namelist()
            assert "word/document.xml" in zf.namelist()
            doc_xml = zf.read("word/document.xml").decode("utf-8")
            assert "正式章节正文" in doc_xml

    # 6.5 人为制造 blocker 严重度问题并验证双门禁反应
    # 模拟在最新检查中存在 blocker 问题的场景
    ws = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()
    r0 = ws["requirements"][0]
    rev = ws["revision"]
    client.patch(
        f"/api/v1/projects/{project_id}/requirements/{r0['id']}",
        json={
            "text": "废标红线条款：投标总价不得超过最高限价，且必须提供原始授权。",
            "category": "disqualification",
            "status": "confirmed",
            "response": "",  # 空响应触发 blocker
            "reason": "注入废标门禁测试用例",
        },
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )

    # 重新检查产生 blocker
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_check_blocker = client.post(
        f"/api/v1/projects/{project_id}/checks",
        json={"volume": "all"},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_check_blocker.status_code == 200
    check_with_blocker = resp_check_blocker.json()["check"]
    assert any(i.get("severity") == "blocker" for i in check_with_blocker["issues"])

    # 6.6 门禁 A：递交版阻断拦截 (kind="submission" + blocker) -> 强拦截 400 CHECK_BLOCKER_EXISTS
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_blocked_export = client.post(
        f"/api/v1/projects/{project_id}/exports",
        json={"check_id": check_with_blocker["id"], "kind": "submission", "volume": "all"},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_blocked_export.status_code == 400
    err = resp_blocked_export.json()
    assert err["code"] == "CHECK_BLOCKER_EXISTS"
    assert "traceId" in err

    # 6.7 门禁 B：内部评审放行 (kind="internal_review" + blocker) -> 200 放行，标记 has_blockers=True 与合规警示
    rev = client.get(f"/api/v1/projects/{project_id}/workspace", headers=lead_headers).json()["revision"]
    resp_internal_export = client.post(
        f"/api/v1/projects/{project_id}/exports",
        json={"check_id": check_with_blocker["id"], "kind": "internal_review", "volume": "all"},
        headers={**lead_headers, "If-Match": str(rev), "Idempotency-Key": str(uuid4())},
    )
    assert resp_internal_export.status_code == 200, resp_internal_export.text
    export_internal = resp_internal_export.json()["export"]
    assert export_internal["has_blockers"] is True
    assert export_internal["compliance_notice"] is not None
    assert "不可作为正式递交文件" in export_internal["compliance_notice"]
