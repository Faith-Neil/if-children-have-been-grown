# 为什么有这个文件：导出 .docx 前的确定性净化管道（export_sanitizer）。
# 它解决什么问题：
# 1. 剥离模型在正文首行重复输出的节标题（真机 24/30 节重复）；
# 2. 清除内部标记：[标:...]、[片:...]、[证:...] 引用、[medium] 风险标签、32 位十六进制文档 ID、「需要核对」核验标记；
# 3. 收敛 Markdown 残留：<br>、---、$$、孤立 **、反引号，防止源码裸露进 Word；
# 4. 在写入 docx 前对整册 markdown 做最后统一净化，与编辑台保持同一份真相源（编辑台看到什么，导出就是什么，只是更干净）。

from __future__ import annotations

import re

# 内部引用标记：[标:xxx]、[片:xxx]、[证:xxx]（允许中文冒号）
_CITATION = re.compile(r"\[(?:标|片|证)[:：][^\]\n]{0,80}\]")
_CITATION_LABELED = re.compile(r"\[(?:标|片|证)[:：]([^\]\n]{0,80})\]")
# 风险等级标签：[medium]、[high]、[low]（大小写不敏感）
_RISK_TAG = re.compile(r"\[(?:high|medium|low)\]", re.IGNORECASE)
# 32 位十六进制文档/chunk ID
_HEX_ID = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{32}(?![0-9a-fA-F])")
# 核验标记行
_REVIEW_MARK = re.compile(r"^\s*需要核对\s*$")
# HTML 换行
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
# 数学块/孤立美元符号
_DOLLAR = re.compile(r"(?<![A-Za-z0-9_])\${1,2}(?![A-Za-z0-9_])")
# 水平分割线（单独一行 --- 或 ***，但表格分隔行 |---| 除外）
_HR = re.compile(r"^\s*(?:-{3,}|_{3,}|\*{3,})\s*$")
# Markdown 强调符号（导出 Word 不允许裸源码；只去符号，不删文字）
_MD_STRONG = re.compile(r"\*\*([^*\n]+)\*\*")
_MD_STRONG_TOKEN = re.compile(r"\*{2,}")
_INTERNAL_SECTION_REF = re.compile(r"(?<![A-Z0-9])(?:[TSR]-\d+(?:-\d+)?)(?![A-Z0-9])")
_QUOTE_PREFIX = re.compile(r"^>\s?")
_EMPTY_PARENS = re.compile(r"[（(]\s*[）)]")
# 行首残留 markdown 标题符号（正文里的 #### 不应作为标题裸露，导出器有自己的标题体系）
_MD_HEADING = re.compile(r"^(#{4,8})\s+")


def preserve_table_citation_labels(markdown: str) -> str:
    """表格里的引用不是正文噪音，而是依据来源；表头引用剥空后由列义兜底，正文引用尽量保留可读名。"""
    lines = []
    raw_lines = (markdown or "").splitlines()
    for line_index, line in enumerate(raw_lines):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and not _is_table_rule(stripped):
            next_line = raw_lines[line_index + 1].strip() if line_index + 1 < len(raw_lines) else ""
            is_header = bool(re.match(r"^\|?\s*:?-{2,}", next_line))

            def repl(match: re.Match) -> str:
                label = (match.group(1) or "").strip()
                if label and not re.fullmatch(r"[0-9a-fA-F]{16,32}", label):
                    return label
                return "" if is_header else "详见对应章节正文"

            line = _CITATION_LABELED.sub(repl, line)
        lines.append(line)
    return "\n".join(lines)


def enforce_export_consistency(text: str) -> str:
    """只做与项目事实无关的模板噪声清理；业务数字/SLA/年限由生成侧与 Verifier 负责。"""
    # CVE-2025-XXXX 是模型常见的过期模板占位，不是真实漏洞编号；真实 CVE 编号不碰。
    return text.replace("CVE-2025-XXXX", "最新披露的相关安全漏洞")


def inject_scoring_scorecard(markdown: str, scoring_rules: list[dict] | None) -> str:
    """在评分对照节开头补齐 30/30/20/20 四大评分项的显性小节标题与加分规则。"""
    if not scoring_rules:
        return markdown
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if not re.match(r"^#{1,3}\s*\d+\s+.*评分对照", line.strip()):
            continue
        following = "\n".join(lines[index:index + 80])
        if "昆航DBA服务需求" in following and "数据库每月巡检" in following:
            return markdown
        section_no = (re.match(r"^#{1,3}\s*(\d+)", line.strip()) or [None, "8"])[1]
        blocks = []
        for pos, rule in enumerate(scoring_rules[:4], start=1):
            item = str(rule.get("item") or "")
            score = str(rule.get("score") or "")
            rule_text = re.sub(r"(?<!（)加(\d+(?:-\d+)?)分", lambda match: "（加" + match.group(1) + "分）", str(rule.get("rule") or ""))
            decision = str(rule.get("decision") or "")
            blocks.extend([
                f"## {section_no}.{pos} {item}（{score}）",
                f"评分规则：{rule_text}",
                f"投标响应决策：{decision}。",
                "",
            ])
        return "\n".join(lines[:index + 1] + ["", *blocks] + lines[index + 1:])
    return markdown


def strip_internal_markers(text: str) -> str:
    """清除引用、风险标签、hex ID、核验标记。保留占位符【待确认】/[待人工补充]（那是给用户看的）。"""
    out = _CITATION.sub("", text)
    out = _RISK_TAG.sub("", out)
    out = _HEX_ID.sub("", out)
    return out


def normalize_markdown_noise(text: str) -> str:
    """把不适合裸露进 Word 的符号转成形：<br>→换行、$$ 清除、Markdown 强调只留文字。"""
    out = _BR.sub("\n", text)
    out = _DOLLAR.sub("", out)
    out = _MD_STRONG.sub(r"\1", out)
    out = _MD_STRONG_TOKEN.sub("", out)
    out = _INTERNAL_SECTION_REF.sub("", out)
    out = re.sub(r"(响应|落实|对照|满足)\s*[、，,\s]*中", r"\1招标文件中", out)
    out = out.replace("满足中", "满足招标文件要求").replace("符合中", "符合招标文件要求")
    out = out.replace("招标文件中标关键条款", "招标文件关键条款")
    out = _EMPTY_PARENS.sub("", out)
    return out


def strip_duplicate_title(body: str, title: str) -> str:
    """模型常在正文首行重复输出节标题（原样或稍加 markdown 符号）。首行与节标题规范化后相同则剥掉。"""
    if not body or not title:
        return body
    lines = body.splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        return body
    first = lines[index].strip().lstrip("#* >").strip()
    want = re.sub(r"[\s#*]", "", title)
    got = re.sub(r"[\s#*]", "", first)
    # 首行也可能带编号（如「3.2 数据库巡检」），编号已在导出标题体系里，一并剥离
    got = re.sub(r"^\d+(?:\.\d+)*", "", got)
    if got and got == re.sub(r"^\d+(?:\.\d+)*", "", want):
        lines.pop(index)
        return "\n".join(lines).lstrip("\n")
    return body


def sanitize_body(text: str, *, title: str = "") -> str:
    """节级净化：剥重复标题 → 清内部标记 → 收敛 markdown 噪声 → 清核验标记行。"""
    out = strip_duplicate_title(str(text or ""), title)
    out = strip_internal_markers(out)
    out = normalize_markdown_noise(out)
    lines = []
    for line in out.splitlines():
        if _REVIEW_MARK.match(line):
            continue
        if _HR.match(line):
            continue
        line = _MD_HEADING.sub("", line)
        lines.append(line.rstrip())
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


_PIPE_LINE = None


def _is_pipe_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") or (stripped.count("|") >= 2 and not stripped.startswith("#"))


def _is_table_rule(line: str) -> bool:
    stripped = line.strip().strip("|")
    cells = [c.strip() for c in stripped.split("|")]
    return bool(cells) and all(c and set(c) <= set("-: ") and "-" in c for c in cells)


def clean_orphan_pipe_lines(text: str) -> str:
    """合法 markdown 表格（表头行+分隔行+数据行）原样保留交给导出器转 Word 原生表格；
    落单的管道行（被截断的半截表格、缺分隔行的伪表格）把 | 转成全角⎮，杜绝源码裸露。"""
    lines = text.splitlines()
    n = len(lines)
    in_table: list[bool] = [False] * n
    index = 0
    while index < n:
        if _is_pipe_line(lines[index]) and index + 1 < n and _is_table_rule(lines[index + 1]):
            j = index
            while j < n and (_is_pipe_line(lines[j]) or _is_table_rule(lines[j])) and lines[j].strip():
                in_table[j] = True
                j += 1
            index = j
        else:
            index += 1
    out_lines = []
    for i, line in enumerate(lines):
        if line.strip() and _is_pipe_line(line) and not in_table[i] and not _is_table_rule(line):
            cleaned = line.replace("|", "⎮")
            out_lines.append(cleaned)
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def fill_citation_empty_table_cells(text: str) -> str:
    """引用标签剥离后，表格单元格不得空白；表头按列义补齐，正文空单元格才回填章节正文。"""
    header_fallback = ["事项", "响应要求", "服务措施", "执行记录", "依据来源", "交付物"]
    out_lines = []
    raw_lines = text.splitlines()
    for line_index, line in enumerate(raw_lines):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and not _is_table_rule(stripped):
            parts = stripped.strip("|").split("|")
            if any(not part.strip() for part in parts):
                next_line = raw_lines[line_index + 1].strip() if line_index + 1 < len(raw_lines) else ""
                is_header = bool(re.match(r"^\|?\s*:?-{2,}", next_line))
                fixed = []
                for cell_index, part in enumerate(parts):
                    if part.strip():
                        fixed.append(part)
                    elif is_header:
                        fixed.append(" " + (header_fallback[cell_index] if cell_index < len(header_fallback) else "说明") + " ")
                    else:
                        fixed.append(" 详见对应章节正文 ")
                line = "|" + "|".join(fixed) + "|"
        out_lines.append(line)
    return "\n".join(out_lines)


def infer_table_basis_cells(text: str) -> str:
    """仅在“合规条款”表内补齐依据来源；依据名从本节上下文动态提取，不写死项目/机构名。"""
    lines = text.splitlines()
    out_lines: list[str] = []
    in_compliance_table = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        is_table = stripped.startswith("|") and stripped.endswith("|")
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if is_table and "合规条款" in stripped and re.match(r"^\|?\s*:?-{2,}", next_line):
            in_compliance_table = True
            out_lines.append(line)
            continue
        if in_compliance_table and (not is_table):
            in_compliance_table = False
        if in_compliance_table and is_table and "详见对应章节正文" in stripped and not _is_table_rule(stripped) and "合规条款" not in stripped:
            parts = stripped.strip("|").split("|")
            subject = " ".join(part.strip() for part in parts[:-1])
            context = "\n".join(lines[max(0, index - 30):index])
            quoted = re.findall(r"《([^》]{2,60})》", context)
            basis = ""
            if "招投标法" in subject:
                basis = next((f"《{name}》" for name in quoted if "招投标法" in name), "招标文件评标与合规条款")
            elif "第三方披露" in subject or "安全协议" in subject:
                basis = next((f"《{name}》" for name in quoted if "安全协议" in name), "招标文件信息安全与保密条款")
            elif "保密" in subject or "泄露" in subject:
                basis = next((f"《{name}》" for name in quoted if "保密" in name), "保密协议及招标文件保密条款")
            if basis:
                parts[-1] = " " + basis + " "
                line = "|" + "|".join(parts) + "|"
        out_lines.append(line)
    return "\n".join(out_lines)


def _opening_subject(title: str) -> str:
    pairs = (
        (("故障", "应急"), "应急体系"), (("重保", "驻场"), "驻场服务安排"),
        (("团队", "人员"), "服务团队"), (("沟通",), "沟通机制"),
        (("保密", "合规"), "保密合规体系"), (("成果", "交付"), "交付保障机制"),
        (("评分",), "评分响应方案"), (("DBA",), "DBA服务方案"),
        (("维保", "巡检", "执行标准"), "运维服务体系"), (("服务",), "服务方案"),
    )
    for words, subject in pairs:
        if any(word in title for word in words):
            return subject
    return "本节方案"


def deformalize_section_openings(markdown: str) -> str:
    """非第 1 节禁止机械地用「本项目…」开篇。保留事实，只替换起始主语。"""
    lines = markdown.splitlines()
    section_index = 0
    pending_title = ""
    pending_heading = -1
    for index, line in enumerate(lines):
        stripped = line.strip()
        heading = re.match(r"^#{1,6}\s*(\d+(?:\.\d+)*)\s+(.+)$", stripped)
        if heading:
            section_index += 1
            pending_title = heading.group(2).strip()
            pending_heading = index
            continue
        if pending_heading < 0 or not stripped or stripped.startswith(("#", "|", "---")):
            continue
        first_content_index = index
        if section_index > 1 and stripped.startswith("本项目"):
            subject = _opening_subject(pending_title)
            replaced = re.sub(
                r"^本项目(针对|面向|聚焦|严格|在|将|所|的)?",
                lambda m: subject + (m.group(1) or ""),
                stripped,
                count=1,
            )
            replaced = replaced.replace(subject + "所", "我司所")
            lines[first_content_index] = replaced
        pending_heading = -1
    return "\n".join(lines)


def sanitize_markdown(markdown: str) -> str:
    """整册 markdown 出口净化（标题行/表格行结构保留，只处理正文行内的内部标记与噪声）。"""
    markdown = preserve_table_citation_labels(markdown)
    out = strip_internal_markers(markdown)
    out = normalize_markdown_noise(out)
    out = enforce_export_consistency(out)
    lines = []
    for line in out.splitlines():
        if _REVIEW_MARK.match(line):
            continue
        if _HR.match(line) and not line.strip().startswith("|"):
            continue
        line = _QUOTE_PREFIX.sub("", line)
        lines.append(line.rstrip())
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = fill_citation_empty_table_cells(out)
    out = infer_table_basis_cells(out)
    out = deformalize_section_openings(out)
    out = clean_orphan_pipe_lines(out)
    return out
