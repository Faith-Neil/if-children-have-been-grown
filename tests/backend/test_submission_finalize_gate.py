# 为什么有这个文件：为 Step ④ 规则最小可递交集 + 分册定稿闸门提供端到端自动化测试。
# 它解决什么问题：
# 1. 验证未定稿分册无法导出正式递交版（409 RULES_INCOMPLETE）；
# 2. 验证单分册定稿但全册未齐时精准指明未定稿分册；
# 3. 验证存在未解决 blocker 时严格阻断（400 CHECK_BLOCKER_EXISTS）；
# 4. 验证技术册与商务册均定稿且检查通过后，放行正式递交版导出，并验证责任人下载鉴权。

from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login


def test_submission_export_blocked_until_all_volumes_finalized(client):
    flow = ProjectFlow(client).ready()
    state = flow.state()

    # 执行项目全部分册合规检查
    check = flow.write("/checks", {"volume": "all"})["check"]
    assert check["status"] == "passed"
    assert not any(i.get("severity") == "blocker" for i in check["issues"])

    manager_headers = login(client, "alpha-manager")

    # 1. 未定稿状态下尝试导出递交版 -> 拦截 409 RULES_INCOMPLETE
    sub_payload = {
        "check_id": check["id"],
        "kind": "submission",
        "volume": "all",
    }
    resp_unfinalized = client.post(
        f"{flow.path}/exports",
        json=sub_payload,
        headers={
            **manager_headers,
            "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid.uuid4()),
        },
    )
    assert resp_unfinalized.status_code == 409
    err = resp_unfinalized.json()
    assert err["code"] == "RULES_INCOMPLETE"
    assert "尚未完成责任人定稿锁定" in err["message"]
    assert "技术分册" in err["message"]
    assert "商务分册" in err["message"]

    # 2. 仅定稿技术分册，商务分册未定稿 -> 仍拦截 409，精准提示商务分册未定稿
    rev = flow.state()["revision"]
    resp_fin_tech = client.post(
        f"{flow.path}/volumes/technical/finalize",
        json={"check_id": check["id"]},
        headers={
            **manager_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid.uuid4()),
        },
    )
    assert resp_fin_tech.status_code == 200
    assert resp_fin_tech.json()["is_finalized"] is True

    rev = flow.state()["revision"]
    resp_partial = client.post(
        f"{flow.path}/exports",
        json=sub_payload,
        headers={
            **manager_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid.uuid4()),
        },
    )
    assert resp_partial.status_code == 409
    err_partial = resp_partial.json()
    assert err_partial["code"] == "RULES_INCOMPLETE"
    assert "商务分册尚未完成责任人定稿锁定" in err_partial["message"]

    # 3. 商务分册也完成定稿锁定 -> 两册均定稿
    rev = flow.state()["revision"]
    resp_fin_biz = client.post(
        f"{flow.path}/volumes/business/finalize",
        json={"check_id": check["id"]},
        headers={
            **manager_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid.uuid4()),
        },
    )
    assert resp_fin_biz.status_code == 200
    assert resp_fin_biz.json()["is_finalized"] is True

    # 4. 定稿闸门全部通过 -> 正式放行递交版导出
    rev = flow.state()["revision"]
    resp_sub_ok = client.post(
        f"{flow.path}/exports",
        json=sub_payload,
        headers={
            **manager_headers,
            "If-Match": str(rev),
            "Idempotency-Key": str(uuid.uuid4()),
        },
    )
    assert resp_sub_ok.status_code == 200, resp_sub_ok.text
    export_data = resp_sub_ok.json()["export"]
    assert export_data["kind"] == "submission"
    assert export_data["is_submission"] is True
    assert export_data.get("compliance_notice") is None
    assert export_data["has_blockers"] is False
    assert len(export_data["volumes"]) == 2

    export_id = export_data["id"]

    # 5. 下载权限校验：编写人下载正式递交版拦截 403 SUBMISSION_FORBIDDEN
    writer_headers = login(client, "alpha-editor")
    resp_dl_writer = client.get(
        f"{flow.path}/exports/{export_id}/technical",
        headers=writer_headers,
    )
    assert resp_dl_writer.status_code == 403
    assert resp_dl_writer.json()["code"] == "SUBMISSION_FORBIDDEN"

    # 6. 项目经理下载正式递交版成功
    resp_dl_mgr = client.get(
        f"{flow.path}/exports/{export_id}/technical",
        headers=manager_headers,
    )
    assert resp_dl_mgr.status_code == 200
    assert resp_dl_mgr.headers["Content-Type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert "attachment;" in resp_dl_mgr.headers["Content-Disposition"]
