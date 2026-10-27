# 为什么有这个文件：前后端契约联调工单 INT-DICT-CONFIG-RBAC-GLUE 专属端到端集成测试。
# 它解决什么问题：
# 1. 验证数据字典与状态码表配置（/api/v1/metadata/dict/*）在平台管理员与公司管理员下的全生命周期（创建、启停用、属性更新、安全删除）；
# 2. 验证核心安全红线：“已使用或系统内置的字典代码只能停用，严禁物理硬删除”，拦截 409 DICT_ITEM_IN_USE；
# 3. 验证同分类下代码唯一性约束，重复代码拦截 409 DICT_CODE_DUPLICATED；
# 4. 验证严格的 8 角色 RBAC 权限隔离：普通写作者（bid_writer）、项目负责人（project_lead）、审计员（auditor）、观察员（viewer）写操作全量拦截 403 FORBIDDEN；
# 5. 验证多租户数据隔离语义及 RFC 7807 统一错误响应规范（code, message, details, traceId 与 X-Request-ID）。

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import client, login


def test_list_dict_types_and_items(client: TestClient):
    """验证 GET /api/v1/metadata/dict/types 与 listDictItems 字典调阅契约。"""
    headers = login(client, "alpha-company-admin")

    # 1. 查询全部字典分类
    res = client.get("/api/v1/metadata/dict/types", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] == len(data["items"])
    assert data["total"] >= 10, f"Expected at least 10 dict types, got {data['total']}"

    types_map = {t["type_code"]: t for t in data["items"]}
    assert "project_status" in types_map
    assert "chapter_status" in types_map
    assert "job_status" in types_map
    assert "check_status" in types_map
    assert "export_status" in types_map
    assert "lock_status" in types_map
    assert "requirement_category" in types_map
    assert "source_tier" in types_map
    assert "sla_group" in types_map

    # 2. 调阅合规检查状态 check_status 的代码项
    res_items = client.get("/api/v1/metadata/dict/types/check_status/items", headers=headers)
    assert res_items.status_code == 200, res_items.text
    items_data = res_items.json()
    assert items_data["type_code"] == "check_status"
    assert items_data["total"] >= 3

    check_codes = {item["item_code"]: item for item in items_data["items"]}
    assert "passed" in check_codes
    assert "warning" in check_codes
    assert "blocker" in check_codes
    assert check_codes["blocker"]["is_builtin"] is True
    assert check_codes["blocker"]["in_use"] is True
    assert check_codes["blocker"]["is_disabled"] is False


def test_admin_create_and_toggle_disable_dict_item(client: TestClient):
    """验证管理员创建自定义字典项、启用/停用切换及标签更新。"""
    headers = login(client, "alpha-company-admin")

    # 1. 创建自定义字典代码项
    create_payload = {
        "type_code": "requirement_category",
        "item_code": "esg_sustainability",
        "label": "ESG 与绿色低碳要求",
        "description": "节能减排、环境保护与社会责任等绿色合规要求",
        "sort_order": 90,
        "metadata": {"icon": "leaf", "is_starred": True},
    }
    res_create = client.post("/api/v1/metadata/dict/items", headers=headers, json=create_payload)
    assert res_create.status_code == 201, res_create.text
    created = res_create.json()
    assert created["type_code"] == "requirement_category"
    assert created["item_code"] == "esg_sustainability"
    assert created["label"] == "ESG 与绿色低碳要求"
    assert created["is_builtin"] is False
    assert created["in_use"] is False
    assert created["is_disabled"] is False
    assert created["company_id"] == "alpha"

    # 2. 停用该字典项 (is_disabled = True)
    res_disable = client.patch(
        "/api/v1/metadata/dict/items/requirement_category/esg_sustainability",
        headers=headers,
        json={"is_disabled": True},
    )
    assert res_disable.status_code == 200, res_disable.text
    assert res_disable.json()["is_disabled"] is True

    # 3. 验证列表查询带 include_disabled=False 时不返回停用项
    res_active_only = client.get(
        "/api/v1/metadata/dict/types/requirement_category/items?include_disabled=false",
        headers=headers,
    )
    assert res_active_only.status_code == 200
    active_codes = [i["item_code"] for i in res_active_only.json()["items"]]
    assert "esg_sustainability" not in active_codes

    # 4. 重新启用 (is_disabled = False) 并更新标签
    res_enable = client.patch(
        "/api/v1/metadata/dict/items/requirement_category/esg_sustainability",
        headers=headers,
        json={"is_disabled": False, "label": "ESG 绿色节能标准 (修订)"},
    )
    assert res_enable.status_code == 200
    updated = res_enable.json()
    assert updated["is_disabled"] is False
    assert updated["label"] == "ESG 绿色节能标准 (修订)"


def test_duplicate_dict_code_blocked_409(client: TestClient):
    """验证同分类下字典代码重复冲突拦截 409 DICT_CODE_DUPLICATED 及 RFC 7807 规范体。"""
    headers = login(client, "alpha-company-admin")

    # 尝试创建与内置代码 qualification 重复的项
    duplicate_payload = {
        "type_code": "requirement_category",
        "item_code": "qualification",
        "label": "重复的资质要求",
    }
    res = client.post("/api/v1/metadata/dict/items", headers=headers, json=duplicate_payload)
    assert res.status_code == 409, res.text

    err = res.json()
    assert err["code"] == "DICT_CODE_DUPLICATED"
    assert "qualification" in err["message"]
    assert "traceId" in err
    assert res.headers.get("X-Request-ID") == err["traceId"]


def test_delete_in_use_or_builtin_dict_item_blocked_409(client: TestClient):
    """验证核心安全红线：在用与内置字典项坚决禁止物理硬删除，拦截 409 DICT_ITEM_IN_USE。"""
    headers = login(client, "alpha-company-admin")

    # 1. 尝试删除系统内置且在用的 check_status/blocker
    res_del_builtin = client.delete(
        "/api/v1/metadata/dict/items/check_status/blocker",
        headers=headers,
    )
    assert res_del_builtin.status_code == 409, res_del_builtin.text
    err = res_del_builtin.json()
    assert err["code"] == "DICT_ITEM_IN_USE"
    assert "内置" in err["message"] or "只能停用" in err["message"]
    assert "traceId" in err
    assert res_del_builtin.headers.get("X-Request-ID") == err["traceId"]

    # 2. 尝试删除系统内置的 project_status/draft
    res_del_draft = client.delete(
        "/api/v1/metadata/dict/items/project_status/draft",
        headers=headers,
    )
    assert res_del_draft.status_code == 409
    assert res_del_draft.json()["code"] == "DICT_ITEM_IN_USE"

    # 3. 正常删除未被业务引用的自定义代码项
    # 先创建一个临时自定义项
    client.post(
        "/api/v1/metadata/dict/items",
        headers=headers,
        json={
            "type_code": "requirement_category",
            "item_code": "temp_delete_target",
            "label": "待删除的临时代码",
        },
    )
    res_del_custom = client.delete(
        "/api/v1/metadata/dict/items/requirement_category/temp_delete_target",
        headers=headers,
    )
    assert res_del_custom.status_code == 200, res_del_custom.text
    del_data = res_del_custom.json()
    assert del_data["success"] is True
    assert del_data["item_code"] == "temp_delete_target"

    # 再次删除已不存在的项应返回 404 NOT_FOUND
    res_del_404 = client.delete(
        "/api/v1/metadata/dict/items/requirement_category/temp_delete_target",
        headers=headers,
    )
    assert res_del_404.status_code == 404
    assert res_del_404.json()["code"] == "NOT_FOUND"


def test_role_rbac_write_forbidden_403(client: TestClient):
    """验证写作者、项目负责人、观察员、审计员等角色发起写操作被严格拦截 403 FORBIDDEN。"""
    non_admin_accounts = [
        ("alpha-editor", "bid_writer"),
        ("alpha-manager", "project_lead"),
        ("alpha-viewer", "viewer"),
        ("alpha-auditor", "auditor"),
        ("alpha-group-admin", "group_admin"),
        ("alpha-data-admin", "data_admin"),
    ]

    for acc_id, role_name in non_admin_accounts:
        headers = login(client, acc_id)

        # 1. 尝试 POST 新增字典项
        res_post = client.post(
            "/api/v1/metadata/dict/items",
            headers=headers,
            json={
                "type_code": "requirement_category",
                "item_code": f"unauthorized_{role_name}",
                "label": "越权新增测试",
            },
        )
        assert res_post.status_code == 403, f"{acc_id} ({role_name}) POST should be 403, got {res_post.status_code}"
        err_post = res_post.json()
        assert err_post["code"] == "FORBIDDEN"
        assert "traceId" in err_post

        # 2. 尝试 PATCH 更新字典项
        res_patch = client.patch(
            "/api/v1/metadata/dict/items/requirement_category/qualification",
            headers=headers,
            json={"label": "越权修改标签"},
        )
        assert res_patch.status_code == 403, f"{acc_id} ({role_name}) PATCH should be 403, got {res_patch.status_code}"
        assert res_patch.json()["code"] == "FORBIDDEN"

        # 3. 尝试 DELETE 删除字典项
        res_del = client.delete(
            "/api/v1/metadata/dict/items/requirement_category/qualification",
            headers=headers,
        )
        assert res_del.status_code == 403, f"{acc_id} ({role_name}) DELETE should be 403, got {res_del.status_code}"
        assert res_del.json()["code"] == "FORBIDDEN"


def test_unauthenticated_request_blocked_401(client: TestClient):
    """验证未认证请求拦截 401 UNAUTHENTICATED。"""
    res = client.get("/api/v1/metadata/dict/types")
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_tenant_isolation_dict_items(client: TestClient):
    """验证公司多租户数据隔离：Company Alpha 创建的自定义代码对 Company Beta 隔离不可见，平台管理员可见。"""
    headers_alpha = login(client, "alpha-company-admin")
    headers_beta = login(client, "beta-manager")
    headers_platform = login(client, "platform-admin")

    # Alpha 创建专属自定义字典项
    res_create = client.post(
        "/api/v1/metadata/dict/items",
        headers=headers_alpha,
        json={
            "type_code": "requirement_category",
            "item_code": "alpha_private_spec",
            "label": "Alpha 专有需求规范",
        },
    )
    assert res_create.status_code == 201

    # Beta 查阅同分类字典项，不应包含 Alpha 专有项
    res_beta = client.get(
        "/api/v1/metadata/dict/types/requirement_category/items",
        headers=headers_beta,
    )
    assert res_beta.status_code == 200
    beta_items = [i["item_code"] for i in res_beta.json()["items"]]
    assert "alpha_private_spec" not in beta_items, "Tenant isolation leak: Beta can see Alpha's custom item"

    # Platform Admin 查阅，可跨租户调阅
    res_platform = client.get(
        "/api/v1/metadata/dict/types/requirement_category/items",
        headers=headers_platform,
    )
    assert res_platform.status_code == 200
    platform_items = [i["item_code"] for i in res_platform.json()["items"]]
    assert "alpha_private_spec" in platform_items
