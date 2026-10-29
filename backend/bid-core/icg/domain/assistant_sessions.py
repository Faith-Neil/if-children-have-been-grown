# 为什么有这个文件：编辑台对话助手的会话留痕（PRD v1.8 §5.11.2 会话列表、§5.11.11 留痕与隔离；APP-M2-T176）。
# 它解决什么问题：
# 1. 每次选区提问（选区、修改方式、要求、知识库开关、检索结果、样例）和每次写入都追加到本人本章的会话里，只追加不改；
# 2. 同一会话里接着提要求时，把这段文字之前的要求与样例交给模型，用户可以说“再短一点”；
# 3. 会话只有本人、项目负责人和本公司公司管理员能看；继续提问只能本人。会话存在项目工作流里，随项目持久化。

from __future__ import annotations

from typing import Any

from .domain import DemoState, DomainError, Principal, new_id

MAX_SESSIONS = 200
MAX_MESSAGES = 200
HISTORY_TURNS = 2


def _sessions(workflow: dict) -> dict:
    return workflow.setdefault("assistant_sessions", {})


def can_read(state: DemoState, principal: Principal, project_id: str, session: dict) -> bool:
    from .project_access import lead, normalize_role
    if session["owner_id"] == principal.user.id or lead(state, project_id, principal.user.id):
        return True
    account = state.accounts.get(principal.user.id)
    project = state.projects.get(project_id)
    return bool(account and project and normalize_role(account.role) == "company_admin"
                and account.company_id == project.company_id)


def readable_session(state: DemoState, principal: Principal, project_id: str, session_id: str) -> dict:
    session = (state.workflows.get(project_id) or {}).get("assistant_sessions", {}).get(session_id)
    if session is None or not can_read(state, principal, project_id, session):
        raise DomainError(404, "NOT_FOUND", "未找到有权查看的会话。")
    return session


def history_lines(workflow: dict, session: dict, selection_hash: str) -> list[str]:
    """同一段文字在本会话里最近几轮的要求和样例（每轮取已采纳的样例，否则取第一条）。"""
    batches = workflow.get("assistant_suggestions", {})
    turns = []
    for message in session["messages"]:
        if message["kind"] != "samples":
            continue
        batch = batches.get(message.get("batch_id") or "")
        if not batch or batch.get("selection_hash") != selection_hash or not batch.get("samples"):
            continue
        chosen = next((s for s in batch["samples"] if s["status"] == "adopted"), batch["samples"][0])
        ask = batch["mode_label"] + (f"：{batch['instruction']}" if batch.get("instruction") else "")
        turns.append(f"- 要求：{ask} → 样例（{chosen['style_label']}）：{chosen['text'][:200]}")
    return turns[-HISTORY_TURNS:]


def record_request(workflow: dict, principal: Principal, chapter: Any, batch: dict, session_id: str | None, now: str) -> str:
    sessions = _sessions(workflow)
    session = sessions.get(session_id) if session_id else None
    if session is None:
        session = {"id": new_id("session"), "project_id": chapter.project_id, "chapter_id": chapter.id,
                   "chapter_title": chapter.title, "owner_id": principal.user.id, "owner_name": principal.user.name,
                   "title": batch["selected_text"][:24], "created_at": now, "updated_at": now, "messages": []}
        sessions[session["id"]] = session
        for old in sorted(sessions.values(), key=lambda item: item["updated_at"])[:-MAX_SESSIONS]:
            sessions.pop(old["id"], None)
    messages = session["messages"]
    messages.append({"id": new_id("msg"), "role": "user", "kind": "selection_request", "created_at": now,
                     "selected_text": batch["selected_text"], "start": batch["start"], "end": batch["end"],
                     "base_revision": batch["base_revision"], "mode": batch["mode"], "mode_label": batch["mode_label"],
                     "instruction": batch["instruction"], "knowledge_base_enabled": batch["knowledge_base_enabled"]})
    messages.append({"id": new_id("msg"), "role": "assistant", "kind": "samples", "created_at": now,
                     "batch_id": batch["id"], "status": batch["status"], "sample_count": len(batch["samples"]),
                     "dropped_count": len(batch["dropped"]), "retrieval": batch.get("retrieval"),
                     "model": batch.get("model") or batch.get("provider"),
                     "library_query_skipped": not batch["knowledge_base_enabled"]})
    del messages[:-MAX_MESSAGES]
    session["updated_at"] = now
    return session["id"]


def record_apply(workflow: dict, session_id: str, operation: dict) -> None:
    session = _sessions(workflow).get(session_id)
    if session is None:
        return
    session["messages"].append({"id": new_id("msg"), "role": "user", "kind": "applied", "created_at": operation["created_at"],
                                "batch_id": operation["batch_id"], "sample_id": operation["sample_id"],
                                "operation_id": operation["id"], "edit_mode_label": operation["edit_mode_label"],
                                "result_revision": operation["result_revision"]})
    del session["messages"][:-MAX_MESSAGES]
    session["updated_at"] = operation["created_at"]


def summary(session: dict) -> dict:
    return {key: session[key] for key in ("id", "chapter_id", "chapter_title", "owner_id", "owner_name", "title",
                                          "created_at", "updated_at")} | {"message_count": len(session["messages"])}


def list_sessions(demo: Any, principal: Principal, project_id: str, chapter_id: str | None) -> dict:
    state = demo.repository.read()
    if not _company_admin(state, principal, project_id):
        demo._project(state, principal, project_id)  # 其他人须是项目成员
    sessions = (state.workflows.get(project_id) or {}).get("assistant_sessions", {}).values()
    visible = [summary(s) for s in sessions if (chapter_id is None or s["chapter_id"] == chapter_id)
               and can_read(state, principal, project_id, s)]
    return {"sessions": sorted(visible, key=lambda item: item["updated_at"], reverse=True)}


def session_detail(demo: Any, principal: Principal, project_id: str, session_id: str) -> dict:
    state = demo.repository.read()
    if not _company_admin(state, principal, project_id):
        demo._project(state, principal, project_id)
    session = readable_session(state, principal, project_id, session_id)
    batches = (state.workflows.get(project_id) or {}).get("assistant_suggestions", {})
    from .selection_rewrite import public_batch
    messages = []
    for message in session["messages"]:
        item = dict(message)
        if message["kind"] == "samples" and message.get("batch_id") in batches:
            item["batch"] = public_batch(batches[message["batch_id"]])
        messages.append(item)
    return {**summary(session), "messages": messages, "read_only": session["owner_id"] != principal.user.id}


def _company_admin(state: DemoState, principal: Principal, project_id: str) -> bool:
    from .project_access import normalize_role
    account = state.accounts.get(principal.user.id)
    project = state.projects.get(project_id)
    return bool(account and project and not project.is_deleted and normalize_role(account.role) == "company_admin"
                and account.company_id == project.company_id and state.sessions.get(principal.session_token) == account.id)
