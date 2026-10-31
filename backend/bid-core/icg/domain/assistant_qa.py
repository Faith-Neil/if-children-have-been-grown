# 为什么有这个文件：编辑台对话助手的自由提问（PRD v1.8 §5.11.3“未选中正文 → 自由提问：只回答，不提供写入按钮；
# 知识库打开时回答附引用”；§5.11.11 会话留痕；§6.4/6.5 降级与敏感项目只用本地模型；APP-M2-T179、T177）。
# 它解决什么问题：
# 1. 先按词表判断是否直查本项目或本公司数据：命中且查到时直接返回答案卡，不调用模型；
# 2. 否则调用模型逐字流式回答；知识库打开时只能引用本次检索到的资料（[片:…] 标记），引用了检索结果以外的标记一律去掉并提示；
#    知识库打开但没检索到时不调用模型，提示去补资料或关闭知识库；
# 3. 回答只供参考和复制，不提供写入正文；上游错误、思考过程、空回答不当作回答；
# 4. 主模型健康类失败改用备用模型并标明；敏感项目只用本地模型；
# 5. 提问和回答追加到本人本章会话，会话记录与选区改写共用。

from __future__ import annotations

import re
import threading
from typing import Any

from .domain import DemoState, DomainError, Principal, iso_time, new_id

MAX_QUESTION = 1000
MAX_ANSWER = 3000
CITE = re.compile(r"\[片:[^\]]+\]")


def _system_prompt(knowledge_base: bool) -> str:
    lines = [
        "你是投标文件编写助手，回答编写人关于本章写作的问题。",
        "必须遵守：",
        "1. 只依据【本章回应的招标要求】【已确认的项目事实】" + ("和【可引用的资料】" if knowledge_base else "") + "回答，不编造本公司资质、业绩、人员、数值和承诺；资料里没有的就说明需要补充资料；",
        "2. 不写“以下是”“希望对你有帮助”等对话套话，不展示思考过程；",
        "3. 回答简明，不超过 600 字。",
    ]
    if knowledge_base:
        lines.append("4. 用到【可引用的资料】时，在句末原样写上它的标记（如 [片:lib-1]），只能用列出的标记。")
    return "\n".join(lines)


def _user_content(title: str, requirements: list[str], facts: list[dict], hits: list[dict], history: list[str], question: str) -> str:
    lines = [f"【章节】{title}"]
    if requirements:
        lines += ["【本章回应的招标要求】", *[f"- {text[:200]}" for text in requirements[:6]]]
    if facts:
        lines += ["【已确认的项目事实】", *[f"- {f['key']}：{f['value']}{f.get('unit') or ''}" for f in facts[:12]]]
    if hits:
        lines += ["【可引用的资料】", *[f"- {h['cite_tag']} {h['name']}（v{h['revision']}）：{h['content'][:300]}" for h in hits]]
    if history:
        lines += ["【本会话之前的问答】", *history]
    lines.append(f"【问题】{question}")
    return "\n".join(lines)


def clean_answer(text: str, allowed: set[str]) -> tuple[str | None, list[str], str]:
    """返回（回答或 None，提示，不能展示的原因）。"""
    from .selection_rewrite import THINKING, UPSTREAM_ERROR, _clean
    if UPSTREAM_ERROR.search((text or "")[:300]):
        return None, [], "模型服务返回了错误信息（如额度或频率限制）"
    if THINKING.search(text or ""):
        return None, [], "模型输出了思考过程而不是回答，请换用不带思考过程的模型"
    answer = _clean(text)
    if not answer:
        return None, [], "模型没有返回内容"
    notes = []
    foreign = [tag for tag in CITE.findall(answer) if tag not in allowed]
    if foreign:
        answer = CITE.sub(lambda m: m.group(0) if m.group(0) in allowed else "", answer)
        notes.append(f"去掉了 {len(foreign)} 个不在本次检索结果里的引用标记")
    if len(answer) > MAX_ANSWER:
        answer = answer[:MAX_ANSWER] + "…"
        notes.append("回答过长，已截断")
    return answer, notes, ""


class AssistantQAService:
    def __init__(self, demo: Any, rewrite: Any) -> None:
        self.demo = demo
        self.rewrite = rewrite  # SelectionRewriteService：共用章节核对、公司策略、检索与资料来源

    def prepare(self, principal: Principal, project_id: str, chapter_id: str, payload: dict) -> dict:
        from .answer_card import resolve_assistant_query_route
        from .project_access import normalize_role, READONLY_SYSTEM_ROLES
        if normalize_role(principal.user.role) in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不能使用对话助手提问。")
        question = (payload.get("question") or "").strip()
        if not question:
            raise DomainError(422, "VALIDATION_ERROR", "请输入问题。")
        state = self.demo.repository.read()
        chapter = self.demo._chapter(state, principal, chapter_id)
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
        project = self.demo._project(state, principal, project_id)
        team = (state.project_teams.get(project_id) or {}).get("members", {})
        if (team.get(principal.user.id) or {}).get("project_role") in ("viewer", "readonly"):
            raise DomainError(403, "FORBIDDEN", "项目只读成员不能使用对话助手提问。")
        policy = self.rewrite._policy(state, project.company_id)
        if not policy["enabled"]:
            raise DomainError(403, "FORBIDDEN", "本公司已关闭对话助手。")
        kb_on = payload.get("knowledge_base_enabled")
        kb_on = policy["kb_default"] if kb_on is None else bool(kb_on)
        if not kb_on and not policy["allow_kb_off"]:
            raise DomainError(422, "VALIDATION_ERROR", "本公司要求对话助手使用知识库，不能关闭。")
        workflow = state.workflows.get(project_id) or {}
        session_id = payload.get("session_id")
        history: list[str] = []
        if session_id:
            from .assistant_sessions import readable_session
            session = readable_session(state, principal, project_id, session_id)
            if session["owner_id"] != principal.user.id or session["chapter_id"] != chapter_id:
                raise DomainError(403, "FORBIDDEN", "只能在本人本章的会话中继续提问。")
            history = [f"- 问：{m['question'][:200]} → 答：{(m.get('answer') or '')[:300]}"
                       for m in session["messages"] if m["kind"] == "answer"][-2:]
        base = {"principal": principal, "project_id": project_id, "chapter_id": chapter_id, "chapter_title": chapter.title,
                "question": question, "kb_on": kb_on, "session_id": session_id, "sensitive": bool(project.sensitive)}
        route = resolve_assistant_query_route(question, kb_on)
        if route.query_route == "direct_query":
            from .answer_card import AnswerCardService
            card = AnswerCardService(self.demo).assemble_answer_card(principal, project_id, question, route)
            if card and card.records:
                return {**base, "card": card.to_dict()}
        self.demo.require_allowed_model(project, state=state)
        provider = self.demo.resolve_model_provider(state, project_id, "assistant_qa")
        if not getattr(provider, "is_real_model", False):
            raise DomainError(502, "MODEL_UNAVAILABLE", "尚未接入真实大模型：对话助手不提供模拟回答。请公司管理员在“模型配置”中接入模型后再试。")
        facts, requirements = self.rewrite._sources(state, project_id, chapter_id, workflow)
        hits, retrieval = [], {"status": "off", "message": "知识库已关闭，未查询本公司资料库。"}
        if kb_on:
            hits, retrieval = self.rewrite._retrieve(principal, project.company_id, chapter.title, question, "")
        return {**base, "card": None, "provider": provider, "hits": hits, "retrieval": retrieval,
                "system": _system_prompt(kb_on), "user_content": _user_content(chapter.title, requirements, facts, hits, history, question)}

    def stream(self, prepared: dict, cancel: Any = None):
        """事件：started →（card）或 delta / fallback / queued → answer → done；知识库无结果时不调用模型。"""
        import queue
        from icg.infra.model_fallback import call_model, degradable, failure_text, model_name
        from icg.infra.openai_model import ModelCancelled
        from .selection_rewrite import LOCAL_QUEUE_SECONDS, LOCAL_QUEUE_STEPS
        cancel = cancel if cancel is not None else threading.Event()
        if prepared.get("card"):
            yield {"event": "started", "route": "direct_query", "knowledge_base_enabled": prepared["kb_on"]}
            yield from self._finish(prepared, {"route": "direct_query", "answer_card": prepared["card"], "answer": None})
            return
        provider = prepared["provider"]
        backup = getattr(provider, "fallback", None)
        yield {"event": "started", "route": "model", "retrieval": prepared["retrieval"], "knowledge_base_enabled": prepared["kb_on"],
               "model": model_name(provider), "fallback_model": model_name(backup) if backup is not None else None}
        if prepared["kb_on"] and not prepared["hits"]:
            yield from self._finish(prepared, {"route": "no_results", "answer": None, "message": prepared["retrieval"]["message"]})
            return
        inbox: queue.Queue = queue.Queue()

        def work():
            waited, attempt = 0.0, 0
            while True:
                try:
                    inbox.put(("result", call_model(provider, prepared["system"], prepared["user_content"],
                                                    on_delta=lambda text: inbox.put(("delta", text)),
                                                    on_reset=lambda name, why: inbox.put(("fallback", (name, why))), cancel=cancel)))
                    return
                except ModelCancelled:
                    inbox.put(("cancelled", None))
                    return
                except Exception as error:
                    if prepared["sensitive"] and degradable(error) and waited < LOCAL_QUEUE_SECONDS and not cancel.is_set():
                        attempt += 1
                        pause = min(LOCAL_QUEUE_STEPS[min(attempt - 1, len(LOCAL_QUEUE_STEPS) - 1)], LOCAL_QUEUE_SECONDS - waited)
                        inbox.put(("queued", {"attempt": attempt, "wait_seconds": pause, "reason": failure_text(error)}))
                        if cancel.wait(pause):
                            inbox.put(("cancelled", None))
                            return
                        waited += pause
                        continue
                    inbox.put(("failed", failure_text(error)))
                    return

        threading.Thread(target=work, daemon=True).start()
        try:
            while not cancel.is_set():
                try:
                    kind, value = inbox.get(timeout=0.5)
                except queue.Empty:
                    continue
                if kind == "delta":
                    yield {"event": "delta", "text": value}
                elif kind == "fallback":
                    yield {"event": "fallback", "model": value[0], "reason": value[1]}
                elif kind == "queued":
                    if value["attempt"] == 1:
                        self.rewrite._notify_queue(prepared, value["reason"])
                    yield {"event": "queued", **value,
                           "message": f"本地模型暂时不可用（{value['reason']}），敏感项目不改走云端，{int(value['wait_seconds'])} 秒后重试"}
                elif kind == "cancelled":
                    break
                elif kind == "failed":
                    yield {"event": "error", "status": 502, "code": "MODEL_UNAVAILABLE", "message": f"对话助手暂时不可用：{value}，请稍后重试。"}
                    return
                else:
                    allowed = {h["cite_tag"] for h in prepared["hits"]}
                    answer, notes, reason = clean_answer(value.text, allowed)
                    if answer is None:
                        yield {"event": "error", "status": 502, "code": "MODEL_OUTPUT_INVALID", "message": f"回答没有通过预检：{reason}。"}
                        return
                    sources = [dict(h, content=h["content"][:200]) for h in prepared["hits"] if h["cite_tag"] in answer]
                    yield from self._finish(prepared, {"route": "model", "answer": answer, "warnings": notes, "sources": sources,
                                                       "model": value.model, "is_fallback": value.is_fallback,
                                                       "fallback_reason": value.fallback_reason, "is_local_model": value.is_local})
                    return
            yield {"event": "cancelled", "message": "已停止，本次回答不保存。"}
        finally:
            cancel.set()

    def _finish(self, prepared: dict, result: dict):
        principal = prepared["principal"]
        now = iso_time(self.demo._now())
        record = {"id": new_id("answer"), "question": prepared["question"], "knowledge_base_enabled": prepared["kb_on"],
                  "retrieval": prepared.get("retrieval"), "can_insert": False, "action": "copy_only", "created_at": now, **result}

        def operation(state: DemoState):
            from .assistant_sessions import record_question
            chapter = self.demo._chapter(state, principal, prepared["chapter_id"])
            flow = state.workflows.setdefault(prepared["project_id"], {})
            record["session_id"] = record_question(flow, principal, chapter, record, prepared["session_id"], now)
            self.demo._audit(state, principal, chapter, "assistant.question",
                             {"answer_id": record["id"], "route": record["route"], "knowledge_base_enabled": prepared["kb_on"],
                              "model": record.get("model"), "is_fallback": record.get("is_fallback", False)})
            return record

        try:
            yield {"event": "done", "answer": self.demo.repository.transaction(operation)}
        except DomainError as error:
            yield {"event": "error", "status": error.status, "code": error.code, "message": error.message}
