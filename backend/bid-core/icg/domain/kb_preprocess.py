# 为什么有这个文件：知识库文档入 RAGFlow 前的确定性预处理：历史标书“去实体化”清洗与多型号参数表/故障台账“带表头拆行”。
# 它解决什么问题：
# 1. 历史标书原件若带旧甲方名、旧项目名、旧项目编号和合同金额入库，本地大模型极易直接照抄造成严重串标事故；
# 2. 产品对比参数大表（A/B/C 三款型号并列）或 Excel 故障案例台账若被普通切片把表头切丢，检索与生成会跨型号张冠李戴，
#    且本机 RAGFlow v1.0 会丢弃原生 doc_type=table 分块。这里在入库前拆成携带表头与精确型号的独立章节块。

from __future__ import annotations

import csv
import io
import re
from pathlib import PurePosixPath
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

_LABELLED_CLIENT = re.compile(
    r"(?:采购人|招标人|业主单位|业主名称|甲方名称|甲方|采购单位|客户名称)\s*[：:]\s*([^\n\r，,。；;|｜]{2,42})"
)
_LABELLED_PROJECT = re.compile(
    r"(?:项目名称|采购项目名称|招标项目名称|工程名称)\s*[：:]\s*([^\n\r，,。；;|｜]{3,64})"
)
_PROJECT_CODE = re.compile(
    r"((?:项目编号|招标编号|采购编号|合同编号)\s*[：:]\s*)[A-Za-z0-9_\-〔〕()（）/]{4,48}"
)
_AMOUNT = re.compile(
    r"(?<![A-Za-z0-9.])\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:万元|亿元|元整|元人民币)"
)
_SPECIFIC_ORG = re.compile(
    r"[\u4e00-\u9fff]{2,14}?(?:农村商业银行|农商行|农村信用社|农信社|商业银行|人民银行|银行|"
    r"人民医院|中医院|妇幼保健院|医院|财政局|大数据局|政务服务局|卫健委|公安局|税务局|交通局|人社局|"
    r"有限责任公司|股份有限公司|集团有限公司)"
)
_GENERIC_ORG_PREFIX = (
    "我公司", "本公司", "贵公司", "某", "招标", "投标", "采购", "供应", "第三", "原厂", "合作",
)
# 主流厂商/品牌词白名单：这些词命中的机构名属于产品厂商或生态伙伴而非旧甲方，脱敏不得误伤
_BUILTIN_ALLOWLIST = (
    "华为", "华三", "新华三", "H3C", "浪潮", "联想", "曙光", "中兴", "Cisco", "思科",
    "Dell", "戴尔", "IBM", "Oracle", "甲骨文", "VMware", "微软", "Microsoft",
    "海康", "大华", "宇视", "深信服", "奇安信", "启明星辰", "绿盟", "天融信", "安恒",
    "中国移动", "中国联通", "中国电信", "国家电网",
)


def _deid_allowlist(user_meta: dict[str, str] | None) -> list[str]:
    """内置品牌词 + user_meta 扩展（deid_allow/entity_allowlist 逗号分隔，bidder_name/our_company 我方公司名）。"""
    meta = user_meta or {}
    words: list[str] = list(_BUILTIN_ALLOWLIST)
    raw = str(meta.get("deid_allow") or meta.get("entity_allowlist") or "")
    words.extend(w for w in re.split(r"[,，;；\s]+", raw) if w.strip())
    for key in ("bidder_name", "our_company", "company_name"):
        cleaned = _clean_entity(meta.get(key, ""))
        if cleaned:
            words.append(cleaned)
    return list(dict.fromkeys(w for w in words if len(w) >= 2))
_MODEL_HEADERS = ("型号", "产品型号", "适用型号", "设备型号", "规格型号", "model", "product_model")
_FAULT_HEADERS = ("故障分类", "故障类型", "故障类别", "问题分类", "fault_category")
_SEVERITY_HEADERS = ("故障等级", "严重程度", "级别", "severity")
_PARAM_COL0 = ("参数", "指标", "功能", "规格", "技术项", "项目", "特性")


def _clean_entity(raw: str) -> str:
    val = re.sub(r"[（(].*?[)）]$", "", str(raw or "").strip()).strip("。；;，, ")
    return val if len(val) >= 2 else ""


def desensitize_history_text(text: str, user_meta: dict[str, str] | None = None) -> tuple[str, dict[str, int]]:
    """对历史标书正文执行去实体化：替换旧甲方名称、旧项目名称、项目编号与具体金额。"""
    source = str(text or "")
    if not source:
        return source, {"clients": 0, "projects": 0, "codes": 0, "amounts": 0}

    meta = user_meta or {}
    clients: list[str] = []
    projects: list[str] = []

    for key in ("purchaser", "client_name", "owner"):
        c = _clean_entity(meta.get(key, ""))
        if c and c not in clients:
            clients.append(c)
    for key in ("project_name",):
        p = _clean_entity(meta.get(key, ""))
        if p and p not in projects:
            projects.append(p)

    for m in _LABELLED_CLIENT.finditer(source):
        c = _clean_entity(m.group(1))
        if c and not c.startswith("[") and c not in clients:
            clients.append(c)
    for m in _LABELLED_PROJECT.finditer(source):
        p = _clean_entity(m.group(1))
        if p and not p.startswith("[") and p not in projects:
            projects.append(p)

    # 白名单只约束“按机构后缀自动探测”的旧甲方候选；显式标注的采购人/项目名称仍是脱敏红线
    allowlist = _deid_allowlist(user_meta)
    for m in _SPECIFIC_ORG.finditer(source):
        org = m.group(0).strip()
        if len(org) < 4 or any(org.startswith(prefix) for prefix in _GENERIC_ORG_PREFIX):
            continue
        if any(token in org for token in allowlist):
            continue
        if org not in clients:
            clients.append(org)

    # 先替换较长项目名，再替换甲方名，防止子串残留（如“XX银行核心运维项目”先整体变 [某项目]）
    projects.sort(key=len, reverse=True)
    clients.sort(key=len, reverse=True)

    out = source
    proj_hits = 0
    for p in projects:
        if p in out:
            proj_hits += out.count(p)
            out = out.replace(p, "[某项目]")

    client_hits = 0
    for c in clients:
        if c in out:
            client_hits += out.count(c)
            out = out.replace(c, "[某甲方]")

    code_hits = len(_PROJECT_CODE.findall(out))
    out = _PROJECT_CODE.sub(r"\1[项目编号]", out)

    amount_hits = len(_AMOUNT.findall(out))
    out = _AMOUNT.sub("[合同金额]", out)

    return out, {
        "clients": client_hits,
        "projects": proj_hits,
        "codes": code_hits,
        "amounts": amount_hits,
    }


def _scrub_docx_zip(data: bytes, user_meta: dict[str, str] | None) -> tuple[bytes, dict[str, int]] | None:
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with ZipFile(io.BytesIO(data), "r") as zin:
            if "word/document.xml" not in zin.namelist():
                return None
            entries = {name: zin.read(name) for name in zin.namelist()}
        root = ElementTree.fromstring(entries["word/document.xml"])
    except (BadZipFile, ElementTree.ParseError, KeyError):
        return None

    # 先拼出全文以便识别“采购人：XXX”“项目名称：YYY”，再按段落回写，解决跨 <w:t> 拆词问题
    paragraphs = list(root.iter(ns + "p"))
    full_text = "\n".join(
        "".join(el.text or "" for el in p.iter(ns + "t"))
        for p in paragraphs
    )
    _, _ = desensitize_history_text(full_text, user_meta)

    extra_meta = dict(user_meta or {})
    for m in _LABELLED_CLIENT.finditer(full_text):
        extra_meta.setdefault("purchaser", _clean_entity(m.group(1)))
    for m in _LABELLED_PROJECT.finditer(full_text):
        extra_meta.setdefault("project_name", _clean_entity(m.group(1)))

    totals = {"clients": 0, "projects": 0, "codes": 0, "amounts": 0}
    for p in paragraphs:
        t_nodes = list(p.iter(ns + "t"))
        if not t_nodes:
            continue
        joined = "".join(node.text or "" for node in t_nodes)
        if not joined.strip():
            continue
        cleaned, counts = desensitize_history_text(joined, extra_meta)
        if cleaned != joined:
            t_nodes[0].text = cleaned
            for rest in t_nodes[1:]:
                rest.text = ""
            for k in totals:
                totals[k] += counts[k]

    entries["word/document.xml"] = ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)
    out_buf = io.BytesIO()
    with ZipFile(out_buf, "w") as zout:
        for name, content in entries.items():
            zout.writestr(name, content)
    return out_buf.getvalue(), totals


def preprocess_history_upload(
    filename: str, data: bytes, user_meta: dict[str, str] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """历史标书上传前去实体化：支持真实 DOCX XML 改写、纯文本字节改写，二进制 PDF/DOC 标记解析后分块清洗。"""
    if data[:4] == b"PK\x03\x04":
        scrubbed = _scrub_docx_zip(data, user_meta)
        if scrubbed is not None:
            new_bytes, stats = scrubbed
            return new_bytes, {"desensitized": True, "mode": "docx_xml", "stats": stats, "deferred_chunk_scrub": False}

    # 兼容测试或文本化历史稿直接传入 UTF-8 内容
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix != ".pdf" and not data.startswith(b"\xd0\xcf\x11\xe0"):
        try:
            decoded = data.decode("utf-8")
            cleaned, stats = desensitize_history_text(decoded, user_meta)
            return cleaned.encode("utf-8"), {
                "desensitized": True,
                "mode": "utf8_text",
                "stats": stats,
                "deferred_chunk_scrub": False,
            }
        except UnicodeDecodeError:
            pass

    return data, {"desensitized": False, "mode": "deferred_chunk_scrub", "stats": {}, "deferred_chunk_scrub": True}


def _read_csv_rows(data: bytes) -> list[list[str]]:
    text = ""
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not text.strip():
        return []
    reader = csv.reader(io.StringIO(text))
    return [[cell.strip() for cell in row] for row in reader if any(cell.strip() for cell in row)]


def _col_index(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha()).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return max(0, idx - 1)


def _read_xlsx_rows(data: bytes) -> list[list[str]]:
    if data[:4] != b"PK\x03\x04":
        return []
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    try:
        with ZipFile(io.BytesIO(data), "r") as zf:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                s_root = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in s_root.findall(ns + "si"):
                    shared.append("".join(t.text or "" for t in si.iter(ns + "t")).strip())
            sheets = sorted(n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
            rows: list[list[str]] = []
            for sheet_name in sheets:
                w_root = ElementTree.fromstring(zf.read(sheet_name))
                for row_el in w_root.iter(ns + "row"):
                    cells_map: dict[int, str] = {}
                    max_c = -1
                    for c_el in row_el.findall(ns + "c"):
                        col_i = _col_index(c_el.attrib.get("r", ""))
                        if col_i == 0 and max_c >= 0 and not c_el.attrib.get("r"):
                            col_i = max_c + 1
                        max_c = max(max_c, col_i)
                        c_type = c_el.attrib.get("t", "")
                        v_el = c_el.find(ns + "v")
                        is_el = c_el.find(ns + "is")
                        val = ""
                        if c_type == "s" and v_el is not None and v_el.text:
                            try:
                                val = shared[int(v_el.text)]
                            except (ValueError, IndexError):
                                val = v_el.text
                        elif c_type == "inlineStr" and is_el is not None:
                            val = "".join(t.text or "" for t in is_el.iter(ns + "t"))
                        elif v_el is not None and v_el.text:
                            val = v_el.text
                        cells_map[col_i] = val.strip()
                    if max_c >= 0:
                        row = [cells_map.get(i, "") for i in range(max_c + 1)]
                        if any(row):
                            rows.append(row)
            return rows
    except (BadZipFile, ElementTree.ParseError, KeyError):
        return []


def _is_transposed_model_matrix(headers: list[str], body_rows: list[list[str]]) -> bool:
    """识别『参数项 | Model-A | Model-B | Model-C』横向并列对比参数表。"""
    if len(headers) < 3 or len(body_rows) < 2:
        return False
    col0 = headers[0].lower()
    if not any(k in col0 for k in _PARAM_COL0):
        return False
    model_cols = [h for h in headers[1:] if h and not any(k in h for k in ("备注", "说明", "单位"))]
    return len(model_cols) >= 2


def rows_to_header_bound_markdown(
    title: str, rows: list[list[str]], kind: str, user_meta: dict[str, str] | None = None,
) -> tuple[str, dict[str, str]]:
    """把二维表拆成每行/每型号自带完整表头的 Markdown 章节，并抽取型号/故障分类元数据。"""
    if len(rows) < 2:
        return "", {}
    headers = [h.strip() or f"列{i + 1}" for i, h in enumerate(rows[0])]
    body = [r for r in rows[1:] if any(c.strip() for c in r)]
    if not body:
        return "", {}

    meta_out: dict[str, str] = {}
    lines = [f"# {title}"]

    if kind in ("products", "materials") and _is_transposed_model_matrix(headers, body):
        models_found: list[str] = []
        param_label = headers[0]
        for col_idx in range(1, len(headers)):
            model_name = headers[col_idx].strip()
            if not model_name or model_name in ("备注", "说明", "单位"):
                continue
            models_found.append(model_name)
            lines.append("")
            lines.append(f"## 适用型号：{model_name}（{title}）")
            lines.append(f"- 适用型号：{model_name}")
            for r in body:
                p_name = r[0].strip() if len(r) > 0 else ""
                p_val = r[col_idx].strip() if col_idx < len(r) else ""
                if p_name and p_val:
                    lines.append(f"- {param_label}[{p_name}]：{p_val}")
        if models_found and not (user_meta or {}).get("model"):
            meta_out["model"] = ",".join(models_found[:10])
        return "\n".join(lines).strip() + "\n", meta_out

    model_col = next(
        (i for i, h in enumerate(headers) if any(k in h.lower() for k in _MODEL_HEADERS)),
        None,
    )
    fault_col = next(
        (i for i, h in enumerate(headers) if any(k in h.lower() for k in _FAULT_HEADERS)),
        None,
    )
    sev_col = next(
        (i for i, h in enumerate(headers) if any(k in h.lower() for k in _SEVERITY_HEADERS)),
        None,
    )

    models_seen: list[str] = []
    faults_seen: list[str] = []

    for row_no, r in enumerate(body, start=1):
        padded = [r[i].strip() if i < len(r) else "" for i in range(len(headers))]
        model_val = padded[model_col] if model_col is not None and padded[model_col] else str((user_meta or {}).get("model") or (user_meta or {}).get("product_model") or "").strip()
        fault_val = padded[fault_col] if fault_col is not None and padded[fault_col] else str((user_meta or {}).get("fault_category") or "").strip()
        sev_val = padded[sev_col] if sev_col is not None and padded[sev_col] else ""
        if model_val and model_val not in models_seen:
            models_seen.append(model_val)
        if fault_val and fault_val not in faults_seen:
            faults_seen.append(fault_val)

        primary = next((c for c in padded if c), f"记录{row_no}")
        tags = []
        if model_val:
            tags.append(f"型号:{model_val}")
        if fault_val:
            tags.append(f"分类:{fault_val}")
        if sev_val:
            tags.append(f"等级:{sev_val}")
        tag_prefix = f"[{' | '.join(tags)}] " if tags else ""
        lines.append("")
        lines.append(f"## {tag_prefix}第{row_no}条 {primary[:40]}")
        for h, val in zip(headers, padded):
            if val:
                lines.append(f"- {h}：{val}")

    if models_seen:
        key_name = "product_model" if kind == "fault_cases" else "model"
        if not (user_meta or {}).get(key_name):
            meta_out[key_name] = ",".join(models_seen[:10])
    if faults_seen and not (user_meta or {}).get("fault_category"):
        meta_out["fault_category"] = ",".join(faults_seen[:10])
    return "\n".join(lines).strip() + "\n", meta_out


DEFAULT_DOC_TYPE = {
    "manuals": "manual",
    "fault_cases": "fault_case",
    "products": "product_spec",
}


def preprocess_material_upload(
    filename: str,
    data: bytes,
    kind: str,
    content_type: str = "",
    user_meta: dict[str, str] | None = None,
) -> tuple[str, bytes, str, dict[str, str]]:
    """对资料库子库上传文件做带表头拆行与默认 doc_type 元数据补齐。"""
    meta_extra: dict[str, str] = {}
    if kind in DEFAULT_DOC_TYPE and not (user_meta or {}).get("doc_type"):
        meta_extra["doc_type"] = DEFAULT_DOC_TYPE[kind]

    stem = PurePosixPath(filename).stem or "material"
    suffix = PurePosixPath(filename).suffix.lower()

    rows: list[list[str]] = []
    if suffix == ".csv":
        rows = _read_csv_rows(data)
    elif suffix == ".xlsx":
        rows = _read_xlsx_rows(data)

    if rows and kind in ("products", "fault_cases", "materials"):
        md_text, extracted_meta = rows_to_header_bound_markdown(stem, rows, kind, user_meta)
        if md_text:
            meta_extra.update(extracted_meta)
            return f"{stem}.md", md_text.encode("utf-8"), "text/markdown", meta_extra

    return filename, data, content_type, meta_extra
