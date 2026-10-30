为什么有这个文件：记录 APP-M2-T164 变量节点的实际交付和测试证据。

它解决什么问题：说明正文变量怎样显示取值、怎样标失效、提交时后台拒绝什么，以及还没做的部分。

# APP-M2-T164：变量节点

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T164 |
| 代码解释 | [APP-M2-T164](../code/APP-M2-T164.md) |
| 验收 | 2026-10-30：正文里的 `{{fact:…}}` / `{{sla:…}}` 在只读与未持锁视图里显示为带底色的取值，取值来自后台按当前数据源的解析；身份证号、手机号、银行账号类取值显示掩码（与导出同一套掩码）；不存在、未确认、来源失效、单位不符、格式残缺的变量标红并写明原因；悬停或点开变量可“去项目事实表 / 去服务承诺矩阵”。持锁编辑时文本框下方列出本节变量，有失效变量时提示个数。提交正文与版本回退时，后台拒绝新写入的失效变量（409，错误码沿用 `FACT_VARIABLE_*` / `SLA_VARIABLE_*`）；正文原有、之后才失效的变量不挡提交，由检查拦截导出。这类 409 不再被当成版本冲突进入合并弹窗 |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T164](../tasks/APP-M2.md#app-m2-t164)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)；看板工作包 WP-1；依赖 [APP-M2-T161](APP-M2-T161.md) 段落键
- 验证记录：[WP-1 变量节点与问题联动验证](../testing/2026-10-30-wp1-variables-issues.md)

## 实际文件
- 后端：`backend/bid-core/icg/domain/variable_nodes.py`（新）；`icg/api/chapter_versions.py` 新增 `POST /api/v1/projects/{p}/chapters/{c}/variables`（`resolveChapterVariables`，只读）；`icg/domain/domain.py` 提交、`icg/domain/version_rollback.py` 回退各加一处 `refuse_new_invalid`
- 前端：`frontend/web/src/editor/variable-nodes.ts`（新）、`VariableChip.tsx`（新）、`CiteCapsule.tsx`（只读视图渲染变量）、`EditorPage.tsx`（解析请求、变量栏、失效提示、错误处理）、`editor-conflict.ts`（来源与变量类 409 不进合并流程）
- `spec/openapi/demo-v1.json`

## 测试证据
- `tests/backend/test_variable_nodes.py`：取值、掩码、未确认、不存在、格式残缺；只读成员可读、他公司不可读；提交拒绝四类新失效变量且正文不变；原有失效变量不挡提交，再新写一处仍拒；回退不能带回已删除事实的变量
- `tests/backend/test_sla.py`、`test_generation_context.py` 三个用例改为“提交先被拒，检查仍拦截原有失效变量”两段断言
- `frontend/web/tests/unit/variable-nodes.test.mjs`：按后台位置切分、文字改过不显示、胶囊文字与入口
- `frontend/web/e2e/variable-nodes.spec.ts`：真实解析 → 确认事实 → 只读视图显示取值不显示 `{{fact:` → 持锁写入不存在的变量 → 提示失效 → 提交被拒且正文不变 → 出现“去项目事实表”
- 全量：后端 1084 项（改前 9 项失败已逐项处理：5 项为本卡预期行为变化，4 项为 OpenAPI 未重新导出）、前端单测 556 项、类型检查、构建

## 未实现项与限制
- 编辑中的文本框仍是纯文本，变量在框内显示为 `{{fact:…}}` 原文；取值与状态在框下方变量栏显示。框内节点化要等编辑器换成结构化组件。
- “敏感变量”按取值格式掩码（身份证、手机、长账号），事实本身还没有敏感标记字段；字典若补字段再接。
- “去数据源修改”跳到项目事实表或服务承诺矩阵页，不定位到具体一行。
- 卡里“三种宽度截图、正文区 <700 工具栏收起、与 04a 并排截图”属于 T160 断点，本卡未做。
