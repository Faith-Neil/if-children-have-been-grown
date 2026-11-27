为什么有这个文件：登记 P0 级安全红线、保存导出阻断、平台配置知识库与部署四类止血修复。

它解决什么问题：平台默认模型兜底可能把涉密正文发往公网、普通成员可越权读取审计日志、平台安全策略保存会覆盖其他已存项；有效合规检查被热路径误判过期阻断递交导出、重庆中烟项目保存/提交死锁、进度写入失败静默分裂；平台级 RAGFlow 配置未对下属公司生效、项目负责人无法绑定模型、知识库重建后已转换 Word 不可解析且转换失败误报 500、本机开发种子账号登录即失效；生产容器健康检查误报 unhealthy、端口默认暴露全部网卡。

# ISSUE-059：P0 安全红线、保存导出阻断与配置部署止血

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-059 |
| 类型 | bug |
| 优先级 | P0 |
| 状态 | in-review |
| 登记日期 | 2026-11-27 |
| 最后更新日期 | 2026-11-27 |
| revision | p0-security-export-deploy-hotfix-r1 |
| 关联 Task | [P0-SEC-MODEL-AUDIT-HOTFIX](../docs/tasks/P0-HOTFIX.md#p0-sec-model-audit-hotfix)、[P0-EXPORT-STATE-HOTFIX](../docs/tasks/P0-HOTFIX.md#p0-export-state-hotfix)、[P0-CONFIG-KB-HOTFIX](../docs/tasks/P0-HOTFIX.md#p0-config-kb-hotfix)、[P0-DEPLOY-HOTFIX](../docs/tasks/P0-HOTFIX.md#p0-deploy-hotfix) |
| 关联 PR | [PR #56](https://github.com/Faith-Neil/if-children-have-been-grown/pull/56)（OPEN，未合入） |
| 本地验收 | 开发自测已完成（2026-11-27）：4 个安全新测试文件 39 passed、`test_iss059_backend_hotfix` + `test_kb_admin` 23 passed 2 skipped、generation_session 组合 17 passed 2 skipped、真实 MySQL 复现 2 passed、reference_flow 21 passed、前端 fingerprint-recovery 14 例 + platform-security 7 例全绿、`export_openapi.py --check` 100% 一致；QA 签署 / PD 验收 / PM 确认未执行 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [P0-SEC-MODEL-AUDIT-HOTFIX](../docs/delivery/P0-SEC-MODEL-AUDIT-HOTFIX.md)、[P0-EXPORT-STATE-HOTFIX](../docs/delivery/P0-EXPORT-STATE-HOTFIX.md)、[P0-CONFIG-KB-HOTFIX](../docs/delivery/P0-CONFIG-KB-HOTFIX.md)、[P0-DEPLOY-HOTFIX](../docs/delivery/P0-DEPLOY-HOTFIX.md) |
| 代码 / 流程解释 | [P0-SEC-MODEL-AUDIT-HOTFIX](../docs/code/P0-SEC-MODEL-AUDIT-HOTFIX.md)、[P0-EXPORT-STATE-HOTFIX](../docs/code/P0-EXPORT-STATE-HOTFIX.md)、[P0-CONFIG-KB-HOTFIX](../docs/code/P0-CONFIG-KB-HOTFIX.md)、[P0-DEPLOY-HOTFIX](../docs/code/P0-DEPLOY-HOTFIX.md) |
| 验证记录 | [iss-059-p0-hotfix-verification](../docs/testing/iss-059-p0-hotfix-verification.md)（含局限：真实 RAGFlow/真实模型门控未验证、知识库为 Fake、前端 jsdom 单元级、部署未在目标机执行） |

## 现象与证据

用户 2026-11-27 要求基于 main 切出 `feat/iss-059-p0-security-export-deploy-hotfix`，对以下 4 组 12 项 P0 缺陷执行止血修复。本轮为生产阻断级缺陷，不引入新功能、不改变产品范围。

### 组 1：安全红线与策略覆盖（卡 P0-SEC-MODEL-AUDIT-HOTFIX，跨 BE/FE）

- (a) `backend/bid-core/icg/infra/model_config_storage.py`：① 平台模型兜底逻辑可能把公司正文经平台默认模型发往公网外部服务，违反 B5/B6 内网零外泄红线，必须封堵；② 在用公司模型无法轮换密钥（更新密钥被拦截），运维上无法定期换密；③ 平台默认模型判定逻辑误挡合规本地模型的涉密项目生成，把本可用的内网本地模型一并拒绝。
- (b) `backend/bid-core/icg/api/audit.py:54`：`GET /api/v1/audit-logs` 对非平台管理员只按 `company_id` 过滤，普通成员（编写人、只读、项目负责人）也能读取本公司审计日志，属 CWE-862 缺少授权；必须改为普通成员一律 403，仅 platform_admin 可读全局、company_admin 可读本公司。
- (c) `frontend/web/src/admin/PlatformSecurityPage.tsx:32`：保存平台安全策略时前端把整份本地 `settings`（含首次加载前的默认值）PATCH 回后端，会用前端默认值覆盖其他已存策略项；必须先读回真实服务端快照再合并提交，或改为只提交实际编辑字段。

### 组 2：保存导出阻断（卡 P0-EXPORT-STATE-HOTFIX，跨 BE/FE）

- (d) `backend/bid-core/icg/infra/repositories/hot_reads.py:251`：热路径按作用域读取时输入指纹所需的资料/SLA 模板条目未被完整加载，仍有效的合规检查被误判为「已过期」，阻断递交版导出。
- (e) 重庆中烟项目保存/提交死锁（追踪号 `056a411dff69418f92eafbed9649791b`）：来源变化后来源指纹未自动刷新，用户保存/提交互相拒绝形成死锁；除后端修复指纹自动刷新外，前端须提供「刷新最新来源并保留当前草稿重试」恢复按钮，保留用户已写内容。
- (f) `backend/bid-core/icg/domain/technical_volume_sessions.py:307`：进度写入失败时静默继续提交正文，造成任务进度与正文/状态分裂；进度写入失败必须如实失败或补偿，严禁静默继续。

### 组 3：平台配置与知识库（卡 P0-CONFIG-KB-HOTFIX）

- (g) `backend/bid-core/icg/api/ragflow.py:69`：平台级 RAGFlow 配置更新后未对下属公司实际生效，公司仍沿用旧配置或环境变量。
- (h) `backend/bid-core/icg/api/model_configs.py:76`：项目模型绑定端点误用 `require_platform_admin`，项目负责人（project_lead）无法按 ISSUE-056 之前的既有能力绑定本项目模型，须恢复项目负责人与公司管理员的绑定能力。
- (i) `backend/bid-core/icg/domain/kb_admin.py:497`：重建知识库后已转换 Word 文档无法解析（转换产物未随重建链路透传）；且 Word 转换失败时返回 500 而非 422 `FILE_CONVERSION_FAILED`，客户端无法区分业务失败与服务异常。
- (j) `backend/bid-core/icg/infra/repositories/hot_reads.py:205`：本机 MySQL 开发种子账号登录后立即失效——`read_auth_state` 作用域读取未完整还原本机种子账号/公司状态，登录态刚建即被判无效。

### 组 4：部署（卡 P0-DEPLOY-HOTFIX）

- (k) `deploy/docker-compose.yml:24`：健康检查指向错误或判据不当，正常运行的容器被报 unhealthy；须修复为探测 `/health` 且 `persistent=true` 才判健康。
- (l) 端口默认绑定 `127.0.0.1`：明文 HTTP 不得默认暴露全部网卡；须在 `deploy/docker-compose.yml` 与 `deploy/README.md` 固化「只绑回环 + 经宿主机反向代理以 HTTPS 对外」的安全默认。

## 影响与分流

- 影响范围：后端模型配置存储与运行时、审计日志授权、热路径作用域读取、技术卷会话进度写入、RAGFlow 与模型配置生效链、知识库重建与 Word 转换、部署编排与运维文档；前端平台安全策略保存与编辑台死锁恢复入口。
- 本轮为止血修复，不扩大产品范围、不改变角色体系与业务规则；涉密零外泄、多租户强隔离、`RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS` 导出门禁底线不得削弱。
- 不伪造真实 RAGFlow 或真实模型验证；真实连通性测试仍按既有环境变量门控，受阻如实记录。
- 依赖：本机真实 MySQL 可达；`deploy/` 与 `deploy/README.md` 已有未提交修改（组 4 实施进行中），协作时保留他人修改，严禁覆盖。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| [P0-SEC-MODEL-AUDIT-HOTFIX](../docs/tasks/P0-HOTFIX.md#p0-sec-model-audit-hotfix) | 组 1（a/b/c）：平台模型兜底不外泄、在用公司模型可轮换密钥、本地模型不误挡；审计日志授权 403；安全策略保存不覆盖 | `icg/infra/model_config_storage.py`、`icg/api/audit.py`、`frontend/web/src/admin/PlatformSecurityPage.tsx` | AC-01～AC-03 | in-review |
| [P0-EXPORT-STATE-HOTFIX](../docs/tasks/P0-HOTFIX.md#p0-export-state-hotfix) | 组 2（d/e/f）：热路径指纹误判过期、重庆中烟死锁与恢复按钮、进度写入失败不静默 | `icg/infra/repositories/hot_reads.py`、`icg/domain/technical_volume_sessions.py`、前端编辑台 | AC-04～AC-06 | in-review |
| [P0-CONFIG-KB-HOTFIX](../docs/tasks/P0-HOTFIX.md#p0-config-kb-hotfix) | 组 3（g/h/i/j）：平台 RAGFlow 配置生效、项目负责人绑定模型、知识库重建可解析与 422、种子账号登录持久 | `icg/api/ragflow.py`、`icg/api/model_configs.py`、`icg/domain/kb_admin.py`、`icg/infra/repositories/hot_reads.py` | AC-07～AC-10 | in-review |
| [P0-DEPLOY-HOTFIX](../docs/tasks/P0-HOTFIX.md#p0-deploy-hotfix) | 组 4（k/l）：容器健康检查修复、端口回环默认与反代 HTTPS 文档固化 | `deploy/docker-compose.yml`、`deploy/README.md` | AC-11～AC-12 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 平台模型兜底不再把公司正文发往公网外部服务；在用公司模型可轮换密钥；合规本地模型涉密生成不被误挡；有后端聚焦单测 | 已验证（开发自测）：`test_issue059_model_security.py` 15 passed——`config_compliant_for_sensitive()` 按 URL 判定公网端点，resolve_model_provider 四分支统一涉密校验；轮换链路固化（密文非确定性更新、MySQL diff 检出，轮换根因为 API 层 403，见 AC-08 修复）；本地模型不误挡、非本地门禁不削弱。真实模型端点未验证（门控） |
| AC-02 | 普通成员（编写人/只读/项目负责人）读取 `/api/v1/audit-logs` 一律 403；platform_admin 全局可读、company_admin 仅本公司可读；有授权矩阵单测 | 已验证（开发自测）：`test_issue059_audit_rbac.py` 6 passed，含跨公司查询 403 |
| AC-03 | 平台安全策略保存不用前端默认值覆盖其他已存策略项；保存后读回比对一致 | 已验证（开发自测）：`platform-security-settings.test.mjs` 7 例全绿——baseline/draft 双态、只上行 changedSecurityFields、未读回快照禁止保存、刷新不丢草稿；为 jsdom 单元级，未做真实浏览器联调 |
| AC-04 | 仍有效的合规检查不再被热路径误判过期；递交导出门禁按真实指纹判定，有回归单测 | 已验证（开发自测）：`apply_entries_by_json_field()` 以 JSON_EXTRACT+COLLATE utf8mb4_bin SQL 层精确匹配、指纹输入按 id 规范化排序；真实 MySQL 标记用例 2 passed（全量态 vs 热路径指纹一致）；修复前已生成的受影响指纹会安全显示一次 stale 后稳定（如实记录） |
| AC-05 | 重庆中烟追踪号 `056a411dff69418f92eafbed9649791b` 场景可复现并修复：来源指纹自动刷新；前端提供「刷新最新来源并保留当前草稿重试」恢复按钮，草稿内容不丢 | 已验证（开发自测）：`fingerprint-recovery.test.mjs` 14 例全绿——四时机自动刷新（原流式完成用生成前闭包旧指纹=必败指纹）、409 恢复按钮保留草稿重试、拉取失败零写入、恢复后自动保存；`.audit` 未找到追踪号原始现场，按复现场景修复（如实记录）；遗留：指纹仍含全项目章节 content/revision，建议后端契约演进 |
| AC-06 | 进度写入失败时不再静默继续提交正文，状态不分裂；有失败注入单测 | 已验证（开发自测）：generation_session 组合 17 passed 2 skipped——save_job 失败不启动线程落 failed、update_job_progress 失败取消后续正文写入、finally 二次异常不覆盖第一现场；内存与 MySQL 语义一致 |
| AC-07 | 平台级 RAGFlow 配置更新对下属公司实际生效，有生效链验证 | 已验证（开发自测）：`test_issue059_ragflow_fallback.py` 11 passed——`effective_ragflow_connection()` 缺密钥回落平台 system 端点/密钥/超时但保留公司租户身份与 dataset_ids、显式停用不回落、get_client 与 _configured_client 统一口径、api/ragflow.py 移除 10 处误加 require_platform_admin；真实 RAGFlow 未验证（门控），知识库测试为进程内 Fake |
| AC-08 | 项目负责人可绑定本项目模型；编写人/只读仍 403；敏感项目本地模型门禁不削弱 | 已验证（开发自测）：`test_issue059_model_config_rbac.py` 7 passed；model_configs.py 移除 9 行误加一刀切恢复既定设计；`test_admin_rbac_security_cleanup.py` 矛盾旧测试经主 Agent 裁定改写为真正安全边界（普通成员写 403、跨租户/平台配置 404）8 passed |
| AC-09 | 重建知识库后已转换 Word 可正常解析入库；Word 转换失败返回 422 `FILE_CONVERSION_FAILED` 而非 500 | 已验证（开发自测）：`test_iss059_backend_hotfix` + `test_kb_admin` 23 passed 2 skipped——已转换 PDF 用 .pdf 文件名+application/pdf、存量未转换先补转换、转换失败先于数据集移动/删除抛 422、`FILE_CONVERSION_FAILED` 冻结进 errors/frozen_error_codes/OpenAPI；顺带修复冻结名单漏收 COMPANY_NAME_DUPLICATED；OpenAPI `--check` 100% 一致 |
| AC-10 | 本机 MySQL 开发种子账号登录后会话持续有效，不立即失效 | 已验证（开发自测）：真实 MySQL 3407 复现 2 passed——种子账号登录后可建项目、读 workspace；`apply_development_seed_accounts()` 只填补缺失、不覆盖条目表真实账号、只接受 _DEMO_ONLY 种子，生产为空 |
| AC-11 | 正常运行的容器健康检查为 healthy，`persistent=true` 才判健康；异常容器如实报 unhealthy | 部分验证（开发自测）：探针端点已从不存在的 `/api/v1/health` 改为真实 `/health` 且断言 persistent=true；python 单行探针经编译验证、compose YAML 经解析验证；真实容器内 healthy/unhealthy 状态翻转未在目标机执行（诚实保留，留待 QA/部署复核） |
| AC-12 | `deploy/docker-compose.yml` 端口默认绑定 `127.0.0.1`；`deploy/README.md` 写明反向代理 HTTPS 暴露的安全默认与显式放开方式 | 已验证（静态审查）：端口默认 `${ICG_BIND_HOST:-127.0.0.1}:8710:8710`；README 新增「3.1 端口暴露安全默认（反向代理 HTTPS）」节含 Nginx 示例、proxy_read_timeout/client_max_body_size 要点、严禁 0.0.0.0 明文直暴警示与 ICG_BIND_HOST 显式放开方式；健康检查 curl 路径已修正 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响：止血修复不改变产品范围、角色或业务规则，只恢复既有规则的正确执行 | `docs/PRD.md` | p0-security-export-deploy-hotfix-r1 / ISSUE-059 / 2026-11-27 | 已核对 |
| ROADMAP | 无影响：不改变里程碑顺序，属于当前主链路阻断止血 | `docs/ROADMAP.md` | 同上 | 已核对 |
| ARCHITECTURE | 有影响：模型兜底安全边界、审计授权边界、部署端口绑定与健康检查约束变化 | `docs/ARCHITECTURE.md` | 同上 | 待处理 |
| TASK_BOARD | 有影响：新增四张 P0 止血任务卡 | `docs/TASK_BOARD.md` | 同上 | 已登记，持续同步 |
| PROJECT_STATUS | 有影响：记录本轮 P0 止血开工状态 | `docs/PROJECT_STATUS.md` | 同上 | 已登记，持续同步 |
| DOCUMENT_INDEX | 有影响：新增 Issue、任务卡模块与后续交付/代码说明条目 | `docs/DOCUMENT_INDEX.md` | 同上 | 已登记，持续同步 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-11-27 | p0-security-export-deploy-hotfix-r1 / in-progress | 已按用户要求切出 `feat/iss-059-p0-security-export-deploy-hotfix` 并登记 Issue 与四张任务卡；组 4 部署修复已在工作区开工 | 用户本轮指令 |
| 2026-11-27 | p0-security-export-deploy-hotfix-r1 / in-review | 四组修复实施进行中，Issue 登记提交复核；四张任务卡保持 in-progress，严禁标 done；待实施完成后补交付、验证并等待 QA/PD/PM | 治理登记 |
| 2026-11-27 | p0-security-export-deploy-hotfix-r1 / in-review | 四组 12 项修复实施完成，四张任务卡与看板原子同步为 in-review；交付、代码说明与验证登记已留档（4 安全测试 39 passed、hotfix+kb_admin 23 passed 2 skipped、真实 MySQL 2 passed、reference_flow 21 passed、前端 21 例全绿、OpenAPI 100% 一致）；AC-01～AC-10、AC-12 已验证（开发自测），AC-11 部分验证（静态通过、真实容器未执行）；局限如实登记：真实 RAGFlow/真实模型门控未验证、知识库为 Fake、前端 jsdom 单元级；建议 PM 在 QA 签署 + PD 产品验收后复核标 done，不标 done/closed | [验证登记](../docs/testing/iss-059-p0-hotfix-verification.md)；四份交付见 `docs/delivery/` |
| 2026-11-27 | p0-security-export-deploy-hotfix-r1 / in-review | 最后一轮 Devin Review 复扫收敛完成：`PUBLIC_MODEL_ENDPOINT_FORBIDDEN` 403 冻结与对话助手 HTTP 回归、公网显式绑定/路由 fail-closed、RAGFlow 停用写入阻断、首次保存掩码保护、任务路由 system 池保存/运行一致、平台管理员路由候选收口；聚焦后端 43 passed、前端聚焦 3 passed、`tsc` 通过、OpenAPI 100% 一致。仍不标 done/closed，待 QA/PD/PM | [验证登记](../docs/testing/iss-059-p0-hotfix-verification.md) 第四轮补充 |

## 本地验收与后续合入发布

- 本地验收结论与日期：2026-11-27 开发自测完成，四张任务卡 in-review；QA 独立签署、PD 产品验收与人类 PM 确认尚未执行。
- 验证方式、通过及失败项、未覆盖范围：见 [iss-059-p0-hotfix-verification](../docs/testing/iss-059-p0-hotfix-verification.md)；无失败项，skipped 均为真实服务门控跳过；未覆盖真实 RAGFlow/真实模型/真实浏览器/真实容器编排。
- 六份基线同步与互链复核：PRD/ROADMAP 无影响（止血修复不改产品范围与里程碑）；ARCHITECTURE 有影响（模型兜底安全边界、审计授权边界、部署端口绑定与健康检查约束），正文对齐待处理；TASK_BOARD/PROJECT_STATUS/DOCUMENT_INDEX 已同步。
- PR 状态：[PR #56](https://github.com/Faith-Neil/if-children-have-been-grown/pull/56) OPEN，未合入。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
