为什么有这个文件：记录QA独立复跑与会话真实HTTP复核入库的实际交付。

它解决什么问题：让接手者知道哪些自报结果已被独立复现、如何重跑会话实时检查及其局限。

# REV-M0-T02：QA独立复跑与会话真实HTTP复核入库交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-M0-T02 |
| 代码解释 | [代码解释](../code/REV-M0-T02.md)；仅新增验证脚本，未改应用代码 |
| 验收 | 后台262、前端72、构建、治理12/原型6/同步10/旧页7、5个真实HTTP冒烟、会话实时15/15及治理检查通过；见[复跑记录](../testing/2026-10-12-qa-rerun.md) |
| 项目进度 | 338项15done；REV-M0 2/2；APP-M2-T001仍in-progress |
<!-- task-delivery:end -->

## 关联与状态

- 日期2026-10-12；REV-M0；[ISSUE-013](../../issues/ISSUE-013.md)；[任务卡](../tasks/REV-M0.md#rev-m0-t02)。
- 分支`codex/repository-foundation`，PR #3。
- 本地验收通过；未合入、未发布。

## 完成内容与变更文件

- `tests/backend/session_live_http.py`：自启uvicorn于空闲本机端口的会话实时检查15项。文件名不匹配`test_*.py`，默认pytest不收集。
- `docs/testing/2026-10-12-qa-rerun.md`：复跑命令、环境、计数与局限。
- 同步：`issues/ISSUE-013.md`、`issues/index.md`、`docs/tasks/REV-M0.md`、`docs/TASK_BOARD.md`、`docs/PROJECT_STATUS.md`、`docs/DOCUMENT_INDEX.md`。

## 验证

`python tests/backend/session_live_http.py` → TOTAL 15 PASS 15；`python -m pytest tests/backend -q` → 262 passed；`node scripts/check-project-governance.cjs`通过。CI显式运行会话脚本即可（需已安装requirements）。

## 同步与剩余

PRD/ROADMAP/ARCHITECTURE无影响（未改需求、阶段或接口）。原16项中1项无法还原，记为间接复核；CI须用Node 24；GUI未复验。APP-M1-T14/T15按实际代码与测试判定为done（本地验收），APP-M2.md“拆分时状态”为历史快照，非不一致，未修改。
