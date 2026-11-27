为什么有这个文件：记录 P0-CONFIG-KB-HOTFIX 平台 RAGFlow 配置生效、项目负责人绑定模型、知识库重建 Word 转换与种子账号登录止血的实际完成内容、验收证据与遗留风险。

# P0-CONFIG-KB-HOTFIX 交付说明

| 项 | 内容 |
|---|---|
| 状态 | in-review；建议 PM 复核后标 done |
| Issue | [ISSUE-059](../../issues/ISSUE-059.md) |
| 任务卡 | [P0-HOTFIX](../tasks/P0-HOTFIX.md#p0-config-kb-hotfix) |
| 代码说明 | [P0-CONFIG-KB-HOTFIX](../code/P0-CONFIG-KB-HOTFIX.md) |
| 验证登记 | [iss-059-p0-hotfix-verification](../testing/iss-059-p0-hotfix-verification.md) |

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | P0-CONFIG-KB-HOTFIX |
| 代码解释 | [代码说明](../code/P0-CONFIG-KB-HOTFIX.md) |
| 验收 | `tests/backend/test_issue059_ragflow_fallback.py` 11 passed、`tests/backend/test_issue059_model_config_rbac.py` 7 passed、`tests/backend/test_admin_rbac_security_cleanup.py` 8 passed、`tests/backend/test_iss059_backend_hotfix.py` + `test_kb_admin` 23 passed 2 skipped（含真实 MySQL 3407 复现用例 2 passed）、`reference_flow` 21 passed；`export_openapi.py --check` 100% 一致。 |
| 项目进度 | in-review；建议 PM 复核后标 done。ISSUE-059 四张止血卡全部实施完成进入 in-review，等待 QA 签署 + PD 产品验收 + 人类 PM 确认；未创建 PR，未合入，未发布。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-11-27；P0 止血（无里程碑变更）；[ISSUE-059](../../issues/ISSUE-059.md)；[P0-HOTFIX 任务卡](../tasks/P0-HOTFIX.md#p0-config-kb-hotfix)。
- 分支、提交、PR：分支 `feat/iss-059-p0-security-export-deploy-hotfix`；PR 未创建。
- 本地验收状态：聚焦单测与真实 MySQL 复现用例通过（见验收结果）；真实 RAGFlow 连通性未在本轮验证。
- 合入 / 发布状态：未合入、未发布。

## 完成内容与变更文件

对应用户止血清单组 3（g/h/i/j），无范围偏差：

1. **(g) 平台级 RAGFlow 配置对下属公司生效**：新增 `backend/bid-core/icg/domain/ragflow_config.py` 的 `effective_ragflow_connection()`——公司配置缺密钥时回落平台 system 端点/密钥/超时，但保留公司租户身份与 `dataset_ids`；公司显式停用时不回落。`get_client` 与 `knowledge_base.py` 的 `_configured_client` 统一走该函数；`backend/bid-core/icg/api/ragflow.py` 移除 `59f091e` 误加的 10 处 `require_platform_admin`，恢复 `5c3ec77` 既定设计。
2. **(h) 项目负责人绑定模型能力恢复**：`backend/bid-core/icg/api/model_configs.py` 移除 `59f091e` 误加的 9 行 `require_platform_admin` 一刀切，恢复既定设计：公司管理员 CRUD、项目负责人绑定本项目模型，编写人/只读仍 403。主 Agent 裁定：`tests/backend/test_admin_rbac_security_cleanup.py` 中与既有设计矛盾的 ISSUE-056 测试已改写为真正的安全边界（普通成员写操作 403、跨租户/平台配置不可触达 404），8 passed。
3. **(i) 知识库重建 Word 转换链透传**：`backend/bid-core/icg/domain/kb_admin.py` 重建时已转换 PDF 字节使用 `.pdf` 文件名 + `application/pdf`（原先沿用 `.docx` 名导致类型错配解析失败）；存量未转换 Word 字节重建前先补转换；转换失败在移动/删除旧数据集之前抛 422 `FILE_CONVERSION_FAILED`（已冻结进 `errors.py` / `frozen_error_codes.py` / OpenAPI）；先完成全部转换校验再 detach 数据集。顺带修复冻结名单漏收 `COMPANY_NAME_DUPLICATED` 的既有问题。
4. **(j) 本机 MySQL 种子账号登录持久**：根因——非生产种子账号只在内存、从未写入 `demo_state_entry`，热路径 `read_auth_state` 按条目加载时账号缺失。修复：`mysql_repository` 构造时保留只读 `_development_seed_accounts`（生产为空），`hot_reads.py` 新增 `apply_development_seed_accounts()` 只填补缺失账号、绝不覆盖条目表真实账号、只接受 `_DEMO_ONLY` 种子；接入全部 4 条热路径。真实 MySQL 3407 复现验证。

## 代码解释

详见 [代码说明](../code/P0-CONFIG-KB-HOTFIX.md)：平台配置回落生效链、RBAC 恢复边界、重建转换顺序与 422 语义、种子账号只读填补机制。

## 验收结果

| 验收条目 | 执行方式 | 结果与证据 |
|---|---|---|
| 平台级 RAGFlow 配置更新后下属公司检索/摄入链路使用新配置 | `tests/backend/test_issue059_ragflow_fallback.py` | 11 passed：缺密钥回落平台端点但保留公司租户身份与 dataset_ids；显式停用不回落 |
| 项目负责人绑定项目模型成功；编写人/只读 403；敏感项目本地模型门禁不削弱 | `tests/backend/test_issue059_model_config_rbac.py` | 7 passed；`test_admin_rbac_security_cleanup.py` 改写后 8 passed（普通成员写 403、跨租户/平台配置 404） |
| 重建知识库后已转换 Word 可解析；转换失败返回 422 | `test_iss059_backend_hotfix` + `test_kb_admin` | 23 passed 2 skipped：`.pdf` 文件名+MIME 透传、422 `FILE_CONVERSION_FAILED` 先于数据集移动/删除、冻结名单一致 |
| 本机 MySQL 种子账号登录后会话持续有效 | 真实 MySQL 标记用例 | 2 passed：种子账号登录后可建项目、可读取 workspace（真实 MySQL 3407 复现） |
| 既有主链路无回归 | `tests/backend/test_reference_flow.py` | 21 passed |
| OpenAPI 契约零漂移 | `export_openapi.py --check` | 100% 一致（`FILE_CONVERSION_FAILED` 冻结在契约内） |

未验证范围：真实 RAGFlow 连通性仍受 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 门控，本轮未执行；知识库测试为进程内 Fake RAGFlow；skipped 用例为真实服务门控跳过，非失败。

## 项目进度

in-review；建议 PM 复核后标 done。ISSUE-059 四张止血卡全部实施完成并进入 in-review；下一步为 QA 独立签署、PD 产品验收与人类 PM 确认。本卡不标 done。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响：止血修复不改变产品范围、角色或业务规则；项目负责人绑定模型是恢复 ISSUE-056 之前既有能力，非新功能 |
| ROADMAP | 无影响：不改变里程碑顺序，属当前主链路阻断止血 |
| ARCHITECTURE | 无新增架构变更：配置生效链（公司级优先、平台 system 兜底）为既定设计的恢复与补全；错误码冻结名单为既有机制的修正 |
| Issue 看板/详情 | 已同步：ISSUE-059 验收条目 AC-07～AC-10 更新为实证，处理记录追加一行 |
| TASK_BOARD / PROJECT_STATUS | 已同步：看板本卡 in-review 并链接本交付；PROJECT_STATUS P0 段落同步四卡 in-review |
| DOCUMENT_INDEX | 已登记：本交付与代码说明条目（D-1100 / D-1104） |

## 风险与后续

- 平台回落语义：公司配置缺密钥时回落平台端点/密钥/超时但保留公司租户身份与 dataset_ids——租户隔离边界不变（`${company_id}::` 数据集前缀不变）；显式停用不回落，避免平台配置意外复活公司已停用的检索。
- `require_platform_admin` 误加移除后，模型配置端点恢复公司管理员 CRUD + 项目负责人绑定；安全边界由改写后的 `test_admin_rbac_security_cleanup.py` 固化（普通成员写 403、跨租户 404），多租户强隔离未削弱。
- 真实 RAGFlow 端到端重建未在本轮验证，QA 如需真机证据须在内网按门控执行；转换失败 422 语义已在 Fake RAGFlow 下固化。
- `COMPANY_NAME_DUPLICATED` 冻结名单漏收为既有问题的顺带修复，无行为变化（错误码本身早已使用）。


## 第二轮补充（Devin Review 收口）

- Critical 6：重建历史标书生成新文档 ID 时重置脱敏/去实体化状态标记，确保 knowledge_base 在解析完成后对新分块完整重跑脱敏，杜绝敏感实体借重建绕过脱敏直接进入可检索状态；
- RAGFlow 引擎配置权限按 PM 最终模型收回 platform_admin（详见 P0-SEC-MODEL-AUDIT-HOTFIX 第二轮补充）；
- CWE-522/862/918 修复与回归测试见 docs/testing/iss-059-p0-hotfix-verification.md 验证登记。


## 第四轮补充（Devin Review 复扫收敛）

- RAGFlow 平台显式停用后，未独立配置的公司继承连接会被 `KNOWLEDGE_BASE_NOT_CONFIGURED` 阻断，不能再拿平台密钥创建数据集；独立公司配置不被平台实例停用误伤。
- 首次保存只改超时等字段时，部署环境密钥掩码按“保留继承密钥”处理，不再把掩码加密成新密钥；前端也不再上行未修改的掩码。
- 公司任务路由保存与运行时统一允许本公司或 system 池合规模型；平台管理员写 system 全局路由时，前端只列 system 池，避免选到无法保存的公司专属模型。


## 第五轮补充

RAGFlow 密钥现在区分继承与显式清除；显式清除后不复活环境密钥，省略密钥仅改超时时沿用部署密钥并应用保存的超时值；公司租户沿用部署连接时同样继承平台持久化超时。最终后端聚焦回归 252 passed、12 skipped、0 failed，11 个 MySQL 标记用例在 3407 隔离合成库补跑通过。
