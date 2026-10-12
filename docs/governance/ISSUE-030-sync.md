为什么有这个文件：记录 N7 重试例外动了哪些说明，以及哪些基线故意不动。

它解决什么问题：避免把一条客户端判断写成产品范围或任务计数已经改变。

# ISSUE-030 同步

日期 2026-10-12。revision retry-n7-1。状态 in-review。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不记录这一条重试例外。页面范围未变 |
| ROADMAP | 未改 | 阶段、门禁和里程碑未变 |
| ARCHITECTURE | 未改 | 请求层仍是原来的模块。没有新接口 |
| PROJECT_BRIEF | 未改 | 里程碑快照未变 |
| TASK_BOARD | 未改 | APP-M2-T002 保持 done。不新增任务卡，不改计数 |
| PROJECT_STATUS | 已改 | 重试句补上 503 `SECRET_KEY_UNAVAILABLE` |
| DOCUMENT_INDEX | 已改 | 登记本表、Issue、交付、代码说明和验证 |
| docs/tasks/APP-M2.md | 已改一句 | T002 卡片里的重试句与代码一致。卡片状态仍为 done |
| docs/delivery/APP-M2-T002.md、docs/code/APP-M2-T002.md | 已改一句 | 原先写“503 即使带统一错误体仍重试”。该句已过时 |
| docs/reference | 未改 | 本卡不改参考原文 |
| spec/openapi | 未改 | 冻结 JSON 已含 N7。README 的旧句子不代表接口字段 |
| backend | 未改 | 不改错误码实现 |
