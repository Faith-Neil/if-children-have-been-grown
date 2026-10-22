# 为什么有这个文件：独立测试大纲写作方案服务（BE-OUTLINE-PLAN-SERVICE）。
# 它解决什么问题：
# 1. 验证大纲树读取与层级编号、章节分类、增值理由及关联条款结构；
# 2. 验证星号条款（★）与废标条款对应章节绝对禁止标记为“不适用”（直接抛出 400 INVALID_ACTION）；
# 3. 验证三级权限门禁：项目负责人全项目放行、分册负责人本分册放行、跨分册未授权修改拦截 403 FORBIDDEN 与只读角色拦截 403；
# 4. 验证单事务方案确认后章节 revision 与项目 revision 原子自增；
# 5. 验证纯内存模式（MemoryRepository）下完全离线透明降级。

from datetime import datetime, timezone
import pytest

from icg_demo.adapters import DemoModelProvider, MemoryRepository, seed_state
from icg_demo.domain import Chapter, DemoService, DemoState, DomainError, Principal
from icg_demo.outline_service import OutlinePlanError, OutlinePlanService


@pytest.fixture
def service():
    state = seed_state()
    repo = MemoryRepository()
    repo.transaction(lambda s: s.__dict__.update(state.__dict__))
    demo = DemoService(repo, DemoModelProvider())
    demo.outline_service = OutlinePlanService(demo)
    return demo.outline_service


@pytest.fixture
def principals():
    state = seed_state()
    return {
        "manager": Principal(state.accounts["alpha-manager"], "tok-alpha-manager"),
        "editor": Principal(state.accounts["alpha-editor"], "tok-alpha-editor"),
        "viewer": Principal(state.accounts["alpha-viewer"], "tok-alpha-viewer"),
        "outsider": Principal(state.accounts["beta-editor"], "tok-beta-editor"),
    }


def test_get_outline_plan_tree_and_metadata(service):
    # 准备工作流关联条款：包含星号条款与废标条款
    def init_reqs(state: DemoState):
        wf = state.workflows.setdefault("alpha-project", {})
        wf["requirements"] = {
            "req-01": {
                "id": "req-01",
                "chapter_id": "alpha-tech",
                "clause": "★系统高可用故障切换时间小于30秒",
                "volume": "technical",
                "mandatory": True,
            },
            "req-02": {
                "id": "req-02",
                "chapter_id": "alpha-business",
                "clause": "投标人需提供近三年财务审计报告，未提供按废标处理",
                "volume": "business",
                "disqualified": True,
            },
        }

    service.repository.transaction(init_reqs)

    plan = service.get_outline_plan("alpha-project")
    assert plan["project_id"] == "alpha-project"
    assert plan["total_chapters"] == 2
    assert plan["confirmed_count"] == 0
    assert plan["unconfirmed_count"] == 2
    assert len(plan["tree"]) == 2  # technical 与 business 两个分册根节点

    # 验证技术分册章节元数据
    tech_node = next(c for c in plan["chapters"] if c["chapter_id"] == "alpha-tech")
    assert tech_node["volume"] == "technical"
    assert tech_node["level"] == 1
    assert tech_node["section_number"] == "1.0"
    assert tech_node["chapter_type"] == "specialized"  # 识别为专项章节
    assert tech_node["has_asterisk"] is True
    assert tech_node["has_disqualified"] is False
    assert tech_node["is_mandatory"] is True
    assert tech_node["associated_clause_ids"] == ["req-01"]
    assert tech_node["confirmation_status"] == "unconfirmed"
    assert tech_node["assignee_id"] == "alpha-editor"
    assert tech_node["assignee_name"] is not None
    assert len(tech_node["value_added_reason"]) > 0

    # 验证商务分册章节元数据
    biz_node = next(c for c in plan["chapters"] if c["chapter_id"] == "alpha-business")
    assert biz_node["volume"] == "business"
    assert biz_node["has_asterisk"] is False
    assert biz_node["has_disqualified"] is True
    assert biz_node["is_mandatory"] is True
    assert biz_node["associated_clause_ids"] == ["req-02"]

    # 验证按分册过滤读取
    tech_plan = service.get_outline_plan("alpha-project", volume_id="technical")
    assert tech_plan["total_chapters"] == 1
    assert tech_plan["chapters"][0]["chapter_id"] == "alpha-tech"

    # 验证不存在项目抛出 404
    with pytest.raises(DomainError) as exc_info:
        service.get_outline_plan("non-existent-project")
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"


def test_asterisk_and_disqualified_cannot_be_marked_not_applicable(service, principals):
    # 植入星号与废标条款
    def init_reqs(state: DemoState):
        wf = state.workflows.setdefault("alpha-project", {})
        wf["requirements"] = {
            "req-star": {
                "id": "req-star",
                "chapter_id": "alpha-tech",
                "clause": "★关键技术指标响应",
                "volume": "technical",
                "mandatory": True,
            },
            "req-disq": {
                "id": "req-disq",
                "chapter_id": "alpha-business",
                "clause": "无违法违规记录承诺（废标项）",
                "volume": "business",
                "disqualified": True,
            },
        }

    service.repository.transaction(init_reqs)

    manager = principals["manager"]

    # 1. 尝试将带有星号条款的章节标记为 applicable=False
    with pytest.raises(OutlinePlanError) as exc_info:
        service.confirm_outline_plan(
            project_id="alpha-project",
            chapter_id="alpha-tech",
            plan_data={"applicable": False},
            principal=manager,
        )
    assert exc_info.value.status == 400
    assert exc_info.value.code == "INVALID_ACTION"
    assert "星号条款" in exc_info.value.message or "禁止标记为“不适用”" in exc_info.value.message

    # 2. 尝试通过 action="mark_not_applicable" 标记废标条款章节
    with pytest.raises(OutlinePlanError) as exc_info:
        service.confirm_outline_plan(
            project_id="alpha-project",
            chapter_id="alpha-business",
            plan_data={"action": "mark_not_applicable"},
            principal=manager,
        )
    assert exc_info.value.status == 400
    assert exc_info.value.code == "INVALID_ACTION"

    # 3. 尝试在评分行中将星号条款标记为 applicable=False
    with pytest.raises(OutlinePlanError) as exc_info:
        service.confirm_outline_plan(
            project_id="alpha-project",
            chapter_id="alpha-tech",
            plan_data={
                "scoring_rows": [
                    {"id": "sr-1", "clause": "★核心指标", "asterisk": True, "applicable": False}
                ]
            },
            principal=manager,
        )
    assert exc_info.value.status == 400
    assert exc_info.value.code == "INVALID_ACTION"


def test_permission_gates_role_and_volume_owner(service, principals):
    # 配置分册负责人分工
    def configure_team(state: DemoState):
        team = state.project_teams["alpha-project"]
        # alpha-editor 为技术分册负责人，不是商务分册负责人
        team["owners"]["technical"] = "alpha-editor"
        team["owners"]["business"] = "alpha-manager"

    service.repository.transaction(configure_team)

    viewer = principals["viewer"]
    editor = principals["editor"]
    manager = principals["manager"]
    outsider = principals["outsider"]

    # 1. 只读角色（viewer）拦截 403 FORBIDDEN
    with pytest.raises(DomainError) as exc_info:
        service.confirm_outline_plan(
            project_id="alpha-project",
            chapter_id="alpha-tech",
            plan_data={"applicable": True},
            principal=viewer,
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"

    # 2. 非项目成员（outsider）拦截 403 FORBIDDEN
    with pytest.raises(DomainError) as exc_info:
        service.confirm_outline_plan(
            project_id="alpha-project",
            chapter_id="alpha-tech",
            plan_data={"applicable": True},
            principal=outsider,
        )
    assert exc_info.value.status == 404 or exc_info.value.status == 403

    # 3. 分册负责人（editor）修改本人管辖的技术分册：放行通过
    res_tech = service.confirm_outline_plan(
        project_id="alpha-project",
        chapter_id="alpha-tech",
        plan_data={"applicable": True, "chapter_type": "specialized"},
        principal=editor,
    )
    assert res_tech["confirmed_count"] == 1

    # 4. 分册负责人（editor）跨分册修改商务分册：拦截 403 FORBIDDEN
    with pytest.raises(DomainError) as exc_info:
        service.confirm_outline_plan(
            project_id="alpha-project",
            chapter_id="alpha-business",
            plan_data={"applicable": True},
            principal=editor,
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"
    assert "无权修改非本人负责" in exc_info.value.message or "FORBIDDEN" in exc_info.value.code

    # 5. 项目负责人（manager）全项目放行：确认商务分册成功
    res_biz = service.confirm_outline_plan(
        project_id="alpha-project",
        chapter_id="alpha-business",
        plan_data={"applicable": True, "chapter_type": "general"},
        principal=manager,
    )
    assert res_biz["confirmed_count"] == 1


def test_atomic_revision_increment_on_confirmation(service, principals):
    # 初始状态：版本均为 1
    state_before = service.repository.read()
    ch_before = state_before.chapters["alpha-tech"]
    proj_before = state_before.projects["alpha-project"]
    assert ch_before.revision == 1
    assert proj_before.revision == 1

    manager = principals["manager"]
    plan_data = {
        "applicable": True,
        "chapter_type": "specialized",
        "value_added_reason": "引入自动化监控告警组件，提升响应效率30%",
        "writing_points": "1. 架构总览; 2. 冗余设计; 3. 故障切换演练",
        "target_length": 3000,
    }

    # 执行确认
    result = service.confirm_outline_plan(
        project_id="alpha-project",
        chapter_id="alpha-tech",
        plan_data=plan_data,
        principal=manager,
    )

    assert result["confirmed_count"] == 1
    assert result["project_revision"] == 2

    # 验证单事务提交后，章节 revision 自增为 2，项目 revision 自增为 2
    state_after = service.repository.read()
    ch_after = state_after.chapters["alpha-tech"]
    proj_after = state_after.projects["alpha-project"]

    assert ch_after.revision == 2
    assert proj_after.revision == 2
    assert len(ch_after.versions) >= 2
    assert ch_after.versions[-1]["revision"] == 2
    assert "大纲写作方案确认" in ch_after.versions[-1]["change_reason"]

    # 验证大纲树读取后状态为 confirmed
    plan = service.get_outline_plan("alpha-project")
    tech_node = next(c for c in plan["chapters"] if c["chapter_id"] == "alpha-tech")
    assert tech_node["confirmation_status"] == "confirmed"
    assert tech_node["confirmed_by"] == manager.user.id
    assert tech_node["value_added_reason"] == plan_data["value_added_reason"]
    assert plan["confirmed_count"] == 1
    assert plan["unconfirmed_count"] == 1


def test_batch_confirm_by_volume(service, principals):
    manager = principals["manager"]

    # 新建第三个属于 technical 分册的章节以验证批量确认
    def add_chapter(state: DemoState):
        ch3 = Chapter("alpha-tech-extra", "alpha-project", "技术架构说明", "technical", "补充架构说明")
        ch3.assignee_id = "alpha-editor"
        ch3.versions.append({"revision": 1, "content": "补充架构说明", "actor_id": "seed", "created_at": "2026-10-10T00:00:00Z"})
        state.chapters[ch3.id] = ch3

    service.repository.transaction(add_chapter)

    # 按分册批量确认技术分册
    result = service.confirm_outline_plan(
        project_id="alpha-project",
        chapter_id=None,
        volume_id="technical",
        plan_data={"applicable": True, "chapter_type": "specialized"},
        principal=manager,
    )

    # 验证技术分册下的全部 2 个章节均被原子确认
    assert result["confirmed_count"] == 2

    state = service.repository.read()
    assert state.chapters["alpha-tech"].revision == 2
    assert state.chapters["alpha-tech-extra"].revision == 2
    # 商务分册未确认，revision 保持为 1
    assert state.chapters["alpha-business"].revision == 1


def test_memory_repository_polymorphism_offline(service, principals):
    # 纯内存模式纯洁性测试：无需真实 MySQL 依赖即可完成完整的读取、强校验拦截与持久化流转
    assert service.repository.mode == "memory"

    manager = principals["manager"]
    res = service.confirm_outline_plan(
        project_id="alpha-project",
        chapter_id="alpha-tech",
        plan_data={"applicable": True, "chapter_type": "specialized"},
        principal=manager,
    )
    assert res["confirmed_count"] == 1
    plan = service.get_outline_plan("alpha-project")
    assert plan["confirmed_count"] == 1
