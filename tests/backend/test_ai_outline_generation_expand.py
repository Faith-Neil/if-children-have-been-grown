# 为什么有这个文件：验证章节写作方案多段落结构化批量生成引擎（AI-OUTLINE-GENERATE-EXPAND）。
# 它解决什么问题：
# 1. 结构化分段解析（parse_structured_paragraphs）：验证模型生成正文解析为 [P1]~[Pn] 结构化段落，携带独立 paragraph_id、小标题映射、得分要点、字数统计；
# 2. 引用标记提取与幻觉校验（extract_paragraph_citations）：提取 [证:xxx] 与 [片:xxx]，严格基于入参合法 ID 进行白名单校验，识别虚构证据与切片；
# 3. 结构化 Markdown 回写格式化（format_structured_chapter_content）：验证多段落逆向还原为干净的 Markdown 文本；
# 4. 单章同步生成产物增强：验证 start_chapter_generation(sync_execute=True) 自动填充 paragraphs、structured_content、scoring_subheadings；
# 5. 跨章节独立批量生成（batch_generate_chapters）：验证未确认章节（PLAN_NOT_CONFIRMED）绝对不阻塞已确认章节生成；
# 6. 涉密项目本地模型硬门禁（SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）；
# 7. 角色权限拦截（403 FORBIDDEN）与租户隔离（404 NOT_FOUND）；
# 8. HTTP API 端点集成（POST /api/v1/projects/{project_id}/chapters/batch-generate）。

import time
import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg.domain.chapter_generation import (
    ChapterGenerationService,
    extract_paragraph_citations,
    format_structured_chapter_content,
    parse_scoring_points,
    parse_structured_paragraphs,
)
from icg.domain.domain import DemoService, DomainError, Principal, iso_time, new_id
from icg.domain.generation_context import writing_source_fingerprint
from icg.infra.model_config_storage import ModelConfig
from icg.domain.ports import ModelProvider, ParserProvider
from icg.domain.workflow import WorkflowService
from icg.api.workflow import include_workflow_routes
from fastapi import FastAPI


class DummyParser(ParserProvider):
    def parse(self, filename: str, content: bytes) -> dict:
        return {"title": "测试文件", "pagination": "none", "pages": [], "warnings": []}


class MockModelProvider(ModelProvider):
    name = "mock-generator-model"
    is_real_model = True
    is_local = True

    def __init__(self, reply: str | None = None):
        self.reply = reply or (
            "### 1. 总体技术架构设计\n"
            "[P1] 本项目采用微服务与高可用架构[证:ev-iso9001]，严格遵循质量管理标准。\n\n"
            "### 2. 数据库主从高可用与双活保障\n"
            "[P2] 生产数据库采用主从同步与双活设计[片:rag-chunk-01]，故障切换时间小于 {{fact:fact-rto}} 秒。\n\n"
            "### 3. 应急响应机制\n"
            "[P3] 建立 7x24 小时应急运维体系，提供 {{fact:fact-service-term}} 的长效支持。"
        )
        self.calls = []

    def suggest(self, instruction: str, content: str) -> str:
        self.calls.append((instruction, content))
        return self.reply


class MockEvidenceCandidateService:
    def __init__(self, candidates=None):
        self.candidates = candidates or []
        self.calls = []

    def collect(self, cand_req):
        self.calls.append(cand_req)
        class Result:
            pass
        res = Result()
        res.candidates = self.candidates
        return res


@pytest.fixture
def test_env():
    state = seed_state()
    project = state.projects["alpha-project"]
    project.deadline = "2026-12-31T17:00:00+08:00"
    project.sensitive = False

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
                    "第一页：招标基本要求。\n服务期限：36个月。\n恢复时间目标RTO：30秒。\n投标人需提供详细的项目商务报价与付款方式",
                    "第二页：技术指标要求：投标人需具备成熟的数据库高可用方案与应急响应体系",
                ],
            }
        },
        "requirements": {
            "req-tech-01": {
                "id": "req-tech-01",
                "volume": "technical",
                "chapter_id": "alpha-tech",
                "text": "投标人需具备成熟的数据库高可用方案与应急响应体系",
                "importance": "star",
                "category": "technical",
                "status": "confirmed",
                "response": "满足技术要求",
                "evidence_ids": ["ev-iso9001"],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 2,
                    "quote": "投标人需具备成熟的数据库高可用方案与应急响应体系",
                },
            },
            "req-biz-01": {
                "id": "req-biz-01",
                "volume": "business",
                "chapter_id": "alpha-business",
                "text": "投标人需提供详细的项目商务报价与付款方式",
                "importance": "standard",
                "category": "commercial",
                "status": "confirmed",
                "response": "满足商务要求",
                "evidence_ids": [],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "投标人需提供详细的项目商务报价与付款方式",
                },
            },
        },
        "facts": {
            "fact-service-term": {
                "id": "fact-service-term",
                "key": "服务期限",
                "label": "服务期限",
                "value": "36个月",
                "status": "confirmed",
                "required": True,
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "服务期限：36个月。",
                },
            },
            "fact-rto": {
                "id": "fact-rto",
                "key": "恢复时间目标RTO",
                "label": "恢复时间目标RTO",
                "value": "30",
                "status": "confirmed",
                "required": True,
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "恢复时间目标RTO：30秒。",
                },
            },
        },
        "conflicts": {},
        "candidates": {},
        "checks": {},
        "exports": {},
        "plan_confirmed": True,
        "chapter_order": ["alpha-tech", "alpha-business"],
        "writing_plan": {
            "confirmed_by": "alpha-manager",
            "confirmed_at": "2026-10-21T10:00:00+08:00",
            "chapters": {},
        },
    }
    state.workflows["alpha-project"] = wf

    # 设置分册负责人与团队
    state.project_teams["alpha-project"]["owners"] = {
        "technical": "alpha-manager",
        "business": "alpha-manager",
    }
    state.project_teams["alpha-project"]["members"]["alpha-manager"] = {
        "user_id": "alpha-manager",
        "project_role": "lead",
        "volumes": ["technical", "business"],
    }
    state.project_teams["alpha-project"]["members"]["alpha-editor"] = {
        "user_id": "alpha-editor",
        "project_role": "writer",
        "volumes": ["technical", "business"],
    }

    # 预置已确认的技术方案写作计划
    tech_plan = {
        "id": "alpha-tech",
        "writing_points": [
            "1. 总体技术架构设计",
            "2. 数据库主从高可用与双活保障",
            "3. 应急响应机制",
        ],
        "evidence_ids": ["ev-iso9001"],
        "fact_ids": ["fact-service-term", "fact-rto"],
        "custom_instructions": "重点阐述微服务解耦与故障自动隔离机制。",
        "target_word_count": 1800,
        "confirmed_at": "2026-10-21T10:00:00+08:00",
        "confirmed_by": "alpha-manager",
    }
    wf["writing_plan"]["chapters"]["alpha-tech"] = tech_plan
    tech_fingerprint = writing_source_fingerprint(state, "alpha-project", "alpha-tech")
    tech_plan["confirmed_input_fingerprint"] = tech_fingerprint

    # 预置已确认的商务方案写作计划
    biz_plan = {
        "id": "alpha-business",
        "writing_points": [
            "1. 商务报价与计费明细",
            "2. 付款周期与结算方式",
        ],
        "evidence_ids": [],
        "fact_ids": ["fact-service-term"],
        "custom_instructions": "阐明按月结算与履约保函安排。",
        "target_word_count": 1200,
        "confirmed_at": "2026-10-21T10:00:00+08:00",
        "confirmed_by": "alpha-manager",
    }
    wf["writing_plan"]["chapters"]["alpha-business"] = biz_plan
    biz_fingerprint = writing_source_fingerprint(state, "alpha-project", "alpha-business")
    biz_plan["confirmed_input_fingerprint"] = biz_fingerprint

    evidence_service = MockEvidenceCandidateService()
    repo = MemoryRepository(state)
    demo = DemoService(
        repository=repo,
        model_provider=MockModelProvider(),
        evidence_service=evidence_service,
    )
    wf_service = WorkflowService(demo, DummyParser())
    chapter_gen_service = ChapterGenerationService(demo, repository=repo, evidence_service=evidence_service)

    lead_principal = Principal(state.accounts["alpha-manager"], "session-lead")
    writer_principal = Principal(state.accounts["alpha-editor"], "session-writer")
    viewer_principal = Principal(state.accounts["alpha-viewer"], "session-viewer")
    beta_principal = Principal(state.accounts["beta-editor"], "session-beta")

    return {
        "state": state,
        "project": project,
        "repo": repo,
        "demo": demo,
        "workflow_service": wf_service,
        "chapter_gen_service": chapter_gen_service,
        "evidence_service": evidence_service,
        "lead_principal": lead_principal,
        "writer_principal": writer_principal,
        "viewer_principal": viewer_principal,
        "beta_principal": beta_principal,
    }


# 1. 结构化段落解析（含显式标签、得分要点小标题、引用与变量）
def test_parse_structured_paragraphs_with_explicit_labels():
    raw_content = (
        "### 1. 总体技术架构设计\n"
        "[P1] 本项目采用微服务与高可用架构[证:ev-iso9001]，严格遵循质量管理体系标准。\n\n"
        "### 2. 数据库主从高可用与双活保障\n"
        "[P2] 生产数据库采用主从同步[片:rag-chunk-01]，在 {{fact:fact-rto}} 秒内完成故障切换。\n\n"
        "### 3. 应急响应机制\n"
        "[P3] 建立 7x24 小时应急运维体系，提供 {{fact:fact-service-term}} 的长效支持。"
    )
    scoring_points = [
        "1. 总体技术架构设计",
        "2. 数据库主从高可用与双活保障",
        "3. 应急响应机制",
    ]
    allowed_evidences = ["ev-iso9001"]
    allowed_snippets = ["rag-chunk-01"]

    paragraphs = parse_structured_paragraphs(
        raw_content=raw_content,
        scoring_points=scoring_points,
        allowed_evidence_ids=allowed_evidences,
        allowed_snippet_ids=allowed_snippets,
    )

    assert len(paragraphs) == 3

    # P1
    p1 = paragraphs[0]
    assert p1["order"] == 1
    assert p1["label"] == "[P1]"
    assert p1["subheading"] == "### 1. 总体技术架构设计"
    assert p1["title"] == "总体技术架构设计"
    assert p1["scoring_point"] == "总体技术架构设计"
    assert "质量管理体系标准" in p1["text"]
    assert len(p1["citations"]) == 1
    assert p1["citations"][0]["id"] == "ev-iso9001"
    assert p1["citations"][0]["type"] == "evidence"
    assert p1["citations"][0]["valid"] is True
    assert p1["char_length"] == len(p1["text"])

    # P2
    p2 = paragraphs[1]
    assert p2["order"] == 2
    assert p2["label"] == "[P2]"
    assert p2["subheading"] == "### 2. 数据库主从高可用与双活保障"
    assert p2["title"] == "数据库主从高可用与双活保障"
    assert len(p2["citations"]) == 1
    assert p2["citations"][0]["id"] == "rag-chunk-01"
    assert p2["citations"][0]["type"] == "snippet"
    assert p2["citations"][0]["valid"] is True
    assert "fact:fact-rto" in p2["variables"]

    # P3
    p3 = paragraphs[2]
    assert p3["order"] == 3
    assert p3["label"] == "[P3]"
    assert p3["subheading"] == "### 3. 应急响应机制"
    assert p3["title"] == "应急响应机制"
    assert "fact:fact-service-term" in p3["variables"]


# 2. 结构化段落解析（无显式标签时自动分配 [P1]~[Pn] 并对齐要点）
def test_parse_structured_paragraphs_without_labels_auto_assigns():
    raw_content = (
        "第一段内容：总体技术路线阐述与微服务规划。\n\n"
        "第二段内容：高可用集群部署与数据一致性方案。\n\n"
        "第三段内容：运维支持与全生命周期服务保障。"
    )
    scoring_points = [
        "总体技术架构",
        "高可用保障",
        "运维服务体系",
    ]

    paragraphs = parse_structured_paragraphs(
        raw_content=raw_content,
        scoring_points=scoring_points,
    )

    assert len(paragraphs) == 3
    assert paragraphs[0]["label"] == "[P1]"
    assert paragraphs[0]["subheading"] == "### 1.1 总体技术架构"
    assert paragraphs[0]["title"] == "总体技术架构"
    assert paragraphs[0]["scoring_point"] == "总体技术架构"
    assert "总体技术路线" in paragraphs[0]["text"]

    assert paragraphs[1]["label"] == "[P2]"
    assert paragraphs[1]["subheading"] == "### 1.2 高可用保障"
    assert paragraphs[1]["title"] == "高可用保障"

    assert paragraphs[2]["label"] == "[P3]"
    assert paragraphs[2]["subheading"] == "### 1.3 运维服务体系"
    assert paragraphs[2]["title"] == "运维服务体系"


# 3. 引用标记提取与幻觉校验（有效引用 vs 虚构引用）
def test_extract_paragraph_citations_and_detect_unverified():
    text = (
        "根据甲公司资质[证:ev-iso9001]与虚构证书[证:ev-fake-999]，"
        "结合方案切片[片:chunk-real]及编造切片[片:chunk-hallucinated]进行交付。"
    )
    allowed_evidences = ["ev-iso9001"]
    allowed_snippets = ["chunk-real"]

    citations = extract_paragraph_citations(
        text=text,
        allowed_evidence_ids=allowed_evidences,
        allowed_snippet_ids=allowed_snippets,
    )

    assert len(citations) == 4

    # 真实证据
    c_ev_real = next(c for c in citations if c["id"] == "ev-iso9001")
    assert c_ev_real["type"] == "evidence"
    assert c_ev_real["valid"] is True

    # 虚假/编造证据
    c_ev_fake = next(c for c in citations if c["id"] == "ev-fake-999")
    assert c_ev_fake["type"] == "evidence"
    assert c_ev_fake["valid"] is False

    # 真实切片
    c_snip_real = next(c for c in citations if c["id"] == "chunk-real")
    assert c_snip_real["type"] == "snippet"
    assert c_snip_real["valid"] is True

    # 虚假切片
    c_snip_fake = next(c for c in citations if c["id"] == "chunk-hallucinated")
    assert c_snip_fake["type"] == "snippet"
    assert c_snip_fake["valid"] is False


# 4. 结构化段落 Markdown 回写格式化
def test_format_structured_chapter_content_roundtrip():
    paragraphs = [
        {
            "paragraph_id": "p-01",
            "order": 1,
            "label": "[P1]",
            "subheading": "### 1. 总体架构",
            "text": "本章节介绍系统微服务设计。[证:ev-01]",
        },
        {
            "paragraph_id": "p-02",
            "order": 2,
            "label": "[P2]",
            "subheading": "### 2. 安全保障",
            "text": "采用三员分立与国密算法加密。[片:snip-01]",
        },
    ]

    formatted_md = format_structured_chapter_content(paragraphs)
    assert "### 1. 总体架构" in formatted_md
    assert "[P1] 本章节介绍系统微服务设计。[证:ev-01]" in formatted_md
    assert "### 2. 安全保障" in formatted_md
    assert "[P2] 采用三员分立与国密算法加密。[片:snip-01]" in formatted_md


# 5. 单章同步生成产物增强（包含 paragraphs、structured_content、scoring_subheadings）
def test_start_chapter_generation_sync_enriches_candidate_paragraphs(test_env):
    env = test_env
    res = env["chapter_gen_service"].start_chapter_generation(
        project_id="alpha-project",
        chapter_id="alpha-tech",
        principal=env["lead_principal"],
        sync_execute=True,
    )

    assert res["status"] == "completed"
    assert res["candidate"] is not None

    cand = res["candidate"]
    assert "paragraphs" in cand
    assert isinstance(cand["paragraphs"], list)
    assert len(cand["paragraphs"]) == 3

    p1 = cand["paragraphs"][0]
    assert p1["label"] == "[P1]"
    assert p1["subheading"] == "### 1. 总体技术架构设计"
    assert p1["title"] == "总体技术架构设计"
    assert len(p1["citations"]) >= 1

    assert "structured_content" in cand
    assert "[P1]" in cand["structured_content"]

    assert "scoring_subheadings" in cand
    assert len(cand["scoring_subheadings"]) == 3
    assert cand["scoring_subheadings"][0] == "总体技术架构设计"


# 6. 多章节独立批量生成成功（全已确认）
def test_batch_generate_chapters_all_confirmed_success(test_env):
    env = test_env
    batch_res = env["chapter_gen_service"].batch_generate_chapters(
        project_id="alpha-project",
        chapter_ids=["alpha-tech", "alpha-business"],
        principal=env["lead_principal"],
        sync_execute=True,
    )

    assert batch_res["total_chapters"] == 2
    assert batch_res["successful_count"] == 2
    assert batch_res["failed_count"] == 0
    assert len(batch_res["failed_chapters"]) == 0

    results = batch_res["results"]
    assert "alpha-tech" in results
    assert "alpha-business" in results

    tech_item = results["alpha-tech"]
    assert tech_item["status"] == "completed"
    assert tech_item["candidate"] is not None
    assert len(tech_item["paragraphs"]) == 3

    biz_item = results["alpha-business"]
    assert biz_item["status"] == "completed"
    assert biz_item["candidate"] is not None

    # 预算统计与上下文指纹汇总
    summary = batch_res["aggregate_summary"]
    assert summary["total_estimated_tokens"] > 0
    assert "alpha-tech" in summary["context_fingerprints"]
    assert "alpha-business" in summary["context_fingerprints"]


# 7. 批量生成中未确认方案章节绝对不阻塞已确认章节（PRD §5.7.8 关键红线）
def test_batch_generate_chapters_unconfirmed_does_not_block_confirmed(test_env):
    env = test_env
    # 将 alpha-business 的方案重置为未确认
    def unconfirm_biz(st):
        st.workflows["alpha-project"]["writing_plan"]["chapters"]["alpha-business"]["confirmed_at"] = None
    env["repo"].transaction(unconfirm_biz)

    batch_res = env["chapter_gen_service"].batch_generate_chapters(
        project_id="alpha-project",
        chapter_ids=["alpha-tech", "alpha-business"],
        principal=env["lead_principal"],
        sync_execute=True,
    )

    assert batch_res["total_chapters"] == 2
    assert batch_res["successful_count"] == 1
    assert batch_res["failed_count"] == 1

    # 已确认的 alpha-tech 成功生成，不受任何影响
    assert "alpha-tech" in batch_res["results"]
    assert batch_res["results"]["alpha-tech"]["status"] == "completed"
    assert batch_res["results"]["alpha-tech"]["candidate"] is not None

    # 未确认的 alpha-business 独立记录在 failed_chapters 中
    assert "alpha-business" in batch_res["failed_chapters"]
    failed_biz = batch_res["failed_chapters"]["alpha-business"]
    assert failed_biz["code"] == "PLAN_NOT_CONFIRMED"
    assert "未确认方案" in failed_biz["message"] or "写作方案尚未确认" in failed_biz["message"]


# 8. 涉密项目绑定云端模型硬拦截（SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）
def test_batch_generate_chapters_sensitive_project_blocks_cloud_model(test_env):
    env = test_env
    def make_sensitive(st):
        st.projects["alpha-project"].sensitive = True
        cloud_config = ModelConfig(
            id="cfg-cloud-qwen",
            company_id="alpha",
            name="阿里云公有云 Qwen",
            provider="aliyun_dashscope",
            model="qwen-max",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key_masked="sk-***",
            is_local=False,
            allow_sensitive=False,
        )
        st.model_configs["cfg-cloud-qwen"] = cloud_config
        st.project_model_configs["alpha-project"] = "cfg-cloud-qwen"
    env["repo"].transaction(make_sensitive)

    with pytest.raises(DomainError) as exc_info:
        env["chapter_gen_service"].batch_generate_chapters(
            project_id="alpha-project",
            chapter_ids=["alpha-tech"],
            principal=env["lead_principal"],
            sync_execute=True,
        )

    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"


# 9. 只读角色企图批量生成拦截（403 FORBIDDEN）
def test_batch_generate_chapters_readonly_role_interception(test_env):
    env = test_env
    with pytest.raises(DomainError) as exc_info:
        env["chapter_gen_service"].batch_generate_chapters(
            project_id="alpha-project",
            chapter_ids=["alpha-tech"],
            principal=env["viewer_principal"],
            sync_execute=True,
        )

    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"


# 10. 跨租户项目隔离拦截（404 NOT_FOUND）
def test_batch_generate_chapters_cross_tenant_isolation(test_env):
    env = test_env
    with pytest.raises(DomainError) as exc_info:
        env["chapter_gen_service"].batch_generate_chapters(
            project_id="alpha-project",
            chapter_ids=["alpha-tech"],
            principal=env["beta_principal"],
            sync_execute=True,
        )

    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"


# 11. HTTP API 端点集成（POST /api/v1/projects/{project_id}/chapters/batch-generate）
def test_http_batch_generate_chapters_endpoint(test_env):
    env = test_env
    app = FastAPI()

    def dummy_current_user():
        return env["lead_principal"]

    include_workflow_routes(app, env["demo"], dummy_current_user, DummyParser())
    client = TestClient(app)

    payload = {
        "chapter_ids": ["alpha-tech", "alpha-business"],
        "sync_execute": True,
        "max_context_tokens": 12000,
    }

    response = client.post(
        "/api/v1/projects/alpha-project/chapters/batch-generate",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_chapters"] == 2
    assert data["successful_count"] == 2
    assert data["failed_count"] == 0
    assert "alpha-tech" in data["results"]
    assert "alpha-business" in data["results"]
    assert len(data["results"]["alpha-tech"]["paragraphs"]) == 3
