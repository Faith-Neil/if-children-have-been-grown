为什么有这个文件：记录技术服务方案精简主路径 C 组（写作助手）交付。

# TV-M0-T19 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 代码 | [TV-M0-T19](../code/TV-M0-T19.md) |

## 实际变更

- 问答写作不再回固定文案：走现有流式问答，选了小节时回答带本节挂载要点、评分标准与全部废标清单，检索词按本节；回答只可复制，不写入正文。
- 新增按节修改：只改所选小节，上下文为本节要点、评分标准、废标清单与本标、历史标书、资料库检索结果；候选先做废标约束预检，显示违反项与来源，预览后在编辑锁下写入，基线版本或项目输入变化时拒绝。
- 五条快捷指令：补齐未覆盖要点、按五步结构重写、扩写措施、统一承诺数字、重新检索后重写。
- 覆盖视图点「目标章节」跳到编辑台，预填小节和修改要求。
- 项目只读成员按节修改 403；未接真实模型时返回 502，不给模拟修改。

## 验收证据

- `tests/backend/test_technical_assistant.py`：4 passed；`tests/backend/test_assistant_questions.py`、`test_selection_rewrite.py` 通过。
- `test_assistant_kb_sessions.py`、`test_assistant_streaming.py` 有 4 项失败，改动前的代码上同样失败，非本次引入。
- `frontend/web/tests/unit/technical-assistant.test.mjs`：3 passed；前端全量失败集合与改动前相同（9 项既有失败）；`pnpm lint` 通过。
- `export_openapi.py --check` 一致；治理检查通过。
- 只用模型替身验证；未连内网 Qwen / RAGFlow，界面未做浏览器验收。

## 局限

- 数字一致性检查沿用写入后的现有检查，候选预检只覆盖废标与硬约束。
- 问答与修改记录沿用现有按人按章会话，未单独按小节分会话。

## 同步

PRD、ROADMAP、ARCHITECTURE：无改动，按 [ISSUE-053](../../issues/ISSUE-053.md) 的精简设计执行，设计见 [精简方案](../decisions/2026-11-20-technical-plan-simplified.md)。
