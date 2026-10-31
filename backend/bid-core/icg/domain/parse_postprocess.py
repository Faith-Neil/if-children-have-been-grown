# 为什么有这个文件：PRD v1.8 §5.2.4 抽取后处理中不依赖模型的规则部分（APP-M2-T107、T109、T110）。
# 它解决什么问题：
# 1. 去重合并（第①步）：同一要求被不同分块、不同页重复抽出时只留一条主条目，全部来源挂在主条目上，重要性取最高一档；
#    数字取值不同的不合并（交给冲突检测）；人工改过的条目只给“建议合并”；已确认、已对应章节、挂了证据或写了响应的条目
#    只能当主条目，不会被并入别的条目；拆分过的两条不再自动合并。
# 2. 结构化字段统一单位后比较（第③步 b）：“24个月”与“2年”是同一取值，“12个月”与“24个月”才是冲突；金额按元、日期按日与时分。
# 3. 补遗覆盖原文（第③步 a）：补遗、澄清里的条目依次按“原文引号 → 条款编号 → 文字相近”找被修改的原条目；
#    唯一找到算“修改”，找不到但写明“修改为 / 删除”等字样的转人工指定，其余算新增。
# 这里只放纯函数（不读写状态、不依赖框架），写入状态、留痕与接口在 parse_decisions.py。

from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Callable, Iterable

IMPORTANCE_RANK = {"star": 5, "disqualification": 4, "qualification": 3, "scoring": 2, "general": 1}
IMPORTANCE_LABELS = {"star": "星号", "disqualification": "废标", "qualification": "资格", "scoring": "评分", "general": "一般"}
SIMILARITY = 0.85          # 规范化文字相似度阈值（PRD 示例 0.85）
CONTAIN_MIN_CHARS = 8      # “一条包含另一条”时较短一条至少的字数，避免把小标题并进长条款
CONTAIN_MIN_SHARE = 0.3    # 较短一条至少占较长一条的比例
AMEND_SIMILAR = 0.6        # 写明“修改为”等字样时，与原条款文字相近的阈值
RESTATE_SIMILAR = 0.75     # 没写修改字样、直接重述整条时的阈值
AMBIGUOUS_GAP = 0.03       # 第二相近的原条款与最相近的只差这么多时，不自动认定

_LEAD_NO = re.compile(
    r"^\s*(第[零一二三四五六七八九十百0-9]+[章节条款项]|[0-9]{1,2}(\.[0-9]{1,2}){0,3}[．.、)）]?"
    r"|[（(][0-9一二三四五六七八九十]{1,3}[)）]|[①-⑳]|[a-zA-Z][．.、)）])\s*")
_DROP = re.compile(r"[\s\W_]+", re.UNICODE)
_CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNIT = {"十": 10, "百": 100, "千": 1000}
# 只换“带量词”的中文数字（三年、二十四个月、两名、五个工作日），不碰“统一”“一般”这类词
_CN_MEASURED = re.compile(r"([零〇一二两三四五六七八九十百千]+)(?=个|年|月|周|星期|日|天|小时|时|分钟|分|秒|名|人|次|份|套|台|项|家|级|倍|元|万|%|％)")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _cn_to_int(run: str) -> int:
    section, number = 0, 0
    for ch in run:
        if ch in _CN_DIGIT:
            number = _CN_DIGIT[ch]
        else:
            section += (number or 1) * _CN_UNIT[ch]
            number = 0
    return section + number


def _arabic(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text or ""))
    return _CN_MEASURED.sub(lambda m: str(_cn_to_int(m.group(1))), value)


def _num(value: str) -> str:
    number = float(value)
    return str(int(number)) if number == int(number) else f"{number:g}"


def strip_numbering(text: str) -> str:
    return _LEAD_NO.sub("", unicodedata.normalize("NFKC", str(text or "")).strip(), count=1)


def normalize_text(text: str | None) -> str:
    """全角转半角、去条目编号、去空白与标点（含 ★）、英文小写。"""
    return _DROP.sub("", strip_numbering(text).lower())


def numbers(text: str | None) -> tuple[str, ...]:
    """条目里出现的数字（中文数字换成阿拉伯数字，去掉条目编号），排序后比较：数字不同就是取值不同。"""
    value = _arabic(strip_numbering(text)).replace(",", "")
    return tuple(sorted(_num(x) for x in _NUMBER.findall(value)))


def ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if matcher.real_quick_ratio() < SIMILARITY * 0.5:
        return matcher.real_quick_ratio()
    return matcher.ratio()


def same_requirement(text_a: str, text_b: str, norm_a: str | None = None, norm_b: str | None = None,
                     same_numbers: bool | None = None) -> float:
    """是否同一要求被重复抽出：返回相似度（0 表示不是）。数字取值不同一律不是。"""
    na = normalize_text(text_a) if norm_a is None else norm_a
    nb = normalize_text(text_b) if norm_b is None else norm_b
    if same_numbers is None:
        same_numbers = numbers(text_a) == numbers(text_b)
    if len(na) < 4 or len(nb) < 4 or not same_numbers:
        return 0.0
    if na == nb:
        return 1.0
    short, long_ = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(short) >= CONTAIN_MIN_CHARS and short in long_ and len(short) >= CONTAIN_MIN_SHARE * len(long_):
        return round(len(short) / len(long_), 3) or 0.01
    if len(short) < SIMILARITY * len(long_):
        return 0.0
    value = ratio(na, nb)
    return round(value, 3) if value >= SIMILARITY else 0.0


# ---------------------------------------------------------------- 去重合并（第①步）

def importance(row: dict, category_of: Callable[[dict], str]) -> str:
    explicit = str(row.get("importance") or "")
    category = category_of(row)
    best = max((explicit, category), key=lambda k: IMPORTANCE_RANK.get(k, 0))
    return best if best in IMPORTANCE_RANK else "general"


def candidate(row: dict) -> bool:
    """参与去重的条目：未忽略、未并入、未被补遗替代、在本项目编写范围内。"""
    return (row.get("status") != "rejected" and not row.get("merged_into") and not row.get("out_of_scope")
            and row.get("effective_status") != "superseded")


def untouched(row: dict) -> bool:
    """还没有任何人工结果的条目才可以被自动并入别的条目（§5.2.4 规则 4：人工结果不被覆盖）。"""
    return (row.get("status") == "pending" and not row.get("manually_edited") and not row.get("chapter_id")
            and not row.get("evidence_ids") and not str(row.get("response") or "").strip()
            and not row.get("added_from_scan") and not row.get("amends"))


def _bigrams(text: str) -> set[str]:
    return {text[i:i + 2] for i in range(len(text) - 1)}


def _candidate_pairs(rows: list[dict], norms: dict[str, str]) -> Iterable[tuple[dict, dict]]:
    """只比较可能相同的两条：按字二元组倒排找共有片段多的条目，避免上千条两两逐字比对（解析在事务里执行，要快）。

    相似度 ≥0.85 或“一条包含另一条”时，较短一条的二元组绝大部分都出现在另一条里；这里取较松的下限（50%），
    真正是否相同仍由 same_requirement 逐字判断。出现在超过四分之一条目里的常见二元组（“投标”“提供”）不参与计数。"""
    grams = {r["id"]: _bigrams(norms[r["id"]]) for r in rows}
    index: dict[str, list[int]] = {}
    for position, row in enumerate(rows):
        for gram in grams[row["id"]]:
            index.setdefault(gram, []).append(position)
    common = {g for g, posting in index.items() if len(rows) > 40 and len(posting) > len(rows) / 4}
    by_text: dict[str, list[int]] = {}
    for position, row in enumerate(rows):
        by_text.setdefault(norms[row["id"]], []).append(position)
    seen: set[tuple[int, int]] = set()
    for positions in by_text.values():  # 规范化后完全相同的直接成对
        for i, a in enumerate(positions):
            for b in positions[i + 1:]:
                seen.add((a, b))
                yield rows[a], rows[b]
    owns = [grams[row["id"]] - common for row in rows]
    sizes = [len(own) or 1 for own in owns]
    for position, row in enumerate(rows):
        own = owns[position]
        if not own:
            continue
        shared: dict[int, int] = {}
        for gram in own:
            for other in index[gram]:
                if other > position:
                    shared[other] = shared.get(other, 0) + 1
        for other, count in shared.items():
            if count >= 0.5 * min(sizes[position], sizes[other]) and (position, other) not in seen:
                seen.add((position, other))
                yield row, rows[other]


def plan_merges(rows: list[dict], category_of: Callable[[dict], str]) -> dict:
    """rows 按抽取先后排列。返回 {"groups": [{"primary", "members", "importance"}], "suggestions": [(a, b, 相似度)]}。

    - 一组里已有主条目的沿用原主条目（多次解析结果稳定）；否则有人工结果的那条做主条目；再按重要性、先后取第一条；
    - 一组里有两条以上已有人工结果的，只把未处理的并入主条目，其余与主条目之间给“建议合并”；
    - 人工改过原文的条目与任何条目之间都只给建议。"""
    pool = [r for r in rows if candidate(r)]
    position = {r["id"]: i for i, r in enumerate(pool)}
    norms = {r["id"]: normalize_text(r.get("text")) for r in pool}
    nums = {r["id"]: numbers(r.get("text")) for r in pool}
    blocked = {frozenset((r["id"], other)) for r in pool for other in (r.get("merge_blocked") or [])}
    buckets: dict[tuple, list[dict]] = {}
    for row in pool:
        if len(norms[row["id"]]) >= 4:
            buckets.setdefault(nums[row["id"]], []).append(row)
    parent = {r["id"]: r["id"] for r in pool}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    suggestions: list[tuple[str, str, float]] = []
    for bucket in buckets.values():
        for a, b in _candidate_pairs(bucket, norms):
            score = same_requirement(a.get("text"), b.get("text"), norms[a["id"]], norms[b["id"]], True)
            if not score or frozenset((a["id"], b["id"])) in blocked:
                continue
            if a.get("manually_edited") or b.get("manually_edited") or not (untouched(a) or untouched(b)):
                suggestions.append((a["id"], b["id"], score))
                continue
            parent[find(a["id"])] = find(b["id"])
    by_root: dict[str, list[dict]] = {}
    for row in pool:
        by_root.setdefault(find(row["id"]), []).append(row)
    groups = []
    for members in by_root.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda r: position[r["id"]])
        rank = lambda r: (-IMPORTANCE_RANK[importance(r, category_of)], position[r["id"]])  # noqa: E731
        existing = [r for r in members if r.get("merge_status") == "primary"]
        touched = [r for r in members if not untouched(r)]
        primary = (sorted(existing, key=rank) or sorted(touched, key=rank) or sorted(members, key=rank))[0]
        merged = [r for r in members if r is not primary and untouched(r)]
        for row in members:
            if row is not primary and not untouched(row):
                suggestions.append((primary["id"], row["id"], 1.0))
        if merged:
            top = max([primary, *merged], key=lambda r: IMPORTANCE_RANK[importance(r, category_of)])
            groups.append({"primary": primary["id"], "members": [r["id"] for r in merged],
                           "importance": importance(top, category_of)})
    into = {member: group["primary"] for group in groups for member in group["members"]}
    unique = {}
    for a, b, score in suggestions:
        a, b = into.get(a, a), into.get(b, b)  # 被并入的条目由主条目代表
        pair = frozenset((a, b))
        if a != b and pair not in blocked:
            unique.setdefault(pair, (a, b, score))
    return {"groups": groups, "suggestions": list(unique.values())}


# ---------------------------------------------------------------- 结构化字段统一单位（第③步 b）

_DATE = re.compile(r"(\d{4})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*日?"
                   r"(?:[^0-9]{0,6}?(上午|下午|晚上)?\s*(\d{1,2})\s*[:：时点]\s*(\d{1,2})?)?")
_DURATION_UNITS = {"年": ("months", 12), "个月": ("months", 1), "月": ("months", 1), "周": ("days", 7), "星期": ("days", 7),
                   "日历天": ("days", 1), "天": ("days", 1), "日": ("days", 1), "工作日": ("workdays", 1),
                   "小时": ("minutes", 60), "分钟": ("minutes", 1)}
_DURATION = re.compile(r"^(\d+(?:\.\d+)?)\s*(个月|日历天|工作日|小时|分钟|星期|年|月|周|天|日)(.*)$")
_AMOUNT = re.compile(r"^(?:人民币|rmb|¥|￥)?\s*(\d+(?:\.\d+)?)\s*(亿元|万元|元|万)(.*)$")
_AMOUNT_SCALE = {"亿元": 100_000_000, "万元": 10_000, "万": 10_000, "元": 1}


def canonical_value(value: str | None) -> str:
    """事实取值的比较口径：金额折成元、时长折成月/天/分钟、日期取年月日与时分，其余比较规范化文字。"""
    text = _arabic(str(value or "")).strip().lower().replace(",", "")
    date = _DATE.search(text)
    if date:
        year, month, day, noon, hour, minute = date.groups()
        result = f"date:{int(year):04d}-{int(month):02d}-{int(day):02d}"
        if hour is not None:
            h = int(hour) + (12 if noon in ("下午", "晚上") and int(hour) < 12 else 0)
            result += f"T{h:02d}:{int(minute or 0):02d}"
        return result
    compact = re.sub(r"\s+", "", text)
    amount = _AMOUNT.match(compact)
    if amount:
        yuan = float(amount.group(1)) * _AMOUNT_SCALE[amount.group(2)]
        return f"amount:{_num(str(yuan))}|{_DROP.sub('', amount.group(3))}"
    duration = _DURATION.match(compact)
    if duration:
        kind, scale = _DURATION_UNITS[duration.group(2)]
        return f"{kind}:{_num(str(float(duration.group(1)) * scale))}|{_DROP.sub('', duration.group(3))}"
    return "text:" + _DROP.sub("", text)


# ---------------------------------------------------------------- 补遗覆盖原文（第③步 a）

AMEND = re.compile(r"修改为|修订为|调整为|变更为|更正为|更改为|替换为|现改为|改为|删除|取消|作废|不再要求|补充为")
_QUOTED = re.compile(r"[“\"‘「『]([^”\"’」』]{2,300})[”\"’」』]")
_CLAUSE_REF = re.compile(r"(?<![0-9.])([0-9]{1,2}(?:\.[0-9]{1,2}){1,3})(?![0-9])")
_OWN_NO = re.compile(r"^\s*([0-9]{1,2}(?:\.[0-9]{1,2}){1,3})(?![0-9])")


def clause_number(row: dict) -> str:
    """条目自身的条款编号（如 3.2.1）：取原文开头或所在章节标题开头的编号。"""
    for text in (row.get("text"), (row.get("source") or {}).get("quote"), *(reversed(row.get("section_path") or []))):
        found = _OWN_NO.match(unicodedata.normalize("NFKC", str(text or "")))
        if found:
            return found.group(1)
    return ""


def amend_target(row: dict, base: list[dict]) -> dict:
    """补遗条目对原条目的关系：{"kind": same|modified|unlocated|added, "target": id|None, "method", "candidates"}。

    base 是版本链上更早文件里仍有效的条目。只有唯一定位时才算“修改”；多条都像时转人工。"""
    text = strip_numbering(row.get("text"))
    amend = AMEND.search(text)
    head = text[:amend.start()] if amend else text
    if amend:
        quoted = [normalize_text(q) for q in _QUOTED.findall(head or text)]
        quoted = [q for q in quoted if len(q) >= 4]
        if quoted:
            hits = [b for b in base if quoted[0] in normalize_text(b.get("text"))]
            if len(hits) == 1:
                return {"kind": "modified", "target": hits[0]["id"], "method": "quote", "candidates": []}
            if hits:
                return {"kind": "unlocated", "target": None, "method": "quote", "candidates": [b["id"] for b in hits[:5]]}
        refs = set(_CLAUSE_REF.findall(unicodedata.normalize("NFKC", head)))
        if refs:
            hits = [b for b in base if clause_number(b) in refs]
            if len(hits) == 1:
                return {"kind": "modified", "target": hits[0]["id"], "method": "clause_no", "candidates": []}
            if hits:
                return {"kind": "unlocated", "target": None, "method": "clause_no", "candidates": [b["id"] for b in hits[:5]]}
        subject = normalize_text(head)
        if len(subject) >= 4:
            hits = [b for b in base if subject in normalize_text(b.get("text"))]
            if len(hits) == 1:
                return {"kind": "modified", "target": hits[0]["id"], "method": "subject", "candidates": []}
    plain = normalize_text(AMEND.sub("", text))
    scored = sorted(((ratio(plain, normalize_text(b.get("text"))), b) for b in base), key=lambda item: -item[0])
    for b in base:
        if same_requirement(row.get("text"), b.get("text")) and not amend:
            return {"kind": "same", "target": b["id"], "method": "duplicate", "candidates": []}
    threshold = AMEND_SIMILAR if amend else RESTATE_SIMILAR
    if scored and scored[0][0] >= threshold:
        best_score, best = scored[0]
        close = [b for score, b in scored[1:] if score >= best_score - AMBIGUOUS_GAP]
        if not close:
            return {"kind": "modified", "target": best["id"], "method": "similar", "candidates": [],
                    "similarity": round(best_score, 3)}
        if amend:
            return {"kind": "unlocated", "target": None, "method": "similar",
                    "candidates": [best["id"], *[b["id"] for b in close[:4]]]}
    if amend:
        return {"kind": "unlocated", "target": None, "method": "none",
                "candidates": [b["id"] for score, b in scored[:3] if score >= 0.4]}
    return {"kind": "added", "target": None, "method": "none", "candidates": []}


def amended_text(original: str, amendment: str) -> str:
    """补遗之后这条原条款应读作什么：写成“原文‘甲’修改为‘乙’”且甲出现在原条款里时，把甲换成乙；
    写成“第3.2条修改为：……”时取修改为之后的文字；否则就是补遗条目本身。供补遗差异逐字对照。"""
    text = unicodedata.normalize("NFKC", str(amendment or "")).strip()
    found = AMEND.search(text)
    if not found:
        return strip_numbering(text)
    if found.group(0) in ("删除", "取消", "作废", "不再要求"):
        return ""  # 补遗删除了这条
    before, after = text[:found.start()], text[found.end():]
    old = _QUOTED.findall(before)
    new = _QUOTED.findall(after)
    source = unicodedata.normalize("NFKC", str(original or ""))
    if old and new and old[0] in source:
        return source.replace(old[0], new[0], 1)
    if new:
        return new[0]
    return after.lstrip("：: ").strip() or strip_numbering(text)


def text_diff(old: str, new: str) -> list[dict]:
    """补遗差异页逐段对照：[{op: equal|delete|insert, text}]（按字比对，供页面标红标绿）。"""
    a, b = str(old or ""), str(new or "")
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            ops.append({"op": "equal", "text": a[i1:i2]})
        else:
            if i2 > i1:
                ops.append({"op": "delete", "text": a[i1:i2]})
            if j2 > j1:
                ops.append({"op": "insert", "text": b[j1:j2]})
    return ops


def ordered(items: Iterable[dict], key: str = "id") -> list[str]:
    return list(dict.fromkeys(item[key] for item in items))
