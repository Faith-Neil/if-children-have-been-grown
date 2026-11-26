# 为什么有这个文件：导出内部用“响应追溯表”Excel（PRD v1.8 §5.9.1 规则 12，APP-M2-T201）。
# 它解决什么问题：内部审核时要一眼看出每条招标条款在哪个文件第几页、怎么响应、落在哪个分册哪一章哪一段、
# 引了哪些证据（版本）与知识片段、谁负责、谁确认。只供内部审核，不进入投标文件，任何时候都可导出。
# 分册负责人只导出本册；项目负责人导出全部。

from __future__ import annotations

import re
from typing import Any

from .scope_rules import BREAK, normalize
from .export_sanitizer import normalize_markdown_noise

VOLUME_NAMES = {"technical": "技术分册", "business": "商务分册"}
CATEGORY_NAMES = {"mandatory": "实质性条款", "qualification": "资格要求", "technical": "技术服务", "business": "商务要求",
                  "commercial": "商务要求", "sla": "SLA 要求", "star": "星号条款", "disqualification": "废标条款",
                  "scoring": "评分要点", "score": "评分要点", "other": "其他要求"}
STATUS_NAMES = {"confirmed": "已确认", "pending": "待确认", "rejected": "已忽略"}
_CITATION = re.compile(r"\[(证|片)(?::([^\]]+))?\]")


def _grams(text: str) -> set[str]:
    value = normalize(text).replace(BREAK, "")
    return {value[i:i + 2] for i in range(len(value) - 1)}


def best_paragraph(content: str, query: str) -> tuple[int | None, str]:
    """按字面重合找条款在本章最可能对应的段落（1 起）；重合太低返回 None（交 R30 判定）。"""
    want = _grams(query)
    best, best_score, best_text = None, 0.0, ""
    for index, paragraph in enumerate((content or "").split("\n")):
        text = paragraph.strip()
        if not text or text.startswith("#"):
            continue
        own = _grams(text)
        if not own or not want:
            continue
        score = len(own & want) / min(len(own), len(want))
        if score > best_score:
            best, best_score, best_text = index + 1, score, text
    return (best, best_text) if best_score >= 0.2 else (None, "")


def requirement_heading_map(workflow: dict) -> dict[str, dict]:
    """招标条款 → 技术目录叶子节。响应追溯表必须落到 1～12 节，而不是全填唯一章对象。"""
    outline = workflow.get("technical_outline") or {}
    mapping: dict[str, dict] = {}
    for heading in outline.get("headings") or []:
        if not (heading.get("task_id") or heading.get("requirement_id")):
            continue
        rids = list(heading.get("requirement_ids") or [])
        if not rids and heading.get("requirement_id"):
            rids = [heading.get("requirement_id")]
        for rid in rids:
            if rid and rid not in mapping:
                mapping[str(rid)] = heading
    return mapping


def audit_for_requirement(workflow: dict, requirement_id: str, heading: dict | None) -> dict:
    """按条款/任务找生成期实际检索审计；不能把其他节的命中来源贴到每一行。"""
    rid = str(requirement_id or "")
    task_id = str((heading or {}).get("task_id") or "")
    for entry in workflow.get("technical_rag_audit") or []:
        if task_id and str(entry.get("task_id") or "") == task_id:
            return entry
        if rid and rid in [str(x) for x in (entry.get("requirement_ids") or [])]:
            return entry
    return {}


def build_trace_rows(state: Any, project: Any, workflow: dict, volumes: set[str]) -> list[list[object]]:
    files = workflow.get("files") or {}
    chapters = {c.id: c for c in state.chapters.values() if c.project_id == project.id}
    order = {cid: i + 1 for i, cid in enumerate(workflow.get("chapter_order") or [])}
    heading_by_requirement = requirement_heading_map(workflow)
    owners = (state.project_teams.get(project.id) or {}).get("owners", {})
    names = {aid: a.name for aid, a in state.accounts.items()}
    rows: list[list[object]] = []
    requirements = sorted((workflow.get("requirements") or {}).values(),
                          key=lambda r: (r.get("volume", ""), (r.get("source") or {}).get("page") or 0))
    from icg.domain.technical_constraint_context import row_is_non_tech
    eligible = (
        r for r in requirements
        if r.get("volume") in volumes and r.get("status") != "rejected" and not row_is_non_tech(r)
    )
    for number, req in enumerate(eligible, start=1):
        source = req.get("source") or {}
        file = files.get(source.get("file_id")) or {}
        chapter = chapters.get(req.get("chapter_id"))
        heading = heading_by_requirement.get(str(req.get("id") or "")) or {}
        chapter_content = chapter.content if chapter else ""
        scoped_content = chapter_content
        if heading and chapter_content:
            from icg.domain.technical_volume import section_body
            scoped_content = section_body(
                chapter_content,
                str(heading.get("number") or ""),
                str(heading.get("title") or ""),
            ) or chapter_content
        paragraph, text = best_paragraph(scoped_content, f"{req.get('text', '')}{req.get('response', '')}")
        evidence = []
        for eid in req.get("evidence_ids") or []:
            item = state.library.get(eid) or {}
            evidence.append(f"{item.get('name', eid)}（v{item.get('revision', '?')}）")
        snippets = sorted({ref for kind, ref in _CITATION.findall(text) if kind == "片" and ref})
        cited = sorted({ref for kind, ref in _CITATION.findall(text) if kind == "证" and ref})
        owner_id = (chapter.assignee_id if chapter and chapter.assignee_id else owners.get(req.get("volume")))
        owner_name = names.get(owner_id, owner_id or "")
        if "合成" in owner_name:
            owner_name = ""
        # 响应列与偏离表同一套“单条条款→小节/句子”精准提炼，避免章首句批量复制。
        if chapter_content and heading:
            from icg.domain.technical_volume import _content_response
            response_text = _content_response(chapter_content, heading, req)
        elif text:
            first = re.split(r"[。；;\n]", normalize_markdown_noise(text.strip()))[0].strip()
            response_text = ("我司" + first if first and not first.startswith(("我", "本")) else first)[:160]
        else:
            response_text = "待生成后回填"
        # 知识片段来源：正文引用优先；缺失时从生成期检索审计按章节回填真实知识文档名
        knowledge = "、".join(snippets)
        if not knowledge:
            audit_refs: list[str] = []
            entry = audit_for_requirement(workflow, str(req.get("id") or ""), heading)
            for hit in (entry.get("top") or [])[:6]:
                # 历史标书只作为内部知识来源，文件名常含其他业主/厂商；追溯表展示已脱敏类别。
                # 本标切片是检索输入不是知识来源；materials/history 为 0 的节不得凭空填产品名。
                kind = str((hit or {}).get("dataset_kind") or "")
                if kind == "tender":
                    continue
                if kind == "materials" and not int(entry.get("material_hits") or 0):
                    continue
                if kind == "history" and not int(entry.get("history_hits") or 0):
                    continue
                name = "历史标书参考（已脱敏）" if kind == "history" else str((hit or {}).get("name") or "").strip()
                if name and name not in audit_refs:
                    audit_refs.append(name)
            knowledge = "、".join(audit_refs[:4])
        row_values = [
            number,
            str(req.get("text", "")),
            file.get("filename") or "招标文件",
            source.get("page") or "",
            CATEGORY_NAMES.get(req.get("category"), req.get("category") or ""),
            response_text,
            VOLUME_NAMES.get(req.get("volume"), req.get("volume") or ""),
            (f"{heading.get('number', '')} {heading.get('title', '')}".strip() if heading else (f"{order.get(chapter.id, '')} {chapter.title}".strip() if chapter else "未对应章节")),
            paragraph or "",
            "；".join(evidence) + (f"；正文引用 [证] {', '.join(cited)}" if cited else ""),
            knowledge,
            owner_name,
            req.get("confirmed_by_name") or "",
            STATUS_NAMES.get(req.get("status"), req.get("status") or ""),
        ]
        foreign = list(workflow.get("foreign_entity_names") or [])
        if foreign:
            from icg.domain.writing_knowledge_prompt import mask_foreign_names
            row_values = [mask_foreign_names(str(v), foreign) if isinstance(v, str) else v for v in row_values]
        rows.append(row_values)
    return rows


HEADER = ["序号", "招标条款", "所属文件", "页码", "条款类别", "响应方式与要点", "所在分册", "对应章节", "段落",
          "证据（版本）", "知识片段来源", "负责人", "确认人", "条款状态"]


def trace_sheets(project: Any, rows: list[list[object]], *, scope: str, generated_at: str) -> list[dict]:
    head = [
        [f"响应追溯表（内部用，不进入投标文件）· {project.name}"],
        [f"范围：{scope} · 生成：{generated_at} · 共 {len(rows)} 条"],
        [],
        HEADER,
    ]
    return [{"name": "响应追溯表", "rows": head + rows, "header_rows": 4,
             "widths": [6, 48, 18, 6, 12, 40, 10, 22, 6, 28, 18, 12, 12, 10]}]
