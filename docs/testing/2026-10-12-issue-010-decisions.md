为什么有这个文件：留下 ISSUE-010 关闭时核对过的决定，以及没有跑过的运行时。

它解决什么问题：避免把设计文档或配置页清单写成模型已经接通。

# 2026-10-12 ISSUE-010 决定核对

日期：2026-10-12。关联 [ISSUE-010](../../issues/ISSUE-010.md)、[AI-01](../tasks/AI-M0.md#ai-01)、[ISSUE-028](../../issues/ISSUE-028.md)、[ISSUE-029](../../issues/ISSUE-029.md)。

## 结论

三件用户决定已写入 ISSUE-010，该 Issue 改为 closed。AI-01 改为 in-review。真实端点、真实 RAGFlow 和配置页都没有实现，AI-01 不标 done。

核对方式是阅读决定原文、现有适配器、检索口、内网草案和 RAGFlow 公开发布的 HTTP API。没有连接内网，没有调用模型，没有改 `backend/bid-core` 或 `spec/openapi/demo-v1.json`。

并入 `763064a` 之后 `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：213 份 Markdown、362 项任务、27 项 Issue。」检查程序未修改。没有因此重跑 pytest：本轮不改后台代码。PRD、ROADMAP、PROJECT_BRIEF 保持 ISSUE-025 写下的 362 项、7 in-review、50 blocked。看板因 AI-01 从 blocked 改为 in-review，为 362 项：26 done、8 in-review、7 in-progress、268 planned、49 blocked、4 ready。

## 对照

| 决定 | 落点 |
|---|---|
| 对话模型由配置页提供，可切换本地与云端，默认流式，支持 JSON 模式 | [配置设计](../architecture/model-config-provider.md) |
| 嵌入与向量库用 RAGFlow 自带，检索层去连 RAGFlow | [适配器设计](../architecture/ragflow-retrieval-adapter.md) |
| 生产生成只在内网，开发与测试可以出网 | 同上，并与 [内网草案](../operations/intranet-deployment-plan.md) 第 7 节一致 |

敏感项目拒绝云端模型使用 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，留在 Provider 侧。当前 `require_allowed_model` 仍是 409 `LOCAL_MODEL_REQUIRED`，本轮不改。

## 局限

没有假服务器，也没有真实连接测试。依赖没有变化：`httpx==0.28.1` 已在仓库。ISSUE-024 已存在，由后台建档并拥有模型配置字段。ISSUE-025 与 ISSUE-026 已有详情。ISSUE-027 随后已由后端建档，是 Word 版式，本记录不改它。本轮新建 ISSUE-028 与 ISSUE-029。关闭 ISSUE-010 时 PRD、ROADMAP、PROJECT_BRIEF 的任务计数没有改。

PM 随后把范围拆开：ISSUE-028 只保留 Provider 读取配置、启动快照、local/cloud 路由、敏感项目约束、流式与 JSON 模式、错误映射和 `job.model_call`。存储、字段定义、API、加密、If-Match 和幂等归 ISSUE-024。ISSUE-024 已由后台建档，状态 new，拥有模型配置字段。流式与 JSON 模式开关的字段名只链接 [ISSUE-024](../../issues/ISSUE-024.md) 的 [`stream_enabled`](../../issues/ISSUE-024.md) 与 [`json_mode_enabled`](../../issues/ISSUE-024.md)。ISSUE-028 不重定义。这次拆分不改任务计数。
