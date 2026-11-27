为什么有这个文件：登记 ISSUE-059 四张 P0 止血卡本轮开发自测的实际范围、结果与未覆盖环境。

它解决什么问题：让 QA 独立复测时能对照同一组验证口径，并看清哪些环境本轮没有执行。

# ISSUE-059 P0 止血修复验证登记（2026-11-27）

- 分支 `feat/iss-059-p0-security-export-deploy-hotfix`；[ISSUE-059](../../issues/ISSUE-059.md)；[PR #56](https://github.com/Faith-Neil/if-children-have-been-grown/pull/56) OPEN，未合入
- 环境：Windows 本机 + Git Bash，Python 3.12.9，Node 24，pnpm；本机真实 MySQL 可达（端口 3407 复现用例）；无内网真实 RAGFlow 与真实模型
- 性质：各实施 subagent 开发自测汇总，不是 QA 签署；QA 独立复测、PD 产品验收与 PM 确认尚未执行

## 结果

| 检查 | 范围 | 结果 |
|---|---|---|
| 涉密模型安全 | `tests/backend/test_issue059_model_security.py` | 15 passed（公网 URL 判定、四分支统一涉密校验、平台兜底排除公网、密钥轮换密文非确定性更新与 MySQL diff、本地模型不误挡） |
| 审计日志授权 | `tests/backend/test_issue059_audit_rbac.py` | 6 passed（普通成员 403、company_admin 本公司、跨公司 403、platform_admin 全局） |
| RAGFlow 平台回落 | `tests/backend/test_issue059_ragflow_fallback.py` | 11 passed（缺密钥回落平台端点保留租户身份与 dataset_ids、显式停用不回落） |
| 模型配置 RBAC | `tests/backend/test_issue059_model_config_rbac.py` | 7 passed（项目负责人绑定、编写人/只读 403） |
| RBAC 安全边界改写 | `tests/backend/test_admin_rbac_security_cleanup.py` | 8 passed（普通成员写操作 403、跨租户/平台配置 404；矛盾旧测试经主 Agent 裁定改写） |
| 止血回归 + 知识库重建 | `tests/backend/test_iss059_backend_hotfix.py` + `test_kb_admin` | 23 passed 2 skipped（`.pdf` 文件名+MIME 透传、422 `FILE_CONVERSION_FAILED` 先于数据集移动、skipped 为真实服务门控） |
| 真实 MySQL 复现 | `test_iss059_backend_hotfix.py` mysql 标记用例 | 2 passed（全量态 vs 热路径指纹一致；种子账号登录后可建项目、读 workspace，本机 3407 复现） |
| 进度写入一致性 | generation_session 组合测试 | 17 passed 2 skipped（save_job/update_job_progress 失败注入，内存与 MySQL 语义一致） |
| 导出门禁回归 | T28/T29/T30 测试文件 | 41 passed（`RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS` 门禁语义未削弱） |
| 主链路参考流 | `tests/backend/test_reference_flow.py` | 21 passed |
| OpenAPI 契约 | `export_openapi.py --check` | 100% 一致零漂移（`FILE_CONVERSION_FAILED` 冻结在契约内） |
| 前端指纹恢复 | `frontend/web/tests/unit/fingerprint-recovery.test.mjs` | 14 例全绿（自动刷新时机、409 恢复按钮、拉取失败零写入、恢复后自动保存、revision 冲突走合并） |
| 前端安全策略保存 | `frontend/web/tests/unit/platform-security-settings.test.mjs` | 7 例全绿（只上行改动字段、未读回快照禁止保存、刷新不丢草稿） |
| 部署静态验证 | `deploy/docker-compose.yml` | 健康检查 python 单行探针经编译验证；compose YAML 经解析验证；端口默认 `${ICG_BIND_HOST:-127.0.0.1}:8710:8710` |

## 未执行或受限（如实登记）

- 真实 RAGFlow 连通性：仍受 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 门控，本轮未执行；知识库测试为进程内 Fake RAGFlow，不能声称生产 RAGFlow 对接已验证。
- 真实模型连通性：仍受 `ICG_RUN_REAL_MODEL_TESTS=1` 门控，本轮未执行；涉密门禁验证基于配置判定逻辑单测，非真实端点。
- 前端测试为 jsdom/单元级，未做真实浏览器联调；指纹恢复按钮与平台安全策略保存未在真实浏览器走查。
- 部署卡未在真实目标机执行 `docker compose up` 观察 healthy/unhealthy 状态翻转；Nginx 反代 HTTPS 为文档示例，未在真实终端验证。
- 重庆中烟追踪号 `056a411dff69418f92eafbed9649791b` 原始现场在 `.audit` 中未找到，指纹死锁修复按复现场景与指纹生命周期分析验证，非原始现场回放。
- 后端聚焦回归全量组合（admin_rbac/mysql_gate/kb_admin/generation_session/parse_jobs/T28/T29/T30 + 新增安全测试 + model_config_glue/storage + ragflow_config_api）的最终 PR 实证以 PR 描述为准；本表登记的是各 subagent 已完成的验证口径。
- 后端全量 `python -m pytest tests/backend` 与前端全量 `pnpm --dir frontend/web test` 本轮未跑全量，存量失败口径未更新；QA 签署时须复跑。

## 链接

- 交付：[P0-SEC-MODEL-AUDIT-HOTFIX](../delivery/P0-SEC-MODEL-AUDIT-HOTFIX.md)、[P0-EXPORT-STATE-HOTFIX](../delivery/P0-EXPORT-STATE-HOTFIX.md)、[P0-CONFIG-KB-HOTFIX](../delivery/P0-CONFIG-KB-HOTFIX.md)、[P0-DEPLOY-HOTFIX](../delivery/P0-DEPLOY-HOTFIX.md)
- 任务卡：[P0-HOTFIX](../tasks/P0-HOTFIX.md)；Issue：[ISSUE-059](../../issues/ISSUE-059.md)


## 第四轮复扫收敛（2026-11-27）

- 后端聚焦：`tests/backend/test_issue059_round3_review.py` + `test_issue059_model_security.py` + `test_issue059_ragflow_fallback.py` + `test_issue059_security_depth.py`，43 passed。覆盖 `PUBLIC_MODEL_ENDPOINT_FORBIDDEN` 403、公网显式绑定 fail-closed、任务路由 system 池保存/运行一致、RAGFlow 停用阻断继承写入、首次保存掩码不覆写。
- 前端聚焦：`node --test tests/unit/structure-model-route.test.mjs tests/unit/model-config-access.test.mjs`，3 passed；`pnpm --dir frontend/web lint`（`tsc -b --noEmit`）通过。
- 契约：`python backend/bid-core/export_openapi.py --check` 100% 一致；`PUBLIC_MODEL_ENDPOINT_FORBIDDEN` 已冻结进错误表、冻结名单与 OpenAPI。
- 说明：前端全量测试的既有陈旧失败（公司设置/编排等）与本轮无关，未冒充通过；真实 RAGFlow/真实模型/真实浏览器仍未执行。


## 第五轮边界清零（2026-11-28）

- 新增公网备用模型回归：健康内网主模型正常调用，不合规公网备用在 provider 组装前被丢弃且零请求；新增 RAGFlow 显式清除/继承超时两项回归，公司租户沿用部署连接时也继承平台持久化超时；`test_issue059_model_security.py` + `test_issue059_round3_review.py` 27 passed。
- 完整后端聚焦回归：29 个文件 / 264 tests，`252 passed, 12 skipped, 0 failed`（4 分 41 秒）；skip 中 11 个为 mysql 标记、1 个为真实模型门控。
- MySQL 标记补跑：11 passed（127.0.0.1:3407，隔离合成 schema `icg_regression_20261128`）；其中种子账号热路径 2 个与模型配置 round-trip 1 个也在真实 `icg` 库复跑 3 passed。
- 回归口径修正：`test_model_config_provider.py` 的模型配置 setup 改用 platform_admin 并显式写入 alpha 租户，符合 PM 锁定权限；`test_parse_jobs.py` 孤儿任务用例阻断首个后台解析线程，消除版本竞争。两处均只改测试，不放松业务权限或门禁。
- 契约与前端：`python backend/bid-core/export_openapi.py --check` 100% 一致；`pnpm --dir frontend/web lint`（`tsc -b --noEmit`）通过；前端聚焦 `structure-model-route` + `model-config-access` 3 passed。

## 第六轮收尾清零（2026-11-28）

- 平台显式清除 RAGFlow 密钥后，继承链与平台停用同为终态；存在部署环境密钥时，无公司配置行与仅有 incomplete 公司行的租户均不再回落部署密钥，公司独立密钥优先序不变。
- 连续两次只改超时（90s → 120s）回归通过：未编辑密钥输入框时前端省略 `api_key` 字段，后端继承掩码响应保持一致，最终仍使用部署密钥且超时为 120s。
- 后端聚焦 `round3/ragflow_fallback/model_security/security_depth` 47 passed，`test_ragflow_config_api.py` 3 passed；前端 `ragflow-config-modal` 单元测试 5 passed、相关前端聚焦合计 8 passed；`tsc -b --noEmit` 与 production build 通过；OpenAPI 100% 一致，治理检查通过。
