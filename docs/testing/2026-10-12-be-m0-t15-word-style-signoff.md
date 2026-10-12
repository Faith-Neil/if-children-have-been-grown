为什么有这个文件：记录QA对BE-M0-T15（Word导出默认版式，ISSUE-027）的独立核对与签署结论。

它解决什么问题：版式按用户确认的原文逐项核对，而不是只看交付文档；同时把只在LibreOffice上看过、Word/WPS待用户确认的边界写清楚。

# BE-M0-T15 Word 默认版式 QA 签署复核

ISSUE-013 / REV-M0-T10；关联[ISSUE-027](../../issues/ISSUE-027.md)。执行人成长测试QA；复核提交 `7428ec7`（首轮 `ca4afc4`）。环境：Linux、Python 3.13、LibreOffice（soffice headless）。只读复核，未改产品代码；**BE-M0-T15 保持 in-review**，done 需用户确认版式后由项目经理设置。

## 结论

- XML 结构核对：**通过**。四份导出均全部通过独立检查器。
- 视觉签收：**仅 LibreOffice**，Word 与 WPS 待用户确认（见文末两栏）。

## 版式原文核对

[docs/standards/word-default-style.md](../standards/word-default-style.md) 的六条与项目经理转发的用户确认原文逐条一致，只有措辞展开（“段前、段后都是”“封面不显示页码”“可以单独覆盖以上设置”），无数值或语义差异。

该文件另有一段原文中没有的英文补充：“黑体 is a user-approved substitute font used only when 方正小标宋 is not installed, and is NOT a Latin/Western fallback. 封面标题的 eastAsia、ascii 和 hAnsi 都写方正小标宋。”与 ca4afc4 的 M1 修复一致（三种属性都写方正小标宋）。注意：docx 内没有写入替代字体的机制，缺字时由 Word/WPS 自行替换，“黑体替代”只能靠客户机字体映射实现；该段为中文文档中的英文句，建议改为中文并由用户确认（Q3）。

## 检查器

`tests/backend/qa_docx_style_check.py`（非 pytest 用例，仅标准库 zipfile + xml.etree）。版式值按用户原文独立硬编码（二号22、三号16、小三15、四号14、小四12、五号10.5 磅；边距 1417/1417/1587/1474 缇 ±1；0.5 行 = beforeLines/afterLines 50；固定 28 磅 = line 560 exact；首行 2 字符 = firstLineChars 200），不读交付文档或 `docx_style.py`。属性按 docDefaults → basedOn 链 → 直接格式解析。逐项 PASS/FAIL，全部通过才退出 0。

覆盖：docDefaults 仿宋_GB2312；`settings.xml` 的 `updateFields`；A4 与两节边距；封面节无页码、正文节 `pgNumType start=1`、页脚 PAGE 域居中；页眉页脚宋体五号居中；内置 Heading 1～3、多级编号、大纲级别、对齐、加粗、0.5 行、三种字体属性；正文行距/段距/首行缩进/两端对齐/字体；封面标题（三种属性方正小标宋、二号、加粗、居中、CoverTitle 非标题且在封面节）；封面项目名（黑体三号居中、在封面节）；TOC 域 `\o "1-3"` 与宋体小四；表头 `tblHeader` + 加粗、数据行不加粗、宋体五号；V1 封面节 `w:type nextPage`；V2 一级标题不重复封面标题；V3 TocTitle“目录”非标题、TOC 域结果区占位文字。

自检：对 T15 之前的旧导出只过 4/15；人为删除 updateFields、首行缩进、tblHeader 后三项均 FAIL。

## 结果（7428ec7）

| 文件 | 来源 | 结果 |
|---|---|---|
| 样张（封面、目录、三级标题、正文、表格） | 应用导出函数 `build_docx` + `chapter_export_block`，合成数据 | 61/61 |
| 样张 `h1_align="left"` | 同上，覆盖一级标题为左对齐（styles 中 Heading1 jc=left） | 61/61 |
| 技术册 | `smoke_t06.py --output-dir`，真实 HTTP 导出 | 47/47 |
| 商务册 | 同上 | 47/47 |
| 服务承诺函 | 真实下载路由 `/sla/commitment/{id}` | 47/47 |

首轮 ca4afc4 的差异 M1（封面标题 ascii/hAnsi 为黑体）、M2（承诺函封面缺项目名称）、V1～V3 均已修复并由检查器覆盖。

样张入库：[`samples/2026-10-12-word-style-sample.docx`](samples/2026-10-12-word-style-sample.docx)。

复跑：后台 pytest 335 passed、2 skipped；治理检查通过；未改依赖文件。

## LibreOffice 渲染（仅本机，非 CI）

PNG 在 QA 机 `/workspace/qa-artifacts/word-7428ec7/`（未入库）：封面 `sample-page-1.png`、目录与标题正文表格 `sample-page-2.png`、承诺函 `sla-page-1.png`/`sla-page-2.png`、技术册 `tech-page-*.png`。封面单独成页且无页码，正文页码为 1；目录页显示“目录”和“右键更新域以生成目录”；LibreOffice 转换不更新域，目录条目未生成。

渲染机未安装方正小标宋、仿宋_GB2312、楷体_GB2312、黑体、宋体，均回退 Noto 字体，**字形、字宽与换行不代表 Word/WPS 实际效果**。

## 缺陷与观察

| 编号 | 现象 | 位置 | 严重程度 | 建议负责人 |
|---|---|---|---|---|
| Q1 | LibreOffice 中正文首行没有缩进：只写了 `w:firstLineChars="200"`，未同时写 `w:firstLine`（四号 14 磅×2 = 560 缇）。Word 认 firstLineChars；LibreOffice 忽略；WPS 待确认 | `docx_style.py` BodyText | P3 | 成长后端开发 |
| Q2 | 服务承诺函没有任何标题，仍插入“目录”和 TOC 域，更新后为空目录。原文未规定承诺函是否需要目录 | 承诺函导出 | P3（待用户决定） | 项目经理 / 成长后端开发 |
| Q3 | 版式原文文件中的英文补充段原文没有，且替代字体无法写入 docx | `docs/standards/word-default-style.md` | P3（文档） | 项目经理 |
| 说明 | V1 的 `w:type nextPage` 写在封面节 sectPr 中；按 OOXML，该元素描述的是本节如何开始，正文节缺省即为 nextPage，所以对 Word 实际无影响，LibreOffice 渲染中封面已单独成页 | — | 信息 | — |

## Word / WPS 待用户确认

| 核对项 | Word（待用户确认） | WPS（待用户确认） |
|---|---|---|
| 打开时是否提示更新域，更新后目录列出 1～3 级标题 | 待确认 | 待确认 |
| 目录页“右键更新域以生成目录”占位被替换 | 待确认 | 待确认 |
| 封面单独一页、无页码，正文从 1 开始底部居中 | 待确认 | 待确认 |
| 方正小标宋/仿宋_GB2312/楷体_GB2312 缺字时的替代效果（黑体替代） | 待确认 | 待确认 |
| 正文首行缩进 2 字符（Q1） | 待确认 | 待确认 |
| 多级编号 1 / 1.1 / 1.1.1 显示 | 待确认 | 待确认 |
| 表头跨页重复、加粗 | 待确认 | 待确认 |

## 复核二：Q1～Q3 修正（`034b184` + `f989af7`）

2026-10-12，在 `f989af7`（含 `034b184`）上复跑。只读复核，未改产品代码；**BE-M0-T15 仍为 in-review**，done 待用户在 Word/WPS 中确认样张后由项目经理设置。

检查器新增（原有项全部保留）：

- Q1：正文样式 `w:ind` 同时有 `firstLineChars="200"` 与 `firstLine="560"`；每个正文段落的有效缩进都是这两个值。
- Q2：文档没有 Heading 1～3 时，不得有“目录”段落、TOC 域和“更新域”占位文字；有标题时必须有 TocTitle 和 TOC 域，V3 与 TOC 字体检查只在有标题时执行。
- Q3：`--spec-doc` 核对规格末段：没有英文句子；写明 docx 不能指定替换字体、由 Word 或 WPS 决定、需安装方正小标宋；全文不再有旧英文句。

自检：7428ec7 的样张 Q1 两项 FAIL（62/64）；承诺函 Q1 两项与 Q2 三项 FAIL（42/47）；84a3fca 的规格 Q3 五项全 FAIL。

| 文件 | 来源 | 结果 |
|---|---|---|
| 样张 + 规格 Q3 | `build_docx` + `chapter_export_block`，合成数据；`--spec-doc` | 69/69 |
| 样张 `h1_align="left"` | 同上，styles 中 Heading1 `jc=left` | 64/64 |
| 技术册 | `smoke_t06.py --output-dir`，真实 HTTP 导出 | 50/50 |
| 商务册 | 同上 | 50/50 |
| 服务承诺函 | 真实下载路由，无标题 | 45/45（Q2 三项通过：无“目录”、无 TOC 域、无占位） |

样张已用本次导出覆盖 [`samples/2026-10-12-word-style-sample.docx`](samples/2026-10-12-word-style-sample.docx)（sha256 `22af2391…a233d`）。

LibreOffice 渲染 PNG 在 QA 机 `/workspace/qa-artifacts/word-034b184/`（未入库）：`sample-page-1.png`、`sample-page-2.png`、`sla-page-1.png`、`sla-page-2.png`、`tech-page-1.png`、`tech-page-2.png`。正文首行缩进两字符在 LibreOffice 中已可见（Q1 修复前不可见）；承诺函正文页只有正文和表格，没有“目录”页。字体仍回退 Noto，不代表 Word/WPS 效果。

复跑：后台 pytest 335 passed、2 skipped；治理检查通过（227 份 Markdown、366 项任务、28 项 Issue）。

结论：Q1～Q3 已修复，XML 核对通过，无新缺陷。上文“Word / WPS 待用户确认”表仍待用户在新样张上填写；Q2 承诺函无目录这一点也请用户一并确认。

## 后续：用户目视确认

2026-10-12 18:01，项目经理确认用户已在 Word/WPS 目视 OK，并把 BE-M0-T15 标为 done。ISSUE-027 标为 closed。上文签署结论与命令计数不改。未合入，未发布。
