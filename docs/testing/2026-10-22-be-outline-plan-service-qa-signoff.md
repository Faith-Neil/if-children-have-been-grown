为什么有这个文件：记录QA对BE-OUTLINE-PLAN-SERVICE（大纲写作方案服务与持久化接口）的独立复验与签署结论。

它解决什么问题：不轻信开发自报结果，亲手执行大纲写作方案专属单测套件、分册结构化大纲树读取、核心红线门禁（星号条款★与废标条款对应章节绝对禁止标记为“不适用”，强行拦截抛出 400 INVALID_ACTION）、三级数据权限与分册隔离（403 FORBIDDEN）、单事务原子版本号递增（chapter.revision += 1, project.revision += 1）、分册批量确认、以及纯内存多态透明降级与全量测试回归。

# BE-OUTLINE-PLAN-SERVICE 大纲写作方案服务与持久化接口独立复测与 QA 签署

- 被验任务：[BE-OUTLINE-PLAN-SERVICE](../delivery/BE-OUTLINE-PLAN-SERVICE.md) · 大纲写作方案服务与持久化接口
- 关联审查任务：REV-M0-T64
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md) / [ISSUE-018](../../issues/ISSUE-018.md)
- 关联交付：[BE-OUTLINE-PLAN-SERVICE 交付](../delivery/BE-OUTLINE-PLAN-SERVICE.md)、[代码解释](../code/BE-OUTLINE-PLAN-SERVICE.md)
- 依赖基线：BE-WORKFLOW-JOB-PERSISTENCE（工作流持久化）、BE-8ROLES-RBAC（八角色权限）
- 被验核心文件：
  - `backend/bid-core/icg_demo/outline_service.py`
  - `backend/bid-core/icg_demo/workflow.py`
  - `backend/bid-core/icg_demo/project_access.py`
  - `tests/backend/test_outline_plan_service.py`
  - `tests/backend/test_outline_contract_draft.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**BE-OUTLINE-PLAN-SERVICE 保持 in-review，严禁标 done；关联 Issue 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 结构化大纲树生成与元数据设计 | 通过 | `get_outline_plan` 产出包含完整层级的大纲树，节点丰富挂接 `section_number`、`chapter_type`（推导或人工设定为 specialized/general/system）、`value_added_reason`、`has_asterisk`、`has_disqualified`、`is_mandatory`、`assignee_name`、`confirmation_status` 与 `revision`；支持按 `technical` / `business` 分册过滤 |
| AC-02 【核心门禁红线】星号/废标条款绝对禁止标记不适用 | 通过 | `confirm_outline_plan` 实行强合规门禁校验：若目标章节关联了星号条款（★）或废标/一票否决条款，任何试图设置 `applicable=False` 或 `action="mark_not_applicable"` 的调用均被底层强行拦截，抛出 `OutlinePlanError(status=400, code="INVALID_ACTION", message="章节包含星号条款（★）或废标条款，绝对禁止标记为“不适用”。")` |
| AC-03 三级数据权限与分册隔离红线 | 通过 | 严格落实八角色与分册负责人边界：① 系统只读角色（group_admin、viewer、auditor、platform_admin）及项目只读成员拦截 403 `FORBIDDEN`；② 分册负责人仅限确认所管辖分册的大纲方案，跨分册操作拦截 403 `FORBIDDEN`；③ 项目负责人（lead）放行全局所有分册 |
| AC-04 单事务内原子版本递增与历史快照 | 通过 | `confirm_outline_plan` 在单一事务边界内执行：章节当前版本号原子递增（`chapter.revision += 1`）、追加版本快照至 `chapter.versions`（记录变更原因）、项目版本同步自增（`project.revision += 1`），且同步更新工作流元数据 `workflow["outline_plans"]` |
| AC-05 分册批量确认能力 | 通过 | 支持传入 `volume_id` 与批量计划，原子流转整册所有适用章节的大纲方案确认状态至 `confirmed`，大幅提升复杂标书编制编排效率 |
| AC-06 纯内存模式透明降级多态 | 通过 | 未配置 `ICG_DATABASE_URL` 时，服务完全基于 `MemoryRepository` 纯内存自适应运行，保障 CI 与纯离线测试 0 外部数据库依赖纯洁性 |
| AC-07 OpenAPI 契约与冻结错误码一致性 | 通过 | 契约与权限单测全部通过，143 个冻结错误码保持 100% 吻合，`OutlinePlanError` 针对性复用 400 `INVALID_ACTION`，无任何错误码表破坏 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 大纲写作方案专属单测套件 | `python -m pytest tests/backend/test_outline_plan_service.py -v` | **6 passed, 0 failed** (大纲树读取、红线门禁、分册权限、原子版本自增、批量确认全绿) | 0.09s |
| 大纲契约单测套件 | `python -m pytest tests/backend/test_outline_contract_draft.py -v` | **6 passed, 0 failed** (契约草案对齐) | 0.09s |
| 契约与八角色权限单测 | `python -m pytest tests/backend/test_error_idempotency.py tests/backend/test_eight_roles_access.py -v` | **19 passed, 0 failed** (143 冻结错误码完备) | 5.34s |
| 后端全量测试回归套件 | `python -m pytest tests/backend/ -rs` | **538 passed, 37 skipped, 0 failed** (包含新增 6 项大纲方案专属单测) | 339.20s |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **前后端对“星号与废标条款禁止不适用”的双重闭环锁死**：前端在下拉控件置灰禁用（`disabled: true`），后端在 `confirm_outline_plan` 中深度扫描条款关联并硬拦截抛出 400 `INVALID_ACTION`，彻底切断了任何通过 API 绕过前端直接修改的漏洞可能。
2. **分册级与项目级的权限矩阵协同严谨**：精准区分了技术分册负责人、商务分册负责人与项目负责人的权责范围，杜绝了跨分册篡改方案的协同混乱。
3. **原子双版本自增机制**：每次大纲确认同时推进章节 revision 与项目 revision，为后续在线协同与编辑锁的心跳续约提供了强一致版本基准。

## 签署状态

BE-OUTLINE-PLAN-SERVICE 保持 **in-review**，**严禁标 done**。
