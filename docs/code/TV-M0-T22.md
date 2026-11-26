为什么有这个文件：解释 TV-M0-T22 招标解析表格保真、跨页续表与溯源锚点的代码。

# TV-M0-T22 代码说明

| 文件 | 说明 |
|---|---|
| [tender_remote.py](../../backend/bid-core/icg/domain/tender_remote.py) | DeepDOC 返回的 HTML 表格转 Markdown 表（保留表头行）；页末未闭合表格与次页续表检测并补表头 |
| [parsing.py](../../backend/bid-core/icg/domain/parsing.py) | 本地 DOCX 表格还原为 Markdown 行；内网 RAGFlow 可用时技术标 PDF 优先 DeepDOC |
| [technical_model_extract.py](../../backend/bid-core/icg/domain/technical_model_extract.py) | 扫描窗口携带 `[第 P 页]` 页锚与重叠区，切块避开表格行边界；强制输出精确页码、quote、chunk_id |
| [technical_digest.py](../../backend/bid-core/icg/domain/technical_digest.py) | T/S/R 清单条目保留页码、原文摘录与本标 chunk_id 溯源字段 |
| [test_tv_m0_t22_table_parse.py](../../tests/backend/test_tv_m0_t22_table_parse.py) | 跨页表格保真、表头承接、溯源锚点断言 |
