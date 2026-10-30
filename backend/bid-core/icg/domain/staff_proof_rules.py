# 为什么有这个文件：R33 拟派人员条件与 R38 证明材料与评分要点对应（PRD v1.8 §5.8.1、§5.1.4 第 4 项“拟派人员”；
# 字典 v1.9 R33、R38 输入、project_person；APP-M2-T241、T253）。
# 它解决什么问题：
# 1. 从招标条款里抽出结构化人员条件：角色、人数、学历、专业、工作年限、证书、AB 角、不得兼任（规则抽取，结果写在检查明细里可核对）；
# 2. 拟派人员：项目负责人从资料库“人员”类资料里选人、定角色、A/B 角与是否关键人员，保存在项目工作流里；
# 3. R33 逐项核对：资格要求不满足阻断，评分要求不满足提示，其他条款不满足警告；没排人或人员资料缺学历/专业/参加工作时间/证书时警告
#    （“资料缺失”），工作年限算到投标截止时间；
# 4. R38：评分项要求截图或证明的，拆出功能点，每个功能点至少一份挂接附件的功能点标签（或资料名称、正文）能找到该功能点或其同义词，
#    同义词取公司设置 custom_settings.r38_synonyms；附件文字识别与截图内容理解尚未接入（PRD 截图理解为二期），明细里写明。
# 人员资料目前是资料库的文字正文：按“学历：…”“专业：…”“参加工作：YYYY-MM”“证书：…”逐行读取，读不到的项算资料缺失，不猜。

from __future__ import annotations

import re
from datetime import date
from typing import Any

from .content_rules import _issue, _result, _rows
from .domain import DomainError, Principal, iso_time, new_id

ROLES = ("项目经理", "项目负责人", "技术负责人", "驻场工程师", "运维工程师", "实施工程师", "数据库工程师", "DBA", "安全工程师",
         "网络工程师", "系统工程师", "开发工程师", "测试工程师", "售后工程师", "服务经理")
ROLE_ALIAS = {"项目负责人": "项目经理", "DBA": "数据库工程师"}
TEAM = "团队成员"
DEGREES = {"大专": 1, "专科": 1, "本科": 2, "大学本科": 2, "学士": 2, "硕士": 3, "研究生": 3, "博士": 4}
CERTS = ("PMP", "信息系统项目管理师", "系统集成项目管理工程师", "系统规划与管理师", "系统架构设计师", "网络规划设计师",
         "信息安全工程师", "网络工程师", "数据库系统工程师", "CISP", "CISSP", "ITIL", "OCP", "OCM", "RHCE", "CCIE", "HCIE", "HCIP",
         "高级工程师", "中级工程师", "一级建造师", "二级建造师")
_PERSON_WORDS = re.compile(r"人员|经理|负责人|工程师|团队|成员|DBA")
_DEGREE = re.compile(r"(博士|硕士|研究生|大学本科|本科|学士|大专|专科)")
_MAJOR = re.compile(r"(?:^|[，,。；;：:\s（(]|学历|具有|具备|为|毕业于|所学)([\u4e00-\u9fa5A-Za-z、/或和及]{2,24}?)(?:等)?(?:相关)?专业")
_YEARS = re.compile(r"(\d{1,2})\s*年(?:及)?以上[^，。；\n]{0,10}?(?:工作|从业|管理|运维|相关|项目)?经验|(?:工作|从业)年限(?:不少于|不低于|≥|在)?\s*(\d{1,2})\s*年")
_COUNT = re.compile(r"(?:不少于|不低于|至少|≥)\s*(\d{1,2})\s*(?:名|人|位)|(\d{1,2})\s*(?:名|人)(?:及以上|以上)")
_CERT = re.compile(r"(?:具有|具备|持有|取得)(?:有效的?)?([A-Za-z\u4e00-\u9fa5（）()]{2,24}?)(?:证书|资格证|认证|证)")
_AB = re.compile(r"A\s*[/、]?\s*B\s*角|AB\s*角|A角.{0,4}B角")
_EXCLUSIVE = re.compile(r"不得兼任|不能兼任|专职")
_PROOF = re.compile(r"截图|证明|证明材料|佐证|演示|证书|检测报告|测试报告")
_FEATURES = re.compile(r"(?:支持|具备|具有|包括|包含|实现|提供)([^，。；;\n]{2,80}?)(?:等)?(?:功能|能力|模块|特性)")
_SPLIT = re.compile(r"[、，,；;/和及与或]+")


# ---------------------------------------------------------------- 招标人员条件

def _norm_role(role: str) -> str:
    return ROLE_ALIAS.get(role, role)


def conditions(text: str) -> dict | None:
    """一条招标条款里的结构化人员条件；条款与人员无关时返回 None。"""
    text = str(text or "")
    if not _PERSON_WORDS.search(text):
        return None
    role = next((r for r in ROLES if r in text), None)
    degree = _DEGREE.search(text)
    majors = []
    for match in _MAJOR.finditer(text):
        majors += [m for m in (w.strip() for w in _SPLIT.split(match.group(1))) if len(m) >= 2 and m not in ("相关", "以上")]
    years = next((int(g) for m in _YEARS.finditer(text) for g in m.groups() if g), None)
    count = next((int(g) for m in _COUNT.finditer(text) for g in m.groups() if g), None)
    certs = [c for c in CERTS if c in text]
    for match in _CERT.finditer(text):
        name = match.group(1).strip("（）()")
        if len(name) >= 2 and not any(name in c or c in name for c in certs) and not _DEGREE.search(name):
            certs.append(name)
    spots = sorted(text.find(c) for c in certs if c in text)
    any_cert = len(spots) > 1 and "或" in text[spots[0]:spots[-1]]  # “PMP 或信息系统项目管理师”：持其一即可
    found = {"role": _norm_role(role) if role else TEAM, "count": count,
             "degree": degree.group(1) if degree else None, "majors": majors, "years": years, "certificates": certs,
             "certificates_any": any_cert,
             "ab_role": bool(_AB.search(text)), "exclusive": bool(_EXCLUSIVE.search(text))}
    if role is None and not any((found["degree"], majors, years, certs)):
        return None
    if not any((count, found["degree"], majors, years, certs, found["ab_role"], found["exclusive"])):
        return None
    return found


# ---------------------------------------------------------------- 人员资料

def _line(content: str, *labels: str) -> str | None:
    for label in labels:
        match = re.search(label + r"\s*[：:]\s*([^\n]+)", content)
        if match:
            return match.group(1).strip()
    return None


def profile(item: dict) -> dict:
    """资料库人员资料 → 学历、专业、参加工作时间（或工作年限）、证书；读不到的项为 None。"""
    content = f"{item.get('content') or ''}"
    degree_line = _line(content, "学历", "最高学历", "学位")
    degree = _DEGREE.search(degree_line or "")
    start = None
    raw = _line(content, "参加工作时间", "参加工作", "工作起始时间", "从业起始时间", "开始工作时间")
    if raw:
        match = re.search(r"(\d{4})\s*[-./年]\s*(\d{1,2})", raw)
        if match:
            start = date(int(match.group(1)), min(12, max(1, int(match.group(2)))), 1)
    years_line = _line(content, "工作年限", "从业年限")
    years = int(re.search(r"\d+", years_line).group(0)) if years_line and re.search(r"\d+", years_line) else None
    cert_line = _line(content, "证书", "资格证书", "认证", "职称")
    certs = None
    if cert_line is not None:
        certs = [c.strip() for c in re.split(r"[、，,；;]", cert_line) if c.strip()]
    elif any(c in content for c in CERTS):
        certs = [c for c in CERTS if c in content]
    return {"degree": degree.group(1) if degree else None, "major": _line(content, "专业", "所学专业"),
            "work_start": start.isoformat() if start else None, "years": years, "certificates": certs}


def _years_at(person: dict, deadline: str | None) -> float | None:
    if person["work_start"]:
        until = date.fromisoformat(deadline[:10]) if deadline else date.today()
        return round((until - date.fromisoformat(person["work_start"])).days / 365.25, 1)
    return float(person["years"]) if person["years"] is not None else None


# ---------------------------------------------------------------- 拟派人员

def staff_list(workflow: dict) -> list[dict]:
    return list(workflow.get("proposed_staff") or [])


def public_staff(state: Any, project: Any, workflow: dict) -> dict:
    rows = []
    for entry in staff_list(workflow):
        item = state.library.get(entry["person_id"]) or {}
        rows.append({**entry, "person_name": item.get("name", "资料已删除"),
                     "profile": profile(item) if item else None})
    return {"staff": rows, "roles": list(ROLES)}


def validate_staff(state: Any, project: Any, entries: list[dict]) -> list[dict]:
    cleaned, seen = [], set()
    for entry in entries:
        person = state.library.get(entry["person_id"])
        if person is None or person.get("company_id") != project.company_id or person.get("type") != "personnel":
            raise DomainError(422, "VALIDATION_ERROR", "拟派人员必须从本公司资料库的“人员”资料中选择。", {"person_id": entry["person_id"]})
        if person.get("status") == "rejected":
            raise DomainError(422, "VALIDATION_ERROR", f"{person['name']} 的资料已被驳回，不能拟派。")
        role = _norm_role(entry["role"].strip())
        key = (entry["person_id"], role)
        if key in seen:
            raise DomainError(422, "VALIDATION_ERROR", f"{person['name']} 已拟派为{role}，不要重复添加。")
        seen.add(key)
        cleaned.append({"id": entry.get("id") or new_id("staff"), "person_id": entry["person_id"], "role": role,
                        "position": entry.get("position") or None, "is_key_person": bool(entry.get("is_key_person"))})
    return cleaned


class ProposedStaffMixin:
    """挂在 WorkflowService 上：读取与保存拟派人员（保存仅项目负责人；动作名 staff.update）。"""

    def proposed_staff(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        result = public_staff(state, project, workflow)
        result["r33"] = check_r33(state, project, workflow).to_dict()
        return result

    def save_proposed_staff(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        def operation(state, project, workflow):
            workflow["proposed_staff"] = validate_staff(state, project, payload["staff"])
            workflow["proposed_staff_updated"] = {"by": principal.user.id, "at": iso_time(self.demo._now())}
            result = public_staff(state, project, workflow)
            result["r33"] = check_r33(state, project, workflow).to_dict()  # 排人时即提示（PRD §5.8.4）
            return result
        return self._write(principal, project_id, "staff.update", payload, expected, key, operation)


# ---------------------------------------------------------------- R33

def _severity(row: dict) -> str:
    kind, category = row.get("section_kind"), row.get("category")
    if kind == "qualification" or category in ("qualification", "mandatory") or "★" in str(row.get("text")):
        return "blocker"
    if kind == "scoring" or category == "scoring":
        return "info"
    return "warning"


def check_r33(state: Any, project: Any, workflow: dict, volume: str = "all"):
    title = "拟派人员条件"
    staff = staff_list(workflow)
    people = {e["person_id"]: profile(state.library.get(e["person_id"]) or {}) for e in staff}
    names = {e["person_id"]: (state.library.get(e["person_id"]) or {}).get("name", "资料已删除") for e in staff}
    issues, checked = [], []
    for row in _rows(workflow, volume):
        need = conditions(row.get("text"))
        if need is None:
            continue
        checked.append({"requirement_id": row["id"], "conditions": need})
        level = _severity(row)
        assigned = [e for e in staff if need["role"] == TEAM or e["role"] == need["role"]]
        quote = str(row.get("text"))[:40]

        def unmet(code: str, message: str, **details):
            issues.append(_issue("R33", code, level, message, requirement_id=row["id"], details=details))

        def missing(message: str, **details):
            issues.append(_issue("R33", "STAFF_DATA_MISSING", "warning", message, requirement_id=row["id"], details=details))

        if not assigned:
            missing(f"尚未拟派{need['role']}，无法核对：{quote}", role=need["role"])
            continue
        if need["count"] and len({e["person_id"] for e in assigned}) < need["count"]:
            unmet("STAFF_COUNT_SHORT", f"{need['role']}要求不少于 {need['count']} 人，现拟派 {len(assigned)} 人：{quote}",
                  role=need["role"], required=need["count"], assigned=len(assigned))
        if need["ab_role"] and not {"A", "B"} <= {e.get("position") for e in assigned}:
            unmet("STAFF_AB_ROLE_MISSING", f"{need['role']}须设 A、B 角，现未同时指定 A 角和 B 角：{quote}", role=need["role"])
        for entry in assigned:
            person, who = people[entry["person_id"]], names[entry["person_id"]]
            if need["exclusive"]:
                others = sorted({e["role"] for e in staff if e["person_id"] == entry["person_id"] and e["role"] != entry["role"]})
                if others:
                    unmet("STAFF_DUAL_ROLE", f"{who}拟任{entry['role']}，招标要求不得兼任，但同时拟任{'、'.join(others)}",
                          person_id=entry["person_id"], roles=[entry["role"], *others])
            if need["degree"]:
                if person["degree"] is None:
                    missing(f"{who}的人员资料没有学历，无法核对“{need['degree']}”要求", person_id=entry["person_id"])
                elif DEGREES.get(person["degree"], 0) < DEGREES.get(need["degree"], 0):
                    unmet("STAFF_DEGREE_UNMET", f"{who}学历为{person['degree']}，低于要求的{need['degree']}",
                          person_id=entry["person_id"])
            if need["majors"]:
                if not person["major"]:
                    missing(f"{who}的人员资料没有专业，无法核对专业要求", person_id=entry["person_id"])
                elif not any(m in person["major"] or person["major"] in m for m in need["majors"]):
                    unmet("STAFF_MAJOR_UNMET", f"{who}专业为{person['major']}，不在要求的{'、'.join(need['majors'])}之列",
                          person_id=entry["person_id"])
            if need["years"]:
                years = _years_at(person, project.deadline)
                if years is None:
                    missing(f"{who}的人员资料没有参加工作时间或工作年限，无法核对 {need['years']} 年经验要求",
                            person_id=entry["person_id"])
                elif years < need["years"]:
                    unmet("STAFF_YEARS_UNMET", f"{who}工作年限算到投标截止时间约 {years:g} 年，不足要求的 {need['years']} 年",
                          person_id=entry["person_id"], years=years)
            if need["certificates"]:
                if person["certificates"] is None:
                    missing(f"{who}的人员资料没有证书信息，无法核对证书要求", person_id=entry["person_id"])
                else:
                    lacking = [c for c in need["certificates"]
                               if not any(c in own or own in c for own in person["certificates"])]
                    if need.get("certificates_any") and len(lacking) < len(need["certificates"]):
                        lacking = []
                    if lacking:
                        unmet("STAFF_CERT_MISSING", f"{who}缺少要求的证书：{('或' if need.get('certificates_any') else '、').join(lacking)}",
                              person_id=entry["person_id"], certificates=lacking)
    return _result("R33", title, issues,
                   ok="拟派人员满足招标的结构化人员条件。" if checked else "招标条款里没有可结构化核对的人员条件。",
                   fail="{n} 项拟派人员条件须处理。", suggestion="到项目设置“拟派人员”调整人选，或到资料库补全人员学历、专业、参加工作时间与证书。",
                   details={"conditions": checked, "staff": len(staff),
                            "not_checked": "人员证书有效期与学历证明附件未逐项核对；条件为规则抽取，请对照条款核对"})


# ---------------------------------------------------------------- R38

def features(text: str) -> list[str]:
    found = []
    for match in _FEATURES.finditer(str(text or "")):
        for part in _SPLIT.split(match.group(1)):
            word = re.sub(r"^(系统|平台|软件|具备|支持|的)+|等$", "", part.strip())
            if len(word) >= 2 and word not in found:
                found.append(word)
    return found


def _synonyms(state: Any, company_id: str) -> dict[str, list[str]]:
    stored = ((getattr(state, "service_stores", {}) or {}).get("company_settings") or {}).get(company_id) or {}
    raw = (stored.get("custom_settings") or {}).get("r38_synonyms") or {}
    return {str(k): [str(v) for v in (vals if isinstance(vals, list) else [vals])] for k, vals in raw.items()} if isinstance(raw, dict) else {}


def check_r38(state: Any, project: Any, workflow: dict, volume: str = "all"):
    from .attachments import for_library
    synonyms = _synonyms(state, project.company_id)
    issues, checked = [], []
    for row in _rows(workflow, volume):
        text = str(row.get("text") or "")
        scoring = row.get("category") == "scoring" or row.get("section_kind") == "scoring"
        if not scoring or not _PROOF.search(text):
            continue
        points = features(text)
        evidence = [state.library[e] for e in row.get("evidence_ids") or [] if e in state.library]
        attachments = [a for item in evidence for a in for_library(state, project.company_id, item["id"])]
        checked.append({"requirement_id": row["id"], "features": points, "attachments": len(attachments)})
        if not attachments:
            issues.append(_issue("R38", "PROOF_ATTACHMENT_MISSING", "warning",
                                 f"评分项要求截图或证明，挂接的资料还没有附件扫描件：{text[:40]}", requirement_id=row["id"]))
            continue
        haystack = " ".join([*(t for a in attachments for t in a.get("feature_tags") or []),
                             *(f"{i.get('name', '')} {i.get('content', '')}" for i in evidence)])
        for point in points:
            words = [point, *synonyms.get(point, [])]
            if not any(w and w in haystack for w in words):
                issues.append(_issue("R38", "FEATURE_PROOF_MISSING", "warning",
                                     f"功能点“{point}”没有找到对应的证明附件（附件功能点标签与资料内容里都没有该词或同义词）",
                                     requirement_id=row["id"], details={"feature": point}))
    return _result("R38", "证明材料与评分要点对应", issues,
                   ok="要求截图或证明的评分项，每个功能点都有对应附件。" if checked else "评分项里没有要求截图或证明的条款。",
                   fail="{n} 个功能点或评分项缺少对应证明附件。", suggestion="到资料库为附件补功能点标签，或挂接对应的截图与证明。",
                   details={"checked": checked, "synonyms": len(synonyms),
                            "not_checked": "附件文字识别与截图图像内容尚未核对（截图理解为二期）"})
