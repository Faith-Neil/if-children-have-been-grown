# 为什么有这个文件：验证 TV-M0-T25 检索意图拆解、四库并发召回、metadata_condition 过滤与三源上下文配额截断。
from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from fake_ragflow_v1 import FakeRagflowV1
from icg.app.main import create_app
from icg.domain.technical_query_plan import plan_section_queries
from icg.domain.technical_rag import knowledge_prompt_block, rag_summary, retrieve_for_section
from test_reference_flow import login


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode()


def test_query_plan_llm_and_rule_fallback_build_model_and_history_filters():
    class JsonPlannerModel:
        def suggest(self, system, user, profile=None):
            assert "Model-X800" in user
            return json.dumps({
                "section_type": "emergency_plan",
                "tender_query": "故障分级 SLA 超时罚款",
                "history_queries": ["数据库 故障分级 应急响应流程 服务方案"],
                "product_queries": ["Model-X800 双活热备 秒级切换"],
                "manual_queries": ["Model-X800 应急切换 SOP 回滚步骤"],
                "fault_case_queries": ["数据库 高并发宕机 根因定位 案例"],
            }, ensure_ascii=False)

    plan = plan_section_queries(
        "故障分级与应急响应机制",
        breadcrumb="第四章 售后服务方案 / 4.2 故障分级与应急响应机制",
        points=["15分钟响应、2小时修复", "三级应急预案"],
        target_models=["Model-X800"],
        model=JsonPlannerModel(),
        use_llm=True,
    )
    assert plan.source == "model"
    assert plan.section_type == "emergency_plan"
    assert "Model-X800" in plan.product_queries[0]
    assert plan.product_metadata_condition == {
        "logic": "and",
        "conditions": [{"name": "model", "comparison_operator": "is", "value": "Model-X800"}],
    }
    # 真机实测 RAGFlow 1.0 负向算子不可靠，history 排他改为应用侧执行（_filter_history_hits），
    # 查询计划不再下发负向 metadata 条件
    assert not plan.history_metadata_condition["conditions"]

    # 模型超时回落规则拆解
    class TimeoutModel:
        def suggest(self, system, user, profile=None):
            raise TimeoutError("ollama busy")

    fallback = plan_section_queries(
        "故障分级与应急响应机制",
        points=["15分钟响应"],
        target_models=["Model-X800", "Model-S200"],
        model=TimeoutModel(),
        use_llm=True,
    )
    assert fallback.source == "rule"
    assert fallback.product_metadata_condition["logic"] == "or"
    assert len(fallback.product_metadata_condition["conditions"]) == 2


def test_four_library_concurrent_retrieval_filters_metadata_and_enforces_quota():
    fake = FakeRagflowV1()
    app = create_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False

    with TestClient(app) as client:
        admin = login(client, "alpha-company-admin")
        client.post(
            "/api/v1/kb-admin/pipelines/deploy",
            headers=admin,
            json={"kinds": ["history", "manuals", "fault_cases", "products"]},
        )

        # 1. 上传两条历史标书：一条可复用，一条标为 not_reusable（必须被 metadata_condition 过滤掉）
        client.post(
            "/api/v1/kb-admin/datasets/history/documents",
            headers=admin,
            json={
                "filename": "优质历史应急方案.docx",
                "content_base64": _b64("# 技术服务方案\n\n## 故障分级与应急响应\n按实施步骤建立一级、二级、三级故障分级响应流程，突发宕机应急处置预案，重大故障快速切换。" + "历史模板参考段落。" * 80),
                "metadata": {"reusability": "high", "content_role": "bidder_response"},
            },
        )
        client.post(
            "/api/v1/kb-admin/datasets/history/documents",
            headers=admin,
            json={
                "filename": "废弃不可复用历史稿.docx",
                "content_base64": _b64("# 废弃稿\n\n## 5.1 故障分级\n故障分级响应废弃无效内容[[BAD_HISTORY]]。"),
                "metadata": {"reusability": "not_reusable", "content_role": "bidder_response"},
            },
        )

        # 2. 上传两款不同型号产品参数：锁定 Model-X800 时，Model-Old999 不得混入
        client.post(
            "/api/v1/kb-admin/datasets/products/documents",
            headers=admin,
            json={
                "filename": "X800白皮书.md",
                "content_base64": _b64("# X800白皮书\n\n## 高可用能力\nModel-X800 技术参数：原生双活热备与高可用能力，故障自动切换，RTO小于10秒。"),
                "metadata": {"model": "Model-X800"},
            },
        )
        client.post(
            "/api/v1/kb-admin/datasets/products/documents",
            headers=admin,
            json={
                "filename": "Old999白皮书.md",
                "content_base64": _b64("# Old999白皮书\n\n## 高可用能力\nModel-Old999 故障切换需人工停机4小时[[WRONG_MODEL]]。"),
                "metadata": {"model": "Model-Old999"},
            },
        )

        # 3. 上传运维手册与故障案例
        client.post(
            "/api/v1/kb-admin/datasets/manuals/documents",
            headers=admin,
            json={
                "filename": "X800运维手册V3.md",
                "content_base64": _b64("# Model-X800 运维手册\n\n## 故障应急SOP\n操作流程：执行 health_check 巡检规范 SOP 核验集群状态，故障分级应急处置并保存切换日志。"),
                "metadata": {"model": "Model-X800"},
            },
        )
        client.post(
            "/api/v1/kb-admin/datasets/fault_cases/documents",
            headers=admin,
            json={
                "filename": "高并发节点宕机案例.md",
                "content_base64": _b64("# Model-X800 故障案例\n\n## 突发宕机应急处置\n故障排查与根因定位：连接池耗尽触发主备切换；应急处置：隔离慢SQL并自动漂移VIP。"),
                "metadata": {"product_model": "Model-X800", "fault_category": "高可用切换故障"},
            },
        )

        workflow = {
            "global_fact_sheet_snapshot": {
                "project_name": "政务云核心库维保",
                "client_name": "星河大数据局",
                "target_models": ["Model-X800"],
            },
            "files": {"f1": {"pages": ["服务要求：故障分级响应需满足15分钟响应，超时每次扣罚2000元。"]}},
        }
        chunks, audit = retrieve_for_section(
            kb,
            "alpha",
            "故障分级与应急响应",
            workflow,
            breadcrumb="4 售后服务 / 4.2 故障分级与应急响应",
            points=["故障分级响应", "突发宕机应急处置"],
        )
        assert audit["history_hits"] == 1
        assert audit["product_hits"] == 1
        assert audit["manual_hits"] == 1
        assert audit["fault_case_hits"] == 1
        assert audit["material_hits"] == 3

        summary = rag_summary(audit)
        assert summary["status"] == "hit"
        assert (summary["product_hits"], summary["manual_hits"], summary["fault_case_hits"]) == (1, 1, 1)

        rendered = knowledge_prompt_block(chunks, workflow)
        assert "[[BAD_HISTORY]]" not in rendered
        assert "[[WRONG_MODEL]]" not in rendered
        assert "[来源：kb_products | 型号：Model-X800]" in rendered
        assert "[来源：kb_manuals | 型号：Model-X800]" in rendered
        assert "[来源：kb_fault_cases | 型号：Model-X800 | 分类：高可用切换故障]" in rendered


def test_metadata_condition_fallback_relaxes_model_then_doc_type():
    """带型号 metadata_condition 零命中时逐级放宽：精确型号 → 型号变体 OR → doc_type 级 → 不过滤。"""
    from icg.domain.technical_rag import _call_kb_search

    class _StubKb:
        def __init__(self):
            self.conditions = []

        def search(self, company_id, query, *, limit, kinds, metadata_condition=None, max_chunks_per_doc=2):
            self.conditions.append(metadata_condition)
            names = {c.get("name") for c in (metadata_condition or {}).get("conditions", [])}
            if "model" in names:
                return [], "empty"
            hit = type("H", (), {"source_id": "s1", "name": "X800手册", "content": "参数", "score": 0.9,
                                 "document_id": "d1", "chunk_ids": ["c1"], "cite_tag": "", "meta_fields": {},
                                 "dataset_kind": "manuals", "reference_only": False})()
            return [hit], ""

    kb = _StubKb()
    hits, _ = _call_kb_search(
        kb, "alpha", "巡检", limit=3, kinds={"manuals"},
        metadata_condition={"logic": "and", "conditions": [
            {"name": "model", "comparison_operator": "is", "value": "Model-X800"}]},
    )
    assert hits
    assert len(kb.conditions) == 3
    assert kb.conditions[0]["conditions"][0]["value"] == "Model-X800"
    variants = {c["value"] for c in kb.conditions[1]["conditions"]}
    assert kb.conditions[1]["logic"] == "or" and "X800" in variants
    assert kb.conditions[2]["conditions"][0]["name"] == "doc_type"
    assert kb.conditions[2]["conditions"][0]["value"] == "manual"


def test_metadata_condition_fallback_never_drops_history_exclusions():
    """history 的 not_reusable/buyer_requirement 排他条件是安全底线，零命中也不放宽。"""
    from icg.domain.technical_rag import _call_kb_search

    class _EmptyKb:
        def __init__(self):
            self.calls = 0

        def search(self, company_id, query, *, limit, kinds, metadata_condition=None, max_chunks_per_doc=2):
            self.calls += 1
            return [], "empty"

    kb = _EmptyKb()
    hits, _ = _call_kb_search(
        kb, "alpha", "运维方案", limit=3, kinds={"history"},
        metadata_condition={"logic": "and", "conditions": [
            {"name": "reusability", "comparison_operator": "not is", "value": "not_reusable"}]},
    )
    assert hits == []
    assert kb.calls == 1

def _hit(name, score, kind, meta=None):
    return type("H", (), {"source_id": name, "name": name, "content": f"{name}内容", "score": score,
                          "document_id": f"d-{name}", "chunk_ids": [f"c-{name}"], "cite_tag": "",
                          "meta_fields": meta or {}, "dataset_kind": kind, "reference_only": kind == "history"})()


class _RouteStubKb:
    """按 kinds 分路返回预设命中；history 含一条 not_reusable 验证应用侧排他。"""

    def __init__(self, fail_kinds=frozenset()):
        self.fail_kinds = set(fail_kinds)

    def search(self, company_id, query, *, limit, kinds, metadata_condition=None, max_chunks_per_doc=2):
        kind = next(iter(kinds or {"materials"}))
        if kind in self.fail_kinds:
            raise TimeoutError("simulated concurrent timeout")
        if kind == "history":
            return [
                _hit("优质历史方案", 0.66, "history", {"reusability": "high"}),
                _hit("废弃历史稿", 0.62, "history", {"reusability": "not_reusable"}),
            ], ""
        if kind in ("manuals", "products", "fault_cases"):
            return [_hit(f"{kind}文档", 0.7, kind)], ""
        return [], "empty"


def test_route_audit_details_complete():
    """每路检索强制记录 status/raw/post/top_score/error_detail，不得静默。"""
    from icg.domain.technical_rag import retrieve_dual

    chunks, audit = retrieve_dual(_RouteStubKb(), "alpha", "巡检服务 月度巡检计划", limit=8)
    routes = audit.get("routes") or []
    assert routes, "审计必须携带分路明细"
    for detail in routes:
        for key in ("route", "status", "raw_hits", "post_filter_hits", "top_score", "error_detail"):
            assert key in detail, f"缺少审计字段 {key}"
        assert detail["status"] in ("ok", "empty", "filtered_empty", "error")
    assert "history" in {d["route"] for d in routes}


def test_route_audit_records_error():
    """并发检索异常显式记录 error 状态与 error_detail，不得静默吞错。"""
    from icg.domain.technical_rag import retrieve_dual

    _chunks, audit = retrieve_dual(_RouteStubKb(fail_kinds={"history"}), "alpha", "巡检服务", limit=8)
    history_detail = next(d for d in audit["routes"] if d["route"] == "history")
    assert history_detail["status"] == "error"
    assert "TimeoutError" in history_detail["error_detail"]


def test_history_overfetch_survives_filtering():
    """history 超额召回 + 应用侧排他：not_reusable 丢弃后仍有余量，过滤后不归零。"""
    from icg.domain.technical_rag import retrieve_dual

    _chunks, audit = retrieve_dual(_RouteStubKb(), "alpha", "巡检服务 实施方案", limit=8)
    history_detail = next(d for d in audit["routes"] if d["route"] == "history")
    assert history_detail["raw_hits"] == 2
    assert history_detail["dropped"] == 1
    assert history_detail["post_filter_hits"] == 1
    assert history_detail["status"] == "ok"
    assert audit.get("history_excluded") == 1
