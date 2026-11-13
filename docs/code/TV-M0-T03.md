为什么有这个文件：说明 TV-M0-T03 的代码改在哪里。

它解决什么问题：下次改招标文件上传时，能看出技术分册的限制没有套到旧的两册项目上。

# TV-M0-T03 代码说明

规则在 `backend/bid-core/icg/domain/technical_sources.py`。只有 `volume_mode` 为 `technical_only` 的项目才进入这些限制。

上传时 `TenderOrchestratorMixin.upload` 先检查扩展名和文件类型。删除、改类型、设为被替代时调用 `invalidate_after_file_change`：目录确认和矩阵行的确认时间清空，章节正文不动，有字的章节 id 记入 `needs_regeneration`。

抽取入口仍是原来的 `parse`。技术分册在抽取前要求至少一份招标文件，并拿当前文件集合的指纹和上次成功抽取的指纹比较。两次相同就返回 `SAME_SOURCE_FILES`。工作区把这两个指纹和章节的 `needs_regeneration` 交给前端。

页面在 `frontend/web/src/project/TenderTab.tsx`。技术分册只显示三种类型，上传框只接受 pdf、doc、docx，按钮写成「抽取技术条款」。两册项目仍用原来的六种类型和补遗差异。
