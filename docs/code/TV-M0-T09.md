为什么有这个文件：说明工单 2 动态目录与去矩阵闸门的代码落点。

它解决什么问题：后续改覆盖视图 / 一键全文时，知道目录确认已是唯一用户闸门。

# TV-M0-T09 代码说明

## 目录

- `technical_outline.py`：`arrange` 产出 L1「技术规范响应」「评分主观分响应」及编号树叶子；`assign_numbers` 支持跳级；`confirm_directory` 写入 `technical_outline_snapshot`。
- `workflow_schemas.py` + OpenAPI：`OutlineHeadingInput.level` ∈ [1,4]。

## 生成闸门

- `technical_volume.assert_ready`：仅 `plan_confirmed` + outline；检索 `running` 时暂缓；**不再**要求矩阵逐条 confirmed。
- `writable`：有响应原文即可，不看 `status`。
- `produce_section` / `stand_in`：按节自由组织，拒绝空壳（&lt;40 字），不强制六段标题。
- `_leaves`：按目录顺序取挂 `requirement_id` 的节点，删除 `WRITE_ORDER`。

## 前端

- `OutlineTreeView`：级别一至四级；按钮「开始生成」；再生针对有条款叶子。
- `EditorPage`：提交 1～4 级；去掉 `historyBlocked`。
