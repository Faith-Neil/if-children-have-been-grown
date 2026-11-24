为什么有这个文件：记录技术服务方案精简主路径 D 组（三角色权限收口）交付。

# TV-M0-T20 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 代码 | [TV-M0-T20](../code/TV-M0-T20.md) |

## 实际变更

- 登录角色只认平台管理员、公司管理员、普通用户。旧角色名只在归一化入口兼容（登录会话、用户接口输入），保存时一律归一；业务授权不再按 `data_admin`、`group_admin`、`manager`、`viewer` 原值判断。
- 只读只看项目角色 `readonly`（旧数据 `viewer` 同义）：`ensure_not_readonly()` 与 `writable()` 按项目成员判断；解除段落锁、问答、编辑台智能上下文、答案卡统一用同一判断。
- 知识库：普通用户可看，写入、删除整类数据集、改连接只给公司管理员；受限资料只给公司管理员。
- SLA 与必备事实：不再要求登录角色 `manager`，项目内看本项目负责人，公司模板看公司管理员或任一项目负责人。
- 通知：跨公司只认平台管理员；资料到期通知发公司管理员。
- 演示账号改三角色命名：`alpha-viewer` 为「普通用户·本项目只读」，`alpha-auditor` 为「普通用户·未进项目」，`alpha-data-admin` 为第二公司管理员，`alpha-group-admin` 为集团公司普通用户。
- 前端顶栏、字典页、资料库、方案片段、权限指令、用户管理去掉旧角色标签与白名单。

## 只读写拒绝核查

`tests/backend/test_readonly_member_writes.py` 按 OpenAPI 逐个调用 `/api/v1` 下带 `{project_id}` 的写接口（POST/PUT/PATCH/DELETE），项目只读成员全部 403。排除项：3 个只读计算接口（合规规则试算、章节变量、矩阵匹配）；按节修改与解除段落锁需要先有资源，分别由 `test_technical_assistant.py::test_readonly_member_cannot_rewrite` 与本文件 `test_readonly_member_cannot_unlock_own_lock` 覆盖。

## 验收证据

- `test_readonly_member_writes.py`、`test_paragraph_locks.py`：9 passed。
- 受影响测试按新角色语义更新后通过：知识库、SLA、通知、字典、会话、模型配置、问答、密码登录、状态标签共 99 passed。
- 后端角色、知识库、会话、问答、锁、事实、招标相关测试子集：559 passed、8 failed；8 项在改动前的代码上同样失败（助手会话 3、助手流式 1、粘贴识别 1、技术来源 3），非本次引入。
- 前端 `pnpm lint` 通过；前端全量失败集合与改动前相同。
- 只用合成数据与模型替身验证；未连内网 Qwen / RAGFlow，界面未做浏览器验收。

## 局限

- 旧角色名仍可作为用户接口输入（兼容旧客户端），保存时归一为三角色。
- 项目角色兼容值 `project_lead`、`bid_writer` 仍在团队判断里按 `lead`、`writer` 处理。

## 同步

PRD、ROADMAP、ARCHITECTURE：无改动，按用户 2026-11-20 确认的三角色与项目只读执行，见 [角色审计](../reviews/2026-11-20-role-feature-audit.md)。
