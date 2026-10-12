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

敏感项目拒绝云端模型使用后台草案码 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。主密钥缺失使用 503 `SECRET_KEY_UNAVAILABLE`。当前 `require_allowed_model` 仍是 409 `LOCAL_MODEL_REQUIRED`，本轮不改。

## 局限

没有假服务器，也没有真实连接测试。依赖没有变化：`httpx==0.28.1` 已在仓库；Fernet 使用 ISSUE-023 已批准的 `cryptography`，本轮不调用。ISSUE-024 留给后台模型配置契约，本仓库不建详情。ISSUE-025 与 ISSUE-026 已有详情，分别为 MySQL CI 与基线计数，均为 in-review。ISSUE-027 留给后端 Word 样式卡，本仓库不建详情。本轮新建 ISSUE-028 与 ISSUE-029。PRD、ROADMAP、PROJECT_BRIEF 里的任务计数没有改。
