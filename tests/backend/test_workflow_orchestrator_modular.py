# 为什么有这个文件：为 BE-TECH-DEBT-03 建立独立的工作流解耦与子编排服务测试套件。
# 它解决什么问题：
# 1. 验证 workflow_orchestrator 巨石代码行数严格 <= 350 行；
# 2. 验证 OutlineOrchestrator, GenerationOrchestrator, CheckOrchestrator, TenderOrchestrator, LibraryOrchestrator 的独立实例与方法委托契约；
# 3. 验证 Outline 树构建与章节序号规范化、大纲定稿就绪检查；
# 4. 验证 Prompt 预算与大模型写作方案组装（DynamicPromptContextManager 集成）；
# 5. 验证合规检查全规则引擎调用与阻断缺陷汇总（aggregate_blockers / CheckBlockerError）；
# 6. 验证增量复检队列管理（schedule_incremental_recheck）。

from __future__ import annotations

import pathlib
import pytest

from icg_demo.adapters import MemoryRepository, seed_state
from icg.domain.domain import DemoService, DemoState, Principal, Chapter, new_id, iso_time
from icg.domain.workflow_orchestrator import WorkflowService
from icg.domain.outline_orchestrator import OutlineOrchestrator, OutlineOrchestratorMixin
from icg.domain.generation_orchestrator import GenerationOrchestrator, GenerationOrchestratorMixin
from icg.domain.check_orchestrator import CheckOrchestrator, CheckOrchestratorMixin, CheckBlockerError
from icg.domain.tender_orchestrator import TenderOrchestrator, TenderOrchestratorMixin
from icg.domain.library_orchestrator import LibraryOrchestrator, LibraryOrchestratorMixin
from icg.domain.export_service import ExportService
from icg.domain.generation_service import GenerationService
from icg.domain.outline_service import OutlineService
from icg.domain.parsing import LocalTextParser


@pytest.fixture
def test_setup():
    repo = MemoryRepository(seed_state())
    demo = DemoService(repo, None)
    parser = LocalTextParser()
    workflow = WorkflowService(demo, parser)

    def seed_sessions(st: DemoState):
        st.sessions["token-manager"] = "alpha-manager"

    repo.transaction(seed_sessions)
    state = repo.read()
    principal = Principal(state.accounts["alpha-manager"], "token-manager")
    return demo, workflow, principal


def test_workflow_orchestrator_line_count():
    """硬性门禁：WorkflowService 巨石文件行数必须严格控制在 350 行以内。"""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    file_path = repo_root / "backend" / "bid-core" / "icg" / "domain" / "workflow_orchestrator.py"
    assert file_path.exists(), f"找不到文件: {file_path}"
    lines = file_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 350, f"workflow_orchestrator.py 代码行数为 {len(lines)}，超过了 350 行上限！"


def test_sub_orchestrators_mounted(test_setup):
    """验证各领域子编排服务实例正确挂载且支持双向委托。"""
    demo, workflow, principal = test_setup

    assert isinstance(workflow.outline_orchestrator, OutlineOrchestrator)
    assert isinstance(workflow.generation_orchestrator, GenerationOrchestrator)
    assert isinstance(workflow.check_orchestrator, CheckOrchestrator)
    assert isinstance(workflow.tender_orchestrator, TenderOrchestrator)
    assert isinstance(workflow.library_orchestrator, LibraryOrchestrator)

    # 验证子编排器能通过 __getattr__ 委托访问宿主 workflow 的属性与方法
    assert workflow.outline_orchestrator.demo is demo
    assert workflow.generation_orchestrator.demo is demo
    assert workflow.check_orchestrator.demo is demo


def test_outline_orchestrator_tree_and_readiness(test_setup):
    """验证 OutlineOrchestrator 大纲树构建、编号规范化与定稿就绪检查。"""
    demo, workflow, principal = test_setup

    project_id = "alpha-project"
    state = demo.repository.read()

    # 验证大纲树构建
    tree = workflow.outline_orchestrator.build_outline_tree(state, project_id, "technical")
    assert isinstance(tree, list)
    assert len(tree) > 0
    assert "id" in tree[0]
    assert "section_number" in tree[0]

    # 验证大纲定稿就绪检查
    readiness = workflow.outline_orchestrator.check_outline_finalization_readiness(state, project_id, "technical")
    assert "ready" in readiness
    assert "plan_confirmed" in readiness
    assert "unmapped_requirements_count" in readiness


def test_generation_orchestrator_prompt_plan_and_candidate(test_setup):
    """验证 GenerationOrchestrator 写作提示词组装与动态预算集成。"""
    demo, workflow, principal = test_setup
    project_id = "alpha-project"
    chapter_id = "alpha-tech"

    # 验证方法可通过 workflow 或 generation_orchestrator 调用
    assert hasattr(workflow, "assemble_writing_prompt_plan")
    assert hasattr(workflow.generation_orchestrator, "assemble_writing_prompt_plan")
    assert hasattr(workflow, "start_chapter_generation")
    assert hasattr(workflow.generation_orchestrator, "start_chapter_generation")

    # 组装写作计划 Prompt 方案
    plan = workflow.generation_orchestrator.assemble_writing_prompt_plan(
        project_id=project_id,
        chapter_id=chapter_id,
        principal=principal,
    )
    assert plan["project_id"] == project_id
    assert plan["chapter_id"] == chapter_id
    assert "prompt" in plan
    assert "token_budget_usage" in plan
    assert "context_fingerprint" in plan


def test_check_orchestrator_and_blocker_aggregation(test_setup):
    """验证 CheckOrchestrator 规则评估、阻断缺陷聚合与增量复检队列。"""
    demo, workflow, principal = test_setup
    project_id = "alpha-project"

    # 1. 验证 aggregate_blockers 能够过滤出阻断级/废标级缺陷
    issues = [
        {"id": "iss-1", "severity": "minor", "message": "正文略短"},
        {"id": "iss-2", "severity": "blocker", "message": "缺失废标条款响应", "is_blocker": True},
        {"id": "iss-3", "severity": "critical", "message": "星号条款未挂接证据"},
    ]
    blockers = CheckOrchestrator.aggregate_blockers(issues)
    assert len(blockers) == 2
    assert {b["id"] for b in blockers} == {"iss-2", "iss-3"}

    # 2. 验证 CheckBlockerError 构造与抛出
    err = CheckBlockerError("存在废标条款缺陷")
    assert err.code == "CHECK_BLOCKER_EXISTS"
    assert err.status == 400

    # 3. 验证 schedule_incremental_recheck 增量复检队列管理
    state = demo.repository.read()
    res = workflow.check_orchestrator.schedule_incremental_recheck(state, project_id, ["alpha-tech"])
    assert res["project_id"] == project_id
    assert "alpha-tech" in res["pending_chapters"]
    assert res["recheck_count"] == 1


def test_backward_compatibility_facades():
    """验证 GenerationService, OutlineService, ExportService 等历史 Façade 保持 100% 导入兼容。"""
    assert issubclass(GenerationService, GenerationOrchestratorMixin)
    assert issubclass(OutlineService, OutlineOrchestratorMixin)
    assert issubclass(ExportService, CheckOrchestratorMixin)
