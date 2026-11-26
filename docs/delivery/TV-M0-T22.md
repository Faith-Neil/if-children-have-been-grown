为什么有这个文件：记录技术服务方案招标文件解析表格保真与跨页续表切分优化交付。

# TV-M0-T22 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 代码 | [TV-M0-T22](../code/TV-M0-T22.md) |

## 实际变更

- DeepDOC HTML 表格与本地 DOCX 表格还原为标准 Markdown 表格（保留表头行），不再压成普通文本行。
- 跨页续表识别：页末未闭合的表格块在下一页续切时自动补齐表头行，避免跨页评分表的得分细则与表头拆散。
- `technical_model_extract` 扫描窗口带 `[第 P 页]` 页锚与重叠区，切块避开表格行边界，强制模型输出精确页码、原文 `quote` 与本标 `chunk_id` 溯源锚点；T/S/R 三张清单每条均可回溯到原文位置。

## 验收证据

- `tests/backend/test_tv_m0_t22_table_parse.py`：2 passed（跨页表格保真、表头承接与溯源锚点）。
- 全套后端回归：本任务相关解析用例无新增失败（存量失败清单见交付末尾说明）。

## 局限

- 普通文字版 PDF 默认仍走本地 `pypdf`；内网 RAGFlow 可用时才优先 DeepDOC。
- 只用模型替身与合成数据验证；未连内网 Qwen / RAGFlow 做真实文件验收。

## 同步

PRD、ROADMAP、ARCHITECTURE：无改动，按 [ISSUE-054](../../issues/ISSUE-054.md) 的 Wave 1 设计执行。
