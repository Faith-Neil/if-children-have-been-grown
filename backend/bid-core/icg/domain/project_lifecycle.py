# 为什么有这个文件：项目状态流转、取消后只读、拟派人员占用冲突提示（PRD v1.8 §4.3、§5.1.1、§5.1.3、§5.1.4 第 4 项；
# APP-M2-T097、T099）。
# 它解决什么问题：
# 1. Project 数据类没有状态列，登记类状态（已递交 → 已开标 → 已结束 / 已取消）存在项目工作流里，随同一事务、版本、幂等与审计保存；
#    编制过程中的状态（草稿 … 已导出）由工作台阶段推出，不重复存一份；
# 2. 项目已取消后一切经 _write 的写入都被拒绝（PRD 5.1.3“项目取消后只读”），取消不可撤销；
# 3. 拟派人员占用冲突：同公司其他在投项目已拟派同一人时给出提示，只提示不锁定（PRD 5.1.4 第 4 项）。
# 限制：不经 _write 的写入（例如编辑台正文自动保存）不在这里拦截，见任务卡交付说明。

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .domain import DomainError, Principal, iso_time

SHANGHAI = timezone(timedelta(hours=8))
STATUS_LABEL = {"draft": "草稿", "pending_confirm": "待确认", "compiling": "编制中", "exported": "已导出",
                "submitted": "已递交", "opened": "已开标", "ended": "已结束", "cancelled": "已取消"}
STAGE_STATUS = {"upload": "draft", "review": "pending_confirm", "matrix": "compiling", "writing": "compiling", "exported": "exported"}
RESULTS = {"won": "中标", "lost": "未中标", "void": "废标", "failed_tender": "流标"}
CLOSED = ("opened", "ended", "cancelled")  # 在投占用已释放
ACTION_TARGET = {"submit": "submitted", "open": "opened", "result": "ended", "cancel": "cancelled"}
ACTION_FROM = {"submit": ("exported",), "open": ("submitted",), "result": ("opened",),
               "cancel": ("draft", "pending_confirm", "compiling")}


def parse_time(value: str | None) -> datetime | None:
    try:
        moment = datetime.fromisoformat(str(value or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.replace(tzinfo=SHANGHAI) if moment.tzinfo is None else moment


def registered_status(workflow: dict) -> str | None:
    return (workflow.get("project_status") or {}).get("status")


def current_status(workflow: dict, stage: str) -> dict:
    """页面展示用状态：已登记的优先，否则由工作台阶段推出。"""
    saved = workflow.get("project_status") or {}
    code = saved.get("status") or STAGE_STATUS.get(stage, "draft")
    return {"status": code, "label": STATUS_LABEL[code], "read_only": code == "cancelled",
            "registered": bool(saved.get("status")), "result": saved.get("result"),
            "result_label": RESULTS.get(saved.get("result") or ""), "history": list(saved.get("history") or [])}


def ensure_not_cancelled(state: Any, project_id: str) -> None:
    if registered_status(state.workflows.get(project_id) or {}) == "cancelled":
        raise DomainError(409, "PROJECT_CANCELLED", "项目已取消，只能查看，不能再修改。")


def occupancy_conflicts(state: Any, project: Any, workflow: dict) -> list[dict]:
    """同公司其他在投项目已拟派同一人：只提示，不锁定。已开标、已结束、已取消的项目不再占用。"""
    mine = {e["person_id"]: e for e in workflow.get("proposed_staff") or []}
    found = []
    for other_id, other in state.projects.items():
        flow = state.workflows.get(other_id) or {}
        if other_id == project.id or other.company_id != project.company_id or other.is_deleted:
            continue
        if registered_status(flow) in CLOSED:
            continue
        for entry in flow.get("proposed_staff") or []:
            if entry["person_id"] in mine:
                person = state.library.get(entry["person_id"]) or {}
                found.append({"person_id": entry["person_id"], "person_name": person.get("name", "资料已删除"),
                              "role": mine[entry["person_id"]]["role"], "other_project_id": other_id,
                              "other_project_name": other.name, "other_role": entry["role"],
                              "other_deadline": other.deadline or None})
    return found


class ProjectLifecycleMixin:
    """挂在 WorkflowService 上：项目状态流转（动作名 project.update:status，仅项目负责人）。"""

    def transition_project(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        action = payload["action"]
        reason = (payload.get("reason") or "").strip()
        result = payload.get("result")
        if action == "cancel" and len(reason) < 2:
            raise DomainError(422, "VALIDATION_ERROR", "取消项目须填写原因。")
        if action == "result" and result not in RESULTS:
            raise DomainError(422, "VALIDATION_ERROR", "登记结果须选择中标、未中标、废标或流标。")
        if action != "result" and result is not None:
            raise DomainError(422, "VALIDATION_ERROR", "只有登记结果时才填写结果类型。")

        def operation(state, project, workflow):
            stage = self.workspace_stage(state, project.id, workflow)
            now = current_status(workflow, stage)["status"]
            if now not in ACTION_FROM[action]:
                raise DomainError(409, "INVALID_STATUS_TRANSITION",
                                  f"项目当前为“{STATUS_LABEL[now]}”，不能办理此状态变更。", {"status": now})
            if action == "submit" and not any(e.get("kind") == "submission" and e.get("export_status") != "failed"
                                              for e in workflow.get("exports", {}).values()):
                raise DomainError(409, "INVALID_STATUS_TRANSITION", "还没有成功导出的递交版，不能登记递交。", {"status": now})
            saved = workflow.setdefault("project_status", {"history": []})
            saved["history"].append({"from": now, "to": ACTION_TARGET[action], "reason": reason, "result": result,
                                     "by": principal.user.id, "at": iso_time(self.demo._now())})
            saved["status"] = ACTION_TARGET[action]
            if result:
                saved["result"] = result
            return {"status": current_status(workflow, stage)}

        return self._write(principal, project_id, "project.update:status", payload, expected, key, operation,
                           {"action": action, "result": result})

    def workspace_stage(self, state, project_id: str, workflow: dict) -> str:
        from .generation_context import plan_is_current
        exported = any(e.get("fingerprint") == self._fingerprint(state, project_id) for e in workflow["exports"].values())
        return ("exported" if exported else "writing" if plan_is_current(state, project_id) else
                "matrix" if workflow["parse_confirmed"] else "review" if workflow["requirements"] else "upload")
