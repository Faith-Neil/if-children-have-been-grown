# 为什么有这个文件：验证插入为引用功能完整闭环（APP-M2-T183，ISSUE-007，PRD v1.8 §5.11.15 规则 4、§5.11.6）。
# 它解决什么问题：
# 1. 门禁 1（编辑锁守卫）：验证调用方持有目标章节的有效编辑租约（若无租约、租约过期、令牌不匹配或跨会话所有者不符，抛出 423 LOCK_LOST）。
# 2. 门禁 2（卡片类型与资格拦截）：
#    - 仅 source_type="company_library" 且 can_insert=True 的合格资料卡允许执行插入；
#    - 本项目数据卡（source_type="project_data"）严格禁止插入（抛出 403 FORBIDDEN）；
#    - 已过期（400 EVIDENCE_EXPIRED）、受限无权（403 FORBIDDEN）或未确认/不可用（400 EVIDENCE_NOT_USABLE）严格禁止插入。
# 3. 门禁 3（引用标记与正文写入）：
#    - 将资料内容格式化为带溯源标识的引用节点（[证:ID]），写入目标段落（追加 append 或替换 replace），正文 revision 与项目 revision 自增；
# 4. 门禁 4（增量复查标记与审计历史）：
#    - 插入完成后，章节 incremental_check_status 置为 "pending"，工作流章节状态置为 "人工已处理"，
#    - 生成版本历史变更记录（edit_mode="insert_answer_card", version_origin="assistant_edit", 包含完整 citation 信息），
#    - 触发增量复查任务记录（incremental_checks 记录），清理草稿，生成审计日志。
# 5. 跨租户隔离与未找到校验：404 NOT_FOUND。
# 6. WorkflowService.insert_answer_card 委托调用验证。

import pytest

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.answer_card import AnswerCard, AnswerCardService
from icg_demo.domain import DemoService, DomainError, Principal
from icg_demo.ports import ParserProvider
from icg_demo.workflow import WorkflowService


class DummyParser(ParserProvider):
    def parse(self, filename: str, content: bytes) -> dict:
        return {"title": "测试文件", "pagination": "none", "pages": [], "warnings": []}


@pytest.fixture
def insert_setup():
    state = seed_state()
    project = state.projects["alpha-project"]
    project.deadline = "2026-12-31T17:00:00+08:00"

    # 初始化工作流数据
    workflow = state.workflows.setdefault(project.id, {
        "files": {},
        "requirements": {
            "req-001": {
                "id": "req-001",
                "text": "★技术要求：投标人应缴纳投标保证金人民币20万元整。",
                "category": "商务",
                "status": "confirmed",
                "response": "20万元整",
                "unit": "万元",
                "source": {"file_id": "file-1", "page": 4},
            },
        },
        "facts": {
            "fact-001": {
                "id": "fact-001",
                "key": "服务期限",
                "value": "12个月",
                "status": "confirmed",
                "unit": "月",
                "source_type": "parsed",
            },
        },
        "conflicts": {},
        "checks": {},
        "candidates": {},
        "exports": {},
        "parse_confirmed": True,
        "plan_confirmed": True,
        "chapter_statuses": {},
        "incremental_checks": {},
        "sla": "alpha-sla-tmpl",
    })

    # 初始化公司资料库
    state.library.update({
        "lib-cert-valid": {
            "id": "lib-cert-valid",
            "company_id": "alpha",
            "name": "张三 Oracle OCP 认证",
            "type": "person_cert",
            "content": "持证人张三，持有 Oracle OCP 认证，专业数据库运维工程师。",
            "status": "confirmed",
            "valid_until": "2027-12-31",
            "is_restricted": False,
            "revision": 1,
        },
        "lib-qual-valid": {
            "id": "lib-qual-valid",
            "company_id": "alpha",
            "name": "甲公司涉密资质认证",
            "type": "qualification",
            "content": "甲公司持有涉密信息系统集成乙级资质。",
            "status": "confirmed",
            "valid_until": "2028-12-31",
            "is_restricted": False,
            "revision": 1,
        },
        "lib-contract-valid": {
            "id": "lib-contract-valid",
            "company_id": "alpha",
            "name": "某省政务大厅运维项目",
            "type": "contract",
            "content": "合同金额1200万元，服务范围涵盖软硬件运维。",
            "status": "confirmed",
            "valid_until": "2027-12-31",
            "is_restricted": False,
            "revision": 1,
        },
        "lib-cert-pending": {
            "id": "lib-cert-pending",
            "company_id": "alpha",
            "name": "李四 PMP 认证",
            "type": "person_cert",
            "content": "持证人李四，持有 PMP 证书。",
            "status": "pending",
            "valid_until": "2027-12-31",
            "is_restricted": False,
            "revision": 1,
        },
        "lib-cert-expired": {
            "id": "lib-cert-expired",
            "company_id": "alpha",
            "name": "王五 软考高级网络规划设计师",
            "type": "person_cert",
            "content": "持证人王五，持有软考高级证书。",
            "status": "confirmed",
            "valid_until": "2025-06-30",
            "is_restricted": False,
            "revision": 1,
        },
        "lib-qual-restricted": {
            "id": "lib-qual-restricted",
            "company_id": "alpha",
            "name": "甲公司军工保密资格认证",
            "type": "qualification",
            "content": "军工二级保密资格，严格受限资料。",
            "status": "confirmed",
            "valid_until": "2028-12-31",
            "is_restricted": True,
            "revision": 1,
        },
        "lib-beta-cert": {
            "id": "lib-beta-cert",
            "company_id": "beta",
            "name": "乙公司专属资质",
            "type": "qualification",
            "content": "乙公司独有资质",
            "status": "confirmed",
            "valid_until": "2027-12-31",
            "is_restricted": False,
            "revision": 1,
        },
    })

    # 初始化 SLA 模板
    state.sla_templates["alpha-sla-tmpl"] = {
        "id": "alpha-sla-tmpl",
        "company_id": "alpha",
        "template_name": "标准云服务SLA承诺",
        "levels": [
            {"level": "一级", "response_minutes": 15},
            {"level": "二级", "response_minutes": 30},
        ],
    }

    # 准备章节草稿
    chapter = state.chapters["alpha-tech"]
    chapter.content = "第一节 系统总体架构设计说明。\n[待补充资质证书证明]\n第二节 数据库运维与灾备。"
    chapter.revision = 1
    chapter.drafts["alpha-editor"] = "用户未提交的草稿内容"

    state.sessions.update({
        "session-alpha-editor": "alpha-editor",
        "session-alpha-admin": "alpha-company-admin",
        "session-beta-editor": "beta-editor",
    })

    repo = MemoryRepository(state)
    demo = DemoService(repo, None)
    workflow_svc = WorkflowService(demo, DummyParser())
    answer_svc = AnswerCardService(demo)

    principal_editor = Principal(state.accounts["alpha-editor"], "session-alpha-editor")
    principal_admin = Principal(state.accounts["alpha-company-admin"], "session-alpha-admin")
    principal_beta = Principal(state.accounts["beta-editor"], "session-beta-editor")

    return {
        "state": state,
        "project": project,
        "repo": repo,
        "demo": demo,
        "workflow_svc": workflow_svc,
        "answer_svc": answer_svc,
        "principal_editor": principal_editor,
        "principal_admin": principal_admin,
        "principal_beta": principal_beta,
    }


def test_insert_answer_card_success_append(insert_setup):
    """验证合格公司资料卡（追加模式）成功插入并满足全部 4 个门禁状态。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    # 取得编辑租约
    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    # 构造合格卡片数据（通过 direct query 或直接组装）
    card_dict = {
        "title": "本公司资料 · 资质证书",
        "direct_query_domain": "person_cert",
        "source_type": "company_library",
        "source": "本公司资料库",
        "can_insert": True,
        "records": [{
            "id": "lib-cert-valid",
            "name": "张三 Oracle OCP 认证",
            "type": "person_cert",
            "content": "持证人张三，持有 Oracle OCP 认证，专业数据库运维工程师。",
            "valid_until": "2027-12-31",
            "confirm_status": "confirmed",
            "validity_status": "valid",
            "can_insert": True,
        }],
    }

    initial_project_rev = insert_setup["project"].revision

    res = answer_svc.insert_answer_card(
        principal=principal,
        project_id="alpha-project",
        chapter_id="alpha-tech",
        card_data=card_dict,
        lease_token=lease_token,
        item_id="lib-cert-valid",
        insert_mode="append",
    )

    # 1. 验证响应字段
    assert res["chapter_id"] == "alpha-tech"
    assert res["revision"] == 2
    assert "[证:lib-cert-valid]" in res["inserted_text"]
    assert "[证:lib-cert-valid]" in res["content"]
    assert res["incremental_check_status"] == "pending"
    assert res["chapter_status"] == "人工已处理"

    # 2. 验证引用对象格式与审计溯源
    citation = res["citation"]
    assert citation["id"].startswith("cite-")
    assert citation["source_type"] == "company_library"
    assert citation["item_id"] == "lib-cert-valid"
    assert citation["tag"] == "[证:lib-cert-valid]"
    assert citation["actor_id"] == principal.user.id
    assert "张三" in citation["cite_text"]

    # 3. 验证章节与项目内部持久化状态
    state = insert_setup["repo"].read()
    chapter = state.chapters["alpha-tech"]
    project = state.projects["alpha-project"]

    assert chapter.revision == 2
    assert project.revision == initial_project_rev + 1
    assert chapter.incremental_check_status == "pending"
    # 草稿已被清理
    assert principal.user.id not in chapter.drafts

    # 4. 验证版本变更记录
    assert len(chapter.versions) == 2
    latest_version = chapter.versions[-1]
    assert latest_version["revision"] == 2
    assert latest_version["edit_mode"] == "insert_answer_card"
    assert latest_version["version_origin"] == "assistant_edit"
    assert latest_version["citation"]["item_id"] == "lib-cert-valid"
    assert latest_version["incremental_check_status"] == "pending"

    # 5. 验证工作流增量复查标记
    workflow = state.workflows["alpha-project"]
    assert workflow["chapter_statuses"]["alpha-tech"] == "人工已处理"
    check_entry = workflow["incremental_checks"]["alpha-tech"]
    assert check_entry["status"] == "pending"
    assert check_entry["revision"] == 2
    assert check_entry["operation_type"] == "insert_answer_card"
    assert check_entry["citation_id"] == citation["id"]


def test_insert_answer_card_success_replace(insert_setup):
    """验证合格公司资料卡（替换模式）精准替换占位段落。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    target_para = "[待补充资质证书证明]"

    card_dict = {
        "title": "本公司资料 · 资质",
        "direct_query_domain": "qualification",
        "source_type": "company_library",
        "source": "本公司资料库",
        "can_insert": True,
        "records": [{
            "id": "lib-qual-valid",
            "name": "甲公司涉密资质认证",
            "type": "qualification",
            "content": "甲公司持有涉密信息系统集成乙级资质。",
            "valid_until": "2028-12-31",
            "can_insert": True,
        }],
    }

    res = answer_svc.insert_answer_card(
        principal=principal,
        project_id="alpha-project",
        chapter_id="alpha-tech",
        card_data=card_dict,
        lease_token=lease_token,
        item_id="lib-qual-valid",
        insert_mode="replace",
        target_paragraph=target_para,
    )

    # 占位段落被完全替换
    assert target_para not in res["content"]
    assert "[证:lib-qual-valid] 公司持有甲公司涉密资质认证" in res["content"]
    assert "第一节 系统总体架构设计说明。" in res["content"]
    assert "第二节 数据库运维与灾备。" in res["content"]


def test_insert_answer_card_sla_template(insert_setup):
    """验证 SLA 服务承诺卡片插入格式化。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    card_dict = {
        "title": "本公司资料 · SLA服务承诺",
        "direct_query_domain": "sla",
        "source_type": "company_library",
        "source": "本公司SLA服务承诺",
        "can_insert": True,
        "records": [{
            "id": "alpha-sla-tmpl",
            "name": "标准云服务SLA承诺",
            "type": "sla",
            "can_insert": True,
        }],
    }

    res = answer_svc.insert_answer_card(
        principal=principal,
        project_id="alpha-project",
        chapter_id="alpha-tech",
        card_data=card_dict,
        lease_token=lease_token,
        item_id="alpha-sla-tmpl",
    )

    assert "[证:alpha-sla-tmpl]" in res["inserted_text"]
    assert "公司提供 SLA 服务承诺：标准云服务SLA承诺" in res["inserted_text"]
    assert "一级响应时限 15 分钟" in res["inserted_text"]


def test_gate_1_missing_or_empty_lease(insert_setup):
    """门禁 1：未提供租约令牌或章节未加锁，严格拦截抛出 423 LOCK_LOST。"""
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    card_dict = {
        "title": "本公司资料",
        "direct_query_domain": "person_cert",
        "source_type": "company_library",
        "can_insert": True,
        "records": [{"id": "lib-cert-valid"}],
    }

    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="alpha-tech",
            card_data=card_dict,
            lease_token="",
            item_id="lib-cert-valid",
        )
    assert exc_info.value.status == 423
    assert exc_info.value.code == "LOCK_LOST"


def test_gate_1_expired_lease(insert_setup):
    """门禁 1：租约已过期，严格拦截抛出 423 LOCK_LOST。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    # 取得锁后手动置为过期时间
    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    def expire_lock(state):
        state.chapters["alpha-tech"].lock.expires_at = demo._now() - 10
    insert_setup["repo"].transaction(expire_lock)

    card_dict = {
        "title": "本公司资料",
        "direct_query_domain": "person_cert",
        "source_type": "company_library",
        "can_insert": True,
        "records": [{"id": "lib-cert-valid"}],
    }

    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="alpha-tech",
            card_data=card_dict,
            lease_token=lease_token,
            item_id="lib-cert-valid",
        )
    assert exc_info.value.status == 423
    assert exc_info.value.code == "LOCK_LOST"


def test_gate_1_mismatched_token_or_other_user_lease(insert_setup):
    """门禁 1：使用他人租约令牌或错误令牌，严格拦截抛出 423 LOCK_LOST。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    fake_token = "invalid-token-12345"

    card_dict = {
        "title": "本公司资料",
        "direct_query_domain": "person_cert",
        "source_type": "company_library",
        "can_insert": True,
        "records": [{"id": "lib-cert-valid"}],
    }

    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="alpha-tech",
            card_data=card_dict,
            lease_token=fake_token,
            item_id="lib-cert-valid",
        )
    assert exc_info.value.status == 423
    assert exc_info.value.code == "LOCK_LOST"


def test_gate_2_project_data_strictly_forbidden(insert_setup):
    """门禁 2：本项目结构化数据卡（招标要求、项目事实、检查结果等）严禁插入正文，抛出 403 FORBIDDEN。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    # 尝试插入 source_type="project_data" 卡片
    project_cards = [
        {"source_type": "project_data", "direct_query_domain": "tender_requirement", "can_insert": False},
        {"source_type": "project_data", "direct_query_domain": "project_fact", "can_insert": False},
        {"source_type": "project_data", "direct_query_domain": "response_matrix", "can_insert": False},
        {"source_type": "project_data", "direct_query_domain": "check_result", "can_insert": False},
    ]

    for card in project_cards:
        with pytest.raises(DomainError) as exc_info:
            answer_svc.insert_answer_card(
                principal=principal,
                project_id="alpha-project",
                chapter_id="alpha-tech",
                card_data=card,
                lease_token=lease_token,
            )
        assert exc_info.value.status == 403
        assert exc_info.value.code == "FORBIDDEN"
        assert "本项目结构化数据卡禁止插入正文" in str(exc_info.value)


def test_gate_2_expired_evidence_blocked(insert_setup):
    """门禁 2：已过期的公司资料严格拦截，抛出 409 EVIDENCE_EXPIRED。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    # 1. 前置 card can_insert=False, reason="已过期"
    card_precheck_expired = {
        "source_type": "company_library",
        "can_insert": False,
        "insert_disabled_reason": "已过期",
        "records": [{"id": "lib-cert-expired"}],
    }
    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="alpha-tech",
            card_data=card_precheck_expired,
            lease_token=lease_token,
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "EVIDENCE_EXPIRED"

    # 2. 伪造前端 can_insert=True 尝试绕过，后端校验实体状态再次拦截
    card_tampered = {
        "source_type": "company_library",
        "can_insert": True,
        "direct_query_domain": "person_cert",
        "records": [{"id": "lib-cert-expired"}],
    }
    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="alpha-tech",
            card_data=card_tampered,
            lease_token=lease_token,
            item_id="lib-cert-expired",
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "EVIDENCE_EXPIRED"


def test_gate_2_unconfirmed_evidence_blocked(insert_setup):
    """门禁 2：未确认状态的公司资料严格拦截，抛出 409 EVIDENCE_NOT_USABLE。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    # 1. 前置 card can_insert=False, reason="未确认"
    card_precheck = {
        "source_type": "company_library",
        "can_insert": False,
        "insert_disabled_reason": "未确认",
        "records": [{"id": "lib-cert-pending"}],
    }
    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="alpha-tech",
            card_data=card_precheck,
            lease_token=lease_token,
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "EVIDENCE_NOT_USABLE"

    # 2. 伪造前端 can_insert=True 尝试绕过，后端校验实体状态再次拦截
    card_tampered = {
        "source_type": "company_library",
        "can_insert": True,
        "direct_query_domain": "person_cert",
        "records": [{"id": "lib-cert-pending"}],
    }
    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="alpha-tech",
            card_data=card_tampered,
            lease_token=lease_token,
            item_id="lib-cert-pending",
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "EVIDENCE_NOT_USABLE"


def test_gate_2_restricted_evidence_unauthorized_blocked(insert_setup):
    """门禁 2：普通编写人尝试引用未授权的受限资料，严格拦截抛出 403 FORBIDDEN。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    card_restricted = {
        "source_type": "company_library",
        "can_insert": True,
        "direct_query_domain": "qualification",
        "records": [{"id": "lib-qual-restricted"}],
    }

    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="alpha-tech",
            card_data=card_restricted,
            lease_token=lease_token,
            item_id="lib-qual-restricted",
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_cross_tenant_and_not_found_isolation(insert_setup):
    """验证跨租户或不存在的资料记录、章节与项目严格隔离，抛出 404 NOT_FOUND。"""
    demo = insert_setup["demo"]
    answer_svc = insert_setup["answer_svc"]
    principal = insert_setup["principal_editor"]

    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    # 1. 尝试引用属于乙公司 (beta) 的资料
    card_beta = {
        "source_type": "company_library",
        "can_insert": True,
        "direct_query_domain": "qualification",
        "records": [{"id": "lib-beta-cert"}],
    }
    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="alpha-tech",
            card_data=card_beta,
            lease_token=lease_token,
            item_id="lib-beta-cert",
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"

    # 2. 尝试操作不存在的章节
    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="alpha-project",
            chapter_id="non-existent-chapter",
            card_data=card_beta,
            lease_token=lease_token,
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"

    # 3. 尝试跨项目操作乙公司项目
    with pytest.raises(DomainError) as exc_info:
        answer_svc.insert_answer_card(
            principal=principal,
            project_id="beta-project",
            chapter_id="alpha-tech",
            card_data=card_beta,
            lease_token=lease_token,
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"


def test_workflow_service_delegation(insert_setup):
    """验证 WorkflowService 统一门面方法正确委托给 AnswerCardService。"""
    demo = insert_setup["demo"]
    workflow_svc = insert_setup["workflow_svc"]
    principal = insert_setup["principal_editor"]

    lock_res = demo.acquire_lock(principal, "alpha-tech", None)
    lease_token = lock_res["lease_token"]

    card_dict = {
        "title": "本公司资料 · 业绩合同",
        "direct_query_domain": "contract",
        "source_type": "company_library",
        "source": "本公司资料库",
        "can_insert": True,
        "records": [{
            "id": "lib-contract-valid",
            "name": "某省政务大厅运维项目",
            "type": "contract",
            "content": "合同金额1200万元，服务范围涵盖软硬件运维。",
            "valid_until": "2027-12-31",
            "confirm_status": "confirmed",
            "validity_status": "valid",
            "can_insert": True,
        }],
    }

    res = workflow_svc.insert_answer_card(
        principal=principal,
        project_id="alpha-project",
        chapter_id="alpha-tech",
        card_data=card_dict,
        lease_token=lease_token,
        item_id="lib-contract-valid",
        insert_mode="append",
    )

    assert res["chapter_id"] == "alpha-tech"
    assert res["revision"] == 2
    assert "[证:lib-contract-valid]" in res["inserted_text"]
    assert "某省政务大厅运维项目" in res["inserted_text"]
    assert res["incremental_check_status"] == "pending"
    assert res["chapter_status"] == "人工已处理"
