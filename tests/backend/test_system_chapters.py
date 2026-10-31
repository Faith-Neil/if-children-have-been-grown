# 为什么有这个文件：验证五类系统生成章节（APP-M2-T191～T195，PRD v1.8 §5.7.2 规则 9）。
# 它解决什么问题：内容只来自数据源，缺来源写【待补】不编造；正文不能手改；数据源变了检查会挡住，重新生成后恢复。

from uuid import uuid4

from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def _add_chapter(flow, title, volume="technical"):
    chapters = flow.state()["chapters"]
    plan = [{"id": c["id"], "title": c["title"], "volume": c["volume"]} for c in chapters] + [{"title": title, "volume": volume}]
    flow.confirm_plan({"chapters": plan})
    return next(c for c in flow.state()["chapters"] if c["title"] == title)


def _generate(flow, chapter_id, expected=200):
    return flow.write(f"/chapters/{chapter_id}/system/generate", {}, expected=expected)


def _content(flow, chapter_id):
    return flow.client.get(f"/api/chapters/{chapter_id}", headers=flow.headers).json()["content"]


def test_point_to_point_and_deviation_come_from_matrix(client):
    flow = ProjectFlow(client).ready()
    p2p = _add_chapter(flow, "点对点应答")
    _generate(flow, p2p["id"])
    text = _content(flow, p2p["id"])
    tech = next(r for r in flow.state()["requirements"] if r["volume"] == "technical")
    assert "| 序号 | 招标条款 | 应答 | 响应方式 |" in text and tech["text"].lstrip("★") in text and "经核对满足要求。" in text
    assert "★" in text  # 星号条款不漏
    dev = _add_chapter(flow, "偏离表", "business")
    _generate(flow, dev["id"])
    assert "无偏离" in _content(flow, dev["id"])
    biz = next(r for r in flow.state()["requirements"] if r["volume"] == "business")
    flow.write("/requirements/" + biz["id"], {"response_type": "deviate", "deviation_reason": "资质证书年审中，年审后补交"}, "PATCH")
    preview = client.get(f"{flow.path}/chapters/{dev['id']}/system", headers=flow.headers).json()
    assert preview["stale"] is True and "负偏离" in preview["content"] and "年审后补交" in preview["content"]


def test_review_index_leaves_page_for_merge_and_service_plan_never_invents_numbers(client):
    flow = ProjectFlow(client).ready()
    row = next(r for r in flow.state()["requirements"] if r["volume"] == "technical")
    flow.write("/requirements/" + row["id"], {"category": "scoring"}, "PATCH")
    flow.write("/parse/confirm", {})
    index = _add_chapter(flow, "评审索引表")
    preview = client.get(f"{flow.path}/chapters/{index['id']}/system", headers=flow.headers).json()
    assert preview["kind"] == "review_index" and "合标后由商务填写" in preview["content"]
    plan = _add_chapter(flow, "年度服务计划表")
    preview = client.get(f"{flow.path}/chapters/{plan['id']}/system", headers=flow.headers).json()
    assert "【待补：SLA 模板未登记该项频次】" in preview["content"] and preview["gaps"]
    cells = [line.split("|")[2].strip() for line in preview["content"].splitlines()
             if line.startswith("| ") and not line.startswith("| 服务项目")]
    assert cells and all(c.startswith("{{sla:") or c.startswith("【待补") for c in cells)  # 频次只引用已确认变量，否则待补


def test_proof_list_marks_missing_and_attached_materials(client):
    flow = ProjectFlow(client).ready()
    biz = next(r for r in flow.state()["requirements"] if r["volume"] == "business")
    flow.write("/requirements/" + biz["id"], {"category": "qualification"}, "PATCH")
    flow.write("/parse/confirm", {})
    chapter = _add_chapter(flow, "证明材料清单", "business")
    _generate(flow, chapter["id"])
    text = _content(flow, chapter["id"])
    assert "合成企业资质 v1" in text and "已挂接" in text


def test_system_chapter_is_readonly_and_stale_content_blocks_check(client):
    flow = ProjectFlow(client).ready()
    chapter = _add_chapter(flow, "偏离表", "business")
    _generate(flow, chapter["id"])
    detail = client.get(f"/api/chapters/{chapter['id']}", headers=flow.headers).json()
    lock = client.post(f"/api/chapters/{chapter['id']}/lock", headers=flow.headers, json={}).json()
    edit = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers, json={
        "lease_token": lock["lease_token"], "base_revision": detail["revision"], "content": "手改的偏离表",
        "input_fingerprint": flow.state()["input_fingerprint"], "idempotency_key": str(uuid4())})
    assert edit.status_code == 409 and edit.json()["code"] == "SYSTEM_CHAPTER_READONLY"
    client.post(f"/api/chapters/{chapter['id']}/lock/release", headers=flow.headers, json={"lease_token": lock["lease_token"]})
    biz = next(r for r in flow.state()["requirements"] if r["volume"] == "business")
    flow.write("/requirements/" + biz["id"], {"response_type": "deviate", "deviation_reason": "年审中"}, "PATCH")
    check = flow.write("/checks", {"volume": "all"})["check"]
    assert any(i["code"] == "SYSTEM_CHAPTER_STALE" for i in check["issues"])
    _generate(flow, chapter["id"])
    check = flow.write("/checks", {"volume": "all"})["check"]
    assert not any(i["code"] == "SYSTEM_CHAPTER_STALE" for i in check["issues"])


def test_only_chapter_editors_generate_and_ordinary_chapters_are_refused(client):
    flow = ProjectFlow(client).ready()
    chapter = _add_chapter(flow, "偏离表", "business")
    viewer = {**login(client, "alpha-viewer"), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    assert client.post(f"{flow.path}/chapters/{chapter['id']}/system/generate", json={}, headers=viewer).status_code == 403
    ordinary = next(c for c in flow.state()["chapters"] if c["title"] == "技术方案")
    assert _generate(flow, ordinary["id"], expected=409)["code"] == "SYSTEM_CHAPTER_READONLY"
