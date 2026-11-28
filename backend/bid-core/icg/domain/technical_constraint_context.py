# 为什么有这个文件：技术节提示按废标级别组装短上下文。
# 它解决什么问题：信用中国、失信、资格和装订否决不进每节项目硬约束。

from __future__ import annotations

from dataclasses import dataclass

from icg.domain.technical_clause_extract import _matter_key, _same
from icg.domain.technical_clause_role import classify_constraint, is_bid_packaging, is_section_constraint_row

# 风险提示只留开头，长截图的后半段不进本节提示。
_TIP_CLIP = 160
_TIP_CAP = 8
_PROJECT_CAP = 8
_NON_TECH_MARKERS = (
    "信用中国",
    "资格",
    "资质",
    "商务",
    "价格",
    "保证金",
    "营业执照",
    "黑名单",
    "包装",
)


@dataclass(frozen=True)
class ConstraintContext:
    """L0 技术硬约束、L1 本章硬约束、L0 非技术风险提示。"""

    project: tuple[str, ...]
    section: tuple[str, ...]
    tips: tuple[str, ...]


def text_is_non_tech(text: str) -> bool:
    blob = str(text or "")
    if not blob:
        return False
    if is_bid_packaging(blob):
        return True
    return any(marker in blob for marker in _NON_TECH_MARKERS)


# 商务/报价/格式包装类条款硬标记：命中即商务卷条款，硬拦截不得进技术目录树与技术偏离表。
# 注意保持保守：服务期/质保期/SLA/运维 是技术条款，词表不得误伤。
_BUSINESS_MARKERS = (
    "投标报价",
    "报价一览表",
    "基准价",
    "币种",
    "人民币",
    "投标文件格式",
    "装订",
    "盖章",
    "密封",
    "签字或盖章",
    "付款方式",
    "付款条件",
    "发票",
    "税率",
    "商务业绩",
    "投标保证金",
    "保证金",
    "联合体投标",
    "联合体",
    "转包",
    "分包",
    "投标文件份数",
    "正本",
    "副本",
    "报名材料",
    "报名条件",
    "资格条件",
    "投标有效期",
    "开标一览",
    "报价得分",
    "价格分",
    # 招标人义务 / 程序格式 / 文件制作递交：不属于技术方案正文。
    "投标文件制作",
    "书写或打印",
    "不褪色",
    "涂改",
    "行间插字",
    "按时递交",
    "逾期送达",
    "送达指定地点",
    "递交时间和地点",
    "出席开标",
    "开标会议",
    "开标程序",
    "成交结果",
    "结果公示",
    "采购公告",
    "评标办法",
    "前附表审核",
    "电子文件",
    "纸质文件",
    "书面文件与电子文件",
    "最不利原则",
    "投标文件内容",
    "投标文件原件",
    # ISSUE-060：限价/付款/账户/清算破产与资格程序——纯商务与资格条款，不属于技术方案。
    # 注意保持保守限定（付款方式/支付比例等复合词），裸词「付款/支付/清算」会误伤
    # 支付接口、数据清算等真实技术条款。
    "最高限价",
    "限价",
    "付款期限",
    "付款比例",
    "支付比例",
    "预付款",
    "进度款",
    "基本账户",
    "进入清算",
    "清算或破产",
    "破产清算",
    "宣告破产",
    "资格审查",
)

# 投标/响应文件本身的做法要求（格式、编写、装订、签署、密封、修改、份数……）是形式条款；
# 单个词太宽（「修改」「格式」可能出现在技术条款里），必须和「投标文件/响应文件」同时命中才拦。
_BID_DOC_WORDS = ("投标文件", "响应文件", "投标函")
_BID_DOC_FORMAT_WORDS = (
    "格式", "编写", "编制", "装订", "签署", "签字", "盖章", "密封", "修改", "澄清",
    "份数", "正本", "副本", "打印", "书写", "涂改", "递交", "送达", "组成",
)


def is_bid_document_format(text: str) -> bool:
    """「投标文件应按第六章格式编写」「投标文件修改需书面通知」这类形式条款。"""
    blob = str(text or "")
    if not blob:
        return False
    if not any(word in blob for word in _BID_DOC_WORDS):
        return False
    return any(word in blob for word in _BID_DOC_FORMAT_WORDS)


def is_business_clause_text(text: str) -> bool:
    blob = str(text or "")
    if not blob:
        return False
    if any(marker in blob for marker in _BUSINESS_MARKERS):
        return True
    return is_bid_document_format(blob)


def is_business_clause(item: dict) -> bool:
    """商务卷条款判定：报价/币种/格式/装订/付款类。技术 SLA 与运维条款不得命中。"""
    blob = f"{item.get('text') or ''} {item.get('extracted_summary') or ''} {item.get('score_item') or ''}"
    return is_business_clause_text(blob)


def row_is_non_tech(item: dict) -> bool:
    if item.get("requirement_type") == "qualification":
        return True
    if is_business_clause(item):
        return True
    blob = f"{item.get('text') or ''} {item.get('extracted_summary') or ''}"
    return text_is_non_tech(blob)


def build_constraint_context(
    rows: list[dict],
    workflow: dict | None,
    task: dict | None = None,
) -> ConstraintContext:
    """组装本节提示用的三条清单。只注入 tech_hard；非技术进提示；说不清的不进正文。"""
    section: list[str] = []
    tips: list[str] = []
    seen: list[str] = []
    tipped: list[str] = []
    for item in rows or []:
        text = _shown(item)
        if not text:
            continue
        classified = classify_constraint(text, item)
        if classified["kind"] == "non_tech_risk":
            _add_tip(tips, tipped, text)
            continue
        if (
            classified["kind"] == "tech_hard"
            and classified["level"] in ("L0", "L1")
            and is_section_constraint_row(item)
            and _keep_matter(text, seen)
        ):
            section.append(text)
    candidates: list[str] = []
    for raw in _sidecar_lines(workflow):
        text = str(raw or "").strip()
        if not text:
            continue
        classified = classify_constraint(text)
        if classified["kind"] == "non_tech_risk":
            _add_tip(tips, tipped, text)
            continue
        if classified["kind"] != "tech_hard" or classified["level"] not in ("L0", "L1"):
            continue
        if not _keep_matter(text, seen):
            continue
        candidates.append(text)
    project = _choose_project(candidates, _linked_texts(task, workflow))
    return ConstraintContext(tuple(project), tuple(section), tuple(tips))


def _shown(item: dict) -> str:
    return str(item.get("extracted_summary") or item.get("text") or "").strip()


def _sidecar_lines(workflow: dict | None) -> list:
    return ((workflow or {}).get("technical_sidecars") or {}).get("rejection_lines") or []


def _keep_matter(text: str, seen: list[str]) -> bool:
    key = _matter_key(text)
    if key and any(_same(key, item) for item in seen):
        return False
    if key:
        seen.append(key)
    return True


def _clip_tip(text: str) -> str:
    if len(text) <= _TIP_CLIP:
        return text
    return text[:_TIP_CLIP]


def _add_tip(tips: list[str], seen: list[str], text: str) -> None:
    if not _keep_matter(text, seen):
        return
    if len(tips) >= _TIP_CAP:
        return
    tips.append(_clip_tip(text))


def _linked_texts(task: dict | None, workflow: dict | None) -> list[str]:
    if not task:
        return []
    ids = [
        *(task.get("rejection_requirement_ids") or []),
        *(task.get("constraint_ids") or []),
    ]
    if not ids:
        return []
    requirements = (workflow or {}).get("requirements") or {}
    if not isinstance(requirements, dict):
        return []
    texts: list[str] = []
    for rid in ids:
        row = requirements.get(rid)
        if not isinstance(row, dict) or row_is_non_tech(row):
            continue
        text = _shown(row)
        if text:
            texts.append(text)
    return texts


def _overlaps(line: str, linked: list[str]) -> bool:
    key = _matter_key(line)
    if not key:
        return False
    return any(_same(key, _matter_key(text)) for text in linked)


def _choose_project(candidates: list[str], linked: list[str]) -> list[str]:
    # 挂载原文对得上才收窄；对不上时仍用短全局列表，避免措辞不一致把技术废标整段拿掉。
    if linked:
        matched = [line for line in candidates if _overlaps(line, linked)]
        if matched:
            return matched[:_PROJECT_CAP]
    return candidates[:_PROJECT_CAP]
