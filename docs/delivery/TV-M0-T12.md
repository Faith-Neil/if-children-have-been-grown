为什么有这个文件：记录工单 5（一键全文 + 质量八条）实际改了什么。

它解决什么问题：生成后按八条抽检标「需核对」，可见警告、允许导出、不恢复矩阵闸门。

# TV-M0-T12 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T12](../tasks/TV-M0.md#tv-m0-t12) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-05 |
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| 代码解释 | [TV-M0-T12](../code/TV-M0-T12.md) |

## 实际变更

- 新增 `technical_quality.py`：八条规则/抽检清单；未达标写 `warning` 与 `review_titles`。
- `write_volume` 全文/按节生成后跑抽检，节末补「需要核对」，落 `technical_quality`；任务消息带警告。
- 工作区暴露 `technical_quality`，并与 `technical_needs_review` 合并；OpenAPI 同步 `technical_kb` / `technical_quality`。
- 编辑台、导出页可见警告；目录树节标「需核对」。不挡内部稿导出，不恢复矩阵确认闸门。

## 验收证据

- `pytest tests/backend/test_technical_quality.py tests/backend/test_technical_rag.py` → 7 passed。
- `python backend/bid-core/export_openapi.py --check` → OK。
- 未宣称：Figma 编辑台精简 UI（工单 6）、写作助手双模式（工单 7）。

## 基线同步

TASK_BOARD / PROJECT_STATUS / DOCUMENT_INDEX / Issue 本轮已更新。
