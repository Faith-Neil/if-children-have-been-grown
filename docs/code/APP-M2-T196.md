# APP-M2-T196 代码解释：Word模板与正文样式渲染（整本递交版/内部稿导出与下载）

本任务与 **APP-M2-T195**（合规检查红线门禁）在同一架构单元内协同实现与交付。

详细代码解释、架构设计、状态流转与边界测试详见：
👉 **[docs/code/APP-M2-T195.md](APP-M2-T195.md)**

### 核心实现要点
1. **分册范围单选**：在 `frontend/web/src/project/ProjectPages.tsx` ExportPage 中集成 `export-volume-radio`（技术分册、商务分册、两册合订）；
2. **导出类型双轨制**：集成 `export-kind-radio`（内部评审稿 `internal` 与正式递交版 `submission`），内部稿用于线下校审并附带水印提示，正式递交版受 blocker 红线硬拦截；
3. **导出历史表格与元数据展示**：集成 `export-history-table`，完整呈现快照编号（`export-history-id`）、生成时间、操作人、分册范围、类型 Tag、文件大小与 SHA256 版式指纹（`export-fingerprint`）；
4. **受控下载操作**：集成 `export-download-btn`，实现分册独立下载或打包下载功能。
