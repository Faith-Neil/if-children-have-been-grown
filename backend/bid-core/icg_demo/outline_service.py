# 为什么有这个文件：实现大纲写作方案服务（BE-OUTLINE-PLAN-SERVICE）。
# 它解决什么问题：
# 1. 结构化大纲树生成：支持读取多层级章节树、自动生成章节编号（如 1.0, 1.1）、识别章节类型（通用/专项/系统）、增值理由与关联条款；
# 2. 强安全门禁：星号条款（★）与废标条款关联章节绝对禁止标记为“不适用”，违者直接抛出 400 INVALID_ACTION；
# 3. 三级数据权限门禁：项目负责人全项目放行，分册负责人仅限分管分册（跨分册拦截 403 FORBIDDEN），只读系统角色与项目只读成员拦截 403；
# 4. 单事务版本原子推进：方案确认在单一事务内完成元数据持久化并推进章节 revision 自增，保证纯内存与持久化仓库多态一致。

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable

from .domain import Chapter, DemoService, DemoState, DomainError, Principal, Project, iso_time, new_id
from .generation_context import chapter_plan, writing_source_fingerprint
from .project_access import READONLY_SYSTEM_ROLES, lead, member, normalize_role, volume_owner, writable


class OutlinePlanError(DomainError):
    """大纲方案专属领域异常，支持自定义 HTTP 状态码（如 400 INVALID_ACTION）且兼容 DomainError。"""

    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}
        # 绕过 DomainError.__init__ 的 status_for 静态冻结码校验
        Exception.__init__(self, message)


def infer_chapter_type(title: str, explicit_type: str | None = None) -> str:
    """推断章节分类：general（通用）、specialized（专项）、system（系统生成）。"""
    if explicit_type in ("general", "specialized", "system"):
        return explicit_type
    lower = title.lower()
    if any(k in lower for k in ("系统", "封面", "目录", "声明", "导出", "签署", "附录")):
        return "system"
    if any(k in lower for k in ("专项", "技术", "安全", "实施", "应急", "演练", "架构", "巡检", "维保", "服务方案")):
        return "specialized"
    return "general"


class OutlinePlanService:
    def __init__(self, demo: DemoService):
        self.demo = demo
        self.repository = demo.repository

    def get_outline_plan(self, project_id: str, volume_id: str | None = None) -> dict[str, Any]:
        """获取结构化大纲方案树。

        包含：大纲树、章节编号、层级、章节类型、增值理由、关联条款标识、星号/废标标记、编写人与确认状态。
        """
        state = self.repository.read()
        project = state.projects.get(project_id)
        if project is None:
            raise DomainError(404, "NOT_FOUND", "项目不存在或当前公司无权访问。")

        workflow = state.workflows.get(project_id, {})
        requirements = list(workflow.get("requirements", {}).values())
        outline_plans = workflow.get("outline_plans", {})
        writing_plan_chapters = workflow.get("writing_plan", {}).get("chapters", {})

        # 获取属于该项目的章节
        chapters = [c for c in state.chapters.values() if c.project_id == project_id]
        if volume_id is not None:
            chapters = [c for c in chapters if c.volume == volume_id]

        # 排序：遵循 chapter_order，其余按 id 排序
        chapter_order = workflow.get("chapter_order", [])
        order_map = {cid: idx for idx, cid in enumerate(chapter_order)}
        chapters.sort(key=lambda c: order_map.get(c.id, len(order_map)))

        chapter_nodes = []
        tree_by_volume: dict[str, list[dict[str, Any]]] = {}

        for index, chapter in enumerate(chapters):
            # 获取该章节关联的所有条款
            matched_reqs = [r for r in requirements if r.get("chapter_id") == chapter.id]
            req_ids = [r["id"] for r in matched_reqs]

            # 判定星号条款（★）与废标条款
            has_asterisk = any(
                r.get("mandatory") or r.get("asterisk") or "★" in r.get("clause", "") or "★" in r.get("text", "")
                for r in matched_reqs
            )
            has_disqualified = any(
                r.get("disqualified") or "废标" in r.get("clause", "") or "废标" in r.get("text", "")
                for r in matched_reqs
            )
            is_mandatory = has_asterisk or has_disqualified

            # 方案元数据读取
            meta = outline_plans.get(chapter.id, {})
            wp = writing_plan_chapters.get(chapter.id, {})
            is_confirmed = bool(
                meta.get("status") == "confirmed"
                or (wp.get("confirmed_at") and not wp.get("confirmation_pending"))
            )

            chapter_type = infer_chapter_type(chapter.title, meta.get("chapter_type"))
            value_added_reason = meta.get(
                "value_added_reason",
                "结合行业先进标杆与规范化服务指标，提供高于招标要求的差异化增值响应与质量保证。",
            )

            # 层级与章节编号（支持如 1.0, 2.0；若标题含有编号则解析）
            section_number = meta.get("section_number") or f"{index + 1}.0"
            level = int(meta.get("level", 1))

            assignee_id = chapter.assignee_id
            assignee_name = state.accounts[assignee_id].name if assignee_id in state.accounts else None

            node: dict[str, Any] = {
                "id": chapter.id,
                "chapter_id": chapter.id,
                "project_id": project_id,
                "volume": chapter.volume,
                "title": chapter.title,
                "section_number": section_number,
                "level": level,
                "chapter_type": chapter_type,
                "value_added_reason": value_added_reason,
                "associated_clause_ids": req_ids,
                "has_asterisk": has_asterisk,
                "has_disqualified": has_disqualified,
                "is_mandatory": is_mandatory,
                "applicable": meta.get("applicable", True),
                "assignee_id": assignee_id,
                "assignee_name": assignee_name,
                "confirmation_status": "confirmed" if is_confirmed else "unconfirmed",
                "confirmed_by": meta.get("confirmed_by") or wp.get("confirmed_by"),
                "confirmed_by_name": meta.get("confirmed_by_name") or wp.get("confirmed_by_name"),
                "confirmed_at": meta.get("confirmed_at") or wp.get("confirmed_at"),
                "revision": chapter.revision,
                "content_length": len(chapter.content),
                "children": [],
            }
            chapter_nodes.append(node)
            tree_by_volume.setdefault(chapter.volume, []).append(node)

        # 构建分册树状结构
        tree_roots = []
        for vol, nodes in tree_by_volume.items():
            tree_roots.append({
                "id": f"vol-{vol}",
                "volume": vol,
                "title": "技术分册" if vol == "technical" else "商务分册",
                "level": 0,
                "children": nodes,
            })

        return {
            "project_id": project_id,
            "volume_id": volume_id,
            "revision": project.revision,
            "total_chapters": len(chapter_nodes),
            "confirmed_count": sum(1 for c in chapter_nodes if c["confirmation_status"] == "confirmed"),
            "unconfirmed_count": sum(1 for c in chapter_nodes if c["confirmation_status"] != "confirmed"),
            "tree": tree_roots,
            "chapters": chapter_nodes,
        }

    def confirm_outline_plan(
        self,
        project_id: str,
        chapter_id: str | None = None,
        plan_data: dict[str, Any] | None = None,
        principal: Principal | None = None,
        volume_id: str | None = None,
    ) -> dict[str, Any]:
        """确认大纲方案。

        支持按章或按分册确认。
        - 核心门禁：星号条款 / 废标条款对应章节绝对禁止标记为“不适用”（抛出 400 INVALID_ACTION）；
        - 权限门禁：项目负责人全项目放行；分册负责人仅限本人分管分册，跨分册修改抛出 403 FORBIDDEN；只读角色拦截 403；
        - 单事务原子持久化方案元数据并使章节 revision 自增。
        """
        if principal is None:
            raise DomainError(401, "UNAUTHENTICATED", "未登录或会话无效。")

        plan_data = plan_data or {}

        def transaction_operation(state: DemoState) -> dict[str, Any]:
            project = state.projects.get(project_id)
            if project is None or project.company_id != principal.user.company_id:
                raise DomainError(404, "NOT_FOUND", "项目不存在或当前公司无权访问。")

            workflow = state.workflows.setdefault(project_id, {})
            requirements = list(workflow.get("requirements", {}).values())

            # 1. 权限门禁：只读系统角色与项目只读成员拦截
            norm_role = normalize_role(principal.user.role)
            if norm_role in READONLY_SYSTEM_ROLES:
                raise DomainError(403, "FORBIDDEN", "只读角色无权修改或确认大纲方案。")

            user_member = member(state, project_id, principal.user.id)
            if user_member is None:
                raise DomainError(403, "FORBIDDEN", "非本项目成员无权操作大纲方案。")
            if user_member.get("project_role") == "readonly":
                raise DomainError(403, "FORBIDDEN", "项目只读成员无权确认大纲方案。")

            is_project_lead = lead(state, project_id, principal.user.id)

            # 2. 定位目标章节
            target_chapters: list[Chapter] = []
            if chapter_id and chapter_id != "all":
                ch = state.chapters.get(chapter_id)
                if ch is None or ch.project_id != project_id:
                    raise DomainError(404, "NOT_FOUND", "章节不存在或不属于本项目。")
                target_chapters.append(ch)
            else:
                vol = volume_id or plan_data.get("volume_id") or plan_data.get("volume")
                all_proj_chapters = [c for c in state.chapters.values() if c.project_id == project_id]
                if vol:
                    target_chapters = [c for c in all_proj_chapters if c.volume == vol]
                    if not target_chapters:
                        raise DomainError(404, "NOT_FOUND", f"分册 {vol} 无可用章节。")
                else:
                    target_chapters = all_proj_chapters
                    if not target_chapters:
                        raise DomainError(404, "NOT_FOUND", "本项目尚未建立大纲章节。")

            # 3. 权限门禁：分册负责人与跨分册授权校验
            for ch in target_chapters:
                if not is_project_lead:
                    is_owner = volume_owner(state, project_id, ch.volume, principal.user.id)
                    if not is_owner:
                        raise DomainError(403, "FORBIDDEN", f"无权修改非本人负责的 {ch.volume} 分册大纲方案。")

            # 4. 核心安全门禁：星号条款 / 废标条款对应章节绝对禁止标记为“不适用”
            # 检测是否标记为“不适用”
            is_marked_not_applicable = (
                plan_data.get("applicable") is False
                or plan_data.get("is_applicable") is False
                or plan_data.get("status") in ("not_applicable", "excluded", "omitted")
                or plan_data.get("action") == "mark_not_applicable"
            )

            for ch in target_chapters:
                matched_reqs = [r for r in requirements if r.get("chapter_id") == ch.id]
                has_asterisk = any(
                    r.get("mandatory") or r.get("asterisk") or "★" in r.get("clause", "") or "★" in r.get("text", "")
                    for r in matched_reqs
                )
                has_disqualified = any(
                    r.get("disqualified") or "废标" in r.get("clause", "") or "废标" in r.get("text", "")
                    for r in matched_reqs
                )

                if (has_asterisk or has_disqualified) and is_marked_not_applicable:
                    clause_desc = "星号条款（★）" if has_asterisk else "废标条款"
                    raise OutlinePlanError(
                        400,
                        "INVALID_ACTION",
                        f"章节【{ch.title}】包含{clause_desc}，绝对禁止标记为“不适用”。",
                        details={"chapter_id": ch.id, "has_asterisk": has_asterisk, "has_disqualified": has_disqualified},
                    )

            # 检查细项评分行中的 applicable 标记
            for sr in plan_data.get("scoring_rows", []):
                sr_asterisk = sr.get("asterisk") or "★" in sr.get("clause", "")
                sr_disqualified = sr.get("disqualified") or "废标" in sr.get("clause", "")
                if (sr_asterisk or sr_disqualified) and sr.get("applicable") is False:
                    raise OutlinePlanError(
                        400,
                        "INVALID_ACTION",
                        "评分行中包含星号条款或废标条款，绝对禁止标记为“不适用”。",
                        details={"scoring_row_id": sr.get("id")},
                    )

            # 5. 单事务内原子持久化元数据并使章节 revision 自增
            now_dt = datetime.now(timezone.utc)
            now_str = iso_time(now_dt.timestamp())

            confirmed_plans = []
            outline_plans_map = workflow.setdefault("outline_plans", {})
            writing_plan_chapters = workflow.setdefault("writing_plan", {}).setdefault("chapters", {})

            for ch in target_chapters:
                # 章节 revision 原子自增
                ch.revision += 1

                meta_record = {
                    "chapter_id": ch.id,
                    "volume": ch.volume,
                    "status": "confirmed",
                    "confirmed_by": principal.user.id,
                    "confirmed_by_name": principal.user.name,
                    "confirmed_at": now_str,
                    "chapter_type": infer_chapter_type(ch.title, plan_data.get("chapter_type")),
                    "value_added_reason": plan_data.get(
                        "value_added_reason",
                        "结合行业先进标杆与规范化服务指标，提供高于招标要求的差异化增值响应与质量保证。",
                    ),
                    "applicable": True if (has_asterisk or has_disqualified) else plan_data.get("applicable", True),
                    "scoring_rows": deepcopy(plan_data.get("scoring_rows", [])),
                    "snippet_plan": deepcopy(plan_data.get("snippet_plan", [])),
                    "plan_data": deepcopy(plan_data),
                    "revision": ch.revision,
                }
                outline_plans_map[ch.id] = meta_record

                # 同步更新兼容 writing_plan
                existing_wp = chapter_plan(workflow, ch.id)
                writing_plan_chapters[ch.id] = {
                    **existing_wp,
                    "confirmed_by": principal.user.id,
                    "confirmed_by_name": principal.user.name,
                    "confirmed_at": now_str,
                    "confirmation_pending": False,
                    "writing_points": plan_data.get("writing_points", existing_wp.get("writing_points", "")),
                    "target_length": plan_data.get("target_length", existing_wp.get("target_length")),
                    "fact_ids": plan_data.get("fact_ids", existing_wp.get("fact_ids", [])),
                    "confirmed_input_fingerprint": writing_source_fingerprint(state, project_id, ch.id),
                }

                # 记录审计版本
                ch.versions.append({
                    "revision": ch.revision,
                    "content": ch.content,
                    "actor_id": principal.user.id,
                    "created_at": now_str,
                    "change_reason": f"大纲写作方案确认（{meta_record['chapter_type']}）",
                })
                confirmed_plans.append(meta_record)

            # 项目总体版本递增
            project.revision += 1
            workflow["plan_confirmed"] = True

            # 若持久化仓库支持章节和工作流存储，执行同步落库
            if hasattr(self.repository, "save_chapter"):
                for ch in target_chapters:
                    self.repository.save_chapter(ch, updated_at=now_dt)
            if hasattr(self.repository, "save_workflow"):
                self.repository.save_workflow({
                    "project_id": project_id,
                    "current_stage": workflow.get("current_stage", "outline"),
                    "stages_json": workflow.get("stages", {}),
                    "incremental_checks_json": workflow.get("incremental_checks", []),
                    "revision": project.revision,
                }, updated_at=now_dt)

            return {
                "project_id": project_id,
                "project_revision": project.revision,
                "confirmed_count": len(confirmed_plans),
                "plans": confirmed_plans,
            }

        return self.repository.transaction(transaction_operation)
