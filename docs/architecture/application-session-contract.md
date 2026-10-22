为什么有这个文件：让页面和后台共同约定当前账号、导航及资源权限的可信读取方式。

它解决什么问题：避免页面凭登录时的旧角色或自己传入的公司参数决定访问范围。

# 应用会话与导航契约

维护日期：2026-10-22；版本：application-foundation-2（DOC-SYNC-1 与 WP-6 会话演进）。关联 ISSUE-009 / WP-6。会话身份规则是本契约的主体；系统已实现正式凭据认证、八角色单源收口与演示模式关闸。实际接口说明从后台代码自动化导出到 `spec/openapi/demo-v1.json` 并受 CI 门禁保障。

## 当前阶段入口

`GET /api/v1/session`，操作名`getSession`。Bearer从后台现有会话读取当前账号；没有请求正文，不接受客户端角色、用户ID或公司范围。可选`project_id`只选择要核验的项目，仍按后台公司及项目成员权限核验。

响应：演示身份模式、当前账号、公司范围、原PRD角色映射、服务端允许的导航入口和动作、默认首页，以及会话续期是否可用。选项目时返回最小项目权限，不带正文、证据内容或任何人的草稿。当前演示会话没有真实到期/续期机制，明确返回`expires_at: null`、`renew_supported: false`，不能假设OIDC已接入。

系统支持两种运行与认证模式，可通过环境变量与配置解耦：
1. **演示模式（默认或 `VITE_DEMO=1`）**：支持演示账号快速登录，会话返回 `auth_mode: "synthetic-demo"` 与 `role_mode: "legacy-demo-compat"`；历史三角色映射为标准角色（`manager → project_lead`、`editor → bid_writer`、`viewer → viewer`）。
2. **正式认证模式（`VITE_DEMO=0`）**：前端登录页仅展示正式 Access Token 凭据输入框；后端支持正式会话凭据核验，返回 `auth_mode: "authenticated"` 与 `role_mode: "rbac-8roles"`。在生产环境（`ICG_REQUIRE_MYSQL=1`）下，后端强行阻断演示账号登录。
3. **八角色权威单源**：前端单一事实源收口至 `frontend/web/src/shared/roles.ts`（包含 `platform_admin`、`group_admin`、`company_admin`、`data_admin`、`project_lead`、`bid_writer`、`auditor`、`viewer` 8 大角色及其权限集），并通过 `shared/codes.ts` 单源驱动状态字典。
4. **枚举一致性对齐说明**：经 WP-6 / 本轮治理收敛，前端 `RoleMode`、后端 `schemas.py` 与 OpenAPI 契约均统一为严格一致的 `["legacy-demo-compat", "rbac-8roles"]`，移除了历史过渡遗留的 `standard` 别名。

| 返回字段 | 契约取值与说明 |
|---|---|
| `auth_mode` | `"synthetic-demo" | "authenticated"`，标识是合成演示会话还是正式凭据认证会话 |
| `role_mode` | `"legacy-demo-compat" | "rbac-8roles"`，标识是旧三角色兼容还是标准 8 角色 RBAC 模型 |
| `user` | 包含 `id`, `name`, `company_id`, `role`, `roles`, `primary_role`；响应不带令牌敏感信息 |
| `scope` | `kind: company`、`active_company_id`、`allowed_company_ids`，只含身份实际所属公司 |
| `navigation` | `route_id`、`path`、`access: read/write`；页面还检查入口与路径是否匹配 |
| `allowedActions` | 当前粗粒度读写动作；导航与动作同时允许才读取对应公司数据 |
| `home_path` | 当前`/workbench`。`/` 登录后进入该首页；已登记的全局路径和项目页签按地址打开 |
| `session` | `expires_at: null`、`renew_supported: false` |
| `project_access`（可选） | 项目`id`、`revision`、`route_permissions`、项目`permissions`和章节`id/volume/permissions`；不含正文、证据或草稿 |

三种账号均可读取获准的项目、资料、服务模板和任务；editor/manager保留旧资料写权限，manager保留项目创建和服务模板写权限。这里的`library.write`不是完整资料负责人、审核、受限字段权限，后者仍需原任务实现。manager只有`admin.rules`只读入口，没有`admin`公司管理入口；viewer没有写作档案入口。项目导出入口还按当前项目分工和后台资源权限计算。

## 失败与范围

未登录/坏会话401；未知角色或不可信范围403；跨公司或未加入项目404，使用一致的不暴露资源文案。除唯一`project_id`外的查询字段、重复项目ID或请求正文返回422，不能通过角色/公司参数提升权限。会话及资源请求每次重新读取后台当前账号，撤权后不得沿用登录时的角色。公司范围来自身份，导航权限不替代具体业务接口的再次授权。404/403不返回正文或私稿。

实际生成的OpenAPI现为49路径、57操作；新增`getSession`并保留既有主流程操作。产品深链接由不进入 OpenAPI 的页面回退提供，未知 `/api` 仍是 JSON 404。会话专项33项是阶段一证据；2026-10-12 全后台 293 项含新增页面回退测试。T001 为 in-review。

## 后续本卡完整验收

ProLayout 与 History API 地址已提交复核：菜单只使用服务端允许的入口，未知地址不读取工作区，编辑台未保存时拦截站内切换、前进后退和刷新。401 直接退出。三断点实机截图、侧栏记忆、通用表单离开、OIDC 和精细字段权限仍按 T009、T007、T010 及元数据卡继续，本轮不计这些功能完成。
