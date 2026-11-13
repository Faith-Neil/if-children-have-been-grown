为什么有这个文件：说明 TV-M0-T07 的正文和偏离表写在哪里。

它解决什么问题：下次接本地模型时，能看出六段替身、样表填写和内部稿导出是分开的。

# TV-M0-T07 代码说明

规则在 `backend/bid-core/icg/domain/technical_volume.py`。

`write_volume` 在目录已确认、检索已结束、历史无偏离行已确认之后，按服务内容、服务方式、质量、应急、进度、培训、保密、质保的顺序写三级标题。写回章节时仍按目录编号排列。`section` 只重写一节。`produce_section` 在绑定的写作函数、本地模型、六段替身之间选择。公网模型不调用。返回的正文缺任何一段时，这一节不替换。

`find_samples` 只读招标文件和技术规范书里的技术偏离表。`export_parts` 在导出时把已确认矩阵填进样表，不写回服务方案正文。附件样表放到另一次下载。`export_service.py` 对技术分册的内部稿走这条路径，不再要求检查批次通过。

工作区用 `technical_deviation_note` 和 `technical_needs_review` 把「没有样表」和「需要核对」交给页面。页面按钮在 `TenderTab.tsx` 和导出页。
