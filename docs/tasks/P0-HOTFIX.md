为什么有这个文件：把 ISSUE-059 的 P0 安全红线、保存导出阻断、平台配置知识库与部署止血修复拆成可验收任务卡。

它解决什么问题：避免止血修复只改代码不登记看板，或未经 QA/PD/PM 验收就标 done。

# P0-HOTFIX：P0 安全/导出/配置/部署止血

日期：2026-11-27。关联 [ISSUE-059](../../issues/ISSUE-059.md)。分支 `feat/iss-059-p0-security-export-deploy-hotfix`。

四张卡均为 in-review（2026-11-27 实施完成提交复核）。最高只能到 in-review，严禁标 done；done 须 QA 签署 + PD 产品验收 + 人类 PM 最终确认。涉密零外泄、多租户强隔离与 `RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS` 导出门禁底线不得因止血修复削弱。四卡交付与代码说明见 `docs/delivery/` 与 `docs/code/` 同名文档，验证口径登记于 [iss-059-p0-hotfix-verification](../testing/iss-059-p0-hotfix-verification.md)。

<a id="p0-sec-model-audit-hotfix"></a>

## P0-SEC-MODEL-AUDIT-HOTFIX · 平台模型安全红线、密钥轮换与审计授权/策略保存止血

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-059](../../issues/ISSUE-059.md) |
| 依赖 | — |
| 来源 | 用户 2026-11-27 P0 止血清单组 1（a/b/c），跨 BE/FE |
| 完成时交付 | `docs/delivery/P0-SEC-MODEL-AUDIT-HOTFIX.md` |
| 代码解释 | `docs/code/P0-SEC-MODEL-AUDIT-HOTFIX.md` |

范围：① `backend/bid-core/icg/infra/model_config_storage.py` 封堵平台模型兜底把公司正文发往公网外部服务的路径（B5/B6 内网零外泄红线），修复在用公司模型无法轮换密钥的拦截，修复平台默认模型判定误挡合规本地模型涉密生成；② `backend/bid-core/icg/api/audit.py:54` 审计日志授权收口：普通成员（编写人/只读/项目负责人）读取一律 403（CWE-862），仅 platform_admin 可读全局、company_admin 可读本公司；③ `frontend/web/src/admin/PlatformSecurityPage.tsx:32` 保存平台安全策略不得用前端默认值覆盖其他已存策略项，改为基于服务端真实快照合并或只提交实际编辑字段。

可验证验收：

- [x] 平台兜底路径在涉密/公司正文场景绝不选择公网外部模型，有后端聚焦单测。
- [x] 在用公司模型可轮换密钥，旧密钥更新后运行时即刻生效。
- [x] 合规本地模型的涉密项目生成不被平台默认模型判定误挡；非本地模型涉密门禁不削弱。
- [x] 普通成员读 `/api/v1/audit-logs` 返回 403；platform_admin 全局、company_admin 本公司可读，有授权矩阵单测。
- [x] 平台安全策略保存后其他未编辑策略项保持服务端原值，读回比对一致。

<a id="p0-export-state-hotfix"></a>

## P0-EXPORT-STATE-HOTFIX · 检查过期误判、保存提交死锁恢复与进度写入一致性止血

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-059](../../issues/ISSUE-059.md) |
| 依赖 | — |
| 来源 | 用户 2026-11-27 P0 止血清单组 2（d/e/f），跨 BE/FE |
| 完成时交付 | `docs/delivery/P0-EXPORT-STATE-HOTFIX.md` |
| 代码解释 | `docs/code/P0-EXPORT-STATE-HOTFIX.md` |

范围：① `backend/bid-core/icg/infra/repositories/hot_reads.py:251` 热路径作用域读取补齐输入指纹所需的全部资料与 SLA 模板条目，仍有效的合规检查不得被误判过期而阻断递交导出；② 重庆中烟项目保存/提交死锁（追踪号 `056a411dff69418f92eafbed9649791b`）：来源变化后来源指纹自动刷新，前端编辑台提供「刷新最新来源并保留当前草稿重试」恢复按钮，用户草稿内容不丢；③ `backend/bid-core/icg/domain/technical_volume_sessions.py:307` 进度写入失败严禁静默继续提交正文或造成任务进度与正文/状态分裂，失败须如实上抛或补偿一致。

可验证验收：

- [x] 有效合规检查不再被误判过期，递交导出门禁按真实输入指纹判定，有回归单测。
- [x] 追踪号场景复现并修复：指纹自动刷新；恢复按钮保留当前草稿重试成功，有前后端证据。
- [x] 进度写入失败注入测试：不静默提交正文，状态不分裂，错误如实可读。
- [x] `RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS` 门禁语义不被削弱，诚实记录任何剩余阻断。

<a id="p0-config-kb-hotfix"></a>

## P0-CONFIG-KB-HOTFIX · 平台配置生效、项目负责人绑模型、知识库重建与种子账号止血

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-059](../../issues/ISSUE-059.md) |
| 依赖 | — |
| 来源 | 用户 2026-11-27 P0 止血清单组 3（g/h/i/j） |
| 完成时交付 | `docs/delivery/P0-CONFIG-KB-HOTFIX.md` |
| 代码解释 | `docs/code/P0-CONFIG-KB-HOTFIX.md` |

范围：① `backend/bid-core/icg/api/ragflow.py:69` 平台级 RAGFlow 配置更新后对下属公司实际生效，公司运行时不再沿用旧配置或环境变量；② `backend/bid-core/icg/api/model_configs.py:76` 恢复项目负责人绑定本项目模型能力（现误用 `require_platform_admin`），公司管理员保持可绑定，编写人/只读仍 403；③ `backend/bid-core/icg/domain/kb_admin.py:497` 重建知识库后已转换 Word 文档可正常解析入库（转换产物随重建链路透传），Word 转换失败返回 422 `FILE_CONVERSION_FAILED` 而非 500；④ `backend/bid-core/icg/infra/repositories/hot_reads.py:205` 修复本机 MySQL 开发种子账号登录后立即失效：`read_auth_state` 作用域读取完整还原种子账号与公司状态，登录态持续有效。

可验证验收：

- [x] 平台级 RAGFlow 配置更新后下属公司检索/摄入链路使用新配置，有生效链验证。
- [x] 项目负责人绑定项目模型成功；编写人/只读 403；敏感项目本地模型门禁不削弱。
- [x] 重建知识库后已转换 Word 可解析；转换失败返回 422 且有单测。
- [x] 本机 MySQL 种子账号登录后会话持续有效，聚焦复测通过。

<a id="p0-deploy-hotfix"></a>

## P0-DEPLOY-HOTFIX · 容器健康检查修复与端口回环安全默认固化

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 3小时 |
| 关联 Issue | [ISSUE-059](../../issues/ISSUE-059.md) |
| 依赖 | — |
| 来源 | 用户 2026-11-27 P0 止血清单组 4（k/l） |
| 完成时交付 | `docs/delivery/P0-DEPLOY-HOTFIX.md` |
| 代码解释 | `docs/code/P0-DEPLOY-HOTFIX.md` |

范围：① `deploy/docker-compose.yml:24` 修复健康检查：正常运行的容器不应报 unhealthy，探测 `/health` 且 `persistent=true` 才判健康，异常容器如实 unhealthy；② 端口默认绑定 `127.0.0.1`，明文 HTTP 不默认暴露全部网卡；在 `deploy/docker-compose.yml` 与 `deploy/README.md` 固化「只绑回环 + 宿主机反向代理（Nginx/Caddy）以 HTTPS 终止后转发」的安全默认，并写明确需局域网直连时的显式放开方式。

可验证验收：

- [ ] 健康检查判据与实际启动入口一致：正常容器 healthy、非持久化或异常容器 unhealthy。（探针目标 `/health` 与 `persistent=true` 判据一致性、python 单行语法与 compose YAML 已静态验证；真实容器内 healthy/unhealthy 状态翻转未在目标机执行，留待 QA/部署复核）
- [x] compose 端口默认 `127.0.0.1` 绑定；`deploy/README.md` 写明反代 HTTPS 暴露步骤、密钥不入库与显式放开方式。
- [x] 不引入 Redis、不增加 worker，与既有三机部署底座一致。
