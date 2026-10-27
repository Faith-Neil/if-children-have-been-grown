# 为什么有这个文件：前后端契约联调 INT-STATUS-TAG-METADATA-GLUE 专属集成测试。
# 它解决什么问题：
# 1. 验证 6 大核心业务状态（ProjectStatus、ChapterStatus、JobStatus、CheckStatus、ExportStatus、LockStatus）在 /api/v1/metadata/fields/all 与专用状态接口中的键值与前端 StatusTag 完全对齐；
# 2. 验证非演示模式（VITE_DEMO=0）及 8 大标准 RBAC 角色在多租户下字段元数据的 editable 权限自适应（只读角色自动封退 editable=False，写作者保留可编辑）；
# 3. 验证未知分类 404、未认证 401 与 RFC 7807 统一错误响应对齐。

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import client, login


def test_get_field_metadata_all_category(client: TestClient):
    """验证 GET /api/v1/metadata/fields/all 全量聚合查询接口契约。"""
    headers = login(client, "alpha-manager")
    res = client.get("/api/v1/metadata/fields/all", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["category"] == "all"
    assert data["category_name"] == "全部分类字段元数据"
    assert data["total"] == len(data["fields"])
    assert data["total"] >= 25, f"Expected at least 25 fields in all, got {data['total']}"
    assert data["fields"] == data["items"]

    field_keys = {f["field_key"] for f in data["fields"]}
    # 验证涵盖 6 大核心业务域与历史主营域的标志性字段
    assert "project_name" in field_keys      # project
    assert "status" in field_keys            # project/job/export
    assert "tender_no" in field_keys         # tender
    assert "name" in field_keys              # kb_record
    assert "var_key" in field_keys           # sla
    assert "chapter_title" in field_keys     # chapter
    assert "job_type" in field_keys          # job
    assert "rule_id" in field_keys           # check
    assert "volume_type" in field_keys       # export
    assert "resource_id" in field_keys       # lock


def test_six_status_domains_metadata_mapping_complete(client: TestClient):
    """验证 6 大业务状态码表（项目、章节、长任务、合规检查、导出交付、编辑租约）选项完备性与前端 StatusTag 对齐。"""
    headers = login(client, "alpha-manager")

    # 1. 验证专用状态字典接口 /api/v1/metadata/fields/status 及别名 /statuses
    for ep in ("/api/v1/metadata/fields/status", "/api/v1/metadata/fields/statuses"):
        res = client.get(ep, headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["category"] == "status"
        status_fields = {f["field_key"]: f for f in data["fields"]}

        # 验证 6 大状态字段均在字典中注册
        assert "project_status" in status_fields
        assert "chapter_status" in status_fields
        assert "job_status" in status_fields
        assert "check_status" in status_fields
        assert "export_status" in status_fields
        assert "lock_status" in status_fields

        # 1.1 ProjectStatus 选项核验
        proj_opts = {opt["value"]: opt["label"] for opt in status_fields["project_status"]["options"]}
        for val in ["draft", "parsing", "pending_confirm", "in_progress", "checking", "exportable", "exported", "submitted", "opened", "closed", "cancelled"]:
            assert val in proj_opts, f"Missing project status value: {val}"

        # 1.2 ChapterStatus 选项核验
        chap_opts = {opt["value"]: opt["label"] for opt in status_fields["chapter_status"]["options"]}
        for val in ["not_started", "generating", "draft", "reviewed", "approved", "locked", "stale"]:
            assert val in chap_opts, f"Missing chapter status value: {val}"

        # 1.3 JobStatus 选项核验
        job_opts = {opt["value"]: opt["label"] for opt in status_fields["job_status"]["options"]}
        for val in ["queued", "running", "completed", "failed", "cancelled"]:
            assert val in job_opts, f"Missing job status value: {val}"

        # 1.4 CheckStatus 选项核验
        check_opts = {opt["value"]: opt["label"] for opt in status_fields["check_status"]["options"]}
        for val in ["passed", "warning", "blocker"]:
            assert val in check_opts, f"Missing check status value: {val}"

        # 1.5 ExportStatus 选项核验
        exp_opts = {opt["value"]: opt["label"] for opt in status_fields["export_status"]["options"]}
        for val in ["idle", "processing", "completed", "failed"]:
            assert val in exp_opts, f"Missing export status value: {val}"

        # 1.6 LockStatus 选项核验
        lock_opts = {opt["value"]: opt["label"] for opt in status_fields["lock_status"]["options"]}
        for val in ["unlocked", "locked_self", "locked_other", "expired"]:
            assert val in lock_opts, f"Missing lock status value: {val}"

    # 2. 验证各个专用领域接口均能正常加载自身状态字段
    domain_endpoints = [
        ("chapter", "chapter_status"),
        ("job", "status"),
        ("check", "status"),
        ("export", "status"),
        ("lock", "status"),
    ]
    for domain, status_key in domain_endpoints:
        res_d = client.get(f"/api/v1/metadata/fields/{domain}", headers=headers)
        assert res_d.status_code == 200, f"Domain {domain} failed: {res_d.text}"
        data_d = res_d.json()
        assert data_d["category"] == domain
        f_map = {f["field_key"]: f for f in data_d["fields"]}
        assert status_key in f_map, f"{status_key} not in {domain} fields"
        assert f_map[status_key]["render_type"] == "tag"
        assert len(f_map[status_key]["options"]) >= 3


def test_rbac_editable_permission_matrix_across_8_roles(client: TestClient):
    """验证 8 大标准 RBAC 角色在多租户会话下的字段 editable 权限自适应矩阵。"""
    # 具备写权限的角色：字段保留定义中的可编辑性（如 project_name 为 True，status 为 False）
    writable_accounts = [
        ("alpha-manager", "project_lead"),
        ("alpha-editor", "bid_writer"),
        ("alpha-company-admin", "company_admin"),
        ("alpha-data-admin", "data_admin"),
    ]
    for acc_id, role_name in writable_accounts:
        headers = login(client, acc_id)
        res = client.get("/api/v1/metadata/fields/project", headers=headers)
        assert res.status_code == 200, f"{acc_id} failed"
        fields = {f["field_key"]: f for f in res.json()["fields"]}
        assert fields["project_name"]["editable"] is True, f"{acc_id} ({role_name}) should have project_name editable=True"
        assert fields["status"]["editable"] is False

    # 只读系统角色：所有字段均被自适应封退为 editable=False
    readonly_accounts = [
        ("alpha-viewer", "viewer"),
        ("alpha-auditor", "auditor"),
        ("alpha-group-admin", "group_admin"),
        ("platform-admin", "platform_admin"),
    ]
    for acc_id, role_name in readonly_accounts:
        headers = login(client, acc_id)
        # 测试单一分类
        res = client.get("/api/v1/metadata/fields/project", headers=headers)
        assert res.status_code == 200, f"{acc_id} failed"
        for field in res.json()["fields"]:
            assert field["editable"] is False, f"Readonly role {role_name} ({acc_id}) field {field['field_key']} must have editable=False"

        # 测试全量分类 all
        res_all = client.get("/api/v1/metadata/fields/all", headers=headers)
        assert res_all.status_code == 200, f"{acc_id} all failed"
        for field in res_all.json()["fields"]:
            assert field["editable"] is False, f"Readonly role {role_name} ({acc_id}) field {field['field_key']} in all must have editable=False"


def test_field_metadata_security_and_rfc7807_error_compliance(client: TestClient):
    """验证未登录 401、未知分类 404 与 RFC 7807 统一错误体合规性。"""
    # 1. 未传 Token 拦截 401
    res_401_no_token = client.get("/api/v1/metadata/fields/all")
    assert res_401_no_token.status_code == 401
    body_401 = res_401_no_token.json()
    assert body_401["code"] == "UNAUTHENTICATED"
    assert "traceId" in body_401

    # 2. 非法 Token 拦截 401
    res_401_bad_token = client.get(
        "/api/v1/metadata/fields/all",
        headers={"Authorization": "Bearer bad-jwt-token-9999"}
    )
    assert res_401_bad_token.status_code == 401
    assert res_401_bad_token.json()["code"] == "UNAUTHENTICATED"

    # 3. 未知分类返回 404 NOT_FOUND
    headers = login(client, "alpha-manager")
    res_404 = client.get("/api/v1/metadata/fields/non_existent_category_foo", headers=headers)
    assert res_404.status_code == 404
    body_404 = res_404.json()
    assert body_404["code"] == "NOT_FOUND"
    assert "未找到该分类的字段元数据" in body_404["message"]
    assert "traceId" in body_404
    assert res_404.headers.get("X-Request-ID") == body_404["traceId"]
