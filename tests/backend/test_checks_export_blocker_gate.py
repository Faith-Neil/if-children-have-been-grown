# 为什么有这个文件：为 BE-CHECKS-EXPORT-ALIGN 提供检查阻断红线与整本导出门禁的自动化测试。
# 它解决什么问题：验证废标红线与关键星号条款的 blocker 严重度判定、递交版 400 CHECK_BLOCKER_EXISTS 门禁拦截、内部稿放行及 has_blockers 标记、64位 SHA-256 文件指纹与 Word 默认版式元数据。

import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import iso_time
from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, client, login


def test_disqualification_and_star_clauses_yield_blocker_severity(client):
    flow = ProjectFlow(client).ready()
    state = flow.state()
    reqs = state["requirements"]
    assert len(reqs) >= 2
    r0 = reqs[0]
    r1 = reqs[1]

    # 1. 废标条款：未响应（response为空或待补）时产生 blocker
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "废标红线：供应商必须具备国家甲级安全资质，否则作否决投标处理。",
            "category": "disqualification",
            "status": "confirmed",
            "response": "",
            "reason": "废标条款核对",
        },
        "PATCH",
    )

    # 2. 关键星号条款：未映射有效章节时产生 blocker
    flow.write(
        f"/requirements/{r1['id']}",
        {
            "text": "★技术关键要求：核心系统需满足RPO=0、RTO<30秒。",
            "category": "star",
            "chapter_id": None,
            "status": "confirmed",
            "response": "承诺满足全部技术指标要求。",
            "reason": "星号关键指标",
        },
        "PATCH",
    )

    check_res = flow.write("/checks", {"volume": "all"})
    check = check_res["check"]
    assert check["passed"] is False

    issues = check["issues"]
    # 查找废标条款生成的 issue (应为 blocker)
    disqual_issues = [i for i in issues if i.get("requirement_id") == r0["id"]]
    assert len(disqual_issues) > 0
    assert any(i["severity"] == "blocker" for i in disqual_issues)
    assert any(i["code"] == "MATRIX_RESPONSE_MISSING" for i in disqual_issues)

    # 查找星号条款生成的 issue (应为 blocker)
    star_issues = [i for i in issues if i.get("requirement_id") == r1["id"]]
    assert len(star_issues) > 0
    assert any(i["severity"] == "blocker" for i in star_issues)
    assert any(i["code"] == "MATRIX_MAPPING_MISSING" for i in star_issues)


def test_submission_export_blocked_with_400_when_blocker_exists(client):
    flow = ProjectFlow(client).ready()
    state = flow.state()
    r0 = state["requirements"][0]

    # 将 r0 改为废标条款且未填写响应
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "废标红线：必须提供原厂三年维保授权书，否则投标无效。",
            "category": "disqualification",
            "status": "confirmed",
            "response": "",
            "reason": "废标条款测试",
        },
        "PATCH",
    )

    check = flow.write("/checks", {"volume": "all"})["check"]
    assert any(i.get("severity") == "blocker" for i in check["issues"])

    # 作为项目经理尝试导出正式递交版 (submission)
    manager_headers = login(client, "alpha-manager")
    export_payload = {
        "check_id": check["id"],
        "kind": "submission",
        "volume": "all",
    }
    resp = client.post(
        f"{flow.path}/exports",
        json=export_payload,
        headers={
            **manager_headers,
            "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid4()),
        },
    )
    # 断言：必须强拦截返回 400 CHECK_BLOCKER_EXISTS，杜绝带病递交
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == "CHECK_BLOCKER_EXISTS"
    assert "阻断项" in data["message"]
    assert "traceId" in data


def test_internal_review_export_allowed_with_blocker_flag_and_compliance_notice(client):
    flow = ProjectFlow(client).ready()
    state = flow.state()
    r0 = state["requirements"][0]

    # 将 r0 改为缺少资质证据的关键星号条款
    flow.write(
        f"/requirements/{r0['id']}",
        {
            "text": "★技术资质要求：提供信息安全服务资质认证证书。",
            "category": "star",
            "status": "confirmed",
            "response": "本公司具备该资质证书。",
            "reason": "星号资质条款",
            "evidence_ids": [],  # 证明类条款缺少证据
        },
        "PATCH",
    )

    check = flow.write("/checks", {"volume": "all"})["check"]
    assert any(i.get("severity") == "blocker" for i in check["issues"])

    # 作为项目经理导出 internal_review 内部评审稿
    manager_headers = login(client, "alpha-manager")
    export_payload = {
        "check_id": check["id"],
        "kind": "internal_review",
        "volume": "all",
    }
    resp = client.post(
        f"{flow.path}/exports",
        json=export_payload,
        headers={
            **manager_headers,
            "If-Match": str(flow.state()["revision"]),
            "Idempotency-Key": str(uuid4()),
        },
    )
    # 断言：内部评审稿允许放行导出（200），但快照中标记 has_blockers=True 并携带合规警示
    assert resp.status_code == 200
    exported = resp.json()["export"]
    assert exported["kind"] == "internal_review"
    assert exported["has_blockers"] is True
    assert exported["compliance_notice"] is not None
    assert "不可作为正式递交文件" in exported["compliance_notice"]


def test_export_contains_64bit_sha256_and_word_default_format_metadata(client):
    flow = ProjectFlow(client).ready()
    check, exported = flow.checked_export()

    # 验证整本/分册快照元数据
    sha256_pattern = re.compile(r"^[a-f0-9]{64}$")
    assert exported["sha256"] is not None
    assert sha256_pattern.match(exported["sha256"]), f"Invalid record SHA256: {exported['sha256']}"

    # 验证 Word 默认版式元数据
    meta = exported["format_metadata"]
    assert meta is not None
    assert meta["page_size"] == "A4"
    assert meta["orientation"] == "portrait"
    assert meta["margins"]["top_cm"] == 2.5
    assert meta["margins"]["left_cm"] == 2.8
    assert meta["margins"]["right_cm"] == 2.6
    assert meta["fonts"]["cover_title"] == "方正小标宋"
    assert meta["fonts"]["h1"] == "黑体"
    assert meta["fonts"]["body"] == "仿宋_GB2312"
    assert meta["font_sizes_pt"]["h1"] == 16.0
    assert meta["font_sizes_pt"]["body"] == 14.0
    assert meta["line_spacing"]["body_line_pt"] == 28.0
    assert meta["h1_align"] == "center"

    # 验证各分册元数据包含 64 位 SHA256 与版式元数据
    assert len(exported["volumes"]) == 2
    for vol in exported["volumes"]:
        assert vol["sha256"] is not None
        assert sha256_pattern.match(vol["sha256"]), f"Invalid volume SHA256: {vol['sha256']}"
        vol_meta = vol["format_metadata"]
        assert vol_meta["page_size"] == "A4"
        assert vol_meta["fonts"]["h1"] == "黑体"
