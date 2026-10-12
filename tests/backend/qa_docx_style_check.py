# 为什么有这个文件：QA 独立核对 Word 导出是否符合已批准的默认版式（ISSUE-027 / BE-M0-T15），非 pytest 用例。
# 它解决什么问题：只用标准库打开 docx，按 docDefaults → basedOn 链 → 直接格式解析有效属性，逐项给出 PASS/FAIL。
"""Run: python tests/backend/qa_docx_style_check.py FILE.docx [--kind sample|chapter|sla]
退出码 0 仅当所有检查项通过。kind 决定哪些项必需（chapter 无表格；sla 无标题/目录要求按实际导出判定）。"""
import argparse
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
q = lambda tag: f"{{{W}}}{tag}"
val = lambda el, attr="val": None if el is None else el.get(q(attr))

# 用户确认的 Word 默认版式原文（项目经理转发，后台将入库为 docs/standards/word-default-style.md）。
# 本表按原文独立硬编码，不读取 BE-M0-T15 交付文档或 docx_style.py。
# 字号：二号=22pt 三号=16 小三=15 四号=14 小四=12 五号=10.5；w:sz 为半磅。
PT = {"二号": 44, "三号": 32, "小三": 30, "四号": 28, "小四": 24, "五号": 21}
CM = lambda cm: cm * 1440 / 2.54
SPEC = {
    "margins": {"top": CM(2.5), "bottom": CM(2.5), "left": CM(2.8), "right": CM(2.6)},  # 1417/1417/1587.4/1474，容差 ±1
    "page": (11906, 16838),
    "CoverTitle": dict(ea="方正小标宋", ascii="方正小标宋", hansi="方正小标宋", sz=PT["二号"], jc=("center",), bold=True),
    "CoverProject": dict(ea="黑体", ascii="黑体", hansi="黑体", sz=PT["三号"], jc=("center",)),
    "Heading1": dict(ea="黑体", ascii="黑体", hansi="黑体", sz=PT["三号"], jc=("center", "left"), lvl=0),
    "Heading2": dict(ea="楷体_GB2312", ascii="楷体_GB2312", hansi="楷体_GB2312", sz=PT["小三"], jc=("left",), bold=True, lvl=1),
    "Heading3": dict(ea="仿宋_GB2312", ascii="仿宋_GB2312", hansi="仿宋_GB2312", sz=PT["四号"], jc=("left",), bold=True, lvl=2),
    "BodyText": dict(ea="仿宋_GB2312", ascii="仿宋_GB2312", hansi="仿宋_GB2312", sz=PT["四号"], jc=("both",), bold=False),
    "body_spacing": dict(line="560", lineRule="exact", before="0", after="0", firstLineChars="200"),
    "heading_spacing": dict(beforeLines="50", afterLines="50"),
    "table": dict(ea="宋体", ascii="宋体", hansi="宋体", sz=PT["五号"]),
    "headerfooter": dict(ea="宋体", ascii="宋体", hansi="宋体", sz=PT["五号"], jc="center"),
    "toc": dict(ea="宋体", ascii="宋体", hansi="宋体", sz=PT["小四"]),
    "defaults": dict(ea="仿宋_GB2312", ascii="仿宋_GB2312", hansi="仿宋_GB2312"),
}

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))


def merge(base, over):
    """按子元素标签合并属性：后者覆盖前者。返回 {tag: {attr: value}}。"""
    out = {k: dict(v) for k, v in base.items()}
    if over is None:
        return out
    for child in over:
        out.setdefault(child.tag, {}).update(child.attrib)
        if child.tag == q("b") and not child.attrib:
            out[child.tag][q("val")] = "true"
    return out


class Styles:
    def __init__(self, root):
        self.by_id = {s.get(q("styleId")): s for s in root.iter(q("style"))}
        dd = root.find(q("docDefaults"))
        self.rdef = dd.find(f"{q('rPrDefault')}/{q('rPr')}") if dd is not None else None
        self.pdef = dd.find(f"{q('pPrDefault')}/{q('pPr')}") if dd is not None else None
        self.default_para = next((s.get(q("styleId")) for s in self.by_id.values()
                                  if s.get(q("type")) == "paragraph" and s.get(q("default")) in ("1", "true")), None)

    def chain(self, sid):
        seen, out = set(), []
        while sid and sid in self.by_id and sid not in seen:
            seen.add(sid); out.append(self.by_id[sid])
            sid = val(self.by_id[sid].find(q("basedOn")))
        return list(reversed(out))

    def rpr(self, sid, direct=None):
        props = merge({}, self.rdef)
        for st in self.chain(sid or self.default_para):
            props = merge(props, st.find(q("rPr")))
        return merge(props, direct)

    def ppr(self, sid, direct=None):
        props = merge({}, self.pdef)
        for st in self.chain(sid or self.default_para):
            props = merge(props, st.find(q("pPr")))
        return merge(props, direct)


def fonts(props):
    f = props.get(q("rFonts"), {})
    return f.get(q("eastAsia")), f.get(q("ascii")), f.get(q("hAnsi"))


def bold(props):
    b = props.get(q("b"))
    return b is not None and b.get(q("val"), "true") not in ("0", "false")


def size(props):
    s = props.get(q("sz"), {}).get(q("val"))
    return int(s) if s else None


def run_ok(props, spec):
    ea, a, h = fonts(props)
    probs = []
    if ea != spec["ea"]: probs.append(f"eastAsia={ea}")
    if "ascii" in spec and a != spec["ascii"]: probs.append(f"ascii={a}")
    if "hansi" in spec and h != spec["hansi"]: probs.append(f"hAnsi={h}")
    if size(props) != spec["sz"]: probs.append(f"sz={size(props)}")
    if "bold" in spec and bold(props) != spec["bold"]: probs.append(f"bold={bold(props)}")
    return probs


def para_style(p):
    return val(p.find(f"{q('pPr')}/{q('pStyle')}"))


def para_text(p):
    return "".join(t.text or "" for t in p.iter(q("t")))


def runs(p):
    return [r for r in p.iter(q("r")) if r.find(q("t")) is not None and (r.find(q("t")).text or "")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx"); ap.add_argument("--kind", default="sample", choices=["sample", "chapter", "sla"])
    args = ap.parse_args()
    z = ZipFile(args.docx)
    names = set(z.namelist())
    doc = ET.fromstring(z.read("word/document.xml"))
    styles = Styles(ET.fromstring(z.read("word/styles.xml")))
    rels = {}
    if "word/_rels/document.xml.rels" in names:
        for rel in ET.fromstring(z.read("word/_rels/document.xml.rels")):
            rels[rel.get("Id")] = "word/" + rel.get("Target")
    body = doc.find(q("body"))
    paras = list(body.iter(q("p")))
    print(f"== {args.docx} ({args.kind})")

    # docDefaults
    ea, a, h = fonts(merge({}, styles.rdef))
    d = SPEC["defaults"]
    check("docDefaults rFonts 仿宋_GB2312（eastAsia/ascii/hAnsi）", (ea, a, h) == (d["ea"], d["ascii"], d["hansi"]), (ea, a, h))

    # settings updateFields
    st = ET.fromstring(z.read("word/settings.xml")) if "word/settings.xml" in names else None
    uf = st.find(q("updateFields")) if st is not None else None
    check("settings.xml 含 <w:updateFields w:val=\"true\"/>", uf is not None and val(uf) in ("true", "1"),
          "settings.xml 缺失" if st is None else "无 updateFields")

    # sections
    sects = [s for s in doc.iter(q("sectPr"))]
    check("至少两节（封面节 + 正文节）", len(sects) >= 2, len(sects))
    for i, s in enumerate(sects):
        m = s.find(q("pgMar")); sz = s.find(q("pgSz"))
        got = {k: int(m.get(q(k))) for k in ("top", "bottom", "left", "right")} if m is not None else None
        check(f"第{i+1}节 页边距 上2.5/下2.5/左2.8/右2.6 cm（±1 缇）", got is not None and
              all(abs(got[k] - SPEC["margins"][k]) <= 1 for k in got), got)
        check(f"第{i+1}节 A4", sz is not None and (int(sz.get(q("w"))), int(sz.get(q("h")))) == SPEC["page"])

    def footer_xml(sect):
        ref = next((f for f in sect.findall(q("footerReference")) if f.get(q("type")) in ("default", None)), None)
        path = rels.get(ref.get(f"{{{R}}}id")) if ref is not None else None
        return ET.fromstring(z.read(path)) if path in names else None

    def has_page_field(x):
        if x is None: return False
        instr = "".join(t.text or "" for t in x.iter(q("instrText")))
        simple = [f.get(q("instr")) or "" for f in x.iter(q("fldSimple"))]
        return "PAGE" in instr or any("PAGE" in s for s in simple)

    if len(sects) >= 2:
        cover, last = sects[0], sects[-1]
        check("封面节页脚无页码", not has_page_field(footer_xml(cover)))
        pg = last.find(q("pgNumType"))
        check("正文节页码从 1 开始（pgNumType start=1）", pg is not None and pg.get(q("start")) == "1")
        f = footer_xml(last)
        check("正文节页脚含 PAGE 域", has_page_field(f))
        if f is not None:
            fp = f.find(q("p"))
            jc = styles.ppr(para_style(fp), fp.find(q("pPr"))).get(q("jc"), {}).get(q("val"))
            check("页脚居中", jc == "center", jc)
            rs = [r for r in fp.iter(q("r"))]
            hf = SPEC["headerfooter"]
            probs = [p for r in rs for p in run_ok(styles.rpr(para_style(fp), r.find(q("rPr"))), hf)]
            check("页脚字体 宋体 五号 10.5 磅（三种字体属性）", not probs, probs[:3])
    hdr_ref = sects[-1].find(q("headerReference")) if sects else None
    if hdr_ref is not None and rels.get(hdr_ref.get(f"{{{R}}}id")) in names:
        hx = ET.fromstring(z.read(rels[hdr_ref.get(f"{{{R}}}id")]))
        hp = hx.find(q("p"))
        jc = styles.ppr(para_style(hp), hp.find(q("pPr"))).get(q("jc"), {}).get(q("val"))
        probs = [p for r in runs(hp) for p in run_ok(styles.rpr(para_style(hp), r.find(q("rPr"))), SPEC["headerfooter"])]
        check("页眉居中、宋体 五号 10.5 磅（三种字体属性）", jc == "center" and not probs, (jc, probs[:3]))

    # built-in headings + numbering
    for sid, name in (("Heading1", "heading 1"), ("Heading2", "heading 2"), ("Heading3", "heading 3")):
        s = styles.by_id.get(sid)
        check(f"内置样式 {sid}（name={name}）存在", s is not None and val(s.find(q("name"))) == name)
    numbering = ET.fromstring(z.read("word/numbering.xml")) if "word/numbering.xml" in names else None

    def multilevel_for(numid):
        if numbering is None: return None
        num = next((n for n in numbering.iter(q("num")) if n.get(q("numId")) == numid), None)
        if num is None: return None
        aid = val(num.find(q("abstractNumId")))
        return next((a for a in numbering.iter(q("abstractNum")) if a.get(q("abstractNumId")) == aid), None)

    used = {sid: [p for p in paras if para_style(p) == sid] for sid in ("Heading1", "Heading2", "Heading3", "BodyText", "CoverTitle", "CoverProject")}
    need_levels = ("Heading1", "Heading2", "Heading3") if args.kind == "sample" else ("Heading1",) if args.kind == "chapter" else ()
    for sid in ("Heading1", "Heading2", "Heading3"):
        spec = SPEC[sid]
        if not used[sid]:
            check(f"{sid} 段落存在", sid not in need_levels, "文档中没有该级标题")
            continue
        p = used[sid][0]
        pp = styles.ppr(sid, p.find(q("pPr")))
        # numPr 是嵌套元素，按 basedOn 链与直接格式单独解析
        npr = None
        for st_el in styles.chain(sid):
            found = st_el.find(f"{q('pPr')}/{q('numPr')}")
            npr = found if found is not None else npr
        if p.find(f"{q('pPr')}/{q('numPr')}") is not None:
            npr = p.find(f"{q('pPr')}/{q('numPr')}")
        lvl = val(npr.find(q("ilvl"))) if npr is not None else None
        nid = val(npr.find(q("numId"))) if npr is not None else None
        ab = multilevel_for(nid)
        mlt = val(ab.find(q("multiLevelType"))) if ab is not None else None
        check(f"{sid} 接多级编号（ilvl={spec['lvl']}，multilevel）", lvl == str(spec["lvl"]) and mlt == "multilevel"
              and ab is not None and any(l.get(q("ilvl")) == str(spec["lvl"]) for l in ab.findall(q("lvl"))), (lvl, nid, mlt))
        ol = pp.get(q("outlineLvl"), {}).get(q("val"))
        check(f"{sid} 大纲级别 {spec['lvl']}", ol == str(spec["lvl"]), ol)
        jc = pp.get(q("jc"), {}).get(q("val"))
        check(f"{sid} 对齐 {'/'.join(spec['jc'])}", jc in spec["jc"], jc)
        sp = pp.get(q("spacing"), {})
        check(f"{sid} 段前段后 0.5 行", all(sp.get(q(k)) == v for k, v in SPEC["heading_spacing"].items()), sp)
        probs = [x for r in runs(p) for x in run_ok(styles.rpr(sid, r.find(q("rPr"))), spec)]
        check(f"{sid} 字体 {spec['ea']} {spec['sz']/2:g} 磅{' 加粗' if spec.get('bold') else ''}（三种字体属性）", not probs, probs[:4])
        if "bold" in spec:
            rb = [bold(styles.rpr(sid, r.find(q("rPr")))) for r in runs(p)]
            check(f"{sid} 加粗={spec['bold']}", rb and all(b == spec["bold"] for b in rb), rb)

    # body
    if used["BodyText"]:
        p = used["BodyText"][0]
        pp = styles.ppr("BodyText", p.find(q("pPr")))
        sp, ind = pp.get(q("spacing"), {}), pp.get(q("ind"), {})
        b = SPEC["body_spacing"]
        check("正文 固定行距 28 磅、段前段后 0", sp.get(q("line")) == b["line"] and sp.get(q("lineRule")) == b["lineRule"]
              and sp.get(q("before"), "0") == "0" and sp.get(q("after"), "0") == "0", sp)
        check("正文 首行缩进 2 字符", ind.get(q("firstLineChars")) == b["firstLineChars"], ind)
        check("正文 两端对齐", pp.get(q("jc"), {}).get(q("val")) == "both")
        probs = [x for p2 in used["BodyText"] for r in runs(p2) for x in run_ok(styles.rpr("BodyText", r.find(q("rPr"))), SPEC["BodyText"])]
        check("正文 仿宋_GB2312 14 磅 不加粗（三种字体属性）", not probs, probs[:4])
    else:
        check("正文段落存在", args.kind == "sla", "无 BodyText 段落")

    # cover
    if used["CoverTitle"]:
        p = used["CoverTitle"][0]
        pp = styles.ppr("CoverTitle", p.find(q("pPr")))
        probs = [x for r in runs(p) for x in run_ok(styles.rpr("CoverTitle", r.find(q("rPr"))), SPEC["CoverTitle"])]
        ea_probs = [x for x in probs if not x.startswith(("ascii", "hAnsi"))]
        check("封面标题 eastAsia 方正小标宋、二号 22 磅、加粗", not ea_probs, ea_probs[:4])
        latin = [x for x in probs if x.startswith(("ascii", "hAnsi"))]
        check("封面标题 ascii/hAnsi 也为方正小标宋（原文只写方正小标宋）", not latin, latin[:2])
        check("封面标题 居中", pp.get(q("jc"), {}).get(q("val")) == "center")
        is_heading = (q("outlineLvl") in pp) or any(s.get(q("styleId")).startswith("Heading") for s in styles.chain("CoverTitle")) \
            or p.find(f"{q('pPr')}/{q('numPr')}") is not None
        check("封面标题 用 CoverTitle 且不是标题、不进目录（无 outlineLvl/numPr、不基于 Heading）", not is_heading)
        cover_idx = paras.index(p)
        first_sect_idx = next((i for i, x in enumerate(paras) if x.find(f"{q('pPr')}/{q('sectPr')}") is not None), None)
        check("封面标题位于封面节", first_sect_idx is not None and cover_idx <= first_sect_idx)
    else:
        check("封面标题（CoverTitle）存在", False)
    check("封面项目名称段落（CoverProject）存在", bool(used["CoverProject"]), "封面没有项目名称")
    if used["CoverProject"]:
        p = used["CoverProject"][0]
        probs = [x for r in runs(p) for x in run_ok(styles.rpr("CoverProject", r.find(q("rPr"))), SPEC["CoverProject"])]
        check("封面项目名 黑体 三号 16 磅", not probs, probs[:4])
        jc = styles.ppr("CoverProject", p.find(q("pPr"))).get(q("jc"), {}).get(q("val"))
        check("封面项目名 居中", jc == "center", jc)
        first_sect_idx = next((i for i, x in enumerate(paras) if x.find(f"{q('pPr')}/{q('sectPr')}") is not None), -1)
        check("封面项目名位于封面节", paras.index(p) <= first_sect_idx)

    # V1：封面单独成页
    if len(sects) >= 2:
        ct = val(sects[0].find(q("type")))
        check("V1 封面节 sectPr 含 <w:type w:val=\"nextPage\"/>", ct == "nextPage", ct)
        bt = val(sects[-1].find(q("type")))
        check("V1 正文节分节类型为下一页（nextPage 或缺省，缺省即 nextPage）", bt in (None, "nextPage"), bt)

    def not_heading(sid, p):
        pp = styles.ppr(sid, p.find(q("pPr")))
        chain_heading = any((s.get(q("styleId")) or "").startswith("Heading") for s in styles.chain(sid))
        numbered = p.find(f"{q('pPr')}/{q('numPr')}") is not None or any(
            s.find(f"{q('pPr')}/{q('numPr')}") is not None for s in styles.chain(sid))
        return q("outlineLvl") not in pp and not chain_heading and not numbered

    # V2：封面标题不再重复成一级标题
    cover_texts = {para_text(p).strip() for p in used["CoverTitle"]}
    dup = [para_text(p) for p in used["Heading1"] if para_text(p).strip() in cover_texts]
    check("V2 一级标题不重复封面标题", not dup, dup[:2])

    # V3：目录标题与占位文字
    tt = [p for p in paras if para_style(p) == "TocTitle"]
    check("V3 目录标题段落（TocTitle）存在且文字为“目录”", tt and para_text(tt[0]).strip() == "目录",
          [para_text(p) for p in tt])
    if tt:
        check("V3 目录标题不是标题、不进目录（无 outlineLvl/numPr、不基于 Heading）", not_heading("TocTitle", tt[0]))
        probs = [x for r in runs(tt[0]) for x in run_ok(styles.rpr("TocTitle", r.find(q("rPr"))), SPEC["toc"])]
        check("V3 目录标题 宋体 小四", not probs, probs[:3])

    def field_result(p_list):
        state, text = None, ""
        for p in p_list:
            for r in p.iter(q("r")):
                fc = r.find(q("fldChar"))
                it = r.find(q("instrText"))
                if fc is not None:
                    kind = fc.get(q("fldCharType"))
                    if kind == "begin": state = "begin"
                    elif kind == "separate" and state == "toc": state = "result"
                    elif kind == "end" and state in ("toc", "result"): return text
                elif it is not None and state == "begin" and "TOC" in (it.text or ""):
                    state = "toc"
                elif state == "result":
                    text += "".join(x.text or "" for x in r.iter(q("t")))
        return text
    placeholder = field_result(paras)
    check("V3 TOC 域结果区有占位文字", bool(placeholder.strip()), repr(placeholder))

    # TOC
    instr = " ".join(t.text or "" for t in body.iter(q("instrText")))
    simple = " ".join(f.get(q("instr")) or "" for f in body.iter(q("fldSimple")))
    toc_ok = "TOC" in instr + simple and '\\o "1-3"' in instr + simple
    check("TOC 域存在（\\o \"1-3\"）", toc_ok or args.kind == "sla", instr[:80])
    if toc_ok:
        tp = next(p for p in paras if any("TOC" in (t.text or "") for t in p.iter(q("instrText"))))
        rp = [r for r in tp.iter(q("r")) if r.find(q("instrText")) is not None]
        probs = [x for r in rp for x in run_ok(styles.rpr(para_style(tp), r.find(q("rPr"))), SPEC["toc"])]
        check("目录 宋体 小四 12 磅（三种字体属性）", not probs, probs[:3])
        first_sect_idx = next((i for i, x in enumerate(paras) if x.find(f"{q('pPr')}/{q('sectPr')}") is not None), -1)
        check("目录位于正文节（封面之后）", paras.index(tp) > first_sect_idx)

    # tables
    tables = list(body.iter(q("tbl")))
    if not tables:
        check("表格存在", args.kind == "chapter", "无表格")
    for ti, t in enumerate(tables):
        rows = t.findall(q("tr"))
        hdr = rows[0]
        check(f"表{ti+1} 首行 w:tblHeader", hdr.find(f"{q('trPr')}/{q('tblHeader')}") is not None)

        def row_runs(row):
            return [(p, r) for p in row.iter(q("p")) for r in runs(p)]
        hb = [bold(styles.rpr(para_style(p), r.find(q("rPr")))) for p, r in row_runs(hdr)]
        check(f"表{ti+1} 表头行全部加粗（w:b）", hb and all(hb), hb)
        db = [bold(styles.rpr(para_style(p), r.find(q("rPr")))) for row in rows[1:] for p, r in row_runs(row)]
        check(f"表{ti+1} 数据行不加粗", not any(db), sum(db))
        check(f"表{ti+1} 数据行无 tblHeader", all(r.find(f"{q('trPr')}/{q('tblHeader')}") is None for r in rows[1:]))
        probs = [x for row in rows for p, r in row_runs(row)
                 for x in run_ok(styles.rpr(para_style(p), r.find(q("rPr"))), SPEC["table"])]
        check(f"表{ti+1} 宋体 10.5 磅（三种字体属性）", not probs, probs[:3])

    failed = [n for n, ok in results if not ok]
    print(f"== {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
