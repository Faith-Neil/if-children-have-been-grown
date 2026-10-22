为什么有这个文件：记录QA对字段元数据服务 getFieldMetadata（APP-M2-T005 / T006 前置支持，REV-M0-T45）的独立复测与签署结论。

它解决什么问题：不轻信后端自报结果，亲手执行字段元数据专项契约测试、operationId 唯一性与规范测试、错误码与幂等冻结套件；全面核验 401 UNAUTHENTICATED 未认证拦截、404 NOT_FOUND 未知分类处理、四大核心业务分类（project, tender, kb_record, sla）及其别名容错解析、多角色账号访问权限，以及 OpenAPI spec demo-v1.json 契约一致性。

# 字段元数据服务 getFieldMetadata 独立复测与 QA 签署（REV-M0-T45）

- 被验任务：字段元数据服务 `getFieldMetadata`（APP-M2-T005 前置支持）
- 关联审查任务：REV-M0-T45
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md) / [ISSUE-005](../../issues/ISSUE-005.md)
- 被验核心文件：`backend/bid-core/icg_demo/field_metadata.py`、`tests/backend/test_field_metadata.py`、`spec/openapi/demo-v1.json`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**相关卡片保持 in-review，严禁标 done**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 401 未认证拦截与标准错误体 | 通过 | `test_field_metadata_unauthenticated_returns_401`：不携带 Token 或携带无效 Token 时，接口强制拦截并返回 401 `UNAUTHENTICATED`；响应体包含 `traceId` 且与响应头 `X-Request-ID` 一致 |
| AC-02 404 未知分类错误拦截 | 通过 | `test_nonexistent_category_returns_404`：请求未知分类（如 `unknown_finance_category`）时，正确返回 404 `NOT_FOUND`，提示“未找到该分类的字段元数据”，响应包含 `traceId` |
| AC-03 四大核心业务分类完整性 | 通过 | `test_get_field_metadata_for_all_supported_categories`：覆盖 `project`（投标项目，含必填/editable/starred/badge/align right 等）、`tender`（招标要求，含资格/废标/置信度/原文摘录 cite 等）、`kb_record`（企业资料，含来源分级/受限资料/有效期/证件掩码 masked 等）、`sla`（服务承诺，含指标分组/招标要求值/我方承诺值/超出承诺预警 badge 等） |
| AC-04 分类别名平滑容错映射 | 通过 | `test_field_metadata_category_aliases`：验证 `bid_project`/`projects` -> `project`；`tender_requirement`/`requirement`/`tenders` -> `tender`；`library`/`kb`/`records` -> `kb_record`；`project_sla`/`sla_value`/`sla_template` -> `sla` 均可正确解析返回对应规范分类 |
| AC-05 多角色账号访问权限一致性 | 通过 | `test_permission_access_across_roles`：`alpha-manager`（负责人）、`alpha-editor`（编写人）、`alpha-viewer`（只读人）、`beta-manager`（跨公司用户）均能平稳读取字段元数据，保证前端表单/表格组件不受角色阻塞 |
| AC-06 字段属性结构与枚举约束 | 通过 | `test_field_metadata_structure_and_constraints`：所有返回字段项均包含 `field_key`、`label`、`data_type`、`required`、`editable`、`align`、`render_type`、`filterable`、`sortable`、`is_starred`、`is_sensitive`，枚举 options 结构完备且 `fields` 与 `items` 严格等价（双字段兼容） |
| AC-07 OpenAPI 契约与 operationId 规范 | 通过 | `test_operation_ids.py`：`/api/v1/metadata/fields/{category}` 路由显式声明 `operationId="getFieldMetadata"`，遵循 lowerCamelCase，全局唯一无冲突，在 `spec/openapi/demo-v1.json` 中定义完整 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 字段元数据专属测试 | `python -m pytest tests/backend/test_field_metadata.py -v -rs` | **6 passed, 0 failed** | 3.65s |
| operationId 契约与唯一性 | `python -m pytest tests/backend/test_operation_ids.py -v -rs` | **5 passed, 0 failed** (72 个 operationId 严格唯一) | 3.59s |
| 错误码与幂等冻结套件 | `python -m pytest tests/backend/test_error_idempotency.py -v -rs` | **9 passed, 0 failed** (143 冻结错误码保持一致) | 5.12s |
| 后端全量回归 (离线) | `python -m pytest tests/backend/ -m "not mysql" -rs` | **468 passed, 5 skipped, 12 deselected** (0 failure) | 331.14s |

## 签署状态

字段元数据服务相关支持卡片保持 **in-review**，**严禁标 done**。
