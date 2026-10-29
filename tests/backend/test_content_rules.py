# 为什么有这个文件：验证 R36、R39、R40、R41、R42、R43、R44（PRD v1.8 §5.8.1）的正例与反例。
# 它解决什么问题：这些规则依赖正文内容；数据缺失的子项必须写“未核对”，不能冒充通过。

from types import SimpleNamespace

from icg.domain.content_rules import check_r36, check_r39, check_r40, check_r41, check_r42, check_r43, check_r44


def _chapter(cid, volume, title, content):
    return SimpleNamespace(id=cid, project_id="p", volume=volume, title=title, content=content, revision=1)


def _state(chapters, library=(), team_mode="both", company_name=""):
    return SimpleNamespace(
        chapters={c.id: c for c in chapters}, library={i["id"]: i for i in library},
        workflows={"p": {"chapter_order": [c.id for c in chapters]}}, projects={},
        project_teams={"p": {"volume_mode": team_mode, "members": {}, "owners": {}}},
        service_stores={"company_settings": {"alpha": {"company_name": company_name}}} if company_name else {})


PROJECT = SimpleNamespace(id="p", company_id="alpha")


def _wf(text="", requirements=()):
    return {"files": {"f": {"filename": "t.pdf", "pages": [text]}}, "requirements": {r["id"]: r for r in requirements},
            "facts": {}, "outline_plans": {}}


def _codes(result):
    return {i["code"] for i in result.issues}


def test_r36_cross_volume_and_single_volume_skip():
    lib = [{"id": "q1", "company_id": "alpha", "type": "qualification", "name": "ISO27001证书", "status": "confirmed"},
           {"id": "p1", "company_id": "alpha", "type": "personnel", "name": "张三丰", "status": "confirmed"}]
    chapters = [_chapter("t", "technical", "技术方案", "我司持有ISO27001证书，项目经理张三丰。"),
                _chapter("b", "business", "商务响应", "资质见附件。")]
    result = check_r36(_state(chapters, lib), PROJECT, _wf())
    assert _codes(result) == {"CROSS_VOLUME_QUALIFICATION_MISSING", "CROSS_VOLUME_PERSONNEL_MISMATCH"}
    assert not result.passed and result.severity == "blocker"
    chapters[1].content = "ISO27001证书复印件；人员一览：张三丰。"
    assert check_r36(_state(chapters, lib), PROJECT, _wf()).passed
    single = check_r36(_state(chapters[:1], lib, "technical_only"), PROJECT, _wf())
    assert single.passed and single.details["skipped"] == "single_volume" and "R36 未运行" in single.finding_summary


def test_r39_disclosure_paragraph_required_and_never_auto_passes():
    row = {"id": "r", "text": "投标人须如实披露近三年行政处罚情况。", "status": "confirmed", "volume": "technical", "chapter_id": "c"}
    chapters = [_chapter("c", "technical", "企业信誉", "我司经营规范。")]
    assert _codes(check_r39(_state(chapters), PROJECT, _wf(requirements=[row]))) == {"DISCLOSURE_MISSING"}
    chapters[0].content = "我司近三年未受到任何行政处罚。"
    result = check_r39(_state(chapters), PROJECT, _wf(requirements=[row]))
    assert _codes(result) == {"DISCLOSURE_UNVERIFIED"} and result.severity == "warning"


def test_r40_review_index_coverage_order_and_targets():
    rows = [{"id": "s1", "text": "技术方案（30分）", "category": "scoring", "score": 30, "status": "confirmed", "volume": "technical"},
            {"id": "s2", "text": "项目团队（20分）", "category": "scoring", "score": 20, "status": "confirmed", "volume": "technical"}]
    wf = _wf("本项目须提供评审索引表。", rows)
    missing = check_r40(_state([_chapter("a", "technical", "技术方案", "正文")]), PROJECT, wf)
    assert _codes(missing) == {"REVIEW_INDEX_MISSING"}
    index = _chapter("i", "technical", "评审索引表", "| 评分项 | 章节 |\n|---|---|\n| 项目团队 | 第 2 章 |\n| 技术方案 | 第 9 章 |")
    result = check_r40(_state([_chapter("a", "technical", "技术方案", "正文"), index]), PROJECT, wf)
    assert _codes(result) == {"REVIEW_INDEX_ORDER", "REVIEW_INDEX_TARGET_MISSING"}
    assert check_r40(_state([index]), PROJECT, _wf("无索引要求", rows)).passed


def test_r41_proof_materials_and_seal_hint():
    rows = [{"id": "q", "text": "提供营业执照复印件。", "category": "qualification", "status": "confirmed", "volume": "business"},
            {"id": "s", "text": "提供类似项目合同扫描件（每个得1分）", "category": "scoring", "status": "confirmed", "volume": "technical"}]
    result = check_r41(_state([]), PROJECT, _wf("投标函须加盖公章。", rows))
    assert _codes(result) == {"PROOF_MATERIAL_MISSING", "SCORING_PROOF_MISSING", "SEAL_STATUS_UNVERIFIED"}
    for row in rows:
        row["evidence_ids"] = ["e1"]
    hinted = check_r41(_state([]), PROJECT, _wf("投标函须加盖公章。", rows))
    assert _codes(hinted) == {"SEAL_STATUS_UNVERIFIED"} and hinted.passed  # 盖章只是提示，不挡导出


def test_r42_blind_bid_identity_in_body():
    lib = [{"id": "p1", "company_id": "alpha", "type": "personnel", "name": "李四", "status": "confirmed"}]
    chapters = [_chapter("t", "technical", "技术方案", "项目经理李四负责，联系电话13800138000。\n华东数智承诺按期交付。")]
    result = check_r42(_state(chapters, lib, company_name="华东数智"), PROJECT, _wf("技术部分采用暗标评审。"))
    assert len(result.issues) == 2 and not result.passed
    assert check_r42(_state(chapters, lib), PROJECT, _wf("无特殊要求")).passed


def test_r43_ai_tone_and_tender_words_released():
    text = ("我们高度重视本项目，提供全方位、全流程、一站式的服务，打造行业领先的赋能体系。\n"
            "不是简单运维，而是深度融合。不是被动响应，而是主动保障。\n"
            "我们将持续优化。\n我们将不断创新。\n我们将全面提升。\n总之，我们有能力完成。\n结束语。")
    result = check_r43(_state([_chapter("c", "technical", "服务方案", text)]), PROJECT, _wf())
    findings = result.issues[0]["details"]["findings"]
    assert any("套话" in f for f in findings) and any("否定对比" in f for f in findings)
    assert any("连续 3 段" in f for f in findings) and any("总结句" in f for f in findings)
    assert result.severity == "warning"
    plain = check_r43(_state([_chapter("c", "technical", "服务方案", "每月巡检一次，故障30分钟响应。")]), PROJECT, _wf())
    assert plain.passed


def test_r44_fact_density_per_scoring_item():
    rows = [{"id": f"s{i}", "text": f"评分项{i}", "category": "scoring", "status": "confirmed", "volume": "technical", "chapter_id": "c"}
            for i in range(3)]
    thin = _chapter("c", "technical", "实施方案", "我们将认真做好各项工作，确保项目顺利实施。")
    assert _codes(check_r44(_state([thin]), PROJECT, _wf(requirements=rows))) == {"LOW_FACT_DENSITY"}
    thin.content = "驻场 2 名工程师，故障 30 分钟响应，每月 1 次巡检。"
    assert check_r44(_state([thin]), PROJECT, _wf(requirements=rows)).passed
