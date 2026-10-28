# 为什么有这个文件：章节生成产物合规性自动即时质检门禁测试套件（PRD MVP v1.8 §5.7.8 & §5.10 / AI-CHAPTER-AUTO-VALIDATION-GATE）。
# 它解决什么问题：
# 1. 生成即质检（Validation on Generation）：核验在单章节或批量生成时自动触发即时合规质量检查；
# 2. R34 占位符与“待补/待完善”残留字样排查（【待定】、【待补】、TODO、XXXX 及 AI 对话客套残留）；
# 3. R37 / R28 负偏离与不满足排查（不满足、负偏离、无法提供、存在差距等实质性违规表述）；
# 4. R24 签字盖章槽位合规排查（法定承诺与授权章节缺少签字盖章槽位或包含未盖公章标记）；
# 5. CITATION_AUTH 引用白名单真实性核验（排查虚构未登记证据编号 [证:xxx] 与未匹配切片 [片:xxx]）；
# 6. 质量健康度评分（quality_health_score: 0~100）与评级（excellent / good / warning / critical）梯度；
# 7. 候选草稿 candidate 元数据与 demo_job 进度注入；
# 8. 批量流水线 schedule_batch_pipeline 质量看板与汇聚统计（validation_summary）；
# 9. 多租户强隔离（跨公司 404 NOT_FOUND）与 RBAC 只读角色门禁（403 FORBIDDEN）；
# 10. 涉密项目本地模型硬门禁（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）；
# 11. HTTP API 端点集成（POST /api/v1/projects/{project_id}/chapters/{chapter_id}/validate-candidate）。

from __future__ import annotations

import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg.domain.chapter_generation import (
    ChapterGenerationService,
    extract_paragraph_citations,
    format_structured_chapter_content,
    parse_structured_paragraphs,
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
            "[P2] 生产数据库采用主从同步与双活设计[片:rag-chunk-01]，保障系统平稳切换。\n\n"
            "### 3. 应急响应机制\n"
            "[P3] 建立 7x24 小时应急运维体系，保障平台全天候高可用性。"
        )
        self.calls = []

    def suggest(self, instruction: str, content: str) -> str:
        self.calls.append((instruction, content))
        return self.reply


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

    # 预置项目工作流与招标文件条款
    wf = {
        "parse_confirmed": True,
        "files": {
            "file-tender-01": {
                "file_id": "file-tender-01",
                "filename": "招标技术规范书.pdf",
                "sha256": "sha-dummy-1234",
                "status": "parsed",
                "pagination": "page",
                "pages": [
                    "第一页：招标基本要求与架构设计。",
                    "第二页：技术指标要求与法定承诺书。",
                ],
            }
        },
        "requirements": {
            "req-arch": {
                "id": "req-arch",
                "volume": "technical",
                "chapter_id": "ch-tech-01",
                "text": "系统必须提供微服务与高可用架构方案",
                "importance": "star",
                "category": "technical",
                "score": 15.0,
                "status": "confirmed",
                "response": "提供微服务与高可用双活方案",
                "evidence_ids": ["ev-iso9001"],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "系统必须提供微服务与高可用架构方案",
                },
            },
            "req-letter": {
                "id": "req-letter",
                "volume": "business",
                "chapter_id": "ch-letter-01",
                "text": "投标人必须签署并加盖公章提交法定代表人授权委托书与服务承诺函",
                "importance": "star",
                "category": "commitment",
                "score": 10.0,
                "status": "confirmed",
                "response": "完全承诺并加盖公章签署",
                "evidence_ids": ["ev-cmmi5"],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 2,
                    "quote": "法定代表人授权委托书与服务承诺函",
                },
            },
        },
        "writing_plan": {
            "confirmed_at": "2026-10-25T10:00:00+08:00",
            "chapters": {},
        },
        "candidates": {},
    }

    # 预置 2 个测试章节
    ch_tech = Chapter(
        id="ch-tech-01",
        project_id="alpha-project",
        volume="technical",
        title="1.1 总体架构与微服务高可用方案",
        revision=1,
        content="待生成内容",
    )
    ch_letter = Chapter(
        id="ch-letter-01",
        project_id="alpha-project",
        volume="business",
        title="2.1 法定代表人授权委托书与服务承诺函",
        revision=1,
        content="待生成内容",
    )
    state.chapters["ch-tech-01"] = ch_tech
    state.chapters["ch-letter-01"] = ch_letter

    state.workflows["alpha-project"] = wf

    # 配置章节写作计划并打上指纹
    now_ts = time.time()
    now_iso = iso_time(now_ts)

    for cid, ch in [("ch-tech-01", ch_tech), ("ch-letter-01", ch_letter)]:
        ev_id = "ev-iso9001" if cid == "ch-tech-01" else "ev-cmmi5"
        plan_obj = {
            "chapter_id": cid,
            "title": ch.title,
            "volume": ch.volume,
            "writing_points": "1. 总体设计规范\n2. 详细技术实现\n3. 应急运维保障",
            "target_length": 800,
            "confirmed_at": now_iso,
            "evidence": [state.library[ev_id]],
            "retrieved_evidence": [
                {
                    "tag": "[片]",
                    "chunk_id": "rag-chunk-01",
                    "id": "rag-chunk-01",
                    "document_id": "doc-cloud-01",
                    "content": "高可用双活数据库方案切片内容",
                }
            ],
            "requirements": [wf["requirements"]["req-arch"] if cid == "ch-tech-01" else wf["requirements"]["req-letter"]],
        }
        wf["writing_plan"]["chapters"][cid] = plan_obj
        plan_obj["confirmed_input_fingerprint"] = writing_source_fingerprint(state, "alpha-project", cid)

    # 设置分册负责人与团队
    state.project_teams["alpha-project"] = {
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
        },
    }

    repo = MemoryRepository(state)
    demo = DemoService(
        repo,
        model_provider=MockLocalModelProvider(),
    )
    workflow_svc = WorkflowService(demo, DummyParser())
    demo.workflow = workflow_svc
    gen_service = ChapterGenerationService(demo, repository=repo)

    leader = Principal(
        user=state.accounts["alpha-manager"],
        session_token="tok-alpha-manager",
    )
    viewer = Principal(
        user=state.accounts["alpha-viewer"],
        session_token="tok-alpha-viewer",
    )
    auditor = Principal(
        user=state.accounts["alpha-auditor"],
        session_token="tok-alpha-auditor",
    )
    beta_user = Principal(
        user=state.accounts["beta-editor"],
        session_token="tok-beta-editor",
    )

    return {
        "state": state,
        "repo": repo,
        "demo": demo,
        "gen_service": gen_service,
        "workflow_svc": workflow_svc,
        "leader": leader,
        "viewer": viewer,
        "auditor": auditor,
        "beta_user": beta_user,
        "project": project,
        "ch_tech": ch_tech,
        "ch_letter": ch_letter,
    }


def test_clean_generated_chapter_passes_validation(test_env):
    """测试 1：清洁、无占位符、无负偏离且引用合法的生成产物 100% 通过即时质检。"""
    content = (
        "### 1. 总体架构规范\n"
        "[P1] 本项目严格遵循国家信息安全等级保护标准，采用微服务分布式集群架构[证:ev-iso9001]，保障平台高并发吞吐。\n\n"
        "### 2. 数据库高可用双活\n"
        "[P2] 生产数据库采用主从同步与双活设计[片:rag-chunk-01]，实现零数据丢失与故障秒级自愈。\n\n"
        "### 3. 运维应急体系\n"
        "[P3] 建立 7x24 小时应急运维监控体系，全天候保障业务稳定运行。"
    )
    allowed_ev = {"ev-iso9001"}
    allowed_snip = {"rag-chunk-01"}

    res = validate_chapter_candidate(
        content=content,
        chapter=test_env["ch_tech"],
        allowed_evidence_ids=allowed_ev,
        allowed_snippet_ids=allowed_snip,
    )

    assert res["validation_passed"] is True
    assert res["validation_failed"] is False
    assert res["quality_health_score"] == 100
    assert res["quality_health_rating"] == "excellent"
    assert len(res["detected_blockers"]) == 0
    assert len(res["detected_warnings"]) == 0
    assert any("通过" in s for s in res["remediation_suggestions"])


def test_r34_placeholder_residuals_trigger_blocker(test_env):
    """测试 2：R34 占位符（【待定】、【待补】、TODO、XXXX）与 AI 对话残留字样阻断拦截。"""
    # 场景 A：占位符与未填充标记
    content_with_placeholders = (
        "### 1. 总体架构规范\n"
        "[P1] 系统设计方案【待补：补充核心微服务组件】，计划支持高并发业务。\n\n"
        "### 2. 参数指标\n"
        "[P2] 系统吞吐量指标为 XXXX TPS，容灾恢复时间 TODO 待定 [证:ev-iso9001]。"
    )
    res_a = validate_chapter_candidate(
        content=content_with_placeholders,
        chapter=test_env["ch_tech"],
        allowed_evidence_ids={"ev-iso9001"},
    )
    assert res_a["validation_passed"] is False
    assert res_a["validation_failed"] is True
    assert any(b["code"] == "PLACEHOLDER_RESIDUAL" for b in res_a["detected_blockers"])
    assert any("占位符" in s for s in res_a["remediation_suggestions"])

    # 场景 B：AI 对话客套语句残留
    content_with_ai_residual = (
        "希望能帮到您！以下是为您生成的章节方案：\n"
        "### 1. 总体架构规范\n"
        "[P1] 本项目采用微服务架构[证:ev-iso9001]。\n"
        "作为AI大模型，如果您还有其他需要补充，请随时告知，祝您投标顺利！"
    )
    res_b = validate_chapter_candidate(
        content=content_with_ai_residual,
        chapter=test_env["ch_tech"],
        allowed_evidence_ids={"ev-iso9001"},
    )
    assert res_b["validation_passed"] is False
    assert res_b["validation_failed"] is True
    assert any(b["code"] == "AI_CONVERSATION_RESIDUAL" for b in res_b["detected_blockers"])
    assert any("AI对话" in s or "客套" in s for s in res_b["remediation_suggestions"])


def test_r37_negative_deviation_triggers_blocker(test_env):
    """测试 3：R37 / R28 负偏离与不满足排查阻断（负偏离、无法满足、存在差距等）。"""
    content = (
        "### 1. 总体架构规范\n"
        "[P1] 由于当前技术平台限制，本系统在微服务灰度发布方面存在负偏离，无法提供毫秒级发布[证:ev-iso9001]。\n\n"
        "### 2. 指标响应\n"
        "[P2] 部分高可用指标不满足招标文件严苛要求，存在一定技术差距。"
    )
    res = validate_chapter_candidate(
        content=content,
        chapter=test_env["ch_tech"],
        allowed_evidence_ids={"ev-iso9001"},
    )
    assert res["validation_passed"] is False
    assert res["validation_failed"] is True
    assert any(b["code"] == "NEGATIVE_DEVIATION_DETECTED" for b in res["detected_blockers"])
    assert any("负偏离" in s for s in res["remediation_suggestions"])


def test_r24_statutory_form_seal_signature_missing(test_env):
    """测试 4：R24 签字盖章槽位合规排查（法定承诺章节缺少公章/签字或存在未盖公章标记）。"""
    # 场景 A：法定承诺书包含显式“未盖公章”
    content_missing_seal = (
        "### 法定代表人授权委托书\n"
        "本人作为法定代表人，特授权张三负责本项目投标事宜。\n"
        "投标人（未盖章）：甲公司\n"
        "法定代表人：未签字"
    )
    res_a = validate_chapter_candidate(
        content=content_missing_seal,
        chapter=test_env["ch_letter"],
        allowed_evidence_ids={"ev-cmmi5"},
    )
    assert res_a["validation_passed"] is False
    assert res_a["validation_failed"] is True
    assert any(b["code"] == "MANDATORY_SEAL_SIGNATURE_MISSING" for b in res_a["detected_blockers"])

    # 场景 B：法定承诺章节正文正规，但缺少标准签字盖章槽位
    content_no_markers = (
        "### 法定代表人授权委托书\n"
        "本人作为法定代表人，特授权张三负责本项目投标事宜。\n"
        "投标人：甲公司，特此声明。"
    )
    res_b = validate_chapter_candidate(
        content=content_no_markers,
        chapter=test_env["ch_letter"],
        allowed_evidence_ids={"ev-cmmi5"},
    )
    assert res_b["validation_passed"] is False
    assert any(b["code"] == "MANDATORY_SEAL_SIGNATURE_MISSING" for b in res_b["detected_blockers"])

    # 场景 C：合规携带标准【公章】与【法定代表人签字】
    content_valid_seal = (
        "### 法定代表人授权委托书\n"
        "本人作为法定代表人，特授权张三负责本项目投标事宜。\n"
        "投标人：甲公司【公章】\n"
        "法定代表人：李四【法定代表人签字】\n"
        "日期：2026年10月28日"
    )
    res_c = validate_chapter_candidate(
        content=content_valid_seal,
        chapter=test_env["ch_letter"],
        allowed_evidence_ids={"ev-cmmi5"},
    )
    assert not any(b["code"] == "MANDATORY_SEAL_SIGNATURE_MISSING" for b in res_c["detected_blockers"])


def test_citation_auth_fabricated_evidence_and_unverified_snippet(test_env):
    """测试 5：CITATION_AUTH 证据白名单核验（虚构证据阻断，未知切片告警）。"""
    # 虚构未登记证据编号
    content_fake_ev = (
        "### 1. 资质实力\n"
        "[P1] 本公司具备国家最高安全等级资质证书[证:fake-cert-unregistered-999]，真实有效。"
    )
    res_ev = validate_chapter_candidate(
        content=content_fake_ev,
        chapter=test_env["ch_tech"],
        allowed_evidence_ids={"ev-iso9001"},
    )
    assert res_ev["validation_passed"] is False
    assert any(b["code"] == "FABRICATED_OR_INVALID_EVIDENCE_CITATION" for b in res_ev["detected_blockers"])
    assert any("虚构证据" in s for s in res_ev["remediation_suggestions"])

    # 未登记在当前知识库候选切片中的切片 -> 告警 warning，不阻断 passed
    content_unverified_snip = (
        "### 1. 架构参考\n"
        "[P1] 参考外部知识库经验[片:unverified-rag-chunk-888]，采用分库分表[证:ev-iso9001]。"
    )
    res_snip = validate_chapter_candidate(
        content=content_unverified_snip,
        chapter=test_env["ch_tech"],
        allowed_evidence_ids={"ev-iso9001"},
        allowed_snippet_ids={"rag-chunk-01"},
    )
    assert res_snip["validation_passed"] is True
    assert res_snip["validation_failed"] is False
    assert any(w["code"] == "UNVERIFIED_SNIPPET_CITATION" for w in res_snip["detected_warnings"])


def test_quality_health_score_and_rating_gradation(test_env):
    """测试 6：质量健康度评分（0~100）与评级（excellent / good / warning / critical）梯度核验。"""
    # 1. 完美无瑕疵：100分，excellent
    clean_text = "### 1. 规范\n[P1] 系统设计完全满足要求[证:ev-iso9001]。"
    r1 = validate_chapter_candidate(clean_text, chapter=test_env["ch_tech"], allowed_evidence_ids={"ev-iso9001"}, allowed_snippet_ids={"s1"})
    assert r1["quality_health_score"] == 100
    assert r1["quality_health_rating"] == "excellent"
    assert r1["validation_passed"] is True

    # 2. 只有 1 个告警（未知切片）：90分，excellent
    warn1_text = "### 1. 规范\n[P1] 系统设计[片:unknown-1][证:ev-iso9001]。"
    r2 = validate_chapter_candidate(warn1_text, chapter=test_env["ch_tech"], allowed_evidence_ids={"ev-iso9001"}, allowed_snippet_ids={"s1"})
    assert r2["quality_health_score"] == 90
    assert r2["quality_health_rating"] == "excellent"
    assert r2["validation_passed"] is True

    # 3. 2 个告警（2 个未知切片）：80分，good
    warn2_text = "### 1. 规范\n[P1] 系统[片:unknown-1]架构[片:unknown-2][证:ev-iso9001]。"
    r3 = validate_chapter_candidate(warn2_text, chapter=test_env["ch_tech"], allowed_evidence_ids={"ev-iso9001"}, allowed_snippet_ids={"s1"})
    assert r3["quality_health_score"] == 80
    assert r3["quality_health_rating"] == "good"
    assert r3["validation_passed"] is True

    # 4. 1 个阻断（单占位符）：55分，warning，passed 为 False
    block1_text = "### 1. 规范\n[P1] 系统设计【待补】核心逻辑[证:ev-iso9001]。"
    r4 = validate_chapter_candidate(block1_text, chapter=test_env["ch_tech"], allowed_evidence_ids={"ev-iso9001"})
    assert r4["validation_passed"] is False
    assert r4["validation_failed"] is True
    assert r4["quality_health_score"] == 55
    assert r4["quality_health_rating"] == "warning"

    # 5. 2 个以上阻断（占位符 + 负偏离）：<= 35分，critical
    block2_text = "### 1. 规范\n[P1] 系统设计【待补】关键参数，且无法满足指标要求[证:ev-iso9001]。"
    r5 = validate_chapter_candidate(block2_text, chapter=test_env["ch_tech"], allowed_evidence_ids={"ev-iso9001"})
    assert r5["validation_passed"] is False
    assert r5["validation_failed"] is True
    assert r5["quality_health_score"] <= 35
    assert r5["quality_health_rating"] == "critical"


def test_start_chapter_generation_integrates_validation(test_env):
    """测试 7：单章生成 start_chapter_generation 自动即时质检并写入 candidate 与 job 结果。"""
    gen_svc = test_env["gen_service"]
    res = gen_svc.start_chapter_generation(
        project_id="alpha-project",
        chapter_id="ch-tech-01",
        principal=test_env["leader"],
        sync_execute=True,
    )

    # 返回字典包含即时质检字段
    assert "validation_passed" in res
    assert "quality_health_score" in res
    assert "quality_health_rating" in res
    assert "detected_blockers" in res
    assert "detected_warnings" in res
    assert "remediation_suggestions" in res
    assert "validation_report" in res

    # 检查持久化 candidate 元数据
    cand = res["candidate"]
    assert cand is not None
    assert cand["validation_passed"] is True
    assert cand["quality_health_score"] == 100
    assert cand["quality_health_rating"] == "excellent"
    assert cand["detected_blockers"] == []

    # 检查 demo_job 进度中的 result_json
    job = res["job"]
    rj = job.get("result_json", {})
    assert rj.get("validation_passed") is True
    assert rj.get("quality_health_rating") == "excellent"
    assert rj.get("blocker_count") == 0


def test_batch_pipeline_aggregates_validation_summary(test_env):
    """测试 8：批量流水线 schedule_batch_pipeline 自动聚合质量门禁仪表盘看板。"""
    gen_svc = test_env["gen_service"]
    pipe_res = gen_svc.schedule_batch_pipeline(
        project_id="alpha-project",
        principal=test_env["leader"],
        chapter_ids=["ch-tech-01"],
        concurrency_limit=2,
        sync_execute=True,
    )

    # 批次元数据包含即时质检结果
    batch_meta = pipe_res["batches"][0]["chapters_metadata"][0]
    assert batch_meta["validation_passed"] is True
    assert batch_meta["quality_health_rating"] == "excellent"
    assert batch_meta["blocker_count"] == 0

    # 看板全局聚合统计
    summary = pipe_res["validation_summary"]
    assert summary["total_validation_passed"] == 1
    assert summary["total_validation_failed"] == 0
    assert summary["total_detected_blockers"] == 0
    assert summary["average_quality_score"] == 100.0

    # 工作流持久化记录同步具备 validation_summary
    wf = test_env["repo"].read().workflows["alpha-project"]
    latest_run = wf["latest_batch_pipeline_run"]
    assert "validation_summary" in latest_run
    assert latest_run["validation_summary"]["total_validation_passed"] == 1


def test_service_validate_chapter_content_on_demand(test_env):
    """测试 9：按需即时合规质检 validate_chapter_content 独立调用。"""
    gen_svc = test_env["gen_service"]

    # 传入含有缺陷的正文
    dirty_content = "### 1. 架构设计\n[P1] 系统参数【待确认】，暂无法满足毫秒级同步。"
    res_dirty = gen_svc.validate_chapter_content(
        project_id="alpha-project",
        chapter_id="ch-tech-01",
        principal=test_env["leader"],
        content=dirty_content,
    )
    assert res_dirty["validation_passed"] is False
    assert res_dirty["quality_health_rating"] in ("warning", "critical")
    assert len(res_dirty["detected_blockers"]) >= 2

    # 传入清洁正文
    clean_content = "### 1. 架构设计\n[P1] 系统设计完全遵循技术规范[证:ev-iso9001]。"
    res_clean = gen_svc.validate_chapter_content(
        project_id="alpha-project",
        chapter_id="ch-tech-01",
        principal=test_env["leader"],
        content=clean_content,
    )
    assert res_clean["validation_passed"] is True
    assert res_clean["quality_health_score"] == 100


def test_multitenant_isolation_and_rbac_gates(test_env):
    """测试 10：多租户物理强隔离（404）与只读系统角色门禁（403）。"""
    gen_svc = test_env["gen_service"]

    # 跨企业非法访问 -> 404 NOT_FOUND
    with pytest.raises(DomainError) as exc_404:
        gen_svc.validate_chapter_content(
            project_id="alpha-project",
            chapter_id="ch-tech-01",
            principal=test_env["beta_user"],
        )
    assert exc_404.value.status == 404
    assert exc_404.value.code == "NOT_FOUND"

    # 只读审计角色调用 -> 403 FORBIDDEN
    with pytest.raises(DomainError) as exc_403:
        gen_svc.validate_chapter_content(
            project_id="alpha-project",
            chapter_id="ch-tech-01",
            principal=test_env["auditor"],
        )
    assert exc_403.value.status == 403
    assert exc_403.value.code == "FORBIDDEN"


def test_sensitive_project_local_model_gate(test_env):
    """测试 11：涉密项目本地模型硬门禁（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）。"""
    def set_sensitive(st):
        st.projects["alpha-project"].sensitive = True
        wf = st.workflows["alpha-project"]
        for cid in ["ch-tech-01", "ch-letter-01"]:
            wf["writing_plan"]["chapters"][cid]["confirmed_input_fingerprint"] = writing_source_fingerprint(
                st, "alpha-project", cid
            )
    test_env["repo"].transaction(set_sensitive)

    # 绑定云端大模型服务
    cloud_demo = DemoService(
        test_env["repo"],
        model_provider=MockCloudModelProvider(),
    )
    cloud_gen = ChapterGenerationService(cloud_demo, repository=test_env["repo"])

    with pytest.raises(DomainError) as exc:
        cloud_gen.start_chapter_generation(
            project_id="alpha-project",
            chapter_id="ch-tech-01",
            principal=test_env["leader"],
            sync_execute=True,
        )
    assert exc.value.status == 403
    assert exc.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"


def test_http_api_validate_candidate_endpoint(test_env):
    """测试 12：HTTP API 端点 POST /api/v1/projects/{project_id}/chapters/{chapter_id}/validate-candidate 集成测试。"""
    app = FastAPI()
    current_p = test_env["leader"]

    @app.exception_handler(DomainError)
    async def domain_error_handler(request, exc: DomainError):
        from starlette.responses import JSONResponse
        return JSONResponse(status_code=exc.status, content={"code": exc.code, "message": exc.message})

    def override_current_user():
        return current_p

    include_workflow_routes(app, test_env["demo"], override_current_user, DummyParser())
    client = TestClient(app)

    # 1. 提交清洁内容验证 -> 200 OK
    resp_clean = client.post(
        "/api/v1/projects/alpha-project/chapters/ch-tech-01/validate-candidate",
        json={"content": "### 1. 规范设计\n[P1] 系统设计完全满足要求[证:ev-iso9001]。"},
    )
    assert resp_clean.status_code == 200
    data_clean = resp_clean.json()
    assert data_clean["validation_passed"] is True
    assert data_clean["quality_health_score"] == 100
    assert data_clean["quality_health_rating"] == "excellent"

    # 2. 提交带瑕疵内容验证 -> 200 OK，包含 blocker 详细列表
    resp_dirty = client.post(
        "/api/v1/projects/alpha-project/chapters/ch-tech-01/validate-candidate",
        json={"content": "### 1. 规范设计\n[P1] 参数【待补】，存在负偏离无法满足要求。"},
    )
    assert resp_dirty.status_code == 200
    data_dirty = resp_dirty.json()
    assert data_dirty["validation_passed"] is False
    assert len(data_dirty["detected_blockers"]) >= 2
    assert any(b["code"] == "PLACEHOLDER_RESIDUAL" for b in data_dirty["detected_blockers"])

    # 3. 跨租户鉴权拦截 -> 404 NOT_FOUND
    current_p = test_env["beta_user"]
    resp_404 = client.post(
        "/api/v1/projects/alpha-project/chapters/ch-tech-01/validate-candidate",
        json={"content": "测试内容"},
    )
    assert resp_404.status_code == 404
