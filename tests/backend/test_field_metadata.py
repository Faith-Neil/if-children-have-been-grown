# 为什么有这个文件：验证字段元数据接口 getFieldMetadata（APP-M2-T005 / T006 前置）契约与业务逻辑。
# 它解决什么问题：确保 project、tender、kb_record、sla 等分类的元数据结构完备，
# 验证 401 未登录、404 分类不存在与不同角色账号权限控制。

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import client, login


def test_field_metadata_unauthenticated_returns_401(client: TestClient):
    """未携带 Bearer Token 或 Token 无效时，必须拦截 401 UNAUTHENTICATED。"""
    # 1. 完全不传 Authorization 请求头
    res = client.get("/api/v1/metadata/fields/project")
    assert res.status_code == 401
    body = res.json()
    assert body["code"] == "UNAUTHENTICATED"
    assert "traceId" in body
    assert res.headers.get("X-Request-ID") == body["traceId"]

    # 2. 携带无效或非法 Token
    res_invalid = client.get(
        "/api/v1/metadata/fields/project",
        headers={"Authorization": "Bearer invalid-token-12345"}
    )
    assert res_invalid.status_code == 401
    assert res_invalid.json()["code"] == "UNAUTHENTICATED"


def test_get_field_metadata_for_all_supported_categories(client: TestClient):
    """验证四大核心业务分类（project, tender, kb_record, sla）元数据完整读取。"""
    headers = login(client, "alpha-manager")

    # 1. 投标项目分类 project
    res_project = client.get("/api/v1/metadata/fields/project", headers=headers)
    assert res_project.status_code == 200, res_project.text
    data_proj = res_project.json()
    assert data_proj["category"] == "project"
    assert data_proj["category_name"] == "投标项目"
    assert data_proj["total"] == len(data_proj["fields"])
    assert data_proj["total"] >= 10

    fields_dict_proj = {f["field_key"]: f for f in data_proj["fields"]}
    assert "project_name" in fields_dict_proj
    p_name = fields_dict_proj["project_name"]
    assert p_name["label"] == "项目名称"
    assert p_name["data_type"] == "string"
    assert p_name["required"] is True
    assert p_name["editable"] is True
    assert p_name["is_starred"] is True
    assert p_name["render_type"] == "text"
    assert p_name["system_key"] == "project_name"

    assert "is_sensitive" in fields_dict_proj
    assert fields_dict_proj["is_sensitive"]["render_type"] == "badge"
    assert fields_dict_proj["is_sensitive"]["data_type"] == "boolean"

    assert "status" in fields_dict_proj
    p_status = fields_dict_proj["status"]
    assert p_status["render_type"] == "tag"
    assert p_status["editable"] is False
    assert any(opt["value"] == "draft" for opt in p_status["options"])
    assert any(opt["value"] == "in_progress" for opt in p_status["options"])

    assert "budget_amount" in fields_dict_proj
    assert fields_dict_proj["budget_amount"]["align"] == "right"
    assert fields_dict_proj["budget_amount"]["render_type"] == "number"

    # 2. 招标要求分类 tender
    res_tender = client.get("/api/v1/metadata/fields/tender", headers=headers)
    assert res_tender.status_code == 200, res_tender.text
    data_tender = res_tender.json()
    assert data_tender["category"] == "tender"
    assert data_tender["category_name"] == "招标要求与抽取条目"
    fields_dict_tender = {f["field_key"]: f for f in data_tender["fields"]}

    assert "category" in fields_dict_tender
    assert any(opt["value"] == "qualification" for opt in fields_dict_tender["category"]["options"])

    assert "importance" in fields_dict_tender
    assert fields_dict_tender["importance"]["is_starred"] is True
    assert fields_dict_tender["importance"]["render_type"] == "badge"

    assert "quote_text" in fields_dict_tender
    assert fields_dict_tender["quote_text"]["render_type"] == "cite"

    assert "confidence" in fields_dict_tender
    assert fields_dict_tender["confidence"]["render_type"] == "number"

    # 3. 投标资料库分类 kb_record
    res_kb = client.get("/api/v1/metadata/fields/kb_record", headers=headers)
    assert res_kb.status_code == 200, res_kb.text
    data_kb = res_kb.json()
    assert data_kb["category"] == "kb_record"
    assert data_kb["category_name"] == "企业投标资料库"
    fields_dict_kb = {f["field_key"]: f for f in data_kb["fields"]}

    assert "name" in fields_dict_kb
    assert fields_dict_kb["name"]["required"] is True
    assert fields_dict_kb["name"]["is_starred"] is True

    assert "valid_until" in fields_dict_kb
    assert fields_dict_kb["valid_until"]["render_type"] == "date"
    assert fields_dict_kb["valid_until"]["data_type"] == "date"

    assert "source_tier" in fields_dict_kb
    assert any(opt["value"] == "own" for opt in fields_dict_kb["source_tier"]["options"])

    assert "id_number_masked" in fields_dict_kb
    assert fields_dict_kb["id_number_masked"]["is_sensitive"] is True
    assert fields_dict_kb["id_number_masked"]["render_type"] == "masked"

    # 4. 服务承诺与 SLA 分类 sla
    res_sla = client.get("/api/v1/metadata/fields/sla", headers=headers)
    assert res_sla.status_code == 200, res_sla.text
    data_sla = res_sla.json()
    assert data_sla["category"] == "sla"
    assert data_sla["category_name"] == "服务承诺与SLA"
    fields_dict_sla = {f["field_key"]: f for f in data_sla["fields"]}

    assert "var_key" in fields_dict_sla
    assert "project_value" in fields_dict_sla
    assert fields_dict_sla["project_value"]["align"] == "right"
    assert fields_dict_sla["project_value"]["required"] is True

    assert "sla_group" in fields_dict_sla
    assert any(opt["value"] == "response_time" for opt in fields_dict_sla["sla_group"]["options"])

    assert "exceeds_capability" in fields_dict_sla
    assert fields_dict_sla["exceeds_capability"]["render_type"] == "badge"


def test_field_metadata_category_aliases(client: TestClient):
    """验证别名能平滑解析为规范分类（如 library -> kb_record, bid_project -> project）。"""
    headers = login(client, "alpha-editor")

    # 别名映射测试
    alias_cases = [
        ("bid_project", "project"),
        ("projects", "project"),
        ("tender_requirement", "tender"),
        ("requirement", "tender"),
        ("library", "kb_record"),
        ("kb", "kb_record"),
        ("project_sla", "sla"),
        ("sla_value", "sla"),
    ]

    for alias, expected_canonical in alias_cases:
        res = client.get(f"/api/v1/metadata/fields/{alias}", headers=headers)
        assert res.status_code == 200, f"Failed for alias: {alias}"
        data = res.json()
        assert data["category"] == expected_canonical


def test_nonexistent_category_returns_404(client: TestClient):
    """请求不存在的元数据分类，必须返回 404 NOT_FOUND。"""
    headers = login(client, "alpha-manager")
    res = client.get("/api/v1/metadata/fields/unknown_finance_category", headers=headers)
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "NOT_FOUND"
    assert "未找到该分类的字段元数据" in body["message"]
    assert "traceId" in body
    assert res.headers.get("X-Request-ID") == body["traceId"]


def test_permission_access_across_roles(client: TestClient):
    """验证系统各角色账号（项目负责人、编写人、只读查看人）均能正常加载表格/表单元数据。"""
    roles = ["alpha-manager", "alpha-editor", "alpha-viewer", "beta-manager"]
    for role_account in roles:
        headers = login(client, role_account)
        res = client.get("/api/v1/metadata/fields/project", headers=headers)
        assert res.status_code == 200, f"Role {role_account} failed to load project metadata"
        data = res.json()
        assert data["category"] == "project"
        assert len(data["fields"]) > 0


def test_field_metadata_structure_and_constraints(client: TestClient):
    """验证所有返回字段项严格包含规范所要求的核心键与枚举值域。"""
    headers = login(client, "alpha-manager")
    for category in ("project", "tender", "kb_record", "sla"):
        res = client.get(f"/api/v1/metadata/fields/{category}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "category" in data
        assert "category_name" in data
        assert "total" in data
        assert "fields" in data
        assert "items" in data
        assert data["fields"] == data["items"]

        for item in data["fields"]:
            assert isinstance(item["field_key"], str) and len(item["field_key"]) > 0
            assert isinstance(item["label"], str) and len(item["label"]) > 0
            assert item["data_type"] in ("string", "integer", "number", "boolean", "date", "datetime", "array", "object")
            assert isinstance(item["required"], bool)
            assert isinstance(item["editable"], bool)
            assert item["align"] in ("left", "center", "right")
            assert item["render_type"] in ("text", "tag", "badge", "date", "datetime", "number", "cite", "masked", "link", "select")
            assert isinstance(item["filterable"], bool)
            assert isinstance(item["sortable"], bool)
            assert isinstance(item["is_starred"], bool)
            assert isinstance(item["is_sensitive"], bool)
            if item.get("options") is not None:
                assert isinstance(item["options"], list)
                for opt in item["options"]:
                    assert "value" in opt and "label" in opt
