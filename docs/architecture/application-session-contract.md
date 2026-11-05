为什么有这个文件：让页面和后台共同约定当前账号、导航及资源权限的可信读取方式。

它解决什么问题：避免页面凭登录时的旧角色或自己传入的公司参数决定访问范围。

# 应用会话与导航契约

维护日期：2026-11-04；版本：application-foundation-3（ISSUE-048 三角色）。关联 ISSUE-009 / WP-6 / ISSUE-048。会话身份规则是本契约的主体。参考原文 PRD v1.8 的八角色不改写。活动会话改为三个登录角色。实际接口说明从后台代码自动化导出到 `spec/openapi/demo-v1.json`。

## 当前阶段入口

`GET /api/v1/session`，操作名`getSession`。Bearer从后台现有会话读取当前账号；没有请求正文，不接受客户端角色、用户ID或公司范围。可选`project_id`只选择要核验的项目，仍按后台公司及项目成员权限核验。

响应：演示身份模式、当前账号、公司范围、原PRD角色映射、服务端允许的导航入口和动作、默认首页，以及会话续期是否可用。选项目时返回最小项目权限，不带正文、证据内容或任何人的草稿。当前演示会话没有真实到期/续期机制，明确返回`expires_at: null`、`renew_supported: false`，不能假设OIDC已接入。

系统支持两种运行与认证模式，可通过环境变量与配置解耦：
1. **演示模式（`VITE_DEMO=1`）**：支持演示账号快速登录。正式会话仍返回 `auth_mode: "authenticated"` 与 `role_mode: "rbac-3roles"`。
2. **正式认证模式（`VITE_DEMO` 未设置或为 0）**：登录走 Access Token。会话返回 `auth_mode: "authenticated"` 与 `role_mode: "rbac-3roles"`。生产环境（`ICG_REQUIRE_MYSQL=1`）阻断演示账号登录。
3. **三个登录角色**：单源在 `frontend/web/src/shared/roles.ts` 与 `backend/bid-core/icg/domain/project_access.py`。登录角色是 `platform_admin`、`company_admin`、`member`。旧登录角色和别名收成 `member`。项目负责人是项目成员身份。
4. **枚举**：`role_mode` 为 `rbac-3roles`。`ApplicationRole` 为上述三个登录角色。账号上保存的历史角色码仍可出现在 `user.role`，`primary_role` 使用归一化后的登录角色。

| 返回字段 | 契约取值与说明 |
|---|---|
| `auth_mode` | `"synthetic-demo" | "authenticated"`，标识是合成演示会话还是正式凭据认证会话 |
| `role_mode` | `"rbac-3roles"`，三个登录角色 |
| `user` | 包含 `id`, `name`, `company_id`, `role`, `roles`, `primary_role`；响应不带令牌敏感信息 |
| `scope` | `kind: company`、`active_company_id`、`allowed_company_ids`，只含身份实际所属公司 |
| `navigation` | `route_id`、`path`、`access: read/write`；页面还检查入口与路径是否匹配 |
| `allowedActions` | 当前粗粒度读写动作；导航与动作同时允许才读取对应公司数据 |
| `home_path` | 平台管理员为 `/admin/rules`，其余为 `/workbench` |
| `session` | `expires_at: null`、`renew_supported: false` |
| `project_access`（可选） | 项目`id`、`revision`、`route_permissions`、项目`permissions`和章节`id/volume/permissions`；不含正文、证据或草稿 |

### 角色模型与权限说明

在 **三个登录角色（`role_mode: rbac-3roles`）** 下：
- `platform_admin`：管理公司、用户和平台配置。打开投标项目正文、生成和导出得到 404。种子账号 `admin` 同样不能打开正文。
- `company_admin`：管理本公司普通用户、知识库和本项目规则覆盖。可以建项目、确认分析并导出。不能建立平台管理员或其他公司管理员，也不能列出别的公司用户。
- `member`：可以新建项目并完成上传、分析、编辑、导出。创建者成为该项目负责人。编写范围由项目成员身份决定。可以查看本公司知识库，不能上传、停用、删除或修改连接。

旧登录角色 `group_admin`、`data_admin`、`project_lead`、`bid_writer`、`auditor`、`viewer` 以及别名 `manager`、`editor`、`reviewer`、`readonly` 收成 `member`。没有公司归属的集团管理员仍因公司范围为空而不能进项目。参考原文的八角色定义不改。

## 失败与范围

未登录/坏会话401；未知角色或不可信范围403；跨公司或未加入项目404，使用一致的不暴露资源文案。除唯一`project_id`外的查询字段、重复项目ID或请求正文返回422，不能通过角色/公司参数提升权限。会话及资源请求每次重新读取后台当前账号，撤权后不得沿用登录时的角色。公司范围来自身份，导航权限不替代具体业务接口的再次授权。404/403不返回正文或私稿。

实际生成的OpenAPI现为49路径、57操作；新增`getSession`并保留既有主流程操作。产品深链接由不进入 OpenAPI 的页面回退提供，未知 `/api` 仍是 JSON 404。会话专项33项是阶段一证据；2026-10-12 全后台 293 项含新增页面回退测试。T001 为 in-review。

## 后续本卡完整验收

ProLayout 与 History API 地址已提交复核：菜单只使用服务端允许的入口，未知地址不读取工作区，编辑台未保存时拦截站内切换、前进后退和刷新。401 直接退出。三断点实机截图、侧栏记忆、通用表单离开、OIDC 和精细字段权限仍按 T009、T007、T010 及元数据卡继续，本轮不计这些功能完成。
