为什么有这个文件：说明三角色和四段主路径改在哪些入口。

它解决什么问题：接手时能找到角色、页签、检索响应和规则覆盖的判断位置。

# FLOW-3ROLE：代码说明

登录角色的归一化在 `backend/bid-core/icg/domain/project_access.py` 和 `frontend/web/src/shared/roles.ts`。会话 `role_mode` 固定为 `rbac-3roles`，写在 `backend/bid-core/icg/domain/session_navigation.py`。平台管理员和账号 `admin` 读项目时由 `domain._project` 返回 404。

项目页签在 `frontend/web/src/project/project-header-core.ts`。旧地址在 `frontend/web/src/app/session-navigation.ts` 的 `canonicalProjectTab` 转到分析或导出。分析页把解析、矩阵和事实叠在一起，检查与导出把检查、导出和人工队列叠在一起，见 `frontend/web/src/app/ProjectWorkspaceContent.tsx`。

矩阵检索在 `fill_technical_responses`。解析完成后，技术分册和两册项目都会检索。已绑定的测试检索钩子优先。没有钩子时使用传入的知识库检索。没有命中写入 `no_evidence`，不再调用 `local_draft`。手写正文的 PATCH 在 `tender_orchestrator.patch_requirement` 被拒绝。技术条款没有依据时不能确认进正文。

废标相关事实的判断在 `parse_review.blocking_fact`。确认解析使用同一条件。

项目规则覆盖由 `compliance_rules._project_rule_override` 读出。社保月数进入 R11。`check_service_period` 为否时跳过服务期条款，SLA 负偏离仍检查。`require_own_staff` 为否时不再仅因「本单位人员」要求挂证明。`proof_valid_days.<材料>` 在材料名称包含该类型且带有 `age_days` 时比较天数。目录规则的 `can_disable` 仍全部为假。

用户管理页面用 `/api/v1/users` 读取和创建。平台管理员可建公司管理员和普通用户。公司管理员只能建本公司普通用户。
