# 为什么有这个文件：验证 R29 本公司查重与 R30 超范围响应（APP-M2-T235～T237，PRD v1.8 §5.8.1 / §5.8.3），以及警告逐项放行。
# 它解决什么问题：按 PRD 验收条目逐条核对——近 20 个月的历史标书原样复用要报、30 个月前的不报、招标原文与注明出处不报、
# 改连续字数后按新设置算、白名单术语不计；无条款段落与额外数值承诺按增值/非增值区分；警告须负责人填理由放行、阻断不能放行。

from datetime import date, timedelta
from uuid import uuid4

from icg.domain.scope_rules import commitments_in, duplicate_runs, grams, normalize
from test_reference_flow import ProjectFlow, client, login  # noqa: F401

REUSED = "我司建立了覆盖事前预防事中处置事后复盘的三级运维保障体系确保业务连续"


def _months_ago(months):
    return (date.today() - timedelta(days=int(months * 30.5))).isoformat()


def _rules(flow, volume="all"):
    resp = flow.client.get(f"{flow.path}/compliance-rules?volume={volume}", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    return {r["rule_id"]: r for r in resp.json()["rules"]}


def _technical(flow):
    return next(c for c in flow.state()["chapters"] if c["volume"] == "technical")


def _settings(flow, **values):
    resp = flow.client.patch("/api/v1/companies/alpha/settings", headers=login(flow.client, "alpha-company-admin"), json=values)
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------- 纯函数

def test_normalize_drops_punctuation_variables_and_ascii_terms():
    assert normalize("巡检，每月 一次！") == "巡检每月一次"
    assert "MySQL" not in normalize("采用 MySQL 数据库主备") and normalize("采用 MySQL 数据库主备").count("\u0000") == 1
    assert normalize("{{fact:f1}}小时[证:ev1]响应") == "\u0000小时\u0000响应"
    value = normalize(REUSED)
    covered, runs = duplicate_runs(value, 8, {g: 0 for g in grams(value, 8)}, set())
    assert covered == len(value) and runs[0][0] == value


def test_commitments_skip_dates_and_normalize_units():
    found = {(v, u) for v, u, _ in commitments_in("2025年起提供 30 分钟响应，驻场 2 名工程师，每季度 1 次巡检，可用率 99.9％，质保3个月")}
    assert found == {("30", "分钟"), ("2", "人"), ("1", "次"), ("99.9", "%"), ("3", "月")}
    assert commitments_in("见第 2025 年版规范") == []


# ---------------------------------------------------------------- R29

def test_r29_reports_recent_history_and_skips_old_cited_and_tender_text(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    flow.library(name="2024 年某银行运维投标书", type="history", content=f"第三章 运维体系\n{REUSED}。",
                 status="pending", submitted_on=_months_ago(20))
    flow.commit(chapter["id"], f"技术正文：{REUSED}。")
    r29 = _rules(flow)["R29"]
    assert r29["passed"] is False and r29["severity"] == "info"
    issue = r29["issues"][0]
    assert issue["code"] == "COMPANY_DUPLICATE_TEXT" and issue["chapter_id"] == chapter["id"]
    assert issue["details"]["targets"][0]["name"] == "2024 年某银行运维投标书"
    assert issue["details"]["dup_char_count"] >= len(REUSED) - 2
    # 分册检查不运行 R29
    assert _rules(flow, "technical")["R29"]["details"]["skipped"] == "volume_check"

    # 注明出处的段落不报
    flow.commit(chapter["id"], f"技术正文：{REUSED}（出处：本公司 2024 年运维白皮书）。")
    assert _rules(flow)["R29"]["passed"] is True


def test_r29_ignores_history_older_than_window(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    flow.library(name="三十个月前的投标书", type="history", content=REUSED, status="pending", submitted_on=_months_ago(30))
    flow.commit(chapter["id"], f"技术正文：{REUSED}。")
    assert _rules(flow)["R29"]["passed"] is True


def test_r29_reference_material_is_warning_and_min_chars_setting_applies(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    flow.library(name="行业白皮书摘录", type="qualification", content="故障发生后立即启动应急响应流程", status="pending",
                 source_tier="reference")
    # 正文里只有 9 个字与资料相同：按默认 8 字报，改为 10 字后不报
    flow.commit(chapter["id"], "技术正文：发生后立即启动应急，由值班经理统一调度。")
    r29 = _rules(flow)["R29"]
    assert r29["passed"] is False and r29["issues"][0]["severity"] == "warning"
    _settings(flow, dup_min_chars=10)
    assert _rules(flow)["R29"]["passed"] is True


def test_r29_whitelist_terms_and_tender_text_do_not_count(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    flow.library(name="历史标书", type="history", content="数据库采用 MySQL 主备 ALTER SYSTEM 参数调优", status="pending",
                 submitted_on=_months_ago(3))
    flow.commit(chapter["id"], "技术正文：数据库采用 MySQL 主备 ALTER SYSTEM 参数调优。")
    # 去掉英文术语后每段只剩 ≤5 个中文字，凑不成 8 字重复
    assert _rules(flow)["R29"]["passed"] is True
    requirement = flow.state()["requirements"][0]["text"]
    flow.library(name="历史标书二", type="history", content=requirement, status="pending", submitted_on=_months_ago(3))
    flow.commit(chapter["id"], f"技术正文：{requirement}")
    assert _rules(flow)["R29"]["passed"] is True  # 与招标原文相同的部分不算重复


# ---------------------------------------------------------------- R30

def test_r30_flags_extra_numeric_commitment_but_not_tender_backed_numbers(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    row = next(r for r in flow.state()["requirements"] if r["volume"] == "technical")
    flow.write("/requirements/" + row["id"], {"text": "一级故障 30 分钟内响应。", "chapter_id": chapter["id"],
                                             "response": "满足。"}, "PATCH")
    flow.commit(chapter["id"], "技术正文：一级故障 30 分钟内响应，并免费延长质保 24 个月。")
    r30 = _rules(flow, "technical")["R30"]
    extra = [i for i in r30["issues"] if i["code"] == "EXTRA_NUMERIC_COMMITMENT"]
    assert len(extra) == 1 and extra[0]["details"]["values"] == ["24 个月"] and extra[0]["severity"] == "warning"


def test_r30_chapter_without_clause_is_warning(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    for row in flow.state()["requirements"]:
        if row["chapter_id"] == chapter["id"]:
            flow.write("/requirements/" + row["id"], {"chapter_id": None}, "PATCH")
    r30 = _rules(flow, "technical")["R30"]
    assert any(i["code"] == "SCOPE_CHAPTER_WITHOUT_CLAUSE" for i in r30["issues"])


def test_recheck_routes_extra_commitment_to_project_lead(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    flow.commit(chapter["id"], "技术正文：每月巡检，另承诺免费延长质保 24 个月。")
    headers = {**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    assert client.post(f"{flow.path}/chapters/{chapter['id']}/loop/recheck", json={}, headers=headers).status_code == 200
    issues = client.get(f"{flow.path}/human-queue", headers=flow.headers).json()["chapters"][0]["issues"]
    extra = next(i for i in issues if i["code"] == "EXTRA_NUMERIC_COMMITMENT")
    assert extra["human_reason_label"] == "招标未要求的额外数值承诺" and extra["route"] == "direct_human"
    writer = client.get(f"{flow.path}/human-queue", headers=login(client, "alpha-editor")).json()
    writer_issue = next(i for g in writer["chapters"] for i in g["issues"] if i["code"] == "EXTRA_NUMERIC_COMMITMENT")
    assert writer_issue["permissions"]["resolve"] is False  # 额外承诺只能由项目负责人处理


# ---------------------------------------------------------------- 警告放行

def test_warning_release_requires_lead_and_reason_and_expires_with_content(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    flow.commit(chapter["id"], "技术正文：每月巡检，另承诺免费延长质保 24 个月。")
    check = flow.write("/checks", {"volume": "all"})["check"]
    assert check["passed"] is False
    issue = next(i for i in check["issues"] if i["code"] == "EXTRA_NUMERIC_COMMITMENT")
    path = f"/checks/{check['id']}/issues/{issue['id']}/release"

    viewer = {**login(client, "alpha-viewer"), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    assert client.post(flow.path + path, json={"reason": "x"}, headers=viewer).status_code == 403
    flow.write(path, {"reason": ""}, expected=422)
    released = flow.write(path, {"reason": "销售确认本项目额外赠送质保", "decision": "keep"})["check"]
    target = next(i for i in released["issues"] if i["id"] == issue["id"])
    assert target["released"]["reason"] == "销售确认本项目额外赠送质保"
    blockers_left = [i for i in released["issues"] if i["severity"] not in ("info", "hint") and not i.get("released")]
    assert released["passed"] is (not blockers_left)

    # 同样内容重新检查，放行仍有效；改了正文就是新问题
    again = flow.write("/checks", {"volume": "all"})["check"]
    assert next(i for i in again["issues"] if i["code"] == "EXTRA_NUMERIC_COMMITMENT").get("released")
    flow.commit(chapter["id"], "技术正文：每月巡检，另承诺免费延长质保 36 个月。")
    changed = flow.write("/checks", {"volume": "all"})["check"]
    assert not next(i for i in changed["issues"] if i["code"] == "EXTRA_NUMERIC_COMMITMENT").get("released")


def test_blocker_cannot_be_released(client):
    flow = ProjectFlow(client).ready()
    chapter = _technical(flow)
    flow.commit(chapter["id"], "技术正文：项目经理为【待补：姓名】。")
    check = flow.write("/checks", {"volume": "all"})["check"]
    blocker = next(i for i in check["issues"] if i["severity"] in ("blocker", "blocking"))
    flow.write(f"/checks/{check['id']}/issues/{blocker['id']}/release", {"reason": "想放行"}, expected=409)


def test_r30_value_added_chapter_exempts_scope_but_not_numbers():
    from types import SimpleNamespace
    from icg.domain.scope_rules import check_r30

    chapter = SimpleNamespace(id="c1", project_id="p", volume="technical", title="增值服务方案",
                              content="开篇概述。\n我司额外提供年度安全培训与知识转移，帮助客户团队成长。\n额外提供 2 名驻场工程师。\n总结。")
    project = SimpleNamespace(id="p", company_id="alpha")
    state = SimpleNamespace(chapters={"c1": chapter}, projects={"p": project}, workflows={})
    plain = {"requirements": {}, "files": {}, "facts": {}}
    codes = {i["code"] for i in check_r30(state, project, plain).issues}
    assert codes == {"SCOPE_CHAPTER_WITHOUT_CLAUSE", "EXTRA_NUMERIC_COMMITMENT"}
    value_added = {**plain, "outline_plans": {"c1": {"value_added": True}}}
    issues = check_r30(state, project, value_added).issues
    assert [i["code"] for i in issues] == ["EXTRA_NUMERIC_COMMITMENT"]
    assert issues[0]["details"]["value_added_chapter"] is True
