# 为什么有这个文件：核对 ISSUE-033 挂证据字段和拒绝规则。
# 它解决什么问题：避免新增错误码，并确认运行时已按冻结字段名执行。

import json

from icg_demo.errors import ERROR_STATUS
from icg_demo.frozen_error_codes import FROZEN_NAMES
from icg_demo.main import create_app
from test_error_idempotency import SPEC, implemented_contract

LIBRARY = "/api/v1/library"
REQUIREMENT = "/api/v1/projects/{project_id}/requirements/{requirement_id}"


def load_spec():
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_evidence_mount_fields_follow_dictionary_v19_and_reuse_codes():
    spec = load_spec()
    fields = spec["components"]["schemas"]["EvidenceMountFields"]
    assert fields["x-contract-status"] == "frozen"
    assert fields["x-implemented"] is False
    assert fields["x-aligned-with"] == "BE-M0-T18"
    props = fields["properties"]
    assert list(props) == ["source_tier", "is_restricted", "agreement_present", "valid_to", "is_long_term"]
    assert "restricted" not in props
    assert props["source_tier"]["enum"] == ["own", "partner", "reference"]
    assert "reference" in props["source_tier"]["description"]
    assert props["is_restricted"]["type"] == "boolean"
    assert props["is_restricted"]["default"] is False
    assert "resource_acl" in props["is_restricted"]["description"]
    assert props["agreement_present"]["readOnly"] is True
    assert "派生" in props["agreement_present"]["description"]
    assert "agreement_attachment_id" in props["agreement_present"]["description"]
    assert "不入库" in props["agreement_present"]["description"]
    assert "bid_deadline_at" in props["valid_to"]["description"]
    assert "今天" in props["valid_to"]["description"]
    assert "expiring" in props["valid_to"]["description"]
    assert "unknown" in props["valid_to"]["description"]
    assert props["is_long_term"]["default"] is False

    mount = spec["paths"][REQUIREMENT]["patch"]["x-issue-033"]
    assert mount["x-implemented"] is True
    rules = "\n".join(mount["rules"])
    assert "409 EVIDENCE_EXPIRED" in rules
    assert "409 EVIDENCE_NOT_USABLE" in rules
    assert "403 FORBIDDEN" in rules
    assert "expiring" in rules and "允许挂接" in rules
    assert "unknown" in rules and "不返回 409" in rules
    assert mount["compare_deadline"] == "bid_deadline_at"
    library = spec["paths"][LIBRARY]["get"]["x-issue-033"]
    assert library["schema"].endswith("/EvidenceMountFields")
    assert library["x-implemented"] is True

    enum = spec["components"]["schemas"]["V1Error"]["properties"]["code"]["enum"]
    assert len(enum) == len(FROZEN_NAMES)
    assert len(ERROR_STATUS) == len(FROZEN_NAMES)
    assert set(enum) == FROZEN_NAMES
    statuses = spec["components"]["x-error-status"]["statuses"]
    assert "EVIDENCE_EXPIRED" in statuses["409"]
    assert "EVIDENCE_NOT_USABLE" in statuses["409"]
    assert "FORBIDDEN" in statuses["403"]
    assert implemented_contract(spec) == create_app().openapi()
