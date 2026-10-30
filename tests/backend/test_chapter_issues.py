# 为什么有这个文件：验证编辑台本章问题清单与段落定位（APP-M2-T166 / PRD v1.8 §5.11.2 问题侧栏、§5.11.6 第 5 项）。
# 它解决什么问题：
# 1. 章节循环、检查批次、编辑后复查三处问题合成一张清单，每条折算到当前段落键；
# 2. 正文改动后问题跟着段落走（段落键或原句），段落删掉的标“未能定位”，不按旧行号乱指；
# 3. 编辑后复查的问题按当前正文重跑，不再出现的标已解决；只读成员可看、他公司不可看。

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg.app.main import create_app
from icg.domain import paragraph_keys
from icg.domain.chapter_issues import annotate_check_issues, locate
from test_reference_flow import ProjectFlow, client, login  # noqa: F401

DEFECTIVE = "\n".join([
    "第一段：每月安排巡检并提交巡检报告。",
    "",
    "第二段：我司无法提供全天候驻场。",
    "第三段：项目业绩见【待补：同类业绩】。",
])


def _headers(flow, account="alpha-manager"):
    return {**login(flow.client, account), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}


def _prepared(client):
    flow = ProjectFlow(client).ready()
    cid = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")["id"]
    flow.commit(cid, DEFECTIVE)
    recheck = client.post(f"{flow.path}/chapters/{cid}/loop/recheck", json={}, headers=_headers(flow))
    assert recheck.status_code == 200, recheck.text
    return flow, cid


def _issues(client, flow, cid, account="alpha-manager"):
    res = client.get(f"{flow.path}/chapters/{cid}/issues", headers=login(client, account))
    assert res.status_code == 200, res.text
    return res.json()


def _key_at(client, flow, cid, line):
    chapter = client.get(f"/api/chapters/{cid}", headers=flow.headers).json()
    return next(p["key"] for p in chapter["paragraphs"] if p["line_start"] <= line <= p["line_end"]), chapter


def test_loop_issues_carry_paragraph_keys_and_follow_edits(client):
    flow, cid = _prepared(client)
    body = _issues(client, flow, cid)
    loop = {i["code"]: i for i in body["items"] if i["origin"] == "loop"}
    assert set(loop) == {"NEGATIVE_DEVIATION_DETECTED", "PLACEHOLDER_RESIDUAL"}
    deviation_key, chapter = _key_at(client, flow, cid, 2)
    placeholder_key, _ = _key_at(client, flow, cid, 3)
    assert loop["NEGATIVE_DEVIATION_DETECTED"]["paragraph_key"] == deviation_key
    assert loop["PLACEHOLDER_RESIDUAL"]["paragraph_key"] == placeholder_key
    assert loop["PLACEHOLDER_RESIDUAL"]["located_by"] == "key"
    assert all(i["open"] and i["status_label"] == "待人工处理" and i["route_label"] for i in loop.values())
    assert body["counts"]["open"] >= 2 and body["revision"] == chapter["revision"]

    # 在开头插两行：行号整体后移，问题仍按段落键指到原段落
    flow.commit(cid, "新增导语：本节说明服务内容。\n\n" + chapter["content"])
    moved = {i["code"]: i for i in _issues(client, flow, cid)["items"] if i["origin"] == "loop"}
    assert moved["PLACEHOLDER_RESIDUAL"]["paragraph_key"] == placeholder_key
    assert moved["PLACEHOLDER_RESIDUAL"]["line_start"] == loop["PLACEHOLDER_RESIDUAL"]["line_start"] + 2

    # 删掉负偏离那一段：不按旧行号乱指，标未能定位
    current = client.get(f"/api/chapters/{cid}", headers=flow.headers).json()["content"]
    flow.commit(cid, "\n".join(line for line in current.split("\n") if "无法提供" not in line))
    gone = {i["code"]: i for i in _issues(client, flow, cid)["items"] if i["origin"] == "loop"}
    assert gone["NEGATIVE_DEVIATION_DETECTED"]["paragraph_key"] is None
    assert gone["NEGATIVE_DEVIATION_DETECTED"]["located_by"] == "none"
    assert gone["NEGATIVE_DEVIATION_DETECTED"]["locate_note"]


def test_check_issues_are_listed_with_stale_flag_and_chapter_level_location(client):
    flow, cid = _prepared(client)
    check = flow.write("/checks", {"volume": "technical"})["check"]
    assert check["chapter_revisions"][cid] >= 1
    body = _issues(client, flow, cid)
    assert body["check"]["id"] == check["id"] and body["check"]["stale"] is False
    checks = [i for i in body["items"] if i["origin"] == "check"]
    pending = next(i for i in checks if i["code"] == "PENDING_CONTENT")
    assert pending["located_by"] == "chapter" and pending["paragraph_key"] is None and pending["locate_note"] == "整章问题"
    assert pending["route"] in ("must_fix", "fix_or_release", "hint")

    _, chapter = _key_at(client, flow, cid, 0)
    flow.commit(cid, chapter["content"] + "\n补充一段。")
    after = _issues(client, flow, cid)
    assert after["check"]["stale"] is True
    assert all(i["stale"] for i in after["items"] if i["origin"] == "check")


def test_annotate_and_locate_by_key_quote_and_trusted_line(client):
    flow, cid = _prepared(client)
    state = client.app.state.service.repository.read()
    chapter = state.chapters[cid]
    lines = chapter.content.split("\n")
    target = next(i for i, line in enumerate(lines) if "【待补" in line)
    issue = {"chapter_id": cid, "details": {"paragraph_index": target, "quote": lines[target].strip()[:120]}}
    annotate_check_issues(state, [issue])
    blocks = paragraph_keys.current(chapter)
    expected = next(b["key"] for b in blocks if b["line_start"] <= target <= b["line_end"])
    assert issue["paragraph_key"] == expected
    texts = [{**b, "text": "\n".join(lines[b["line_start"]:b["line_end"] + 1])} for b in blocks]
    assert locate(texts, key=None, quote=lines[target], line=None, line_trusted=False)[1] == "quote"
    assert locate(texts, key=None, quote=None, line=target, line_trusted=False) == (None, "none")
    assert locate(texts, key=None, quote=None, line=target, line_trusted=True)[1] == "line"
    assert locate(texts, key=None, quote=None, line=None, line_trusted=False) == (None, "chapter")


def test_readonly_member_reads_and_other_company_cannot(client):
    flow, cid = _prepared(client)
    assert _issues(client, flow, cid, "alpha-viewer")["chapter_id"] == cid
    denied = client.get(f"{flow.path}/chapters/{cid}/issues", headers=login(client, "beta-manager"))
    assert denied.status_code == 404
    wrong_project = client.get(f"/api/v1/projects/alpha-project/chapters/{cid}/issues", headers=flow.headers)
    assert wrong_project.status_code == 404


SAMPLE = "我方每月安排专业工程师开展一次例行巡检并提交巡检报告"


class OneReply:
    name, is_real_model, is_local, model = "scripted", True, True, "scripted-1"

    def suggest(self, system, user):
        return SAMPLE


@pytest.fixture
def scripted():
    with TestClient(create_app(model_provider=OneReply())) as actual:
        yield actual


def test_pasted_recheck_is_listed_and_resolves_when_the_paragraph_is_fixed(scripted):
    flow = ProjectFlow(scripted).ready()
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    start = chapter["content"].index("每月安排巡检")
    batch = scripted.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=flow.headers, json={
        "base_revision": chapter["revision"], "start": start, "end": start + 6, "selected_text": "每月安排巡检",
        "knowledge_base_enabled": False}).json()
    pasted = chapter["content"] + "\n" + batch["samples"][0]["text"] + "，共 7 人。"
    flow.commit(chapter["id"], pasted)

    items = [i for i in _issues(scripted, flow, chapter["id"])["items"] if i["origin"] == "edit_recheck"]
    r30 = next(i for i in items if i["rule_id"] == "R30")
    assert r30["open"] and r30["origin_label"] == "编辑后复查" and r30["paragraph_key"]
    assert r30["route"] == "direct_human"

    flow.commit(chapter["id"], chapter["content"] + "\n" + batch["samples"][0]["text"] + "。")
    fixed = next(i for i in _issues(scripted, flow, chapter["id"])["items"] if i["id"] == r30["id"])
    assert fixed["open"] is False and fixed["status"] == "resolved"
