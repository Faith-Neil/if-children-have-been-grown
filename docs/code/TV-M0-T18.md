为什么有这个文件：解释 TV-M0-T18 覆盖视图改动的代码。

# TV-M0-T18 代码说明

| 文件 | 说明 |
|---|---|
| [technical_rag.py](../../backend/bid-core/icg/domain/technical_rag.py) | `rag_summary()`：单节检索摘要，status 为 hit / empty / skipped / failed，带检索词、两库与本标命中数、前 3 条来源、原因与时间 |
| [technical_volume.py](../../backend/bid-core/icg/domain/technical_volume.py) | 每节任务补丁带 `rag`、`failure_reason`；重新生成清空上次的人工确认 |
| [technical_response_plan.py](../../backend/bid-core/icg/domain/technical_response_plan.py) | `coverage_rows()` 增加 digest_id、kind、score_item、score、rag、confirm_reasons、failure_reason、confirmed_at、retryable；`confirm_reasons()` 汇总生成失败、知识库无依据、废标约束待核、质量八条未达标 |
| [generation_orchestrator.py](../../backend/bid-core/icg/domain/generation_orchestrator.py) | `confirm_technical_task()`：只确认已生成的节；走 `_write`，项目只读成员 403 |
| [workflow.py](../../backend/bid-core/icg/api/workflow.py) | `POST /api/v1/projects/{project_id}/technical-tasks/{task_id}/confirm` |
| [workflow_schemas.py](../../backend/bid-core/icg/domain/workflow_schemas.py) | CoverageRow、ResponseTask 新字段；工作区带 `tender_digest` |
| [CoverageView.tsx](../../frontend/web/src/project/CoverageView.tsx) | 清单编号与评分标签、知识库检索列（悬浮看来源）、人工确认列与确认按钮、失败节重试、废标清单折叠面板 |
| [coverage-live.ts](../../frontend/web/src/project/coverage-live.ts) | 会话补丁合并 rag 与失败原因；`ragLabel()`；统计待人工确认 |
