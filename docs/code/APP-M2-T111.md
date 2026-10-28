为什么有这个文件：解释星号/废标兜底扫描与疑似遗漏处理的代码路径。

它解决什么问题：说明扫描何时运行、覆盖如何判定、处理结果如何保留以及确认闸门在哪里。

# APP-M2-T111：代码解释

- 对应任务 APP-M2-T111；Issue [ISSUE-040](../../issues/ISSUE-040.md)；交付 [APP-M2-T111 交付](../delivery/APP-M2-T111.md)
- 提交 `06f107d`、`2c8d51c`

## 入口和调用顺序

1. `TenderOrchestratorMixin.parse` 每个文件解析成功后调用 `post_process.run_scan(workflow, file_id, pages, now)`：按行扫描平台词表与“条款开头的 *”，新命中登记为 `open`；同一 (文件, 页, 原文) 已有记录不重复登记，已处理结果保持不变。
2. `GET /parse/omissions`（`listScanHits`）→ `OmissionMixin.list_scan_hits`：每条 `open` 命中实时判定 `covered` / `suspected`；返回统计、词表版本、`can_handle`（项目负责人）。
3. `POST /parse/omissions/{id}/add`（`addScanHitAsRequirement`）：项目负责人；类别 `star` / `disqualification`；同来源已有条目则升级类别与重要性、退回待确认，否则新建条目；命中记 `added`。
4. `POST /parse/omissions/{id}/exclude`（`excludeScanHit`）：项目负责人；理由必填；命中记 `excluded`。
5. `confirm_parse` 在既有检查之后调用 `require_no_omissions`，有疑似遗漏则 409 `OMISSIONS_PENDING`。
6. workspace 返回 `omissions_pending`；解析页按钮、左栏后处理入口与“确认解析结果”按钮使用它；`OmissionsDrawer` 逐条列出，只有单条“新增为条目 / 排除”。

## 数据与状态

`workflow["post_process"] = {"scan_version": "platform-2026.10-1", "hits": {id: {file_id, page, quote, terms[], status: open|added|excluded, reason, requirement_id, handled_by, handled_at}}}`；MySQL 模式写入 `demo_project_workflow_state`。

## 关键判断与异常

- 覆盖判定与合规检查共用 `CheckOrchestratorMixin._is_critical_requirement`（★、标星、废标、否决、类别），被排除的条目不算覆盖；因此负责人忽略一条星号条目后，该命中会重新成为疑似遗漏。
- 不调用模型；没有批量接口。
- 命中超过 30 条时返回 `too_many`，页面提示复核词表。

## 验证与限制

见 [Wave 11 验证](../testing/2026-10-28-wave-11-verification.md)。词表固定为平台初始版本；公司词表维护（APP-M2-T148）、“引用未解析”页签、补遗重跑差异未在本卡实现。
