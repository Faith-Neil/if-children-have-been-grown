# 为什么有这个文件：针对大纲多章节批量生成流水线调度引擎的独立自动化测试套件（AI-OUTLINE-BATCH-GENERATION-PIPELINE）。
# 它解决什么问题：
# 1. 优先级推荐队列排序与并发批次切片：验证一票否决红线/★星标条款/高分章节优先调度，并发门限（concurrency_limit: 1~5）严格批次切片；
# 2. PRD §5.7.8 绝对红线：未确认章节（PLAN_NOT_CONFIRMED）或单章失败绝对不阻塞其他章节调度生成（skipped_unconfirmed_chapters，partial_completed）；
# 3. 优先级门限过滤（priority_threshold: critical/high/medium/low）；
# 4. 全局 Token 消耗仪表盘与执行耗时聚合（duration_ms, token_budget_dashboard, priority_execution_summary）；
# 5. 多租户强隔离（跨企业 404 NOT_FOUND）；
# 6. RBAC 权限门禁（只读角色 403 FORBIDDEN / PROJECT_WRITER_REQUIRED）；
# 7. 涉密项目本地模型硬门禁（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）；
# 8. HTTP API 端点集成（POST /api/v1/projects/{project_id}/outline/batch-pipeline）。

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
            "[P1] 本项目采用微服务与高可用架构[证:ev-iso9001]，严格遵循质量管理体系要求。\n\n"
            "### 2. 数据库主从高可用与双活保障\n"
            "[P2] 生产数据库采用主从同步与双活设计[片:rag-chunk-01]，故障切换时间小于 {{fact:fact-rto}} 秒。\n\n"
            "### 3. 应急响应机制\n"
            "[P3] 建立 7x24 小时应急运维体系，提供 {{fact:fact-service-term}} 的长效支持。"
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
        return "云端模型建议"


@pytest.fixture
def test_env():
    state = seed_state()
    project = state.projects["alpha-project"]
    project.deadline = "2026-12-31T17:00:00+08:00"
    project.sensitive = False

    # 清空 demo 默认的 alpha-tech / alpha-business 章节，使用干净的 6 个被测章节
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
                    "第一页：招标基本要求。\n服务期限：36个月。\n恢复时间目标RTO：30秒。",
                    "第二页：技术指标要求：投标人需具备成熟的数据库高可用方案与应急响应体系",
                ],
            }
        },
        "requirements": {
            "req-disq": {
                "id": "req-disq",
                "volume": "technical",
                "chapter_id": "ch-disq",
                "text": "投标人不满足国家等保三级认证者一票否决废标",
                "disqualified": True,
                "importance": "star",
                "category": "security",
                "score": 0.0,
                "status": "confirmed",
                "response": "满足等保要求",
                "evidence_ids": ["ev-iso9001"],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "投标人不满足国家等保三级认证者一票否决废标",
                },
            },
            "req-star": {
                "id": "req-star",
                "volume": "technical",
                "chapter_id": "ch-star",
                "text": "★ 系统须提供跨机房高可用双活容灾方案",
                "asterisk": True,
                "importance": "star",
                "category": "technical",
                "score": 20.0,
                "status": "confirmed",
                "response": "提供双活方案",
                "evidence_ids": ["ev-iso9001"],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 2,
                    "quote": "★ 系统须提供跨机房高可用双活容灾方案",
                },
            },
            "req-high": {
                "id": "req-high",
                "volume": "technical",
                "chapter_id": "ch-high",
                "text": "系统总体技术拓扑与分布式架构",
                "category": "technical",
                "score": 30.0,
                "status": "confirmed",
                "response": "提供微服务拓扑",
                "evidence_ids": ["ev-iso9001"],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 2,
                    "quote": "系统总体技术拓扑与分布式架构",
                },
            },
            "req-med": {
                "id": "req-med",
                "volume": "business",
                "chapter_id": "ch-med",
                "text": "近三年审计财务状况良好",
                "category": "commercial",
                "score": 15.0,
                "status": "confirmed",
                "response": "审计良好",
                "evidence_ids": [],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "近三年审计财务状况良好",
                },
            },
            "req-low1": {
                "id": "req-low1",
                "volume": "business",
                "chapter_id": "ch-low1",
                "text": "法定代表人身份合规证明",
                "category": "commercial",
                "score": 5.0,
                "status": "confirmed",
                "response": "合规",
                "evidence_ids": [],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "法定代表人身份合规证明",
                },
            },
            "req-low2": {
                "id": "req-low2",
                "volume": "business",
                "chapter_id": "ch-low2",
                "text": "日常办公场所证明",
                "category": "commercial",
                "score": 2.0,
                "status": "confirmed",
                "response": "提供证明",
                "evidence_ids": [],
                "source": {
                    "file_id": "file-tender-01",
                    "page": 1,
                    "quote": "日常办公场所证明",
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
        "chapter_order": ["ch-disq", "ch-star", "ch-high", "ch-med", "ch-low1", "ch-low2"],
        "recommended_writing_order": [
            {"chapter_id": "ch-disq", "title": "等保三级一票否决合规", "priority": "critical", "priority_score": 100.0, "total_score": 0.0, "section_number": "1.1"},
            {"chapter_id": "ch-star", "title": "★高可用双活容灾方案", "priority": "critical", "priority_score": 80.0, "total_score": 20.0, "section_number": "1.2"},
            {"chapter_id": "ch-high", "title": "系统总体微服务架构", "priority": "high", "priority_score": 45.0, "total_score": 30.0, "section_number": "1.3"},
            {"chapter_id": "ch-med", "title": "财务审计与资产负债", "priority": "medium", "priority_score": 22.5, "total_score": 15.0, "section_number": "2.1"},
            {"chapter_id": "ch-low1", "title": "法人身份合规证明", "priority": "low", "priority_score": 7.5, "total_score": 5.0, "section_number": "2.2"},
            {"chapter_id": "ch-low2", "title": "办公场所与设施说明", "priority": "low", "priority_score": 3.0, "total_score": 2.0, "section_number": "2.3"},
        ],
        "writing_plan": {
            "confirmed_by": "alpha-manager",
            "confirmed_at": "2026-10-21T10:00:00+08:00",
            "chapters": {},
        },
    }
    state.workflows["alpha-project"] = wf

    # 创建 6 个章节
    chapters_meta = [
        ("ch-disq", "1.1", "等保三级一票否决合规", "technical"),
        ("ch-star", "1.2", "★高可用双活容灾方案", "technical"),
        ("ch-high", "1.3", "系统总体微服务架构", "technical"),
        ("ch-med", "2.1", "财务审计与资产负债", "business"),
        ("ch-low1", "2.2", "法人身份合规证明", "business"),
        ("ch-low2", "2.3", "办公场所与设施说明", "business"),
    ]

    for cid, sec, title, vol in chapters_meta:
        chapter = Chapter(
            id=cid,
            project_id="alpha-project",
            title=title,
            volume=vol,
            content=f"这是 {title} 的初始草稿内容。",
            assignee_id="alpha-manager",
            revision=1,
        )
        state.chapters[cid] = chapter

        # 写入已确认写作计划
        plan = {
            "id": cid,
            "writing_points": [f"{title}要点一", f"{title}要点二"],
            "evidence_ids": ["ev-iso9001"],
            "fact_ids": ["fact-service-term", "fact-rto"],
            "custom_instructions": f"针对{title}的详尽方案编写。",
            "target_word_count": 1000,
            "confirmed_at": "2026-10-21T10:00:00+08:00",
            "confirmed_by": "alpha-manager",
        }
        wf["writing_plan"]["chapters"][cid] = plan
        plan["confirmed_input_fingerprint"] = writing_source_fingerprint(state, "alpha-project", cid)

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

    repo = MemoryRepository()
    repo.transaction(lambda s: s.__dict__.update(state.__dict__))
    model_provider = MockLocalModelProvider()
    demo = DemoService(repo, model_provider)

    return {
        "repo": repo,
        "demo": demo,
        "model_provider": model_provider,
        "principals": {
            "manager": Principal(state.accounts["alpha-manager"], "tok-alpha-manager"),
            "editor": Principal(state.accounts["alpha-editor"], "tok-alpha-editor"),
            "viewer": Principal(state.accounts["alpha-viewer"], "tok-alpha-viewer"),
            "outsider": Principal(state.accounts["beta-editor"], "tok-beta-editor"),
        },
    }


# ==================== 1. 优先级推荐队列排序与并发批次切片 ====================

def test_batch_pipeline_priority_sorting_and_slicing(test_env):
    """验证大纲批量生成流水线根据综合优先级调度，并按并发门限严格分批。"""
    demo = test_env["demo"]
    manager = test_env["principals"]["manager"]

    # 6个章节，并发限制为 2 -> 应切分为 3 个批次
    result = demo.schedule_batch_pipeline(
        project_id="alpha-project",
        principal=manager,
        concurrency_limit=2,
        sync_execute=True,
    )

    assert result["project_id"] == "alpha-project"
    assert result["pipeline_status"] == "completed"
    assert result["concurrency_limit"] == 2
    assert result["total_chapters_scheduled"] == 6
    assert result["total_batches"] == 3
    assert len(result["skipped_unconfirmed_chapters"]) == 0

    batches = result["batches"]
    assert len(batches) == 3

    # 批次 0 必须包含一票否决(ch-disq)与★星标必保(ch-star)——最紧急关键优先级
    stage_0_cids = batches[0]["chapter_ids"]
    assert len(stage_0_cids) == 2
    assert stage_0_cids == ["ch-disq", "ch-star"]
    assert batches[0]["status"] == "completed"

    # 批次 1 应为高分值技术架构(ch-high: 30分)与中分值财务(ch-med: 15分)
    stage_1_cids = batches[1]["chapter_ids"]
    assert len(stage_1_cids) == 2
    assert stage_1_cids == ["ch-high", "ch-med"]
    assert batches[1]["status"] == "completed"

    # 批次 2 应为低分值章节(ch-low1: 5分, ch-low2: 2分)
    stage_2_cids = batches[2]["chapter_ids"]
    assert len(stage_2_cids) == 2
    assert stage_2_cids == ["ch-low1", "ch-low2"]
    assert batches[2]["status"] == "completed"

    # 优先级汇总字典统计
    priority_summary = result["priority_execution_summary"]
    assert priority_summary["critical"]["total"] == 2
    assert priority_summary["critical"]["succeeded"] == 2
    assert priority_summary["high"]["total"] == 1
    assert priority_summary["high"]["succeeded"] == 1
    assert priority_summary["medium"]["total"] == 1
    assert priority_summary["medium"]["succeeded"] == 1
    assert priority_summary["low"]["total"] == 2
    assert priority_summary["low"]["succeeded"] == 2

    # 验证候选结果全部正确生成并落盘至 candidates
    def check_candidates(state):
        candidates = state.workflows["alpha-project"]["candidates"]
        for cid in ["ch-disq", "ch-star", "ch-high", "ch-med", "ch-low1", "ch-low2"]:
            assert cid in candidates
            assert len(candidates[cid]["content"]) > 0
            assert "structured_content" in candidates[cid]
            assert "paragraphs" in candidates[cid]

    test_env["repo"].transaction(check_candidates)


# ==================== 2. PRD §5.7.8 绝对红线：未确认章节不阻塞其余章节调度 ====================

def test_batch_pipeline_unconfirmed_chapter_non_blocking(test_env):
    """PRD §5.7.8 绝对红线：未确认写作计划的章节必须跳过，绝不允许阻塞后续章节生成。"""
    demo = test_env["demo"]
    manager = test_env["principals"]["manager"]

    # 将 ch-high 设为未确认状态（移除 confirmed_at）
    def unconfirm_ch_high(state):
        wf = state.workflows["alpha-project"]
        wf["writing_plan"]["chapters"]["ch-high"]["confirmed_at"] = None

    test_env["repo"].transaction(unconfirm_ch_high)

    # 调度流水线
    result = demo.schedule_batch_pipeline(
        project_id="alpha-project",
        principal=manager,
        concurrency_limit=2,
        sync_execute=True,
    )

    # 流水线状态为 partial_completed
    assert result["pipeline_status"] == "partial_completed"

    # ch-high 必须记录在 skipped_unconfirmed_chapters 中
    skipped = result["skipped_unconfirmed_chapters"]
    assert len(skipped) == 1
    assert skipped[0]["chapter_id"] == "ch-high"
    assert skipped[0]["reason"] == "PLAN_NOT_CONFIRMED"
    assert skipped[0]["status"] == "skipped"

    # 其余 5 个章节必须全数调度并成功执行
    assert result["total_chapters_scheduled"] == 6
    assert result["succeeded_count"] == 5
    assert result["skipped_unconfirmed_count"] == 1

    # 检查 candidates，除 ch-high 外均有生成候选
    def check_candidates(state):
        candidates = state.workflows["alpha-project"]["candidates"]
        assert "ch-high" not in candidates
        assert "ch-disq" in candidates
        assert "ch-star" in candidates

    test_env["repo"].transaction(check_candidates)


# ==================== 3. 优先级门限过滤（priority_threshold） ====================

def test_batch_pipeline_priority_threshold_filtering(test_env):
    """验证按照 priority_threshold 仅调度指定优先级及以上的章节。"""
    demo = test_env["demo"]
    manager = test_env["principals"]["manager"]

    # 仅调度 critical 紧急红线章节
    result_critical = demo.schedule_batch_pipeline(
        project_id="alpha-project",
        principal=manager,
        priority_threshold="critical",
        concurrency_limit=2,
        sync_execute=True,
    )

    assert result_critical["pipeline_status"] == "completed"
    assert result_critical["total_chapters_scheduled"] == 2
    critical_cids = [cid for b in result_critical["batches"] for cid in b["chapter_ids"]]
    assert set(critical_cids) == {"ch-disq", "ch-star"}

    # 调度 high（包含 critical 和 high）
    result_high = demo.schedule_batch_pipeline(
        project_id="alpha-project",
        principal=manager,
        priority_threshold="high",
        concurrency_limit=2,
        sync_execute=True,
    )
    high_cids = [cid for b in result_high["batches"] for cid in b["chapter_ids"]]
    assert set(high_cids) == {"ch-disq", "ch-star", "ch-high"}


# ==================== 4. 全局 Token 仪表盘与执行耗时聚合 ====================

def test_batch_pipeline_token_budget_and_metrics_aggregation(test_env):
    """验证批次生成耗时 duration_ms 与 token_budget_dashboard 正确汇聚。"""
    demo = test_env["demo"]
    manager = test_env["principals"]["manager"]

    result = demo.schedule_batch_pipeline(
        project_id="alpha-project",
        principal=manager,
        concurrency_limit=3,
        sync_execute=True,
    )

    # 耗时统计
    assert "duration_ms" in result
    assert result["duration_ms"] >= 0

    # Token 仪表盘
    dashboard = result["token_budget_dashboard"]
    assert "total_prompt_tokens" in dashboard
    assert "total_completion_tokens" in dashboard
    assert "total_tokens" in dashboard
    assert dashboard["total_tokens"] > 0
    assert "by_chapter" in dashboard
    assert len(dashboard["by_chapter"]) == 6

    # 验证工作流原子落盘记录
    def check_workflow_persistence(state):
        wf = state.workflows["alpha-project"]
        assert "batch_pipeline_runs" in wf
        assert len(wf["batch_pipeline_runs"]) == 1
        assert "latest_batch_pipeline_run" in wf
        latest = wf["latest_batch_pipeline_run"]
        assert latest["pipeline_id"] == result["pipeline_id"]
        assert latest["total_chapters_scheduled"] == 6

    test_env["repo"].transaction(check_workflow_persistence)


# ==================== 5. 并发门限边界保护 ====================

def test_batch_pipeline_concurrency_limit_boundaries(test_env):
    """验证 concurrency_limit 的上下限钳制 (1~5)。"""
    demo = test_env["demo"]
    manager = test_env["principals"]["manager"]

    # 传入 0 钳制为 1
    r_min = demo.schedule_batch_pipeline(
        project_id="alpha-project",
        principal=manager,
        concurrency_limit=0,
        sync_execute=False,
    )
    assert r_min["concurrency_limit"] == 1
    assert r_min["total_batches"] == 6  # 6个章节每个批次1个

    # 传入 100 钳制为 5
    r_max = demo.schedule_batch_pipeline(
        project_id="alpha-project",
        principal=manager,
        concurrency_limit=100,
        sync_execute=False,
    )
    assert r_max["concurrency_limit"] == 5
    assert r_max["total_batches"] == 2  # 6个章节，第一批5个，第二批1个


# ==================== 6. 多租户强隔离 ====================

def test_batch_pipeline_multi_tenant_isolation(test_env):
    """验证跨企业租户调用流水线时严密拦截并返回 404 NOT_FOUND。"""
    demo = test_env["demo"]
    outsider = test_env["principals"]["outsider"]  # beta-editor 属于 beta 公司

    with pytest.raises(DomainError) as exc_info:
        demo.schedule_batch_pipeline(
            project_id="alpha-project",
            principal=outsider,
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"


# ==================== 7. RBAC 权限门禁 ====================

def test_batch_pipeline_rbac_permission_gate(test_env):
    """验证只读角色 (viewer) 尝试触发流水线调度时拦截 403。"""
    demo = test_env["demo"]
    viewer = test_env["principals"]["viewer"]

    with pytest.raises(DomainError) as exc_info:
        demo.schedule_batch_pipeline(
            project_id="alpha-project",
            principal=viewer,
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"


# ==================== 8. 涉密项目本地模型硬门禁 ====================

def test_batch_pipeline_sensitive_project_local_model_gate(test_env):
    """验证涉密项目强制使用内网本地模型，云端外部模型硬阻断 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
    demo = test_env["demo"]
    manager = test_env["principals"]["manager"]

    # 标记项目为涉密
    def set_sensitive(state):
        state.projects["alpha-project"].sensitive = True
        for cid in ["ch-disq", "ch-star", "ch-high", "ch-med", "ch-low1", "ch-low2"]:
            state.workflows["alpha-project"]["writing_plan"]["chapters"][cid]["confirmed_input_fingerprint"] = writing_source_fingerprint(state, "alpha-project", cid)

    test_env["repo"].transaction(set_sensitive)

    # 注入云端非本地模型
    demo.model_provider = MockCloudModelProvider()

    with pytest.raises(DomainError) as exc_info:
        demo.schedule_batch_pipeline(
            project_id="alpha-project",
            principal=manager,
            sync_execute=True,
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 换回本地模型 -> 正常通行
    demo.model_provider = MockLocalModelProvider()
    res = demo.schedule_batch_pipeline(
        project_id="alpha-project",
        principal=manager,
        concurrency_limit=2,
        sync_execute=True,
    )
    assert res["pipeline_status"] == "completed"


# ==================== 9. HTTP API 端点集成 ====================

def test_batch_pipeline_http_api_endpoint(test_env):
    """验证 POST /api/v1/projects/{project_id}/outline/batch-pipeline HTTP 端点。"""
    app = FastAPI()
    demo = test_env["demo"]
    manager = test_env["principals"]["manager"]

    include_workflow_routes(app, demo, lambda: manager, DummyParser())
    client = TestClient(app)

    response = client.post(
        "/api/v1/projects/alpha-project/outline/batch-pipeline",
        json={
            "concurrency_limit": 3,
            "priority_threshold": "high",
            "sync_execute": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "alpha-project"
    assert data["pipeline_status"] == "completed"
    assert data["concurrency_limit"] == 3
    assert "token_budget_dashboard" in data
    assert "priority_execution_summary" in data
    assert len(data["batches"]) >= 1
