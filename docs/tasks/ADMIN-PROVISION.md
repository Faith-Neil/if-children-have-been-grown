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
