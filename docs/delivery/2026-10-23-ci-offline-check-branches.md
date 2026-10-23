为什么有这个文件：记录修复 `.github/workflows/offline-check.yml` 的触发分支配置（包含 `main` 与 `feat/opencode-ICG`），恢复 GitHub Actions 持续集成自动验证能力。

它解决什么问题：解决因历史分支 `codex/repository-foundation` 删除后，推送代码至 `feat/opencode-ICG` 与 `main` 无法触发 CI 导致 checks 为 0 的问题。

# CI 工作流触发分支修复交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | CI-OFFLINE-CHECK-BRANCHES |
| 代码解释 | 见 [变更说明](#2-变更内容)；配置变更无需独立 code 文档 |
| 验收 | `.github/workflows/offline-check.yml` 的 `on.push` 与 `on.pull_request` 已配置 `main` 与 `feat/opencode-ICG`；本地预演通过；治理检查 0 错误通过 |
| 项目进度 | 第一步（① 修 CI 工作流）配置已就绪，推送到远端仓库触发 Actions 五大作业验证 |
<!-- task-delivery:end -->

## 1. 变更背景

DevOps 审查发现：
1. `.github/workflows/offline-check.yml` 的触发分支此前仅硬编码了 `codex/repository-foundation`；
2. 由于 `codex/repository-foundation` 分支已合并并删除，向合作主分支 `feat/opencode-ICG` 及 `main` 推送任何提交均不会触发 Actions 运行；
3. 远端 tip 长期处于 checks=0 状态，违背 CI 门禁治理原则。

## 2. 变更内容

文件：`.github/workflows/offline-check.yml`

```yaml
on:
  push:
    branches:
      - main
      - feat/opencode-ICG
  pull_request:
    branches:
      - main
      - feat/opencode-ICG
```

## 3. GitHub Actions 五大职能检查范围

触发后将自动执行以下五项作业：
1. **`backend`**：
   - Python 3.13.5 环境安装依赖；
   - `pytest tests/backend -q`（单元测试）；
   - `python tests/backend/session_live_http.py`（真实监听 HTTP 会话断言）；
   - `python tests/backend/qa_error_idempotency_live_http.py`（幂等与错误体断言）；
   - `smoke_t06.py`（T06 冒烟）；
   - `python backend/bid-core/export_openapi.py --check`（OpenAPI 契约一致性校验）。
2. **`backend-mysql`**：
   - 启动 Docker `mysql:8.4` 服务；
   - 动态生成 48 位强密码并配置；
   - 执行 `alembic upgrade head`；
   - 执行 `pytest tests/backend -m mysql`（持久化事务与连接复用断言）。
3. **`frontend`**：
   - Node.js 24.9.0 + pnpm 11.25.0；
   - `pnpm --dir frontend/web build`（类型检查与生产构建）；
   - `pnpm --dir frontend/web lint`（`tsc -b --noEmit`）；
   - `pnpm --dir frontend/web test`（370 项前端权威单测）。
4. **`governance`**：
   - CommonJS 测试套件回归；
   - `node scripts/check-project-governance.cjs`（514 份 Markdown 治理校验）。
5. **`e2e`**：
   - 安装 Chromium 驱动；
   - 运行 Playwright 端到端浏览器测试并上传 artifacts。

## 4. 本地验证与索引登记

- 本地治理测试：`node scripts/check-project-governance.cjs` 通过；
- 文档登记：登记入 `docs/DOCUMENT_INDEX.md`（D-721）。

## 5. 远端 Actions 运行排查与修复记录

1. **初次触发（Run ID `39911657851`，Commit `cfa4f23`）**：
   - `frontend`: 成功（耗时 51s）；
   - `governance`: 成功（耗时 17s）；
   - `backend-mysql`: 成功（耗时 1m48s）；
   - `backend`: 失败（`test_real_parsed_fact`、`test_same_unit_variable` 报 `PLACEHOLDER_RESIDUAL`；`test_outline_contract_draft` 报 `KeyError: 'deprecated'`）；
   - `e2e`: 因依赖失败被取消。

2. **根因定位与修复（Commit `9d6eace`）**：
   - **R34 合法变量误判修复**：在 `backend/bid-core/icg/domain/compliance_rules.py` 中，将 Handlebars 占位符正则表达式调整为 `\{\{(?!(?:fact|sla):)[^}]+\}\}`，排除合法的系统级事实标记 `{{fact:...}}` 与 SLA 承诺标记 `{{sla:...}}`；
   - **OpenAPI 废弃标记保留**：在 `backend/bid-core/export_openapi.py` 中，导出时保留已废弃过渡接口（`DEPRECATED_OPERATIONS`）的 `deprecated: true` 及说明文字，保证 `demo-v1.json` 与代码导出 100% 一致；
   - 本地全量回归：630 项后端测试全绿，370 项前端测试全绿。

3. **第二次触发（Run ID `39913789636`，Commit `9d6eace`）**：
   - `frontend`: 成功；
   - `governance`: 成功；
   - `backend-mysql`: 成功；
   - `backend`: **成功**（Pytest 630+全部通过，HTTP live 验收通过，T06 冒烟通过，OpenAPI 契约一致性 100% 通过）；
   - `e2e`: 在运行至 `Browser end-to-end` 步骤时触发原配置的 10 分钟硬上限（无缓存环境下安装 Chromium 依赖耗时约 8m40s），因此将 `e2e` 超时时间调整为 25 分钟（`timeout-minutes: 25`）。
