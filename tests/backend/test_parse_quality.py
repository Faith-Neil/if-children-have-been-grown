# 为什么有这个文件：验证解析条目的置信度与“原文不可读”（PRD v1.8 §5.2.2 规则 2、异常与边界，验收⑤；APP-M2-T104、T105）。
# 它解决什么问题：文字版文件的条目置信度 1.0；扫描件识别的条目最高 0.9，乱码页更低；乱码摘录标“原文不可读”，
# 不能直接确认或批量确认，补录文字后才能确认；解析页闸门列出不可读条数（阻断）与低置信度条数（只提示）；
# 阈值来自公司设置；扫描件识别走真实编排路径，只把 RAGFlow 换成返回合成识别结果的替身。

import pytest
from fastapi.testclient import TestClient

from icg.app.main import create_app
from icg.domain.domain import DomainError
from icg.domain.parse_quality import assess, garble_ratio
from icg.domain.parsing import ParsedDocument
from icg.domain.tender_remote import RemoteOutcome
from test_reference_flow import ProjectFlow, login

GOOD = "第一章 投标人资格要求\n1. 投标人须提供有效的营业执照副本复印件。\n"
GARBLED = "第二章 技术要求\n2. Ã¦Å\u0095æ ‡äººé¡»æ\u008f\u0090ä¾›Ã©Â\u0081Â\u008f\n"
TENDER = "合成招标文件：置信度验收\n招标编号：CONF-001\n" + GOOD + GARBLED


class ScanOnly:
    name = "scan-only"

    def parse(self, filename, content):
        raise DomainError(422, "OCR_REQUIRED", "本地没有文字层。")


@pytest.fixture
def scanned(monkeypatch):
    from icg.domain import tender_remote

    class FakeDeepDoc:
        def __init__(self, *args, **kwargs):
            pass

        @staticmethod
        def eligible(filename, error):
            return True

        def submit(self, company_id, filename, data):
            return RemoteOutcome("done", ParsedDocument(pages=TENDER.split("第二章")[0:1] + ["第二章" + TENDER.split("第二章")[1]],
                                                        pagination="page", warnings=[tender_remote.REMOTE_WARNING]))

    monkeypatch.setattr(tender_remote, "RemoteTenderParser", FakeDeepDoc)
    with TestClient(create_app(parser_provider=ScanOnly())) as client:
        yield client


def _parse(client):
    flow = ProjectFlow(client)
    flow.upload(TENDER.encode(), "合成扫描件.pdf")
    flow.write("/parse", {})
    return flow


def _rows(flow):
    rows = flow.state()["requirements"]
    good = next(r for r in rows if "营业执照" in r["text"])
    bad = next(r for r in rows if r["source"]["page"] == 2 and r.get("unreadable"))
    return good, bad


def test_quality_rules():
    assert assess("投标人须提供营业执照副本。", recognized=False) == {"confidence": 1.0, "unreadable": False, "unreadable_reason": ""}
    assert assess("投标人须提供营业执照副本。", recognized=True)["confidence"] == 0.9
    assert assess("投标人须提供营业执照副本。", recognized=True, page_ratio=0.15)["confidence"] == 0.75
    garbled = assess("Ã¦Å\u0095æ ‡äººé¡»", recognized=True)
    assert garbled["unreadable"] and garbled["confidence"] < 0.5 and "对照原页补录" in garbled["unreadable_reason"]
    assert assess("★", recognized=False)["confidence"] == 0.9  # 过短片段
    assert garble_ratio("") == 1.0 and garble_ratio("ISO 9001：2015 认证") == 0.0


def test_text_files_score_full_confidence(client_text):
    flow = ProjectFlow(client_text)
    flow.upload(TENDER.replace(GARBLED, "").encode())
    flow.write("/parse", {})
    rows = flow.state()["requirements"]
    assert rows and all(r["confidence"] >= 0.9 and not r["unreadable"] for r in rows)


@pytest.fixture
def client_text():
    with TestClient(create_app()) as client:
        yield client


def test_scanned_rows_carry_confidence_and_unreadable_rows_must_be_re_entered(scanned):
    flow = _parse(scanned)
    good, bad = _rows(flow)
    assert good["confidence"] <= 0.9 and not good["unreadable"]
    assert bad["unreadable"] and bad["confidence"] < 0.8 and "扫描件" in bad["unreadable_reason"]
    review = scanned.get(f"{flow.path}/parse/review", headers=flow.headers).json()
    gates = {g["code"]: g for g in review["gates"]}
    assert gates["UNREADABLE_PENDING"]["count"] >= 1 and gates["UNREADABLE_PENDING"]["blocking"]
    assert gates["LOW_CONFIDENCE"]["count"] >= 1 and not gates["LOW_CONFIDENCE"]["blocking"]
    assert review["confidence_threshold"] == 0.8

    error = flow.write("/requirements/" + bad["id"], {"status": "confirmed"}, "PATCH", 409)
    assert error["code"] == "REQUIREMENT_NOT_READY" and "对照原页补录" in error["message"]
    batch = flow.write("/requirements/batch-confirm", {"requirement_ids": [bad["id"]]}, expected=409)
    assert batch["code"] == "REQUIREMENT_NOT_READY"

    fixed = flow.write("/requirements/" + bad["id"], {"text": "投标人须提供近三年同类项目业绩证明。"}, "PATCH")["requirement"]
    assert fixed["manually_edited"] and fixed["status"] == "pending"
    confirmed = flow.write("/requirements/" + bad["id"], {"status": "confirmed"}, "PATCH")["requirement"]
    assert confirmed["status"] == "confirmed"
    review = scanned.get(f"{flow.path}/parse/review", headers=flow.headers).json()
    unreadable_left = [r for r in flow.state()["requirements"] if r.get("unreadable") and not r.get("manually_edited") and r["status"] != "rejected"]
    assert {g["code"]: g for g in review["gates"]}["UNREADABLE_PENDING"]["count"] == len(unreadable_left) + sum(
        1 for f in flow.state()["facts"] if f.get("unreadable") and not f.get("manually_edited") and f["status"] != "rejected")


def test_threshold_comes_from_company_settings(scanned):
    admin = login(scanned, "alpha-company-admin")
    bad = scanned.patch("/api/v1/companies/alpha/settings", json={"parse_confidence_threshold": 0.3}, headers=admin)
    assert bad.status_code == 422 and bad.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    saved = scanned.patch("/api/v1/companies/alpha/settings", json={"parse_confidence_threshold": 0.95}, headers=admin)
    assert saved.status_code == 200, saved.text
    flow = _parse(scanned)
    review = scanned.get(f"{flow.path}/parse/review", headers=flow.headers).json()
    assert review["confidence_threshold"] == 0.95
    low = {g["code"]: g for g in review["gates"]}["LOW_CONFIDENCE"]
    pending = [r for r in flow.state()["requirements"] + flow.state()["facts"] if r.get("status") == "pending"]
    assert low["count"] == sum(1 for r in pending if r.get("confidence") is not None and r["confidence"] < 0.95) and "0.95" in low["label"]
