# 为什么有这个文件：实现 PRD v1.8 §5.2.4 抽取后处理第④步“星号/废标兜底扫描”与“疑似遗漏”逐条处理（APP-M2-T111）。
# 它解决什么问题：
# 1. 用关键词和正则全量扫描解析文本，不依赖模型；命中块已被星号/废标条目覆盖记“已覆盖”，否则记“疑似遗漏”；
# 2. 项目负责人逐条“新增为条目”或“排除”（排除须写理由），不提供批量接口；
# 3. 疑似遗漏未处理完不能确认解析结果；重新解析或补遗重跑时已处理的结果保持不变；
# 4. 扫描结果记录所用词表版本，处理全程写审计。

from __future__ import annotations

import re
from .domain import DemoState, DomainError, Principal, iso_time, new_id
from .project_access import require_lead

# 平台初始兜底扫描词表（PRD v1.8 §5.2.4 第④步示例）。公司词表维护页（APP-M2-T148）未交付前统一使用本版本。
PLATFORM_SCAN_VERSION = "platform-2026.10-1"
PLATFORM_SCAN_TERMS: tuple[str, ...] = (
    "★", "实质性要求", "实质性条款", "不允许偏离", "不得偏离", "否决投标", "否决其投标",
    "无效投标", "投标无效", "废标", "不予受理",
)
_LEADING_STAR = re.compile(r"^\s*[\*＊]")


def scan_text_lines(pages: list[str], terms: tuple[str, ...] = PLATFORM_SCAN_TERMS) -> list[dict]:
    hits = []
    for page_no, text in enumerate(pages, start=1):
        for raw in (text or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            matched = [t for t in terms if t in line]
            if _LEADING_STAR.match(line):
                matched.insert(0, "条款开头的“*”")
            if matched:
                hits.append({"page": page_no, "quote": line, "terms": matched})
    return hits


def _is_critical(requirement: dict) -> bool:
    """与合规检查、定稿门禁同一口径判断星号/废标条目，避免两处判断不一致。"""
    from .check_orchestrator import CheckOrchestratorMixin

    return (CheckOrchestratorMixin._is_critical_requirement(requirement)
            or str(requirement.get("importance", "")).lower() in ("star", "disqualification"))


def hit_covered(workflow: dict, hit: dict) -> str | None:
    """命中块被未忽略的星号/废标条目覆盖时返回该条目 ID。"""
    for requirement in workflow.get("requirements", {}).values():
        # 被并入主条目、被补遗替代的条目仍代表原文这一处已抽取（不删除），所在块算已覆盖
        handled = requirement.get("merged_into") or requirement.get("effective_status") == "superseded"
        if (requirement.get("status") == "rejected" and not handled) or not _is_critical(requirement):
            continue
        source = requirement.get("source") or {}
        same_block = source.get("file_id") == hit["file_id"] and source.get("page") == hit["page"]
        text = requirement.get("text") or ""
        quote = source.get("quote") or ""
        if (same_block and (hit["quote"] in quote or quote in hit["quote"])) or hit["quote"] in text:
            return requirement["id"]
    return None


def store(workflow: dict) -> dict:
    data = workflow.setdefault("post_process", {})
    data.setdefault("scan_version", PLATFORM_SCAN_VERSION)
    data.setdefault("hits", {})
    return data


def run_scan(workflow: dict, file_id: str, pages: list[str], now_iso: str) -> None:
    """解析完成后执行兜底扫描；已处理的命中保持不变（§5.2.4 规则 4）。"""
    data = store(workflow)
    data["scan_version"] = PLATFORM_SCAN_VERSION
    known = {(h["file_id"], h["page"], h["quote"]) for h in data["hits"].values()}
    for hit in scan_text_lines(pages):
        key = (file_id, hit["page"], hit["quote"])
        if key in known:
            continue
        identity = new_id("scan")
        data["hits"][identity] = {"id": identity, "file_id": file_id, **hit, "status": "open", "reason": "",
                                  "requirement_id": None, "scan_version": PLATFORM_SCAN_VERSION,
                                  "created_at": now_iso, "handled_by": None, "handled_at": None}
        known.add(key)


def public_hit(workflow: dict, hit: dict) -> dict:
    result = dict(hit)
    if hit["status"] == "open":
        covered = hit_covered(workflow, hit)
        result["state"] = "covered" if covered else "suspected"
        result["covered_by"] = covered
    else:
        result["state"] = hit["status"]
        result["covered_by"] = hit.get("requirement_id")
    return result


def suspected(workflow: dict) -> list[dict]:
    return [h for h in (public_hit(workflow, h) for h in workflow.get("post_process", {}).get("hits", {}).values())
            if h["state"] == "suspected"]


class OmissionMixin:
    """WorkflowService 的疑似遗漏处理能力。"""

    def list_scan_hits(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        data = workflow.get("post_process", {"hits": {}, "scan_version": PLATFORM_SCAN_VERSION})
        hits = [public_hit(workflow, h) for h in data.get("hits", {}).values()]
        files = workflow.get("files", {})
        for hit in hits:
            hit["filename"] = files.get(hit["file_id"], {}).get("filename", "")
        hits.sort(key=lambda h: ({"suspected": 0, "covered": 1}.get(h["state"], 2), h["filename"], h["page"]))
        count = lambda name: len([h for h in hits if h["state"] == name])  # noqa: E731
        return {"revision": project.revision, "project_id": project_id,
                "scan_version": data.get("scan_version", PLATFORM_SCAN_VERSION),
                "summary": {"total": len(hits), "suspected": count("suspected"), "covered": count("covered"),
                            "added": count("added"), "excluded": count("excluded"),
                            "too_many": len(hits) > 30},
                "can_handle": self._is_lead(state, principal, project_id),
                "hits": hits}

    def _is_lead(self, state: DemoState, principal: Principal, project_id: str) -> bool:
        try:
            require_lead(state, principal, project_id)
            return True
        except DomainError:
            return False

    def _open_hit(self, state: DemoState, principal: Principal, project_id: str, workflow: dict, hit_id: str) -> dict:
        require_lead(state, principal, project_id)
        hit = store(workflow)["hits"].get(hit_id)
        if hit is None:
            raise DomainError(404, "NOT_FOUND", "未找到本项目的扫描命中。")
        if hit["status"] != "open":
            raise DomainError(409, "VERSION_CONFLICT", "该命中已处理，请刷新后查看。", {"status": hit["status"]})
        return hit

    def add_scan_hit(self, principal: Principal, project_id: str, hit_id: str, payload: dict,
                     expected: str | None, key: str | None) -> dict:
        category = payload.get("category")
        if category not in ("star", "disqualification"):
            raise DomainError(422, "VALIDATION_ERROR", "请选择条目类别（星号 / 废标）。", {"fields": {"category": "invalid"}})
        volume = payload.get("volume") or "technical"
        if volume not in ("technical", "business"):
            raise DomainError(422, "VALIDATION_ERROR", "分册取值无效。", {"fields": {"volume": "invalid"}})

        def operation(state: DemoState, project, workflow):
            hit = self._open_hit(state, principal, project_id, workflow, hit_id)
            from icg.domain.project_access import require_project_volume
            require_project_volume(state, project_id, volume)
            text = str(payload.get("text") or hit["quote"]).strip()
            if not text:
                raise DomainError(422, "EMPTY_REQUIREMENT", "条款原文不能为空。")
            fields = {"category": "disqualification" if category == "disqualification" else "mandatory",
                      "importance": category, "status": "pending", "reason": "", "volume": volume, "text": text,
                      "added_from_scan": hit_id}
            existing = next((r for r in workflow["requirements"].values()
                             if (r.get("source") or {}).get("file_id") == hit["file_id"]
                             and (r.get("source") or {}).get("page") == hit["page"]
                             and (r.get("source") or {}).get("quote") == hit["quote"]), None)
            if existing is not None:
                existing.update(fields)
                requirement = existing
            else:
                requirement = {"id": new_id("req"), "chapter_id": None, "response": "", "evidence_ids": [],
                               "source": {"file_id": hit["file_id"], "page": hit["page"], "quote": hit["quote"]},
                               "references": [], "reference_status": "none", **fields}
                workflow["requirements"][requirement["id"]] = requirement
            now = iso_time(self.demo._now())
            hit.update(status="added", requirement_id=requirement["id"], handled_by=principal.user.id, handled_at=now)
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"hit": public_hit(workflow, hit), "requirement": requirement}

        return self._write(principal, project_id, f"parse.omission.add:{hit_id}", payload, expected, key, operation,
                           {"hit_id": hit_id, "category": category})

    def exclude_scan_hit(self, principal: Principal, project_id: str, hit_id: str, payload: dict,
                         expected: str | None, key: str | None) -> dict:
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise DomainError(422, "REASON_REQUIRED", "排除疑似遗漏必须填写理由。")

        def operation(state: DemoState, project, workflow):
            hit = self._open_hit(state, principal, project_id, workflow, hit_id)
            hit.update(status="excluded", reason=reason, handled_by=principal.user.id,
                       handled_at=iso_time(self.demo._now()))
            return {"hit": public_hit(workflow, hit)}

        return self._write(principal, project_id, f"parse.omission.exclude:{hit_id}", payload, expected, key,
                           operation, {"hit_id": hit_id, "reason": reason})


def require_no_omissions(workflow: dict) -> None:
    pending = suspected(workflow)
    if pending:
        raise DomainError(409, "OMISSIONS_PENDING",
                          f"兜底扫描还有 {len(pending)} 条疑似遗漏未处理，请逐条新增为条目或写明理由排除。",
                          {"pending": len(pending)})
