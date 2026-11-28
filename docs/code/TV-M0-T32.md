为什么有这个文件：解释 TV-M0-T32 两阶段目录规划、失败语义与前端重跑入口的代码结构。

# TV-M0-T32 代码说明

## 后端两阶段规划

入口是 `backend/bid-core/icg/domain/technical_digest_outline.py::plan_technical_outline`：

1. `build_digest` 生成清洗后的 T/S/R 清单。
2. `_stage_skeleton` 用 `SKELETON_SYSTEM` 让模型只输出章节骨架；`_normalize_skeleton` 校验层级、编号、叶子和禁用兜底章名。
3. `_stage_mount` 用 `MOUNT_SYSTEM` 让模型把 T/S 编号挂到叶子；`_normalize_mounts` 只接受有效编号和叶子节点，重复挂载会进入重试反馈。
4. `build_from_mounts` 把挂载结果转成 headings/tasks；未挂编号只写入 `validation.unmounted_digest_refs`，不进入兜底章。
5. `repair_json_payload` 做有限的 JSON 修复；每阶段最多 3 次尝试。失败记录包含 stage、attempts、timeout、type、message 与 cause chain。

`technical_model_extract.error_is_timeout` 沿异常 cause 链识别 `httpx.TimeoutException`、`TimeoutError` 与被 `ModelCallError` 包装的 `RetryableModelError("timeout")`。

## 失败语义

- 没有可用本地模型：只允许解析期规则草稿存在。
- 模型可用但规划失败：返回空 plan，写 `tree_model_failed=True`、可读 `outline_reason`、内部 `outline_model_error`；不写新的规则树冒充结果。
- 已有模型目录重跑失败时不清空旧目录，`outline_source` 表示当前可见目录的真实来源。

## 前端重跑入口

- `frontend/web/src/project/outline-rebuild-core.ts` 判定失败态、权限、端点和响应语义。
- `frontend/web/src/project/OutlineRebuildNotice.tsx` 在编辑台显示错误级驻留告警；管理员可点击重跑，非管理员只看到需要管理员处理。
- `EditorPage.tsx` 在成功后刷新工作台并复用目录章节刷新；有未保存编辑时不覆盖本地 dirty 内容。
- `parse-honesty.ts` 支持 `includeOutline=false`，避免同一目录失败在编辑台重复告警。

## 边界

`outline_model_error` 是内部诊断字段，不进入公开 Workspace API，避免 OpenAPI 契约膨胀；公开契约仍是 `outline_source/tree_model_failed/outline_reason`。

## PR #57 Review 修复轮补充

- 挂载归一化在任何去重、覆盖率与候选择优前把评分组号统一展开为点号，避免组号/点号重复响应或误算遗漏。
- 模型目录落盘前裁剪无挂载空叶子及因此变空的父节点，并重新顺序编号；可生成任务均有实质挂载，不写「待补」空章。
- 多次重试结果合并后重新计算叶子集中度；合并导致过度倾倒时宁可换平衡候选或显式失败，不产出失真目录。

## PR #57 最终 Review 清零补充

- 缺项合并改为保留全部候选叶子位置的小型回溯选择，容量不足时宁可留未挂载池也不超限倾倒；合格基底候选作为保守结果保留。
- 标题编号清洗增加乘号时间规格保护，`7×24` / `7x24` / `5×8` 前缀不再被剥成残标题。
