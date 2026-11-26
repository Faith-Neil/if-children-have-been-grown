为什么有这个文件：登记双管理员权限隔离、后台模块精简与任务中心核实的工程变更。

它解决什么问题：后台存在只写不读字典孤岛、公司设置空壳字段、模型假配置项、平台/公司管理员权限边界不清，以及审计与任务中心链路需要核实收口。

# ISSUE-056：双管理员权限隔离、后台模块精简与任务中心核实

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-056 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | in-progress |
| 登记日期 | 2026-11-27 |
| 最后更新日期 | 2026-11-27 |
| revision | admin-rbac-cleanup-r1 |
| 关联 Task | [ADMIN-RBAC-PLATFORM-SPLIT](../docs/tasks/ADMIN-PROVISION.md#admin-rbac-platform-split)、[ADMIN-SETTINGS-CLEANUP](../docs/tasks/ADMIN-PROVISION.md#admin-settings-cleanup)、[ADMIN-MODEL-CONFIG-CLEANUP](../docs/tasks/ADMIN-PROVISION.md#admin-model-config-cleanup)、[ADMIN-TASKCENTER-JOBS](../docs/tasks/ADMIN-PROVISION.md#admin-taskcenter-jobs) |
| 关联 PR | 未创建 |
| 本地验收 | 未执行 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 待补：对应 `docs/delivery/` |
| 代码 / 流程解释 | 待补：对应 `docs/code/` |
| 验证记录 | 待补：RBAC、密码策略、任务中心与聚焦回归 |

## 现象与证据

用户 2026-11-27 明确六项要求：先复核后台五个管理入口的 API 角色与租户隔离、生成任务在 `demo_job` 与任务中心的链路；随后下线 A-03 字典配置页、收口 A-05 公司设置并后端强制平台安全策略、清理模型设置假开关、按平台管理员/公司管理员重构后台导航与纯净文案，最终补 RBAC/密码策略/任务中心单测并提 PR 不合并。

## 影响与分流

- 影响范围：后台管理前端、用户/公司/设置/模型/RAGFlow/审计 API、会话安全策略、任务中心、OpenAPI 与前端类型。
- 不改变投标主链路业务语义；不删除仍被编辑器或解析链路真实消费的配置。
- 公司管理员严格限制本公司；平台级配置仅平台管理员可写。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| [ADMIN-RBAC-PLATFORM-SPLIT](../docs/tasks/ADMIN-PROVISION.md#admin-rbac-platform-split) | 后台 API RBAC/租户审计、导航分家、纯净文案、审计日志后端过滤 | `api/users.py`、`api/companies.py`、审计与前端 admin/app | 公司管理员调平台接口 403，跨租户用户/日志不可见 | in-progress |
| [ADMIN-SETTINGS-CLEANUP](../docs/tasks/ADMIN-PROVISION.md#admin-settings-cleanup) | 下线字典配置、清理公司设置空壳字段、平台安全策略后端强制 | `dict_config*`、`company_settings.py`、登录/改密逻辑 | 空壳字段不可写，密码/锁定/会话策略单测通过 | ready |
| [ADMIN-MODEL-CONFIG-CLEANUP](../docs/tasks/ADMIN-PROVISION.md#admin-model-config-cleanup) | 清理模型假配置项与重复入口 | `ModelConfigModal.tsx`、模型配置 API/存储 | 仅保留真实生效配置或只读说明，契约一致 | ready |
| [ADMIN-TASKCENTER-JOBS](../docs/tasks/ADMIN-PROVISION.md#admin-taskcenter-jobs) | 核实并补齐生成/解析任务 demo_job 与任务中心链路 | `technical_volume_sessions.py`、`parse_jobs.py`、`TaskCenterDrawer.tsx` | 进度、耗时、报错、取消、重试可验 | ready |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 第 0 步两项核查结论写入 PR：后台 API 权限/租户矩阵、任务中心链路 | 未执行 |
| AC-02 | 字典配置页与后端写接口下线，状态文案收口常量模块，无引用报错 | 未执行 |
| AC-03 | 公司设置删除空壳字段/隐藏技术参数，保留真实生效业务配置 | 未执行 |
| AC-04 | 密码策略、登录锁定、会话过期由后端强制，单测通过 | 未执行 |
| AC-05 | 模型配置只保留真实生效项，假开关/重复入口清除 | 未执行 |
| AC-06 | 平台管理员与公司管理员后台菜单分家，后端同步 403 与租户过滤 | 未执行 |
| AC-07 | 任务中心生成/解析任务链路单测通过；聚焦回归、OpenAPI、前端类型、治理检查通过 | 未执行 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 待评估：后台范围与权限边界变化，需在交付中核对是否属产品范围收口 | `docs/PRD.md` | admin-rbac-cleanup-r1 / ISSUE-056 / 2026-11-27 | 待处理 |
| ROADMAP | 待评估：上线前后台收口，不改变主业务里程碑 | `docs/ROADMAP.md` | 同上 | 待处理 |
| ARCHITECTURE | 有影响：后台权限边界、设置消费面、任务持久化与审计接口变化 | `docs/ARCHITECTURE.md` | 同上 | 待处理 |
| TASK_BOARD | 有影响：新增四张任务卡 | `docs/TASK_BOARD.md` | 同上 | 已登记 |
| PROJECT_STATUS | 有影响：记录本轮后台收口开工状态 | `docs/PROJECT_STATUS.md` | 同上 | 待同步 |
| DOCUMENT_INDEX | 有影响：新增 Issue、任务交付与代码说明条目 | `docs/DOCUMENT_INDEX.md` | 同上 | 待同步 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-11-27 | admin-rbac-cleanup-r1 / in-progress | 已从最新 main 切出 `feat/iss-056-admin-rbac-cleanup` 并登记 Issue/任务；下一步执行第 0 步核查 | 用户本轮指令 |

## 本地验收与后续合入发布

- 本地验收结论与日期：待执行。
- 验证方式、通过及失败项、未覆盖范围：待填写。
- 六份基线同步与互链复核：待执行。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
