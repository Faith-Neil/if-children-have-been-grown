为什么有这个文件：记录三角色和四段主路径这一轮实际改了什么。

它解决什么问题：避免把内存测试通过写成已经可以上线。

# FLOW-3ROLE：简化投标技术方案流程

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FLOW-3ROLE |
| 代码解释 | [代码说明](../code/FLOW-3ROLE.md) |
| 验收 | 2026-11-04 前端测试 598 项通过。后端 `test_technical_sources.py`、`test_application_session.py`、`test_eight_roles_access.py`、`test_auth_super_admin.py`、`test_auth_login_rbac_glue.py` 与社保覆盖用例在内存仓储通过。未在浏览器点选。未在要求 MySQL 的真实库重跑。未声称生产 RAGFlow 已接通 |
| 项目进度 | 任务为 in-review。不标 done。参考原文八角色不改。下一件事是在关演示且要求 MySQL 的环境核对本公司用户和规则覆盖 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-11-04。Issue：[ISSUE-048](../../issues/ISSUE-048.md)。
- 分支、提交、PR：未创建 PR，未合入。
- 本地验收：内存仓储与前端单测。浏览器和真实 MySQL 未跑。
- 合入 / 发布：未合入，未发布。

## 完成内容与变更文件

登录角色收成平台管理员、公司管理员、普通用户。旧角色收成普通用户。平台管理员和种子账号 `admin` 打开项目正文得到 404。用户管理列表和新建走 `/api/v1/users`。项目主导航收成概览、招标文件、分析、编辑台、检查与导出、项目设置。矩阵正文在没有检索依据时留空。手写「我方响应要点」不再提交。服务承诺不再另开一栏手写。项目事实显示在分析页。确认条件收成废标相关事实和取值冲突。合规检查读取已保存的社保月数、本单位人员、服务期和证明材料有效天数。侧栏「管理规则（只读）」改为「管理」。普通用户可以查看本公司知识库，不能上传或修改。

## 代码解释

见 [代码说明](../code/FLOW-3ROLE.md)。

## 验收结果

- 前端 `node --test tests/*.test.mjs tests/**/*.test.mjs`：598 项通过。
- 后端上述文件在内存仓储通过。`test_social_insurance_months_override_changes_r11_and_unset_projects_keep_the_code_rule` 覆盖 6 个月与未设置两种情况。
- 未验证：浏览器里从上传走到导出；`ICG_REQUIRE_MYSQL=1` 下的真实账号；生产 RAGFlow 是否返回命中。没有命中时条款保持待确认，这是内存替身下的行为。

## 项目进度

建议 PM 先看交付，不标 done。`RULES_INCOMPLETE` 与 `CHECK_BLOCKER_EXISTS` 仍会拦截导出。
