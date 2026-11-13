为什么有这个文件：说明 TV-M0-T05 的目录写在哪里。

它解决什么问题：下次改服务方案目录时，能看出它和技术分册抽取、两册旧大纲不是同一条规则。

# TV-M0-T05 代码说明

目录在 `backend/bid-core/icg/domain/technical_outline.py`。`apply_technical_outline` 在技术分册抽取成功且抽出了条款之后调用。它把项目里那一章技术章节改名为招标标题，并把二级、三级标题写进正文。

二级只在有条款时出现。服务方式、质量管理、实施计划、应急、培训、保密、质保按条款里的词归类，其余进服务内容。健康检查、故障、巡检、升级、性能排在服务内容前面。

确认仍走原来的 `POST /api/v1/projects/{id}/plan`。只有已经排出 `technical_outline` 时才走这条新规则。缺三级标题返回 `REQUIREMENT_NOT_READY`。两册旧项目的大纲确认不变。
