为什么有这个文件：解释本目录验收图片的来源和用途。

它解决什么问题：区分实际产品截图、旧后台截图和未修改的ICG设计原图，避免将截图误当完整交付。

# 页面验收图片

`backend-demo.jpg`是BE-M0-T01的小后台验证页历史证据。

`icg-reference-diff.jpg`、`icg-reference-checks.jpg`、`icg-reference-export.jpg`来自2026-10-10真实运行的ICG产品页，全部使用合成项目和证明材料。分别证明候选差异确认、当前流程检查和两个内部稿文件的实际下载入口；图片不能证明尚未实现的完整规则、正式Word版式或高级页面。图片实际编码为JPEG，扩展名按实际格式登记。

原始ICG设计图片保留在`ICG/frontend doc/前端设计示例/`，本目录不覆盖原件。截图是二进制，不能在图片文件开头加入文字，来源与作用统一在这里说明。

新增解析、矩阵、编辑台、1280窗口、草稿恢复和失败上传恢复截图，具体文件与阶段上下文见[测试记录](../2026-10-10-icg-reference.md)。1280使用实际窗口截图，完整页截图可能包含滚动时固定顶栏的捕获位置，不据此冒称像素级一致。

服务承诺新增 `icg-sla-not-satisfied.jpg`、`icg-sla-facts.jpg`、`icg-sla-editor-variable.jpg`、`icg-sla-matrix.jpg`、`icg-sla-template-stale.jpg`、`icg-sla-overview-review.jpg`、`icg-sla-templates.jpg`。全部来自实际同源产品、合成数据；前五张为第一次页面项目，后两张为重载最终版本后的项目/模板，详见[数值验收](../2026-10-10-sla.md)。它们证明记录的操作与当前字段，不能代替完整P-07、R09/R10/R30或正式Word视觉验收。

写作输入新增`icg-writing-plan.jpg`、`icg-writing-candidate-input.jpg`、`icg-writing-candidate-facts.jpg`、`icg-writing-stale.jpg`、`icg-writing-fact-variable.jpg`、`icg-writing-source-advice.jpg`、`icg-writing-export.jpg`，均为2026-10-10实际同源页面与合成项目。用途、不同操作阶段及未验收范围见[写作验收](../2026-10-10-writing-input.md)；图片为JPEG，不能代替真实模型、逐段来源、全文规则或Word视觉验收。

写作收尾3张JPEG：icg-writing-atomic-guard.jpg显示来源变化后提交被拒绝且文字保留；icg-writing-source-review.jpg显示人工来源复核入口（截图是确认前状态）；icg-writing-final-export.jpg显示最终v8合成正文的有效两册与旧文件过期。来自最终服务project-f7cd99f538074c04ab78d5668b2464a5，详细顺序见[写作验收](../2026-10-10-writing-input.md)。图片不证明Word页面版式已验收。
