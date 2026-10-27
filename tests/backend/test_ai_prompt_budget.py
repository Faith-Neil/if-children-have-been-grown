# 为什么有这个文件：验证自适应 Prompt 动态上下文裁剪与 Token 预算控制（AI-DYNAMIC-PROMPT-CONTEXT / PRD MVP v1.8 §5.7.8）。
# 它解决什么问题：
# 1. Token 预算分配策略：根据模型上下文窗口动态分配 Token 预算，支持 max_context_tokens 动态设定并预留生成空间；
# 2. 四级优先级动态自适应裁剪：
#    - Priority 1（最高，绝对不裁剪）：System Prompt、章节标题与评分项必须达标要点、硬性限制规则与格式要求；
#    - Priority 2（高）：高置信度方案片段（相关度 >= 0.70）与强制项目事实变量；
#    - Priority 3（中）：招标文件相关切片与条款；超出预算按相关度降序截取；
#    - Priority 4（低）：补充背景与历史参考片段，超出预算时自适应丢弃；
# 3. 上下文指纹与 Token 统计：中英文字符加权估算（中文字符约 0.7 token，英文单词约 1.3 token），输出完整 token_budget_usage 指标与不可篡改 16 位 SHA-256 context_fingerprint；
# 4. 涉密隔离与防编造红线：涉密项目强制使用本地模型（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL），未匹配变量如实标入 missing_variables，严禁凭空编造。

import pytest
import time

from icg.infra.memory_repository import MemoryRepository, seed_state
from icg.domain.chapter_generation import (
    ChapterGenerationService,
    assemble_writing_prompt_plan,
    start_chapter_generation,
)
from icg.domain.domain import DemoService, DomainError, Principal
from icg.domain.generation_context import writing_source_fingerprint
from icg.domain.ports import ModelProvider, ParserProvider
from icg.domain.prompt_budget import (
    DEFAULT_MAX_CONTEXT_TOKENS,
    DEFAULT_RESERVED_GENERATION_TOKENS,
    DynamicPromptContextManager,
    TokenBudgetUsage,
    check_sensitive_model_gate,
    compute_context_fingerprint,
    estimate_tokens,
)
from icg.infra.model_config_storage import ModelConfig


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
def budget_env():
    state = seed_state()
    project = state.projects["alpha-project"]
    project.deadline = "2026-12-31T17:00:00+08:00"
    project.sensitive = False

    # 预置公司证据
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

    # 预置工作流与条款
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
                "source": {
                    "file_id": "file-tender-01",
                    "page": 2,
                    "quote": "技术指标要求：投标人须具备有效ISO9001证书，并具备高可用容灾架构能力。",
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
    }
    state.project_teams["alpha-project"]["members"]["alpha-manager"] = {
        "user_id": "alpha-manager",
        "project_role": "lead",
        "volumes": ["technical"],
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

    # RAGFlow 假切片候选
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
    chapter_gen_service = ChapterGenerationService(demo, repository=repo, evidence_service=evidence_service)
    lead_principal = Principal(state.accounts["alpha-manager"], "session-lead")

    return {
        "state": state,
        "project": project,
        "repo": repo,
        "demo": demo,
        "chapter_gen_service": chapter_gen_service,
        "evidence_service": evidence_service,
        "lead_principal": lead_principal,
    }


# ==============================================================================
# 1. Token 加权估算测试（中英文差异化与边界值）
# ==============================================================================
def test_token_estimation_chinese_and_english_weighted():
    # 空文本为 0
    assert estimate_tokens("") == 0
    assert estimate_tokens(None) == 0

    # 纯中文：12 个中文字符，约 12 * 0.7 = 8.4 -> 9 tokens
    chinese_text = "甲公司拥有高可用容灾架构"
    chinese_tokens = estimate_tokens(chinese_text)
    assert chinese_tokens == 9
    # 10 个中文字符：10 * 0.7 = 7.0 -> 7 tokens
    assert estimate_tokens("一二三四五六七八九十") == 7

    # 纯英文单词：5 个英文单词，约 5 * 1.3 = 6.5 -> 7 tokens
    english_text = "high availability cloud disaster recovery"
    english_tokens = estimate_tokens(english_text)
    assert english_tokens >= 7

    # 混合文本
    mixed_text = "SLA可用性达到 99.99%，支持 multi-region 部署。"
    mixed_tokens = estimate_tokens(mixed_text)
    assert mixed_tokens > 0
    # 极短字符至少 1
    assert estimate_tokens("a") >= 1
    assert estimate_tokens("中") >= 1


# ==============================================================================
# 2. Priority 1（最高核心指令）极紧预算下绝对不裁剪
# ==============================================================================
def test_priority_1_core_never_truncated_under_tight_budget():
    snapshot = {
        "chapter": {"id": "c-01", "title": "安全运维保障", "volume": "technical"},
        "plan": {"writing_points": "1. 安全制度\n2. 演练计划", "target_length": 1000},
        "project": {"name": "合成投标项目"},
        "facts": [{"id": "f-01", "key": "可用性", "value": "99.99", "unit": "%"}],
        "requirements": [{"id": "r-01", "text": "需具备安全资质", "response": "已具备"}],
    }
    # 设定极端微小的上下文预算（512 token，其中预留 128 -> prompt 预算 384）
    manager = DynamicPromptContextManager(max_context_tokens=512, reserved_generation_tokens=128)
    res = manager.assemble_budgeted_prompt(snapshot)

    prompt = res["prompt"]
    # 验证 P1 核心元素全部在 prompt 中完整存在，绝对不被裁剪
    assert "【章节与分册目标】" in prompt
    assert "安全运维保障" in prompt
    assert "【得分要点小标题与写作计划】" in prompt
    assert "1. 安全制度" in prompt
    assert "2. 演练计划" in prompt
    assert "【字数预期】" in prompt
    assert "1000 字" in prompt
    assert "【事实约束规范】" in prompt
    assert "【证据引用规范】" in prompt

    # priority_breakdown 记录了 P1 的消耗
    assert res["token_budget_usage"]["priority_breakdown"]["priority_1_system_and_core"] > 0


# ==============================================================================
# 3. 优先级自适应裁剪：预算紧张时低优先级 Priority 4 优先丢弃
# ==============================================================================
def test_priority_adaptive_truncation_p4_dropped_first():
    snapshot = {
        "chapter": {"id": "c-01", "title": "系统架构设计", "volume": "technical"},
        "plan": {"writing_points": "架构概述", "target_length": 500},
        "project": {"name": "智慧政务系统"},
        "facts": [{"id": "f-01", "key": "并发数", "value": "10000", "unit": "TPS"}],
        "requirements": [{"id": "r-01", "text": "需支持双活", "response": "完全支持双活架构"}],
        "evidence": [{"id": "ev-01", "name": "CMMI5认证", "content": "软件成熟度顶级认证"}],
        "retrieved_evidence": [
            {
                "id": "chunk-bg-01",
                "chunk_id": "chunk-bg-01",
                "content": "长篇背景资料：" + "分布式数据库架构细节与演化历史。" * 20,
                "reference_only": True,
            }
        ],
    }
    # 预算适中，足够容纳 P1, P2, P3，但不足以容纳超长的 P4
    manager = DynamicPromptContextManager(max_context_tokens=600, reserved_generation_tokens=150)
    res = manager.assemble_budgeted_prompt(snapshot)

    # P4 切片被裁剪或丢弃
    truncated = res["truncated_items"]
    assert any(item["priority"] == "P4" and item["id"] == "chunk-bg-01" for item in truncated)
    # P1/P2/P3 核心内容依然保留
    assert "【已确认项目事实与变量清单】" in res["prompt"]
    assert "并发数" in res["prompt"]
    assert "【已关联公司证据清单】" in res["prompt"]


# ==============================================================================
# 4. Priority 2 高置信度方案片段在空间紧张时优雅局部截断
# ==============================================================================
def test_priority_2_snippet_partial_truncation():
    snapshot = {
        "chapter": {"id": "c-01", "title": "应急处置预案", "volume": "technical"},
        "plan": {"writing_points": "预案说明", "target_length": 500},
        "project": {"name": "应急指挥系统"},
    }
    # 提供一段长的高置信度方案片段（score=0.92）
    long_body = "高可用秒级容灾切换方案：" + "在发生机房级故障时，流量调度系统秒级切换。" * 30
    snippet_matches = [
        {
            "snippet_id": "snip-high-01",
            "product": "秒级容灾平台",
            "snippet_type": "应急方案",
            "score": 0.92,
            "rendered_body": long_body,
            "cite_tag": "[片:snip-high-01]",
        }
    ]
    # 预算紧凑，只留出少量空间给 P2 局部截断
    manager = DynamicPromptContextManager(max_context_tokens=520, reserved_generation_tokens=120)
    res = manager.assemble_budgeted_prompt(snapshot, snippet_matches=snippet_matches)

    prompt = res["prompt"]
    # 方案片段被局部截断并附带提示
    assert "[片:snip-high-01]" in prompt
    assert "[因Token预算限制，该方案片段后续内容已截断]" in prompt
    assert any(
        item["id"] == "snip-high-01" and item["reason"] == "partially_truncated_by_budget"
        for item in res["truncated_items"]
    )


# ==============================================================================
# 5. Token 预算统计准确性与结构完整性
# ==============================================================================
def test_token_budget_usage_statistics_accuracy():
    manager = DynamicPromptContextManager(max_context_tokens=2048, reserved_generation_tokens=512)
    assert manager.max_context_tokens == 2048
    assert manager.reserved_generation_tokens == 512
    assert manager.prompt_budget == 1536

    snapshot = {
        "chapter": {"id": "c-01", "title": "技术架构", "volume": "technical"},
        "plan": {"writing_points": "架构图与说明", "target_length": 600},
        "project": {"name": "平台项目"},
    }
    res = manager.assemble_budgeted_prompt(snapshot)
    usage = res["token_budget_usage"]

    assert usage["max_context_tokens"] == 2048
    assert usage["reserved_generation_tokens"] == 512
    assert usage["prompt_budget"] == 1536
    assert usage["prompt_tokens"] > 0
    assert usage["remaining_prompt_tokens"] == usage["prompt_budget"] - usage["prompt_tokens"]
    assert usage["total_estimated_tokens"] == usage["prompt_tokens"] + usage["reserved_generation_tokens"]
    assert "priority_1_system_and_core" in usage["priority_breakdown"]
    assert "priority_2_snippets_and_facts" in usage["priority_breakdown"]
    assert "priority_3_tender_clauses" in usage["priority_breakdown"]
    assert "priority_4_background_references" in usage["priority_breakdown"]


# ==============================================================================
# 6. 上下文指纹（context_fingerprint）确定性与防篡改
# ==============================================================================
def test_context_fingerprint_deterministic_and_tamper_evident():
    fp1 = compute_context_fingerprint(
        chapter_id="c-01",
        core_summary="技术架构:总体设计",
        retained_p2_ids=["f-01", "snip-01"],
        retained_p3_ids=["req-01"],
        retained_p4_ids=["chunk-01"],
        facts_snapshot={"服务期限": "12 个月"},
    )
    # 长度为 16 位的十六进制字符串
    assert len(fp1) == 16

    # 确定性：相同入参产生完全一致的指纹
    fp2 = compute_context_fingerprint(
        chapter_id="c-01",
        core_summary="技术架构:总体设计",
        retained_p2_ids=["snip-01", "f-01"],  # 顺序不同但内部会排序
        retained_p3_ids=["req-01"],
        retained_p4_ids=["chunk-01"],
        facts_snapshot={"服务期限": "12 个月"},
    )
    assert fp1 == fp2

    # 防篡改：任何微小事实变更，指纹立刻改变
    fp_tampered = compute_context_fingerprint(
        chapter_id="c-01",
        core_summary="技术架构:总体设计",
        retained_p2_ids=["f-01", "snip-01"],
        retained_p3_ids=["req-01"],
        retained_p4_ids=["chunk-01"],
        facts_snapshot={"服务期限": "24 个月"},  # 改变事实取值
    )
    assert fp1 != fp_tampered


# ==============================================================================
# 7. 缺失变量如实标入 missing_variables，杜绝模型幻觉编造
# ==============================================================================
def test_missing_variables_detected_without_hallucination():
    snapshot = {
        "chapter": {"id": "c-01", "title": "实施进度计划", "volume": "technical"},
        "plan": {"writing_points": "里程碑规划", "target_length": 500},
        "project": {"name": "交付项目"},
        "facts": [{"id": "f-01", "key": "总工期", "value": "180", "unit": "天"}],
    }
    snippet_matches = [
        {
            "snippet_id": "snip-01",
            "product": "项目管理规范",
            "score": 0.85,
            "rendered_body": "项目于 {{fact:start_date}} 启动，关键里程碑负责人为 {{pm_name}}。",
            "missing_variables": ["fact:start_date", "pm_name"],
        }
    ]
    manager = DynamicPromptContextManager(max_context_tokens=2048)
    res = manager.assemble_budgeted_prompt(snapshot, snippet_matches=snippet_matches)

    assert res["has_missing_variables"] is True
    assert "fact:start_date" in res["missing_variables"]
    assert "pm_name" in res["missing_variables"]


# ==============================================================================
# 8. 敏感项目本地模型硬门禁拦截
# ==============================================================================
def test_sensitive_project_blocks_cloud_model(budget_env):
    env = budget_env
    state = env["state"]
    project = env["project"]

    # 标记项目为敏感项目
    project.sensitive = True

    # 绑定云端/非本地模型配置
    cloud_config = ModelConfig(
        id="cfg-cloud-qwen",
        company_id="alpha",
        name="云端通义千问",
        provider="cloud",
        base_url="https://dashscope.aliyuncs.com/api/v1",
        model="qwen-max",
        is_local=False,
        allow_sensitive=False,
    )
    state.model_configs["cfg-cloud-qwen"] = cloud_config
    state.project_model_configs["alpha-project"] = "cfg-cloud-qwen"

    # 尝试组装或启动生成，应被 403 门禁阻断
    with pytest.raises(DomainError) as exc_info:
        assemble_writing_prompt_plan(state, "alpha-project", "alpha-tech")
    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 更换为合规的本地离线模型
    local_config = ModelConfig(
        id="cfg-local-ollama",
        company_id="alpha",
        name="内网本地Qwen",
        provider="local",
        base_url="http://127.0.0.1:11434/v1",
        model="qwen2.5:14b",
        is_local=True,
        allow_sensitive=True,
    )
    state.model_configs["cfg-local-ollama"] = local_config
    state.project_model_configs["alpha-project"] = "cfg-local-ollama"

    # 再次组装，成功通过
    res = assemble_writing_prompt_plan(state, "alpha-project", "alpha-tech")
    assert res["project_id"] == "alpha-project"
    assert "token_budget_usage" in res


# ==============================================================================
# 9. 端到端写作计划组装完整性
# ==============================================================================
def test_assemble_writing_prompt_plan_end_to_end_integration(budget_env):
    env = budget_env
    plan_data = env["chapter_gen_service"].assemble_writing_prompt_plan(
        "alpha-project",
        "alpha-tech",
        principal=env["lead_principal"],
        max_context_tokens=4096,
    )

    # 验证核心返回结构
    assert "prompt" in plan_data
    assert "token_budget_usage" in plan_data
    assert "context_fingerprint" in plan_data
    assert "missing_variables" in plan_data
    assert "has_missing_variables" in plan_data
    assert "truncated_items_count" in plan_data
    assert "truncated_items" in plan_data
    assert "retained_counts" in plan_data

    # 验证 Token 预算指标
    usage = plan_data["token_budget_usage"]
    assert usage["max_context_tokens"] == 4096
    assert usage["prompt_tokens"] > 0
    assert len(plan_data["context_fingerprint"]) == 16


# ==============================================================================
# 10. start_chapter_generation 异步任务与候选成果记录 Token 指标与指纹
# ==============================================================================
def test_start_chapter_generation_records_budget_and_fingerprint(budget_env):
    env = budget_env
    gen_result = env["chapter_gen_service"].start_chapter_generation(
        "alpha-project",
        "alpha-tech",
        principal=env["lead_principal"],
        sync_execute=True,
    )

    # 返回结构包含预算与指纹
    assert "token_budget_usage" in gen_result
    assert "context_fingerprint" in gen_result
    assert len(gen_result["context_fingerprint"]) == 16

    # 异步任务记录包含预算与指纹
    job = gen_result["job"]
    assert job["token_budget_usage"] is not None
    assert job["context_fingerprint"] == gen_result["context_fingerprint"]

    # 生成的候选包含预算与指纹
    cand = gen_result["candidate"]
    assert cand is not None
    assert cand["context_fingerprint"] == gen_result["context_fingerprint"]
    assert cand["token_budget_usage"] == gen_result["token_budget_usage"]
