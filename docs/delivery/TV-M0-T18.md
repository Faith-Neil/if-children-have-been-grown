为什么有这个文件：记录技术服务方案精简主路径 B 组（覆盖视图）交付。

# TV-M0-T18 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 代码 | [TV-M0-T18](../code/TV-M0-T18.md) |

## 实际变更

- 覆盖视图即矩阵：每行显示清单编号（T / S）、评分项与分值、目标章节、生成状态、知识库检索摘要、人工确认原因。
- 失败节显示原因并可单节重试；已生成且有确认原因的节可人工确认。
- 新增人工确认接口；项目只读成员确认与重试均被后端拒绝（403）。
- 废标清单以折叠面板展示，标明正文硬约束。
- 评审修复：确认须有本章编辑权；单节重试按任务编号定位，同名小节不受影响；整卷写入只替换本次重写的任务，生成期间的人工确认不被覆盖。
- 用户决定（2026-11-24）：重新生成时保留第一个目录标题之前的引言；人工确认时记下本节正文指纹，之后正文被改过则确认作废，覆盖视图提示「确认后正文已修改」。

## 验收证据

- `tests/backend/test_technical_coverage_view.py` 与 `tests/backend/test_technical_digest.py`：13 passed。
- `frontend/web/tests/unit/coverage-live.test.mjs`：7 passed；`pnpm lint` 通过。
- `export_openapi.py --check` 一致。
- 只用模型替身验证；未连内网 Qwen / RAGFlow。

## 同步

PRD、ROADMAP、ARCHITECTURE：无改动，按 [ISSUE-053](../../issues/ISSUE-053.md) 的精简设计执行，设计见 [精简方案](../decisions/2026-11-20-technical-plan-simplified.md)。
