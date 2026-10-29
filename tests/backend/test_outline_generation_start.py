# 为什么有这个文件：验证章节写作计划Prompt输入组装（APP-M2-T124）与按逐节确认结果启动生成（APP-M2-T126）。
# 它解决什么问题：
# 1. 写作方案输入上下文组装（APP-M2-T124）：验证各章节得分要点小标题、已关联公司证据版本（含 [证] 标记与版本）、RAGFlow 候选切片（含 [片] 溯源）、项目可用事实及 SLA 变量组装为标准模型 Prompt 写作计划，包含字数预期、事实变量不可篡改约束及 [证] 引用标记规范；
# 2. 逐节确认启动生成（APP-M2-T126）：落地 start_chapter_generation(project_id, chapter_id, principal)，验证按逐节确认结果独立启动已确认章节的生成任务，未确认分册或未确认章节绝对不阻塞已确认章节的独立启动；未确认方案的章节企图启动生成前置抛出 400 PLAN_NOT_CONFIRMED；
# 3. 异步任务与进度流转：验证在 demo_job 中创建异步任务（job_type="generate_chapter", status="running", progress=0），并与 JobProgress 进度流转对接；
# 4. 敏感项目本地模型强门禁：验证敏感项目强制使用本地模型配置，企图使用云端模型抛出 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。

import time
import pytest

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.chapter_generation import (
    ChapterGenerationService,
    assemble_writing_prompt_plan,
    start_chapter_generation,
)
from icg_demo.domain import DemoService, DomainError, Principal, iso_time, new_id
from icg_demo.generation_context import (
    build_generation_context,
    chapter_plan,
    plan_is_current,
    writing_source_fingerprint,
)
from icg_demo.model_config_storage import ModelConfig
from icg_demo.ports import ModelProvider, ParserProvider
from icg_demo.workflow import WorkflowService


class DummyParser(ParserProvider):
    def parse(self, filename: str, content: bytes) -> dict:
        return {"title": "测试文件", "pagination": "none", "pages": [], "warnings": []}


class MockModelProvider(ModelProvider):
    name = "mock-generator-model"
    is_real_model = True
    is_local = True

    def __init__(self, reply: str = "本章根据已确认条款和事实进行技术方案阐述。服务期限为 {{fact:fact-service-term}}。"):
        self.reply = reply
        self.calls = []

    def suggest(self, instruction: str, content: str) -> str:
        self.calls.append((instruction, content))
        return self.reply


class MockRetrievalCandidate:
    def __init__(self, source_id, text, chunk_id=None, document_id=None, path="B", reference_only=True):
        self.source_id = source_id
        self.text = text
        self.chunk_id = chunk_id or source_id
        self.document_id = document_id or "doc-rag-01"
        self.path = path
        self.attachable = False
        self.reference_only = reference_only


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
def generation_env():
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
                    "第一页：招标基本要求。\n服务期限：12个月。",
                    "第二页：技术指标要求：投标人须具备有效ISO9001证书，并具备高可用容灾架构能力。",
                ],
            }
        },
        "requirements": {
            "req-tech-01": {
                "id": "req-tech-01",
                "volume": "technical",
                "category": "technical",
                "chapter_id": "alpha-tech",
                "text": "投标人须具备有效ISO9001证书，并具备高可用容灾架构能力。",
                "response": "经核对，我司具备该证书及完备高可用方案。",
                "status": "confirmed",
                "evidence_ids": ["ev-iso9001"],
                "volume_confirmed_by": "alpha-manager",  # 分流已由项目负责人确认（PRD §5.3.1 规则 8）
                "volume_confirmed_at": "2026-10-01T00:00:00+00:00",
                "source": {
                    "file_id": "file-tender-01",
                    "page": 2,
                    "quote": "技术指标要求：投标人须具备有效ISO9001证书，并具备高可用容灾架构能力。",
                },
            },
            "req-biz-01": {
                "id": "req-biz-01",
                "volume": "business",
                "category": "business",
                "chapter_id": "alpha-business",
                "text": "商务响应要求提供付款方式承诺与报价明细。",
                "response": "同意商务付款条款。",
                "status": "confirmed",
                "evidence_ids": [],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "招标基本要求。",
                },
            },
        },
        "facts": {
            "fact-service-term": {
                "id": "fact-service-term",
                "key": "服务期限",
                "value": "12",
                "unit": "个月",
                "status": "confirmed",
                "required": True,
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "服务期限：12个月。",
                },
            }
        },
        "candidates": {},
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

    # 设置技术章节 alpha-tech 的方案为已确认状态
    tech_plan = {
        "id": "alpha-tech",
        "fact_ids": ["fact-service-term"],
        "writing_points": "1. 总体技术架构设计\n2. 数据库主从高可用与双活保障\n3. 应急响应机制",
        "target_length": 800,
        "confirmed_by": "alpha-manager",
        "confirmed_by_name": "甲公司项目经理（合成）",
        "confirmed_at": "2026-10-21T10:00:00+08:00",
        "confirmation_pending": False,
    }
    wf["writing_plan"]["chapters"]["alpha-tech"] = tech_plan
    tech_plan["confirmed_input_fingerprint"] = writing_source_fingerprint(state, "alpha-project", "alpha-tech")

    # 商务章节 alpha-business 故意保持未确认（confirmed_at=None）
    biz_plan = {
        "id": "alpha-business",
        "fact_ids": [],
        "writing_points": "商务条款响应与商务承诺函",
        "target_length": 500,
        "confirmed_by": None,
        "confirmed_at": None,
        "confirmation_pending": True,
        "confirmed_input_fingerprint": None,
    }
    wf["writing_plan"]["chapters"]["alpha-business"] = biz_plan

    # 设置 RAGFlow 假切片候选
    rag_candidate = MockRetrievalCandidate(
        source_id="chunk-bge-001",
        text="甲公司在同类大型高可用平台建设中，采用分布式微服务与三地两中心灾备体系，SLA可用性达到99.99%。",
        chunk_id="chunk-bge-001",
        document_id="doc-ragflow-tech-kb-01",
        path="B",
        reference_only=True,
    )
    evidence_service = MockEvidenceCandidateService(candidates=[rag_candidate])

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


def test_assemble_writing_prompt_plan_context_complete(generation_env):
    """验证写作方案输入上下文完整组装（APP-M2-T124）。"""
    env = generation_env
    plan_data = env["chapter_gen_service"].assemble_writing_prompt_plan(
        "alpha-project",
        "alpha-tech",
        principal=env["lead_principal"],
    )

    prompt = plan_data["prompt"]
    assert "【章节与分册目标】" in prompt
    assert "章节：技术方案（分册：technical）" in prompt
    assert "项目：甲公司合成投标项目" in prompt

    # 1. 各章节得分要点小标题
    assert "【得分要点小标题与写作计划】" in prompt
    assert "1. 总体技术架构设计" in prompt
    assert "2. 数据库主从高可用与双活保障" in prompt
    assert "3. 应急响应机制" in prompt

    # 2. 字数预期
    assert "【字数预期】" in prompt
    assert "800 字" in prompt

    # 3. 事实约束规范
    assert "【事实约束规范】" in prompt
    assert "正文引用事实必须保留变量标记" in prompt
    assert "{{fact:fact-service-term}}" in prompt

    # 4. [证] 引用标记规范
    assert "【证据引用规范】" in prompt
    assert "必须使用 [证] 或 [证:编号] 标记引用已核对的公司资质" in prompt
    assert "[片] 检索切片仅供写作方案参考，不得作为正式附着证据" in prompt

    # 5. 已关联公司证据清单（带 tag [证]、版本、有效期）
    assert "【已关联公司证据清单】" in prompt
    assert "[证] 已确认可引用证据：ISO9001质量管理体系认证证书" in prompt
    assert "记录版本 2" in prompt
    assert "有效期至 2027-06-30" in prompt
    assert "QA-2024-9001" in prompt

    # 6. RAGFlow 检索证据切片（带 tag [片]、chunk_id、document_id 溯源）
    assert "【RAGFlow 检索证据候选切片】" in prompt
    assert "[片:chunk-bge-001] 检索切片（chunk_id: chunk-bge-001, document_id: doc-ragflow-tech-kb-01）" in prompt
    assert "三地两中心灾备体系" in prompt

    # 7. 结构化 snapshot 对象校验
    snapshot = plan_data["input_snapshot"]
    assert snapshot["scope"] == "whole_chapter"
    assert snapshot["chapter"]["id"] == "alpha-tech"
    assert len(snapshot["evidence"]) == 1
    assert snapshot["evidence"][0]["id"] == "ev-iso9001"
    assert len(snapshot["retrieved_evidence"]) == 1
    assert snapshot["retrieved_evidence"][0]["chunk_id"] == "chunk-bge-001"


def test_start_chapter_generation_success_creates_job(generation_env):
    """验证逐节确认后启动已确认章节生成，在 demo_job 中创建异步任务（APP-M2-T126）。"""
    env = generation_env
    res = env["chapter_gen_service"].start_chapter_generation(
        "alpha-project",
        "alpha-tech",
        env["lead_principal"],
    )

    job_id = res["job_id"]
    assert job_id.startswith("job-")
    assert res["project_id"] == "alpha-project"
    assert res["chapter_id"] == "alpha-tech"
    assert res["status"] == "running"
    assert res["progress"] >= 0

    # 验证 demo_job 持久化记录
    job_record = env["repo"].read_job(job_id)
    assert job_record is not None
    assert job_record["id"] == job_id
    assert job_record["job_type"] == "generate_chapter"
    assert job_record["project_id"] == "alpha-project"
    assert job_record["status"] == "running"
    assert job_record["created_by"] == "alpha-manager"
    assert job_record["step_name"] is not None

    # 验证 recoverable_jobs 状态同步
    state = env["repo"].read()
    assert job_id in state.recoverable_jobs
    assert state.recoverable_jobs[job_id]["type"] == "generate_chapter"


def test_independent_start_unconfirmed_chapters_do_not_block_confirmed_chapter(generation_env):
    """验证逐节独立启动：未确认分册或章节绝对不阻塞已确认章节的独立启动（APP-M2-T126 核心门禁）。"""
    env = generation_env

    # 确保 alpha-business 处于未确认状态
    state = env["repo"].read()
    assert not plan_is_current(state, "alpha-project", "alpha-business")

    # 1. 启动已确认的技术章节 alpha-tech -> 必须成功，不被未确认的商务章节阻塞！
    res = env["chapter_gen_service"].start_chapter_generation(
        "alpha-project",
        "alpha-tech",
        env["writer_principal"],
    )
    assert res["status"] == "running"
    assert res["job_id"] is not None

    # 2. 企图启动尚未确认写作方案的商务章节 alpha-business -> 必须前置强拦截并抛出 400 PLAN_NOT_CONFIRMED
    with pytest.raises(DomainError) as exc_info:
        env["chapter_gen_service"].start_chapter_generation(
            "alpha-project",
            "alpha-business",
            env["writer_principal"],
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "PLAN_NOT_CONFIRMED"
    assert "尚未确认" in exc_info.value.message


def test_start_generation_stale_plan_rejected(generation_env):
    """验证方案过期拦截：方案确认后若项目事实被修改导致指纹失效，启动生成被 409 PLAN_NOT_CONFIRMED 拦截。"""
    env = generation_env

    # 修改事实取值，使之前的 confirmed_input_fingerprint 失效
    def tamper_fact(st):
        st.workflows["alpha-project"]["facts"]["fact-service-term"]["value"] = "24"
        st.projects["alpha-project"].revision += 1
    env["repo"].transaction(tamper_fact)

    state = env["repo"].read()
    assert not plan_is_current(state, "alpha-project", "alpha-tech")

    with pytest.raises(DomainError) as exc_info:
        env["chapter_gen_service"].start_chapter_generation(
            "alpha-project",
            "alpha-tech",
            env["lead_principal"],
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "PLAN_NOT_CONFIRMED"


def test_sensitive_project_blocks_cloud_model(generation_env):
    """验证涉密项目本地模型强门禁：敏感项目绑定云端模型在启动生成前阻断（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）。"""
    env = generation_env

    # 将项目设为敏感项目
    def make_sensitive(st):
        st.projects["alpha-project"].sensitive = True
        st.workflows["alpha-project"]["writing_plan"]["chapters"]["alpha-tech"]["confirmed_input_fingerprint"] = writing_source_fingerprint(st, "alpha-project", "alpha-tech")
        # 绑定云端非本地模型配置
        cloud_cfg = ModelConfig(
            id="cfg-cloud-test",
            company_id="alpha",
            name="公有云大模型",
            provider="openai-compatible",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
            is_local=False,
            allow_sensitive=False,
        )
        st.model_configs[cloud_cfg.id] = cloud_cfg
        st.project_model_configs["alpha-project"] = cloud_cfg.id
    env["repo"].transaction(make_sensitive)

    with pytest.raises(DomainError) as exc_info:
        env["chapter_gen_service"].start_chapter_generation(
            "alpha-project",
            "alpha-tech",
            env["lead_principal"],
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"
    assert "敏感项目只能使用本地模型" in exc_info.value.message


def test_sensitive_project_allows_local_model(generation_env):
    """验证涉密项目本地模型门禁：敏感项目绑定合格本地离线模型配置时正常放行。"""
    env = generation_env

    def make_sensitive_local(st):
        st.projects["alpha-project"].sensitive = True
        st.workflows["alpha-project"]["writing_plan"]["chapters"]["alpha-tech"]["confirmed_input_fingerprint"] = writing_source_fingerprint(st, "alpha-project", "alpha-tech")
        local_cfg = ModelConfig(
            id="cfg-local-test",
            company_id="alpha",
            name="内网离线模型",
            provider="openai-compatible",
            base_url="http://192.168.1.10:8000/v1",
            model="qwen2.5-32b",
            is_local=True,
            allow_sensitive=True,
        )
        st.model_configs[local_cfg.id] = local_cfg
        st.project_model_configs["alpha-project"] = local_cfg.id
    env["repo"].transaction(make_sensitive_local)

    res = env["chapter_gen_service"].start_chapter_generation(
        "alpha-project",
        "alpha-tech",
        env["lead_principal"],
    )
    assert res["status"] == "running"
    assert res["job_id"] is not None


def test_readonly_roles_interception(generation_env):
    """验证只读角色（viewer / auditor / group_admin / platform_admin）启动章节生成被拦截。"""
    env = generation_env

    # 1. 系统只读角色 viewer
    with pytest.raises(DomainError) as exc_info:
        env["chapter_gen_service"].start_chapter_generation(
            "alpha-project",
            "alpha-tech",
            env["viewer_principal"],
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code in ("FORBIDDEN", "PROJECT_WRITER_REQUIRED")

    # 2. 集团管理员 group_admin
    state = env["repo"].read()
    state.accounts["user-group-admin"] = type(state.accounts["alpha-manager"])(
        id="user-group-admin", name="集团只读管理员", company_id="alpha", role="group_admin"
    )
    group_principal = Principal(state.accounts["user-group-admin"], "session-group")

    with pytest.raises(DomainError) as exc_info:
        env["chapter_gen_service"].start_chapter_generation(
            "alpha-project",
            "alpha-tech",
            group_principal,
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_cross_tenant_isolation(generation_env):
    """验证跨租户多公司隔离：乙公司用户无法启动甲公司项目章节生成（404 NOT_FOUND）。"""
    env = generation_env

    with pytest.raises(DomainError) as exc_info:
        env["chapter_gen_service"].start_chapter_generation(
            "alpha-project",
            "alpha-tech",
            env["beta_principal"],
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"


def test_sync_execution_generates_candidate_and_completes_job(generation_env):
    """验证 sync_execute 同步完成候选生成并推进 job 状态至 100% completed。"""
    env = generation_env

    res = env["chapter_gen_service"].start_chapter_generation(
        "alpha-project",
        "alpha-tech",
        env["lead_principal"],
        sync_execute=True,
    )

    assert res["status"] == "completed"
    assert res["progress"] == 100
    assert res["step_name"] == "章节生成完成"
    assert res["candidate"] is not None
    assert "服务期限为 {{fact:fact-service-term}}" in res["candidate"]["content"]

    # 验证候选保存到 workflow
    state = env["repo"].read()
    assert "alpha-tech" in state.workflows["alpha-project"]["candidates"]
    cand = state.workflows["alpha-project"]["candidates"]["alpha-tech"]
    assert cand["id"] == res["candidate"]["id"]

    # 验证 job 状态
    job = env["repo"].read_job(res["job_id"])
    assert job["status"] == "completed"
    assert job["progress"] == 100
    assert job["result_json"]["candidate_id"] == cand["id"]


def test_workflow_service_delegation(generation_env):
    """验证 WorkflowService 顶层门面委派正常。"""
    env = generation_env
    wf = env["workflow_service"]

    # 组装 prompt
    prompt_res = wf.assemble_writing_prompt_plan(
        "alpha-project",
        "alpha-tech",
        principal=env["lead_principal"],
    )
    assert "【得分要点小标题与写作计划】" in prompt_res["prompt"]

    # 启动生成
    start_res = wf.start_chapter_generation(
        "alpha-project",
        "alpha-tech",
        env["lead_principal"],
    )
    assert start_res["status"] == "running"
    assert start_res["job_id"] is not None

    # 顶层全局函数调用 start_chapter_generation 形式 1
    func_res1 = start_chapter_generation(wf, "alpha-project", "alpha-tech", env["lead_principal"])
    assert func_res1["status"] == "running"

    # 顶层全局函数调用 start_chapter_generation 形式 2
    func_res2 = start_chapter_generation("alpha-project", "alpha-tech", env["lead_principal"], demo=env["demo"])
    assert func_res2["status"] == "running"
