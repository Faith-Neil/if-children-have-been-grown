# 为什么有这个文件：验证粘贴识别（PRD v1.8 §5.11.7、风险 K26；公司设置 assistant_paste_match_ratio；APP-M2-T188）。
# 它解决什么问题：把对话助手样例手工粘贴进正文提交时，该段来源记为“对话助手撰写（粘贴）”、提交结果带复查问题、审计记段落；
# 人工写的、改动很大的段落不误判；阈值来自公司设置且有上下限。

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg.app.main import create_app
from icg.domain.paste_detection import coverage, detect
from test_reference_flow import ProjectFlow, login

SAMPLE = "我方每月安排专业工程师开展一次例行巡检并提交巡检报告"


class OneReply:
    name, is_real_model, is_local, model = "scripted", True, True, "scripted-1"

    def suggest(self, system, user):
        return SAMPLE


def test_coverage_and_detect():
    outputs = [{"kind": "sample", "id": "s1", "batch_id": "b1", "text": SAMPLE}]
    assert coverage(SAMPLE + "。", SAMPLE) > 0.9
    assert coverage("每月我们去现场看看设备运行情况，报告交给负责人。", SAMPLE) < 0.5
    found = detect("旧段落", "旧段落\n" + SAMPLE + "，共 5 人。", outputs, 0.8)
    assert detect("旧段落", "旧段落\n" + SAMPLE + "，并由项目负责人逐项核对巡检记录和客户签字。", outputs, 0.8) == []  # 加了大量自己的内容
    assert [f["paragraph_index"] for f in found] == [1] and found[0]["origin"]["batch_id"] == "b1"
    assert detect(SAMPLE, SAMPLE, outputs, 0.8) == []  # 原有段落不算新粘贴


@pytest.fixture
def client():
    with TestClient(create_app(model_provider=OneReply())) as actual:
        yield actual


def test_pasting_an_assistant_sample_is_recorded_as_assistant_written(client):
    flow = ProjectFlow(client).ready()
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    start = chapter["content"].index("每月安排巡检")
    batch = client.post(f"{flow.path}/chapters/{chapter['id']}/selection-rewrites", headers=flow.headers, json={
        "base_revision": chapter["revision"], "start": start, "end": start + 6, "selected_text": "每月安排巡检",
        "knowledge_base_enabled": False}).json()
    assert batch["samples"], batch
    lock = client.post(f"/api/chapters/{chapter['id']}/lock", headers=flow.headers, json={}).json()
    pasted = chapter["content"] + "\n" + batch["samples"][0]["text"] + "，共 7 人。"
    resp = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers, json={
        "lease_token": lock["lease_token"], "base_revision": chapter["revision"], "content": pasted,
        "idempotency_key": str(uuid4()), "input_fingerprint": flow.state()["input_fingerprint"]})
    assert resp.status_code == 200, resp.text
    detected = resp.json()["paste_detected"]
    assert detected and detected[0]["source_label"] == "对话助手撰写（粘贴）" and detected[0]["match_ratio"] >= 0.8
    assert any(i["rule_id"] == "R30" for i in detected[0]["issues"])  # “7 名”没有来源
    state = client.app.state.service.repository.read()
    version = state.chapters[chapter["id"]].versions[-1]
    assert version["paragraph_sources"][0]["source"] == "assistant_pasted"
    assert any(e["action"] == "version.commit" and e["details"].get("pasted_paragraphs") for e in state.audit)

    lock = client.post(f"/api/chapters/{chapter['id']}/lock", headers=flow.headers, json={}).json()
    manual = pasted + "\n本节另由项目负责人逐项核对了巡检记录与客户签字流程。"
    resp = client.post(f"/api/chapters/{chapter['id']}/versions", headers=flow.headers, json={
        "lease_token": lock["lease_token"], "base_revision": chapter["revision"] + 1, "content": manual,
        "idempotency_key": str(uuid4()), "input_fingerprint": flow.state()["input_fingerprint"]})
    assert resp.status_code == 200 and not resp.json().get("paste_detected")


def test_paste_ratio_is_a_bounded_company_setting(client):
    admin = login(client, "alpha-company-admin")
    bad = client.patch("/api/v1/companies/alpha/settings", headers=admin, json={"assistant_paste_match_ratio": 0.2})
    assert bad.status_code == 422
    ok = client.patch("/api/v1/companies/alpha/settings", headers=admin, json={"assistant_paste_match_ratio": 0.6})
    assert ok.status_code == 200 and ok.json()["assistant_paste_match_ratio"] == 0.6
