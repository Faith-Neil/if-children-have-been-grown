为什么有这个文件：把 ISSUE-052 公司开通与账号归属拆成可验收任务卡。

它解决什么问题：避免只改代码不登记看板，或不经 QA/PD 就标 done。

# ADMIN-PROVISION：公司开通与账号归属

日期：2026-11-09。关联 [ISSUE-052](../../issues/ISSUE-052.md)。设计：[公司开通与账号归属设计](../superpowers/specs/2026-11-09-company-provisioning-design.md)。计划：[实现计划](../superpowers/plans/2026-11-09-company-provisioning.md)。

最高状态 in-review。不标 done。不合入 PR #8，除非人类 PM 另令。

<a id="admin-provision-t01"></a>

## ADMIN-PROVISION-T01 · 后端开通公司与可选强制改密

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-052](../../issues/ISSUE-052.md) |
| 依赖 | — |
| 完成时交付 | [docs/delivery/ADMIN-PROVISION-T01.md](../delivery/ADMIN-PROVISION-T01.md) |
| 代码解释 | [docs/code/ADMIN-PROVISION-T01.md](../code/ADMIN-PROVISION-T01.md) |

范围：`POST /api/v1/companies` 原子开通；`CreateUserRequest.must_change_password`；OpenAPI 同步；错误码 `COMPANY_NAME_DUPLICATED`。

<a id="admin-provision-t02"></a>

## ADMIN-PROVISION-T02 · 顶栏去公司名与新建公司弹窗

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-052](../../issues/ISSUE-052.md) |
| 依赖 | [ADMIN-PROVISION-T01](#admin-provision-t01) |
| 完成时交付 | [docs/delivery/ADMIN-PROVISION-T02.md](../delivery/ADMIN-PROVISION-T02.md) |
| 代码解释 | [docs/code/ADMIN-PROVISION-T02.md](../code/ADMIN-PROVISION-T02.md) |

范围：平台管理员顶栏不渲染公司名；公司管理「新建公司」同一弹窗。

<a id="admin-provision-t03"></a>

## ADMIN-PROVISION-T03 · 公司详情路由与加人

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-052](../../issues/ISSUE-052.md) |
| 依赖 | [ADMIN-PROVISION-T01](#admin-provision-t01)、[ADMIN-PROVISION-T02](#admin-provision-t02) |
| 完成时交付 | [docs/delivery/ADMIN-PROVISION-T03.md](../delivery/ADMIN-PROVISION-T03.md) |
| 代码解释 | [docs/code/ADMIN-PROVISION-T03.md](../code/ADMIN-PROVISION-T03.md) |

范围：`/admin/companies/:companyId`；用户列表与添加账号（平台可加管理员/成员，公司管理员仅成员）。

<a id="admin-provision-t04"></a>

## ADMIN-PROVISION-T04 · 项目与双库隔离回归

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-052](../../issues/ISSUE-052.md) |
| 依赖 | [ADMIN-PROVISION-T01](#admin-provision-t01) |
| 完成时交付 | [docs/delivery/ADMIN-PROVISION-T04.md](../delivery/ADMIN-PROVISION-T04.md) |
| 代码解释 | [docs/code/ADMIN-PROVISION-T04.md](../code/ADMIN-PROVISION-T04.md) |

范围：两公司项目互不可见；双库 `${company_id}::icg-history` / `icg-material` 不串库。

<a id="admin-rbac-platform-split"></a>

## ADMIN-RBAC-PLATFORM-SPLIT · 双管理员后台权限分家与纯净后台

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-056](../../issues/ISSUE-056.md) |
| 依赖 | 第 0 步后台 API RBAC 与租户隔离核查 |
| 来源 | 用户 2026-11-27 第 0/4 步要求 |
| 完成时交付 | `docs/delivery/ADMIN-RBAC-PLATFORM-SPLIT.md` |
| 代码解释 | `docs/code/ADMIN-RBAC-PLATFORM-SPLIT.md` |

范围：核查并收口 `AuditLogPage`、`UsersPage`、`CompanyManagePage`、`RagflowConfigModal`、`ModelConfigModal` 对应后端 API 的角色与 `company_id` 隔离；按平台管理员/公司管理员重构后台菜单与文案；公司管理员访问平台级接口 403，用户/审计严格本公司过滤；清除内部编号和研发黑话。

可验证验收：

- [ ] 公司管理员调平台级接口返回 403，跨租户查用户/日志不可见。
- [ ] 平台管理员与公司管理员菜单按用户指定集合分家。
- [ ] 后台页面无 A 编号、PRD 引文、StatusTag、租户 ID 等外露黑话。

<a id="admin-settings-cleanup"></a>

## ADMIN-SETTINGS-CLEANUP · 字典下线与公司设置/安全策略收口

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-056](../../issues/ISSUE-056.md) |
| 依赖 | 公司设置字段消费清单 |
| 来源 | 用户 2026-11-27 第 1/2 步要求 |
| 完成时交付 | `docs/delivery/ADMIN-SETTINGS-CLEANUP.md` |
| 代码解释 | `docs/code/ADMIN-SETTINGS-CLEANUP.md` |

范围：删除字典配置页及后端死写接口；清理 `custom_settings`、`loop_max_rounds`、`model_review_enabled`、`dup_min_chars`、`dup_history_months`；隐藏锁心跳/自动保存技术参数；保留划词、粘贴、解析阈值；将密码策略、登录锁定、会话超时收口平台管理员全局配置并在后端强制。

可验证验收：

- [ ] 空壳字段不可配置且无前端入口；前端类型检查通过。
- [ ] 密码修改弱口令、连续失败锁定、会话过期均由后端强制并有单测。
- [ ] OpenAPI 契约同步且无漂移。

<a id="admin-model-config-cleanup"></a>

## ADMIN-MODEL-CONFIG-CLEANUP · 平台模型配置真实生效项收口

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 2小时 |
| 关联 Issue | [ISSUE-056](../../issues/ISSUE-056.md) |
| 依赖 | `openai_model.py` 分档参数核实 |
| 来源 | 用户 2026-11-27 第 3 步要求 |
| 完成时交付 | `docs/delivery/ADMIN-MODEL-CONFIG-CLEANUP.md` |
| 代码解释 | `docs/code/ADMIN-MODEL-CONFIG-CLEANUP.md` |

范围：核实 `ModelCallProfile` 对 `max_tokens`、`timeout_seconds`、`temperature` 的真实覆盖；精简模型配置表单与 API 展示，仅保留真实生效的 base_url、model、api_key、is_local、连通性测试与场景绑定；分档上限改只读说明或移除；消除与 A-05 重复。

可验证验收：

- [ ] 管理员不再被假配置项误导。
- [ ] 连通性测试与场景绑定保持可用，主链路生成回归通过。

<a id="admin-taskcenter-jobs"></a>

## ADMIN-TASKCENTER-JOBS · 生成/解析任务中心链路核实补齐

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 3小时 |
| 关联 Issue | [ISSUE-056](../../issues/ISSUE-056.md) |
| 依赖 | `volume_sessions` / `recoverable_jobs` / `demo_job` 现状核查 |
| 来源 | 用户 2026-11-27 第 0/5 步要求 |
| 完成时交付 | `docs/delivery/ADMIN-TASKCENTER-JOBS.md` |
| 代码解释 | `docs/code/ADMIN-TASKCENTER-JOBS.md` |

范围：核查解析、章节生成、技术卷生成是否以独立 `job_type` 写入 `demo_job`；补齐缺失持久化与状态同步；确认 `TaskCenterDrawer` 展示进度、耗时、报错、取消与重试；补任务监管单测。

可验证验收：

- [ ] 技术卷生成任务写入 `demo_job` 且类型为 `technical_volume`。
- [ ] 任务中心显示进度、耗时、报错、取消和可重试入口。
- [ ] 聚焦任务测试通过。
