为什么有这个文件：记录工单 4（双库 RAG + 审计）实际改了什么。

它解决什么问题：钉死现网 `icg-history` / `icg-material`（单数）并强制节生成双库检索审计。

# TV-M0-T11 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T11](../tasks/TV-M0.md#tv-m0-t11) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-05 |
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| 代码解释 | [TV-M0-T11](../code/TV-M0-T11.md) |

## 实际变更

- 默认资料库后缀改为 `icg-material`；可用 `ICG_KB_DATASET_*` / `RAGFLOW_DATASET_*` 覆盖；查找兼认旧别名 `icg-materials`。
- `technical_rag.py`：节 Query、双库检索、审计；`write_volume` 强制检索并落 `technical_rag_audit`。
- 工作区暴露 `technical_kb`；编辑台缺库显性提示。
- 知识库角色：保留 data_admin/manager 细权限，避免三角色归一挡管控。

## 验收证据

- `pytest tests/backend/test_technical_rag.py tests/backend/test_kb_admin.py` → 16 passed。
- 未宣称：质量八条门禁、Figma UI、写作助手。

## 基线同步

TASK_BOARD / PROJECT_STATUS / DOCUMENT_INDEX / Issue 本轮已更新。
