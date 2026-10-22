# 为什么有这个文件：系统测试八角色权限矩阵、项目/分册/章节三级授权及跨公司隔离守卫。
# 它解决什么问题：验证 PRD v1.8 §2.2 与 §2.3 所定义的八角色权限边界、只读拦截、分册隔离和即时失效。

import pytest

from icg_demo.adapters import DemoModelProvider, MemoryRepository, seed_state
from icg_demo.domain import Account, Chapter, DemoService, DomainError, Principal, Project
from icg_demo.project_access import (
    LEAD_COMPANY_ROLES,
    READONLY_SYSTEM_ROLES,
    ROLE_AUDITOR,
    ROLE_BID_WRITER,
    ROLE_COMPANY_ADMIN,
    ROLE_DATA_ADMIN,
    ROLE_GROUP_ADMIN,
    ROLE_PLATFORM_ADMIN,
    ROLE_PROJECT_LEAD,
    ROLE_VIEWER,
    WRITER_COMPANY_ROLES,
    chapter_edit,
    chapter_structure,
    ensure_not_readonly,
    lead,
    normalize_role,
    require_chapter,
    require_data_admin,
    require_lead,
    require_project_writer,
    require_same_company,
    require_volume_owner,
    volume_owner,
    writable,
)


@pytest.fixture
def repo():
    return MemoryRepository(seed_state())


@pytest.fixture
def service(repo):
    return DemoService(repo, DemoModelProvider())


def create_principal(repo, user_id: str, name: str, company_id: str, role: str) -> Principal:
    """创建并登记测试会话主体。"""
    token = f"session-token-{user_id}"
    user = Account(user_id, name, company_id, role)

    def op(state):
        state.accounts[user_id] = user
        state.sessions[token] = user_id

    repo.transaction(op)
    return Principal(user, token)


def test_role_normalization_and_aliases():
    """验证八角色标准名称及其别名归一化。"""
    assert normalize_role("manager") == ROLE_PROJECT_LEAD
    assert normalize_role("project_lead") == ROLE_PROJECT_LEAD
    assert normalize_role("editor") == ROLE_BID_WRITER
    assert normalize_role("bid_writer") == ROLE_BID_WRITER
    assert normalize_role("viewer") == ROLE_VIEWER
    assert normalize_role("readonly") == ROLE_VIEWER
    assert normalize_role("auditor") == ROLE_AUDITOR
    assert normalize_role("reviewer") == ROLE_AUDITOR
    assert normalize_role("platform_admin") == ROLE_PLATFORM_ADMIN
    assert normalize_role("group_admin") == ROLE_GROUP_ADMIN
    assert normalize_role("company_admin") == ROLE_COMPANY_ADMIN
    assert normalize_role("data_admin") == ROLE_DATA_ADMIN

    assert ROLE_GROUP_ADMIN in READONLY_SYSTEM_ROLES
    assert ROLE_VIEWER in READONLY_SYSTEM_ROLES
    assert ROLE_AUDITOR in READONLY_SYSTEM_ROLES
    assert ROLE_PLATFORM_ADMIN in READONLY_SYSTEM_ROLES

    assert ROLE_PROJECT_LEAD in LEAD_COMPANY_ROLES
    assert ROLE_COMPANY_ADMIN in LEAD_COMPANY_ROLES

    assert ROLE_BID_WRITER in WRITER_COMPANY_ROLES
    assert ROLE_PROJECT_LEAD in WRITER_COMPANY_ROLES
    assert ROLE_DATA_ADMIN in WRITER_COMPANY_ROLES


def test_readonly_roles_forbidden_from_library_write(repo, service):
    """只读系统角色（集团管理员、只读成员、审核人、平台管理员）禁止执行任何写入操作。"""
    group_admin = create_principal(repo, "grp-admin", "集团总监", "group", "group_admin")
    viewer = create_principal(repo, "vw-user", "只读专员", "alpha", "viewer")
    auditor = create_principal(repo, "aud-user", "审核专员", "alpha", "auditor")
    platform_admin = create_principal(repo, "plt-admin", "平台运维", "platform", "platform_admin")

    for p in (group_admin, viewer, auditor, platform_admin):
        with pytest.raises(DomainError) as exc:
            service._writer(p)
        assert exc.value.status == 403
        assert exc.value.code == "FORBIDDEN"

        with pytest.raises(DomainError) as exc:
            ensure_not_readonly(p)
        assert exc.value.status == 403
        assert exc.value.code == "FORBIDDEN"


def test_writable_roles_permitted_by_writer_guard(repo, service):
    """可写公司角色（项目负责人、编写人、公司管理员、资料管理员）通过 _writer 门禁。"""
    lead_p = create_principal(repo, "lead-p", "项目负责人", "alpha", "project_lead")
    writer_p = create_principal(repo, "writer-p", "投标编写人", "alpha", "bid_writer")
    admin_p = create_principal(repo, "admin-p", "公司管理员", "alpha", "company_admin")
    data_p = create_principal(repo, "data-p", "资料管理员", "alpha", "data_admin")
    legacy_mgr = create_principal(repo, "mgr-p", "旧经理", "alpha", "manager")
    legacy_ed = create_principal(repo, "ed-p", "旧编辑", "alpha", "editor")

    for p in (lead_p, writer_p, admin_p, data_p, legacy_mgr, legacy_ed):
        # 应正常通过，不抛出异常
        service._writer(p)


def test_project_create_permissions(repo, service):
    """新建投标项目：仅允许项目负责人（含legacy manager）与公司管理员创建。"""
    lead_p = create_principal(repo, "p-lead-create", "负责人", "alpha", "project_lead")
    admin_p = create_principal(repo, "p-admin-create", "公司管理员", "alpha", "company_admin")
    mgr_p = create_principal(repo, "p-mgr-create", "经理", "alpha", "manager")

    # 具备资质角色创建成功
    proj1 = service.create_project(lead_p, "负责人新建项目")
    assert proj1["company_id"] == "alpha"

    proj2 = service.create_project(admin_p, "管理员新建项目")
    assert proj2["company_id"] == "alpha"

    proj3 = service.create_project(mgr_p, "旧经理新建项目")
    assert proj3["company_id"] == "alpha"

    # 无资质角色创建失败 (403 PROJECT_CREATE_FORBIDDEN)
    writer_p = create_principal(repo, "p-writer-create", "编写人", "alpha", "bid_writer")
    data_p = create_principal(repo, "p-data-create", "资料管理员", "alpha", "data_admin")
    viewer_p = create_principal(repo, "p-viewer-create", "只读成员", "alpha", "viewer")
    group_p = create_principal(repo, "p-group-create", "集团管理员", "group", "group_admin")

    for p in (writer_p, data_p, viewer_p, group_p):
        with pytest.raises(DomainError) as exc:
            service.create_project(p, "违规新建项目")
        assert exc.value.status == 403
        assert exc.value.code == "PROJECT_CREATE_FORBIDDEN"


def test_volume_lead_isolation_and_cross_volume_rejection(repo, service):
    """分册负责人权限与跨分册越权拦截：技术分册负责人只能修改技术分册章节，不能修改商务分册章节。"""
    state = repo.read()
    project_id = "alpha-project"

    # 设置分册负责人与编写人
    tech_lead = create_principal(repo, "alpha-tech-lead", "技术分册负责人", "alpha", "bid_writer")
    biz_lead = create_principal(repo, "alpha-biz-lead", "商务分册负责人", "alpha", "bid_writer")
    project_leader = create_principal(repo, "alpha-lead-overall", "整体负责人", "alpha", "project_lead")

    def config_team(s):
        team = s.project_teams[project_id]
        team["members"]["alpha-tech-lead"] = {"user_id": "alpha-tech-lead", "project_role": "writer", "volumes": ["technical"]}
        team["members"]["alpha-biz-lead"] = {"user_id": "alpha-biz-lead", "project_role": "writer", "volumes": ["business"]}
        team["members"]["alpha-lead-overall"] = {"user_id": "alpha-lead-overall", "project_role": "lead", "volumes": ["technical", "business"]}
        team["owners"]["technical"] = "alpha-tech-lead"
        team["owners"]["business"] = "alpha-biz-lead"

    repo.transaction(config_team)
    s = repo.read()

    tech_chap = s.chapters["alpha-tech"]
    biz_chap = s.chapters["alpha-business"]

    # 1. 技术分册负责人对其分册内的章节有 edit 权
    assert chapter_edit(s, tech_chap, "alpha-tech-lead") is True
    require_chapter(s, tech_lead, tech_chap)

    # 2. 技术分册负责人对商务分册章节无 edit 权 (403 CHAPTER_EDITOR_REQUIRED)
    assert chapter_edit(s, biz_chap, "alpha-tech-lead") is False
    with pytest.raises(DomainError) as exc:
        require_chapter(s, tech_lead, biz_chap)
    assert exc.value.status == 403
    assert exc.value.code == "CHAPTER_EDITOR_REQUIRED"

    # 3. 商务分册负责人对技术分册章节无 edit 权
    assert chapter_edit(s, tech_chap, "alpha-biz-lead") is False
    with pytest.raises(DomainError) as exc:
        require_chapter(s, biz_lead, tech_chap)
    assert exc.value.status == 403
    assert exc.value.code == "CHAPTER_EDITOR_REQUIRED"

    # 4. 项目负责人对两册所有章节均有编辑权
    assert chapter_edit(s, tech_chap, "alpha-lead-overall") is True
    assert chapter_edit(s, biz_chap, "alpha-lead-overall") is True
    require_chapter(s, project_leader, tech_chap)
    require_chapter(s, project_leader, biz_chap)

    # 5. 技术分册负责人结构权限仅限技术分册
    assert chapter_structure(s, tech_chap, "alpha-tech-lead") is True
    assert chapter_structure(s, biz_chap, "alpha-tech-lead") is False

    # 6. 分册负责人确认自身分册成功，跨分册被阻断
    require_volume_owner(s, tech_lead, project_id, "technical")
    with pytest.raises(DomainError) as exc:
        require_volume_owner(s, tech_lead, project_id, "business")
    assert exc.value.status == 403
    assert exc.value.code == "VOLUME_OWNER_REQUIRED"


def test_data_admin_kb_dedicated_and_project_membership_gate(repo, service):
    """资料管理员专注于知识库/资料库；非项目成员禁止操作项目章节，加入项目后遵从分工。"""
    data_admin = create_principal(repo, "alpha-data-spec", "资料专员", "alpha", "data_admin")
    s = repo.read()
    project_id = "alpha-project"
    tech_chap = s.chapters["alpha-tech"]

    # 1. 资料管理员操作知识库/资料库：通过
    require_data_admin(s, data_admin)

    # 2. 未加入项目时：writable 为 False，无法编辑章节
    assert writable(s, project_id, "alpha-data-spec") is False
    assert chapter_edit(s, tech_chap, "alpha-data-spec") is False
    with pytest.raises(DomainError) as exc:
        require_chapter(s, data_admin, tech_chap)
    assert exc.value.status == 403
    assert exc.value.code == "CHAPTER_EDITOR_REQUIRED"

    # 3. 作为只读成员加入项目：仍不可写
    repo.transaction(lambda st: st.project_teams[project_id]["members"].__setitem__(
        "alpha-data-spec", {"user_id": "alpha-data-spec", "project_role": "readonly", "volumes": ["technical"]}
    ))
    s2 = repo.read()
    assert writable(s2, project_id, "alpha-data-spec") is False

    # 4. 作为编写人加入项目并分配章节：可编辑分配的章节
    repo.transaction(lambda st: st.project_teams[project_id]["members"].__setitem__(
        "alpha-data-spec", {"user_id": "alpha-data-spec", "project_role": "writer", "volumes": ["technical"]}
    ))
    repo.transaction(lambda st: setattr(st.chapters["alpha-tech"], "assignee_id", "alpha-data-spec"))
    s3 = repo.read()
    assert writable(s3, project_id, "alpha-data-spec") is True
    assert chapter_edit(s3, s3.chapters["alpha-tech"], "alpha-data-spec") is True
    require_chapter(s3, data_admin, s3.chapters["alpha-tech"])


def test_cross_company_isolation(repo, service):
    """跨公司隔离：甲公司账号无法访问、编辑乙公司项目或章节。"""
    alpha_user = create_principal(repo, "alpha-intruder", "甲公司用户", "alpha", "project_lead")
    s = repo.read()
    beta_proj = "beta-project"
    beta_chap = s.chapters["beta-tech"]

    # require_same_company 阻断
    with pytest.raises(DomainError) as exc:
        require_same_company(s, alpha_user, beta_proj)
    assert exc.value.status == 403
    assert exc.value.code == "FORBIDDEN"

    # require_lead 阻断跨公司操作
    with pytest.raises(DomainError) as exc:
        require_lead(s, alpha_user, beta_proj)
    assert exc.value.status == 403
    assert exc.value.code == "FORBIDDEN"

    # require_chapter 阻断跨公司章节
    with pytest.raises(DomainError) as exc:
        require_chapter(s, alpha_user, beta_chap)
    assert exc.value.status == 403
    assert exc.value.code == "FORBIDDEN"


def test_revocation_immediately_invalidates_chapter_edit(repo, service):
    """撤权即时失效：失去成员资格或从编写人降级为只读，立即丧失编辑与加锁权限。"""
    writer = create_principal(repo, "alpha-assigned-writer", "分工编写人", "alpha", "bid_writer")
    project_id = "alpha-project"
    tech_chap_id = "alpha-tech"

    # 加入项目并分配技术章节
    def setup_team(s):
        s.project_teams[project_id]["members"]["alpha-assigned-writer"] = {
            "user_id": "alpha-assigned-writer", "project_role": "writer", "volumes": ["technical"]
        }
        s.chapters[tech_chap_id].assignee_id = "alpha-assigned-writer"

    repo.transaction(setup_team)
    s = repo.read()
    assert chapter_edit(s, s.chapters[tech_chap_id], "alpha-assigned-writer") is True

    # 获得编辑锁
    lease = service.acquire_lock(writer, tech_chap_id, takeover_reason=None)
    assert lease["owner_id"] == "alpha-assigned-writer"

    # 撤权：降级为 readonly
    repo.transaction(lambda st: st.project_teams[project_id]["members"].__setitem__(
        "alpha-assigned-writer", {"user_id": "alpha-assigned-writer", "project_role": "readonly", "volumes": ["technical"]}
    ))
    s2 = repo.read()
    assert chapter_edit(s2, s2.chapters[tech_chap_id], "alpha-assigned-writer") is False

    # 再次尝试以原编辑权提交正文或加锁：立即被拒
    with pytest.raises(DomainError) as exc:
        service.save_draft(writer, tech_chap_id, lease["lease_token"], base_revision=1, sequence=1, content="篡改")
    assert exc.value.status == 403
    assert exc.value.code == "CHAPTER_EDITOR_REQUIRED"


def test_team_membership_update_role_eligibility(repo, service):
    """团队成员维护：验证八角色提升为项目负责人或编写人的资质规则。"""
    from icg_demo.project_team import ProjectTeamService
    from icg_demo.workflow import WorkflowService
    from icg_demo.parsing import LocalTextParser

    workflow = WorkflowService(service, LocalTextParser())
    team_svc = ProjectTeamService(workflow)

    # 准备主账号与候选账号
    mgr = create_principal(repo, "lead-actor", "主负责人", "alpha", "project_lead")
    create_principal(repo, "cand-viewer", "只读专员", "alpha", "viewer")
    create_principal(repo, "cand-auditor", "审核人", "alpha", "auditor")
    create_principal(repo, "cand-writer", "编写人", "alpha", "bid_writer")
    create_principal(repo, "cand-data", "资料管理员", "alpha", "data_admin")
    create_principal(repo, "cand-cadmin", "公司管理员", "alpha", "company_admin")

    project_id = "alpha-project"
    repo.transaction(lambda s: s.project_teams[project_id]["members"].__setitem__(
        "lead-actor", {"user_id": "lead-actor", "project_role": "lead", "volumes": ["technical", "business"]}
    ))
    repo.transaction(lambda s: s.project_teams[project_id].__setitem__("assembly_owner_id", "lead-actor"))

    # 1. 尝试提升 viewer 为编写人 -> 422 MEMBER_ROLE_NOT_WRITABLE
    payload_viewer = {
        "members": [
            {"user_id": "lead-actor", "project_role": "lead", "volumes": ["technical", "business"]},
            {"user_id": "cand-viewer", "project_role": "writer", "volumes": ["technical"]},
        ],
        "volumes": [{"volume": "technical", "owner_id": "lead-actor"}, {"volume": "business", "owner_id": "lead-actor"}],
        "assembly_owner_id": "lead-actor",
    }
    with pytest.raises(DomainError) as exc:
        team_svc.update(mgr, project_id, payload_viewer, expected="1", key="key-team-001")
    assert exc.value.status == 422
    assert exc.value.code == "MEMBER_ROLE_NOT_WRITABLE"

    # 2. 尝试提升 auditor 为负责人 -> 422 MEMBER_ROLE_NOT_WRITABLE
    payload_auditor = {
        "members": [
            {"user_id": "lead-actor", "project_role": "lead", "volumes": ["technical", "business"]},
            {"user_id": "cand-auditor", "project_role": "writer", "volumes": ["technical"]},
        ],
        "volumes": [{"volume": "technical", "owner_id": "lead-actor"}, {"volume": "business", "owner_id": "lead-actor"}],
        "assembly_owner_id": "lead-actor",
    }
    with pytest.raises(DomainError) as exc:
        team_svc.update(mgr, project_id, payload_auditor, expected="1", key="key-team-002")
    assert exc.value.status == 422
    assert exc.value.code == "MEMBER_ROLE_NOT_WRITABLE"

    # 3. 尝试设置 bid_writer 为项目负责人 -> 422 PROJECT_LEAD_COMPANY_ROLE_REQUIRED
    payload_writer_lead = {
        "members": [
            {"user_id": "lead-actor", "project_role": "lead", "volumes": ["technical", "business"]},
            {"user_id": "cand-writer", "project_role": "lead", "volumes": ["technical", "business"]},
        ],
        "volumes": [{"volume": "technical", "owner_id": "lead-actor"}, {"volume": "business", "owner_id": "lead-actor"}],
        "assembly_owner_id": "lead-actor",
    }
    with pytest.raises(DomainError) as exc:
        team_svc.update(mgr, project_id, payload_writer_lead, expected="1", key="key-team-003")
    assert exc.value.status == 422
    assert exc.value.code == "PROJECT_LEAD_COMPANY_ROLE_REQUIRED"

    # 4. 尝试设置 data_admin 为项目负责人 -> 422 PROJECT_LEAD_COMPANY_ROLE_REQUIRED
    payload_data_lead = {
        "members": [
            {"user_id": "lead-actor", "project_role": "lead", "volumes": ["technical", "business"]},
            {"user_id": "cand-data", "project_role": "lead", "volumes": ["technical", "business"]},
        ],
        "volumes": [{"volume": "technical", "owner_id": "lead-actor"}, {"volume": "business", "owner_id": "lead-actor"}],
        "assembly_owner_id": "lead-actor",
    }
    with pytest.raises(DomainError) as exc:
        team_svc.update(mgr, project_id, payload_data_lead, expected="1", key="key-team-004")
    assert exc.value.status == 422
    assert exc.value.code == "PROJECT_LEAD_COMPANY_ROLE_REQUIRED"

    # 5. 合法配置：company_admin 为 lead，cand-writer 与 cand-data 为 writer
    payload_valid = {
        "members": [
            {"user_id": "lead-actor", "project_role": "lead", "volumes": ["technical", "business"]},
            {"user_id": "cand-cadmin", "project_role": "lead", "volumes": ["technical", "business"]},
            {"user_id": "cand-writer", "project_role": "writer", "volumes": ["technical"]},
            {"user_id": "cand-data", "project_role": "writer", "volumes": ["business"]},
            {"user_id": "cand-viewer", "project_role": "readonly", "volumes": ["technical", "business"]},
        ],
        "volumes": [{"volume": "technical", "owner_id": "cand-writer"}, {"volume": "business", "owner_id": "cand-data"}],
        "assembly_owner_id": "lead-actor",
    }
    res = team_svc.update(mgr, project_id, payload_valid, expected="1", key="key-team-005")
    assert len(res["team"]["members"]) == 5


def test_require_project_writer_boundary(repo, service):
    """测试 require_project_writer 门禁：可写成员、只读拦截与跨公司隔离。"""
    writer = create_principal(repo, "pw-writer", "编写人", "alpha", "bid_writer")
    viewer = create_principal(repo, "pw-viewer", "只读", "alpha", "viewer")
    group_admin = create_principal(repo, "pw-group", "集团", "group", "group_admin")
    outsider = create_principal(repo, "pw-outsider", "乙公司", "beta", "bid_writer")

    project_id = "alpha-project"
    repo.transaction(lambda s: s.project_teams[project_id]["members"].__setitem__(
        "pw-writer", {"user_id": "pw-writer", "project_role": "writer", "volumes": ["technical"]}
    ))
    repo.transaction(lambda s: s.project_teams[project_id]["members"].__setitem__(
        "pw-viewer", {"user_id": "pw-viewer", "project_role": "readonly", "volumes": ["technical"]}
    ))

    s = repo.read()

    # 可写编写人正常通过
    require_project_writer(s, writer, project_id)

    # 只读成员阻断为 403 FORBIDDEN
    with pytest.raises(DomainError) as exc:
        require_project_writer(s, viewer, project_id)
    assert exc.value.status == 403
    assert exc.value.code == "FORBIDDEN"

    # 集团管理员阻断为 403 FORBIDDEN
    with pytest.raises(DomainError) as exc:
        require_project_writer(s, group_admin, project_id)
    assert exc.value.status == 403
    assert exc.value.code == "FORBIDDEN"

    # 跨公司阻断为 403 FORBIDDEN
    with pytest.raises(DomainError) as exc:
        require_project_writer(s, outsider, project_id)
    assert exc.value.status == 403
    assert exc.value.code == "FORBIDDEN"
