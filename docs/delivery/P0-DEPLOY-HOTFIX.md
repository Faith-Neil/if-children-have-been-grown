为什么有这个文件：记录 P0-DEPLOY-HOTFIX 容器健康检查修复与端口回环安全默认固化的实际完成内容、验收证据与遗留风险。

# P0-DEPLOY-HOTFIX 交付说明

| 项 | 内容 |
|---|---|
| 状态 | done；用户（人类 PM）已按 PR #56 合入指示收口 |
| Issue | [ISSUE-059](../../issues/ISSUE-059.md) |
| 任务卡 | [P0-HOTFIX](../tasks/P0-HOTFIX.md#p0-deploy-hotfix) |
| 代码说明 | [P0-DEPLOY-HOTFIX](../code/P0-DEPLOY-HOTFIX.md) |
| 验证登记 | [iss-059-p0-hotfix-verification](../testing/iss-059-p0-hotfix-verification.md) |

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | P0-DEPLOY-HOTFIX |
| 代码解释 | [代码说明](../code/P0-DEPLOY-HOTFIX.md)（compose/README 配置变更说明；无应用代码逻辑变化，按配置变更口径撰写） |
| 验收 | 健康检查 python 单行探针经编译验证通过、compose YAML 经解析验证通过；`/health` 端点真实存在且 `persistent=true` 判据与应用启动入口一致；`reference_flow` 21 passed 无回归。未在真实容器环境执行 docker compose up（本机非部署目标机）。 |
| 项目进度 | done。2026-11-28 用户（人类 PM）确认 PR #56 已合入 main（f18708c）并指示 ISSUE-059 收口：本卡标 done，Issue 标 closed；未发布。QA/PD 独立签署未执行，按 PM 明确指示作为例外收口；真实服务/容器等未验证局限仍以验证登记为准。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-11-27；P0 止血（无里程碑变更）；[ISSUE-059](../../issues/ISSUE-059.md)；[P0-HOTFIX 任务卡](../tasks/P0-HOTFIX.md#p0-deploy-hotfix)。
- 分支、提交、PR：分支 `feat/iss-059-p0-security-export-deploy-hotfix`；PR #56 已合入 main（f18708c）。
- 本地验收状态：静态验证通过（见验收结果）；真实容器编排未在本机执行。
- 合入 / 发布状态：已合入 main（f18708c）、未发布。

## 完成内容与变更文件

对应用户止血清单组 4（k/l），无范围偏差：

1. **(k) 容器健康检查修复**：`deploy/docker-compose.yml` 健康检查端点从不存在的 `/api/v1/health` 改为真实端点 `/health`，且断言 `persistent=true`——内存态（非持久化）视为 unhealthy，异常容器如实 unhealthy。健康检查 python 单行探针语法经编译验证、compose YAML 经解析验证。
2. **(l) 端口回环安全默认固化**：端口默认绑定改为 `${ICG_BIND_HOST:-127.0.0.1}:8710:8710`，消除明文 HTTP 默认暴露全部网卡；`deploy/README.md` 新增「3.1 端口暴露安全默认（反向代理 HTTPS）」节——含 Nginx 示例配置、`proxy_read_timeout` / `client_max_body_size` 要点、严禁 `0.0.0.0` 明文直暴警示、确需局域网直连时用 `ICG_BIND_HOST` 显式放开的方式；并修正 README 中健康检查 curl 路径为 `/health`。

## 代码解释

详见 [代码说明](../code/P0-DEPLOY-HOTFIX.md)。本卡无应用代码逻辑变化，代码说明按部署配置变更口径撰写：健康检查判据链、端口绑定语义与反向代理暴露路径。

## 验收结果

| 验收条目 | 执行方式 | 结果与证据 |
|---|---|---|
| 健康检查判据与实际启动入口一致：正常容器 healthy、非持久化或异常容器 unhealthy | 静态验证 | 探针目标 `/health` 为真实端点；python 单行探针经编译验证；compose YAML 经解析验证；`persistent=true` 断言与应用持久化门禁语义一致 |
| compose 端口默认 `127.0.0.1` 绑定；README 写明反代 HTTPS 暴露步骤与显式放开方式 | 静态审查 | `deploy/docker-compose.yml` 为 `${ICG_BIND_HOST:-127.0.0.1}:8710:8710`；`deploy/README.md` 第 3.1 节含 Nginx 示例、`proxy_read_timeout`/`client_max_body_size` 要点、`0.0.0.0` 明文直暴警示与 `ICG_BIND_HOST` 显式放开方式；密钥不入库纪律不变 |
| 不引入 Redis、不增加 worker，与既有三机部署底座一致 | 静态审查 | compose 服务清单无变化，仅健康检查与端口绑定两行级修改 |
| 应用行为无回归 | `tests/backend/test_reference_flow.py` | 21 passed |

未验证范围：未在真实目标机执行 `docker compose up` 观察 healthy/unhealthy 状态翻转（本机非部署目标机）；Nginx 反代配置为文档示例，未在真实 HTTPS 终端验证。

## 项目进度

done。2026-11-28 用户（人类 PM）确认 PR #56 已合入 main（f18708c）并指示 ISSUE-059 收口：本卡标 done，Issue 标 closed；未发布。QA/PD 独立签署未执行，按 PM 明确指示作为例外收口；真实服务/容器等未验证局限仍以验证登记为准。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响：部署安全默认属运维约束，不改变产品范围与业务规则 |
| ROADMAP | 无影响：不改变里程碑顺序，属当前主链路阻断止血 |
| ARCHITECTURE | 有影响：部署端口绑定（默认回环 + 反代 HTTPS）与健康检查判据（`/health` + `persistent=true`）为部署约束变化；ISSUE-059 六份基线同步表已登记「待处理」，由后续架构对齐任务或 PM 复核时落实正文 |
| Issue 看板/详情 | 已同步：ISSUE-059 验收条目 AC-11～AC-12 更新为实证，处理记录追加一行 |
| TASK_BOARD / PROJECT_STATUS | 已同步：看板本卡 done 并链接本交付；PROJECT_STATUS P0 段落同步四卡 done |
| DOCUMENT_INDEX | 已登记：本交付与代码说明条目（D-1101 / D-1105） |

## 风险与后续

- 端口默认改为回环绑定后，既有直接访问宿主机 IP:8710 的局域网部署会断——这是有意为之的安全默认；确需直连须显式设置 `ICG_BIND_HOST`，README 已写明放开方式。
- 健康检查断言 `persistent=true`：内存态容器会持续 unhealthy——这是止血语义（非持久化生产部署视为异常），编排重启策略会按此处理，运维须知悉。
- 真实容器编排验证（`docker compose up` 后 healthy 状态、反代 HTTPS 端到端）留待目标机部署时执行，QA 签署时可按 README 步骤复核。


## 第二轮补充（Devin Review 收口）

- 健康探针加固：`/health` 在 `persistent=true` 时执行轻量 `SELECT 1` 真探活 MySQL，探活失败按 unhealthy 处理（compose 健康检查随 URL 非 200/断言失败自动判定 unhealthy）；单测覆盖探活失败路径。
- 端口默认 `127.0.0.1` 绑定与 `/health` 探活判据已同步 `deploy/README.md` 第 3 节与 3.1 节；新增「2.1 RAGFlow 密钥轮换与实例切换操作顺序」：同实例轮换只改密钥不重建；跨实例切换必须显式新密钥（CWE-522 后端强制）并执行四库重建/迁移。
- 限制如实保留：真实容器编排翻转与真实 MySQL 断电探活仍未在目标机执行，AC-11 维持部分验证。

## 收口记录（2026-11-28）

PR #56 已合入 main（f18708c）。用户（人类 PM）明确指示 ISSUE-059 收口，本卡状态同步为 done；未发布。QA/PD 独立签署未执行，按 PM 明确指示作为例外收口；本文与验证登记中列明的真实 RAGFlow/真实模型/真实浏览器/真实容器编排未验证局限继续保留，不因收口而消除。
