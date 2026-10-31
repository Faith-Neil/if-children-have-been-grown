# 为什么有这个文件：编辑台“选中一段文字，请对话助手给出几种写法，再替换或插入”（PRD v1.8 §5.11.1 第 4 点、§5.11.4～5.11.8；
# APP-M2-T178、T180、T185、T187）。
# 它解决什么问题：原先的助手只能整章重写，选区只是被拼进一句指令；写入时整章被替换。这里：
# 1. 只把选中文字连同前后段落、本章已确认条款和项目事实交给模型，按 3～5 种写法各生成一条样例（默认 3 条）；
# 2. 每条样例先预检：变量和证据标记必须原样保留，含身份证/手机号/银行账号的样例不展示，
#    数字对不上选区、项目事实和本章条款的换成【待补：数值来源】，对话残留和 Markdown 符号去掉，相近样例合并；
# 3. 样例存入项目工作流；写入时只取服务端保存的样例文字（客户端不能夹带别的内容），核对编辑锁和选区；
#    选区被改动但能在本章唯一找到时先返回新位置请用户再确认，找不到或多处时拒绝并把样例标“已失效”；
# 4. 每次写入生成新章节版本，记录编辑操作（修改方式、基础与结果版本、改动区间、所用样例、知识库开关、操作人），
#    并立即对改动段落做文字规则复查（对话残留、占位符、负偏离、新增数值），不重跑整章闭环。
# 5. 知识库开关（公司设置 assistant_kb_default / assistant_allow_kb_off）：打开时只检索本公司知识库，每条样例至少引用 1 条
#    本次检索结果（标记 [片:来源编号]，编号须在本次结果内），检索无结果时不调用模型；关闭时样例标“无知识库来源”；
# 6. 每次提问与写入记入本人的会话（只追加，见 assistant_sessions.py），同一会话可接着上一轮的样例继续提要求；
# 7. 流式：模型逐字输出时边收边推给页面（delta），每种写法预检通过即推送样例；用户停止或断开连接时全部写法停下、不保存；
#    主模型超时、连接失败、5xx 或限流时该写法改用备用模型，页面显示“已使用备用模型 X”，样例记录实际模型（APP-M2-T177）。
# 没有接入真实模型时直接说明，不返回模拟样例。

from __future__ import annotations

import difflib
import hashlib
import re
from typing import Any

from .domain import DemoState, DomainError, Principal, iso_time, new_id

MODES = {
    "rewrite": ("改写", "在不改变意思的前提下重写这段文字"),
    "expand": ("扩写", "在不新增事实的前提下把这段文字写得更充分、更有条理"),
    "shorten": ("缩写", "压缩篇幅，保留全部要点、事实和变量"),
    "instruction": ("按指令修改", "按用户的修改要求修改这段文字"),
    "rephrase": ("换一种说法", "换一种表达方式，意思和事实保持不变"),
}
STYLES = [
    ("formal", "严谨规范", "用正式、规范的投标文件书面语"),
    ("concise", "简洁精炼", "删去冗余和套话，句子短而完整"),
    ("responsive", "突出响应", "点明对招标要求的实质性响应，但不新增未经核实的承诺"),
    ("structured", "条理分明", "按逻辑层次分句或分点组织"),
    ("plain", "平实易读", "用评委一读就懂的平实表述"),
]
DEFAULT_COUNT, MIN_COUNT, MAX_COUNT = 3, 3, 5
MAX_SELECTION = 2000
KEEP_BATCHES = 50

TOKEN = re.compile(r"\{\{(?:fact|sla):[^}]+\}\}|\[(?:证|片|cite):[^\]]+\]")
NUMBER = re.compile(r"(?<![A-Za-z0-9.{])\d+(?:\.\d+)?(?:\s*(?:%|％|个|名|人|小时|分钟|天|日|月|年|次|项|套|台|万元|元|万|kg|KG|GB|TB|MB))?")
LIST_MARKER = re.compile(r"^\s*\d+(?:\.\d+)*[.、)）]\s*")
SENSITIVE = [
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),        # 身份证号
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),          # 手机号
    re.compile(r"(?<!\d)\d{16,19}(?!\d)"),            # 银行账号
    re.compile(r"(?:密码|口令)[:：]\s*\S+"),
]
LEADING_CHATTER = re.compile(r"^(?:以下是[^\n：:]*[：:]|好的[，,。]?|改写(?:后|如下)?[：:]|修改(?:后|如下)?[：:]|样例[一二三四五\d]*[：:])\s*")
AMOUNT = re.compile(r"\d+(?:\.\d+)?\s*(?:万元|元|亿元)")
# 上游模型出错时，有的网关（如 RAGFlow 的 OpenAI 兼容接口）以 200 返回错误文字，不能当成样例
UPSTREAM_ERROR = re.compile(r"^\s*(?:\*\*)?ERROR(?:\*\*)?\s*[:：]|exceeded your current quota|rate.?limit|Error \d{3}, Message", re.I)
# 模型把思考过程当正文输出（编号加粗的“分析/理解/解构/确定策略/起草”小标题、“起草 - 迭代”、<think>）
THINKING = re.compile(r"^\s*(?:\d+[.、]\s*)?\*\*\s*(?:分析|理解|解构|确定(?:策略|语境)|起草)[^*\n]{0,12}\*\*|起草\s*-\s*迭代|<think>")
PREAMBLE = re.compile(r"^[^\n]{0,80}(?:如下|以下)[：:]\s*$")
REPEAT = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9，、]{4,}?)\1+")
LENGTH_LIMIT = {"expand": (2.5, 200), "shorten": (1.0, 0)}
PENDING_NUMBER = "【待补：数值来源】"
LOCAL_QUEUE_SECONDS = 120.0           # 敏感项目本地模型不可用时最多排队等待的秒数
LOCAL_QUEUE_STEPS = (5, 10, 20, 30)   # 每次重试前的等待（秒），之后按 30 秒


def selection_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _paragraph_bounds(content: str, start: int, end: int) -> tuple[int, int]:
    """选区所在段落（按换行分段）的起止位置。"""
    begin = content.rfind("\n", 0, start) + 1
    stop = content.find("\n", end)
    return begin, len(content) if stop < 0 else stop


def _neighbours(content: str, start: int, end: int) -> tuple[str, str, str]:
    begin, stop = _paragraph_bounds(content, start, end)
    before = content[:begin].rstrip("\n").split("\n")[-1] if begin > 0 else ""
    after = content[stop:].lstrip("\n").split("\n")[0] if stop < len(content) else ""
    return before.strip(), content[begin:stop].strip(), after.strip()


def _clean(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", value).strip()
    value = LEADING_CHATTER.sub("", value).strip()
    lines = value.split("\n")
    if lines and PREAMBLE.match(lines[0].strip()):  # “基于您提供的……扩写如下：”
        value = "\n".join(lines[1:]).strip()
    value = re.sub(r"(?m)^\s*(?:-{3,}|\*{3,}|_{3,})\s*$\n?", "", value)  # 分隔线
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"(?m)^#{1,6}\s*", "", value)
    value = re.sub(r"\n{3,}", "\n\n", value).strip()
    if len(value) >= 2 and value[0] in "\"“「『" and value[-1] in "\"”」』":
        value = value[1:-1].strip()
    return value


def _known_numbers(*sources: str) -> set[str]:
    found: set[str] = set()
    for source in sources:
        for match in NUMBER.finditer(source or ""):
            found.add(re.sub(r"\s+", "", match.group(0)))
            found.add(re.match(r"\d+(?:\.\d+)?", match.group(0)).group(0))
    return found


def _replace_unsourced_numbers(text: str, known: set[str]) -> tuple[str, list[str]]:
    """对不上来源的数字按“模型所写”处理（§5.11.7、R44）：换成【待补：数值来源】，并返回被换掉的数值。行首序号、变量内不算。"""
    unknown: list[str] = []
    lines = []
    for line in text.split("\n"):
        marker = LIST_MARKER.match(line)
        head, body = (line[:marker.end()], line[marker.end():]) if marker else ("", line)

        def swap(match: re.Match) -> str:
            raw = re.sub(r"\s+", "", match.group(0))
            digits = re.match(r"\d+(?:\.\d+)?", raw).group(0)
            if raw in known or digits in known:
                return match.group(0)
            unknown.append(raw)
            return PENDING_NUMBER

        protected = TOKEN.split(body)
        tokens = TOKEN.findall(body)
        rebuilt = "".join(NUMBER.sub(swap, part) + (tokens[i] if i < len(tokens) else "") for i, part in enumerate(protected))
        lines.append(head + rebuilt)
    return "\n".join(lines), unknown


CITE = re.compile(r"\[(?:证|片|cite):[^\]]+\]")


def precheck(sample: str, selection: str, action_scope: str, known: set[str],
             allowed_cites: set[str] | None = None, allowed_vars: set[str] | None = None,
             mode: str = "rewrite") -> tuple[str | None, list[str], str]:
    """返回 (预检后文字或 None, 提示, 不展示原因)。

    变量和选区里的证据标记只能来自选区，替换时须全部保留；知识库打开时（allowed_cites 不为 None），
    样例可以新增本次检索结果的标记，且至少要引用 1 条。"""
    from .chapter_generation import AI_CONVERSATION_RESIDUALS, NEGATIVE_DEVIATION_TRIGGERS
    if UPSTREAM_ERROR.search((sample or "")[:300]):
        return None, [], "模型服务返回了错误信息（如额度或频率限制），不是改写结果"
    if THINKING.search(sample or ""):
        # 实测 GLM-4.7-flash 经 RAGFlow 时把“分析请求…起草迭代”等思考过程写进正文；整条丢弃，提示换用不输出思考过程的模型
        return None, [], "模型输出了思考过程而不是改写结果（请换用不带思考过程的模型，或在模型服务里关闭思考输出）"
    text = _clean(sample)
    if not text:
        return None, [], "模型没有返回内容"
    if re.search(r"\{\{|\}\}", TOKEN.sub("", text)):
        return None, [], "变量标记残缺（只剩半个 {{ 或 }}）"
    # 流式转发偶尔把一段文字紧挨着重复一遍（实测“巡检报告巡检报告”）；4 字以上的紧邻重复只留一份并提示
    collapsed = REPEAT.sub(r"\1", text) if TOKEN.search(text) is None else text
    repeated = collapsed != text
    text = collapsed
    ratio, slack = LENGTH_LIMIT.get(mode, (2.0, 120))
    plain_len = len(re.sub(r"\s+", "", TOKEN.sub("", text)))
    limit = len(re.sub(r"\s+", "", TOKEN.sub("", selection))) * ratio + slack
    if mode == "shorten" and plain_len >= len(re.sub(r"\s+", "", TOKEN.sub("", selection))):
        return None, [], "缩写后没有变短"
    if mode != "shorten" and plain_len > limit:
        return None, [], f"超出选区改写范围（{plain_len} 字，远长于原文）"
    if re.sub(r"\s+", "", TOKEN.sub("", text)) == re.sub(r"\s+", "", TOKEN.sub("", selection)):
        return None, [], "与原文相同"
    if any(pattern.search(text) for pattern in SENSITIVE):
        return None, [], "含证件号、手机号、银行账号或口令"
    wanted = sorted(TOKEN.findall(selection))
    got = TOKEN.findall(text)
    # 新增的变量只能是已确认的项目事实变量；新增的引用只能是本次检索结果
    extra = [token for token in set(got) - set(wanted) if token not in (allowed_vars or set())]
    if any(not CITE.fullmatch(token) or allowed_cites is None or token not in allowed_cites for token in extra):
        return None, [], "出现了选区以外的变量，或引用了本次检索结果之外的资料" if allowed_cites is not None \
            else "出现了选区以外的变量或证据标记"
    if action_scope == "replace" and sorted(t for t in got if t in wanted) != wanted:
        return None, [], "改动或丢失了选区中的变量、证据标记"
    cited = sorted({token for token in got if allowed_cites and token in allowed_cites})
    if allowed_cites is not None and not cited:
        return None, [], "没有引用本次检索到的资料"
    for residual in AI_CONVERSATION_RESIDUALS:
        text = text.replace(residual, "")
    text = text.strip()
    if not text:
        return None, [], "只有对话套话"
    text, replaced = _replace_unsourced_numbers(text, known)
    notes = ["去掉了紧挨着重复的文字，请核对"] if repeated else []
    if replaced:
        notes.append(f"{len(replaced)} 处数值对不上项目事实、本章条款、引用资料或原文，已换成【待补：数值来源】")
    if AMOUNT.search(text):
        notes.append("涉及金额，采纳后转人工核对")
    hits = [t for t in NEGATIVE_DEVIATION_TRIGGERS if t in text and t not in selection]
    if hits:
        notes.append(f"含负偏离或不满足表述（{hits[0]}），请核对是否属实")
    return text, notes, ""


def cited_tokens(text: str, allowed: set[str]) -> list[str]:
    return sorted({token for token in CITE.findall(text) if token in allowed})


def _merge_similar(samples: list[dict]) -> tuple[list[dict], int]:
    kept: list[dict] = []
    merged = 0
    for sample in samples:
        plain = re.sub(r"\s+", "", sample["text"])
        if any(difflib.SequenceMatcher(None, plain, re.sub(r"\s+", "", other["text"])).ratio() >= 0.92 for other in kept):
            merged += 1
            continue
        kept.append(sample)
    return kept, merged


def text_issues(text: str, known: set[str]) -> list[dict]:
    """写入后对改动段落做的文字规则复查（§5.11.6 第 5 项中不需要模型的部分）。"""
    from .chapter_generation import AI_CONVERSATION_RESIDUALS, NEGATIVE_DEVIATION_TRIGGERS, PLACEHOLDER_REGEXES
    issues = []
    if any(pattern.search(text) for pattern in PLACEHOLDER_REGEXES):
        issues.append({"rule_id": "R15", "severity": "warning", "message": "改动段落含【待补】或未替换的占位，导出前须补齐。"})
    residual = next((r for r in AI_CONVERSATION_RESIDUALS if r in text), None)
    if residual:
        issues.append({"rule_id": "R34", "severity": "blocker", "message": f"改动段落含对话残留：{residual}"})
    deviation = next((t for t in NEGATIVE_DEVIATION_TRIGGERS if t in text), None)
    if deviation:
        issues.append({"rule_id": "R37", "severity": "blocker", "message": f"改动段落含负偏离或不满足表述：{deviation}"})
    _, extra = _replace_unsourced_numbers(text, known)
    if extra:
        issues.append({"rule_id": "R30", "severity": "warning",
                       "message": "改动段落含项目事实与本章条款中没有的数值：" + "、".join(sorted(set(extra))[:5]) + "，须项目负责人确认保留或删除。"})
    return issues


class SelectionRewriteService:
    def __init__(self, demo: Any) -> None:
        self.demo = demo

    # ---------------------------------------------------------------- 共用

    def _load(self, state: DemoState, principal: Principal, project_id: str, chapter_id: str):
        chapter = self.demo._chapter(state, principal, chapter_id)
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
        self.demo._chapter_writer(state, principal, chapter)  # 角色、章节分配、分册已定稿
        from .system_chapters import is_system_chapter
        workflow = state.workflows.get(project_id) or {}
        if is_system_chapter(workflow, chapter):
            raise DomainError(409, "SYSTEM_CHAPTER_READONLY",
                              "本表由系统按数据生成，不能用对话助手改写；请到响应矩阵、项目事实或资料库修改后重新生成。")
        return chapter, workflow

    @staticmethod
    def _sources(state: DemoState, project_id: str, chapter_id: str, workflow: dict) -> tuple[list[dict], list[str]]:
        from .generation_context import project_facts
        facts = [f for f in project_facts(state, project_id) if f.get("status") == "confirmed"]
        requirements = [r["text"] for r in (workflow.get("requirements") or {}).values()
                        if r.get("chapter_id") == chapter_id and r.get("status") == "confirmed"]
        return facts, requirements

    # ---------------------------------------------------------------- 公司策略

    @staticmethod
    def _policy(state: DemoState, company_id: str) -> dict:
        stored = (state.service_stores.get("company_settings") or {}).get(company_id) or {}
        count = int(stored.get("assistant_suggestion_count") or DEFAULT_COUNT)
        return {"enabled": bool(stored.get("assistant_enabled", True)),
                "kb_default": bool(stored.get("assistant_kb_default", True)),
                "allow_kb_off": bool(stored.get("assistant_allow_kb_off", True)),
                "count": min(MAX_COUNT, max(MIN_COUNT, count))}

    def policy(self, principal: Principal, project_id: str, chapter_id: str) -> dict:
        """页面打开对话助手时读取：公司开关、知识库默认值、样例条数、当前模型（含是否本地）与知识库是否已连接。"""
        state = self.demo.repository.read()
        chapter = self.demo._chapter(state, principal, chapter_id)
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
        project = self.demo._project(state, principal, project_id)
        provider = self.demo.resolve_model_provider(state, project_id, "assistant_suggest")
        kb = getattr(self.demo, "knowledge_base", None)
        connected = bool(kb is not None and kb.client_for(project.company_id, state) is not None)
        from icg.infra.model_fallback import model_name
        backup = getattr(provider, "fallback", None)
        return {**self._policy(state, project.company_id),
                "model": model_name(provider),
                "fallback_model": model_name(backup) if backup is not None else None,
                "streaming": bool(getattr(provider, "stream_enabled", False)),
                "is_real_model": bool(getattr(provider, "is_real_model", False)),
                "is_local_model": bool(getattr(provider, "is_local", False)),
                "sensitive_project": bool(project.sensitive), "knowledge_base_connected": connected}

    # ---------------------------------------------------------------- 生成样例

    def generate(self, principal: Principal, project_id: str, chapter_id: str, payload: dict) -> dict:
        prepared = self.prepare(principal, project_id, chapter_id, payload)
        final = None
        for event in self.stream(prepared):
            if event["event"] == "error":
                raise DomainError(event["status"], event["code"], event["message"], event.get("details") or {})
            if event["event"] == "done":
                final = event["batch"]
        return final

    def prepare(self, principal: Principal, project_id: str, chapter_id: str, payload: dict) -> dict:
        """生成前的全部核对与检索（不调用模型、不写状态）；出错直接按 HTTP 错误返回。"""
        state = self.demo.repository.read()
        chapter, workflow = self._load(state, principal, project_id, chapter_id)
        project = self.demo._project(state, principal, project_id)
        policy = self._policy(state, project.company_id)
        if not policy["enabled"]:
            raise DomainError(403, "FORBIDDEN", "本公司已关闭对话助手。")
        self.demo.require_allowed_model(project, state=state)
        start, end, selected = int(payload["start"]), int(payload["end"]), payload["selected_text"]
        content = chapter.content or ""
        if chapter.revision != int(payload["base_revision"]):
            raise DomainError(409, "REVISION_CONFLICT", f"正文已更新到 r{chapter.revision}，请在最新正文中重新选择后再问。")
        if not (0 <= start < end <= len(content)) or content[start:end] != selected or not selected.strip():
            raise DomainError(409, "REVISION_CONFLICT", "选区与已提交正文对不上，请先提交手改或重新选择。")
        from .paragraph_locks import refuse_locked_selection
        refuse_locked_selection(state, chapter, start, end)
        mode = payload.get("mode") or "rewrite"
        instruction = (payload.get("instruction") or "").strip()
        if mode == "instruction" and not instruction:
            raise DomainError(422, "VALIDATION_ERROR", "“按指令修改”须写明修改要求。")
        count = int(payload.get("count") or policy["count"])
        kb_on = payload.get("knowledge_base_enabled")
        kb_on = policy["kb_default"] if kb_on is None else bool(kb_on)
        if not kb_on and not policy["allow_kb_off"]:
            raise DomainError(422, "VALIDATION_ERROR", "本公司要求对话助手使用知识库，不能关闭。")
        from .assistant_sessions import history_lines, readable_session
        session_id = payload.get("session_id")
        history: list[str] = []
        if session_id:
            session = readable_session(state, principal, project_id, session_id)
            if session["owner_id"] != principal.user.id or session["chapter_id"] != chapter_id:
                raise DomainError(403, "FORBIDDEN", "只能在本人本章的会话中继续提问。")
            history = history_lines(workflow, session, selection_hash(selected))
        facts, requirements = self._sources(state, project_id, chapter_id, workflow)
        from .generation_context import refuse_source_change
        refuse_source_change(instruction, {"facts": [{"key": f["key"], "variable": f["variable_token"]} for f in facts]})
        provider = self.demo.resolve_model_provider(state, project_id, "assistant_suggest")
        if not getattr(provider, "is_real_model", False):
            raise DomainError(502, "MODEL_UNAVAILABLE",
                              "尚未接入真实大模型：选区改写不提供模拟样例。请公司管理员在“模型配置”中接入模型后再试。")
        hits, retrieval = ([], {"status": "off", "message": "知识库已关闭，未检索本公司资料；样例标“无知识库来源”。"})
        if kb_on:
            hits, retrieval = self._retrieve(principal, project.company_id, chapter.title, selected, instruction)
        before, paragraph, after = _neighbours(content, start, end)
        known = _known_numbers(selected, paragraph, *requirements, *(f"{f['value']}" for f in facts),
                               *(hit["content"] for hit in hits))
        return {
            "principal": principal, "project_id": project_id, "chapter_id": chapter_id, "chapter_title": chapter.title,
            "base_revision": chapter.revision, "start": start, "end": end, "selected": selected, "mode": mode,
            "instruction": instruction, "count": count, "kb_on": kb_on, "hits": hits, "retrieval": retrieval,
            "known": known, "provider": provider, "session_id": session_id, "sensitive": bool(project.sensitive),
            "fact_tokens": {f["variable_token"] for f in facts},
            "user_content": self._user_content(chapter.title, requirements, facts, before, selected, after, instruction,
                                               hits=hits, history=history),
        }

    def _retrieve(self, principal: Principal, company_id: str, title: str, selected: str, instruction: str):
        kb = getattr(self.demo, "knowledge_base", None)
        if kb is None:
            raise DomainError(409, "KNOWLEDGE_BASE_NOT_CONFIGURED", "本公司知识库尚未连接；可关闭知识库后重试（样例将标“无知识库来源”）。")
        query = " ".join(part for part in (title, selected, instruction) if part)[:500]
        try:
            raw, reason = kb.search(company_id, query, limit=5, user=principal.user)
        except Exception as error:
            raise DomainError(502, "KNOWLEDGE_BASE_UPSTREAM_ERROR", "知识库检索暂时不可用，可稍后重试或关闭知识库后重试。") from error
        if reason == "RAGFlow is not configured":
            raise DomainError(409, "KNOWLEDGE_BASE_NOT_CONFIGURED", "本公司知识库尚未连接；可关闭知识库后重试（样例将标“无知识库来源”）。")
        hits = [{"cite_tag": hit.cite_tag, "source_id": hit.source_id, "source_type": hit.source_type, "name": hit.name,
                 "item_type": hit.item_type, "revision": hit.revision, "score": round(float(hit.score), 4),
                 "content": hit.content[:600], "document_id": hit.document_id, "chunk_ids": list(hit.chunk_ids)}
                for hit in raw if not hit.reference_only]
        if not hits:
            return [], {"status": "empty", "message": "本公司知识库和资料库中没有找到相关内容。可以关闭知识库后重试（样例将标“无知识库来源”），"
                                                       "或去资料库、方案片段库补充资料。"}
        return hits, {"status": "found", "message": f"检索到 {len(hits)} 条本公司资料，样例须至少引用 1 条。", "count": len(hits)}

    def stream(self, prepared: dict, cancel: Any = None):
        """逐条产出事件：started → delta（逐字）/ fallback（改用备用模型）→ sample / dropped（按完成先后）→ done；
        检索无结果时不调用模型直接 done。cancel（threading.Event）置位或生成器被关闭时停止全部写法、不保存结果，
        产出 cancelled。"""
        import queue
        import threading
        from icg.infra.model_fallback import call_model, failure_text, model_name
        from icg.infra.openai_model import ModelCancelled
        cancel = cancel if cancel is not None else threading.Event()
        provider, mode = prepared["provider"], prepared["mode"]
        styles = STYLES[:prepared["count"]]
        hits = prepared["hits"]
        allowed = {hit["cite_tag"] for hit in hits} if prepared["kb_on"] else None
        backup = getattr(provider, "fallback", None)
        yield {"event": "started", "styles": [label for _, label, _ in styles], "retrieval": prepared["retrieval"],
               "knowledge_base_enabled": prepared["kb_on"], "model": model_name(provider),
               "fallback_model": model_name(backup) if backup is not None else None,
               "streaming": bool(getattr(provider, "stream_enabled", False))}
        samples, dropped, switched, queued = [], [], [], []
        if prepared["kb_on"] and not hits:
            yield from self._finish(prepared, samples, dropped)
            return
        inbox: queue.Queue = queue.Queue()

        def work(style):
            from icg.infra.model_fallback import degradable
            key, label, hint = style
            system = self._system_prompt(MODES[mode], hint, knowledge_base=prepared["kb_on"])
            waited, attempt = 0.0, 0
            while True:
                try:
                    result = call_model(provider, system, prepared["user_content"],
                                        on_delta=lambda text: inbox.put(("delta", label, text)),
                                        on_reset=lambda name, why: inbox.put(("fallback", label, (name, why))), cancel=cancel)
                    inbox.put(("result", style, result))
                    return
                except ModelCancelled:
                    inbox.put(("cancelled", style, None))
                    return
                except Exception as error:  # 单条失败不影响其他写法
                    # 敏感项目只能用本地模型（PRD §6.4、§5.11.14 第 18 项）：本地模型都不可用时排队等待重试，不改走云端
                    if prepared.get("sensitive") and degradable(error) and waited < LOCAL_QUEUE_SECONDS and not cancel.is_set():
                        attempt += 1
                        pause = min(LOCAL_QUEUE_STEPS[min(attempt - 1, len(LOCAL_QUEUE_STEPS) - 1)], LOCAL_QUEUE_SECONDS - waited)
                        inbox.put(("queued", label, {"attempt": attempt, "wait_seconds": pause, "waited_seconds": waited,
                                                     "reason": failure_text(error)}))
                        if cancel.wait(pause):
                            inbox.put(("cancelled", style, None))
                            return
                        waited += pause
                        continue
                    detail = failure_text(error)
                    if prepared.get("sensitive") and degradable(error):
                        detail += f"；敏感项目只能用本地模型，已排队等待 {int(waited)} 秒仍不可用，未改走云端"
                    inbox.put(("failed", style, detail))
                    return

        for style in styles:
            threading.Thread(target=work, args=(style,), daemon=True).start()
        remaining = len(styles)
        try:
            while remaining and not cancel.is_set():
                try:
                    kind, item, value = inbox.get(timeout=0.5)
                except queue.Empty:
                    continue
                if kind == "delta":
                    yield {"event": "delta", "style": item, "text": value}
                    continue
                if kind == "queued":
                    if not queued:
                        self._notify_queue(prepared, value["reason"])
                    queued.append(item)
                    yield {"event": "queued", "style": item, **value,
                           "message": f"本地模型暂时不可用（{value['reason']}），敏感项目不改走云端，{int(value['wait_seconds'])} 秒后重试"}
                    continue
                if kind == "fallback":
                    switched.append({"style": item, "model": value[0], "reason": value[1]})
                    yield {"event": "fallback", "style": item, "model": value[0], "reason": value[1]}
                    continue
                remaining -= 1
                if kind == "cancelled":
                    continue
                key, label, _ = item
                if kind == "failed":
                    entry = {"style": label, "reason": f"模型调用失败：{value}"}
                    dropped.append(entry)
                    yield {"event": "dropped", **entry}
                    continue
                text, notes, reason = precheck(value.text, prepared["selected"], "replace", prepared["known"], allowed,
                                               prepared["fact_tokens"], mode)
                if text is None:
                    entry = {"style": label, "reason": reason}
                    dropped.append(entry)
                    yield {"event": "dropped", **entry}
                    continue
                sources = [dict(hit, content=hit["content"][:200]) for hit in hits if hit["cite_tag"] in cited_tokens(text, allowed or set())]
                sample = {"id": new_id("sample"), "style": key, "style_label": label, "text": text, "warnings": notes,
                          "chars": len(TOKEN.sub("", text)), "sources": sources, "status": "proposed",
                          "model": value.model, "is_local_model": value.is_local, "is_fallback": value.is_fallback,
                          "fallback_reason": value.fallback_reason}
                samples.append(sample)
                yield {"event": "sample", "sample": sample}
            if cancel.is_set():
                yield {"event": "cancelled", "message": "已停止生成，正文没有修改，本次样例不保存。"}
                return
        finally:
            cancel.set()  # 正常结束或被关闭（用户停止、断开连接）都让还在跑的写法停下
        order = {key: index for index, (key, _, _) in enumerate(styles)}
        samples.sort(key=lambda item: order[item["style"]])
        prepared["fallback_used"] = switched
        yield from self._finish(prepared, samples, dropped)

    def _notify_queue(self, prepared: dict, reason: str) -> None:
        """敏感项目开始排队等本地模型：发“本地任务排队”提醒（§5.12.2、§6.5），排队原因如实写“只能使用本地服务”。"""
        from .notifications import notify

        def write(state: DemoState):
            notify(state, [prepared["principal"].user.id], "local_task_queued", "对话助手正在排队等待本地模型",
                   f"《{prepared['chapter_title']}》：{reason}。敏感项目只能使用本地服务，不改走云端，正在排队重试。",
                   now=iso_time(self.demo._now()), project_id=prepared["project_id"], target_id=prepared["chapter_id"])
        try:
            self.demo.repository.transaction(write)
        except Exception:
            pass  # 提醒失败不影响本次结果

    def _finish(self, prepared: dict, samples: list[dict], dropped: list[dict]):
        principal, project_id, chapter_id = prepared["principal"], prepared["project_id"], prepared["chapter_id"]
        from icg.infra.model_fallback import model_name
        samples, merged = _merge_similar(samples)
        if merged:
            dropped.append({"style": "相近写法", "reason": f"{merged} 条与其他样例几乎相同，已合并"})
        no_results = prepared["kb_on"] and not prepared["hits"]
        if not samples and not no_results:
            yield {"event": "error", "status": 502, "code": "MODEL_OUTPUT_INVALID",
                   "message": "模型返回的样例都没有通过预检，正文没有修改：" + "；".join(f"{d['style']}：{d['reason']}" for d in dropped)}
            return
        provider = prepared["provider"]
        batch = {
            "id": new_id("rewrite"), "project_id": project_id, "chapter_id": chapter_id,
            "base_revision": prepared["base_revision"], "start": prepared["start"], "end": prepared["end"],
            "selected_text": prepared["selected"], "selection_hash": selection_hash(prepared["selected"]),
            "mode": prepared["mode"], "mode_label": MODES[prepared["mode"]][0], "instruction": prepared["instruction"],
            "samples": samples, "dropped": dropped, "knowledge_base_enabled": prepared["kb_on"],
            "retrieval": prepared["retrieval"], "provider": getattr(provider, "name", "model"),
            "model": model_name(provider), "is_local_model": bool(getattr(provider, "is_local", False)),
            # 改用备用模型的写法（PRD §6.5 规则 3：界面显示“已使用备用模型 X”，记录实际模型）
            "fallback_used": prepared.get("fallback_used") or [],
            "models_used": sorted({s.get("model") or model_name(provider) for s in samples}),
            "status": "no_results" if no_results else "proposed",
            "created_by": principal.user.id, "created_at": iso_time(self.demo._now()),
        }

        def operation(current: DemoState):
            from .assistant_sessions import record_request
            actual, _ = self._load(current, principal, project_id, chapter_id)
            if actual.revision != batch["base_revision"]:
                raise DomainError(409, "REVISION_CONFLICT", "生成样例期间正文已被提交更新，请重新选择后再问。")
            flow = _project_workflow(current, project_id)
            batch["session_id"] = record_request(flow, principal, actual, batch, prepared["session_id"], iso_time(self.demo._now()))
            store = flow.setdefault("assistant_suggestions", {})
            store[batch["id"]] = batch
            for old in sorted(store.values(), key=lambda b: b["created_at"])[:-KEEP_BATCHES]:
                store.pop(old["id"], None)
            self.demo._audit(current, principal, actual, "assistant.selection_samples",
                             {"batch_id": batch["id"], "samples": len(samples), "dropped": len(dropped),
                              "mode": batch["mode"], "knowledge_base_enabled": batch["knowledge_base_enabled"]})
            return public_batch(batch)

        try:
            yield {"event": "done", "batch": self.demo.repository.transaction(operation)}
        except DomainError as error:
            yield {"event": "error", "status": error.status, "code": error.code, "message": error.message,
                   "details": getattr(error, "details", None) or {}}

    @staticmethod
    def _system_prompt(mode: tuple[str, str], style_hint: str, *, knowledge_base: bool = False) -> str:
        lines = [
            "你是投标文件编写助手，只修改用户选中的那段文字。",
            f"修改方式：{mode[0]}——{mode[1]}。写法：{style_hint}。",
            "必须遵守：",
            "1. 形如 {{fact:…}}、{{sla:…}} 的变量和形如 [证:…]、[片:…] 的证据标记原样保留，不得改写、删除或换成数字；",
            "2. 不新增原文、招标要求、项目事实" + ("和【可引用的资料】" if knowledge_base else "") + "中没有的数字、型号、人员、案例、客户名称和承诺；",
            "3. 不写“以下是”“希望对你有帮助”等对话语气，不用 Markdown 符号、标题和分隔线；",
            "4. 只输出修改后的这段正文，不加标题、引号和解释；篇幅与原文相近" + ("（扩写不超过原文的 2 倍）" if mode[0] == "扩写" else "") + "；",
            "5. 【前文】【后文】只用来理解上下文，不要复述，也不要改写整章；招标要求只用来把握响应重点。",
        ]
        if knowledge_base:
            lines.append("6. 至少引用 1 条【可引用的资料】：在用到该资料的句子末尾原样写上它的标记（例如 [片:lib-1]），只能用列出的标记。")
        return "\n".join(lines)

    @staticmethod
    def _user_content(title, requirements, facts, before, selected, after, instruction, *, hits=(), history=()) -> str:
        lines = [f"【章节】{title}"]
        if requirements:
            lines.append("【本章回应的招标要求】")
            lines += [f"- {text[:200]}" for text in requirements[:6]]
        if facts:
            lines.append("【已确认的项目事实（正文中用变量表示）】")
            lines += [f"- {f['key']}：{f['value']}{f.get('unit') or ''}（变量 {f['variable_token']}）" for f in facts[:12]]
        if hits:
            lines.append("【可引用的资料】（本公司知识库检索结果，只能引用这里列出的标记）")
            lines += [f"- {hit['cite_tag']} {hit['name']}（v{hit['revision']}）：{hit['content'][:300]}" for hit in hits]
        if before:
            lines.append(f"【前文】{before[:400]}")
        lines.append(f"【选中的文字】\n{selected}")
        if after:
            lines.append(f"【后文】{after[:400]}")
        if history:
            lines.append("【本会话之前对这段文字的要求与样例】")
            lines += list(history)
        if instruction:
            lines.append(f"【修改要求】{instruction}")
        # 输出要求放在最后：实测云端模型（经 RAGFlow）只看系统提示时会写分析、方案标题和上下文效果展示
        limit = max(30, len(selected) * 2)
        lines.append(f"【输出要求】只输出用来替换【选中的文字】的那一段正文本身，约 {len(selected)} 字、不超过 {limit} 字；"
                     "不要分析、标题、引号、列表、说明，也不要展示前文后文或替换效果。")
        return "\n".join(lines)

    # ---------------------------------------------------------------- 写入

    def apply(self, principal: Principal, project_id: str, chapter_id: str, payload: dict) -> dict:
        action = payload["action"]

        def operation(state: DemoState):
            chapter, workflow = self._load(state, principal, project_id, chapter_id)
            self.demo._lease(chapter, principal, payload["lease_token"])
            batch = (workflow.get("assistant_suggestions") or {}).get(payload["batch_id"])
            if batch is None or batch["chapter_id"] != chapter_id or batch["created_by"] != principal.user.id:
                raise DomainError(404, "NOT_FOUND", "未找到本人在本章生成的样例。")
            sample = next((s for s in batch["samples"] if s["id"] == payload["sample_id"]), None)
            if sample is None:
                raise DomainError(404, "NOT_FOUND", "未找到该样例。")
            if batch["status"] != "proposed" or sample["status"] != "proposed":
                raise DomainError(409, "REVISION_CONFLICT", "这组样例已采纳或已失效，请重新选择后再问。")
            now = iso_time(self.demo._now())
            # 本人未提交的编辑草稿先提交为一个“手改”版本，保证一个版本只对应一种修改方式（§5.11.6 第 3 项）
            draft = chapter.drafts.get(principal.user.id)
            if draft is not None and draft.content != chapter.content:
                if draft.base_revision != chapter.revision:
                    raise DomainError(409, "REVISION_CONFLICT", "编辑草稿基于旧版本，请先处理草稿后再写入样例。")
                from .paragraph_locks import refuse_locked_change
                refuse_locked_change(state, chapter, draft.content)
                chapter.content = draft.content
                chapter.revision += 1
                state.projects[project_id].revision += 1
                chapter.versions.append({"revision": chapter.revision, "content": chapter.content,
                                         "actor_id": principal.user.id, "created_at": now,
                                         "version_origin": "manual", "edit_mode": "manual"})
            chapter.drafts.pop(principal.user.id, None)
            content = chapter.content or ""
            start, end, selected = batch["start"], batch["end"], batch["selected_text"]
            moved = False
            if content[start:end] != selected:
                positions = [m.start() for m in re.finditer(re.escape(selected), content)]
                if len(positions) != 1:
                    batch["status"] = "invalidated"
                    for item in batch["samples"]:
                        item["status"] = "invalidated"
                    return {"invalidated": True, "batch": public_batch(batch)}
                start, end, moved = positions[0], positions[0] + len(selected), True
            if moved and payload.get("confirm_start") != start:
                raise DomainError(409, "REVISION_CONFLICT", "原文位置已变化，已在本章重新找到，请再次核对差异后确认写入。",
                                  {"relocated": True, "start": start, "end": end, "revision": chapter.revision})
            text = sample["text"]
            begin, stop = _paragraph_bounds(content, start, end)
            if action == "replace":
                new_content = content[:start] + text + content[end:]
                changed = (start, start + len(text))
                edit_mode = "assistant_replace"
            else:
                as_paragraph = "\n" in text or end >= stop
                if as_paragraph:
                    new_content = content[:stop] + "\n" + text + content[stop:]
                    changed = (stop + 1, stop + 1 + len(text))
                else:
                    new_content = content[:end] + text + content[end:]
                    changed = (end, end + len(text))
                edit_mode = "assistant_insert"
            base_revision = chapter.revision
            from .paragraph_locks import refuse_locked_change
            refuse_locked_change(state, chapter, new_content)
            chapter.content = new_content
            chapter.revision += 1
            state.projects[project_id].revision += 1
            operation_id = new_id("edit")
            chapter.versions.append({"revision": chapter.revision, "content": chapter.content,
                                     "actor_id": principal.user.id, "created_at": now,
                                     "version_origin": "assistant_edit", "edit_mode": edit_mode,
                                     "edit_operation_id": operation_id})
            facts, requirements = self._sources(state, project_id, chapter_id, workflow)
            p_begin, p_stop = _paragraph_bounds(new_content, changed[0], max(changed[0], changed[1] - 1))
            changed_text = new_content[p_begin:p_stop]
            known = _known_numbers(selected, content[begin:stop], *requirements, *(f"{f['value']}" for f in facts))
            issues = text_issues(changed_text, known)
            record = {
                "id": operation_id, "chapter_id": chapter_id, "edit_mode": edit_mode,
                "edit_mode_label": "对话助手替换" if action == "replace" else "对话助手增加",
                "base_revision": base_revision, "result_revision": chapter.revision,
                "selection": {"start": start, "end": end, "hash": batch["selection_hash"], "relocated": moved},
                "changed_range": list(changed), "batch_id": batch["id"], "sample_id": sample["id"],
                "style": sample["style_label"], "mode": batch["mode_label"],
                "knowledge_base_enabled": bool(batch.get("knowledge_base_enabled")),
                "sources": [{k: v for k, v in src.items() if k != "content"} for src in sample.get("sources", [])],
                "source_note": "引用本公司知识库" if sample.get("sources") else "无知识库来源",
                "original_text": selected, "written_text": text, "session_id": batch.get("session_id"),
                "actor_id": principal.user.id, "actor_name": principal.user.name, "created_at": now,
                "recheck": {"scope": "changed_paragraphs", "issues": issues, "checked_at": now},
            }
            flow = _project_workflow(state, project_id)
            flow.setdefault("chapter_edit_operations", []).append(record)
            if sample.get("sources"):
                # 写入正文的 [片:来源编号] 记为本章已核对的引用，后续 R02 不再把它当作未核实片段
                cites = flow.setdefault("assistant_citations", {}).setdefault(chapter_id, [])
                cites.extend(src["source_id"] for src in sample["sources"] if src["source_id"] not in cites)
            if batch.get("session_id"):
                from .assistant_sessions import record_apply
                record_apply(flow, batch["session_id"], record)
            flow.setdefault("chapter_statuses", {})[chapter_id] = "人工已处理"
            batch["status"] = "adopted"
            for item in batch["samples"]:
                item["status"] = "adopted" if item["id"] == sample["id"] else "not_adopted"
            self.demo._audit(state, principal, chapter, "assistant.selection_apply",
                             {"operation_id": operation_id, "edit_mode": edit_mode, "revision": chapter.revision})
            return {"invalidated": False, "revision": chapter.revision, "content": chapter.content,
                    "operation": record, "batch": public_batch(batch)}

        result = self.demo.repository.transaction(operation)
        if result.get("invalidated"):
            raise DomainError(409, "REVISION_CONFLICT", "原文已被改动，在本章找不到或找到多处，样例已失效；请重新选择后再问。",
                              {"relocated": False, "batch_id": payload["batch_id"]})
        return result

    def operations(self, principal: Principal, project_id: str, chapter_id: str) -> dict:
        state = self.demo.repository.read()
        chapter = self.demo._chapter(state, principal, chapter_id)
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
        records = [r for r in (state.workflows.get(project_id) or {}).get("chapter_edit_operations", [])
                   if r["chapter_id"] == chapter_id]
        return {"operations": records}


def _project_workflow(state: DemoState, project_id: str) -> dict:
    """取项目工作流；还没有时按标准结构新建（不能建空字典，否则工作区读取缺字段）。"""
    from .workflow_orchestrator import _blank_workflow
    return state.workflows.setdefault(project_id, _blank_workflow())


def public_batch(batch: dict) -> dict:
    kb_on = bool(batch.get("knowledge_base_enabled"))
    retrieval = batch.get("retrieval") or {"status": "off", "message": "知识库已关闭，未检索本公司资料。"}
    return {key: batch[key] for key in (
        "id", "chapter_id", "base_revision", "start", "end", "selected_text", "selection_hash", "mode", "mode_label",
        "instruction", "samples", "dropped", "knowledge_base_enabled", "provider", "model", "is_local_model",
        "status", "created_at")} | {
        "session_id": batch.get("session_id"), "retrieval": retrieval,
        "fallback_used": batch.get("fallback_used") or [], "models_used": batch.get("models_used") or [],
        "source_note": ("引用本公司知识库（每条样例至少 1 条）" if retrieval.get("status") == "found"
                        else retrieval.get("message", "")) if kb_on else "无知识库来源（知识库已关闭）"}
