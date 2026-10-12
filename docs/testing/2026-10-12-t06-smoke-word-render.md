为什么有这个文件：记录APP-M1-T06计划缺口1（贯通冒烟）与缺口3（Word视觉渲染）的实际执行结果。

它解决什么问题：给出可重跑的端到端命令，并首次留下Word页面渲染证据；不代表T06或正式Word版式已验收。

# T06贯通冒烟与Word渲染记录

日期2026-10-12；ISSUE-015 / REV-M0-T04；执行人成长测试QA；基于提交`db246b0`。环境：Linux、Python 3.13.5、LibreOffice 25.2.3.2、poppler pdftoppm 25.03.0。

## 1. 贯通冒烟 smoke_t06.py

命令（CI可用，自启空闲端口，仅标准库+requirements.txt，无新依赖）：

```
cd backend/bid-core && python smoke_t06.py [--output-dir <工作区外目录>]
```

结果：退出码0，12项检查全部通过。E1～E6复用`smoke_members.py`（内含`smoke_reference.py`）；E7实际核对：工作区项目名读回、导出记录在工作区列出、两册均下载、各册接口已提交正文出现在本册Word、私有草稿不在Word、另一册正文不混入、外部经理下载404、新提交后旧导出下载409。

局限：页面数据通过页面所用的同一接口（workspace/chapter）读回核对，未驱动浏览器GUI；模型为替身。

## 2. Word结构与视觉渲染

结构用`smoke_t06.inspect_docx`（标准库zip/XML，未引入python-docx，故无需ISSUE-016和`requirements-dev.txt`）。渲染：`soffice --headless --convert-to pdf`→`pdftoppm -r 80 -png`。**soffice只在QA机器上运行，不进入CI。**

| 文件 | 页 | 结论 |
|---|---|---|
| 技术册（[渲染](assets/t06-word-technical-render.png)） | 1页A4 | 内部稿标记、标题、章节名、正文可读，无缺字/重叠/裁切 |
| 商务册 | 1页A4 | 同上 |
| SLA承诺函（[渲染](assets/t06-word-sla-table-render.png)） | 1页A4 | 5列表格不越界，长单元格自动换行 |

结构事实：A4 11906×16838缇、四边1440缇；默认字体Calibri / 东亚“Microsoft YaHei”，hAnsi未设；样式仅Normal、Title；无Heading样式、无numbering.xml、无TOC域、无页眉页脚；两册无表格，SLA函表格设置了表头重复。渲染机无雅黑，中文回退Noto Sans CJK、Calibri回退Carlito，故字形不代表Windows/WPS实际效果。

10-10记录的“渲染失败”原因是当时Windows无soffice且Word转换失败；本次在Linux渲染成功，失败不再阻塞内部稿视觉检查。

## 3. 发现的缺陷

| 编号 | 现象 | 位置 | 严重度 | 建议负责人 |
|---|---|---|---|---|
| W1 | 无标题样式层级、多级编号、目录、页眉页脚（页码） | `backend/bid-core/icg_demo/adapters.py::build_docx` | P2（正式Word前必须） | 后端 |
| W2 | 章节名（如“技术方案”）用普通段落，与正文同字号，不可进导航/目录 | 同上 | P2 | 后端 |
| W3 | 表头行无加粗/底纹，与数据行难区分 | 同上（表格生成） | P3 | 后端 |
| W4 | 默认字体未设hAnsi，跨平台回退不一致；客户字体规范未定 | styles.xml | P3 | 后端+产品确认 |

剩余：Word/WPS实际打开复核、客户模板版式仍未做。T06保持in-progress。
