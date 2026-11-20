为什么有这个文件：记录 ADMIN-PROVISION-T01 实际交付。

它解决什么问题：避免把开通公司 API 写成已合入或已上线。

# ADMIN-PROVISION-T01：后端开通公司与可选强制改密

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | ADMIN-PROVISION-T01 |
| 代码解释 | [代码说明](../code/ADMIN-PROVISION-T01.md) |
| 验收 | `pytest tests/backend/test_company_provisioning.py tests/backend/test_password_login.py` 14 passed；`export_openapi.py --check` OK。未在真实 MySQL / 浏览器验收 |
| 项目进度 | in-review。建议 PM 待 QA/PD 后标 done。不合并 PR #8 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-11-09。Issue：[ISSUE-052](../../issues/ISSUE-052.md)。
- 分支：`feat/iss-047-technical-volume-mvp`。
- 合入 / 发布：未合入，未发布。

## 完成内容

新增 `POST /api/v1/companies`；`must_change_password` 可入参；登记 `COMPANY_NAME_DUPLICATED`；同步 `spec/openapi/demo-v1.json`。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 实施视图未改章节正文；能力对齐 §5.10.1，见 Issue |
| ROADMAP | 管理面补齐，见 PROJECT_STATUS 短注 |
| ARCHITECTURE | API 面增量见代码说明，未改骨架总图 |
| Issue / TASK_BOARD | 已同步 |
| DOCUMENT_INDEX | 已登记 |
