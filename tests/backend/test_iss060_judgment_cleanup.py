# 为什么有这个文件：核对 ISSUE-060 补缺链路——被分流（non_technical/fragment）条款上遗留的
# 系统假负偏离判断必须清理（合规 R09/R37 直接扫 deviation_type，不清理会继续阻断导出）；
# 存量项目重跑模型目录时，锁外清洗结果必须回写落盘（否则矩阵/偏离表仍面对未清洗旧行）。
from __future__ import annotations

import json

from icg.domain.technical_clause_cleaning import (
    clean_technical_requirements,
    clear_stale_judgment_fields,
)
from test_reference_flow import client, login  # noqa: F401


def _row(rid, text, kind="spec", **extra):
    row = {
        "id": rid, "text": text, "technical_clause": True, "status": "pending",
        "section_kind": kind, "source": {"page": 1, "quote": text, "file_id": "f1"},
    }
    row.update(extra)
    return row


def _fake_negative(row):
    """模拟 ISSUE-060 之前的存量假数据：商务/碎片条款被历史检索误判负偏离。"""
    row.update(
        response="负偏离。历史标书未覆盖该条款，无法满足。",
        response_type="deviate",
        deviation_type="negative",
        deviation_reason="历史无此做法",
        response_origin="history",
        history_filename="历史标书.docx",
        history_quote=" unrelated quote",
    )
    return row


# ---------------------------------------------------------------- 单元：系统判断清理
def test_clear_stale_judgment_wipes_system_negative_on_non_tech_row():
    row = _fake_negative(_row("r1", "投标报价不得高于最高限价"))
    clean_technical_requirements({"requirements": {"r1": row}})
    assert row["requirement_scope"] == "non_technical"
    assert row["response_type"] is None and row["deviation_type"] is None
    assert row["response"] == "" and row["response_origin"] == ""
    assert row["history_filename"] == ""


def test_clear_stale_judgment_wipes_system_negative_on_fragment_row():
    row = _fake_negative(_row("r1", "| 采用数据库", quote="毫无关系的锚点"))
    clean_technical_requirements({"requirements": {"r1": row}})
    assert row["requirement_scope"] == "fragment_filtered"
    assert row["deviation_type"] is None and row["response"] == ""


def test_clear_stale_judgment_preserves_confirmed_rows():
    row = _fake_negative(_row("r1", "投标报价不得高于最高限价", status="confirmed"))
    clean_technical_requirements({"requirements": {"r1": row}})
    # 已确认行由人工负责：范围照标，但系统不擅自清掉人工确认过的数据
    assert row["requirement_scope"] == "non_technical"
    assert row["deviation_type"] == "negative"


def test_clear_stale_judgment_preserves_manually_edited_rows():
    row = _fake_negative(_row("r1", "投标报价不得高于最高限价", manually_edited=True))
    clean_technical_requirements({"requirements": {"r1": row}})
    assert row["requirement_scope"] == "non_technical"
    assert row["deviation_type"] == "negative"


def test_technical_rows_keep_their_judgments():
    row = _row("r1", "每月巡检数据库并出具报告")
    row.update(response="无偏离。按本次招标文件响应。", response_type="comply",
               deviation_type="none", response_origin="history")
    clean_technical_requirements({"requirements": {"r1": row}})
    assert row["requirement_scope"] == "technical"
    assert row["response_type"] == "comply" and row["deviation_type"] == "none"


def test_clear_stale_judgment_direct_helper_guards():
    technical = _row("r1", "每月巡检数据库并出具报告")
    technical["deviation_type"] = "negative"
    assert clear_stale_judgment_fields(technical) is False  # 未排除的行不动
    excluded = _fake_negative(_row("r2", "需提供基本账户证明"))
    excluded["requirement_scope"] = "non_technical"
    assert clear_stale_judgment_fields(excluded) is True
    assert excluded["deviation_type"] is None
    # 幂等：再跑无改动
    assert clear_stale_judgment_fields(excluded) is False


def test_ordinal_heading_never_glued_into_frankenstein_sentence():
    """「第一条 服务内容与范围」是完整一行标题而非被截断的句子：跨行拼接只会把标题与
    下一条无关内容粘成拼接句（编造），必须宁可过滤（ISSUE-060 证据残句）。"""
    page = "第一条 服务内容与范围\n运维服务地点：重庆市渝中区。"
    row = _row("r1", "第一条 服务内容与范围", quote="第一条 服务内容与范围")
    clean_technical_requirements({"requirements": {"r1": row}, "files": {"f1": {"pages": [page]}}})
    assert row["requirement_scope"] == "fragment_filtered"
    assert "运维服务地点" not in row["text"]  # 绝不拼出弗兰肯斯坦句
    assert "ordinal_heading" in (row.get("fragment_reason") or "")


def test_ordinal_heading_with_inline_content_still_completes():
    """标题与内容在同一行时，行内单句补全仍然允许。"""
    page = "第一条 服务内容与范围：提供7×24小时运维保障服务。"
    row = _row("r1", "第一条 服务内容与范围", quote="第一条 服务内容与范围")
    clean_technical_requirements({"requirements": {"r1": row}, "files": {"f1": {"pages": [page]}}})
    assert row["requirement_scope"] == "technical"
    assert "7×24" in row["text"]


def test_cross_line_broken_sentence_still_completes():
    """针本身被换行截断的合法跨行补全（带真实碎片信号）不受序号标题守卫影响。"""
    page = "应急响应时限为：\n30分钟内到场处置。"
    row = _row("r1", "应急响应时限为：", quote="应急响应时限为：")
    clean_technical_requirements({"requirements": {"r1": row}, "files": {"f1": {"pages": [page]}}})
    assert row["requirement_scope"] == "technical"
    assert "30分钟内到场" in row["text"]


# ---------------------------------------------------------------- 服务级：目录重建回写
class FakeModel:
    is_real_model = True
    is_local = True
    base_url = ""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def suggest(self, system, user, profile=None):
        self.calls.append((system, user))
        reply = self.replies.pop(0) if self.replies else RuntimeError("exhausted")
        if isinstance(reply, Exception):
            raise reply
        return reply


def _seed_legacy_project(client):
    """创建技术册项目并直接写入「未清洗的存量」条款：无 scope 标记、带假负偏离。"""
    headers = login(client, "alpha-manager")
    result = client.post("/api/v1/projects", headers=headers,
                         json={"name": "存量项目清洗回写验证", "volume_mode": "technical_only"})
    assert result.status_code == 200, result.text
    project_id = result.json()["id"]
    service = client.app.state.service

    def change(state):
        workflow = state.workflows.setdefault(project_id, {
            "requirements": {}, "facts": {}, "conflicts": {}, "files": {}, "chapter_order": [],
        })
        workflow["requirements"] = {
            "r1": _row("r1", "每月巡检数据库并出具报告"),
            "r2": _row("r2", "应急预案完整可行"),
            "r3": _row("r3", "备份恢复演练每季度一次"),
            "r4": _fake_negative(_row("r4", "投标报价不得高于最高限价")),
            "r5": _fake_negative(_row("r5", "| 采用数据库", quote="无锚点")),
        }
        workflow["technical_sidecars"] = {"rejection_lines": [], "format_lines": []}

    service.repository.transaction(change)
    token = headers["Authorization"].split(" ", 1)[1]
    # 编排方法在 WorkflowService（TenderOrchestratorMixin）上，DemoService 门面不直接暴露。
    from icg.domain.workflow_orchestrator import WorkflowService
    from icg_demo.parsing import LocalTextParser
    orchestrator = WorkflowService(service, LocalTextParser())
    return project_id, service.authenticate(token), orchestrator


def _read_workflow(service, project_id):
    return service.repository.read().workflows[project_id]


def _skeleton():
    return json.dumps({"nodes": [
        {"level": 1, "title": "运维服务方案"},
        {"level": 2, "title": "日常巡检"},
    ]}, ensure_ascii=False)


def _mounts(*refs):
    return json.dumps({"mounts": [{"node": "1.1", "refs": list(refs)}]}, ensure_ascii=False)


def test_outline_rebuild_writes_back_cleaning_and_clears_fake_negative(client):  # noqa: F811
    project_id, principal, service = _seed_legacy_project(client)
    model = FakeModel([_skeleton(), _mounts("T-01", "T-02", "T-03")])
    service._refresh_technical_outline_unlocked(principal, project_id, model)

    workflow = _read_workflow(service, project_id)
    assert workflow.get("outline_source") == "model" and not workflow.get("tree_model_failed")
    rows = workflow["requirements"]
    # 清洗分流落盘：非技术行范围标记持久化，假负偏离被清理
    assert rows["r4"]["requirement_scope"] == "non_technical"
    assert rows["r4"]["deviation_type"] is None and rows["r4"]["response"] == ""
    assert rows["r4"].get("clause_cleaned") is True
    # 碎片行过滤落盘
    assert rows["r5"]["requirement_scope"] == "fragment_filtered"
    assert rows["r5"]["deviation_type"] is None
    # 技术行拿到清单编号并挂进目录
    assert rows["r1"].get("digest_id") == "T-01"
    assert workflow.get("response_tasks")
    outline = workflow.get("technical_outline") or {}
    assert outline.get("headings") and outline.get("outline_source") == "model"


def test_outline_rebuild_failure_still_writes_back_cleaning(client):  # noqa: F811
    project_id, principal, service = _seed_legacy_project(client)
    model = FakeModel([RuntimeError("boom"), RuntimeError("boom"), RuntimeError("boom")])
    service._refresh_technical_outline_unlocked(principal, project_id, model)

    workflow = _read_workflow(service, project_id)
    assert workflow.get("tree_model_failed") is True
    assert workflow.get("outline_model_error", {}).get("stage") == "skeleton"
    rows = workflow["requirements"]
    # 目录失败不影响清洗落盘：两条路径都回写
    assert rows["r4"]["requirement_scope"] == "non_technical"
    assert rows["r4"]["deviation_type"] is None
    assert rows["r5"]["requirement_scope"] == "fragment_filtered"
    # 失败绝不写成模型目录
    assert workflow.get("outline_source") != "model"
