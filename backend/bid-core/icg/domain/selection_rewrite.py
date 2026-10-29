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
# 没有接入真实模型时直接说明，不返回模拟样例。知识库检索与引用、多轮会话在第二步接入，本步样例一律标“无知识库来源”。

from __future__ import annotations

import difflib
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
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
PENDING_NUMBER = "【待补：数值来源】"


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
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"(?m)^#{1,6}\s*", "", value)
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


def precheck(sample: str, selection: str, action_scope: str, known: set[str]) -> tuple[str | None, list[str], str]:
    """返回 (预检后文字或 None, 提示, 不展示原因)。替换与插入共用：变量/证据标记只能来自选区，替换时须全部保留。"""
    from .chapter_generation import AI_CONVERSATION_RESIDUALS, NEGATIVE_DEVIATION_TRIGGERS
    text = _clean(sample)
    if not text:
        return None, [], "模型没有返回内容"
    if re.sub(r"\s+", "", text) == re.sub(r"\s+", "", selection):
        return None, [], "与原文相同"
    if any(pattern.search(text) for pattern in SENSITIVE):
        return None, [], "含证件号、手机号、银行账号或口令"
    wanted, got = sorted(TOKEN.findall(selection)), sorted(TOKEN.findall(text))
    if set(got) - set(wanted):
        return None, [], "出现了选区以外的变量或证据标记"
    if action_scope == "replace" and got != wanted:
        return None, [], "改动或丢失了选区中的变量、证据标记"
    for residual in AI_CONVERSATION_RESIDUALS:
        text = text.replace(residual, "")
    text = text.strip()
    if not text:
        return None, [], "只有对话套话"
    text, replaced = _replace_unsourced_numbers(text, known)
    notes = []
    if replaced:
        notes.append(f"{len(replaced)} 处数值对不上项目事实、本章条款或原文，已换成【待补：数值来源】")
    if AMOUNT.search(text):
        notes.append("涉及金额，采纳后转人工核对")
    hits = [t for t in NEGATIVE_DEVIATION_TRIGGERS if t in text and t not in selection]
    if hits:
        notes.append(f"含负偏离或不满足表述（{hits[0]}），请核对是否属实")
    return text, notes, ""


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

    # ---------------------------------------------------------------- 生成样例

    def generate(self, principal: Principal, project_id: str, chapter_id: str, payload: dict) -> dict:
        state = self.demo.repository.read()
        chapter, workflow = self._load(state, principal, project_id, chapter_id)
        project = self.demo._project(state, principal, project_id)
        self.demo.require_allowed_model(project, state=state)
        start, end, selected = int(payload["start"]), int(payload["end"]), payload["selected_text"]
        content = chapter.content or ""
        if chapter.revision != int(payload["base_revision"]):
            raise DomainError(409, "REVISION_CONFLICT", f"正文已更新到 r{chapter.revision}，请在最新正文中重新选择后再问。")
        if not (0 <= start < end <= len(content)) or content[start:end] != selected or not selected.strip():
            raise DomainError(409, "REVISION_CONFLICT", "选区与已提交正文对不上，请先提交手改或重新选择。")
        mode = payload.get("mode") or "rewrite"
        instruction = (payload.get("instruction") or "").strip()
        if mode == "instruction" and not instruction:
            raise DomainError(422, "VALIDATION_ERROR", "“按指令修改”须写明修改要求。")
        count = int(payload.get("count") or DEFAULT_COUNT)
        facts, requirements = self._sources(state, project_id, chapter_id, workflow)
        from .generation_context import refuse_source_change
        refuse_source_change(instruction, {"facts": [{"key": f["key"], "variable": f["variable_token"]} for f in facts]})
        provider = self.demo.resolve_model_provider(state, project_id)
        if not getattr(provider, "is_real_model", False):
            raise DomainError(502, "MODEL_UNAVAILABLE",
                              "尚未接入真实大模型：选区改写不提供模拟样例。请公司管理员在“模型配置”中接入模型后再试。")
        before, paragraph, after = _neighbours(content, start, end)
        known = _known_numbers(selected, paragraph, *requirements, *(f"{f['value']}" for f in facts))
        styles = STYLES[:count]
        user_content = self._user_content(chapter.title, requirements, facts, before, selected, after, instruction)

        def call(style):
            key, label, hint = style
            system = self._system_prompt(MODES[mode], hint)
            try:
                reply = provider.suggest(system, user_content)
            except Exception as error:  # 单条失败不影响其他写法
                return key, label, None, type(error).__name__
            return key, label, reply if isinstance(reply, str) else str(reply), ""

        with ThreadPoolExecutor(max_workers=len(styles)) as pool:
            replies = list(pool.map(call, styles))
        samples, dropped = [], []
        for key, label, reply, failure in replies:
            if reply is None:
                dropped.append({"style": label, "reason": f"模型调用失败（{failure}）"})
                continue
            text, notes, reason = precheck(reply, selected, "replace", known)
            if text is None:
                dropped.append({"style": label, "reason": reason})
                continue
            samples.append({"id": new_id("sample"), "style": key, "style_label": label, "text": text,
                            "warnings": notes, "chars": len(text), "sources": [], "status": "proposed"})
        samples, merged = _merge_similar(samples)
        if merged:
            dropped.append({"style": "相近写法", "reason": f"{merged} 条与其他样例几乎相同，已合并"})
        if not samples:
            raise DomainError(502, "MODEL_OUTPUT_INVALID", "模型返回的样例都没有通过预检，正文没有修改：" +
                              "；".join(f"{d['style']}：{d['reason']}" for d in dropped))

        batch = {
            "id": new_id("rewrite"), "project_id": project_id, "chapter_id": chapter_id,
            "base_revision": chapter.revision, "start": start, "end": end, "selected_text": selected,
            "selection_hash": selection_hash(selected), "mode": mode, "mode_label": MODES[mode][0],
            "instruction": instruction, "samples": samples, "dropped": dropped, "knowledge_base_enabled": False,
            "provider": getattr(provider, "name", "model"), "model": getattr(provider, "model", ""),
            "is_local_model": bool(getattr(provider, "is_local", False)), "status": "proposed",
            "created_by": principal.user.id, "created_at": iso_time(self.demo._now()),
        }

        def operation(current: DemoState):
            actual, flow = self._load(current, principal, project_id, chapter_id)
            if actual.revision != batch["base_revision"]:
                raise DomainError(409, "REVISION_CONFLICT", "生成样例期间正文已被提交更新，请重新选择后再问。")
            store = _project_workflow(current, project_id).setdefault("assistant_suggestions", {})
            store[batch["id"]] = batch
            for old in sorted(store.values(), key=lambda b: b["created_at"])[:-KEEP_BATCHES]:
                store.pop(old["id"], None)
            self.demo._audit(current, principal, actual, "assistant.selection_samples",
                             {"batch_id": batch["id"], "samples": len(samples), "dropped": len(dropped), "mode": mode})
            return public_batch(batch)

        return self.demo.repository.transaction(operation)

    @staticmethod
    def _system_prompt(mode: tuple[str, str], style_hint: str) -> str:
        return "\n".join([
            "你是投标文件编写助手，只修改用户选中的那段文字。",
            f"修改方式：{mode[0]}——{mode[1]}。写法：{style_hint}。",
            "必须遵守：",
            "1. 形如 {{fact:…}}、{{sla:…}} 的变量和形如 [证:…]、[片:…] 的证据标记原样保留，不得改写、删除或换成数字；",
            "2. 不新增原文、招标要求和项目事实中没有的数字、型号、人员、案例、客户名称和承诺；",
            "3. 不写“以下是”“希望对你有帮助”等对话语气，不用 Markdown 符号；",
            "4. 只输出修改后的正文，不加标题、引号和解释。",
        ])

    @staticmethod
    def _user_content(title, requirements, facts, before, selected, after, instruction) -> str:
        lines = [f"【章节】{title}"]
        if requirements:
            lines.append("【本章回应的招标要求】")
            lines += [f"- {text[:200]}" for text in requirements[:6]]
        if facts:
            lines.append("【已确认的项目事实（正文中用变量表示）】")
            lines += [f"- {f['key']}：{f['value']}{f.get('unit') or ''}（变量 {f['variable_token']}）" for f in facts[:12]]
        if before:
            lines.append(f"【前文】{before[:400]}")
        lines.append(f"【选中的文字】\n{selected}")
        if after:
            lines.append(f"【后文】{after[:400]}")
        if instruction:
            lines.append(f"【修改要求】{instruction}")
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
                "style": sample["style_label"], "mode": batch["mode_label"], "knowledge_base_enabled": False,
                "sources": [], "source_note": "无知识库来源", "original_text": selected, "written_text": text,
                "actor_id": principal.user.id, "actor_name": principal.user.name, "created_at": now,
                "recheck": {"scope": "changed_paragraphs", "issues": issues, "checked_at": now},
            }
            flow = _project_workflow(state, project_id)
            flow.setdefault("chapter_edit_operations", []).append(record)
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
    return {key: batch[key] for key in (
        "id", "chapter_id", "base_revision", "start", "end", "selected_text", "selection_hash", "mode", "mode_label",
        "instruction", "samples", "dropped", "knowledge_base_enabled", "provider", "model", "is_local_model",
        "status", "created_at")} | {"source_note": "无知识库来源（本步未检索知识库）"}
