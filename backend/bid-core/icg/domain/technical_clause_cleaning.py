# 为什么有这个文件：招标条款清洗分流——物理残句补全/丢弃与技术/非技术范围分流（ISSUE-060 / TV-M0-T31）。
# 它解决什么问题：真实招标（重庆中烟 161 条）混入残句碎片与商务/资格/格式条款，
# 进入技术目录挂载与偏离判定后产生大批假「负偏离」阻断导出。清洗结果落盘可审：
# requirement_scope ∈ technical / non_technical / fragment_filtered，
# 残句优先用 quote/所在页原文补全，无法构成有效独立要求的残句被过滤但保留审计样本。

from __future__ import annotations

import re
from typing import Any

from icg.domain.technical_constraint_context import row_is_non_tech
from icg.domain.technical_clause_extract import SERVICE

SCOPE_TECHNICAL = "technical"
SCOPE_NON_TECHNICAL = "non_technical"
SCOPE_FRAGMENT = "fragment_filtered"
EXCLUDED_SCOPES = frozenset({SCOPE_NON_TECHNICAL, SCOPE_FRAGMENT})

# ---------------------------------------------------------------- 非技术条款分流规则
# 商务/资格/保证金/限价/付款/投标格式/装订签署密封修改类。命中即非技术，不进技术目录、
# 偏离表与负偏离判定。保持保守：服务期/质保/SLA/运维属技术条款，规则不得误伤。
_NON_TECH_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"最高限价|限价不得|低于成本价|投标报价|报价一览|报价不得|合同总金额|年度服务费|服务费为|支付方式"), "pricing"),
    (re.compile(r"基本账户|基本存款账户|账户证明|开户许可证|银行资信"), "qualification"),
    (re.compile(r"(?:投标人|供应商|服务商|承包商).{0,16}(?:清算|破产|重整)|(?:进入|处于|被宣告|申请).{0,4}(?:清算|破产|重整)|失信被执行|信用中国|经营异常|黑名单"), "qualification"),
    (re.compile(r"资格审查|资格条件|资质要求|营业执照|社保缴纳|纳税证明|审计报告|财务报告"), "qualification"),
    (re.compile(r"保证金|履约担保|履约金"), "deposit"),
    (re.compile(r"付款方式|付款条件|支付比例|预付款|进度款|发票开具|税率"), "payment"),
    (re.compile(r"投标文件.{0,15}(格式|装订|密封|签署|签字|盖章|份数|编制要求|修改|撤回|澄清)"), "format"),
    (re.compile(r"按第[一二三四五六七八九十\d]+章.{0,6}格式|格式编写|装订成册|密封提交|密封递交"), "format"),
    (re.compile(r"正本.{0,6}副本|电子版.{0,6}纸质|书面形式.{0,8}通知|修改.{0,6}书面通知"), "format"),
    (re.compile(r"投标有效期|开标时间|开标地点|投标截止|递交方式|送达方式"), "procedure"),
    # 资格/合规门槛：不是技术方案要展开响应的服务能力，进非技术查阅区。
    (re.compile(r"独立法人资格|独立承担民事责任|(?:投标人|供应商|服务商).{0,10}(?:专业技术能力|专业资质|从业资格)"), "qualification"),
    (re.compile(r"利害关系|控股关系|重大质量或安全事故|重大违法违规|违法、?违纪|不良纪录|不良记录"), "qualification"),
    (re.compile(r"烟草行业不良行为名单|责令停业|招标代理|相关咨询方|标底编制|取消投标资格|暂停投标资格"), "qualification"),
    # 投标程序与文件组成/备选方案：属于投标形式约束，不进入技术方案目录。
    (re.compile(r"备选技术方案|备选方案|实质性内容响应|投标文件需包含|投标文件须包含"), "format"),
    (re.compile(r"产品质量安全指标检测报告|第三方质量检测机构检测|标的物出现质量问题"), "business_or_packaging"),
    (re.compile(r"签署本合同|甲方的权利义务|乙方的权利义务"), "business_or_packaging"),
    (re.compile(r"不得挂靠|挂靠其他单位|受让或租用"), "business_or_packaging"),
]

# 技术义务/SLA 语境。它们出现在混合句中时，不能因「合同履行过程中」等合同模板前缀
# 或单个行业词把真实技术能力要求整体误分流；混合句宁可留给技术侧人工响应，也不静默丢弃。
_TECHNICAL_OBLIGATION = re.compile(
    r"SLA|响应时间|响应速度|\d+(?:\.\d+)?\s*(?:小时|分钟|天|日|周|月)|到场|恢复服务|故障|巡检|"
    r"备份|容灾|接口|数据库|中间件|系统性能|可用性|运维|实施|迁移|割接|监控|告警|安全加固|验收测试"
)


# 「系统实施前 / 项目验收前 / 合同履行期间」只是时间背景，不是独立技术义务；
# 先剥离这类状语再识别技术词，避免资格证明被「实施/验收」单字撤销分流。
_TEMPORAL_CONTEXT = re.compile(
    r"(?:[一-鿿]{0,8}?(?:系统|项目|合同|工程|服务|运维))?"
    r"(?:实施|验收|履行|交付|建设|运行)(?:前|期间|过程中|阶段|后期)"
)


def _has_technical_obligation(text: str) -> bool:
    blob = _TEMPORAL_CONTEXT.sub("", str(text or ""))
    return bool(_TECHNICAL_OBLIGATION.search(blob))


# ---------------------------------------------------------------- 残句结构信号
_LEADING_BROKEN = re.compile(r"^[)）\]】〉》」』，,、;；:：|]+")
_TRAILING_DANGLING = re.compile(r"[:：,，、;；(（【\[]\s*$")
# 以孤立的否定/连词/介词收尾，语义必然未完（如「……，不」「……未经许可不」「……，提」）。
_TRAILING_INCOMPLETE_WORD = re.compile(r"(?:不|未|和|及|或|且|并|所|按|向|由|对|将|被|使|提)\s*$")
_ORDINAL_HEADING = re.compile(r"^第[0-9一二三四五六七八九十百千]+[条章节篇][、\s]*\S{0,14}$")
_CHINESE_SECTION_HEADING = re.compile(r"^[一二三四五六七八九十]+[、.．]\s*\S{1,14}$")
_GENERIC_HEADINGS = frozenset({"运维服务范围", "运维服务要求"})
_TABLE_NOISE = re.compile(r"^[\s|★\-—–_.…·]*$|^\|")
_MOSTLY_PUNCT = re.compile(r"[\u4e00-\u9fff]")
_ACTION_WORD = re.compile(
    r"提供|执行|完成|响应|支持|服务|保障|实施|提交|满足|不得|应当|应|须|需|进行|出具|编写|"
    r"配备|部署|培训|巡检|维保|达到|符合|包含|覆盖|采用|具备|建立|制定|承诺"
)
_SENTENCE_END = re.compile(r"[。；;！!？?]")
# 标题序号判定用的强动作动词：不含「服务/应/需」这类弱词，否则「第一条 服务内容与范围」会被误当成有效要求。
_STRONG_ACTION = re.compile(
    r"提供|执行|完成|响应|支持|保障|实施|提交|满足|不得|应当|须|进行|出具|编写|"
    r"配备|部署|培训|巡检|维保|达到|符合|包含|覆盖|采用|具备|建立|制定|承诺"
)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text or ""))


def _balanced(text: str) -> bool:
    blob = str(text or "")
    return blob.count("（") == blob.count("）") and blob.count("(") == blob.count(")")


def fragment_signals(text: str) -> list[str]:
    """返回残句结构信号列表；空列表表示这是一条结构完整的要求。"""
    blob = str(text or "").strip()
    signals: list[str] = []
    if not blob:
        return ["empty"]
    compact = _compact(blob)
    if len(compact) <= 1:
        signals.append("too_short")
    if _LEADING_BROKEN.match(blob):
        signals.append("leading_broken_punct")
    if _TRAILING_DANGLING.search(blob):
        signals.append("trailing_dangling_punct")
    if _TRAILING_INCOMPLETE_WORD.search(blob):
        signals.append("trailing_incomplete_word")
    if re.match(r"^(?:或|且|以及|并|和)\S{2,10}$", compact) and _ACTION_WORD.search(blob):
        signals.append("continuation_orphan")
    if not _balanced(blob):
        signals.append("unbalanced_brackets")
    if _ORDINAL_HEADING.match(blob) and not _STRONG_ACTION.search(re.sub(r"^第\S+[条章节篇]\s*", "", blob)):
        signals.append("ordinal_heading")
    if (_CHINESE_SECTION_HEADING.match(blob) or blob in _GENERIC_HEADINGS) and not _STRONG_ACTION.search(blob):
        signals.append("section_heading")
    if blob.lstrip().startswith("|"):
        signals.append("table_noise")
    if not _MOSTLY_PUNCT.search(blob):
        signals.append("no_cjk_content")
    if len(compact) <= 4 and not SERVICE.search(blob) and not _ACTION_WORD.search(blob):
        signals.append("short_no_action")
    return signals


def is_fragment_text(text: str) -> bool:
    return bool(fragment_signals(text))


_SENTENCE_BOUNDARY_CHARS = "。；;！!？?|()（）[]【】<>《》 \t\r\n0123456789.．-—–"


def _match_needle(fragment: str) -> str:
    """条款抽取残句开头的编号噪音不参与原文定位，避免锚点落到编号中间。"""
    needle = _compact(fragment)
    needle = re.sub(r"^[（(]\s*\d+\s*[）)]", "", needle)
    needle = re.sub(r"^\d+(?:\.\d+)*[、.．]?", "", needle)
    return needle.strip("()（）,，、;；:：|\\")


def source_truncation_signals(fragment: str, page_text: str) -> list[str]:
    """用所在页原文判断“缺头少尾”：抽取摘要若是原文长句中段，前后紧邻仍是中文/英文
    字母而非句读、编号或表格边界，就说明它不是独立要求，而是被截断的物理残句。
    该信号只触发回溯补全；补不上时才按残句过滤，避免误丢合法的短名词型技术范围项。
    """
    needle = _match_needle(fragment)
    source = _compact(page_text)
    if len(needle) < 6 or not source:
        return []
    index = source.find(needle)
    if index < 0:
        return []
    before = source[index - 1] if index > 0 else ""
    after_index = index + len(needle)
    after = source[after_index] if after_index < len(source) else ""
    signals: list[str] = []
    if before and before not in _SENTENCE_BOUNDARY_CHARS and ("\u4e00" <= before <= "\u9fff" or before.isalpha()):
        signals.append("truncated_head")
    if after and after not in _SENTENCE_BOUNDARY_CHARS and ("\u4e00" <= after <= "\u9fff" or after.isalpha()):
        signals.append("truncated_tail")
    return signals


def non_tech_category(text: str) -> str:
    """命中非技术条款规则时返回类目；含明确技术义务/SLA 的混合句不被合同模板前缀误伤。"""
    blob = str(text or "")
    if not blob.strip():
        return ""
    for pattern, category in _NON_TECH_RULES:
        if pattern.search(blob):
            if _has_technical_obligation(blob) and category in {"qualification", "business_or_packaging"}:
                return ""
            return category
    if "合同履行过程中" in blob and not _has_technical_obligation(blob):
        return "business_or_packaging"
    return ""


def row_non_tech_category(row: dict) -> str:
    """行级非技术判定：先复用 row_is_non_tech 既有标记，再跑分流规则。"""
    blob = f"{row.get('text') or ''} {row.get('extracted_summary') or ''}"
    category = non_tech_category(blob)
    if category:
        return category
    if row_is_non_tech(row):
        return "business_or_packaging"
    return ""


def row_excluded_from_technical(row: dict) -> bool:
    """落盘后的硬过滤：非技术或残句过滤条款不得参与技术目录挂载、偏离表与负偏离判定。

    存量项目可能已有旧版 `clause_cleaned` 标记但缺 `requirement_scope`；因此这里消费
    与技术清单一致的行级生效判定，而不是只看新字段是否存在。
    """
    if str(row.get("requirement_scope") or "") in EXCLUDED_SCOPES:
        return True
    if row.get("clause_fragment"):
        return True
    return bool(row_non_tech_category(row))


# ---------------------------------------------------------------- 残句补全
def _sentence_spans(text: str) -> list[str]:
    """把页原文切成候选完整句/行，供残句回溯。"""
    spans: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        start = 0
        for match in _SENTENCE_END.finditer(line):
            piece = line[start:match.end()].strip()
            if piece:
                spans.append(piece)
            start = match.end()
        tail = line[start:].strip()
        if tail:
            spans.append(tail)
    return spans


def _number_tokens(text: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", str(text or ""))


def _number_preserved(number: str, text: str) -> bool:
    # 只有数字之间的点才是小数点；句末英文句号不得让 `TLS 1.2.` 误判缺数字。
    return bool(re.search(r"(?<!\d)(?<!\d\.)" + re.escape(number) + r"(?!\d|\.\d)", str(text or "")))


def _anchor_integrity(candidate: str, fragment: str) -> bool:
    """最终裁剪后的补全句仍要保留原始锚点与锚点内全部数值。

    允许“抽取丢失数字”的模糊补全（锚点本身没有该数字），但锚点里已经出现的
    `0.5`、`2` 等时限/数量一个都不能在编号裁剪中丢失。
    """
    needle = _match_needle(fragment)
    if not needle:
        return True
    compact = _compact(candidate)
    if needle not in compact:
        alpha = re.sub(r"[\d.]+", "", needle)
        if len(alpha) < 4 or alpha not in re.sub(r"[\d.]+", "", compact):
            return False
    return all(_number_preserved(number, compact) for number in _number_tokens(needle))


def _finalize_completion(candidate: str, fragment: str) -> str:
    cleaned = str(candidate or "").strip()
    if not _valid_completion(cleaned, fragment) or not _anchor_integrity(cleaned, fragment):
        return ""
    return cleaned


def _valid_completion(candidate: str, fragment: str) -> bool:
    blob = str(candidate or "").strip()
    if not blob or blob == str(fragment or "").strip():
        return False
    compact = _compact(blob)
    if len(compact) < 6 or len(blob) > 200:
        return False
    if len(compact) < len(_compact(fragment)) + 2 and not _SENTENCE_END.search(blob[-2:]):
        return False
    # 合同模板里的交叉引用/待填空白不是可响应的独立技术要求。
    if "见服务方案" in blob and not _STRONG_ACTION.search(re.sub(r"（[^）]*）|\([^)]*\)", "", blob)):
        return False
    if re.search(r"包括：[，,]?共计\s*个单位", blob):
        return False
    if not _balanced(blob):
        return False
    signals = fragment_signals(blob)
    hard = {"leading_broken_punct", "trailing_dangling_punct", "unbalanced_brackets", "table_noise"}
    sentence_closed = bool(_SENTENCE_END.search(blob[-2:]))
    return not any(
        signal in hard and not (signal == "trailing_dangling_punct" and sentence_closed)
        for signal in signals
    )


def _probes(needle: str) -> list[str]:
    """跨行锚定探针：完整针 + 首尾短针，覆盖碎句被换行截断的场景。"""
    probes = [needle]
    for size in (6, 4):
        if len(needle) > size:
            probes.extend([needle[:size], needle[-size:]])
    return [probe for probe in dict.fromkeys(probes) if len(probe) >= 2]


def _best_span(fragment: str, source_text: str, *, min_needle: int = 2) -> str:
    needle = _compact(fragment).strip("()（）,，、;；:：|")
    if len(needle) < min_needle:
        # 超短残句（如「三年」）只在全页唯一命中时可回溯：多句命中属于歧义，宁丢弃不编造。
        if len(needle) < 2:
            return ""
        hits = [span for span in _sentence_spans(source_text) if needle in _compact(span)]
        hits = [span for span in hits if _valid_completion(span, fragment)]
        if len(hits) != 1:
            return ""
        cleaned = _clean_completion_prefix(hits[0].strip()) or hits[0].strip()
        cleaned = _finalize_completion(cleaned, fragment)
        return "" if not cleaned or _compact(cleaned) == _compact(fragment) else cleaned
    best = ""
    spans = _sentence_spans(source_text)
    lines = str(source_text or "").splitlines()
    for span in spans:
        if needle in _compact(span) and _valid_completion(span, fragment):
            if not best or len(span) < len(best):
                best = span.strip()
    if best:
        cleaned = _clean_completion_prefix(best) or best
        cleaned = _finalize_completion(cleaned, fragment)
        return "" if not cleaned or _compact(cleaned) == _compact(fragment) else cleaned
    # 跨行拼接：残句常因换行/分页被截断（针本身可能跨行断开），
    # 按最小窗口扫描至多 4 行拼接，要求合并后包含完整针且通过完整性校验。
    # 序号标题（「第一条 服务内容与范围」类）本身就是完整一行，不是被截断的句子；
    # 跨行拼接只会把标题与下一条无关内容粘成拼接句——禁止（ISSUE-060）。
    if _ORDINAL_HEADING.match(str(fragment or "").strip()):
        return ""
    stripped = [line.strip() for line in lines if line.strip()]
    alpha = re.sub(r"[\d.]+", "", needle)
    fuzzy = len(needle) >= 6 and len(alpha) >= 4
    for width in range(1, 5):
        for start in range(0, len(stripped)):
            merged = "".join(stripped[start:start + width]).strip()
            if len(merged) > 200:
                continue
            compacted = _compact(merged)
            hit = needle in compacted
            if not hit and fuzzy:
                # 抽取丢失数字/小数点的残句：去数字后按字母针匹配（如 ¥5000元 ↔ ¥元）。
                hit = alpha in re.sub(r"[\d.]+", "", compacted)
            if hit and _valid_completion(merged, fragment):
                cleaned = _finalize_completion(_clean_completion_prefix(merged[:200]), fragment)
                if cleaned and _compact(cleaned) != _compact(fragment):
                    return cleaned
    return ""


_COMPLETION_PREFIX = re.compile(
    r"^\s*(?:\d+\s*\|\s*|\|\s*|（\s*[0-9一二三四五六七八九十]+\s*）\s*|"
    r"\(\s*\d+\s*\)\s*|\d+(?:\.\d+)+[、.．]?\s*|[0-9一二三四五六七八九十]+[、.．]\s*)+\s*[，,、]?\s*"
)


def _clean_completion_prefix(text: str) -> str:
    """补全句首的表格序号/列表编号（`3 |`、`（二）`）剥掉，不带进条款正文。"""
    return _COMPLETION_PREFIX.sub("", str(text or "").strip()).strip()


def _completion_by_anchor(fragment: str, source_text: str) -> str:
    """按紧凑原文位置补全：优先从残句前最近的条款编号/句读边界起，截取到下一个句末。
    该行式扫描跨不过 PDF 换行（如「维护培\\n训等。」），紧凑锚定可以；只引用原文，不编造。
    """
    needle = _match_needle(fragment)
    source = _compact(source_text)
    if len(needle) < 4 or not source:
        return ""
    candidates: list[str] = []
    start_search = 0
    while True:
        index = source.find(needle, start_search)
        if index < 0:
            break
        start_search = index + 1
        left_boundary = max(0, index - 140)
        prefix = source[left_boundary:index]
        start = left_boundary
        # 最近的条款编号（（6）/6.1/3、）比句读更精确，可避开「第六条 服务承诺」这类章名。
        markers = list(re.finditer(r"(?:（\s*\d+\s*）|\(\s*\d+\s*\)|\d+\.\d+(?:\.\d+)*|\d+[、.．])", prefix))
        if markers:
            start = left_boundary + markers[-1].start()
        else:
            sentence_starts = [left_boundary + match.end() for match in re.finditer(r"[。；;！!？?：:]", prefix)]
            if sentence_starts:
                start = sentence_starts[-1]
        # 编号/句读到残句之间若只是「运维服务范围」「对招标人的纪律要求」这类章名，
        # 从残句本身开始取，不把标题拼进条款正文。
        gap = re.sub(r"[\d.．、\s]+", "", source[start:index])
        if 0 < len(gap) <= 24 and not _STRONG_ACTION.search(gap):
            start = index
        tail_start = index + len(needle)
        # 残句在右括号前被截断时，右括号本身就是原句边界；继续扫到下一个句号会把
        # 下一条编号条款也吃进来，随后被编号清理误裁成无关句（如驻场值守残句误补成故障修复）。
        closing = None
        if str(fragment or "").count("（") > str(fragment or "").count("）"):
            closing = re.search(r"[）)]", source[tail_start:tail_start + 30])
        if closing:
            end = tail_start + closing.end()
        else:
            end_match = re.search(r"[。；;！!？?]", source[tail_start:])
            end = tail_start + end_match.end() if end_match else min(len(source), tail_start + 90)
        candidate = source[start:end]
        cleaned = _clean_completion_prefix(candidate).strip()
        actor = re.search(r"招标人不得|招标人应|投标人不得|投标人应|乙方|甲方|服务方|我方", cleaned)
        if actor and actor.start() > 0:
            prefix = cleaned[:actor.start()]
            # 只剥明确的章名/标题残渣；句首本来就是责任主体时绝不继续向后找「甲方」，
            # 否则会把「乙方须保证遵守」误裁掉并破坏锚点完整性。
            if len(prefix) <= 24 and re.search(r"第|条|章|服务承诺|服务范围|权利|义务|纪律要求", prefix):
                cleaned = cleaned[actor.start():].strip()
        # 条款编号剥离后仍可能带上一级章名（如「第六条乙方服务承诺6.4」），只裁
        # 句首附近、确实处在编号边界的条款号；`0.5小时` 这类正文小数绝不是编号。
        trailing_marker = list(re.finditer(r"\d+\.\d+(?:\.\d+)*", cleaned[:24]))
        clause_markers = []
        for marker in trailing_marker:
            token = marker.group(0)
            previous = cleaned[marker.start() - 1] if marker.start() else ""
            following = cleaned[marker.end():marker.end() + 2]
            numeric_quantity = token.startswith("0.") or previous in "后内约共达超少高低长宽深近仅" or following.startswith(("小时", "分钟", "天", "日", "月", "年", "%", "％"))
            prefix = cleaned[:marker.start()]
            heading_like = not _SENTENCE_END.search(prefix) and any("一" <= char <= "鿿" for char in prefix)
            if not numeric_quantity and marker.start() <= 16 and heading_like:
                clause_markers.append(marker)
        if clause_markers and clause_markers[-1].end() < len(cleaned):
            tail = cleaned[clause_markers[-1].end():].strip()
            if tail:
                cleaned = tail
        finalized = _finalize_completion(cleaned, fragment)
        if finalized and _compact(finalized) != _compact(fragment):
            candidates.append(finalized)
    if not candidates:
        return ""
    return sorted(candidates, key=lambda item: (not bool(_SENTENCE_END.search(item[-2:])), len(item)))[0]


def complete_fragment_text(fragment: str, quote: str, page_text: str) -> str:
    """残句补全：先用 quote 原文（同源行，锚定可靠），再回溯所在页原文（推测性更强，
    要求更长的锚针防止误拼）。取不到完整句返回空串，不编造。

    序号标题类残句（ordinal_heading，如「第一条 服务内容与范围」）的跨行拼接在
    _best_span 内被禁用：它本身就是完整的一行标题而不是被截断的句子，
    拼接下一行只会编出弗兰肯斯坦句——宁过滤不编造（ISSUE-060）。"""
    quote_completed = _best_span(fragment, str(quote or ""), min_needle=2)
    if quote_completed:
        return quote_completed
    anchored = _completion_by_anchor(fragment, str(page_text or ""))
    if anchored:
        return anchored
    needle = _match_needle(fragment)
    if needle and len(needle) >= 4 and needle in _compact(str(page_text or "")):
        # 原文命中但语义校验拒绝（交叉引用/合同空白等）时，不用模糊匹配拼无关句冒充补全。
        return ""
    return _best_span(fragment, str(page_text or ""), min_needle=4)


# ---------------------------------------------------------------- 行级清洗与审计
# 矩阵响应只可能来自系统检索拟写（公开接口不接受手写正文），这些来源的判断在被分流行上
# 属于「本来就不该存在」的假数据：合规检查（R09/R37 等）直接扫 deviation_type/响应文本，
# 不清理会把早已排除的商务/碎片条款继续当负偏离阻断导出（重庆中烟假负偏离根因之一）。
_SYSTEM_JUDGMENT_ORIGINS = frozenset({"history", "retrieval_failed", "draft_failed", "no_evidence", ""})


def clear_stale_judgment_fields(row: dict) -> bool:
    """行被技术分流排除后，就地清掉系统生成的矩阵判断（响应/偏离）；返回是否有改动。

    矩阵响应只可能来自系统检索拟写（公开接口不接受手写正文）。被分流行上的这类判断属于
    「本来就不该存在」的假数据：合规检查（R09/R37 等）直接扫 deviation_type/响应文本，
    不清理会把早已排除的商务/碎片条款继续当负偏离阻断导出（重庆中烟假负偏离根因之一）。
    只清系统来源（response_origin ∈ history/retrieval_failed/draft_failed/no_evidence 或空）；
    人工接管（已编辑/已确认）的行不动，由人工负责。
    """
    if not row_excluded_from_technical(row):
        return False
    if row.get("manually_edited") or row.get("status") == "confirmed":
        return False
    if not any(row.get(key) for key in ("response", "response_type", "deviation_type")):
        return False
    origin = str(row.get("response_origin") or "")
    if origin not in _SYSTEM_JUDGMENT_ORIGINS:
        return False
    row.update(response="", response_type=None, deviation_type=None, deviation_reason="",
               response_origin="", history_filename="", history_quote="")
    return True


def _page_text_for(workflow: dict, row: dict) -> str:
    source = row.get("source") or {}
    file_id = str(source.get("file_id") or "")
    if not file_id:
        return ""
    record = (workflow.get("files") or {}).get(file_id) or {}
    pages = record.get("pages") or []
    try:
        page = int(source.get("page") or row.get("page") or 0)
    except (TypeError, ValueError):
        page = 0
    if 1 <= page <= len(pages):
        # 抽取页锚在跨页/续表边界常漂移一页；补全只读原文，拼接相邻页比单页更稳。
        parts: list[str] = []
        for number in range(max(1, page - 1), min(len(pages), page + 1) + 1):
            entry = pages[number - 1]
            parts.append(entry if isinstance(entry, str) else str(entry.get("text") or ""))
        return "\n".join(part for part in parts if part)
    return "\n".join((page if isinstance(page, str) else str(page.get("text") or "")) for page in pages)


def _heading_has_inline_content(fragment: str, page_text: str) -> bool:
    """序号标题若与正文在同一行（第一条 服务内容与范围：提供……），允许行内补全；
    若标题独占一行，则不能用下一行拼出伪条款。"""
    needle = str(fragment or "").strip()
    if not needle:
        return False
    for line in str(page_text or "").splitlines():
        index = line.find(needle)
        if index < 0:
            continue
        raw_tail = line[index + len(needle):]
        if not raw_tail.lstrip().startswith(("：", ":")):
            continue
        tail = raw_tail.strip(" ：:，,、")
        if len(_compact(tail)) >= 4 and _ACTION_WORD.search(tail):
            return True
    return False


_SCORING_POINT_HARD_SIGNALS = frozenset({
    "empty", "leading_broken_punct", "trailing_dangling_punct", "trailing_incomplete_word",
    "unbalanced_brackets", "table_noise", "no_cjk_content",
})


def _valid_scoring_point_row(row: dict) -> bool:
    """评分表有效得分要点：来源页/引文与 score_item+score 元数据齐备。
    这类要点常是「项目组织」等名词短语；短和无动词不是残句证据。"""
    if row.get("section_kind") != "scoring":
        return False
    if not str(row.get("score_item") or "").strip() or not isinstance(row.get("score"), (int, float)):
        return False
    source = row.get("source") or {}
    return bool(str(source.get("quote") or "").strip() or source.get("page"))


def _scoring_point_signals(row: dict, text: str) -> list[str]:
    if not _valid_scoring_point_row(row):
        return []
    return [signal for signal in fragment_signals(text) if signal in _SCORING_POINT_HARD_SIGNALS]


def _fragment_basis(row: dict) -> str:
    """重洗时优先用首次抽取的原始碎片；已补全 text 不再作为锚点继续二次扩张。"""
    return str(row.get("source_fragment") or row.get("raw_export_text") or row.get("text") or "").strip()


def clean_requirement_row(row: dict, page_text: str = "") -> dict[str, Any]:
    """单条技术条款清洗。幂等；不改动人工已改/已确认条款的正文，只做范围标记。

    返回落盘字段补丁：scope 分流、残句补全结果或过滤原因。
    """
    patch: dict[str, Any] = {"clause_cleaned": True}
    text = str(row.get("text") or "").strip()
    locked = bool(row.get("manually_edited")) or row.get("status") == "confirmed"
    category = row_non_tech_category(row)
    signals = fragment_signals(text)
    source_signals = source_truncation_signals(text, page_text)
    for signal in source_signals:
        if signal not in signals:
            signals.append(signal)
    if _valid_scoring_point_row(row):
        # 评分点采用独立完整性判定：名词短语（如「项目组织」）是合法得分要点，
        # 只有断 punctuation/括号/表格噪声等硬碎片信号才允许进入补全或过滤。
        signals = [signal for signal in signals if signal in _SCORING_POINT_HARD_SIGNALS]
    if category and not signals:
        patch["requirement_scope"] = SCOPE_NON_TECHNICAL
        patch["non_tech_category"] = category
        patch["fragment_reason"] = ""
        return patch
    if not signals:
        patch["requirement_scope"] = SCOPE_TECHNICAL
        patch["non_tech_category"] = ""
        patch["fragment_reason"] = ""
        patch["clause_fragment"] = False
        return patch
    if locked:
        # 人工已经接管正文：不重写不丢弃，只留审计标记，由人工决定取舍。
        patch["requirement_scope"] = row.get("requirement_scope") or SCOPE_TECHNICAL
        patch["fragment_reason"] = ""
        return patch
    quote = str((row.get("source") or {}).get("quote") or "")
    # 章节/标题残句不是被截断的要求句：宁过滤，不用下一行原文拼出伪条款。
    heading_only = any(signal in signals for signal in ("ordinal_heading", "section_heading"))
    if heading_only and _heading_has_inline_content(text, page_text):
        heading_only = False
    completed = "" if heading_only else complete_fragment_text(text, quote, page_text)
    if completed:
        completed_category = non_tech_category(completed) or category
        patch["source_fragment"] = text
        patch["text"] = completed
        summary = str(row.get("extracted_summary") or "").strip()
        if not summary or summary == text:
            patch["extracted_summary"] = completed[:80]
        patch["fragment_completed"] = True
        patch["fragment_reason"] = ""
        patch["clause_fragment"] = False
        if completed_category:
            # 补全后才暴露完整语境：资格/格式/商务条款仍归非技术，不能借补全混回技术清单。
            patch["requirement_scope"] = SCOPE_NON_TECHNICAL
            patch["non_tech_category"] = completed_category
        else:
            patch["requirement_scope"] = SCOPE_TECHNICAL
            patch["non_tech_category"] = ""
        return patch
    if category:
        # 非技术条款即使是残句，也归入非技术查阅区；fragment_reason 保留供审计解释。
        patch["requirement_scope"] = SCOPE_NON_TECHNICAL
        patch["non_tech_category"] = category
        patch["clause_fragment"] = True
        patch["fragment_completed"] = False
        patch["fragment_reason"] = "+".join(signals)
        return patch
    patch["requirement_scope"] = SCOPE_FRAGMENT
    patch["clause_fragment"] = True
    patch["fragment_completed"] = False
    patch["fragment_reason"] = "+".join(signals)
    return patch


def clean_technical_requirements(workflow: dict) -> dict[str, Any]:
    """工作流级清洗：技术条款逐条分流。audit 落盘 workflow['technical_clause_cleaning'] 供查阅。

    已清洗（clause_cleaned）且未人工变更的行跳过；幂等可重跑。
    """
    requirements = workflow.get("requirements") or {}
    audit: dict[str, Any] = {"checked": 0, "completed": [], "filtered": [], "non_technical": []}
    for row in requirements.values():
        if not isinstance(row, dict) or not row.get("technical_clause") or row.get("merged_into"):
            continue
        if row.get("clause_cleaned") and not row.get("manually_edited"):
            # 已清洗行也要补做系统判断清理：覆盖旧版本清洗（无清理逻辑）留下的假负偏离。
            # 但早期目录重跑快照漏带 files 原文页时，碎片可能在“无原文可补”的环境下被永久过滤；
            # 现在若能取到原文页，允许用首次碎片重新清洗一次。无法补全仍保持过滤，绝不编造。
            page_text = _page_text_for(workflow, row)
            if row.get("clause_fragment") and not row.get("fragment_completed") and page_text:
                basis = _fragment_basis(row)
                probe = dict(row)
                probe["text"] = basis
                patch = clean_requirement_row(probe, page_text)
                if patch.get("fragment_completed") or patch.get("requirement_scope") != row.get("requirement_scope"):
                    row.update(patch)
                    clear_stale_judgment_fields(row)
                    audit["checked"] += 1
            else:
                clear_stale_judgment_fields(row)
            _collect_audit(audit, row)
            continue
        page_text = _page_text_for(workflow, row)
        patch = clean_requirement_row(row, page_text)
        row.update(patch)
        # 分流排除落定后立刻清掉遗留系统矩阵判断，假负偏离不得存活到合规扫描。
        clear_stale_judgment_fields(row)
        audit["checked"] += 1
        _collect_audit(audit, row)
    workflow["technical_clause_cleaning"] = audit
    return audit


def _audit_sample(row: dict) -> dict[str, Any]:
    source = row.get("source") or {}
    return {
        "requirement_id": row.get("id"),
        "text": str(row.get("text") or "")[:120],
        "page": source.get("page") or row.get("page"),
    }


def _collect_audit(audit: dict[str, Any], row: dict) -> None:
    scope = str(row.get("requirement_scope") or "")
    sample = _audit_sample(row)
    if row.get("fragment_completed"):
        if sample not in audit["completed"]:
            audit["completed"].append(sample)
    if scope == SCOPE_NON_TECHNICAL:
        entry = {**sample, "category": row.get("non_tech_category") or ""}
        if entry not in audit["non_technical"]:
            audit["non_technical"].append(entry)
    elif scope == SCOPE_FRAGMENT:
        entry = {**sample, "reason": row.get("fragment_reason") or ""}
        if entry not in audit["filtered"]:
            audit["filtered"].append(entry)
