# 为什么有这个文件：验证 OpenAPI 契约与运行时各路由的 operationId 规范。
# 它解决什么问题：确保所有操作拥有全局唯一、规范的 lowerCamelCase operationId，避免自动生成的 _api_ 冗余前缀和接口名冲突。

import json
import re
from pathlib import Path

import pytest
from icg_demo.main import create_app
from test_error_idempotency import SPEC, implemented_contract

CAMEL_PATTERN = re.compile(r"^[a-z][A-Za-z0-9]*$")
HTTP_METHODS = {"get", "post", "put", "delete", "patch"}


def get_operations_from_spec(paths_dict: dict) -> list[tuple[str, str, str]]:
    """返回 (method, path, operation_id) 列表"""
    operations = []
    for path, item in paths_dict.items():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                op_id = operation.get("operationId")
                operations.append((method.upper(), path, op_id))
    return operations


def test_running_app_all_operation_ids_valid_camel_case_and_no_api_prefix():
    app = create_app()
    schema = app.openapi()
    operations = get_operations_from_spec(schema.get("paths", {}))

    assert len(operations) > 0, "No operations found in running app schema"

    for method, path, op_id in operations:
        assert op_id is not None, f"Missing operationId for {method} {path}"
        assert isinstance(op_id, str) and len(op_id) > 0, f"Empty operationId for {method} {path}"
        assert "_api_" not in op_id, f"operationId '{op_id}' for {method} {path} contains auto-generated '_api_' prefix"
        assert "_" not in op_id, f"operationId '{op_id}' for {method} {path} contains underscores, should be lowerCamelCase"
        assert CAMEL_PATTERN.match(op_id), f"operationId '{op_id}' for {method} {path} does not match lowerCamelCase pattern"


def test_running_app_operation_ids_are_globally_unique():
    app = create_app()
    schema = app.openapi()
    operations = get_operations_from_spec(schema.get("paths", {}))

    seen = {}
    duplicates = []
    for method, path, op_id in operations:
        endpoint = f"{method} {path}"
        if op_id in seen:
            duplicates.append((op_id, seen[op_id], endpoint))
        else:
            seen[op_id] = endpoint

    assert duplicates == [], f"Duplicate operationId found: {duplicates}"


def test_spec_demo_v1_json_all_operation_ids_valid_and_globally_unique():
    raw = json.loads(SPEC.read_text(encoding="utf-8"))
    operations = get_operations_from_spec(raw.get("paths", {}))

    assert len(operations) >= 70, f"Expected at least 70 operations in spec, found {len(operations)}"

    seen = {}
    duplicates = []
    for method, path, op_id in operations:
        assert op_id is not None and len(op_id) > 0, f"Missing operationId in spec for {method} {path}"
        assert "_api_" not in op_id, f"Spec operationId '{op_id}' contains '_api_'"
        assert "_" not in op_id, f"Spec operationId '{op_id}' contains underscores"
        assert CAMEL_PATTERN.match(op_id), f"Spec operationId '{op_id}' is not lowerCamelCase"

        endpoint = f"{method} {path}"
        if op_id in seen:
            duplicates.append((op_id, seen[op_id], endpoint))
        else:
            seen[op_id] = endpoint

    assert duplicates == [], f"Duplicate operationId found in spec: {duplicates}"


def test_well_known_operation_ids():
    raw = json.loads(SPEC.read_text(encoding="utf-8"))
    paths = raw["paths"]

    # Verify key backward-compatible and explicitly named endpoints
    assert paths["/api/v1/session"]["get"]["operationId"] == "getSession"
    assert paths["/api/projects"]["get"]["operationId"] == "listProjects"
    assert paths["/api/projects"]["post"]["operationId"] == "createProject"
    assert paths["/api/v1/projects/{project_id}/exports"]["post"]["operationId"] == "exportVolume"
    assert paths["/api/v1/projects/{project_id}/exports/{export_id}/{volume}"]["get"]["operationId"] == "downloadVolume"

    # Recoverable jobs
    assert paths["/api/v1/projects/{project_id}/generation/start"]["post"]["operationId"] == "startGeneration"
    assert paths["/api/v1/jobs/{job_id}"]["get"]["operationId"] == "getJob"
    assert paths["/api/v1/jobs/{job_id}/events"]["get"]["operationId"] == "streamJobEvents"
    assert paths["/api/v1/jobs/{job_id}/cancel"]["post"]["operationId"] == "cancelJob"

    # Chapter locks
    assert paths["/api/v1/chapters/{chapter_id}/lock"]["post"]["operationId"] == "acquireChapterLock"
    assert paths["/api/v1/chapters/{chapter_id}/lock/renew"]["post"]["operationId"] == "renewChapterLock"
    assert paths["/api/v1/chapters/{chapter_id}/lock/release"]["post"]["operationId"] == "releaseChapterLock"

    # Frozen drafts
    assert paths["/api/v1/projects/{project_id}/outline/plan"]["get"]["operationId"] == "getOutlinePlan"
    assert paths["/api/v1/projects/{project_id}/outline/plan/confirm"]["post"]["operationId"] == "confirmOutlinePlan"


def test_implemented_contract_matches_running_schema():
    raw = json.loads(SPEC.read_text(encoding="utf-8"))
    schema = create_app().openapi()
    assert implemented_contract(raw) == schema
