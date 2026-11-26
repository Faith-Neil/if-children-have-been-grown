# BE-PROJECT-LIST-PAGING 代码说明


## 修改概览

- `icg/infra/repositories/hot_reads.py`：新增鉴权、会话、项目摘要和单项目作用域读取，避免热路径 `repository.read()` 全库扫描。
- `mysql_repository.py` / `projects.py`：接入作用域查询、`last_accessed_at/status` 持久化和列表分页排序筛选。
- `api/session.py`：会话端点改为同步 def，由 FastAPI 线程池执行，避免阻塞事件循环。
- `workflow_orchestrator.py`：工作台读取限定项目状态，进入工作台更新访问时间；裁掉规则内重复嵌套 issues。
- `technical_tender_index.py`：远端招标检索强制 `document_ids=[当前文档]`，缺失时降级本地索引。
- `kb_admin.py`：真实 `.doc/.docx` 先经 `office_pdf.prepare_for_deepdoc` 转 PDF，再推 RAGFlow。
- `ProjectListPage.tsx` / `App.tsx`：项目列表接入服务端分页、关键字和状态查询。
- `deploy/`：三机生产部署底座、外部 MySQL/RAGFlow 配置、LibreOffice 中文字体、健康检查和上线步骤。

## 设计约束

不引入 Redis；单 worker + 线程池 + MySQL；内网客户端继续固定 `trust_env=False`。内存仓储保留多态 fallback，生产 MySQL 走精确查询。
