为什么有这个文件：记录工单 2（动态目录唯一确认）实际改了什么与验收证据。

它解决什么问题：避免仍把六段/单章硬模板或矩阵确认当成生成前置。

# TV-M0-T09 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T09](../tasks/TV-M0.md#tv-m0-t09) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-05 |
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done；本 Agent 不标 done |
| 代码解释 | [TV-M0-T09](../code/TV-M0-T09.md) |

## 实际变更

- `technical_outline.arrange`：按规范编号树 + 评分主观分叶子动态排 1～4 级；删除 `BUCKET_ORDER` 六块硬编码。
- `technical_volume`：生成只认目录确认；去掉矩阵确认闸门与六段完整性硬校验；按叶子顺序写节。
- 前端目录编辑支持一至四级；「开始生成」；去掉 historyBlocked。
- OpenAPI：`outline_headings.level` 改为 1～4。

## 验收证据

- `python -m pytest tests/backend/test_technical_sources.py -q` → 18 passed。
- `python backend/bid-core/export_openapi.py --check` → OK。
- 未宣称：覆盖视图 UI（工单 3）、双库现网名写作（工单 4）、质量八条门禁（工单 5）、编辑台 Figma UI（工单 6）、写作助手（工单 7）。

## 项目进度

工单 2 实现已到 in-review。下一张：工单 3 矩阵后台化 + 覆盖视图。分支仍不合 main。

## 基线同步

| 基线 | impact | 同步 |
|---|---|---|
| PRD | 有影响（最短路径） | 仍以决定为准 |
| ROADMAP | 有影响 | 工单 2 完成实现、待签 |
| ARCHITECTURE | 有影响 | 目录 1～4 级与唯一闸门见决定/本交付 |
| TASK_BOARD / PROJECT_STATUS / DOCUMENT_INDEX / Issue | 有影响 | 本轮已更新 |
| 参考原文 | 无影响 | 不改 |
