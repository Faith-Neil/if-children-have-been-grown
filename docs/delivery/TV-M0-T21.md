为什么有这个文件：记录技术服务方案精简主路径 E 组（写作助手补两项）交付。

# TV-M0-T21 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 代码 | [TV-M0-T21](../code/TV-M0-T21.md) |

## 实际变更

- 按节修改候选写入前查数字，结果随候选返回 `numbers`：
  - 本节需求的偏离类型与数字口径，用写入后的同一条规则（`technical_volume.inconsistent()`）检查；
  - 候选里带单位的承诺数字（分钟、小时、工作日、天、月、年、%、人、名、次等），须在本节原文、本章其他正文、需求与评分、挂载要点、已确认事实或检索片段里出现过，否则列为找不到依据。
- 编辑台候选预览显示数字提示；需核对时要勾选「已核对，数字有依据」才能预览写入。
- 自由提问在技术服务方案里按小节分会话：会话记小节键（任务编号）与标题；续问只能在同一小节，跨小节续问 403；会话下拉只列当前小节的会话，换小节回到新会话。回答仍只可复制。

## 验收证据

- `tests/backend/test_technical_assistant.py`：8 passed（含数字预检、候选带数字结果、按小节分会话与跨小节续问 403）。
- `test_assistant_questions.py`、`test_selection_rewrite.py` 通过；`test_assistant_kb_sessions.py` 3 项失败，改动前的代码上同样失败，非本次引入。
- `frontend/web/tests/unit/technical-assistant.test.mjs`、`selection-rewrite-core.test.mjs`：14 passed；前端 lint 通过。
- `export_openapi.py --check` 一致；治理检查通过。
- 只用模型替身验证；未连内网 Qwen / RAGFlow，界面未做浏览器验收。

## 局限

- 数字依据按「数字 + 单位」字面匹配，中文数字（如「两小时」）不换算。
- 选区修改（非按节）的会话不分小节。

## 同步

PRD、ROADMAP、ARCHITECTURE：无改动，按 [ISSUE-053](../../issues/ISSUE-053.md) 的精简设计执行。
