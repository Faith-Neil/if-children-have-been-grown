# 2026-09-22 RAGFlow 自带向量库 + MySQL 关系库

## 任务名称

知识库采用 RAGFlow 自带向量引擎，业务关系库改用 MySQL。

## 关联信息

- Issue：`issues/ISSUE-001.md`
- 开发类型：技术冻结变更（文档同步）

## 完成内容

1. PRD FR-2 改为：知识库用 RAGFlow；向量由 RAGFlow 部署自带引擎承载；业务关系数据用 MySQL。
2. ARCHITECTURE 同步架构图、技术栈、隔离门、部署与 ADR。
3. ROADMAP 同步 M1 部署与 M6 Docker 打包清单。
4. README 增加 v0.4 版本说明，并登记文档索引。

## 修改文件

- 新增：`issues/template.md`、`issues/index.md`、`issues/ISSUE-001.md`
- 新增：`docs/DOCUMENT_INDEX.md`
- 新增：`docs/delivery/2026-09-22-ragflow-mysql-stack.md`
- 修改：`docs/PRD.md`、`docs/ARCHITECTURE.md`、`docs/ROADMAP.md`、`README.md`

## 技术设计

- 知识库：RAGFlow（解析 / 切块 / 混合检索 / 重排 / 知识库管理）。
- 向量库：RAGFlow 部署自带文档/向量引擎（默认 Elasticsearch，可选 Infinity），不再外接 openGauss DataVec。
- 关系库：MySQL，存储需求、项目、版本、审计日志。

## 测试结果

本次为文档口径同步，无运行时代码。已检索确认现行文档不再把 openGauss 作为向量库或业务关系库（README v0.2 历史条目保留）。

## 已知问题

- `PROJECT_PLAN` / `TECH_DESIGN` / `DEVELOPMENT_PLAN` / `TASK_BOARD` 尚不存在，已在 Issue 注明「无」。

## 下一阶段

按 ROADMAP M1 部署 RAGFlow（自带向量引擎）与 MySQL，跑通知识库检索生成最小闭环。
