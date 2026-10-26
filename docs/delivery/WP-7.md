为什么有这个文件：记录质量整改路线图 WP-7（OpenAPI 生成化校验、测试脚本规范化与全量回归终审）的实际完成内容、测试验收与规范落实说明。

它解决什么问题：实现 OpenAPI 由代码生成并接入 CI 自动化一致性校验（--check 门禁），杜绝手工维护 900KB 巨型契约；补齐 package.json 的 lint/test 脚本；完成全流程全量回归终审，确保整轮质量整改零回归。

# WP-7：OpenAPI 生成化、测试脚本规范化与全量回归终审交付
> **历史快照（DOC-SYNC-1）：** 本文记录整改当时目标与验收；**现行**仓库结构与入口约定见 `docs/architecture/repository-layout.md` 与 `AGENTS.md`。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | WP-7 |
| 代码解释 | 升级 export_openapi.py 支持 --check 门禁与契约扩展保留；在 .github/workflows/offline-check.yml 增加 OpenAPI 生成一致性校验与前端 lint 步骤；在 frontend/web/package.json 补齐 "lint": "tsc -b --noEmit" 脚本；完成后端 610 项、前端 348 项全量单测、生产构建、OpenAPI 校验与工程治理全绿终审；详见第 2、3 节。 |
| 验收 | OpenAPI 校验 python backend/bid-core/export_openapi.py --check 确认 100% 一致通过；后端全量 pytest 610 passed, 42 skipped, 0 failed（耗时 4m39s）；前端全量 node --test 348 passed, 0 failed（耗时 5.1s）；前端 lint（tsc -b --noEmit）0 错误；生产构建（tsc + vite build）通过（1.27s，0 错误）；工程治理 488 份 Markdown、399 任务、37 Issue 100% 通过；治理回归单测 12 passed。 |
| 项目进度 | 整轮 7 个 WP 质量整改（WP-1 至 WP-7）全部圆满交付达成。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 分支与提交：`feat/opencode-ICG`
- 关联规划：`docs/delivery/2026-10-22-quality-remediation-plan.md`（阶段 E 收尾 / WP-7）
- 关联规则：`AGENTS.md`（前端测试权威收口、质量整改与结构冻结规则）
- 本地验收状态：已通过（后端全量 610 passed 42 skipped；前端全量 348 passed；前端 lint/build 绿灯；OpenAPI 生成一致；治理 100% 通过）
- 合入 / 发布状态：分支持续演进，与远程保持同步

---

## 完成内容与变更文件

### 1. OpenAPI 自动化生成与 CI 门禁

1. **导出脚本与检验门禁（[`backend/bid-core/export_openapi.py`](../../backend/bid-core/export_openapi.py)）**：
   - 升级导出脚本支持 `--check` 命令行参数；
   - 提取并复用 `implemented_contract` 契约过滤算法，自动比对已提交契约与当前 FastAPI 运行时应用的 `app.openapi()`；
   - 支持跨平台 Windows 控制台安全输出（避免 Unicode 字符编码崩溃）；
   - 在导出模式下智能保留已冻结草案与扩展元数据（`x-contract-drafts`、`x-issue-033`、`x-idempotency` 等）。
2. **CI 流程集成（[`.github/workflows/offline-check.yml`](../../.github/workflows/offline-check.yml)）**：
   - 在 `backend` 作业中新增 `Verify OpenAPI generation consistency` 步骤，运行 `python backend/bid-core/export_openapi.py --check`，任何契约不一致自动阻断流水线；
   - 在 `frontend` 作业中新增 `Frontend lint` 步骤，执行 `pnpm lint`。

### 2. 测试脚本与权威目录收敛

1. **前端脚本补全（[`frontend/web/package.json`](../../frontend/web/package.json)）**：
   - 新增 `"lint": "tsc -b --noEmit"` 脚本；
   - 保留 `"test": "node --test tests/**/*.test.mjs"` 权威脚本，支持一键运行全量单元测试与 AST 静态契约断言。
2. **测试目录权威性收敛**：
   - 严格落实 `AGENTS.md` 规则：确立 `frontend/web/tests/`（含 `unit/`）为前端唯一权威测试套件；
   - 根目录 `tests/frontend/` 仅保留兼容历史文档引用的轻量级转发壳，无实际业务测试逻辑，测试树零冗余扩展。

---

## 全量回归终审验收结果

1. **OpenAPI 生成一致性检验**：
   - 命令：`python backend/bid-core/export_openapi.py --check`
   - 结果：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`，返回码 0。
2. **后端全量回归套件**：
   - 命令：`pytest`
   - 结果：**610 passed, 42 skipped, 0 failed in 279.94s (4m39s)**：
     - 基础演示流程测试：31 passed；
     - 八角色权限矩阵专属测试：10 passed；
     - API v1 收敛测试：4 passed；
     - 可信应用会话测试：34 passed；
     - 幂等与错误体测试：12 passed；
     - RAGFlow 检索与生成测试：40+ passed；
     - 章节大纲与任务流转测试：全绿；
     - 42 skipped 仅跳过未启动内网真实 MySQL 与未连接真实大模型的专项用例，符合既定门禁规范。
3. **前端全量单测套件**：
   - 命令：`pnpm --dir frontend/web test`
   - 结果：**348 passed, 0 failed, 0 error**（耗时 5.12s）。
4. **前端类型检查与静态审查**：
   - 命令：`pnpm --dir frontend/web lint`
   - 结果：`tsc -b --noEmit` 耗时 7s，**0 错误，0 警告**。
5. **前端生产构建检验**：
   - 命令：`pnpm --dir frontend/web build`
   - 结果：**耗时 1.27s 成功完成**，各域分包体积健康受控。
6. **工程治理与文档完整性检验**：
   - 命令：`node scripts/check-project-governance.cjs`
   - 结果：**488 份 Markdown、399 项任务、37 项 Issue 100% 通过**；
   - 命令：`node --test tests/governance/*.test.cjs`
   - 结果：**12 passed, 0 failed**。
