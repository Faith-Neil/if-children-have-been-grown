为什么有这个文件：说明 P0-SEC-MODEL-AUDIT-HOTFIX 涉密模型判定、审计授权与平台安全策略保存代码的修改原因、运行过程与限制。

# P0-SEC-MODEL-AUDIT-HOTFIX：代码解释

- 对应任务、Issue、交付文档：[P0-SEC-MODEL-AUDIT-HOTFIX](../tasks/P0-HOTFIX.md#p0-sec-model-audit-hotfix)、[ISSUE-059](../../issues/ISSUE-059.md)、[交付说明](../delivery/P0-SEC-MODEL-AUDIT-HOTFIX.md)
- 日期、实际代码路径、提交 / PR：2026-11-27；`backend/bid-core/icg/infra/model_config_storage.py`、`backend/bid-core/icg/domain/domain.py`、`backend/bid-core/icg/api/audit.py`、`frontend/web/src/admin/PlatformSecurityPage.tsx`、`frontend/web/src/admin/platform-security-core.ts`；分支 `feat/iss-059-p0-security-export-deploy-hotfix`，PR 未创建。

## 改了什么以及为什么

原行为有三处 P0 缺陷：

1. 平台模型兜底按 `is_local` 标志判断端点是否本地——`is_local` 是用户填写配置时的自声明标志，公网 URL 的配置只要误标或被标 `is_local=true` 就能通过涉密校验，公司正文可能经平台默认模型发往公网外部服务（违反 B5/B6 内网零外泄红线）；反过来，合规的内网本地模型也可能因平台默认模型（非本地）参与判定而被误挡。
2. `GET /api/v1/audit-logs` 对非平台用户只按 `company_id` 过滤，普通成员也能读本公司审计日志（CWE-862 缺少授权）。
3. 平台安全策略保存时前端把整份本地 `settings`（含首次加载前的默认值）PATCH 回后端，后端 PATCH 是合并语义，于是前端默认值会覆盖其他已存策略项。

目标行为与实现：

- `model_config_storage.py` 新增 `config_compliant_for_sensitive()`：按端点 URL 判定公网端点（不再信任 `is_local` 自声明）；`saved_company_model` 的平台 system 兜底分支排除公网 URL 配置，涉密/公司正文场景兜底绝不选公网外部模型。
- `domain.py`（`backend/bid-core/icg/domain/domain.py`）`resolve_model_provider` 的四个解析分支——项目绑定 → 任务路由 → 公司兜底 → 进程兜底——统一执行涉密校验；`require_allowed_model` 改为按**实际生效配置**校验，平台默认模型不再误挡合规本地模型的涉密生成，非本地模型涉密门禁不削弱。
- `api/audit.py`：非平台用户必须是 `company_admin`；普通成员（编写人/只读/项目负责人）读取一律 403；公司管理员跨公司查询 403；platform_admin 可读全局。
- 前端改为 baseline/draft 双态：服务端快照存入 baseline，用户编辑只改 draft；保存时经 `changedSecurityFields` 只上行与 baseline 真正不同的字段；未读回服务端快照前禁止保存；刷新页面后未保存编辑不丢。

## 入口和调用顺序

- 涉密生成链路：章节生成/问答/改写等任务 → `resolve_model_provider(state, project_id, task)` 逐分支解析生效模型 → 每分支经 `config_compliant_for_sensitive` 校验 → `require_allowed_model` 按生效配置终检 → 命中的 provider 才进入 `openai_model` 调用。
- 审计查询链路：`GET /api/v1/audit-logs` → 角色判定（platform_admin 全局 / company_admin 本公司 / 其他 403）→ `security_audit` 事实源按公司过滤返回。
- 平台安全策略保存链路：`PlatformSecurityPage` 加载 → GET 快照写入 baseline 与 draft → 用户编辑 draft → 保存按钮（快照未读回时禁用）→ `changedSecurityFields(baseline, draft)` 计算增量 → PATCH 只上行增量字段 → 后端合并落盘。

## 数据与状态

- 模型配置持久化在 MySQL（密钥密文存储，密文非确定性更新、MySQL diff 可检出）；密钥轮换链路本身未改，根因修复在 API 层授权（见 P0-CONFIG-KB-HOTFIX 组 3 (h)）。
- 审计日志为 `security_audit` 真事实源，本卡只改授权判定不改存储。
- 前端 baseline/draft 为组件内状态，不引入全局store；保存成功后 baseline 更新为最新服务端读回值。

## 关键判断与异常

- 公网判定按 URL 形态（协议+主机），内网地址/回环/私网段判为合规；`trust_env=False` 的内网客户端约束不变。
- 涉密项目任何分支解析到公网端点都被拒绝；非涉密项目行为不变。
- 审计授权拒绝统一 403，不泄露其他公司是否存在日志。
- 前端增量为空时不发起 PATCH。

## 验证与限制

- `tests/backend/test_issue059_model_security.py` 15 passed；`tests/backend/test_issue059_audit_rbac.py` 6 passed；`frontend/web/tests/unit/platform-security-settings.test.mjs` 7 例全绿。
- 验证登记见 [iss-059-p0-hotfix-verification](../testing/iss-059-p0-hotfix-verification.md)。
- 限制：真实模型端点连通性未验证（`ICG_RUN_REAL_MODEL_TESTS=1` 门控）；URL 判定依赖运维正确配置内网地址；前端测试为 jsdom 单元级，未做真实浏览器联调。解释只对应当前实现。
