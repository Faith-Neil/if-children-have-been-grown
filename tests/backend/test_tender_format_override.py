# 为什么有这个文件：验证招标格式要求覆盖 Word 模板（PRD v1.8 §5.9.1 规则 5；APP-M2-T196）。
# 它解决什么问题：从已确认的格式类条款读出正文、标题字体字号、行距、页边距，按“招标 > 模板 > 默认”叠加并记依据；
# 没有已确认的格式条款时读招标原文；导出的 Word 用的是覆盖后的值。全部为合成招标文本。

from io import BytesIO
from zipfile import ZipFile

from icg.domain.tender_format import apply, overrides
from test_reference_flow import ProjectFlow, client  # noqa: F401

FORMAT = "投标文件正文采用仿宋小四号字，1.5倍行距；一级标题采用黑体三号；页边距上2.5cm、下2.5cm、左3cm、右2.5cm。"


def _workflow(text, status="confirmed"):
    return {"requirements": {"r1": {"id": "r1", "text": text, "status": status, "section_kind": "notice", "category": "business"}}}


def test_format_sentences_become_style_overrides_with_their_basis():
    changes, applied = overrides(_workflow(FORMAT))
    assert changes["body_font"]["east_asia"] == "仿宋" and changes["body_pt"] == 12.0 and changes["body_line_multiple"] == 1.5
    assert changes["h1_font"]["east_asia"] == "黑体" and changes["h1_pt"] == 16.0
    assert (changes["margin_top_cm"], changes["margin_left_cm"], changes["margin_right_cm"]) == (2.5, 3.0, 2.5)
    assert all(item["requirement_id"] == "r1" and item["quote"] for item in applied)
    merged = apply({"body_pt": 14, "h2_pt": 15}, changes)
    assert merged["body_pt"] == 12.0 and merged["h2_pt"] == 15  # 模板里招标没要求的项保留
    assert overrides({"requirements": {}})[0] == {} and apply(None, {}) is None
    exact, _ = overrides(_workflow("正文宋体四号，行距固定值28磅。"))
    assert exact["body_pt"] == 14.0 and exact["body_line_pt"] == 28.0 and "body_line_multiple" not in exact


def test_export_uses_the_tender_format(client):
    tender = ("合成招标文件：格式覆盖\n招标编号：SYNTH-001\n投标截止时间：2026-12-31T17:00:00+08:00\n服务期限：12个月\n"
              "★技术要求：每月完成巡检并提交报告。\f商务要求：提供有效企业资质证明。\n投标文件格式：" + FORMAT)
    flow = ProjectFlow(client)
    flow.reviewed(tender)
    flow.write("/parse/confirm", {})
    chapters = flow.state()["chapters"]
    evidence = flow.library()
    for row in flow.state()["requirements"]:
        chapter = next(c for c in chapters if c["volume"] == row["volume"])
        flow.write("/requirements/" + row["id"], {"chapter_id": chapter["id"], "response": "经核对满足要求。",
                   "evidence_ids": [evidence["id"]] if row["volume"] == "business" else []}, "PATCH")
    flow.confirm_plan({"chapters": [{"id": c["id"], "title": c["title"], "volume": c["volume"]} for c in chapters]})
    for chapter in flow.state()["chapters"]:
        flow.commit(chapter["id"], "合成正文：每月安排巡检，报告由负责人复核。")
    check = flow.write("/checks", {"volume": "all"})["check"]
    export = flow.write("/exports", {"check_id": check["id"], "kind": "internal", "volume": "all"})["export"]
    volume = export["volumes"][0]
    assert {item["item"] for item in volume["format_overrides"]} >= {"正文字体", "正文字号", "正文行距（倍数）", "一级标题字号"}
    data = client.get(volume["download_url"], headers=flow.headers).content
    archive = ZipFile(BytesIO(data))
    styles, document = archive.read("word/styles.xml").decode(), archive.read("word/document.xml").decode()
    body = styles[styles.index('w:styleId="BodyText"'):]
    body = body[:body.index("</w:style>")]
    assert 'w:eastAsia="仿宋"' in body and '<w:sz w:val="24"/>' in body and 'w:line="360" w:lineRule="auto"' in body
    assert 'w:left="1701"' in document  # 左 3cm
