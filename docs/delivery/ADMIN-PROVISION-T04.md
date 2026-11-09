为什么有这个文件：记录 ADMIN-PROVISION-T04 隔离回归交付。

它解决什么问题：避免把假 RAGFlow 测绿写成生产双库已隔离验收完毕。

# ADMIN-PROVISION-T04：项目与双库隔离回归

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | ADMIN-PROVISION-T04 |
| 代码解释 | [代码说明](../code/ADMIN-PROVISION-T04.md) |
| 验收 | `pytest tests/backend/test_company_provisioning.py tests/backend/test_kb_company_dataset_isolation.py` 9 passed（假 RAGFlow）。未连真实 RAGFlow |
| 项目进度 | in-review。建议 PM 待 QA/PD 后标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-11-09。Issue：[ISSUE-052](../../issues/ISSUE-052.md)。
- 合入 / 发布：未合入，未发布。

## 完成内容

跨公司项目 404；两公司 ensure 后数据集全名为各自 `${company_id}::icg-history` / `icg-material`，dataset id 互不交叉。
