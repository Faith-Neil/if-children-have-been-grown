为什么有这个文件：登记平台管理员开通公司并管理各公司账号的需求变更。

它解决什么问题：当前公司管理只能启停、不能创建公司与首个管理员；平台管理员顶栏仍显示合成公司名；跨公司看人缺少「点进公司」主路径。

# ISSUE-052：公司开通与账号归属

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-052 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | in-progress |
| 登记日期 | 2026-11-09 |
| 最后更新日期 | 2026-11-09 |
| revision | company-provision-1 |
| 关联 Task | [ADMIN-PROVISION-T01](../docs/tasks/ADMIN-PROVISION.md#admin-provision-t01)～[T04](../docs/tasks/ADMIN-PROVISION.md#admin-provision-t04) |
| 关联 PR | 产品线 `feat/iss-047-technical-volume-mvp`；[PR #8](https://github.com/Faith-Neil/if-children-have-been-grown/pull/8) DO NOT MERGE |
| 本地验收 | 内存/假 RAGFlow 与前端单测/lint；浏览器与真实 MySQL 未跑 |
| 合入 | 不合入 main（本 Issue 未授权合并） |
| 发布 | 未发布 |
| 交付说明 | 见各卡 delivery |
| 代码 / 流程解释 | [设计](../docs/superpowers/specs/2026-11-09-company-provisioning-design.md)；[计划](../docs/superpowers/plans/2026-11-09-company-provisioning.md) |

## 现象与证据

- 平台管理员顶栏曾有公司名称（合成映射）。
- 原先无 `POST /api/v1/companies`；公司管理仅列表与启停。

## 目标

按设计落地：顶栏对平台管理员隐藏公司名；同一弹窗开通公司与首个管理员；公司详情查看并添加该公司管理员/成员；各公司项目与双库数据集隔离。

## 实施任务

| Task ID | 目标 | 状态 |
|---|---|---|
| ADMIN-PROVISION-T01 | 后端开通公司 + must_change_password | in-review |
| ADMIN-PROVISION-T02 | 顶栏去公司名 + 新建公司弹窗 | in-review |
| ADMIN-PROVISION-T03 | 公司详情路由与加人 UI | in-review |
| ADMIN-PROVISION-T04 | 项目与双库隔离回归 + 治理 | in-review |

## 六份基线

| 基线 | impact |
|---|---|
| PRD | 有影响：对齐 §5.10.1；实施视图未改章节编号 |
| ROADMAP | 有影响：管理面能力补齐（见 PROJECT_STATUS） |
| ARCHITECTURE | 有影响：`POST /companies` 与公司详情路由 |
| Issue 看板 | 本 Issue |
| TASK_BOARD | 四卡 in-review |
| DOCUMENT_INDEX | 设计/计划/交付已登记 |

## 约束

- 不标任务 done；不合并 PR #8，除非人类 PM 另令。
- 关演示正式路径须可验证；不得以 demo 登录单独作为通过凭据。
- 建议 PM 待 QA/PD 签署后再标 done。
