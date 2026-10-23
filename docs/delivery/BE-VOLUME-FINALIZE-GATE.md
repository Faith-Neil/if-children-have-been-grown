为什么有这个文件：记录 BE-VOLUME-FINALIZE-GATE 分册定稿状态机与前置检查门禁的交付事实、测试证据与验收记录。

它解决什么问题：作为质量门禁依据，证明 PRD §5.8.5 分册定稿闭环与安全门禁已在 backend/bid-core/icg/ 上下文分包中落地、严格权限拦截（编写人 403、跨租户 404）、前置双门禁（章节锁定/正文提交 409、blocker 缺陷 409 CHECK_BLOCKER_EXISTS）均已建立完备测试断言且全量绿灯，OpenAPI 契约保持一致，并将任务标为 in-review，绝不私自标 done。

# BE-VOLUME-FINALIZE-GATE：分册定稿状态机与前置检查门禁交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-VOLUME-FINALIZE-GATE |
| 代码解释 | [BE-VOLUME-FINALIZE-GATE](../code/BE-VOLUME-FINALIZE-GATE.md) |
| 验收 | 2026-10-23：分册定稿状态机与前置检查门禁已在 `backend/bid-core/icg/` 分包架构中完全实现；成功支持仅项目负责人（project_lead）与公司管理员（company_admin）触发定稿；编写人触发严格拦截返回 403 FORBIDDEN；跨公司访问严格隔离返回 404 NOT_FOUND；前置门禁 1（章节排他锁定拦截 409 LOCK_HELD、正文空缺拦截 409 CHAPTER_CONTENT_EMPTY）与前置门禁 2（未消解 blocker 缺陷拦截 409 CHECK_BLOCKER_EXISTS）均生效并通过验证；持久化标记 is_finalized=True 并记录定稿人与时间戳；先解锁后修改生命周期（POST unlock）闭环完备；专属单测 10 项全绿，全量回归与 OpenAPI 契约一致性通过 |
| 项目进度 | 任务看板是准绳。本卡状态流转为 in-review，严禁私自标 done，等待项目经理复审验收 |
<!-- task-delivery:end -->

## 关联与状态
- **关联 Issue**：[ISSUE-006](../../issues/ISSUE-006.md)、[ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-005](../../issues/ISSUE-005.md)
- **依赖任务**：[BE-CHECKS-EXPORT-ALIGN](../tasks/BE-M0.md#be-checks-export-align)、[BE-M0-T15](../tasks/BE-M0.md#be-m0-t15)
- **状态流转**：推进至 `in-review`。严格遵守规范，绝不私自将任务看板标为 `done`，绝不私自关闭 Issue。

## 完成内容与变更清单
1. **分包架构与领域状态机实现 (`VolumeFinalizeMixin`)**：
   - 在 `backend/bid-core/icg/domain/volume_finalize.py` 中实现独立的分册定稿状态机领域服务，杜绝向 `icg_demo` 根目录平铺巨石业务；
   - 包含定稿流转（`finalize_volume`）、解锁流转（`unlock_volume`）、单分册定稿状态查询（`get_volume_status`）与全分册状态列表查询（`list_volumes_status`）。
2. **严格权限与租户隔离**：
   - 仅当前公司的项目负责人（`project_lead`，兼容历史 `manager`）或公司管理员（`company_admin`）允许定稿与解锁；
   - 编写人（`bid_writer` / `editor`）或普通只读角色触发定稿时严格拦截返回 HTTP 403 `FORBIDDEN`；
   - 跨公司账号访问其他公司项目触发定稿时严格返回 HTTP 404 `NOT_FOUND`，保证租户间数据强隔离。
3. **前置双安全门禁拦截**：
   - **门禁 1（章节完整性与并发锁）**：检查分册内所有章节必须已提交正式版本正文且当前未处于排他租约锁定状态。若章节被锁定，拦截返回 409 `LOCK_HELD`；若章节缺少正式正文，拦截返回 409 `CHAPTER_CONTENT_EMPTY`；
   - **门禁 2（缺陷阻断项）**：检查分册不存在未消解的 `severity == "blocker"` 缺陷（废标红线与关键星号条款未有效响应或缺企业资质证据），拦截返回 409 `CHECK_BLOCKER_EXISTS`。
4. **状态流转与解锁全生命周期**：
   - 门禁通过后，持久化写入 `is_finalized = True`，记录定稿人 ID `finalized_by` 与 ISO 时间戳 `finalized_at`；
   - 遵循 PRD §5.8.5「定稿后修改：先解锁，记录原因」规范，提供 `POST /api/v1/projects/{project_id}/volumes/{volume_id}/unlock` 端点，强制要求原因说明，记录 `unlocked_by`、`unlocked_at` 与 `unlock_reason`，回退 `is_finalized = False`。
5. **API 路由与 OpenAPI 契约收敛**：
   - 新端点统一注册在 `/api/v1` 前缀下（严禁接入 `/api/demo`）；
   - 执行 `python backend/bid-core/export_openapi.py` 同步最新 OpenAPI 契约至 `spec/openapi/demo-v1.json`，契约一致性校验通过。

## 变更文件清单
- `backend/bid-core/icg/domain/volume_finalize.py`: 新增分册定稿状态机领域服务、门禁核验与领域异常。
- `backend/bid-core/icg/domain/__init__.py`: 导出 `VolumeFinalizeMixin` 与门禁核对函数。
- `backend/bid-core/icg/domain/workflow_orchestrator.py`: `WorkflowService` 混入继承 `VolumeFinalizeMixin`，在 `_authorize` 中强化分册操作权限判定。
- `backend/bid-core/icg/api/volumes.py`: 新增 `/api/v1` 路由，定义定稿、解锁与状态查询接口与契约模型。
- `backend/bid-core/icg/api/__init__.py`: 导出 `include_volume_routes` 及相关 Pydantic 契约。
- `backend/bid-core/icg_demo/main.py`: 装配挂载 `include_volume_routes`。
- `spec/openapi/demo-v1.json`: 同步生成的分册定稿与状态查询契约。
- `tests/backend/test_volume_finalize_gate.py`: 10 项端到端单测用例。
- `docs/code/BE-VOLUME-FINALIZE-GATE.md`: 技术实现说明文档。
- `docs/delivery/BE-VOLUME-FINALIZE-GATE.md`: 交付报告与测试凭据文档。
- `docs/tasks/BE-M0.md`: 登记 `BE-VOLUME-FINALIZE-GATE` 任务定义。
- `docs/TASK_BOARD.md`: 看板更新本卡为 `in-review`。

## 自动化测试与验收结果
- **专属门禁测试 (`tests/backend/test_volume_finalize_gate.py`)**：
  - `test_volume_finalize_normal_by_project_lead` PASSED [10%]
  - `test_volume_finalize_normal_by_company_admin` PASSED [20%]
  - `test_volume_finalize_blocked_for_writer_with_403` PASSED [30%]
  - `test_volume_finalize_cross_tenant_isolation_with_404` PASSED [40%]
  - `test_volume_finalize_invalid_volume_returns_404` PASSED [50%]
  - `test_volume_finalize_gate_blocks_when_chapter_is_locked` PASSED [60%]
  - `test_volume_finalize_gate_blocks_when_chapter_content_empty` PASSED [70%]
  - `test_volume_finalize_gate_blocks_when_blocker_defects_exist` PASSED [80%]
  - `test_volume_unlock_lifecycle_and_reason_requirement` PASSED [90%]
  - `test_volume_finalize_in_non_demo_eight_roles_environment` PASSED [100%]
  - 运行命令：`pytest tests/backend/test_volume_finalize_gate.py -v`
  - 结果：**10 passed in 7.63s**
- **关联回归套件测试**：
  - `pytest tests/backend/test_checks_export_blocker_gate.py tests/backend/test_api_v1_convergence.py tests/backend/test_eight_roles_access.py`
  - 结果：**18 passed in 4.31s**
- **关演示与生产冒烟回归**：
  - `pytest tests/backend/test_smoke_non_demo_pipeline.py`
  - 结果：**3 passed in 2.04s**
- **OpenAPI 契约一致性校验**：
  - `python backend/bid-core/export_openapi.py --check`
  - 结果：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **项目治理检查**：
  - `node scripts/check-project-governance.cjs`
  - 结果：通过。

## 限制与未完成事项
- 严格遵守开发规范，本卡状态推进至 `in-review`，绝不私自标为 `done`。
- 定稿后的状态机目前已完全就绪，后续第三阶段将对接递交版导出的强一致校验（两册均定稿方可进入递交签章包）。
