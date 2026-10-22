# 为什么有这个文件：验证编辑台章节上下文感知问答与划词引用联动（AI-EDITOR-CONTEXT-LINKAGE，PRD v1.8 §5.11.3～5.11.6、§5.7.8）。
# 它解决什么问题：
# 1. 段落解析与划词命中：段落切分为 [P1], [P2]...，选中文本精准命中所在段落；无选中文本时干净兜底；
# 2. 上下文与依据组装：Prompt 上下文注入章节正文段落、选中文本、项目事实/SLA 变量、招标文件条款与 [证]/[片] 溯源依据（含不可篡改指纹）；
# 3. 双场景支持：划词润色/优化（polish，输出 Diff 建议与改写片段）与章节合规性/完整度问答（compliance_qa）；
# 4. 安全守卫与锁控制：
#    - 无编辑锁时强制 can_insert=False, action="copy_only"，正文零突变；
#    - 持有有效编辑锁且具备证据依据时允许生成可溯源替换建议（suggest_replacement）；缺少依据时阻断插入；
#    - 敏感项目强制本地模型隔离（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）；
#    - 只读角色拦截（403 FORBIDDEN）与租户隔离（404 NOT_FOUND）。

import time
import httpx
import pytest

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.answer_card import AnswerCardService
from icg_demo.domain import Account, DemoService, DomainError, Lease, Principal
from icg_demo.editor_ai_context import (
    EditorAIContextService,
    build_editor_prompt_context,
    collect_chapter_citations,
    decompose_chapter_paragraphs,
    detect_editor_scene,
)
from icg_demo.model_config_storage import ModelConfig
from icg_demo.ports import ModelProvider, ParserProvider
from icg_demo.workflow import WorkflowService


class MockEditorModelProvider(ModelProvider):
    name = "mock-editor-model"
    is_real_model = True
    is_local = True

    def __init__(self, reply: str = ""):
        self.reply = reply
        self.calls = []

    def suggest(self, instruction: str, content: str) -> str:
        self.calls.append((instruction, content))
        if self.reply:
            return self.reply
        # 默认根据指令内容返回友好解答
        if "Diff" in instruction or "润色" in instruction:
            return (
                "经过润色优化，建议改写为：采用双活高可用微服务架构，全面满足招标文件要求。\n"
                "【建议改写】：采用双活高可用微服务架构，全面满足招标文件要求。"
            )
        return "针对本章节合规性分析：当前章节响应完整，覆盖了招标文件核心指标，建议补充性能评测附录。"


class FailingModelProvider(ModelProvider):
    name = "failing-model"
    is_real_model = True
    is_local = True

    def suggest(self, instruction: str, content: str) -> str:
        raise RuntimeError("模型服务连接失败")


class MockEvidenceCandidate:
    def __init__(self, cid: str, name: str, text: str = "切片文本", record_type: str = "snippet"):
        self.id = cid
        self.name = name
        self.text = text
        self.record_type = record_type


class MockEvidenceService:
    def __init__(self, candidates=None):
        self.candidates = candidates or []
        self.calls = []

    def search(self, company_id: str, query: str):
        self.calls.append((company_id, query))
        return self.candidates


class DummyParser(ParserProvider):
    def parse(self, filename: str, content: bytes) -> dict:
        return {"title": "测试", "pagination": "none", "pages": [], "warnings": []}


@pytest.fixture
def editor_setup():
    state = seed_state()
    project = state.projects["alpha-project"]
    project.deadline = "2026-12-31T17:00:00+08:00"
    project.sensitive = False

    chapter = state.chapters["alpha-tech"]
    # 丰富章节正文内容以便测试段落切分与划词
    chapter.content = (
        "第一段：本项目遵循微服务架构标准，提供统一身份认证与服务注册发现机制。\n"
        "第二段：系统采用双活容灾备份方案，保障数据零丢失与分钟级故障自动切换。\n"
        "第三段：根据项目事实 {{fact:period}} 与 SLA 承诺 {{sla:response_time}}，提供全天候运维响应支持。"
    )
    chapter.revision = 3

    # 添加关联条款与已确认公司证据
    workflow = state.workflows.setdefault("alpha-project", {
        "parse_confirmed": True,
        "requirements": {},
        "facts": {},
        "files": {},
        "conflicts": {},
    })
    workflow["requirements"]["req-tech-01"] = {
        "id": "req-tech-01",
        "chapter_id": "alpha-tech",
        "text": "投标人须具备 CMMI5 级认证及高可用架构实施案例。",
        "status": "confirmed",
        "volume": "technical",
        "evidence_ids": ["lib-cert-01"],
    }
    state.library["lib-cert-01"] = {
        "id": "lib-cert-01",
        "name": "CMMI 5 级软件能力成熟度模型集成证书",
        "type": "qualification",
        "company_id": "alpha",
        "status": "confirmed",
        "revision": 2,
        "valid_until": "2027-12-31",
        "content": "甲公司已通过 CMMI Maturity Level 5 评估认证。",
    }

    # 账号与会话初始化
    state.accounts["alpha-viewer"] = Account(
        id="alpha-viewer",
        name="只读查看人",
        company_id="alpha",
        role="viewer",
    )
    state.accounts["alpha-auditor"] = Account(
        id="alpha-auditor",
        name="审计员",
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

    state.sessions.update({
        "session-alpha-editor": "alpha-editor",
        "session-alpha-manager": "alpha-manager",
        "session-alpha-viewer": "alpha-viewer",
        "session-alpha-auditor": "alpha-auditor",
        "session-group-admin": "group-admin-user",
        "session-platform-admin": "platform-admin-user",
        "session-beta-editor": "beta-editor",
    })

    repo = MemoryRepository(state)
    mock_model = MockEditorModelProvider()
    mock_evidence = MockEvidenceService([
        MockEvidenceCandidate("chunk-01", "微服务架构容灾切片", "切片正文：微服务节点心跳超时检测为30秒。"),
    ])

    demo = DemoService(repo, mock_model, evidence_service=mock_evidence)
    workflow_svc = WorkflowService(demo, DummyParser())
    answer_svc = AnswerCardService(demo)
    editor_svc = EditorAIContextService(demo)

    principal_editor = Principal(state.accounts["alpha-editor"], "session-alpha-editor")
    principal_manager = Principal(state.accounts["alpha-manager"], "session-alpha-manager")
    principal_viewer = Principal(state.accounts["alpha-viewer"], "session-alpha-viewer")
    principal_auditor = Principal(state.accounts["alpha-auditor"], "session-alpha-auditor")
    principal_group_admin = Principal(state.accounts["group-admin-user"], "session-group-admin")
    principal_platform_admin = Principal(state.accounts["platform-admin-user"], "session-platform-admin")
    principal_beta = Principal(state.accounts["beta-editor"], "session-beta-editor")

    return {
        "state": state,
        "repo": repo,
        "demo": demo,
        "project": project,
        "chapter": chapter,
        "mock_model": mock_model,
        "mock_evidence": mock_evidence,
        "workflow_svc": workflow_svc,
        "answer_svc": answer_svc,
        "editor_svc": editor_svc,
        "principal_editor": principal_editor,
        "principal_manager": principal_manager,
        "principal_viewer": principal_viewer,
        "principal_auditor": principal_auditor,
        "principal_group_admin": principal_group_admin,
        "principal_platform_admin": principal_platform_admin,
        "principal_beta": principal_beta,
    }


def test_decompose_paragraphs_and_selection_matching(editor_setup):
    """测试段落切分、段落标签 [P1] 与选中文本精准命中及兜底。"""
    chapter = editor_setup["chapter"]

    # 1. 精确匹配第二段中的划词
    selected = "双活容灾备份方案"
    paras = decompose_chapter_paragraphs(chapter.content, selected)
    assert len(paras) == 3
    assert paras[0]["label"] == "[P1]"
    assert paras[0]["is_selected"] is False
    assert paras[1]["label"] == "[P2]"
    assert paras[1]["is_selected"] is True
    assert "双活容灾备份方案" in paras[1]["text"]
    assert paras[1]["match_start"] >= 0
    assert paras[2]["label"] == "[P3]"
    assert paras[2]["is_selected"] is False

    # 2. 无选中文本时的干净兜底：全部为 False，不抛异常
    paras_none = decompose_chapter_paragraphs(chapter.content, None)
    assert len(paras_none) == 3
    assert all(not p["is_selected"] for p in paras_none)

    paras_empty = decompose_chapter_paragraphs(chapter.content, "   ")
    assert len(paras_empty) == 3
    assert all(not p["is_selected"] for p in paras_empty)

    # 3. 空正文兜底
    assert decompose_chapter_paragraphs("", "测试") == []


def test_scene_detection():
    """测试润色优化与合规问答场景判定。"""
    # 划词润色场景
    assert detect_editor_scene("请润色这句话", "双活架构") == "polish"
    assert detect_editor_scene("帮我改写更通顺一些", "系统采用备份方案") == "polish"
    assert detect_editor_scene("如何优化表述", "提供全天候支持") == "polish"
    assert detect_editor_scene("这是什么", "提供全天候支持") == "polish"  # 有划词默认倾斜润色

    # 合规问答场景
    assert detect_editor_scene("检查本章节是否合规", None) == "compliance_qa"
    assert detect_editor_scene("是否存在废标风险与条款缺漏", None) == "compliance_qa"
    assert detect_editor_scene("本节是否满足评分项要求", None) == "compliance_qa"

    # 显式指定场景覆盖
    assert detect_editor_scene("自由问答", None, explicit_scene="polish") == "polish"
    assert detect_editor_scene("改写一下", "选中文本", explicit_scene="compliance_qa") == "compliance_qa"


def test_build_editor_prompt_context_polish_scene(editor_setup):
    """测试组装划词润色场景 Prompt 上下文（段落编号、选中文本定位与指纹计算）。"""
    state = editor_setup["state"]
    selected = "双活容灾备份方案"
    ctx = build_editor_prompt_context(
        state=state,
        project_id="alpha-project",
        chapter_id="alpha-tech",
        query="请将选中的这句润色得更专业高端",
        selected_text=selected,
        scene="polish",
    )

    assert ctx["scene"] == "polish"
    assert ctx["has_selected_text"] is True
    assert len(ctx["paragraphs"]) == 3
    assert ctx["paragraphs"][1]["is_selected"] is True

    # 验证 System Prompt 包含润色指令与红线要求
    sys_prompt = ctx["system_prompt"]
    assert "划词优化/润色建议场景专有要求" in sys_prompt
    assert "事实不可篡改" in sys_prompt
    assert "Diff 对比建议" in sys_prompt

    # 验证 User Content 结构化呈现
    user_content = ctx["user_content"]
    assert "[P2] (用户选中文本所在段)" in user_content
    assert "【用户划词选中文本】" in user_content
    assert selected in user_content

    # 验证依据收集与指纹
    assert len(ctx["citations"]) >= 1
    cert = [c for c in ctx["citations"] if c["tag"] == "[证]"][0]
    assert cert["name"] == "CMMI 5 级软件能力成熟度模型集成证书"
    assert len(cert["fingerprint"]) == 16
    assert len(ctx["context_fingerprint"]) == 64


def test_build_editor_prompt_context_compliance_scene(editor_setup):
    """测试组装合规性与完整度问答场景 Prompt 上下文。"""
    state = editor_setup["state"]
    ctx = build_editor_prompt_context(
        state=state,
        project_id="alpha-project",
        chapter_id="alpha-tech",
        query="本章节技术方案是否充分响应了招标要求？",
        selected_text=None,
        scene="compliance_qa",
    )

    assert ctx["scene"] == "compliance_qa"
    assert ctx["has_selected_text"] is False
    assert "无选中文本（针对当前章节全局提供分析建议）" in ctx["user_content"]
    assert "【章节合规性与完整度问答场景专有要求】" in ctx["system_prompt"]
    assert "条款 req-tech-01" in ctx["user_content"]


def test_chat_editor_context_fallback_when_no_selection(editor_setup):
    """测试无选中文本时的全局兜底问答与结构返回。"""
    editor_svc = editor_setup["editor_svc"]
    principal = editor_setup["principal_editor"]

    res = editor_svc.chat_editor_context(
        principal=principal,
        project_id="alpha-project",
        query="当前章节有哪些合规风险？",
        chapter_id="alpha-tech",
        selected_text=None,
    )

    assert res["has_selected_text"] is False
    assert res["selected_text"] is None
    assert res["scene"] == "compliance_qa"
    assert len(res["paragraphs"]) == 3
    assert res["can_insert"] is False
    assert res["action"] == "copy_only"
    assert res["diff_suggestion"] is None
    assert len(res["citations"]) >= 1


def test_chat_editor_context_polish_diff_suggestion(editor_setup):
    """测试划词润色建议与 Diff 对比产物生成。"""
    editor_svc = editor_setup["editor_svc"]
    principal = editor_setup["principal_editor"]
    mock_model = editor_setup["mock_model"]

    mock_model.reply = (
        "润色说明：将口语化表达升级为企业级架构表述。\n\n"
        "【建议改写】：构建端到端双活多活容灾备份体系，实现数据 RPO=0 与服务 RTO<1 分钟。\n\n"
        "（已保留所有技术参数与依据引用）。"
    )

    res = editor_svc.chat_editor_context(
        principal=principal,
        project_id="alpha-project",
        query="请润色选中文本",
        chapter_id="alpha-tech",
        selected_text="双活容灾备份方案",
        scene="polish",
    )

    assert res["scene"] == "polish"
    assert res["has_selected_text"] is True
    assert res["diff_suggestion"] is not None
    assert res["diff_suggestion"]["original"] == "双活容灾备份方案"
    assert "双活多活容灾备份体系" in res["diff_suggestion"]["suggested"]


def test_guard_no_lock_forces_copy_only(editor_setup):
    """门禁：未获得编辑锁时，自由问答与划词润色强制 can_insert=False, action='copy_only'，正文零突变。"""
    editor_svc = editor_setup["editor_svc"]
    principal = editor_setup["principal_editor"]
    chapter = editor_setup["chapter"]

    initial_content = chapter.content
    initial_rev = chapter.revision
    initial_versions_count = len(chapter.versions)

    # 未传入 lease_token，章节也未加锁
    res = editor_svc.chat_editor_context(
        principal=principal,
        project_id="alpha-project",
        query="优化这段文字",
        chapter_id="alpha-tech",
        selected_text="双活容灾备份方案",
        lease_token=None,
    )

    assert res["can_insert"] is False
    assert res["action"] == "copy_only"
    assert "未获取当前章节编辑锁" in res["insert_disabled_reason"]

    # 断言章节正文、修订号、版本历史绝对零修改
    assert chapter.content == initial_content
    assert chapter.revision == initial_rev
    assert len(chapter.versions) == initial_versions_count


def test_guard_valid_lock_and_citations_allow_suggest_replacement(editor_setup):
    """门禁：持有有效编辑锁且具有可溯源 citations 时，划词润色允许生成 suggest_replacement 建议。"""
    editor_svc = editor_setup["editor_svc"]
    principal = editor_setup["principal_editor"]
    repo = editor_setup["repo"]

    # 为当前用户赋予有效独占编辑锁租约
    now = editor_setup["demo"]._now()
    valid_token = "lease-token-alpha-editor-12345"
    def set_lock(s):
        s.chapters["alpha-tech"].lock = Lease(
            token=valid_token,
            owner_id=principal.user.id,
            session_token=principal.session_token,
            expires_at=now + 120,
        )
    repo.transaction(set_lock)

    res = editor_svc.chat_editor_context(
        principal=principal,
        project_id="alpha-project",
        query="优化这段文字并给出改写方案",
        chapter_id="alpha-tech",
        selected_text="双活容灾备份方案",
        scene="polish",
        lease_token=valid_token,
    )

    assert res["can_insert"] is True
    assert res["action"] == "suggest_replacement"
    assert res["insert_disabled_reason"] == ""
    assert len(res["citations"]) > 0
    # 溯源指纹完备
    for c in res["citations"]:
        assert c["fingerprint"] and len(c["fingerprint"]) == 16


def test_guard_valid_lock_without_citations_blocks_insert(editor_setup):
    """门禁：持有有效锁但缺少已核对依据溯源时，禁止标记可插入。"""
    editor_svc = editor_setup["editor_svc"]
    principal = editor_setup["principal_editor"]
    repo = editor_setup["repo"]

    now = editor_setup["demo"]._now()
    valid_token = "lease-token-alpha-editor-67890"

    def clear_cites_and_set_lock(s):
        s.workflows["alpha-project"]["requirements"]["req-tech-01"]["evidence_ids"] = []
        s.chapters["alpha-tech"].lock = Lease(
            token=valid_token,
            owner_id=principal.user.id,
            session_token=principal.session_token,
            expires_at=now + 120,
        )
    repo.transaction(clear_cites_and_set_lock)

    res = editor_svc.chat_editor_context(
        principal=principal,
        project_id="alpha-project",
        query="优化这段文字",
        chapter_id="alpha-tech",
        selected_text="双活容灾备份方案",
        scene="polish",
        lease_token=valid_token,
        knowledge_base_enabled=False,  # 确保切片亦无
    )

    assert res["can_insert"] is False
    assert res["action"] == "copy_only"
    assert "缺少已核对依据溯源" in res["insert_disabled_reason"]


def test_guard_sensitive_project_blocks_cloud_model(editor_setup):
    """门禁：敏感项目强制使用本地模型，配置云端模型时强阻断抛出 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
    editor_svc = editor_setup["editor_svc"]
    principal = editor_setup["principal_editor"]
    repo = editor_setup["repo"]

    # 绑定云端模型
    def make_cloud(s):
        s.projects["alpha-project"].sensitive = True
        cloud_cfg = ModelConfig(
            id="cloud-cfg",
            company_id="alpha",
            name="云端超大模型",
            provider="openai-compatible",
            base_url="https://api.openai.com/v1",
            is_local=False,
            allow_sensitive=False,
        )
        s.model_configs["cloud-cfg"] = cloud_cfg
        s.project_model_configs["alpha-project"] = "cloud-cfg"
    repo.transaction(make_cloud)

    with pytest.raises(DomainError) as exc_info:
        editor_svc.chat_editor_context(
            principal=principal,
            project_id="alpha-project",
            query="合规性分析",
            chapter_id="alpha-tech",
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 改绑合格本地模型后放行
    demo = editor_setup["demo"]
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "本地模型回答成功：当前章节合规性满足要求。"}, "finish_reason": "stop"}]
    }))
    demo.model_transport = transport

    def make_local(s):
        local_cfg = ModelConfig(
            id="local-cfg",
            company_id="alpha",
            name="内网离线模型",
            provider="openai-compatible",
            base_url="http://127.0.0.1:11434/v1",
            is_local=True,
            allow_sensitive=True,
        )
        s.model_configs["local-cfg"] = local_cfg
        s.project_model_configs["alpha-project"] = "local-cfg"
    repo.transaction(make_local)

    res = editor_svc.chat_editor_context(
        principal=principal,
        project_id="alpha-project",
        query="合规性分析",
        chapter_id="alpha-tech",
    )
    assert res["scene"] == "compliance_qa"


def test_guard_readonly_roles_and_cross_tenant_isolation(editor_setup):
    """门禁：系统只读角色与项目只读成员拦截 403；跨租户访问拦截 404。"""
    editor_svc = editor_setup["editor_svc"]
    repo = editor_setup["repo"]

    # 1. 系统只读角色拦截 403
    for p in (editor_setup["principal_viewer"], editor_setup["principal_auditor"],
              editor_setup["principal_group_admin"], editor_setup["principal_platform_admin"]):
        with pytest.raises(DomainError) as exc:
            editor_svc.chat_editor_context(
                principal=p,
                project_id="alpha-project",
                query="分析章节",
                chapter_id="alpha-tech",
            )
        assert exc.value.status == 403
        assert exc.value.code == "FORBIDDEN"

    # 2. 项目只读成员拦截 403
    def set_member_viewer(s):
        s.project_teams["alpha-project"]["members"]["alpha-manager"] = {
            "user_id": "alpha-manager",
            "project_role": "viewer",
            "volumes": ["technical", "business"],
        }
    repo.transaction(set_member_viewer)

    with pytest.raises(DomainError) as exc:
        editor_svc.chat_editor_context(
            principal=editor_setup["principal_manager"],
            project_id="alpha-project",
            query="分析章节",
            chapter_id="alpha-tech",
        )
    assert exc.value.status == 403
    assert exc.value.code == "FORBIDDEN"

    # 3. 跨租户隔离 404
    with pytest.raises(DomainError) as exc:
        editor_svc.chat_editor_context(
            principal=editor_setup["principal_beta"],
            project_id="alpha-project",
            query="分析章节",
            chapter_id="alpha-tech",
        )
    assert exc.value.status == 404
    assert exc.value.code == "NOT_FOUND"


def test_workflow_service_and_answer_card_integration(editor_setup):
    """验证 WorkflowService 与 AnswerCardService 统一门面与划词上下文联动。"""
    workflow_svc = editor_setup["workflow_svc"]
    answer_svc = editor_setup["answer_svc"]
    principal = editor_setup["principal_editor"]

    # 1. 验证 WorkflowService.editor_ai_chat
    res_wf = workflow_svc.editor_ai_chat(
        principal=principal,
        project_id="alpha-project",
        query="请润色选中语句",
        chapter_id="alpha-tech",
        selected_text="双活容灾备份方案",
    )
    assert res_wf["scene"] == "polish"
    assert res_wf["has_selected_text"] is True

    # 2. 验证 WorkflowService.build_editor_prompt_context
    ctx = workflow_svc.build_editor_prompt_context(
        project_id="alpha-project",
        chapter_id="alpha-tech",
        query="合规问答",
        selected_text="微服务架构标准",
    )
    assert len(ctx["paragraphs"]) == 3
    assert ctx["paragraphs"][0]["is_selected"] is True

    # 3. 验证 AnswerCardService.general_chat 传入 selected_text 自动无缝联动
    res_ac = answer_svc.general_chat(
        principal=principal,
        project_id="alpha-project",
        query="改写优化",
        chapter_id="alpha-tech",
        selected_text="双活容灾备份方案",
    )
    assert res_ac["scene"] == "polish"
    assert res_ac["has_selected_text"] is True
