# 为什么有这个文件：独立验证示例页面使用的完整主流程和真实输出内容。
# 它解决什么问题：防止接口表面接通，却遗漏人工确认、证据、公司隔离、旧检查失效和两册内容正确性。

import base64
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from icg_demo.main import create_app
from icg_demo.parsing import LocalTextParser
from icg_demo.domain import DomainError


TENDER = "合成招标文件：测试项目\n招标编号：SYNTH-001\n投标截止时间：2026-12-31T17:00:00+08:00\n服务期限：12个月\n★技术要求：每月完成巡检并提交报告。\f商务要求：提供有效企业资质证明。"
COMMITTED = {"technical": "技术正文验收标记：每月安排巡检，报告由负责人复核。", "business": "商务正文验收标记：企业资质经核对，附件对应原件。"}


@pytest.fixture
def client():
    with TestClient(create_app()) as actual:
        yield actual


def login(client, account="alpha-editor"):
    result = client.post("/api/demo/login", json={"account_id": account})
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}


class ProjectFlow:
    def __init__(self, client, account="alpha-editor"):
        self.client, self.headers = client, login(client, account)
        result = client.post("/api/projects", headers=self.headers, json={"name": "合成双册验收项目"})
        assert result.status_code == 200, result.text
        self.id = result.json()["id"]
        self.path = "/api/v1/projects/" + self.id

    def state(self):
        result = self.client.get(self.path + "/workspace", headers=self.headers)
        assert result.status_code == 200, result.text
        assert result.headers["etag"] == f'"{result.json()["revision"]}"'
        return result.json()

    def write(self, path, data, method="POST", expected=200, headers=None):
        version = self.state()["revision"]
        result = self.client.request(method, self.path + path, json=data,
                                     headers=headers or {**self.headers, "If-Match": str(version), "Idempotency-Key": str(uuid4())})
        assert result.status_code == expected, result.text
        return result.json()

    def upload(self, content=TENDER.encode(), filename="合成招标.txt"):
        return self.write("/files", {"filename": filename, "content_base64": base64.b64encode(content).decode()})["file"]

    def reviewed(self, tender=TENDER):
        self.write("", {"tender_number": "SYNTH-001", "deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")
        self.upload(tender.encode())
        result = self.write("/parse", {})
        assert result["job"]["status"] == "completed"
        for row in self.state()["requirements"]:
            self.write("/requirements/" + row["id"], {"status": "confirmed"}, "PATCH")
        for fact in self.state()["facts"]:
            manager_headers = None
            if fact.get("required"):
                manager_headers = {**login(self.client, "alpha-manager"),
                                   "If-Match": str(self.state()["revision"]),
                                   "Idempotency-Key": str(uuid4())}
            self.write("/facts/" + fact["id"], {"status": "confirmed"}, "PATCH", headers=manager_headers)
        return self

    def library(self, **overrides):
        library = self.client.get("/api/v1/library", headers=self.headers).json()
        payload = {"name": "合成企业资质", "type": "qualification", "content": "仅供测试：有效企业资质已核对。",
                   "valid_until": "2027-12-31", "status": "confirmed", **overrides}
        result = self.client.post("/api/v1/library", json=payload, headers={**self.headers,
                                  "If-Match": str(library["revision"]), "Idempotency-Key": str(uuid4())})
        assert result.status_code == 200, result.text
        return result.json()["item"]

    def confirm_plan(self, data=None, expected=200):
        if data is None:
            data = {"chapters": [{**{key: chapter[key] for key in ("id", "title", "volume")},
                                  **{key: chapter["writing_input"][key] for key in ("fact_ids", "writing_points", "target_length")}}
                                 for chapter in self.state()["chapters"]]}
        # 日常编写仍用原编写人；当前演示尚无章节人员分配，方案由经理确认。
        manager = login(self.client, "alpha-manager")
        headers = {**manager, "If-Match": str(self.state()["revision"]),
                   "Idempotency-Key": str(uuid4())}
        return self.write("/plan", data, expected=expected, headers=headers)

    def ready(self):
        self.reviewed()
        self.write("/parse/confirm", {})
        chapters = self.state()["chapters"]
        evidence = self.library()
        for row in self.state()["requirements"]:
            chapter = next(c for c in chapters if c["volume"] == row["volume"])
            self.write("/requirements/" + row["id"], {"chapter_id": chapter["id"], "response": "经核对满足要求。",
                       "evidence_ids": [evidence["id"]] if row["volume"] == "business" else []}, "PATCH")
        self.confirm_plan({"chapters": [{"id": c["id"], "title": c["title"], "volume": c["volume"]} for c in chapters]})
        for chapter in self.state()["chapters"]:
            self.commit(chapter["id"], COMMITTED[chapter["volume"]])
        return self

    def commit(self, chapter_id, content):
        result = self.client.get("/api/chapters/" + chapter_id, headers=self.headers)
        assert result.status_code == 200
        chapter = result.json()
        lock = self.client.post(f"/api/chapters/{chapter_id}/lock", headers=self.headers, json={})
        assert lock.status_code == 200, lock.text
        lease = lock.json()["lease_token"]
        result = self.client.post(f"/api/chapters/{chapter_id}/versions", headers=self.headers,
                                 json={"lease_token": lease, "base_revision": chapter["revision"],
                                       "content": content, "input_fingerprint": self.state()["input_fingerprint"], "idempotency_key": str(uuid4())})
        assert result.status_code == 200, result.text
        released = self.client.post(f"/api/chapters/{chapter_id}/lock/release", headers=self.headers, json={"lease_token": lease})
        assert released.status_code == 200

    def checked_export(self):
        check = self.write("/checks", {"volume": "all"})["check"]
        assert check["passed"] is True, check
        assert check["coverage"]["complete"] is False
        exported = self.write("/exports", {"check_id": check["id"], "kind": "internal"})["export"]
        return check, exported


def word_text(content):
    with ZipFile(BytesIO(content)) as archive:
        assert "[Content_Types].xml" in archive.namelist()
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    return "\n".join(n.text or "" for n in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))


def test_real_two_volume_flow_and_original_provenance(client):
    flow = ProjectFlow(client).ready()
    state = flow.state()
    assert len(state["requirements"]) == 2
    business = next(r for r in state["requirements"] if r["volume"] == "business")
    assert business["source"]["page"] == 2
    original = client.get(state["files"][0]["download_url"], headers=flow.headers)
    assert original.content == TENDER.encode()
    check, exported = flow.checked_export()
    assert check["status"] == "passed" and exported["status"] == "valid"
    assert exported["excludes_drafts"] is True
    assert {v["volume"] for v in exported["volumes"]} == {"technical", "business"}
    for volume in exported["volumes"]:
        response = client.get(volume["download_url"], headers=flow.headers)
        assert response.status_code == 200, response.text
        text = word_text(response.content)
        assert COMMITTED[volume["volume"]] in text
        other = "business" if volume["volume"] == "technical" else "technical"
        assert COMMITTED[other] not in text
    jobs = client.get("/api/v1/jobs", headers=flow.headers).json()["jobs"]
    assert {j["type"] for j in jobs} >= {"upload", "parse", "check", "export"}


def test_review_gate_and_conflicts_require_explicit_resolution(client):
    flow = ProjectFlow(client)
    flow.upload((TENDER + "\n服务期限：24个月").encode())
    flow.write("/parse", {})
    assert flow.write("/parse/confirm", {}, expected=409)["code"] == "REVIEW_PENDING"
    for row in flow.state()["requirements"]:
        flow.write("/requirements/" + row["id"], {"status": "confirmed"}, "PATCH")
    for fact in flow.state()["facts"]:
        flow.write("/facts/" + fact["id"], {"status": "confirmed"}, "PATCH")
    assert flow.write("/parse/confirm", {}, expected=409)["code"] == "CONFLICTS_PENDING"
    conflict = flow.state()["conflicts"][0]
    flow.write("/conflicts/" + conflict["id"], {"selected_fact_id": conflict["fact_ids"][0], "reason": "依据合成原件第1页。"}, "PATCH")
    assert flow.write("/parse/confirm", {})["parse_confirmed"] is True
    facts = [f for f in flow.state()["facts"] if f["key"] == "服务期限"]
    assert {f["status"] for f in facts} == {"confirmed", "rejected"}


def test_unknown_reference_requires_manual_record(client):
    flow = ProjectFlow(client)
    flow.upload("技术要求：详见附件A，提供巡检。".encode())
    flow.write("/parse", {})
    row = flow.state()["requirements"][0]
    assert row["reference_status"] == "unresolved"
    failure = flow.write("/requirements/" + row["id"], {"status": "confirmed"}, "PATCH", 409)
    assert failure["code"] == "REFERENCE_REASON_REQUIRED"
    updated = flow.write("/requirements/" + row["id"], {"status": "confirmed", "reason": "人工已核对附件A合成原文。"}, "PATCH")
    assert updated["requirement"]["reference_status"] == "resolved"


def test_version_and_repeated_request_protection(client):
    flow = ProjectFlow(client)
    revision = flow.state()["revision"]
    headers = {**flow.headers, "If-Match": str(revision), "Idempotency-Key": str(uuid4())}
    first = flow.write("", {"name": "已更新项目"}, "PATCH", headers=headers)
    assert flow.write("", {"name": "已更新项目"}, "PATCH", headers=headers) == first
    assert flow.state()["revision"] == revision + 1
    assert flow.write("", {"name": "另一内容"}, "PATCH", 409, headers)["code"] == "IDEMPOTENCY_CONFLICT"
    stale = {**headers, "Idempotency-Key": str(uuid4())}
    assert flow.write("", {"name": "旧版本覆盖"}, "PATCH", 409, stale)["code"] == "VERSION_CONFLICT"
    missing = client.patch(flow.path, headers=flow.headers, json={"name": "不得写入"})
    assert missing.status_code == 428
    assert missing.json()["traceId"] == missing.headers["X-Request-ID"]
    assert flow.state()["project"]["name"] == "已更新项目"


@pytest.mark.parametrize("account,status", [("beta-editor", 404), ("alpha-viewer", 403)])
def test_company_and_viewer_writing_boundary(client, account, status):
    flow = ProjectFlow(client).ready()
    outsider = login(client, account)
    result = client.post(flow.path + "/checks", headers={**outsider, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}, json={})
    assert result.status_code == status
    if account == "beta-editor":
        assert client.get(flow.path + "/workspace", headers=outsider).status_code == 404
        file_url = flow.state()["files"][0]["download_url"]
        assert client.get(file_url, headers=outsider).status_code == 404
        assert all(j["project_id"] != flow.id for j in client.get("/api/v1/jobs", headers=outsider).json()["jobs"])


@pytest.mark.parametrize("change", ["project", "requirement", "fact", "evidence", "chapter", "file"])
def test_input_change_invalidates_check_and_export_download(client, change):
    flow = ProjectFlow(client).ready()
    check, exported = flow.checked_export()
    state = flow.state()
    if change == "project":
        flow.write("", {"name": "新项目名称"}, "PATCH")
    elif change == "requirement":
        flow.write("/requirements/" + state["requirements"][0]["id"], {"response": "更新后的响应"}, "PATCH")
    elif change == "fact":
        flow.write("/facts/" + state["facts"][0]["id"], {"value": "另一个招标编号"}, "PATCH")
    elif change == "evidence":
        library = client.get("/api/v1/library", headers=flow.headers).json()
        item = library["items"][0]
        changed = client.patch("/api/v1/library/" + item["id"], headers={**flow.headers, "If-Match": str(library["revision"]), "Idempotency-Key": str(uuid4())}, json={"status": "rejected"})
        assert changed.status_code == 200
    elif change == "chapter":
        flow.commit(state["chapters"][0]["id"], "正文已改变，必须重新检查。")
    else:
        flow.upload(b"new original", "补遗.txt")
    assert next(c for c in flow.state()["checks"] if c["id"] == check["id"])["status"] == "stale"
    assert flow.write("/exports", {"check_id": check["id"], "kind": "internal"}, expected=409)["code"] == "CHECK_STALE"
    for volume in exported["volumes"]:
        result = client.get(volume["download_url"], headers=flow.headers)
        assert result.status_code == 409 and result.json()["code"] == "EXPORT_STALE"


def test_unsubmitted_draft_and_generated_candidate_never_replace_committed_text(client):
    flow = ProjectFlow(client).ready()
    before = {c["id"]: c["content"] for c in flow.state()["chapters"]}
    result = flow.write("/generate", {})
    assert all(c["candidate"]["is_real_model"] is False for c in result["chapters"])
    assert {c["id"]: c["content"] for c in flow.state()["chapters"]} == before
    chapter = flow.state()["chapters"][0]
    lease = client.post(f"/api/chapters/{chapter['id']}/lock", headers=flow.headers, json={}).json()["lease_token"]
    draft = client.put(f"/api/chapters/{chapter['id']}/draft", headers=flow.headers, json={"lease_token": lease,
                       "base_revision": chapter["revision"], "sequence": 1, "content": "仅草稿秘密验收标记", "input_fingerprint": flow.state()["input_fingerprint"]})
    assert draft.status_code == 200, draft.text
    _, exported = flow.checked_export()
    for volume in exported["volumes"]:
        response = client.get(volume["download_url"], headers=flow.headers)
        assert response.status_code == 200
        assert "仅草稿秘密验收标记" not in word_text(response.content)


def test_expired_or_unreviewed_evidence_blocks_use_or_check(client):
    flow = ProjectFlow(client).ready()
    row = next(r for r in flow.state()["requirements"] if r["volume"] == "business")
    pending = flow.library(status="pending")
    error = flow.write("/requirements/" + row["id"], {"evidence_ids": [pending["id"]]}, "PATCH", 409)
    assert error["code"] == "EVIDENCE_NOT_USABLE"
    expired = flow.library(valid_until="2026-01-01")
    flow.write("/requirements/" + row["id"], {"evidence_ids": [expired["id"]]}, "PATCH")
    check = flow.write("/checks", {})["check"]
    assert check["passed"] is False
    assert "EVIDENCE_EXPIRED" in {i["code"] for i in check["issues"]}


def test_submission_cannot_be_claimed_when_rule_coverage_is_incomplete(client):
    flow = ProjectFlow(client).ready()
    check, _ = flow.checked_export()
    assert flow.write("/exports", {"check_id": check["id"], "kind": "submission"}, expected=403)["code"] == "SUBMISSION_FORBIDDEN"
    manager = login(client, "alpha-manager")
    result = client.post(flow.path + "/exports", json={"check_id": check["id"], "kind": "submission"}, headers={**manager, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    assert result.status_code == 409 and result.json()["code"] == "RULES_INCOMPLETE"


@pytest.mark.parametrize("filename,content,error", [("非法.docx", b"not a zip", "INVALID_DOCX"), ("控制字符.txt", b"hello\x00world", "INVALID_TEXT")])
def test_failed_parse_retains_original_and_records_failed_job(client, filename, content, error):
    flow = ProjectFlow(client)
    uploaded = flow.upload(content, filename)
    assert flow.write("/parse", {}, expected=422)["code"] == error
    state = flow.state()
    assert state["parse_confirmed"] is False and state["requirements"] == []
    assert state["jobs"][-1]["status"] == "failed"
    assert client.get(uploaded["download_url"], headers=flow.headers).content == content
    assert flow.write("/parse/confirm", {}, expected=409)["code"] == "PARSE_INCOMPLETE"


def pdf_bytes(with_text):
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    if with_text:
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 40 700 Td (Synthetic tender requirement) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_actual_docx_and_digital_pdf_text_extraction():
    archive_data = BytesIO()
    with ZipFile(archive_data, "w") as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>合成技术要求</w:t><w:br w:type="page"/><w:t>合成商务要求</w:t></w:r></w:p></w:body></w:document>')
    parser = LocalTextParser()
    docx = parser.parse("合成.docx", archive_data.getvalue())
    assert [p.strip() for p in docx.pages] == ["合成技术要求", "合成商务要求"]
    assert docx.pagination == "explicit_docx_breaks_only" and docx.warnings
    pdf = parser.parse("合成.pdf", pdf_bytes(True))
    assert pdf.pagination == "pdf_page_index"
    assert "Synthetic tender requirement" in pdf.pages[0]
    with pytest.raises(DomainError) as scanned:
        parser.parse("扫描.pdf", pdf_bytes(False))
    assert scanned.value.code == "OCR_REQUIRED"


def test_scanned_pdf_is_failed_in_real_route(client):
    flow = ProjectFlow(client)
    flow.upload(pdf_bytes(False), "合成扫描.pdf")
    assert flow.write("/parse", {}, expected=422)["code"] == "OCR_REQUIRED"
    assert flow.state()["files"][0]["status"] == "failed"


def test_edited_requirement_reopens_reference_review(client):
    flow = ProjectFlow(client).reviewed()
    flow.write("/parse/confirm", {})
    row = flow.state()["requirements"][0]
    changed = flow.write("/requirements/" + row["id"], {"text": "技术要求：详见附件B，新技术条件。"}, "PATCH")["requirement"]
    assert changed["status"] == "pending" and changed["reference_status"] == "unresolved"
    assert flow.state()["parse_confirmed"] is False
    assert flow.write("/requirements/" + row["id"], {"status": "confirmed"}, "PATCH", 409)["code"] == "REFERENCE_REASON_REQUIRED"


def test_rejecting_selected_conflict_fact_reopens_conflict(client):
    flow = ProjectFlow(client).reviewed(TENDER + "\n服务期限：24个月")
    conflict = flow.state()["conflicts"][0]
    selected = conflict["fact_ids"][0]
    flow.write("/conflicts/" + conflict["id"], {"selected_fact_id": selected, "reason": "核对合成原件后采用此值。"}, "PATCH")
    flow.write("/parse/confirm", {})
    flow.write("/facts/" + selected, {"status": "rejected", "reason": "原选值已不适用。"}, "PATCH")
    assert flow.state()["conflicts"][0]["status"] == "pending"
    assert flow.write("/parse/confirm", {}, expected=409)["code"] == "CONFLICTS_PENDING"
