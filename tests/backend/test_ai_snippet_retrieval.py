# 为什么有这个文件：自动化测试 AI-SNIPPET-RETRIEVAL-MATCH 方案片段智能检索与上下文精准匹配服务。
# 它解决什么问题：
# 1. 验证多租户强隔离：只召回本 company_id 下已发布的方案片段，严禁跨租户越界召回；
# 2. 验证相关度匹配与排序：综合字块碎片重合度、关键词命中与向量相似度加权排序；
# 3. 验证项目事实表自动对齐与变量占位符填充：{{project_name}}, {{service_period}}, {{sla_availability}} 等精准替换；
# 4. 验证未对齐变量识别与 missing_variables 告警；
# 5. 验证出处防虚构与 .cite 溯源：生成 [片:snippet_id] 引用标记、16位 SHA-256 不可篡改防伪指纹及元数据；
# 6. 验证涉密项目本地模型门禁：敏感项目绑定云端模型强拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL；
# 7. 验证 RAGFlow 外部服务异常时优雅降级为本地内存检索；
# 8. 验证 FastAPI HTTP 端点认证与租户隔离。

from __future__ import annotations

import hashlib
import pytest
from fastapi.testclient import TestClient

from icg.domain.domain import DemoService, DemoState, DomainError, Principal
from icg.infra.model_config_storage import ModelConfig
from icg.domain.parsing import LocalTextParser
from icg.domain.snippet_publication import MemorySnippetPublicationStore
from icg.domain.snippet_retrieval import (
    SnippetRetrievalService,
    align_and_render_snippet_variables,
    compute_snippet_fingerprint,
    extract_project_facts_map,
    format_snippets_for_prompt,
)
from icg.domain.workflow_orchestrator import WorkflowService
from icg.infra.adapters import MemoryRepository, seed_state
from icg.infra.retrieval import SnippetCandidateMatch, SnippetRecord, SnippetRetriever
from icg_demo.main import create_app


@pytest.fixture
def repo():
    return MemoryRepository(seed_state())


@pytest.fixture
def demo(repo):
    return DemoService(repo, None)


@pytest.fixture
def parser():
    return LocalTextParser()


@pytest.fixture
def workflow(demo, parser):
    return WorkflowService(demo, parser)


@pytest.fixture
def snippet_store(demo):
    store = MemorySnippetPublicationStore(clock=demo._now)
    demo.snippet_publications = store
    return store


@pytest.fixture
def setup_context(repo, demo, snippet_store):
    def seed(st: DemoState):
        st.sessions.update({
            "token-alpha-manager": "alpha-manager",
            "token-alpha-editor": "alpha-editor",
            "token-beta-editor": "beta-editor",
        })
        # 为 alpha 项目补充事实
        wf = st.workflows.setdefault("alpha-project", {})
        wf.setdefault("facts", {
            "fact-001": {
                "id": "fact-001",
                "key": "服务期限",
                "value": "36",
                "unit": "个月",
                "status": "confirmed",
                "sla_var_key": "service_period",
            },
            "fact-002": {
                "id": "fact-002",
                "key": "项目预算",
                "value": "500",
                "unit": "万元",
                "status": "confirmed",
                "sla_var_key": None,
            },
        })
        wf.setdefault("sla", {
            "availability": "99.99%",
            "response_time": "15分钟",
            "recovery_time": "2小时",
        })
        # 补充章节评分项
        wf.setdefault("requirements", {
            "req-001": {
                "id": "req-001",
                "chapter_id": "alpha-tech",
                "text": "投标人需提供完善的数据库高可用与日常巡检方案，确保业务不中断。",
                "status": "confirmed",
                "volume": "tech",
                "evidence_ids": [],
            }
        })
    repo.transaction(seed)

    state = repo.read()
    principal_alpha = Principal(state.accounts["alpha-editor"], "token-alpha-editor")
    principal_beta = Principal(state.accounts["beta-editor"], "token-beta-editor")

    # 创建方案片段：
    # 片段 1：Alpha 已发布高可用方案（匹配度高，含变量）
    snip1 = snippet_store.create("alpha", {
        "product": "星河企业级数据库高可用保障方案",
        "snippet_type": "技术架构与安全方案",
        "variables": ["project_name", "service_period", "sla_availability"],
        "source_group": "数据库架构白皮书",
        "draft_body": "针对 {{project_name}}，我司提供主备集群容灾方案。承诺服务期限 {{service_period}} 内系统可用率达到 {{sla_availability}}。",
    })
    snippet_store.publish("alpha", snip1["id"], 1)

    # 片段 2：Alpha 已发布日常运维巡检方案
    snip2 = snippet_store.create("alpha", {
        "product": "数据库日常运维巡检与应急保障",
        "snippet_type": "运维服务方案",
        "variables": ["project_name", "onsite_frequency"],
        "source_group": "运维手册",
        "draft_body": "我司针对 {{project_name}} 开展常态化日常巡检，巡检周期为每月1次，需现场工程师 {{onsite_frequency}} 次/周。",
    })
    snippet_store.publish("alpha", snip2["id"], 1)

    # 片段 3：Alpha 草稿（未发布，published_revision == 0）
    snip3 = snippet_store.create("alpha", {
        "product": "草稿未发布方案",
        "snippet_type": "技术草案",
        "variables": ["project_name"],
        "source_group": "草稿组",
        "draft_body": "这是未发布的草案，不得对外召回 {{project_name}}。",
    })

    # 片段 4：Beta 公司的已发布方案（异企租户）
    snip4 = snippet_store.create("beta", {
        "product": "Beta专属机密高可用方案",
        "snippet_type": "技术方案",
        "variables": ["project_name"],
        "source_group": "Beta机密",
        "draft_body": "Beta租户私有方案，严禁 Alpha 访问 {{project_name}}。",
    })
    snippet_store.publish("beta", snip4["id"], 1)

    return {
        "repo": repo,
        "demo": demo,
        "workflow": workflow,
        "snippet_store": snippet_store,
        "principal_alpha": principal_alpha,
        "principal_beta": principal_beta,
        "snip1_id": snip1["id"],
        "snip2_id": snip2["id"],
        "snip3_id": snip3["id"],
        "snip4_id": snip4["id"],
    }


def test_multi_tenant_isolation_only_published_own_company_recalled(setup_context):
    """1. 验证多租户强隔离：只召回本 company_id 下已发布方案片段，严禁跨租户与未发布草案泄露。"""
    svc = SnippetRetrievalService(setup_context["demo"])
    principal_alpha = setup_context["principal_alpha"]

    result = svc.match_snippets(
        principal=principal_alpha,
        project_id="alpha-project",
        query="数据库高可用保障",
        min_score=0.01,
    )

    matched_ids = [item["snippet_id"] for item in result["items"]]
    assert setup_context["snip1_id"] in matched_ids
    # 未发布的草稿 snip3 严禁召回
    assert setup_context["snip3_id"] not in matched_ids
    # 异企租户 beta 的 snip4 严禁召回
    assert setup_context["snip4_id"] not in matched_ids
    for item in result["items"]:
        assert item["company_id"] == "alpha"
        assert item["published_revision"] > 0


def test_cross_tenant_project_access_rejected(setup_context):
    """2. 验证越权访问拦截：租户不能访问其他公司的项目进行方案检索（404 隔离）。"""
    svc = SnippetRetrievalService(setup_context["demo"])
    principal_beta = setup_context["principal_beta"]

    # Beta 企图访问 Alpha 的项目
    with pytest.raises(DomainError) as exc_info:
        svc.match_snippets(
            principal=principal_beta,
            project_id="alpha-project",
            query="数据库高可用",
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"

    # 不存在的项目
    with pytest.raises(DomainError) as exc_info2:
        svc.match_snippets(
            principal=setup_context["principal_alpha"],
            project_id="non-existent-project",
            query="方案检索",
        )
    assert exc_info2.value.status == 404


def test_relevance_matching_and_scoring(setup_context):
    """3. 验证相关度精准匹配与排序：高相关度片段排在前面，并归一化为 0.0 ~ 1.0 得分。"""
    svc = SnippetRetrievalService(setup_context["demo"])
    principal = setup_context["principal_alpha"]

    # 针对数据库高可用查询
    result = svc.match_snippets(
        principal=principal,
        project_id="alpha-project",
        chapter_id="alpha-tech",
        query="高可用保障主备容灾",
    )

    assert result["total_matched"] >= 1
    first_hit = result["items"][0]
    assert first_hit["snippet_id"] == setup_context["snip1_id"]
    assert 0.0 <= first_hit["score"] <= 1.0
    assert first_hit["score"] > 0.3


def test_variable_extraction_and_project_facts_alignment(setup_context):
    """4. 验证项目事实表自动对齐与变量占位符填充：{{project_name}}, {{service_period}}, {{sla_availability}}。"""
    svc = SnippetRetrievalService(setup_context["demo"])
    principal = setup_context["principal_alpha"]

    result = svc.match_snippets(
        principal=principal,
        project_id="alpha-project",
        query="数据库高可用",
    )

    snip1_match = next(it for it in result["items"] if it["snippet_id"] == setup_context["snip1_id"])

    # 验证变量抽取与对齐
    matched_vars = snip1_match["matched_variables"]
    assert "project_name" in matched_vars
    assert matched_vars["service_period"] == "36个月"

    # 验证渲染后正文不再包含已匹配的变量括号
    rendered = snip1_match["rendered_body"]
    assert "{{service_period}}" not in rendered
    assert "36个月" in rendered
    assert snip1_match["missing_variables"] == []


def test_missing_variables_detection(setup_context):
    """5. 验证缺失变量识别：声明或使用了未录入事实库的变量时，如实标入 missing_variables 并保留占位。"""
    svc = SnippetRetrievalService(setup_context["demo"])
    principal = setup_context["principal_alpha"]

    result = svc.match_snippets(
        principal=principal,
        project_id="alpha-project",
        query="日常运维巡检",
    )

    snip2_match = next(it for it in result["items"] if it["snippet_id"] == setup_context["snip2_id"])
    assert "onsite_frequency" in snip2_match["missing_variables"]
    # 渲染正文中保留了未对齐的占位符，防止虚构
    assert "{{onsite_frequency}}" in snip2_match["rendered_body"]
    assert result["has_missing_variables"] is True


def test_cite_tag_and_anti_tamper_fingerprint(setup_context):
    """6. 验证出处防虚构与 .cite 溯源：标准 [片:ID] 引用标记、16位防伪指纹与元数据。"""
    svc = SnippetRetrievalService(setup_context["demo"])
    principal = setup_context["principal_alpha"]

    result = svc.match_snippets(
        principal=principal,
        project_id="alpha-project",
        query="数据库高可用",
    )

    item = result["items"][0]
    expected_cite_tag = f"[片:{item['snippet_id']}]"
    assert item["cite_tag"] == expected_cite_tag
    assert len(item["fingerprint"]) == 16
    assert isinstance(item["cite_metadata"], dict)
    assert item["cite_metadata"]["tag"] == expected_cite_tag
    assert item["cite_metadata"]["fingerprint"] == item["fingerprint"]
    assert item["cite_metadata"]["status"] == "published"

    # 验证格式化 Prompt 工具
    prompt_context = format_snippets_for_prompt(result["items"])
    assert expected_cite_tag in prompt_context
    assert item["fingerprint"] in prompt_context
    assert "【已核验本公司方案片段依据（严禁虚构未提及内容）】" in prompt_context


def test_sensitive_project_blocks_cloud_model(setup_context):
    """7. 验证涉密项目本地模型门禁：敏感项目若绑定云端模型，强拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
    repo = setup_context["repo"]
    svc = SnippetRetrievalService(setup_context["demo"])
    principal = setup_context["principal_alpha"]

    # 标记为涉密项目并绑定云端模型
    def make_cloud(s: DemoState):
        s.projects["alpha-project"].sensitive = True
        cloud_cfg = ModelConfig(
            id="cloud-model-01",
            company_id="alpha",
            name="公有云大模型",
            provider="openai-compatible",
            base_url="https://api.openai.com/v1",
            is_local=False,
            allow_sensitive=False,
        )
        s.model_configs["cloud-model-01"] = cloud_cfg
        s.project_model_configs["alpha-project"] = "cloud-model-01"
    repo.transaction(make_cloud)

    with pytest.raises(DomainError) as exc_info:
        svc.match_snippets(
            principal=principal,
            project_id="alpha-project",
            query="方案检索",
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 改绑本地模型后放行
    def make_local(s: DemoState):
        local_cfg = ModelConfig(
            id="local-model-01",
            company_id="alpha",
            name="内网离线Qwen",
            provider="openai-compatible",
            base_url="http://127.0.0.1:8000/v1",
            is_local=True,
            allow_sensitive=True,
        )
        s.model_configs["local-model-01"] = local_cfg
        s.project_model_configs["alpha-project"] = "local-model-01"
    repo.transaction(make_local)

    res = svc.match_snippets(
        principal=principal,
        project_id="alpha-project",
        query="数据库高可用",
    )
    assert res["total_matched"] >= 1


def test_retriever_degrades_gracefully_when_ragflow_fails(setup_context):
    """8. 验证 RAGFlow 外部服务异常时优雅降级为本地内存检索。"""
    class BrokenRagflowClient:
        def retrieve(self, *args, **kwargs):
            raise RuntimeError("RAGFlow cluster connection timed out")

    broken_retriever = SnippetRetriever(ragflow_client=BrokenRagflowClient())
    svc = SnippetRetrievalService(setup_context["demo"], retriever=broken_retriever)

    # 在 RAGFlow 抛出异常时，本地内存检索不受影响，依然能返回匹配结果
    res = svc.match_snippets(
        principal=setup_context["principal_alpha"],
        project_id="alpha-project",
        query="数据库高可用",
    )
    assert res["total_matched"] >= 1
    assert res["items"][0]["snippet_id"] == setup_context["snip1_id"]


def test_http_endpoint_match_snippets(setup_context):
    """9. 验证 FastAPI HTTP 端点 POST /api/v1/projects/{project_id}/snippets/match。"""
    demo = setup_context["demo"]
    app = create_app(repository=demo.repository)
    app.state.snippet_publications = setup_context["snippet_store"]
    app.state.service.snippet_publications = setup_context["snippet_store"]
    client = TestClient(app)

    # 1. 未登录 -> 401
    unauth_res = client.post("/api/v1/projects/alpha-project/snippets/match", json={"query": "数据库"})
    assert unauth_res.status_code == 401

    # 2. 跨租户 -> 404
    cross_res = client.post(
        "/api/v1/projects/alpha-project/snippets/match",
        headers={"Authorization": "Bearer token-beta-editor"},
        json={"query": "数据库"},
    )
    assert cross_res.status_code == 404

    # 3. 正常检索 -> 200
    ok_res = client.post(
        "/api/v1/projects/alpha-project/snippets/match",
        headers={"Authorization": "Bearer token-alpha-editor"},
        json={
            "chapter_id": "alpha-tech",
            "query": "数据库高可用",
            "limit": 3,
        },
    )
    assert ok_res.status_code == 200
    data = ok_res.json()
    assert data["project_id"] == "alpha-project"
    assert data["total_matched"] >= 1
    assert len(data["items"]) <= 3
    assert data["items"][0]["cite_tag"].startswith("[片:")


def test_fact_and_sla_alias_variations_alignment(setup_context):
    """10. 验证多格式变量占位符对齐：{{fact:ID}}, {{sla:KEY}}, 中文别名。"""
    body = "承诺 {{sla:service_period}} 内达标，依据原件 {{fact:fact-001}}，系统可用性保证 {{系统可用性}}。"
    declared = ["sla:service_period", "fact:fact-001", "系统可用性"]
    state = setup_context["repo"].read()
    facts_map = extract_project_facts_map(state, "alpha-project")

    rendered, matched, missing = align_and_render_snippet_variables(body, declared, facts_map)
    assert matched["sla:service_period"] == "36个月"
    assert matched["fact:fact-001"] == "36个月"
    assert matched["系统可用性"] == "99.99%"
    assert missing == []
    assert "36个月" in rendered
    assert "99.99%" in rendered


def test_ragflow_cross_tenant_chunk_rejected(setup_context):
    """11. 验证 RAGFlow 数据集隔离：若底层返回越界数据集分块，严格触发 RetrievalError 阻断。"""
    from icg.infra.ragflow_client import RagflowChunk, RagflowRetrievalResult
    from icg.infra.retrieval import RetrievalError

    class RogueRagflowClient:
        def retrieve(self, *args, **kwargs):
            return RagflowRetrievalResult(
                chunks=[
                    RagflowChunk(
                        id="rogue-chunk-1",
                        content="跨租户泄露的内容",
                        dataset_id="other_company::ds_01",
                        document_id="doc-99",
                        similarity=0.9,
                    )
                ],
                doc_aggs=[],
                total=1,
            )

    rogue_retriever = SnippetRetriever(ragflow_client=RogueRagflowClient())
    with pytest.raises(RetrievalError) as exc_info:
        rogue_retriever.retrieve(
            company_id="alpha",
            query="数据库方案",
            dataset_ids=["alpha::ds_01"],
        )
    assert "outside tenant namespace" in str(exc_info.value)

