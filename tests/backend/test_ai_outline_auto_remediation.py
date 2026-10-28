# 为什么有这个文件：章节合规质检缺陷自动整改建议与局部智能重写引擎专属测试套件（PRD MVP v1.8 §5.7.8 & §5.10 / AI-OUTLINE-AUTO-REMEDIATION）。
# 它解决什么问题：
# 1. 自动诊断与针对性整改指引合成（Remediation Prompt Synthesis）：违规语句上下文捕获、修复 Prompt 与确定性替换；
# 2. R34 占位符与 AI 对话客套语清洗替换；
# 3. R37 偏离表述属于直接转人工的问题，系统不改写为“满足”（ISSUE-039，PRD v1.8 §5.7.4 第 4 条）；
# 4. R24 法定承诺/授权表单签字盖章瑕疵修复与规范落款槽位自动注入；
# 5. 本章依据外的证据编号只改为【待补：依据】并转人工，不替换为其他证据；
# 6. 局部针对性修正：仅修正可自动修正的段落，严格保护其他段落逐字不变；直接转人工的问题进入人工处理队列；
# 7. 停止条件按 §5.7.4 第 6 条判定（全部解决 / 剩余需人工 / 达到最大轮数 / 未减少 / 回退）；
# 8. 单章生成 start_chapter_generation(auto_remediate=True) 自动即时修复闭环；
# 9. 批量生成 schedule_batch_pipeline(auto_remediate=True) 批量自动整改与看板汇聚；
# 10. 涉密项目本地模型硬门禁（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）；
# 11. 多租户强隔离（404 NOT_FOUND）与 RBAC 只读角色门禁（403 FORBIDDEN）；
# 12. HTTP RESTful API POST /remediate-candidate 端点集成与零漂移。

from __future__ import annotations

import time
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg.domain.chapter_generation import (
    ChapterGenerationService,
    diagnose_paragraph_defects,
    extract_paragraph_citations,
    format_structured_chapter_content,
    parse_structured_paragraphs,
    remediate_chapter_candidate,
    sanitize_and_remediate_paragraph_text,
    synthesize_remediation_plan,
    validate_chapter_candidate,
)
from icg.domain.domain import Chapter, DemoService, DomainError, Principal, iso_time, new_id
from icg.domain.generation_context import writing_source_fingerprint
from icg.domain.ports import ModelProvider, ParserProvider
from icg.domain.workflow import WorkflowService
from icg.api.workflow import include_workflow_routes


class DummyParser(ParserProvider):
    def parse(self, filename: str, content: bytes) -> dict:
        return {"title": "测试文件", "pagination": "none", "pages": [], "warnings": []}


class MockLocalModelProvider(ModelProvider):
    name = "mock-local-qwen"
    is_real_model = True
    is_local = True

    def __init__(self, reply: str | None = None):
        self.reply = reply or (
            "### 1. 总体技术架构设计\n"
            "[P1] 本项目采用微服务与高可用架构[证:ev-iso9001]，严格遵循国家质量管理体系标准。\n\n"
            "### 2. 数据库主从高可用与双活保障\n"
            "[P2] 生产数据库采用主从同步与双活设计[片:rag-chunk-01]，保障系统平稳切换。"
        )
        self.calls = []

    def suggest(self, instruction: str, content: str) -> str:
        self.calls.append((instruction, content))
        return self.reply


class MockDefectiveModelProvider(ModelProvider):
    """模拟输出带有合规缺陷的生成结果的大模型。"""
    name = "mock-defective-model"
    is_real_model = True
    is_local = True

    def suggest(self, instruction: str, content: str) -> str:
        return (
            "### 1. 总体技术方案\n"
            "[P1] 本项目技术方案成熟，完全满足招标要求。\n\n"
            "### 2. 驻场运维与SLA服务\n"
            "[P2] 驻场运维响应方面，目前无法提供7x24小时支持，存在差距，【待定】。希望能帮到您！\n\n"
            "### 3. 企业资质与认证\n"
            "[P3] 我方具备先进管理体系认证[证:fake-invalid-999]，团队具备深厚经验。"
        )


class MockCloudModelProvider(ModelProvider):
    name = "mock-cloud-model"
    is_real_model = True
    is_local = False

    def suggest(self, instruction: str, content: str) -> str:
        return "云端大模型建议"


@pytest.fixture
def test_env():
    state = seed_state()
    project = state.projects["alpha-project"]
    project.deadline = "2026-12-31T17:00:00+08:00"
    project.sensitive = False

    state.chapters.clear()

    # 预置公司资料库已确认证据条目
    state.library["ev-iso9001"] = {
        "id": "ev-iso9001",
        "company_id": "alpha",
        "name": "ISO9001质量管理体系认证证书",
        "type": "qualification",
        "status": "confirmed",
        "revision": 2,
        "valid_until": "2027-06-30",
        "content": "甲公司通过ISO9001质量管理体系认证，证书编号QA-2024-9001。",
    }
    state.library["ev-cmmi5"] = {
        "id": "ev-cmmi5",
        "company_id": "alpha",
        "name": "CMMI-5软件成熟度认证",
        "type": "qualification",
        "status": "confirmed",
        "revision": 1,
        "valid_until": "2027-12-31",
        "content": "甲公司通过CMMI-5级成熟度评估。",
    }

    # 预置三章节
    ch1 = Chapter(
        id="ch-tech-arch",
        project_id=project.id,
        title="总体技术架构与方案设计",
        volume="technical",
        content="",
        revision=1,
    )
    ch2 = Chapter(
        id="ch-sla-service",
        project_id=project.id,
        title="系统SLA与售后服务保障承诺",
        volume="technical",
        content="",
        revision=1,
    )
    ch3 = Chapter(
        id="ch-legal-commitment",
        project_id=project.id,
        title="投标函及法定承诺声明书",
        volume="business",
        content="",
        revision=1,
    )
    for ch in [ch1, ch2, ch3]:
        state.chapters[ch.id] = ch

    state.project_teams[project.id] = {
        "owners": {
            "technical": "alpha-manager",
            "business": "alpha-manager",
        },
        "members": {
            "alpha-manager": {
                "user_id": "alpha-manager",
                "project_role": "lead",
                "volumes": ["technical", "business"],
            },
            "alpha-editor": {
                "user_id": "alpha-editor",
                "project_role": "writer",
                "volumes": ["technical", "business"],
            },
            "alpha-viewer": {
                "user_id": "alpha-viewer",
                "project_role": "viewer",
                "volumes": ["technical", "business"],
            },
            "alpha-auditor": {
                "user_id": "alpha-auditor",
                "project_role": "auditor",
                "volumes": ["technical", "business"],
            },
        },
    }

    # 预置工作流写作方案及已确认大纲
    wf = state.workflows.setdefault(project.id, {})
    wf["parse_confirmed"] = True
    wf["candidates"] = {}
    wp_chapters = wf.setdefault("writing_plan", {}).setdefault("chapters", {})
    reqs_map = wf.setdefault("requirements", {})

    req1 = {
        "id": "req-001",
        "chapter_id": ch1.id,
        "text": "投标人须具备ISO9001质量认证",
        "response": "完全满足要求",
        "evidence_ids": ["ev-iso9001"],
        "category": "technical",
        "status": "confirmed",
        "volume": ch1.volume,
        "source": None,
    }
    req2 = {
        "id": "req-002",
        "chapter_id": ch2.id,
        "text": "7x24小时驻场运维保障与服务响应SLA",
        "response": "提供 7x24 小时现场与远程支持",
        "evidence_ids": [],
        "category": "technical",
        "status": "confirmed",
        "volume": ch2.volume,
        "source": None,
    }
    req3 = {
        "id": "req-003",
        "chapter_id": ch3.id,
        "text": "法定代表人签署的投标函及授权书，盖单位公章",
        "response": "提交法定代表人签署盖章文件",
        "evidence_ids": [],
        "category": "technical",
        "status": "confirmed",
        "volume": ch3.volume,
        "source": None,
    }
    reqs_map[req1["id"]] = req1
    reqs_map[req2["id"]] = req2
    reqs_map[req3["id"]] = req3

    now_iso = iso_time(time.time())
    for ch, req_item in [(ch1, req1), (ch2, req2), (ch3, req3)]:
        plan_obj = {
            "chapter_id": ch.id,
            "title": ch.title,
            "volume": ch.volume,
            "writing_points": "1. 总体设计理念\n2. 关键实施细节\n3. 落地保障措施",
            "target_length": 1500,
            "confirmed_at": now_iso,
            "confirmed_by": "alpha-manager",
            "evidence": [state.library["ev-iso9001"]] if ch.id == ch1.id else [],
            "retrieved_evidence": [
                {
                    "chunk_id": "rag-chunk-01",
                    "content": "高可用双活数据中心部署与主从同步实施方案切片",
                }
            ],
            "facts": [
                {
                    "key": "项目经理",
                    "variable": "{{fact:项目经理}}",
                    "value": "张工（高级系统架构师）",
                }
            ],
        }
        wp_chapters[ch.id] = plan_obj
        plan_obj["confirmed_input_fingerprint"] = writing_source_fingerprint(state, project.id, ch.id)

    # 预置推荐顺序与大纲方案
    wf["recommended_writing_order"] = [
        {"chapter_id": ch1.id, "priority": "high", "priority_score": 85.0, "section_number": "1.1", "total_score": 15.0},
        {"chapter_id": ch2.id, "priority": "critical", "priority_score": 95.0, "section_number": "1.2", "total_score": 20.0},
        {"chapter_id": ch3.id, "priority": "high", "priority_score": 80.0, "section_number": "2.1", "total_score": 10.0},
    ]

    repo = MemoryRepository(state)
    demo_service = DemoService(repo, model_provider=MockLocalModelProvider())
    workflow_service = WorkflowService(demo_service, DummyParser())

    manager_user = state.accounts["alpha-manager"]
    viewer_user = state.accounts["alpha-viewer"]
    auditor_user = state.accounts["alpha-auditor"]
    beta_user = state.accounts["beta-editor"]

    manager_principal = Principal(manager_user, "token-alpha-manager")
    viewer_principal = Principal(viewer_user, "token-alpha-viewer")
    auditor_principal = Principal(auditor_user, "token-alpha-auditor")
    beta_principal = Principal(beta_user, "token-beta-editor")

    return {
        "state": state,
        "repo": repo,
        "project": project,
        "chapters": [ch1, ch2, ch3],
        "demo": demo_service,
        "workflow": workflow_service,
        "manager": manager_principal,
        "viewer": viewer_principal,
        "auditor": auditor_principal,
        "beta": beta_principal,
    }


def test_diagnose_paragraph_defects_and_synthesize_remediation_plan_r34(test_env):
    """测试 1：R34 占位符与 AI 对话客套残留语句的段落级诊断、整改 Prompt 合成与清洗。"""
    p_text = (
        "[P1] 针对数据库主从同步方案，具体实施参数为【待定】，整体部署架构为TODO。"
        "项目经理为【待补：项目经理】。希望能帮到您！祝您投标顺利！"
    )
    diag = diagnose_paragraph_defects(p_text)
    assert diag["has_blockers"] is True
    assert "【待定】" in diag["placeholders"]
    assert "TODO" in diag["placeholders"]
    assert "【待补：项目经理】" in diag["placeholders"]
    assert "希望能帮到您" in diag["ai_residuals"]
    assert "祝您投标顺利" in diag["ai_residuals"]

    facts = [{"key": "项目经理", "variable": "{{fact:项目经理}}", "value": "张工"}]
    cleaned = sanitize_and_remediate_paragraph_text(p_text, diag, facts=facts)

    # 验证客套语已彻底删除
    assert "希望能帮到您" not in cleaned
    assert "祝您投标顺利" not in cleaned
    # 有已确认事实的【待补】替换为事实变量
    assert "{{fact:项目经理}}" in cleaned
    assert "【待补：项目经理】" not in cleaned
    # 没有依据的占位符保留原样，不写成空泛承诺（不编造）
    assert "【待定】" in cleaned
    assert "TODO" in cleaned
    assert "已全面" not in cleaned and "已按招标规范" not in cleaned

    # 验证合成整改计划
    plan = synthesize_remediation_plan(
        content=p_text,
        facts=facts,
    )
    assert plan["has_defects"] is True
    assert plan["remediable_paragraphs_count"] == 1
    tp = plan["target_paragraphs"][0]
    assert any(d["rule_id"] == "R34" for d in tp["defects"])
    assert "【原段落内容】" in tp["remediation_prompt"]
    assert "【合规整改要求】" in tp["remediation_prompt"]


def test_diagnose_and_synthesize_remediation_plan_r37(test_env):
    """测试 2：R37 偏离表述诊断后保持原文，转人工核实，系统不翻转为“满足”。"""
    p_text = (
        "[P1] 关于投标人技术支持响应时效，我司目前无法提供7x24小时实时驻场，"
        "存在负偏离，与招标文件要求存在差距，指标不满足。"
    )
    diag = diagnose_paragraph_defects(p_text)
    assert diag["has_blockers"] is True
    assert "无法提供" in diag["negative_deviations"]
    assert "存在负偏离" in diag["negative_deviations"]
    assert "存在差距" in diag["negative_deviations"]
    assert "指标不满足" in diag["negative_deviations"]

    cleaned = sanitize_and_remediate_paragraph_text(p_text, diag)
    assert cleaned == p_text.strip()
    assert "完全满足" not in cleaned and "完全响应" not in cleaned

    plan = synthesize_remediation_plan(content=p_text)
    defect = next(d for d in plan["target_paragraphs"][0]["defects"] if d["rule_id"] == "R37")
    assert defect["route"] == "direct_human"
    assert "100%正向" not in plan["target_paragraphs"][0]["remediation_prompt"]

    # 偏离仍是阻断项，导出前必须由人处理
    val = validate_chapter_candidate(cleaned)
    assert any(b["rule_id"] == "R37" for b in val["detected_blockers"])


def test_diagnose_and_synthesize_remediation_plan_r24(test_env):
    """测试 3：R24 法定承诺章节签字盖章瑕疵标记自动替换与落款修复。"""
    p_text = "[P1] 投标人法定承诺书已编制完毕，当前版本为（未盖章）、(未签名)，待盖章。"
    diag = diagnose_paragraph_defects(p_text, is_statutory_form=True)
    assert diag["has_blockers"] is True
    assert "（未盖章）" in diag["missing_seals"]
    assert "(未签名)" in diag["missing_seals"]
    assert "待盖章" in diag["missing_seals"]

    cleaned = sanitize_and_remediate_paragraph_text(p_text, diag)
    assert "（未盖章）" not in cleaned
    assert "(未签名)" not in cleaned
    assert "待盖章" not in cleaned
    assert "【公章】" in cleaned or "【单位公章】" in cleaned
    assert "【法定代表人签字】" in cleaned


def test_diagnose_and_synthesize_remediation_plan_citation_auth(test_env):
    """测试 4：本章依据外的证据编号改为【待补：依据】，不替换为白名单里的其他证据。"""
    p_text = (
        "[P1] 本项目实施过程严格按照质量保证规范执行[证:fake-cert-001]，"
        "参考切片资料[片:unknown-snippet-99]。"
    )
    allowed_ev = {"ev-iso9001", "ev-cmmi5"}
    allowed_snip = {"rag-chunk-01"}

    diag = diagnose_paragraph_defects(
        p_text,
        allowed_evidence_ids=allowed_ev,
        allowed_snippet_ids=allowed_snip,
    )
    assert diag["has_blockers"] is True
    assert "fake-cert-001" in diag["fabricated_ev_ids"]
    assert "unknown-snippet-99" in diag["unverified_snip_ids"]

    cleaned = sanitize_and_remediate_paragraph_text(
        p_text,
        diag,
        allowed_evidence_ids=allowed_ev,
        allowed_snippet_ids=allowed_snip,
    )
    assert "fake-cert-001" not in cleaned
    assert "【待补：依据】" in cleaned
    assert "[证:ev-cmmi5]" not in cleaned and "[证:ev-iso9001]" not in cleaned
    assert "unknown-snippet-99" not in cleaned


def test_targeted_in_place_remediation_preserves_untouched_paragraphs(test_env):
    """测试 5：局部针对性重写核心机制 —— 仅重写违规段落，严格保持未违规段落不受影响。"""
    p1 = "### 1. 方案背景与设计原则\n[P1] 本项目整体设计遵循国家高可用标准，系统运行稳健，安全可控。"
    p2 = "### 2. 服务承诺保障机制\n[P2] 在7x24小时驻场方面，由于人力紧张存在差距，目前无法提供全天候响应，【待定】。希望能帮到您！"
    p3 = "### 3. 项目实施规划与里程碑\n[P3] 项目实施划分为四个阶段，各节点明确，保障按期推进。"
    p4 = "### 4. 体系认证与合规证明\n[P4] 我司具备特级资质证明[证:fake-fraud-999]，全面保障项目合规。"

    content = f"{p1}\n\n{p2}\n\n{p3}\n\n{p4}"

    service = ChapterGenerationService(test_env["demo"], repository=test_env["repo"])
    ch = test_env["chapters"][0]

    res = service.remediate_chapter_candidate(
        project_id=test_env["project"].id,
        chapter_id=ch.id,
        principal=test_env["manager"],
        content=content,
        max_rounds=3,
        auto_save=True,
    )

    # P2 的对话残留可自动删除；P2 的偏离与【待定】、P4 的依据外证据都直接转人工
    assert res["remediation_passed"] is False
    assert res["remediation_applied"] is True
    assert res["remediated_paragraphs_count"] == 1
    assert res["remediated_paragraph_indices"] == [1]
    assert res["loop_stop_reason"] == "NEED_HUMAN"
    reasons = {i["human_reason"] for i in res["human_issues"]}
    assert {"BUSINESS_DEVIATION", "MISSING_EVIDENCE", "EVIDENCE_CITATION"} <= reasons

    remediated_cand = res["candidate"]
    paras = remediated_cand["paragraphs"]
    assert len(paras) == 4

    # 核心金标准：未违规段落文字与标号完全未变
    assert "方案背景与设计原则" in paras[0]["subheading"]
    assert "遵循国家高可用标准" in paras[0]["content"]
    assert "项目实施规划与里程碑" in paras[2]["subheading"]
    assert "项目实施划分为四个阶段" in paras[2]["content"]

    # 可自动修正的部分已修正；直接转人工的内容原样保留，自动修正从不改动它们
    assert "希望能帮到您" not in paras[1]["content"]
    assert "无法提供" in paras[1]["content"]
    assert "【待定】" in paras[1]["content"]
    assert "[证:fake-fraud-999]" in paras[3]["content"]
    assert "完全满足" not in remediated_cand["content"]

    # 人工处理队列已登记本节问题，章节停在“待人工处理”
    queue = test_env["repo"].read().workflows[test_env["project"].id]["human_queue"]
    assert queue["loops"][ch.id]["status"] == "pending_human"
    assert queue["loops"][ch.id]["stop_reason"] == "NEED_HUMAN"
    pending = [i for i in queue["issues"].values() if i["chapter_id"] == ch.id and i["status"] == "pending_human"]
    assert len(pending) == len(res["human_issues"])


def test_multi_round_remediation_convergence(test_env):
    """测试 6：多轮整改收敛机制与前置/后置健康评分与历史记录。"""
    content = (
        "### 1. 运维与应急体系\n"
        "[P1] 现场响应方面无法提供常驻运维，存在负偏离，【待补】。希望能帮到您！\n\n"
        "### 2. 团队持证说明\n"
        "[P2] 项目团队持证齐全[证:fake-cert-888]，待完善。"
    )
    service = ChapterGenerationService(test_env["demo"], repository=test_env["repo"])
    ch = test_env["chapters"][1]

    res = service.remediate_chapter_candidate(
        project_id=test_env["project"].id,
        chapter_id=ch.id,
        principal=test_env["manager"],
        content=content,
        max_rounds=3,
    )

    assert res["remediation_passed"] is False
    assert res["pre_remediation_score"] < 50
    assert res["pre_remediation_rating"] in ("critical", "warning")
    assert len(res["remediation_history"]) >= 1
    assert "希望能帮到您" not in res["candidate"]["content"]
    assert "【待补】" in res["candidate"]["content"]

    # 仓储已落盘保存最新 candidate 与循环记录
    saved = test_env["repo"].read().workflows[test_env["project"].id]
    assert saved["candidates"][ch.id]["remediation_applied"] is True
    assert saved["human_queue"]["loops"][ch.id]["loop_no"] == 1


def test_auto_fixable_defects_converge_to_all_resolved(test_env):
    """测试 6b：只有可自动修正的问题时，循环以“问题全部解决”停止，章节为已完成。"""
    content = "[P1] 本项目由【待补：项目经理】负责现场组织。希望能帮到您！"
    service = ChapterGenerationService(test_env["demo"], repository=test_env["repo"])
    ch = test_env["chapters"][1]
    res = service.remediate_chapter_candidate(
        project_id=test_env["project"].id, chapter_id=ch.id, principal=test_env["manager"], content=content,
    )
    assert res["remediation_passed"] is True
    assert res["loop_stop_reason"] == "ALL_RESOLVED"
    assert "{{fact:项目经理}}" in res["candidate"]["content"]
    loop = test_env["repo"].read().workflows[test_env["project"].id]["human_queue"]["loops"][ch.id]
    assert loop["status"] == "completed"


def test_statutory_form_whole_chapter_seal_block_injection(test_env):
    """测试 7：法定承诺表单章节缺失落款时自动注入规范公章及签字槽位。"""
    statutory_content = (
        "### 1. 投标声明\n"
        "[P1] 我方郑重声明，本投标文件中所提交的所有资质文件与响应材料均真实、合法、有效。"
    )
    service = ChapterGenerationService(test_env["demo"], repository=test_env["repo"])
    ch3 = test_env["chapters"][2]  # "投标函及法定承诺声明书"

    # 初始核验必然报 R24 MANDATORY_SEAL_SIGNATURE_MISSING
    init_val = validate_chapter_candidate(statutory_content, chapter=ch3)
    assert any(b["code"] == "MANDATORY_SEAL_SIGNATURE_MISSING" for b in init_val["detected_blockers"])

    res = service.remediate_chapter_candidate(
        project_id=test_env["project"].id,
        chapter_id=ch3.id,
        principal=test_env["manager"],
        content=statutory_content,
    )

    assert res["remediation_passed"] is True
    rem_content = res["candidate"]["content"]
    assert "【法定代表人签字】" in rem_content
    assert "【公章】" in rem_content
    assert res["post_remediation_score"] == 100


def test_auto_remediate_flag_in_start_chapter_generation(test_env):
    """测试 8：单章生成 start_chapter_generation(auto_remediate=True) 自动即时质检整改闭环。"""
    defective_provider = MockDefectiveModelProvider()
    service = ChapterGenerationService(test_env["demo"], repository=test_env["repo"])
    ch = test_env["chapters"][0]

    # 替换模型提供商为输出有缺陷的模型
    test_env["demo"].resolve_model_provider = lambda st, pid: defective_provider

    # 不开启 auto_remediate 时，生成的 candidate 必然验证失败
    res_no_rem = service.start_chapter_generation(
        project_id=test_env["project"].id,
        chapter_id=ch.id,
        principal=test_env["manager"],
        sync_execute=True,
        auto_remediate=False,
    )
    assert res_no_rem["validation_passed"] is False
    assert res_no_rem["remediation_applied"] is False

    # 开启 auto_remediate=True，生成的 candidate 自动完成整改
    res_rem = service.start_chapter_generation(
        project_id=test_env["project"].id,
        chapter_id=ch.id,
        principal=test_env["manager"],
        sync_execute=True,
        auto_remediate=True,
    )
    # 对话残留被自动删除，偏离、【待定】和依据外证据保留给人工处理，不能以“已通过”冒充
    assert res_rem["remediation_applied"] is True
    assert res_rem["validation_passed"] is False
    assert res_rem["remediated_paragraphs_count"] >= 1
    codes = {b["code"] for b in res_rem["detected_blockers"]}
    assert "NEGATIVE_DEVIATION_DETECTED" in codes
    assert "AI_CONVERSATION_RESIDUAL" not in codes
    queue = test_env["repo"].read().workflows[test_env["project"].id]["human_queue"]
    assert queue["loops"][ch.id]["status"] == "pending_human"


def test_auto_remediate_in_schedule_batch_pipeline(test_env):
    """测试 9：批量流水线 schedule_batch_pipeline(auto_remediate=True) 自动批量整改闭环与看板。"""
    defective_provider = MockDefectiveModelProvider()
    test_env["demo"].resolve_model_provider = lambda st, pid: defective_provider

    service = ChapterGenerationService(test_env["demo"], repository=test_env["repo"])

    res = service.schedule_batch_pipeline(
        project_id=test_env["project"].id,
        principal=test_env["manager"],
        concurrency_limit=2,
        sync_execute=True,
        auto_remediate=True,
    )

    assert res["pipeline_status"] in ("completed", "partial_completed")
    summary = res["validation_summary"]
    # 模型输出带偏离和依据外证据：自动整改只删除对话残留，三章都如实停在待人工
    assert summary["total_validation_passed"] == 0
    assert summary["total_validation_failed"] == 3
    assert summary["total_detected_blockers"] > 0
    assert summary["total_remediated_chapters"] == 3

    first_batch = res["batches"][0]
    for ch_meta in first_batch["chapters_metadata"]:
        assert ch_meta["remediation_applied"] is True
        assert ch_meta["validation_passed"] is False


def test_sensitive_project_airgap_model_gate_on_remediation(test_env):
    """测试 10：涉密项目内网物理隔离红线（Airgap Boundary）—— 严禁调用公网/云端模型整改。"""
    cloud_provider = MockCloudModelProvider()
    test_env["demo"].resolve_model_provider = lambda st, pid: cloud_provider

    # 将项目置为涉密
    def mark_sensitive(st):
        st.projects[test_env["project"].id].sensitive = True

    test_env["repo"].transaction(mark_sensitive)

    service = ChapterGenerationService(test_env["demo"], repository=test_env["repo"])
    ch = test_env["chapters"][0]

    with pytest.raises(DomainError) as exc_info:
        service.remediate_chapter_candidate(
            project_id=test_env["project"].id,
            chapter_id=ch.id,
            principal=test_env["manager"],
            content="[P1] 测试内容【待定】",
        )

    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"


def test_multi_tenant_and_rbac_isolation_on_remediation(test_env):
    """测试 11：多租户防嗅探隔离（404）与 RBAC 只读角色权限门禁（403）。"""
    service = ChapterGenerationService(test_env["demo"], repository=test_env["repo"])
    ch = test_env["chapters"][0]

    # 1. 跨公司用户访问 -> 404 NOT_FOUND
    with pytest.raises(DomainError) as exc_404:
        service.remediate_chapter_candidate(
            project_id=test_env["project"].id,
            chapter_id=ch.id,
            principal=test_env["beta"],
            content="[P1] 跨公司内容",
        )
    assert exc_404.value.status == 404
    assert exc_404.value.code == "NOT_FOUND"

    # 2. 同公司只读角色（viewer / auditor） -> 403 FORBIDDEN
    with pytest.raises(DomainError) as exc_viewer:
        service.remediate_chapter_candidate(
            project_id=test_env["project"].id,
            chapter_id=ch.id,
            principal=test_env["viewer"],
            content="[P1] 只读内容",
        )
    assert exc_viewer.value.status == 403
    assert exc_viewer.value.code == "FORBIDDEN"

    with pytest.raises(DomainError) as exc_auditor:
        service.remediate_chapter_candidate(
            project_id=test_env["project"].id,
            chapter_id=ch.id,
            principal=test_env["auditor"],
            content="[P1] 审计只读内容",
        )
    assert exc_auditor.value.status == 403
    assert exc_auditor.value.code == "FORBIDDEN"


def test_http_api_remediate_candidate_endpoint(test_env):
    """测试 12：HTTP RESTful API POST /remediate-candidate 端点全契约连通测试。"""
    app = FastAPI()

    @app.exception_handler(DomainError)
    async def domain_error_handler(request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status,
            content={
                "code": exc.code,
                "message": exc.message,
                "type": f"https://api.icg.example.com/errors/{exc.code.lower()}",
                "title": exc.code,
                "status": exc.status,
                "detail": exc.message,
            },
        )

    def current_user():
        return test_env["manager"]

    include_workflow_routes(app, test_env["workflow"], current_user, DummyParser())
    client = TestClient(app)

    pid = test_env["project"].id
    cid = test_env["chapters"][0].id

    # 正常调用整改接口
    payload = {
        "content": "[P1] 总体设计方案【待定】。无法提供驻场运维。希望能帮到您！",
        "max_rounds": 3,
        "auto_save": True,
    }
    resp = client.post(f"/api/v1/projects/{pid}/chapters/{cid}/remediate-candidate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["remediation_passed"] is False
    assert data["remediation_applied"] is True
    assert data["remediated_paragraphs_count"] == 1
    assert "candidate" in data
    assert "validation_report" in data
    assert "希望能帮到您" not in data["candidate"]["content"]
    assert "无法提供" in data["candidate"]["content"]
    assert data["loop_stop_reason"] == "NEED_HUMAN"
