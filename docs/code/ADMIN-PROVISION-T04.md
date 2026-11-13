为什么有这个文件：解释隔离回归测试落点。

它解决什么问题：说明本卡以测试锁行为主，未改 RAG 管道 DSL。

# ADMIN-PROVISION-T04 代码说明

- `tests/backend/test_company_provisioning.py`：`test_two_provisioned_companies_cannot_see_each_others_projects`。
- `tests/backend/test_kb_company_dataset_isolation.py`：全名约定与双公司 ensure。
- 运行时命名仍由 `knowledge_base.dataset_full_name` / `create_pipeline_dataset` 的 `${company_id}::` 前缀保证。
