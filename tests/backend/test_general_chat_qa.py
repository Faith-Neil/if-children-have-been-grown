# 为什么有这个文件：验证智能对话助手自由问答（只“复制”与安全隔离）核心业务逻辑与四道安全门禁（APP-M2-T179，ISSUE-007，PRD v1.8 §5.11.3～5.11.6、§5.11.11）。
# 它解决什么问题：
# 1. 门禁 1（禁止写入正文）：自由问答响应中 can_insert 必须恒定为 False，action="copy_only"，绝不返回直接插入正文或段落替换操作，章节正文、修订号与版本历史零污染；
# 2. 门禁 2（知识库关闭常驻说明）：当 knowledge_base_enabled=False 时，严格禁止外呼 RAGFlow 检索公司库，并在回答中保持常驻说明“知识库已关闭，未查询公司资料库”，绝不编造虚假的公司资质或业绩数据；
# 3. 门禁 3（敏感项目模型隔离）：若当前项目为敏感项目（sensitive=True 或 is_sensitive=True），必须强制使用本地模型运行时；企图绑定或调用云端模型时，严格触发 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL；
# 4. 门禁 4（只读角色提问拦截）：只读角色（group_admin、viewer、auditor、platform_admin）及项目只读成员尝试发起自由提问时，统一拦截拒绝（403 FORBIDDEN）；
# 5. 模型故障映射（502 MODEL_UNAVAILABLE）与跨租户多租户安全隔离（404 NOT_FOUND）。

import httpx
import pytest

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.answer_card import AnswerCardService
from icg_demo.domain import DemoService, DomainError, Principal
from icg_demo.model_config_storage import ModelConfig
from icg_demo.ports import ModelProvider, ParserProvider
from icg_demo.workflow import WorkflowService


class MockModelProvider(ModelProvider):
    name = "mock-model"
    is_real_model = True
    is_local = True

    def __init__(self, reply: str = "这是针对提问的模型回答内容。"):
        self.reply = reply
        self.calls = []

    def suggest(self, instruction: str, content: str) -> str:
        self.calls.append((instruction, content))
        return self.reply


class FailingModelProvider(ModelProvider):
    name = "failing-model"
    is_real_model = True
    is_local = True

    def suggest(self, instruction: str, content: str) -> str:
        raise RuntimeError("模型服务连接超时")


class MockEvidenceService:
    def __init__(self, candidates=None):
        self.candidates = candidates or []
        self.search_calls = []

    def search(self, company_id: str, query: str):
        self.search_calls.append((company_id, query))
        return self.candidates


class DummyParser(ParserProvider):
    def parse(self, filename: str, content: bytes) -> dict:
        return {"title": "测试文件", "pagination": "none", "pages": [], "warnings": []}


class DummyCandidate:
    def __init__(self, cid: str, name: str, record_type: str = "snippet"):
        self.id = cid
        self.name = name
        self.record_type = record_type


@pytest.fixture
def chat_setup():
    state = seed_state()
    project = state.projects["alpha-project"]
    project.deadline = "2026-12-31T17:00:00+08:00"
    project.sensitive = False

    state.sessions.update({
        "session-alpha-editor": "alpha-editor",
        "session-alpha-admin": "alpha-company-admin",
        "session-alpha-viewer": "alpha-viewer",
        "session-alpha-auditor": "alpha-auditor",
        "session-group-admin": "platform-admin",
        "session-beta-editor": "beta-editor",
    })

    # 初始化测试用户与账号
    from icg_demo.domain import Account
    state.accounts["alpha-viewer"] = Account(
        id="alpha-viewer",
        name="甲公司只读成员",
        company_id="alpha",
        role="viewer",
    )
    state.accounts["alpha-auditor"] = Account(
        id="alpha-auditor",
        name="甲公司审计员",
        company_id="alpha",
        role="auditor",
    )
    state.accounts["group-admin-user"] = Account(
        id="group-admin-user",
        name="集团管理员",
        company_id="alpha",
        role="group_admin",
    )
    state.accounts["platform-admin-user"] = Account(
        id="platform-admin-user",
        name="平台管理员",
        company_id="alpha",
        role="platform_admin",
    )
    state.sessions["session-group-admin-user"] = "group-admin-user"
    state.sessions["session-platform-admin-user"] = "platform-admin-user"

    repo = MemoryRepository(state)
    mock_model = MockModelProvider("这是针对提问的模型回答内容。")
    mock_evidence = MockEvidenceService([
        DummyCandidate("chunk-001", "微服务高可用架构技术规范", "snippet"),
        DummyCandidate("chunk-002", "数据库容灾备份方案片段", "snippet"),
    ])

    demo = DemoService(repo, mock_model, evidence_service=mock_evidence)
    workflow_svc = WorkflowService(demo, DummyParser())
    answer_svc = AnswerCardService(demo)

    principal_editor = Principal(state.accounts["alpha-editor"], "session-alpha-editor")
    principal_viewer = Principal(state.accounts["alpha-viewer"], "session-alpha-viewer")
    principal_auditor = Principal(state.accounts["alpha-auditor"], "session-alpha-auditor")
    principal_group_admin = Principal(state.accounts["group-admin-user"], "session-group-admin-user")
    principal_platform_admin = Principal(state.accounts["platform-admin-user"], "session-platform-admin-user")
    principal_beta = Principal(state.accounts["beta-editor"], "session-beta-editor")

    return {
        "state": state,
        "repo": repo,
        "demo": demo,
        "project": project,
        "mock_model": mock_model,
        "mock_evidence": mock_evidence,
        "workflow_svc": workflow_svc,
        "answer_svc": answer_svc,
        "principal_editor": principal_editor,
        "principal_viewer": principal_viewer,
        "principal_auditor": principal_auditor,
        "principal_group_admin": principal_group_admin,
        "principal_platform_admin": principal_platform_admin,
        "principal_beta": principal_beta,
    }


def test_gate_1_copy_only_and_no_writing(chat_setup):
    """门禁 1：自由问答响应中 can_insert 必须恒定为 False，action='copy_only'，正文与版本零修改。"""
    answer_svc = chat_setup["answer_svc"]
    principal = chat_setup["principal_editor"]
    repo = chat_setup["repo"]

    initial_state = repo.read()
    chapter_before = initial_state.chapters["alpha-tech"]
    initial_content = chapter_before.content
    initial_rev = chapter_before.revision
    initial_versions_count = len(chapter_before.versions)

    res = answer_svc.general_chat(
        principal=principal,
        project_id="alpha-project",
        query="请问如何规划数据库高可用方案？",
        knowledge_base_enabled=True,
        chapter_id="alpha-tech",
    )

    # 1. 验证门禁 1 标识
    assert res["can_insert"] is False
    assert res["action"] == "copy_only"
    assert "不可直接插入正文" in res["insert_disabled_reason"]
    assert "数据库高可用" in res["query"]
    assert res["reply"] is not None

    # 2. 验证正文、修订号与版本记录绝对未被修改
    after_state = repo.read()
    chapter_after = after_state.chapters["alpha-tech"]
    assert chapter_after.content == initial_content
    assert chapter_after.revision == initial_rev
    assert len(chapter_after.versions) == initial_versions_count


def test_gate_2_kb_disabled_zero_retrieval_and_persistent_notice(chat_setup):
    """门禁 2：知识库关闭时，严格禁止外呼检索，并在回答中常驻说明，绝不自造虚假资质。"""
    answer_svc = chat_setup["answer_svc"]
    principal = chat_setup["principal_editor"]
    mock_evidence = chat_setup["mock_evidence"]

    res = answer_svc.general_chat(
        principal=principal,
        project_id="alpha-project",
        query="公司具备哪些云安全等级保护资质？",
        knowledge_base_enabled=False,
    )

    # 1. 验证零检索调用
    assert len(mock_evidence.search_calls) == 0
    assert res["query_route"] == "no_retrieval"
    assert res["library_query_skipped"] is True
    assert res["kb_enabled"] is False
    assert res["citations"] == []

    # 2. 验证常驻说明文案
    assert "知识库已关闭，未查询公司资料库" in res["notice"]
    assert "知识库已关闭，未查询公司资料库" in res["reply"]


def test_gate_2_kb_enabled_retrieval_and_citations(chat_setup):
    """门禁 2：知识库开启时正常执行检索并附加切片引用。"""
    answer_svc = chat_setup["answer_svc"]
    principal = chat_setup["principal_editor"]
    mock_evidence = chat_setup["mock_evidence"]

    res = answer_svc.general_chat(
        principal=principal,
        project_id="alpha-project",
        query="微服务架构如何实现容灾备份？",
        knowledge_base_enabled=True,
    )

    # 1. 验证检索被调用
    assert len(mock_evidence.search_calls) == 1
    assert mock_evidence.search_calls[0][0] == "alpha"
    assert res["query_route"] == "kb_retrieval"
    assert res["library_query_skipped"] is False
    assert res["kb_enabled"] is True

    # 2. 验证切片引用
    assert len(res["citations"]) == 2
    assert res["citations"][0]["id"] == "chunk-001"
    assert res["citations"][0]["name"] == "微服务高可用架构技术规范"


def test_gate_3_sensitive_project_blocks_cloud_model(chat_setup):
    """门禁 3：敏感项目（sensitive=True）绑定云端模型配置时，严格抛出 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
    answer_svc = chat_setup["answer_svc"]
    principal = chat_setup["principal_editor"]
    repo = chat_setup["repo"]

    # 1. 将项目标记为敏感项目并绑定云端模型
    def make_sensitive(state):
        state.projects["alpha-project"].sensitive = True
        cloud_cfg = ModelConfig(
            id="cfg-cloud-001",
            company_id="alpha",
            name="云端通用大模型",
            provider="openai-compatible",
            base_url="https://api.openai.com",
            model="gpt-4o",
            is_local=False,
            allow_sensitive=False,
        )
        state.model_configs[cloud_cfg.id] = cloud_cfg
        state.project_model_configs["alpha-project"] = cloud_cfg.id

    repo.transaction(make_sensitive)

    with pytest.raises(DomainError) as exc_info:
        answer_svc.general_chat(
            principal=principal,
            project_id="alpha-project",
            query="请解释涉密网关部署方案",
            knowledge_base_enabled=True,
        )

    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"
    assert "敏感项目只能使用本地模型" in str(exc_info.value)


def test_gate_3_sensitive_project_allows_local_model(chat_setup):
    """门禁 3：敏感项目绑定合格本地模型配置时正常放行。"""
    answer_svc = chat_setup["answer_svc"]
    principal = chat_setup["principal_editor"]
    repo = chat_setup["repo"]
    demo = chat_setup["demo"]

    # 注入纯内存 MockTransport，杜绝真实外部连接
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "本地模型回答成功"}, "finish_reason": "stop"}]
    }))
    demo.model_transport = transport

    def bind_local(state):
        state.projects["alpha-project"].sensitive = True
        local_cfg = ModelConfig(
            id="cfg-local-001",
            company_id="alpha",
            name="内网离线本地模型",
            provider="openai-compatible",
            base_url="http://127.0.0.1:8000",
            model="local-qwen",
            is_local=True,
            allow_sensitive=True,
        )
        state.model_configs[local_cfg.id] = local_cfg
        state.project_model_configs["alpha-project"] = local_cfg.id

    repo.transaction(bind_local)

    res = answer_svc.general_chat(
        principal=principal,
        project_id="alpha-project",
        query="请给出内网离线部署规范",
        knowledge_base_enabled=True,
    )
    assert res["reply"] is not None
    assert "本地模型回答成功" in res["reply"]
    assert res["can_insert"] is False


def test_gate_4_readonly_roles_interception(chat_setup):
    """门禁 4：只读系统角色（group_admin、viewer、auditor、platform_admin）发起自由提问时，严格阻断抛出 403 FORBIDDEN。"""
    answer_svc = chat_setup["answer_svc"]
    readonly_principals = [
        ("viewer", chat_setup["principal_viewer"]),
        ("auditor", chat_setup["principal_auditor"]),
        ("group_admin", chat_setup["principal_group_admin"]),
        ("platform_admin", chat_setup["principal_platform_admin"]),
    ]

    for role_name, p in readonly_principals:
        with pytest.raises(DomainError) as exc_info:
            answer_svc.general_chat(
                principal=p,
                project_id="alpha-project",
                query="只读角色尝试提问",
                knowledge_base_enabled=True,
            )
        assert exc_info.value.status == 403
        assert exc_info.value.code == "FORBIDDEN"
        assert "只读角色不可使用智能助手提问" in str(exc_info.value)


def test_gate_4_project_member_viewer_interception(chat_setup):
    """门禁 4：用户虽为普通编写人系统角色，但在当前项目中被指定为 viewer 只读成员，严格阻断。"""
    answer_svc = chat_setup["answer_svc"]
    principal = chat_setup["principal_editor"]
    repo = chat_setup["repo"]

    def set_project_viewer(state):
        team = state.project_teams.setdefault("alpha-project", {"members": {}})
        team["members"]["alpha-editor"] = {
            "user_id": "alpha-editor",
            "project_role": "viewer",
        }
    repo.transaction(set_project_viewer)

    with pytest.raises(DomainError) as exc_info:
        answer_svc.general_chat(
            principal=principal,
            project_id="alpha-project",
            query="项目只读成员提问",
            knowledge_base_enabled=True,
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"
    assert "项目只读成员不可使用智能助手提问" in str(exc_info.value)


def test_cross_tenant_isolation(chat_setup):
    """多租户安全：跨公司访问项目提问，严格抛出 404 NOT_FOUND。"""
    answer_svc = chat_setup["answer_svc"]
    principal_beta = chat_setup["principal_beta"]

    with pytest.raises(DomainError) as exc_info:
        answer_svc.general_chat(
            principal=principal_beta,
            project_id="alpha-project",
            query="乙公司尝试提问甲公司项目",
            knowledge_base_enabled=True,
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"


def test_model_failure_mapped_to_502(chat_setup):
    """模型故障映射：下游模型服务抛出异常时，业务层统一映射为 502 MODEL_UNAVAILABLE。"""
    failing_model = FailingModelProvider()
    repo = chat_setup["repo"]
    demo = DemoService(repo, failing_model)
    answer_svc = AnswerCardService(demo)
    principal = chat_setup["principal_editor"]

    with pytest.raises(DomainError) as exc_info:
        answer_svc.general_chat(
            principal=principal,
            project_id="alpha-project",
            query="测试模型故障时的错误映射",
            knowledge_base_enabled=True,
        )
    assert exc_info.value.status == 502
    assert exc_info.value.code == "MODEL_UNAVAILABLE"


def test_workflow_service_delegation(chat_setup):
    """验证 WorkflowService.general_chat 与 WorkflowService.ask_assistant 正确委派调用。"""
    workflow_svc = chat_setup["workflow_svc"]
    principal = chat_setup["principal_editor"]

    # 1. 验证 general_chat 委派
    res1 = workflow_svc.general_chat(
        principal=principal,
        project_id="alpha-project",
        query="测试 workflow general_chat 委派",
        knowledge_base_enabled=True,
    )
    assert res1["can_insert"] is False
    assert res1["action"] == "copy_only"
    assert res1["reply"] is not None

    # 2. 验证 ask_assistant 别名委派
    res2 = workflow_svc.ask_assistant(
        principal=principal,
        project_id="alpha-project",
        query="测试 workflow ask_assistant 委派",
        knowledge_base_enabled=False,
    )
    assert res2["can_insert"] is False
    assert res2["action"] == "copy_only"
    assert "知识库已关闭" in res2["notice"]
