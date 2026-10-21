为什么有这个文件：记录QA对BE-M0-T07（operationId 规范化检查与修正确认）的独立复验与签署结论。

它解决什么问题：相对开发人员自报，亲手独立核实 OpenAPI 契约与运行时所有操作的 operationId，确认全量 72 个操作（运行时 70 个 + 冻结大纲草案 2 个）全局唯一、符合 lowerCamelCase，且无 `_api_` 冗余前缀和下划线，关键契约测试全量通过。

# BE-M0-T07 operationId 规范化检查 QA 签署（REV-M0-T39）

- 被验任务：[BE-M0-T07](../tasks/BE-M0.md) · operationId 检查
- 关联 Issue：[ISSUE-005](../../issues/ISSUE-005.md) 卡片 (f)
- 关联交付：[BE-M0-T07 交付](../delivery/BE-M0-T07.md)、[代码解释](../code/BE-M0-T07.md)
- 被验核心文件：`backend/bid-core/icg_demo/main.py`、`backend/bid-core/icg_demo/workflow_routes.py`、`spec/openapi/demo-v1.json`、`tests/backend/test_operation_ids.py`
- 复验环境：Windows, Python 3.12.9
- 结论：**通过 (PASS)**。**BE-M0-T07、ISSUE-005 均保持 in-review / in-progress，严禁标 done / closed**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 运行时 operationId 驼峰与无前缀 | 通过 | `test_running_app_all_operation_ids_valid_camel_case_and_no_api_prefix`：运行态 70 个操作均非空、匹配 `^[a-z][A-Za-z0-9]*$`，无 `_api_` 冗余前缀，无下划线 |
| AC-02 运行时 operationId 全局唯一性 | 通过 | `test_running_app_operation_ids_are_globally_unique`：运行态所有 operationId 查重结果为空，确保 API SDK 生成无命名冲突 |
| AC-03 全量契约 operationId 合规与唯一 | 通过 | `test_spec_demo_v1_json_all_operation_ids_valid_and_globally_unique`：`spec/openapi/demo-v1.json` 全量 72 个操作（含 2 个冻结大纲计划草案）均为标准 lowerCamelCase，全局无重复 |
| AC-04 核心与已知端点命名兼容性 | 通过 | `test_well_known_operation_ids`：`getSession`、`listProjects`、`createProject`、`exportVolume`、`startGeneration`、`getJob`、`streamJobEvents`、`cancelJob`、`acquireChapterLock` 等核心标识符保持完全一致 |
| AC-05 运行态契约与静态规范严格一致 | 通过 | `test_implemented_contract_matches_running_schema`：运行态 `create_app().openapi()` 与静态规范 `implemented_contract(spec)` 严格全等 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| BE-M0-T07 专项 | `python -m pytest tests/backend/test_operation_ids.py -v -rs` | **5 passed** | 4.65s |
| 72 个 Operation 脚本独立深度核验 | `python -c "..."` (遍历 spec/openapi/demo-v1.json) | **Total: 72, Unique: 72, Duplicates: 0, Bad camelCase: 0, Has _api_: 0, Has _: 0** | 0.8s |
| 关键契约联合回归 | `python -m pytest tests/backend/test_operation_ids.py tests/backend/test_error_idempotency.py tests/backend/test_recoverable_jobs.py tests/backend/test_v1_lease.py tests/backend/test_evidence_mount_contract.py tests/backend/test_export_snapshot.py -v -rs` | **26 passed** (契约测试全绿) | 19.88s |
| 治理一致性核查 | `node scripts/check-project-governance.cjs` | **检查通过** (347 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与边界提示

1. **冻结大纲草案保留**：契约中保留了 `getOutlinePlan` 与 `confirmOutlinePlan` 两个冻结扩展草案（标记为 `x-contract-drafts`），运行时尚未实现路由，属于预期行为，与此前契约冻结决策保持一致。
2. **错误码与扩展保留**：OpenAPI 规范中已冻结的 143 个错误码枚举以及扩展字段（`x-issue-033`, `EvidenceMountFields` 等）未受到任何扰动或破坏。
3. **旧接口统一计划**：旧 `/api` 错误体与幂等规范依然按计划留待 BE-M0-T09 / ISSUE-021，本卡未引入额外非规范改造。

## 签署状态

BE-M0-T07、ISSUE-005 均保持 **in-review / in-progress**，**严禁标 done / closed**。
