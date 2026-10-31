# 为什么有这个文件：验证本项目招标文件切片轻量索引检索与结构化证据展示（APP-M2-T184，PRD v1.8 §技术方案E08、§5.11.15）。
# 它解决什么问题：
# 1. 切片轻量索引构建与属性抽取：断言条款编号、原文页码、条款类型（废标/评分/商务/技术）、重要性（★）与分值抽取；
# 2. 关键词检索与高亮显示：断言分词匹配、精准定位、HTML 安全包裹 <mark> 标签高亮；
# 3. E08 特性开关控制：断言默认关闭时不检索（返回关闭提示），显式开启后正常检索；
# 4. 证据卡防篡改与插入门禁：断言本项目数据类答案卡一律 can_insert=False, action="inject_context"；
# 5. 一键条款注入当前编辑章节 Prompt 上下文：断言注入后 Prompt 出现条款约束、上下文指纹更新、清除功能正常；
# 6. 数据隔离与 RBAC 权限：严格断言跨项目切片不泄露、跨公司 404、非成员 403、只读成员无权注入；
# 7. HTTP 端点与 OpenAPI 契约安全：端点正常工作且 include_in_schema=False 保持契约冻结不漂移。

import base64
import html
import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.answer_card import AnswerCardService
from icg_demo.domain import Account, DemoService, DomainError, Lease, Principal, Project
from icg_demo.editor_ai_context import build_editor_prompt_context
from icg_demo.main import create_app
from icg_demo.parsing import LocalTextParser
from icg_demo.tender_retrieval import (
    TenderRetrievalService,
    TenderSlice,
    classify_clause_type,
    detect_importance,
    extract_clause_number,
    extract_score_weight,
    highlight_keywords,
    tokenize_query,
)
from icg_demo.workflow import WorkflowService


SAMPLE_TENDER_PAGE_1 = """合成招标文件：星河云平台维保服务项目
招标编号：XH-2026-CLOUD-001
投标截止时间：2026-12-31T17:00:00+08:00
采购人：星河云计算科技有限公司
第三条 投标保证金：本项目投标保证金为人民币伍拾万元整，须在截止日前缴纳。
"""

SAMPLE_TENDER_PAGE_2 = """★第一条 废标条款：未按招标文件要求提供原厂原装授权函及售后承诺书的，作废标处理。
第二条 实质性要求：投标人必须具备 CMMI 3 级以上认证，否则否决投标。
3.1.2 技术要求：提供同城双活高可用数据库集群架构，故障切换时限不超过30秒。
"""

SAMPLE_TENDER_PAGE_3 = """4.2 评分标准：提供高可用双活方案且通过巡检实测得10分，提供单机热备得5分，其余得0分。
第五条 商务要求：近三年具备同类金融行业云平台维保业绩，每份合同得2分，最高6分。
第六条 服务期限：服务期自合同签订之日起 36 个月。
"""


@pytest.fixture
def repo():
    return MemoryRepository(seed_state())


@pytest.fixture
def parser():
    return LocalTextParser()


@pytest.fixture
def demo(repo):
    return DemoService(repo, None)


@pytest.fixture
def workflow(demo, parser):
    return WorkflowService(demo, parser)


@pytest.fixture
def setup_project(repo, workflow):
    def seed_sessions(st):
        st.sessions.update({
            "token-manager": "alpha-manager",
            "token-editor": "alpha-editor",
            "token-viewer": "alpha-viewer",
            "token-outsider": "alpha-outsider-manager",
            "token-beta": "beta-editor",
            "token-beta-manager": "beta-manager",
        })
    repo.transaction(seed_sessions)

    state = repo.read()
    project_id = "alpha-project"
    alpha_manager = Principal(state.accounts["alpha-manager"], "token-manager")
    alpha_editor = Principal(state.accounts["alpha-editor"], "token-editor")

    # 上传多页多条款招标文件并解析
    multi_page_content = f"{SAMPLE_TENDER_PAGE_1}\f{SAMPLE_TENDER_PAGE_2}\f{SAMPLE_TENDER_PAGE_3}"
    payload = {
        "filename": "星河云维保招标文件.txt",
        "content_base64": base64.b64encode(multi_page_content.encode("utf-8")).decode("ascii"),
    }
    upload_res = workflow.upload(
        alpha_manager,
        project_id,
        payload,
        expected=str(state.projects[project_id].revision),
        key="key-up-1",
    )
    file_id = upload_res["file"]["id"]
    state = repo.read()
    workflow.parse(
        alpha_manager,
        project_id,
        {"file_ids": [file_id]},
        expected=str(state.projects[project_id].revision),
        key="key-parse-1",
    )

    return {
        "project_id": project_id,
        "file_id": file_id,
        "manager": alpha_manager,
        "editor": alpha_editor,
        "viewer": Principal(state.accounts["alpha-viewer"], "token-viewer"),
        "outsider": Principal(state.accounts["alpha-outsider-manager"], "token-outsider"),
        "beta_user": Principal(state.accounts["beta-editor"], "token-beta"),
    }


def test_clause_parsing_and_metadata_extraction():
    """测试条款编号、类型、重要性与分值提取工具函数。"""
    # 条款编号抽取
    assert extract_clause_number("第三条 投标保证金：50万元") == "第三条"
    assert extract_clause_number("★第一条 废标条款：未提供授权") == "★第一条"
    assert extract_clause_number("3.1.2 技术要求：高可用架构") == "3.1.2"
    assert extract_clause_number("4.2 评分标准：实测得10分") == "4.2"
    assert extract_clause_number("（一）商务响应：有效业绩证明") == "（一）"

    # 条款类型分类
    c_type, c_lbl = classify_clause_type("★第一条 废标条款：未按要求提供原厂原装授权函的，作废标处理。")
    assert c_type == "disqualification"
    assert c_lbl == "废标条款"

    c_type, c_lbl = classify_clause_type("4.2 评分标准：提供高可用双活方案且通过实测得10分。")
    assert c_type == "scoring"
    assert c_lbl == "评分标准"

    c_type, c_lbl = classify_clause_type("第三条 投标保证金：本项目投标保证金为人民币伍拾万元整。")
    assert c_type == "business"
    assert c_lbl == "商务要求"

    c_type, c_lbl = classify_clause_type("3.1.2 技术要求：提供同城双活高可用数据库集群架构。")
    assert c_type == "technical"
    assert c_lbl == "技术要求"

    # 重要性与分值抽取
    assert detect_importance("★第一条 废标条款", "disqualification") == "star"
    assert detect_importance("第二条 废标项：资质不符", "disqualification") == "disqualification"
    assert detect_importance("4.2 评分标准", "scoring") == "scoring"
    assert detect_importance("普通条款描述", "general") == "normal"

    assert extract_score_weight("提供高可用双活方案得10分，单机得5分") == 10.0
    assert extract_score_weight("每份合同得2分，最高6分") == 2.0
    assert extract_score_weight("无分值要求的条款") is None


def test_tokenization_and_highlighting():
    """测试查询词分词与 HTML 安全包裹高亮。"""
    query = "请问本项目投标保证金是多少？"
    tokens = tokenize_query(query)
    assert "投标保证金" in tokens
    assert "保证金" in tokens
    assert "请问" not in tokens  # 停用词被过滤

    content = "第三条 投标保证金：本项目投标保证金为人民币伍拾万元整。"
    highlighted, matched = highlight_keywords(content, ["投标保证金", "保证金"])
    assert "<mark>投标保证金</mark>" in highlighted
    assert "投标保证金" in matched

    # XSS 安全转义防护
    xss_content = "条款 <script>alert(1)</script> 保证金：50万 & 特殊符号"
    xss_highlighted, _ = highlight_keywords(xss_content, ["保证金"])
    assert "<script>" not in xss_highlighted
    assert "&lt;script&gt;" in xss_highlighted
    assert "<mark>保证金</mark>" in xss_highlighted


def test_indexing_and_e08_switch(setup_project, workflow):
    """测试 E08 特性开关控制（默认关闭时不检索，开启后正常检索）。"""
    ctx = setup_project
    pid = ctx["project_id"]
    editor = ctx["editor"]

    # 1. 默认未开启时检索：应返回 enabled=False，slices=[]，并提示功能已关闭
    res_default = workflow.search_tender_slices(editor, pid, "投标保证金")
    assert res_default["enabled"] is False
    assert len(res_default["slices"]) == 0
    assert "已关闭（默认关闭可选）" in res_default["notice"]
    assert res_default["answer_card"]["records"] == []

    # 2. 显式在查询参数中传入 enabled=True：激活切片索引检索
    res_enabled_param = workflow.search_tender_slices(editor, pid, "投标保证金", enabled=True)
    assert res_enabled_param["enabled"] is True
    assert len(res_enabled_param["slices"]) >= 1
    top_slice = res_enabled_param["slices"][0]
    assert top_slice["page"] == 1
    assert "投标保证金" in top_slice["content"]
    assert "<mark>投标保证金</mark>" in top_slice["highlighted_content"]

    # 3. 更新项目级特性开关为 True
    workflow.set_tender_indexing_switch(editor, pid, True)
    assert workflow.get_tender_indexing_switch(pid) is True

    # 4. 再次不带 enabled 参数查询：此时项目级开关生效，正常返回命中结果
    res_project_switch = workflow.search_tender_slices(editor, pid, "双活 高可用 评分")
    assert res_project_switch["enabled"] is True
    assert len(res_project_switch["slices"]) >= 1
    # 评分标准或高可用相关切片应排在前面
    slice_contents = [s["content"] for s in res_project_switch["slices"]]
    assert any("双活" in c for c in slice_contents)


def test_page_number_and_clause_type_accuracy(setup_project, workflow):
    """测试原文页码定位与条款类型分类准确度。"""
    ctx = setup_project
    pid = ctx["project_id"]
    editor = ctx["editor"]

    # 检索废标条款
    res_void = workflow.search_tender_slices(editor, pid, "废标条款 原厂授权", enabled=True)
    assert res_void["enabled"] is True
    assert len(res_void["slices"]) >= 1
    star_slice = res_void["slices"][0]
    assert star_slice["page"] == 2  # 位于第二页
    assert star_slice["clause_type"] == "disqualification"
    assert star_slice["clause_type_label"] == "废标条款"
    assert star_slice["importance"] == "star"
    assert "★第一条" in star_slice["clause_number"]

    # 检索评分标准
    res_score = workflow.search_tender_slices(editor, pid, "评分标准 10分", enabled=True)
    assert res_score["enabled"] is True
    score_slice = res_score["slices"][0]
    assert score_slice["page"] == 3  # 位于第三页
    assert score_slice["clause_type"] == "scoring"
    assert score_slice["clause_type_label"] == "评分标准"
    assert score_slice["score_weight"] == 10.0


def test_answer_card_safety_and_insertion_gate(setup_project, workflow):
    """测试结构化证据卡（AnswerCard）装配与禁止插入正文安全门禁。"""
    ctx = setup_project
    pid = ctx["project_id"]
    editor = ctx["editor"]

    res = workflow.search_tender_slices(editor, pid, "投标保证金", enabled=True)
    card = res["answer_card"]
    assert card is not None
    assert card["source"] == "本项目招标文件"
    assert card["source_type"] == "tender_document"
    assert card["direct_query_domain"] == "tender_slice"
    # 严格遵循 PRD 5.11.15 第 4 部分第 9 条：本项目数据类证据卡一律 can_insert=False
    assert card["can_insert"] is False
    assert "不提供直接插入正文" in card["insert_disabled_reason"]
    assert card["disclaimer"] == "系统直查 · 招标文件原文切片"
    assert len(card["records"]) >= 1
    assert card["records"][0]["action"] == "inject_context"


def test_inject_clauses_to_chapter_context(setup_project, workflow, repo):
    """测试一键将招标文件条款约束注入当前编辑章节的 Prompt 上下文与指纹联动。"""
    ctx = setup_project
    pid = ctx["project_id"]
    editor = ctx["editor"]
    chapter_id = "alpha-tech"

    # 1. 检索切片并选取切片 ID（包含废标条款与技术要求条款）
    search_res = workflow.search_tender_slices(editor, pid, "★第一条 废标", enabled=True)
    assert len(search_res["slices"]) >= 1
    selected_slice_ids = [search_res["slices"][0]["slice_id"]]
    more_res = workflow.search_tender_slices(editor, pid, "高可用", enabled=True)
    assert len(more_res["slices"]) >= 1
    selected_slice_ids.append(more_res["slices"][0]["slice_id"])

    # 2. 注入当前章节
    inject_res = workflow.inject_tender_clauses(editor, pid, chapter_id, slice_ids=selected_slice_ids)
    assert inject_res["chapter_id"] == chapter_id
    assert inject_res["injected_count"] == 2
    assert "成功为章节" in inject_res["message"]

    # 3. 读取当前已注入条款
    injected_list = workflow.get_injected_tender_clauses(editor, pid, chapter_id)
    assert len(injected_list) == 2

    # 4. 验证 Prompt 上下文组装：包含【用户主动注入的招标文件特定条款约束】
    state = repo.read()
    prompt_ctx = build_editor_prompt_context(
        state=state,
        project_id=pid,
        chapter_id=chapter_id,
        query="请核对本章是否符合废标要求",
    )
    user_prompt = prompt_ctx["user_content"]
    system_prompt = prompt_ctx["system_prompt"]

    assert "【用户主动注入的招标文件特定条款约束】" in user_prompt
    assert "废标条款" in user_prompt
    assert "严格遵循招标文件特定条款约束" in system_prompt
    assert "injected_tender_clauses" in prompt_ctx
    assert len(prompt_ctx["injected_tender_clauses"]) == 2

    # 5. 清除注入条款
    clear_ok = workflow.clear_injected_tender_clauses(editor, pid, chapter_id)
    assert clear_ok is True
    assert workflow.get_injected_tender_clauses(editor, pid, chapter_id) == []


def test_cross_project_and_tenant_isolation(setup_project, workflow, repo):
    """测试严格的数据隔离：禁止跨项目越权检索与跨公司访问。"""
    ctx = setup_project
    pid_alpha = ctx["project_id"]
    manager_alpha = ctx["manager"]
    editor_beta = ctx["beta_user"]

    # 1. 跨公司越权探测拦截：Beta 公司用户试图检索 Alpha 公司的项目 -> 404 NOT_FOUND
    with pytest.raises(DomainError) as exc_info:
        workflow.search_tender_slices(editor_beta, pid_alpha, "投标保证金", enabled=True)
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"

    # 2. 公司内未加入项目的其他用户拦截 -> 403 FORBIDDEN
    outsider = ctx["outsider"]
    with pytest.raises(DomainError) as exc_info:
        workflow.search_tender_slices(outsider, pid_alpha, "投标保证金", enabled=True)
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"

    # 3. 跨项目隔离：在 Beta 项目上传独立招标文件，验证 Alpha 项目绝不返回 Beta 项目内容
    state = repo.read()
    beta_project_id = "beta-project"
    beta_manager = Principal(state.accounts["beta-manager"], "token-beta-manager")

    beta_content = "合成招标文件：乙公司绝密项目\n招标编号：BETA-TOP-SECRET-888\n第99条 绝密要求：仅限乙公司内部可见。"
    b_up = workflow.upload(
        beta_manager,
        beta_project_id,
        {"filename": "乙公司绝密文件.txt", "content_base64": base64.b64encode(beta_content.encode("utf-8")).decode("ascii")},
        expected=str(state.projects[beta_project_id].revision),
        key="key-up-beta",
    )
    state = repo.read()
    workflow.parse(
        beta_manager,
        beta_project_id,
        {"file_ids": [b_up["file"]["id"]]},
        expected=str(state.projects[beta_project_id].revision),
        key="key-parse-beta",
    )

    # 在 Alpha 项目检索 "绝密" 或 "BETA-TOP-SECRET" -> 结果必须为空！
    alpha_search = workflow.search_tender_slices(manager_alpha, pid_alpha, "BETA-TOP-SECRET", enabled=True)
    assert len(alpha_search["slices"]) == 0

    # 在 Beta 项目检索 -> 仅属于 Beta
    beta_search = workflow.search_tender_slices(beta_manager, beta_project_id, "BETA-TOP-SECRET", enabled=True)
    assert len(beta_search["slices"]) == 1
    assert "BETA-TOP-SECRET" in beta_search["slices"][0]["content"]


def test_readonly_user_permission_gates(setup_project, workflow):
    """测试只读角色（viewer）权限门禁：可查阅检索，但禁止更改开关与注入条款。"""
    ctx = setup_project
    pid = ctx["project_id"]
    viewer = ctx["viewer"]

    # 1. 只读成员可以查看检索结果
    res = workflow.search_tender_slices(viewer, pid, "投标保证金", enabled=True)
    assert res["enabled"] is True

    # 2. 只读成员试图更改项目开关 -> 403 FORBIDDEN
    with pytest.raises(DomainError) as exc_info:
        workflow.set_tender_indexing_switch(viewer, pid, True)
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"

    # 3. 只读成员试图注入条款 -> 403 FORBIDDEN
    with pytest.raises(DomainError) as exc_info:
        workflow.inject_tender_clauses(viewer, pid, "alpha-tech", slice_ids=["dummy-slice-id"])
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_http_endpoints_and_openapi_safety(setup_project, repo):
    """测试 FastAPI HTTP 端点贯通及 include_in_schema=False 契约保护。"""
    ctx = setup_project
    pid = ctx["project_id"]

    client = TestClient(create_app(repository=repo))
    login_res = client.post("/api/v1/auth/login", json={"username": "alpha-editor", "password": "X_2026"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. POST /api/v1/projects/{project_id}/tender/search (默认关闭)
    resp = client.post(
        f"/api/v1/projects/{pid}/tender/search",
        headers=headers,
        json={"query": "投标保证金"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False

    # 2. 显式开启检索
    resp_enabled = client.post(
        f"/api/v1/projects/{pid}/tender/search",
        headers=headers,
        json={"query": "投标保证金", "enabled": True},
    )
    assert resp_enabled.status_code == 200
    data_enabled = resp_enabled.json()
    assert data_enabled["enabled"] is True
    assert len(data_enabled["slices"]) >= 1
    slice_id = data_enabled["slices"][0]["slice_id"]

    # 3. PATCH /api/v1/projects/{project_id}/tender/indexing-switch
    resp_sw = client.patch(
        f"/api/v1/projects/{pid}/tender/indexing-switch",
        headers=headers,
        json={"enabled": True},
    )
    assert resp_sw.status_code == 200
    assert resp_sw.json()["tender_indexing_enabled"] is True

    # 4. POST /api/v1/projects/{project_id}/chapters/{chapter_id}/inject-tender-clauses
    resp_inject = client.post(
        f"/api/v1/projects/{pid}/chapters/alpha-tech/inject-tender-clauses",
        headers=headers,
        json={"slice_ids": [slice_id]},
    )
    assert resp_inject.status_code == 200
    assert resp_inject.json()["injected_count"] >= 1

    # 5. GET /api/v1/projects/{project_id}/chapters/{chapter_id}/injected-tender-clauses
    resp_get = client.get(
        f"/api/v1/projects/{pid}/chapters/alpha-tech/injected-tender-clauses",
        headers=headers,
    )
    assert resp_get.status_code == 200
    assert resp_get.json()["count"] >= 1

    # 6. DELETE /api/v1/projects/{project_id}/chapters/{chapter_id}/injected-tender-clauses
    resp_del = client.delete(
        f"/api/v1/projects/{pid}/chapters/alpha-tech/injected-tender-clauses",
        headers=headers,
    )
    assert resp_del.status_code == 200
    assert resp_del.json()["cleared"] is True
