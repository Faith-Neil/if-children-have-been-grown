为什么有这个文件：解释 TV-M0-T20 三角色权限收口与项目只读写拒绝的代码。

# TV-M0-T20 代码说明

| 文件 | 说明 |
|---|---|
| [project_access.py](../../backend/bid-core/icg/domain/project_access.py) | `LOGIN_ROLES` 三角色；`READONLY_PROJECT_ROLES`（`readonly`，旧数据 `viewer` 同义）与 `readonly_member()`；`writable()` 先拒项目只读；`ensure_not_readonly()` 改按项目成员判断；`leads_any_project()` 判公司管理员或任一未删除项目的负责人 |
| [paragraph_locks.py](../../backend/bid-core/icg/domain/paragraph_locks.py) | 解除段落锁带项目上下文做只读判断 |
| [answer_card.py](../../backend/bid-core/icg/domain/answer_card.py)、[editor_ai_context.py](../../backend/bid-core/icg/domain/editor_ai_context.py)、[assistant_qa.py](../../backend/bid-core/icg/domain/assistant_qa.py) | 项目只读判断统一用 `readonly_member()`，`readonly` 与 `viewer` 都拦 |
| [kb_admin.py](../../backend/bid-core/icg/domain/kb_admin.py) | 读：公司管理员与普通用户；写和连接只给公司管理员；不再保留 `data_admin`、`manager`、`viewer` 细角色；追加历史标书给公司管理员或任一项目负责人；资料库（权威资料）上传只给公司管理员 |
| [knowledge_base.py](../../backend/bid-core/icg/domain/knowledge_base.py)、[library_orchestrator.py](../../backend/bid-core/icg/domain/library_orchestrator.py) | 受限资料只认归一后的公司管理员 |
| [notifications.py](../../backend/bid-core/icg/domain/notifications.py) | 跨公司只认平台管理员；资料到期通知发公司管理员 |
| [sla.py](../../backend/bid-core/icg/domain/sla.py)、[tender_orchestrator.py](../../backend/bid-core/icg/domain/tender_orchestrator.py) | 不再要求登录角色 `manager`：项目内看本项目负责人，公司模板看公司管理员或任一项目负责人 |
| [session_navigation.py](../../backend/bid-core/icg/domain/session_navigation.py)、[schemas.py](../../backend/bid-core/icg/domain/schemas.py) | 会话用户带 `leads_project`；任一项目负责人的普通用户多一个 `sla_templates.write` 动作 |
| [SlaPages.tsx](../../frontend/web/src/admin/SlaPages.tsx)、[kb-admin-core.ts](../../frontend/web/src/library/kb-admin-core.ts)、[KnowledgeBaseAdminPage.tsx](../../frontend/web/src/library/KnowledgeBaseAdminPage.tsx) | 服务承诺模板编辑看公司管理员或 `leads_project`；历史标书上传按钮对项目负责人可用，资料库上传仍只给公司管理员 |
| [dict_config.py](../../backend/bid-core/icg/domain/dict_config.py)、[field_metadata.py](../../backend/bid-core/icg/domain/field_metadata.py) | 缺省角色由 `viewer` 改为 `member` |
| [user_management.py](../../backend/bid-core/icg/domain/user_management.py) | 旧角色名仍可作输入，改角色时也按三角色归一后保存 |
| [memory_repository.py](../../backend/bid-core/icg/infra/memory_repository.py) | 演示账号改三角色命名：只读演示 = 普通用户 + 项目 `readonly`；原资料管理员改为第二公司管理员 |
| [roles.ts](../../frontend/web/src/shared/roles.ts) 调用方 | 顶栏、字典页、资料库、方案片段、权限指令、用户管理去掉旧角色标签与白名单 |
| [test_readonly_member_writes.py](../../tests/backend/test_readonly_member_writes.py) | 按 OpenAPI 逐个调用 `/api/v1` 项目写接口，项目只读成员全部 403；只读成员解除自己的段落锁 403 |
