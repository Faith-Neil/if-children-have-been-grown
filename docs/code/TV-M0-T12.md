为什么有这个文件：解释质量八条抽检如何挂到生成与工作区。

它解决什么问题：后人改生成路径时不会漏掉「需核对」标记与导出口径。

# TV-M0-T12 代码说明

## 入口

- `backend/bid-core/icg/domain/technical_quality.py`：`evaluate_quality` / `apply_quality_markers`
- `technical_volume.write_volume`：组装正文后抽检并写回 workflow
- `technical_outline.workspace_fields`：暴露 `technical_quality`，合并需核对标题
- 前端：`EditorPage`、`ProjectPages` 导出区、`OutlineTreeView` 节 Tag

## 口径

- 规则失败 → 节或全文「需核对」+ 可见警告。
- **不**因此恢复矩阵确认闸门。
- 允许导出内部稿。
