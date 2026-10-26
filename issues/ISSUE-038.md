为什么有这个文件：记录质量整改方案交付后排期处理的结构性技术债务。

它解决什么问题：集中跟踪 suggestions 双错误体收敛、EditorPage 与 workflow_orchestrator 二次细粒度拆解瘦身，以及 icg/api 与 icg/app 骨架子包的后续填充处置。

# ISSUE-038：质量整改后遗留结构债务收敛（双错误体、巨石二次瘦身与空包处置）

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-038 |
| 类型 | change |
| 优先级 | P2 |
| 状态 | new |
| 登记日期 | 2026-10-22 |
| 最后更新日期 | 2026-10-22 |
| revision | 1 |
| 关联 Task | [BE-TECH-DEBT-01](../docs/TASK_BOARD.md#be-tech-debt-01)、[FE-TECH-DEBT-01](../docs/TASK_BOARD.md#fe-tech-debt-01)、[BE-TECH-DEBT-02](../docs/TASK_BOARD.md#be-tech-debt-02)；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | 未创建 |
| 本地验收 | 未执行 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 待建立 |
| 代码 / 流程解释 | 待建立 |
| 验证记录 | 待执行 |

## 现象与证据

在 2026-10-22 质量整改方案（WP-1 至 WP-7）主体落地后，经过代码走查与合入前抽查，发现以下待后续进一步深化的架构债务：
1. **`/api/chapters/{id}/suggestions` 双错误体兼容分支**：
   - 现状：在 `backend/bid-core/icg_demo/main.py` 的 `error_response` 中，针对 suggestions 端点仍保留了兼容旧单测断言的 `content["error"] = {"code": code, "message": message}` 及 `content["request_id"] = request_id`。
   - 目标：彻底收敛为全局统一规范错误体 `{"code": ..., "message": ..., "details": ..., "traceId": ...}`，并同步修正 `test_openai_compatible_model.py` 等单测对旧结构字段的直接断言。
2. **重点巨石组件/模块二次瘦身**：
   - `frontend/web/src/editor/EditorPage.tsx`：经 WP-3 初步拆分后当前约 1051 行，仍聚集了较多复杂的编辑交互、版本 Diff 与建议采纳状态机逻辑，宜进一步抽离独立 hooks 与交互子面板。
   - `backend/bid-core/icg/domain/workflow_orchestrator.py`：从 `workflow.py` 拆出后当前约 792 行，仍承载了较重的编排事务，可按阶段拆解为独立子服务。
3. **`icg/api/` 与 `icg/app/` 骨架子包处置**：
   - 当前 `backend/bid-core/icg/api/` 与 `backend/bid-core/icg/app/` 仅有 `__init__.py` 说明文档，尚待在主干路由与应用装配迁移时实际填充，或依据分包演进节奏统一管理。

## 影响与分流

- 影响范围：后端异常体系统一性、单测断言、前端 EditorPage 代码可维护性、后端服务解耦度。
- 本次处理范围：在整改方案主线 WP-1 ~ WP-7 合入后作为独立改进项排期，避免在本轮合入前引发大面积单测断言连带改动。
- 依赖与阻塞解除条件：依赖 WP-1 ~ WP-7 基线合入。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-TECH-DEBT-01 | 收敛 suggestions 双错误体至规范体 | `backend/bid-core/icg_demo/main.py`、`tests/backend/test_openai_compatible_model.py` | AC-01 | in-review |
| FE-TECH-DEBT-01 | EditorPage.tsx 状态机与子面板二次拆分（目标 < 600 行） | `frontend/web/src/editor/EditorPage.tsx` | AC-02 | planned |
| BE-TECH-DEBT-02 | workflow_orchestrator.py 服务细化与 icg/api、icg/app 填充 | `backend/bid-core/icg/` | AC-03 | planned |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | suggestions 接口在异常时仅返回单一标准错误体（无根级 error 与 request_id 冗余），全量单测通过 | 未执行 |
| AC-02 | EditorPage.tsx 单文件行数降至 600 行以内，前端 348 项测试全绿且交互无回归 | 未执行 |
| AC-03 | workflow_orchestrator.py 单文件行数降至 500 行以内，icg/api 与 icg/app 充实实际分层代码 | 未执行 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响：内部重构与代码整洁度，不改变用户功能契约 | 无 | ISSUE-038 / 2026-10-22 | 已核对 |
| ROADMAP | 有影响：计入技术债务消除与架构演进里程碑 | `docs/ROADMAP.md` | ISSUE-038 / 2026-10-22 | 已核对 |
| ARCHITECTURE | 有影响：后端应用组装分层与前端组件边界深化 | `docs/ARCHITECTURE.md` | ISSUE-038 / 2026-10-22 | 已核对 |
| TASK_BOARD | 有影响：登记后续技术债务清理任务 | `docs/TASK_BOARD.md` | ISSUE-038 / 2026-10-22 | 已核对 |
| PROJECT_STATUS | 有影响：记录为合入后待办 Issue | `docs/PROJECT_STATUS.md` | ISSUE-038 / 2026-10-22 | 已核对 |
| DOCUMENT_INDEX | 有影响：索引登记 ISSUE-038 | `docs/DOCUMENT_INDEX.md` | ISSUE-038 / 2026-10-22 | 已核对 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-22 | 1 / new | 依据抽查评审登记质量整改后遗留技术债务，待主干合入后开工 | 抽查评审意见 |
