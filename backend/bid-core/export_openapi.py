# 为什么有这个文件：从实际后端代码导出请求和响应约定，并在 CI 门禁中检验生成一致性。
# 它解决什么问题：避免接口文档与可运行代码采用两套字段；禁止手工维护巨型契约；提供自动化生成与 diff 门禁。

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 确保在任何工作目录下均能载入 icg_demo
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BID_CORE_DIR = Path(__file__).resolve().parent
if str(BID_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(BID_CORE_DIR))

from icg_demo.main import app


SPEC_TARGET = PROJECT_ROOT / "spec" / "openapi" / "demo-v1.json"
FROZEN_STATUS = "frozen"
WRITES_WITHOUT_IDEMPOTENCY_KEY = "没有 Idempotency-Key 的写入不自动重试。"
DEPRECATION_NOTE = "已废弃。新旧入口并存。前端改用 getOutlinePlan、confirmOutlinePlan 与 startGeneration 之后，由后续 Issue 删除本操作。运行时尚未标出 deprecated。"
DEPRECATED_OPERATIONS = (
    "/api/v1/projects/{project_id}/plan",
    "/api/v1/projects/{project_id}/generate",
    "/api/v1/projects/{project_id}/chapters/{chapter_id}/plan/confirm",
)


def implemented_contract(document: dict) -> dict:
    """提取已落地契约，过滤已冻结但未实现的扩展元数据。"""
    spec = json.loads(json.dumps(document))
    spec.pop("x-contract-drafts", None)
    for path, item in list(spec["paths"].items()):
        if isinstance(item, dict) and item.get("x-contract-status") == FROZEN_STATUS:
            del spec["paths"][path]
    for path in DEPRECATED_OPERATIONS:
        if path in spec["paths"] and "post" in spec["paths"][path]:
            operation = spec["paths"][path]["post"]
            operation.pop("deprecated", None)
            if operation.get("description") == DEPRECATION_NOTE:
                operation.pop("description", None)
    schemas = spec.get("components", {}).get("schemas", {})
    for name, body in list(schemas.items()):
        if isinstance(body, dict) and body.get("x-contract-status") == FROZEN_STATUS:
            del schemas[name]
    for item in spec["paths"].values():
        if not isinstance(item, dict):
            continue
        for operation in item.values():
            if isinstance(operation, dict):
                operation.pop("x-issue-033", None)
    idempotency = spec.get("components", {}).get("x-idempotency")
    if isinstance(idempotency, dict) and isinstance(idempotency.get("retry"), str):
        idempotency["retry"] = idempotency["retry"].removesuffix(WRITES_WITHOUT_IDEMPOTENCY_KEY)
    return spec


def check_consistency(target: Path = SPEC_TARGET) -> int:
    """CI 门禁：校验代码生成的 OpenAPI 与已提交的规范文件是否 100% 一致。"""
    if not target.exists():
        print(f"Error: Target OpenAPI spec does not exist: {target}", file=sys.stderr)
        return 1

    stored_raw = json.loads(target.read_text(encoding="utf-8"))
    contract = implemented_contract(stored_raw)
    current_schema = app.openapi()

    if contract == current_schema:
        print(f"[OK] OpenAPI contract ({target.name}) is 100% consistent with running FastAPI application.")
        return 0
    else:
        print(f"[FAIL] OpenAPI contract mismatch between code and {target.name}!", file=sys.stderr)
        return 1


def export_openapi(target: Path = SPEC_TARGET) -> None:
    """从运行中的 FastAPI 应用导出最新 OpenAPI 规范，保留契约扩展字段。"""
    generated = app.openapi()
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        stored_raw = json.loads(target.read_text(encoding="utf-8"))
        # 保留规范特有的扩展元数据
        if "x-contract-drafts" in stored_raw:
            generated["x-contract-drafts"] = stored_raw["x-contract-drafts"]
        for path, item in stored_raw.get("paths", {}).items():
            if isinstance(item, dict) and item.get("x-contract-status") == FROZEN_STATUS:
                generated["paths"][path] = item
            if path in generated["paths"] and isinstance(item, dict):
                for op_key, op_val in item.items():
                    if isinstance(op_val, dict) and "x-issue-033" in op_val:
                        if op_key in generated["paths"][path]:
                            generated["paths"][path][op_key]["x-issue-033"] = op_val["x-issue-033"]
                    if path in DEPRECATED_OPERATIONS and op_key == "post":
                        if op_key in generated["paths"][path]:
                            generated["paths"][path][op_key]["deprecated"] = True
                            generated["paths"][path][op_key]["description"] = DEPRECATION_NOTE
        for schema_name, schema_body in stored_raw.get("components", {}).get("schemas", {}).items():
            if isinstance(schema_body, dict) and schema_body.get("x-contract-status") == FROZEN_STATUS:
                generated["components"]["schemas"][schema_name] = schema_body
        if "x-idempotency" in stored_raw.get("components", {}):
            generated["components"]["x-idempotency"] = stored_raw["components"]["x-idempotency"]

    target.write_text(json.dumps(generated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI exported successfully to: {target.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export or verify FastAPI OpenAPI specification.")
    parser.add_argument("--check", action="store_true", help="Check consistency between code and OpenAPI spec (returns exit code 1 if diff exists)")
    args = parser.parse_args()

    if args.check:
        sys.exit(check_consistency())
    else:
        export_openapi()
