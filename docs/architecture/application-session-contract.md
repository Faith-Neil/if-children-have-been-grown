为什么有这个文件：让页面和后台共同约定当前账号、导航及资源权限的可信读取方式。

它解决什么问题：避免页面凭登录时的旧角色或自己传入的公司参数决定访问范围。

# 应用会话与导航契约

日期2026-10-11，地址补充2026-10-12；版本application-foundation-1。ISSUE-009 / APP-M2-T001 为 in-review。会话身份规则仍是本契约的主体；浏览器地址已接到这些路径，但不表示项目经理已签收，也不表示 OIDC 或八角色已完成。实际接口说明须从代码导出到`spec/openapi/demo-v1.json`。

## 当前阶段入口

`GET /api/v1/session`，操作名`getSession`。Bearer从后台现有会话读取当前账号；没有请求正文，不接受客户端角色、用户ID或公司范围。可选`project_id`只选择要核验的项目，仍按后台公司及项目成员权限核验。

响应：演示身份模式、当前账号、公司范围、原PRD角色映射、服务端允许的导航入口和动作、默认首页，以及会话续期是否可用。选项目时返回最小项目权限，不带正文、证据内容或任何人的草稿。当前演示会话没有真实到期/续期机制，明确返回`expires_at: null`、`renew_supported: false`，不能假设OIDC已接入。

三种既有演示角色的兼容映射：`manager → project_lead`（项目负责人）、`editor → bid_writer`（投标编写人）、`viewer → readonly`（只读成员）；manager不等于公司管理员。原PRD8角色矩阵在`session_navigation.py`独立定义：`platform_admin`、`group_admin`、`company_admin`、`data_admin`、`project_lead`、`bid_writer`、`reviewer`、`readonly`。当前身份来源只给出三种演示角色，不以演示账号冒充全部八角色，也未完成完整业务授权迁移。

| 返回字段 | 当前实际内容 |
|---|---|
| `auth_mode` / `role_mode` | `synthetic-demo` / `legacy-demo-compat`，明确是合成演示和兼容阶段 |
| `user` | 既有账号字段，加`roles`和`primary_role`；响应不带令牌 |
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
