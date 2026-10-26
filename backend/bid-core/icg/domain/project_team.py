# 为什么有这个文件：在一次事务里保存项目成员、两册负责人、章节分工及交接说明。
# 它解决什么问题：交接不会丢正文和个人草稿，失去权限的人也不能拿旧编辑权继续提交。

from copy import deepcopy

from .domain import DomainError, iso_time, new_id
from .project_access import (
    LEAD_COMPANY_ROLES,
    READONLY_SYSTEM_ROLES,
    VOLUMES,
    chapter_edit,
    normalize_role,
    public_team,
    writable,
)


class ProjectTeamService:
    def __init__(self, workflow):
        self.workflow, self.demo, self.repository = workflow, workflow.demo, workflow.repository

    def get(self, principal, project_id):
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        return {"revision": project.revision, **public_team(state, project_id, principal.user.id)}

    @staticmethod
    def eligible(state, project_id, user_id, volume=None):
        if user_id is None:
            return
        membership = state.project_teams[project_id]["members"].get(user_id)
        if not writable(state, project_id, user_id) or (volume and volume not in membership["volumes"]):
            raise DomainError(422, "ASSIGNEE_NOT_WRITABLE", "负责人和编写人必须是本公司已加入项目的可写成员，并参与所分配的分册。")

    def handoff(self, state, principal, project_id, chapters, reason, previous_user_ids):
        if not chapters:
            return
        active_count = sum(bool(c.lock and c.lock.expires_at > self.demo._now()) for c in chapters)
        draft_count = sum(len(c.drafts) for c in chapters)
        if (active_count or draft_count) and not reason.strip():
            raise DomainError(409, "HANDOFF_REASON_REQUIRED", "交接涉及已保存草稿或正在编辑的章节，请写明交接理由；正文、历史和各人草稿会保留。")
        for chapter in chapters:
            chapter.lock = None
        record = {"id": new_id("handoff"), "actor_id": principal.user.id,
                  "at": iso_time(self.demo._now()), "reason": reason.strip(),
                  "chapter_ids": [c.id for c in chapters], "previous_user_ids": sorted(set(previous_user_ids) - {None}),
                  "preserved_draft_count": draft_count, "revoked_lock_count": active_count}
        state.project_teams[project_id].setdefault("handoffs", []).append(record)
        self.workflow._audit(state, principal, project_id, "team.handoff", record)

    def update(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            old_state = deepcopy(state)
            old = state.project_teams[project_id]
            members = {}
            for item in payload["members"]:
                account = state.accounts.get(item["user_id"])
                if account is None or account.company_id != project.company_id:
                    raise DomainError(404, "NOT_FOUND", "成员账号不存在或不属于本公司。")
                if item["user_id"] in members:
                    raise DomainError(422, "DUPLICATE_MEMBER", "同一个账号不能重复加入项目。")
                volumes = item["volumes"]
                if len(volumes) != len(set(volumes)):
                    raise DomainError(422, "DUPLICATE_VOLUME", "参与分册不能重复。")
                norm = normalize_role(account.role)
                if item["project_role"] in ("lead", "writer") and norm in READONLY_SYSTEM_ROLES:
                    raise DomainError(422, "MEMBER_ROLE_NOT_WRITABLE", "公司只读账号不能在项目中提升为负责人或编写人。")
                if item["project_role"] == "lead" and norm not in LEAD_COMPANY_ROLES:
                    raise DomainError(422, "PROJECT_LEAD_COMPANY_ROLE_REQUIRED", "项目负责人必须具有公司的项目经理操作角色，普通编写人可担任分册负责人或本节编写人。")
                if item["project_role"] == "lead" and set(volumes) != set(VOLUMES):
                    raise DomainError(422, "LEAD_ALL_VOLUMES_REQUIRED", "项目负责人负责全部两册，须参与技术和商务。")
                members[item["user_id"]] = deepcopy(item)
            if not any(m["project_role"] == "lead" for m in members.values()):
                raise DomainError(409, "LAST_PROJECT_LEAD_REQUIRED", "项目必须保留至少一位有效负责人。")
            owners = {item["volume"]: item["owner_id"] for item in payload["volumes"]}
            if len(payload["volumes"]) != 2 or set(owners) != set(VOLUMES):
                raise DomainError(422, "TWO_VOLUMES_REQUIRED", "请完整设置技术和商务两册的负责人，可明确留空。")
            new = {"members": members, "owners": owners, "assembly_owner_id": payload["assembly_owner_id"],
                   "handoffs": deepcopy(old.get("handoffs", []))}
            state.project_teams[project_id] = new
            for volume, identity in owners.items():
                self.eligible(state, project_id, identity, volume)
            self.eligible(state, project_id, payload["assembly_owner_id"])
            impacted, previous = [], []
            for chapter in state.chapters.values():
                if chapter.project_id != project_id:
                    continue
                old_chapter = old_state.chapters[chapter.id]
                old_editors = [user_id for user_id in old["members"] if chapter_edit(old_state, old_chapter, user_id)]
                assignment_lost = chapter.assignee_id is not None and (
                    not writable(state, project_id, chapter.assignee_id)
                    or chapter.volume not in members[chapter.assignee_id]["volumes"])
                owner_changed = old["owners"].get(chapter.volume) != owners.get(chapter.volume)
                lost_editors = [identity for identity in old_editors if not chapter_edit(state, chapter, identity)]
                if assignment_lost:
                    previous.append(chapter.assignee_id)
                    chapter.assignee_id = None
                if assignment_lost or owner_changed or lost_editors:
                    impacted.append(chapter)
                    previous += lost_editors + [old["owners"].get(chapter.volume)]
            self.handoff(state, principal, project_id, impacted, payload.get("reason", ""), previous)
            return {"team": public_team(state, project_id, principal.user.id),
                    "chapters": [self.workflow._chapter_summary(state, workflow, c, principal.user.id)
                                 for c in state.chapters.values() if c.project_id == project_id]}
        return self.workflow._write(principal, project_id, "team.update", payload, expected, key, operation)

    def assignment(self, principal, project_id, chapter_id, payload, expected, key):
        def operation(state, project, workflow):
            chapter = self.demo._chapter(state, principal, chapter_id)
            self.eligible(state, project_id, payload["assignee_id"], chapter.volume)
            if chapter.assignee_id != payload["assignee_id"]:
                previous = chapter.assignee_id
                self.handoff(state, principal, project_id, [chapter], payload.get("reason", ""), [previous])
                chapter.assignee_id = payload["assignee_id"]
            return {"chapter": self.workflow._chapter_summary(state, workflow, chapter, principal.user.id)}
        return self.workflow._write(principal, project_id, "chapter.assignment:" + chapter_id, payload, expected, key, operation)
