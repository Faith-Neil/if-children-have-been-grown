# 为什么有这个文件：验证“只写技术标”的项目（用户 2026-10-29 要求：不一定要合标）。
# 它解决什么问题：项目只有技术分册时，不建商务册、商务/资格条款标为不在范围（保留原文与理由）、
# 检查与导出的“全文”就是技术分册、递交版只出一份 Word 且不生成合标核对清单；商务分册的任何写入都拒绝。
# 两册项目行为不变；有正文的商务分册不能被切换模式悄悄删掉。

from uuid import uuid4

from test_reference_flow import COMMITTED, ProjectFlow, client, login  # noqa: F401


class TechFlow(ProjectFlow):
    def __init__(self, client):
        self.client, self.headers = client, login(client, "alpha-manager")
        result = client.post("/api/v1/projects", headers=self.headers, json={"name": "只写技术标项目", "volume_mode": "technical_only"})
        assert result.status_code == 200, result.text
        assert result.json()["volume_mode"] == "technical_only"
        self.id = result.json()["id"]
        self.path = "/api/v1/projects/" + self.id
        self.write("/team", {"members": [
            {"user_id": "alpha-manager", "project_role": "lead", "volumes": ["technical"]},
            {"user_id": "alpha-editor", "project_role": "writer", "volumes": ["technical"]},
            {"user_id": "alpha-viewer", "project_role": "readonly", "volumes": ["technical"]}],
            "volumes": [{"volume": "technical", "owner_id": "alpha-manager"}], "assembly_owner_id": "alpha-manager"}, "PUT")

    def reviewed(self, tender=None):
        from test_reference_flow import TENDER
        self.write("", {"tender_number": "SYNTH-001", "deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")
        self.upload((tender or TENDER).encode())
        assert self.write("/parse", {})["job"]["status"] == "completed"
        for row in self.state()["requirements"]:
            if not row.get("out_of_scope"):
                self.write("/requirements/" + row["id"], {"status": "confirmed"}, "PATCH")
        for fact in self.state()["facts"]:
            self.write("/facts/" + fact["id"], {"status": "confirmed"}, "PATCH")
        return self

    def ready(self):
        self.reviewed()
        self.write("/parse/confirm", {})
        chapter = next(c for c in self.state()["chapters"])
        for row in self.state()["requirements"]:
            if row.get("out_of_scope"):
                continue
            self.write("/requirements/" + row["id"], {"chapter_id": chapter["id"], "response": "经核对满足要求。"}, "PATCH")
        self.confirm_plan({"chapters": [{"id": c["id"], "title": c["title"], "volume": c["volume"]} for c in self.state()["chapters"]]})
        self.commit(chapter["id"], COMMITTED["technical"])
        return self


def _headers(flow, account="alpha-manager"):
    return {**login(flow.client, account), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}


def test_technical_only_project_has_one_volume_and_business_rows_out_of_scope(client):
    flow = TechFlow(client)
    state = flow.state()
    assert state["project"]["volume_mode"] == "technical_only" and state["team"]["volume_mode"] == "technical_only"
    assert [c["volume"] for c in state["chapters"]] == ["technical"]
    assert [v["volume"] for v in state["team"]["volumes"]] == ["technical"]
    assert state["permissions"]["export_volumes"] == ["technical"]
    flow.reviewed()
    rows = flow.state()["requirements"]
    business = [r for r in rows if r["volume"] == "business"]
    assert business and all(r["status"] == "rejected" and r["out_of_scope"] and "只写技术标" in r["reason"] for r in business)
    assert any(r["volume"] == "technical" and r["status"] == "confirmed" for r in rows)
    confirm = flow.write("/requirements/" + business[0]["id"], {"status": "confirmed"}, "PATCH", expected=409)
    assert "先把分册改为技术分册" in confirm["message"]


def test_technical_only_checks_finalizes_and_exports_one_word_without_merge_checklist(client):
    flow = TechFlow(client).ready()
    check = flow.write("/checks", {"volume": "all"})["check"]
    assert not any(i["code"] in ("VOLUME_MISSING", "REQUIREMENT_PENDING", "MATRIX_MAPPING_MISSING") for i in check["issues"]), check["issues"]
    for issue in [i for i in check["issues"] if i["severity"] == "warning"]:
        check = flow.write(f"/checks/{check['id']}/issues/{issue['id']}/release", {"reason": "技术标验收"})["check"]
    assert check["passed"], check["issues"]
    flow.cross_reviewed("technical")
    assert client.post(f"{flow.path}/volumes/technical/finalize", json={"check_id": check["id"]}, headers=_headers(flow)).status_code == 200
    assert client.post(f"{flow.path}/volumes/business/finalize", json={"check_id": check["id"]}, headers=_headers(flow)).status_code == 404
    statuses = client.get(f"{flow.path}/volumes", headers=flow.headers).json()
    assert [v["volume_id"] for v in statuses["volumes"]] == ["technical"]
    export = flow.write("/exports", {"check_id": check["id"], "kind": "submission", "volume": "all"})["export"]
    assert [v["volume"] for v in export["volumes"]] == ["technical"]
    assert "merge_checklist_url" not in export and export["volume_mode"] == "technical_only"
    word = client.get(export["volumes"][0]["download_url"], headers=flow.headers)
    assert word.status_code == 200 and word.content[:2] == b"PK"


def test_business_writes_are_refused_in_technical_only_project(client):
    flow = TechFlow(client)
    flow.reviewed()
    tech = next(r for r in flow.state()["requirements"] if r["volume"] == "technical")
    error = flow.write("/requirements/" + tech["id"], {"volume": "business"}, "PATCH", expected=404)
    assert "只编写技术标" in error["message"]
    team = flow.write("/team", {"members": [{"user_id": "alpha-manager", "project_role": "lead", "volumes": ["technical", "business"]}],
                                "volumes": [{"volume": "technical", "owner_id": "alpha-manager"}], "assembly_owner_id": "alpha-manager"},
                      "PUT", expected=404)
    assert "只编写技术标" in team["message"]
    assert client.get(f"{flow.path}/response-trace.xlsx?volume=business", headers=flow.headers).status_code == 404
    # 商务条款人工纳入技术标
    biz = next(r for r in flow.state()["requirements"] if r.get("out_of_scope"))
    updated = flow.write("/requirements/" + biz["id"], {"volume": "technical", "status": "pending", "reason": ""}, "PATCH")["requirement"]
    assert updated["volume"] == "technical" and updated["out_of_scope"] is False


def test_switching_modes_keeps_written_business_content(client):
    flow = ProjectFlow(client)
    business = next(c for c in flow.state()["chapters"] if c["volume"] == "business")
    flow.commit(business["id"], "商务正文：已写内容。")
    blocked = flow.write("", {"volume_mode": "technical_only"}, "PATCH", expected=409)
    assert blocked["code"] == "CHAPTER_HAS_CONTENT"
    flow.commit(business["id"], "")
    switched = flow.write("", {"volume_mode": "technical_only"}, "PATCH")["project"]
    assert switched["volume_mode"] == "technical_only"
    assert [c["volume"] for c in flow.state()["chapters"]] == ["technical"]
    back = flow.write("", {"volume_mode": "both"}, "PATCH")["project"]
    assert back["volume_mode"] == "both"
    assert sorted(c["volume"] for c in flow.state()["chapters"]) == ["business", "technical"]
    assert sorted(v["volume"] for v in flow.state()["team"]["volumes"]) == ["business", "technical"]
