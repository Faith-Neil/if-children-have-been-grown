为什么有这个文件：记录工单 0（RAGFlow 招标解析打通）实际改了什么与冒烟证据。

它解决什么问题：避免未修解析就宣称最短路径 / MVP 可用。

# TV-M0-T00 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T00](../tasks/TV-M0.md#tv-m0-t00) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-05 |
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done；本 Agent 不标 done |
| 代码解释 | [TV-M0-T00](../code/TV-M0-T00.md) |

## 实际变更

- `tender_remote.ensure_dataset`：招标临时库必须用公司知识库内网嵌入；与现网不一致则删除重建（禁止就地改嵌入导致 Infinity 向量列对不上）。
- 失败文案：外网嵌入 / 出网请求可读提示；失败清 `remote_parse` 以便重试。
- 单测：`tests/backend/test_tender_remote_parse.py` 13 passed（含外网提示与重建）。

## 验收证据

- 根因取证：原 `alpha::icg-tender` 嵌入为 `…@Jiekou.AI`，progress_msg 含 `api.jiekou.ai`。
- 本机重建后冒烟 PDF：Tokenizer Done → COMPLETED，读回正文块。
- 项目 `project-ebf56bea…` 真实文件「德阳市人民医院…Oracle….doc」：`POST …/parse/jobs` 后 `status=parsed`，`page_count=16`，条款 61 条；警告含 DeepDOC 说明。
- 未宣称：管道去闸门、动态目录、双库写作、编辑台 UI、写作助手均未在本卡完成。

## 项目进度

工单 0 阻塞已解除（解析主路径可跑通）。下一张：工单 1 管道去闸门。分支仍不合 main。

## 基线同步

| 基线 | impact | 同步 |
|---|---|---|
| PRD | 有影响（最短路径指针） | 文首/决定链到新决定；两册正文不改 |
| ROADMAP | 有影响 | 注明 TV 工单 0 优先 |
| ARCHITECTURE | 有影响 | 招标临时库嵌入对齐说明见决定 |
| TASK_BOARD / PROJECT_STATUS / DOCUMENT_INDEX / Issue | 有影响 | 本轮已更新 |
| 参考原文 | 无影响 | 不改 |
