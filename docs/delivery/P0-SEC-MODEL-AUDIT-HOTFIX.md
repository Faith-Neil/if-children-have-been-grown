为什么有这个文件：记录 P0-SEC-MODEL-AUDIT-HOTFIX 平台模型安全红线、密钥轮换、审计日志授权与平台安全策略保存止血的实际完成内容、验收证据与遗留风险。

# P0-SEC-MODEL-AUDIT-HOTFIX 交付说明

| 项 | 内容 |
|---|---|
| 状态 | in-review；建议 PM 复核后标 done |
| Issue | [ISSUE-059](../../issues/ISSUE-059.md) |
| 任务卡 | [P0-HOTFIX](../tasks/P0-HOTFIX.md#p0-sec-model-audit-hotfix) |
| 代码说明 | [P0-SEC-MODEL-AUDIT-HOTFIX](../code/P0-SEC-MODEL-AUDIT-HOTFIX.md) |
| 验证登记 | [iss-059-p0-hotfix-verification](../testing/iss-059-p0-hotfix-verification.md) |

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | P0-SEC-MODEL-AUDIT-HOTFIX |
| 代码解释 | [代码说明](../code/P0-SEC-MODEL-AUDIT-HOTFIX.md) |
| 验收 | 后端 `tests/backend/test_issue059_model_security.py` 15 passed、`tests/backend/test_issue059_audit_rbac.py` 6 passed；前端 `frontend/web/tests/unit/platform-security-settings.test.mjs` 7 例全绿；`export_openapi.py --check` 契约一致。真实模型连通性未在本轮验证（`ICG_RUN_REAL_*` 门控）。 |
| 项目进度 | in-review；建议 PM 复核后标 done。ISSUE-059 四张止血卡全部实施完成进入 in-review，等待 QA 签署 + PD 产品验收 + 人类 PM 确认；未创建 PR，未合入，未发布。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-11-27；P0 止血（无里程碑变更）；[ISSUE-059](../../issues/ISSUE-059.md)；[P0-HOTFIX 任务卡](../tasks/P0-HOTFIX.md#p0-sec-model-audit-hotfix)。
- 分支、提交、PR：分支 `feat/iss-059-p0-security-export-deploy-hotfix`；PR 未创建。
- 本地验收状态：聚焦单测通过（见验收结果）；真实模型端到端未验证。
- 合入 / 发布状态：未合入、未发布。

## 完成内容与变更文件

对应用户止血清单组 1（a/b/c），无范围偏差：

1. **(a) 平台模型兜底涉密零外泄封堵**：`backend/bid-core/icg/infra/model_config_storage.py` 新增 `config_compliant_for_sensitive()`，按端点 URL 而非 `is_local` 标志判定公网端点；`saved_company_model` 的平台 system 兜底排除公网 URL 配置。`backend/bid-core/icg/domain/domain.py` 的 `resolve_model_provider` 全分支（项目绑定 → 任务路由 → 公司兜底 → 进程兜底）统一执行涉密校验；`require_allowed_model` 改为按实际生效配置校验，修复平台默认模型误挡合规本地模型的涉密生成。
2. **(a) 在用公司模型密钥轮换恢复**：根因不是轮换链路本身，而是 API 层 403 一刀切（见组 3 (h)，`require_platform_admin` 误加导致公司管理员根本到不了 PUT 端点）。轮换链路本身经测试固化：密文非确定性更新、MySQL diff 可检出，旧密钥更新后运行时即刻生效。
3. **(b) 审计日志授权收口**：`backend/bid-core/icg/api/audit.py` 非平台用户必须是 `company_admin` 才能读审计日志，普通成员（编写人/只读/项目负责人）读取一律 403；公司管理员跨公司查询 403；仅 platform_admin 可读全局。
4. **(c) 平台安全策略保存不覆盖**：`frontend/web/src/admin/PlatformSecurityPage.tsx` + 新增 `frontend/web/src/admin/platform-security-core.ts`。后端 PATCH 为合并语义，前端原先把整份本地对象（含首次加载前的默认值）上行覆盖其他已存策略项；改为 baseline/draft 双态，只上行 `changedSecurityFields` 真正改动的字段；未读回服务端快照前禁止保存；刷新页面不丢未保存编辑。

## 代码解释

详见 [代码说明](../code/P0-SEC-MODEL-AUDIT-HOTFIX.md)：入口、调用顺序、涉密判定逻辑、授权矩阵与前端双态保存机制。

## 验收结果

| 验收条目 | 执行方式 | 结果与证据 |
|---|---|---|
| 平台兜底路径涉密/公司正文场景绝不选择公网外部模型 | `tests/backend/test_issue059_model_security.py` | 15 passed；覆盖项目绑定/任务路由/公司兜底/进程兜底全分支 |
| 在用公司模型可轮换密钥，旧密钥更新后即刻生效 | 同上测试文件内轮换固化用例 | 通过：密文非确定性更新、MySQL diff 检出 |
| 合规本地模型涉密生成不被平台默认模型误挡；非本地模型涉密门禁不削弱 | 同上 | 通过：`require_allowed_model` 按实际生效配置校验 |
| 普通成员读 `/api/v1/audit-logs` 一律 403；platform_admin 全局、company_admin 本公司可读 | `tests/backend/test_issue059_audit_rbac.py` | 6 passed；含跨公司查询 403 授权矩阵 |
| 平台安全策略保存后其他未编辑策略项保持服务端原值 | `frontend/web/tests/unit/platform-security-settings.test.mjs` | 7 例全绿：只上行改动字段、未读回快照禁止保存、刷新不丢草稿 |
| OpenAPI 契约零漂移 | `export_openapi.py --check` | 100% 一致（本轮无新增端点） |

未验证范围：真实模型端点连通性仍受 `ICG_RUN_REAL_MODEL_TESTS=1` 门控，本轮未执行；前端测试为 jsdom 单元级，未做真实浏览器联调。

## 项目进度

in-review；建议 PM 复核后标 done。ISSUE-059 四张止血卡（P0-SEC-MODEL-AUDIT-HOTFIX、P0-EXPORT-STATE-HOTFIX、P0-CONFIG-KB-HOTFIX、P0-DEPLOY-HOTFIX）全部实施完成并进入 in-review；下一步为 QA 独立签署、PD 产品验收与人类 PM 确认。本卡不标 done。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响：止血修复不改变产品范围、角色或业务规则，只恢复 B5/B6 内网零外泄红线与既有授权规则的正确执行 |
| ROADMAP | 无影响：不改变里程碑顺序，属当前主链路阻断止血 |
| ARCHITECTURE | 有影响：模型兜底安全边界（按 URL 判定公网端点）与审计授权边界收紧；ISSUE-059 六份基线同步表已登记「待处理」，由后续架构对齐任务或 PM 复核时落实正文 |
| Issue 看板/详情 | 已同步：ISSUE-059 验收条目 AC-01～AC-03 更新为实证，处理记录追加一行 |
| TASK_BOARD / PROJECT_STATUS | 已同步：看板本卡 in-review 并链接本交付；PROJECT_STATUS P0 段落同步四卡 in-review |
| DOCUMENT_INDEX | 已登记：本交付与代码说明条目（D-1098 / D-1102） |

## 风险与后续

- 涉密判定按 URL 识别公网端点：若内网模型服务经公网域名解析或反代暴露，URL 判定依赖运维正确配置内网地址；内网客户端 `trust_env=False` 红线不变。
- 密钥轮换的根因在 API 层授权（组 3 (h) 修复），本卡测试固化的是轮换链路本身；两项修复合并后才构成完整可轮换能力。
- 真实模型连通性未在本轮验证，QA 复测时如需真机证据须按 `ICG_RUN_REAL_MODEL_TESTS=1` 门控在内网执行。
- 前端保存合并语义依赖后端 PATCH 合并行为保持不变；若后端改为整体替换语义须同步调整。


## 第二轮补充（PM 最终权限模型裁定）

PM 正式驳回第一轮对公司管理员放开模型/RAGFlow 配置写权限的调整。最终权限模型：

- 模型配置 CRUD、密钥轮换（含存量在用模型）、连通性测试与 RAGFlow 引擎连接配置/测试：**严格仅限 platform_admin**，公司管理员与普通成员一律 403（`test_company_admin_cannot_reach_platform_model_or_engine_config` 恢复守护此边界）；
- 项目模型绑定为独立授权：项目负责人与公司管理员可读只写候选列表 `GET /projects/{id}/model-options`（绝不暴露明文密钥）并绑定已有合规模型（公司或平台 system 池）；前端绑定链路已切换到该端点；
- 纵深防御补齐：CWE-639 全局 ID 冲突拒绝 + MySQL 归属约束 UPDATE；CWE-522 RAGFlow 改地址必须显式新密钥或显式清空；CWE-862 create_dataset/sync_knowledge_base 强制 company_admin/platform_admin；CWE-918 端点 scheme/主机/userinfo 校验；
- RAGFlow 部署默认值不再持久化进公司配置行，只在运行时回落层生效（含回归测试）。


## 第四轮补充（Devin Review 复扫收敛）

- 登记 `PUBLIC_MODEL_ENDPOINT_FORBIDDEN=403` 并同步冻结名单/OpenAPI；显式项目绑定或任务路由指向公网模型时不再静默回落，运行时统一 fail-closed，自动扫描默认池时才跳过公网项。
- 对话助手 HTTP 路由新增回归：显式公网绑定返回 403 与“改用内网模型”提示，不再因未登记错误码变成 500。
- 项目模型读取的默认公司范围修正为目标项目所属公司；模型选项仍只返回掩码，不返回 API Key。


## 第五轮补充

公网备用模型改为直接丢弃，不再误阻断健康内网主模型；公网主模型 403 拦截保持不变，并有请求级回归证明没有流量发往公网备用端点。最终后端聚焦回归 252 passed、12 skipped、0 failed，11 个 MySQL 标记用例在 3407 隔离合成库补跑通过。
