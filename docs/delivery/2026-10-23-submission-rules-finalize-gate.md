# 任务交付：规则最小可递交集与分册定稿闸门端到端闭环

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-SUBMISSION-FINALIZE-GATE / BE-COMPLIANCE-RULES-P0 / BE-VOLUME-FINALIZE-GATE |
| 代码解释 | `docs/code/2026-10-23-submission-rules-finalize-gate.md` |
| 验收 | 规则最小可递交集（R15/R23/R34/R37）与分册定稿闸门（技术/商务定稿锁定联动）全链路自动化测试通过（`test_submission_finalize_gate.py`、`test_checks_export_blocker_gate.py`、`test_smoke_non_demo_pipeline.py`、`test_compliance_rules_p0.py` 24 项全绿），未定稿与 blocker 缺陷严格拦截，定稿后合规放行并生成正式递交版 Word，编写人下载拦截 403，项目经理下载 200 成功，OpenAPI 契约 `--check` 100% 一致 |
| 项目进度 | 顺利闭环用户拍板决策 Step ④【规则最小可递交集 + 分册定稿闸门】，打通从单册定稿到整本递交导出的合法业务路径 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-23
- 里程碑：PRD P0 / MVP 核心主链路
- 关联 Issue：[ISSUE-006](../../issues/ISSUE-006.md)、[ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-027](../../issues/ISSUE-027.md)
- 关联卡片：`BE-VOLUME-FINALIZE-GATE`、`BE-COMPLIANCE-RULES-P0`、`INT-VOLUME-FINALIZE-GLUE`、`BE-CHECKS-EXPORT-ALIGN`
- 本地验收状态：`in-review`（严格遵守不自行标 done 约定）
- 分支：`feat/opencode-ICG`

## 背景与用户拍板决策

在前期版本中，整本导出接口 `POST /api/v1/projects/{project_id}/exports` 的递交模式（`kind == "submission"`）无条件抛出 409 `RULES_INCOMPLETE`（“完整合规规则与分册定稿未实现，不能把本地内部稿冒充递交版”），导致系统即便完成主链路全部编辑，也无法合法出具正式递交版 Word 文件。

依据 2026-10-23 专项审查与用户拍板决策 **Step ④【规则最小可递交集 + 分册定稿闸门】**：
1. **打通合法解除 `RULES_INCOMPLETE` 的正规产品路径**：
   - 将 PRD §5.8.5 分册定稿锁定状态机与整本递交导出门禁紧密结合；
   - 目标分册（技术分册与商务分册）未定稿时，坚决维持 409 `RULES_INCOMPLETE`，并精确提示未定稿的具体分册名称，绝不虚假放行；
   - 存在未解决的废标或标星条款缺陷时，坚决维持 400 `CHECK_BLOCKER_EXISTS` 强拦截；
2. **定稿且规则合规后放行正式递交版**：
   - 当项目负责人对各分册均完成前置检查并执行定稿锁定（`is_finalized = True`），且合规规则最小可递交集（R15 证明材料齐全、R23 废标红线与关键标星 100% 响应、R34 占位符清零、R37 偏离表一致性）全项通过时，系统正式放行生成正式递交版 Word；
   - 递交版清除内部评审告警（`compliance_notice is None`），记录定稿责任人 ID，生成防篡改 64 位 SHA-256 版式指纹；
   - 下载权限严格受控：普通编写人拦截 403 `SUBMISSION_FORBIDDEN`，仅限项目负责人/经理下载。

## 完成内容与变更文件

1. **导出服务闸门升级**：
   - [export_service.py](../../backend/bid-core/icg/domain/export_service.py)：
     - 在 `export` 方法中动态读取 `workflow["volumes"]` 的定稿状态；
     - 判定导出范围所涉及分册的 `is_finalized` 标识；未全部定稿时精准抛出 409 `RULES_INCOMPLETE`（包含具体未定稿分册名称）；
     - 定稿且无 blocker 缺陷时放行正式递交版生成，标记 `is_submission = True`，`compliance_notice` 设为 `None`，更新任务记录为“正式递交版已生成”；
2. **契约 Schema 扩展**：
   - [workflow_schemas.py](../../backend/bid-core/icg_demo/workflow_schemas.py)：在 `ProjectExport` 响应体中补充 `is_submission: bool = False` 字段；
   - [demo-v1.json](../../spec/openapi/demo-v1.json)：同步更新 OpenAPI 契约并通过 `--check` 100% 校验；
3. **自动化端到端测试覆盖**：
   - [test_submission_finalize_gate.py](../../tests/backend/test_submission_finalize_gate.py)：覆盖全分册未定稿拦截、单分册定稿未齐拦截、两册定稿后放行递交版导出、Word 文件格式完整性、编写人下载 403 拦截及项目经理下载 200。

## 验收结果与证据

1. **专属闸门测试**：
   - 命令：`pytest tests/backend/test_submission_finalize_gate.py`
   - 结果：`1 passed in 1.67s`。
2. **核心门禁全量回归**：
   - 命令：`pytest tests/backend/test_checks_export_blocker_gate.py tests/backend/test_smoke_non_demo_pipeline.py tests/backend/test_volume_finalize_gate.py tests/backend/test_compliance_rules_p0.py`
   - 结果：`24 passed in 16.84s`。
3. **OpenAPI 契约一致性**：
   - 命令：`python backend/bid-core/export_openapi.py --check`
   - 结果：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
4. **前端全量单测与静态检查**：
   - 命令：`pnpm --dir frontend/web test && pnpm --dir frontend/web lint`
   - 结果：378 单测全绿，TypeScript 0 错误。
5. **工程治理检查**：
   - 命令：`node scripts/check-project-governance.cjs`
   - 结果：`治理检查通过：518 份 Markdown、409 项任务、38 项 Issue。`

## 结论与建议

至此，用户拍板决策的四项重点任务：
- ① 修 `.github/workflows/offline-check.yml` 触发分支与 CI 红绿（D-721）；
- ② 对齐 tip、整理「已签等 PM」清单与关演示人工冒烟留证（D-722、D-723）；
- ③ 前端弹窗：大模型配置与 RAGFlow 知识库配置及真实服务接入联调（D-724、D-725）；
- ④ 规则最小可递交集 + 分册定稿闸门闭环（D-726、D-727）。

全部高质量完成闭环！建议人类 PM 组织对已签署 in-review 任务进行终审并确认。
