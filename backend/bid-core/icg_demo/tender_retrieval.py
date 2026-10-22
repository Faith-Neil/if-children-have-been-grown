# 为什么有这个文件：实现本项目招标文件切片轻量索引检索与结构化证据展示（APP-M2-T184，PRD v1.8 §技术方案E08、§5.11.15）。
# 它解决什么问题：
# 1. 招标文件切片与轻量索引检索：基于本项目上传已解析的招标文件与条款抽取结果，构建细粒度切片索引；
#    支持按关键词检索关键段落，提取原文页码、条款编号与条款类型（废标条款/评分标准/商务要求/技术要求/通用条款）；
# 2. 结构化证据卡展示与关键词高亮：在 AI 助手或证据候选卡片中结构化展示命中结果，HTML 安全包裹 <mark> 标签高亮匹配词；
# 3. 一键条款约束注入：支持一键将选定的招标文件条款约束注入当前编辑章节 Prompt 上下文，计入上下文指纹；
# 4. PRD E08 特性开关控制：一期可选且默认关闭，开关关闭时不检索并提示未启用，显式开启后方可执行切片检索；
# 5. 严格租户隔离与权限门禁：严格限定在当前 project_id 所属招标文件范围，严禁跨项目越权探测；
#    遵循 PRD 5.11.15 规范：本项目数据类证据卡一律 can_insert=False，禁止直接替换正文。

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from typing import Any

from .domain import Chapter, DemoState, DomainError, Principal, Project, new_id
from .project_access import chapter_edit, lead, normalize_role, require_same_company, READONLY_SYSTEM_ROLES


CLAUSE_NUMBER_REGEX = re.compile(
    r"^(?:[★▲]\s*)?"
    r"(第[0-9一二三四五六七八九十百]+[条章节部款项]"
    r"|\d+(?:\.\d+)+"
    r"|[（(]\d+[)）]"
    r"|[一二三四五六七八九十]+[、. ]"
    r"|[（(][一二三四五六七八九十]+[)）]"
    r"|[0-9]{1,3}[、.])"
)

DISQUALIFICATION_KEYWORDS = (
    "废标", "否决投标", "无效标", "不予受理", "视同放弃", "取消投标资格", "一票否决", "实质性要求", "★", "必须满足"
)
SCORING_KEYWORDS = (
    "评分标准", "评分办法", "评审办法", "评分细则", "客观分", "主观分", "分值", "满分", "评标", "得分为", "得分"
)
BUSINESS_KEYWORDS = (
    "商务要求", "商务响应", "商务条款", "投标保证金", "保证金", "开标时间", "开标", "付款方式", "付款", "企业资质", "同类业绩",
    "签约日期", "交货期", "保函", "合同金额", "原厂授权", "授权书"
)
TECHNICAL_KEYWORDS = (
    "技术要求", "技术规格", "技术指标", "巡检", "响应时限", "响应时间", "故障恢复", "高可用", "双活", "架构", "SLA",
    "功能要求", "性能指标", "维保服务", "部署方案", "数据库"
)

STOP_WORDS = {
    "请问", "请", "问", "是", "多少", "的", "了", "在", "和", "及", "与", "有", "哪些",
    "什么", "怎么", "如何", "为", "按", "由", "对", "以", "中", "上", "下", "本", "该", "个",
    "吗", "吧", "呢", "能否", "给出", "列出", "查看", "检索", "查询", "切片", "条款",
    "本项目", "本项目中", "项目", "是多少", "有哪些", "有什么"
}


def extract_clause_number(text: str) -> str | None:
    """提取段落开头的条款编号，支持中英文数字、星号以及冒号前缀。"""
    stripped = text.strip()
    match = CLAUSE_NUMBER_REGEX.match(stripped)
    if match:
        return match.group(0).strip()
    colon_match = re.match(r"^(?:★|▲)?(技术要求|商务要求|通用要求|评分项|废标项)\s*[:：]", stripped)
    if colon_match:
        prefix = "★" if "★" in stripped[:3] else ""
        return prefix + colon_match.group(1)
    return None


def classify_clause_type(text: str) -> tuple[str, str]:
    """返回 (clause_type, clause_type_label)。"""
    if any(k in text for k in DISQUALIFICATION_KEYWORDS):
        return ("disqualification", "废标条款")
    if any(k in text for k in SCORING_KEYWORDS) or re.search(r"\d+(?:\.\d+)?\s*分", text):
        return ("scoring", "评分标准")
    if any(k in text for k in BUSINESS_KEYWORDS):
        return ("business", "商务要求")
    if any(k in text for k in TECHNICAL_KEYWORDS):
        return ("technical", "技术要求")
    return ("general", "通用条款")


def detect_importance(text: str, clause_type: str) -> str:
    """判定条款重要性等级：star(★) / disqualification / scoring / normal。"""
    if "★" in text or "星号" in text:
        return "star"
    if clause_type == "disqualification":
        return "disqualification"
    if clause_type == "scoring":
        return "scoring"
    return "normal"


def extract_score_weight(text: str) -> float | None:
    """提取评分条款分值（如 '10分' -> 10.0）。"""
    match = re.search(r"(?:满分|最高|得分|得|占|计)?\s*(\d+(?:\.\d+)?)\s*分", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def tokenize_query(query: str) -> list[str]:
    """提取查询中的检索关键词元，过滤无意义停用词，按词长降序排列。"""
    raw_query = query.strip()
    if not raw_query:
        return []

    tokens: list[str] = []
    eng_nums = re.findall(r"[A-Za-z0-9_.-]+", raw_query)
    for en in eng_nums:
        if len(en) >= 2 or en in ("★", "▲"):
            tokens.append(en)

    cleaned = raw_query
    for sw in sorted(STOP_WORDS, key=len, reverse=True):
        cleaned = cleaned.replace(sw, " ")

    parts = re.split(r"[\s,，;；、?？!！]+", cleaned)
    for p in parts:
        p_clean = p.strip()
        if not p_clean:
            continue
        chinese_text = re.sub(r"[A-Za-z0-9_.-]+", "", p_clean)
        if len(chinese_text) >= 2:
            tokens.append(chinese_text)
            for sub_len in range(min(len(chinese_text) - 1, 6), 1, -1):
                for i in range(len(chinese_text) - sub_len + 1):
                    sub = chinese_text[i:i + sub_len]
                    if sub not in STOP_WORDS and sub not in tokens:
                        tokens.append(sub)
        elif chinese_text in ("★", "分"):
            tokens.append(chinese_text)

    if "★" in query and "★" not in tokens:
        tokens.append("★")

    seen = set()
    unique_tokens = []
    for t in sorted(tokens, key=len, reverse=True):
        if t.lower() not in seen:
            seen.add(t.lower())
            unique_tokens.append(t)
    return unique_tokens


def highlight_keywords(text: str, keywords: list[str]) -> tuple[str, list[str]]:
    """在文本中安全高亮关键词（包裹 <mark>...</mark>），合并重叠区间避免嵌套，返回 (高亮内容, 实际命中的关键词列表)。"""
    if not text:
        return "", []
    if not keywords:
        return html.escape(text), []

    spans: list[tuple[int, int, str]] = []
    matched_set = set()
    for kw in sorted(set(keywords), key=len, reverse=True):
        if not kw:
            continue
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        for m in pattern.finditer(text):
            spans.append((m.start(), m.end(), kw))
            matched_set.add(kw)

    if not spans:
        return html.escape(text), []

    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    merged: list[tuple[int, int]] = []
    for s_start, s_end, _ in spans:
        if not merged:
            merged.append((s_start, s_end))
        else:
            prev_start, prev_end = merged[-1]
            if s_start < prev_end:
                if s_end > prev_end:
                    merged[-1] = (prev_start, s_end)
            else:
                merged.append((s_start, s_end))

    pieces = []
    last_idx = 0
    for m_start, m_end in merged:
        if m_start > last_idx:
            pieces.append(html.escape(text[last_idx:m_start]))
        pieces.append("<mark>")
        pieces.append(html.escape(text[m_start:m_end]))
        pieces.append("</mark>")
        last_idx = m_end
    if last_idx < len(text):
        pieces.append(html.escape(text[last_idx:]))

    return "".join(pieces), sorted(matched_set, key=len, reverse=True)


def compute_relevance(
    text: str,
    clause_number: str,
    clause_type: str,
    importance: str,
    keywords: list[str],
    raw_query: str,
) -> tuple[float, list[str]]:
    """计算切片与查询词的相关度得分与命中关键词。"""
    matched_kws = []
    score = 0.0
    text_lower = text.lower()
    raw_query_clean = re.sub(r"[\s,，;；、?？!！]+", "", raw_query.lower())

    # 1. 原始短语精确命中
    phrase_matched = False
    if len(raw_query_clean) >= 2 and raw_query_clean in text_lower:
        score += 15.0
        phrase_matched = True

    # 2. 词元匹配
    for kw in keywords:
        kw_l = kw.lower()
        if kw_l in text_lower:
            matched_kws.append(kw)
            score += len(kw) * 2.5
        if kw_l in clause_number.lower():
            score += 5.0
            matched_kws.append(kw)

    # 若既无短语命中亦无关键词命中，相关度得分为 0
    if not phrase_matched and not matched_kws:
        return 0.0, []

    # 3. 条款类型匹配
    if any(kw.lower() in clause_type for kw in keywords):
        score += 4.0

    # 4. 重要性加权
    if importance == "star":
        score += 3.0
    elif importance == "disqualification":
        score += 2.0
    elif importance == "scoring":
        score += 2.0

    return score, sorted(set(matched_kws), key=len, reverse=True)


@dataclass
class TenderSlice:
    slice_id: str
    file_id: str
    filename: str
    page: int
    clause_number: str
    clause_type: str        # "disqualification" | "scoring" | "business" | "technical" | "general"
    clause_type_label: str  # "废标条款" | "评分标准" | "商务要求" | "技术要求" | "通用条款"
    importance: str         # "star" | "disqualification" | "scoring" | "normal"
    score_weight: float | None
    content: str
    highlighted_content: str
    matched_keywords: list[str]
    relevance_score: float
    source_fingerprint: str
    requirement_id: str | None = None
    can_insert: bool = False
    action: str = "inject_context"

    def to_dict(self) -> dict[str, Any]:
        return {
            "slice_id": self.slice_id,
            "file_id": self.file_id,
            "filename": self.filename,
            "page": self.page,
            "clause_number": self.clause_number,
            "clause_type": self.clause_type,
            "clause_type_label": self.clause_type_label,
            "importance": self.importance,
            "score_weight": self.score_weight,
            "content": self.content,
            "highlighted_content": self.highlighted_content,
            "matched_keywords": self.matched_keywords,
            "relevance_score": round(self.relevance_score, 2),
            "source_fingerprint": self.source_fingerprint,
            "requirement_id": self.requirement_id,
            "can_insert": self.can_insert,
            "action": self.action,
        }


@dataclass
class TenderSearchResult:
    project_id: str
    query: str
    enabled: bool
    total_slices_indexed: int
    total_matched: int
    slices: list[TenderSlice]
    notice: str | None = None
    answer_card: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "query": self.query,
            "enabled": self.enabled,
            "total_slices_indexed": self.total_slices_indexed,
            "total_matched": self.total_matched,
            "slices": [s.to_dict() for s in self.slices],
            "notice": self.notice,
            "answer_card": self.answer_card,
        }


class TenderRetrievalService:
    """负责本项目招标文件切片轻量索引检索与结构化证据展示。"""

    def __init__(self, demo_service: Any):
        self.demo = demo_service
        self.repository = getattr(demo_service, "repository", None)

    def get_feature_switch(self, project_id: str) -> bool:
        """获取本项目招标文件轻量索引检索特性开关（PRD E08 默认关闭可选）。"""
        state: DemoState = self.repository.read()
        workflow = state.workflows.get(project_id, {})
        return bool(workflow.get("tender_indexing_enabled", False))

    def set_feature_switch(self, principal: Principal, project_id: str, enabled: bool) -> bool:
        """设置本项目招标文件轻量索引检索开关。需项目成员写权限。"""
        def operation(state: DemoState):
            project = state.projects.get(project_id)
            if project is None or project.company_id != principal.user.company_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
            require_same_company(state, principal, project_id)
            from .project_access import writable
            if not writable(state, project_id, principal.user.id):
                raise DomainError(403, "FORBIDDEN", "只读成员无权更改项目索引检索配置。")
            workflow = state.workflows.setdefault(project_id, {})
            workflow["tender_indexing_enabled"] = bool(enabled)
            return bool(enabled)

        return self.repository.transaction(operation)

    def index_project_tender_documents(self, workflow: dict[str, Any], project_id: str) -> list[TenderSlice]:
        """
        基于当前 project_id 已上传并解析的招标文件（workflow['files']）以及条款抽取结果（workflow['requirements']），
        构建轻量切片索引。严格限定在当前 project 范围。
        """
        slices: list[TenderSlice] = []
        parsed_files = [f for f in workflow.get("files", {}).values() if f.get("status") == "parsed"]
        requirements = list(workflow.get("requirements", {}).values())

        seq = 1

        if parsed_files:
            for f in parsed_files:
                file_id = f.get("id", "file-unknown")
                filename = f.get("filename", "招标文件")
                pages = f.get("pages", [])
                for page_idx, page_text in enumerate(pages, start=1):
                    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
                    for ln in lines:
                        if ln.startswith(("合成招标文件", "招标文件：", "招标文件:")):
                            continue
                        clause_num = extract_clause_number(ln) or f"第{page_idx}页·第{seq}条"
                        c_type, c_label = classify_clause_type(ln)
                        importance = detect_importance(ln, c_type)
                        score_wt = extract_score_weight(ln)

                        matched_req_id = None
                        for req in requirements:
                            if req.get("source", {}).get("file_id") == file_id and req.get("source", {}).get("page") == page_idx:
                                if req.get("source", {}).get("quote") in ln or ln in req.get("text", ""):
                                    matched_req_id = req.get("id")
                                    break

                        fp_src = f"{project_id}:{file_id}:{page_idx}:{clause_num}:{ln[:48]}"
                        fp = hashlib.sha256(fp_src.encode("utf-8")).hexdigest()[:16]

                        slices.append(TenderSlice(
                            slice_id=f"{file_id}_p{page_idx}_s{seq}",
                            file_id=file_id,
                            filename=filename,
                            page=page_idx,
                            clause_number=clause_num,
                            clause_type=c_type,
                            clause_type_label=c_label,
                            importance=importance,
                            score_weight=score_wt,
                            content=ln,
                            highlighted_content=html.escape(ln),
                            matched_keywords=[],
                            relevance_score=0.0,
                            source_fingerprint=fp,
                            requirement_id=matched_req_id,
                            can_insert=False,
                            action="inject_context",
                        ))
                        seq += 1

        # 若未解析 files 或 files 为空，但有 requirements/facts，从 requirements 构建切片兜底
        if not slices and requirements:
            for req in requirements:
                src = req.get("source", {})
                file_id = src.get("file_id", "req-file")
                page = src.get("page", 1)
                text = req.get("text", "")
                clause_num = extract_clause_number(text) or f"条款 {req.get('id', seq)}"
                c_type, c_label = classify_clause_type(text)
                importance = detect_importance(text, c_type)
                score_wt = extract_score_weight(text)

                fp_src = f"{project_id}:{file_id}:{page}:{clause_num}:{text[:48]}"
                fp = hashlib.sha256(fp_src.encode("utf-8")).hexdigest()[:16]

                slices.append(TenderSlice(
                    slice_id=f"slice_{req.get('id', seq)}",
                    file_id=file_id,
                    filename=src.get("filename", "招标文件"),
                    page=page,
                    clause_number=clause_num,
                    clause_type=c_type,
                    clause_type_label=c_label,
                    importance=importance,
                    score_weight=score_wt,
                    content=text,
                    highlighted_content=html.escape(text),
                    matched_keywords=[],
                    relevance_score=0.0,
                    source_fingerprint=fp,
                    requirement_id=req.get("id"),
                    can_insert=False,
                    action="inject_context",
                ))
                seq += 1

        return slices

    def search(
        self,
        principal: Principal,
        project_id: str,
        query: str,
        *,
        enabled: bool | None = None,
        top_k: int = 10,
        clause_type: str | None = None,
    ) -> TenderSearchResult:
        """
        检索当前项目的招标文件切片。
        1. 严格限定范围：只允许检索当前用户所属公司的当前项目；禁止跨项目/跨公司越权；
        2. 校验权限：项目内成员（包括只读成员可查阅，不可写入）；
        3. 开关控制：若 enabled 为 False（或未指定且项目开关未开启），返回关闭提示与空结果；
        4. 命中切片打分与高亮，组装结构化证据卡。
        """
        state: DemoState = self.repository.read()
        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

        # 检查项目成员身份
        team_members = state.project_teams.get(project_id, {}).get("members", {})
        if principal.user.id not in team_members:
            norm_role = normalize_role(principal.user.role)
            if norm_role != "company_admin":
                raise DomainError(403, "FORBIDDEN", "您不是本项目成员，无权检索本项目招标文件。")

        # 开关判断 (E08 规范：一期可选默认关闭)
        workflow = state.workflows.get(project_id, {})
        is_enabled = enabled if enabled is not None else bool(workflow.get("tender_indexing_enabled", False))

        if not is_enabled:
            notice = "本项目招标文件轻量索引检索功能已关闭（默认关闭可选），启用后可按关键词检索招标文件原文切片与条款"
            empty_card = self.build_answer_card(
                TenderSearchResult(
                    project_id=project_id,
                    query=query,
                    enabled=False,
                    total_slices_indexed=0,
                    total_matched=0,
                    slices=[],
                    notice=notice,
                )
            )
            return TenderSearchResult(
                project_id=project_id,
                query=query,
                enabled=False,
                total_slices_indexed=0,
                total_matched=0,
                slices=[],
                notice=notice,
                answer_card=empty_card,
            )

        # 构建切片索引
        raw_slices = self.index_project_tender_documents(workflow, project_id)
        tokens = tokenize_query(query)

        scored_slices: list[TenderSlice] = []
        for s in raw_slices:
            if clause_type and s.clause_type != clause_type:
                continue
            score, matched_kws = compute_relevance(
                s.content, s.clause_number, s.clause_type, s.importance, tokens, query
            )
            if score > 0:
                highlighted, _ = highlight_keywords(s.content, matched_kws or tokens)
                scored_slices.append(TenderSlice(
                    slice_id=s.slice_id,
                    file_id=s.file_id,
                    filename=s.filename,
                    page=s.page,
                    clause_number=s.clause_number,
                    clause_type=s.clause_type,
                    clause_type_label=s.clause_type_label,
                    importance=s.importance,
                    score_weight=s.score_weight,
                    content=s.content,
                    highlighted_content=highlighted,
                    matched_keywords=matched_kws,
                    relevance_score=score,
                    source_fingerprint=s.source_fingerprint,
                    requirement_id=s.requirement_id,
                    can_insert=False,
                    action="inject_context",
                ))

        # 按相关度从高到低排序，相同得分按页码升序
        scored_slices.sort(key=lambda x: (x.relevance_score, -x.page), reverse=True)
        top_slices = scored_slices[:top_k]

        notice = f"已检索本项目招标文件切片，共检索到 {len(scored_slices)} 条匹配条款"
        result = TenderSearchResult(
            project_id=project_id,
            query=query,
            enabled=True,
            total_slices_indexed=len(raw_slices),
            total_matched=len(scored_slices),
            slices=top_slices,
            notice=notice,
        )
        result.answer_card = self.build_answer_card(result)
        return result

    def build_answer_card(self, result: TenderSearchResult) -> dict[str, Any]:
        """按 PRD 5.11.15 标准装配招标文件证据卡。本项目数据类一律 can_insert=False。"""
        records = [s.to_dict() for s in result.slices]
        return {
            "title": f"招标文件检索 · {result.query}" if result.query else "招标文件切片检索",
            "direct_query_domain": "tender_slice",
            "direct_query_intent": "招标文件检索",
            "direct_query_intent_version": 1,
            "query_route": "direct_query",
            "kb_enabled": True,
            "library_query_skipped": False,
            "source": "本项目招标文件",
            "source_type": "tender_document",
            "notice": result.notice,
            "records": records,
            "total_count": result.total_matched,
            "can_insert": False,
            "insert_disabled_reason": "本项目招标文件切片不提供直接插入正文，可一键注入章节Prompt上下文作为依据或以变量引用改写",
            "disclaimer": "系统直查 · 招标文件原文切片",
        }

    def inject_clauses_to_chapter(
        self,
        principal: Principal,
        project_id: str,
        chapter_id: str,
        slice_ids: list[str] | None = None,
        slices: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        一键将选定的招标文件切片/条款约束注入当前编辑章节的 Prompt 上下文。
        1. 严格检查章节归属与项目编辑权限；
        2. 拦截系统只读角色与项目只读成员（403 FORBIDDEN）；
        3. 注入条款以不可篡改指纹固化至 workflow['injected_tender_clauses'][chapter_id]；
        4. 返回注入后的条款清单与上下文指纹。
        """
        def operation(state: DemoState):
            project = state.projects.get(project_id)
            if project is None or project.company_id != principal.user.company_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

            chapter = state.chapters.get(chapter_id)
            if chapter is None or chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")

            from .project_access import chapter_edit, lead
            can_edit = chapter_edit(state, chapter, principal.user.id) or lead(state, project_id, principal.user.id)
            if not can_edit:
                raise DomainError(403, "FORBIDDEN", "您无权为当前章节注入条款约束（需要编写人或项目负责人权限）。")

            workflow = state.workflows.setdefault(project_id, {})
            injected_map = workflow.setdefault("injected_tender_clauses", {})

            target_clauses: list[dict[str, Any]] = []
            if slices:
                for sl in slices:
                    target_clauses.append({
                        "slice_id": sl.get("slice_id"),
                        "clause_number": sl.get("clause_number", "条款"),
                        "clause_type": sl.get("clause_type", "general"),
                        "clause_type_label": sl.get("clause_type_label", "招标文件条款"),
                        "importance": sl.get("importance", "normal"),
                        "score_weight": sl.get("score_weight"),
                        "page": sl.get("page", 1),
                        "content": sl.get("content", ""),
                        "source_fingerprint": sl.get("source_fingerprint", ""),
                    })
            elif slice_ids:
                all_slices = {s.slice_id: s for s in self.index_project_tender_documents(workflow, project_id)}
                for sid in slice_ids:
                    if sid in all_slices:
                        s = all_slices[sid]
                        target_clauses.append({
                            "slice_id": s.slice_id,
                            "clause_number": s.clause_number,
                            "clause_type": s.clause_type,
                            "clause_type_label": s.clause_type_label,
                            "importance": s.importance,
                            "score_weight": s.score_weight,
                            "page": s.page,
                            "content": s.content,
                            "source_fingerprint": s.source_fingerprint,
                        })

            if not target_clauses:
                raise DomainError(422, "VALIDATION_ERROR", "请选择至少一条有效的招标文件条款进行注入。")

            existing = injected_map.get(chapter_id, [])
            existing_ids = {c["slice_id"] for c in existing if c.get("slice_id")}
            for tc in target_clauses:
                if tc["slice_id"] not in existing_ids:
                    existing.append(tc)
                    existing_ids.add(tc["slice_id"])

            injected_map[chapter_id] = existing

            from .editor_ai_context import build_editor_prompt_context
            prompt_ctx = build_editor_prompt_context(
                state=state,
                project_id=project_id,
                chapter_id=chapter_id,
                query="注入条款更新",
            )

            return {
                "chapter_id": chapter_id,
                "project_id": project_id,
                "injected_count": len(existing),
                "injected_clauses": existing,
                "context_fingerprint": prompt_ctx["context_fingerprint"],
                "message": f"成功为章节《{chapter.title}》注入 {len(target_clauses)} 条招标文件条款约束",
            }

        return self.repository.transaction(operation)

    def get_injected_clauses(self, principal: Principal, project_id: str, chapter_id: str) -> list[dict[str, Any]]:
        state: DemoState = self.repository.read()
        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
        chapter = state.chapters.get(chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")
        workflow = state.workflows.get(project_id, {})
        return workflow.get("injected_tender_clauses", {}).get(chapter_id, [])

    def clear_injected_clauses(self, principal: Principal, project_id: str, chapter_id: str) -> bool:
        def operation(state: DemoState):
            project = state.projects.get(project_id)
            if project is None or project.company_id != principal.user.company_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
            chapter = state.chapters.get(chapter_id)
            if chapter is None or chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")
            from .project_access import chapter_edit, lead
            if not (chapter_edit(state, chapter, principal.user.id) or lead(state, project_id, principal.user.id)):
                raise DomainError(403, "FORBIDDEN", "只读成员无权清除注入条款。")
            workflow = state.workflows.setdefault(project_id, {})
            injected_map = workflow.setdefault("injected_tender_clauses", {})
            injected_map[chapter_id] = []
            return True
        return self.repository.transaction(operation)
