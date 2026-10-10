为什么有这个文件：解释本目录验收图片的来源和用途。

它解决什么问题：区分实际产品截图、旧后台截图和未修改的ICG设计原图，避免将截图误当完整交付。

# 页面验收图片

`backend-demo.jpg`是BE-M0-T01的小后台验证页历史证据。

`icg-reference-diff.jpg`、`icg-reference-checks.jpg`、`icg-reference-export.jpg`来自2026-10-10真实运行的ICG产品页，全部使用合成项目和证明材料。分别证明候选差异确认、当前流程检查和两个内部稿文件的实际下载入口；图片不能证明尚未实现的完整规则、正式Word版式或高级页面。图片实际编码为JPEG，扩展名按实际格式登记。

原始ICG设计图片保留在`ICG/frontend doc/前端设计示例/`，本目录不覆盖原件。截图是二进制，不能在图片文件开头加入文字，来源与作用统一在这里说明。

新增解析、矩阵、编辑台、1280窗口、草稿恢复和失败上传恢复截图，具体文件与阶段上下文见[测试记录](../2026-10-10-icg-reference.md)。1280使用实际窗口截图，完整页截图可能包含滚动时固定顶栏的捕获位置，不据此冒称像素级一致。

服务承诺新增 `icg-sla-not-satisfied.jpg`、`icg-sla-facts.jpg`、`icg-sla-editor-variable.jpg`、`icg-sla-matrix.jpg`、`icg-sla-template-stale.jpg`、`icg-sla-overview-review.jpg`、`icg-sla-templates.jpg`。全部来自实际同源产品、合成数据；前五张为第一次页面项目，后两张为重载最终版本后的项目/模板，详见[数值验收](../2026-10-10-sla.md)。它们证明记录的操作与当前字段，不能代替完整P-07、R09/R10/R30或正式Word视觉验收。
