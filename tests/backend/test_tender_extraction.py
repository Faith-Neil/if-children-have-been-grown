# 为什么有这个文件：核对按章节、按条目抽取招标条款，而不是把每一行都当条款。
# 它解决什么问题：真实招标文件有须知、评分、需求、合同条款和格式附件；只有需要响应的条目才进响应矩阵，
# ★ 条款不论在哪一章都不能漏，多行条目要合成一条，原句与页码可回查。

from icg.domain.tender_extraction import extract_facts, extract_requirements, segment

TENDER = [
    """第一章 招标公告
项目名称：合成市政务云运维服务采购项目
项目编号：HC-2026-0001
预算金额：380万元
一、投标人资格要求
1. 具有独立承担民事责任的能力，提供营业执照复印件。
2. 具有良好的商业信誉和健全的财务会计制度，
提供 2025 年度经审计的财务报告。
3. ★投标人须具备 ISO/IEC 27001 信息安全管理体系认证。
二、获取招标文件
1. 时间：2026 年 11 月 1 日至 11 月 7 日。""",
    """第二章 投标人须知
一、总则
1. 本次招标采用综合评分法。
2. 投标人应当按招标文件要求编制投标文件。
3. 投标文件未按要求密封的，按无效投标处理。
第三章 评标办法
一、评分标准
1. 技术方案（30分）：运维体系完整、流程清晰的得 30 分，
较完整的得 20 分，不完整的得 10 分。
2. 项目团队（20分）：项目经理具有 PMP 证书得 10 分。""",
    """第四章 采购需求
一、服务内容
1. 提供 7×24 小时驻场运维服务。
2. 一级故障 30 分钟内响应，2 小时内恢复。
▲3. 每季度提交服务报告。
二、人员要求
1. 驻场工程师不少于 6 名。
第五章 合同条款
一、通用条款
1. 甲方应按合同约定支付合同价款。
2. 乙方应保证所提供服务符合国家标准。
第六章 投标文件格式
一、投标函
1. 致：合成市大数据局
2. 我方愿意按照招标文件规定提供服务。""",
]


def _texts(rows):
    return [r.text for r in rows]


def test_chapters_are_classified():
    kinds = {s.title: s.kind for s in segment(TENDER) if s.level}
    assert kinds["第三章 评标办法"] == "scoring"
    assert kinds["第五章 合同条款"] == "contract"
    assert kinds["第六章 投标文件格式"] == "format"
    assert kinds["一、投标人资格要求"] == "qualification"
    assert kinds["第四章 采购需求"] == "technical"


def test_only_responsive_items_are_extracted_and_multiline_items_merge():
    rows, summary = extract_requirements(TENDER)
    texts = _texts(rows)
    assert summary["structured"] is True
    # 合同条款与格式附件不抽
    assert not any("支付合同价款" in t or "致：合成市大数据局" in t for t in texts)
    # 两行的资格条目合成一条，后半句不丢
    finance = next(r for r in rows if "健全的财务会计制度" in r.text)
    assert "经审计的财务报告" in finance.text and finance.section_kind == "qualification"
    assert finance.quote.startswith("2. 具有良好的商业信誉") and finance.page == 1
    # 评分项带分值，跨行合并
    scheme = next(r for r in rows if r.text.startswith("1. 技术方案"))
    assert scheme.score == 30.0 and "不完整的得 10 分" in scheme.text and scheme.category == "scoring"
    # 须知里的程序性说明不抽，含实质性后果的必须抽
    assert not any("采用综合评分法" in t for t in texts)
    assert any("无效投标" in t for t in texts)
    # 获取招标文件的时间安排不是需要响应的条款
    assert not any("11 月 1 日至" in t for t in texts)
    assert summary["skipped_items"].get("contract", 0) >= 2 and summary["skipped_items"].get("format", 0) >= 2


def test_mandatory_items_are_never_dropped_and_routed():
    rows, summary = extract_requirements(TENDER)
    star = next(r for r in rows if "27001" in r.text)
    assert star.mandatory and star.category == "mandatory" and star.volume == "business"
    triangle = next(r for r in rows if "每季度提交服务报告" in r.text)
    assert triangle.mandatory and triangle.volume == "technical"
    assert summary["mandatory"] >= 3
    sla = next(r for r in rows if "30 分钟内响应" in r.text)
    assert sla.volume == "technical" and sla.section_path[0] == "第四章 采购需求"


def test_every_quote_is_verbatim_on_its_page():
    rows, _ = extract_requirements(TENDER)
    for row in rows:
        assert row.quote in TENDER[row.page - 1], row


def test_facts_use_aliases():
    facts = {(f.key, f.value) for f in extract_facts(TENDER)}
    assert ("项目名称", "合成市政务云运维服务采购项目") in facts
    assert ("招标编号", "HC-2026-0001") in facts
    assert ("预算金额", "380万元") in facts


def test_unstructured_short_text_keeps_line_behaviour():
    rows, summary = extract_requirements(["★技术要求：一级故障响应时限不得超过30分钟。\n服务期限：12个月"])
    assert summary["structured"] is False and len(rows) == 2


# —— 真实招标文件版式（贵阳银行基础软件平台维保，76 页）——
import re
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "tender_guiyang_2025_excerpt.txt"


def _guiyang_pages():
    raw = FIXTURE.read_text(encoding="utf-8")
    pages = [""] * 76
    for match in re.finditer(r"=== PAGE (\d+) ===\n(.*?)(?==== PAGE|\Z)", raw, re.S):
        pages[int(match.group(1)) - 1] = match.group(2)
    return pages


def test_real_tender_inline_qualification_items_are_split():
    rows, _ = extract_requirements(_guiyang_pages())
    quals = [r for r in rows if r.section_kind == "qualification"]
    assert [r.text[:3] for r in quals] == [f"（{n}）" for n in range(1, 9)]
    assert "经审计的财务报告" in quals[1].text and "原厂授权服务商" in quals[4].text
    assert all(r.page == 3 for r in quals)


def test_real_tender_negation_phrases_are_mandatory():
    rows, summary = extract_requirements(_guiyang_pages())
    mandatory = [r.text for r in rows if r.mandatory]
    assert any("将被否决" in t for t in mandatory)
    assert any("视为无效投标" in t and "签字盖章" in t for t in mandatory)
    assert any("做废标处理" in t for t in mandatory)
    # ★ 只出现在格式章的盖章说明里，仍然必抽
    assert any("标★处" in t for t in mandatory)
    assert summary["mandatory"] >= 4


def test_real_tender_flattened_scoring_table_keeps_points():
    rows, _ = extract_requirements(_guiyang_pages())
    scoring = {r.text.split("（", 1)[0]: r.score for r in rows if r.section_kind == "scoring"}
    assert scoring == {"投标报价": 30.0, "技术方案": 25.0, "项目团队": 24.0, "类似业绩": 7.0}
    assert not any("评分因素" in r.text or "前附表" in r.text for r in rows)


def test_real_tender_skips_contract_format_and_procedural_notice():
    rows, summary = extract_requirements(_guiyang_pages())
    texts = [r.text for r in rows]
    assert not any("支付合同价款" in t or "致：贵阳银行" in t for t in texts)
    assert not any(t.startswith("2.1 招标文件包括") for t in texts)
    assert any("驻场工程师不少于2名" in t and r.section_kind == "technical" for t, r in zip(texts, rows))
    assert len(rows) <= 30


def test_real_tender_quotes_verbatim_and_facts_from_tables():
    pages = _guiyang_pages()
    rows, _ = extract_requirements(pages)
    for row in rows:
        assert row.quote in pages[row.page - 1], row
    facts = {(f.key, f.value) for f in extract_facts(pages)}
    assert ("招标编号", "P52011520250008VU") in facts
    assert ("预算金额", "3750000.00元") in facts and ("最高限价", "3750000.00元") in facts
    assert ("投标截止时间", "2025年09月08日 09时30分") in facts
    assert ("投标保证金", "人民币6万元") in facts
    assert ("服务期限", "三年") in facts
    for fact in extract_facts(pages):
        assert fact.quote in pages[fact.page - 1], fact
