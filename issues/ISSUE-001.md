# ISSUE-001：知识库采用 RAGFlow 自带向量库，业务关系库改用 MySQL

## 基本信息

| 项 | 内容 |
| --- | --- |
| 编号 | ISSUE-001 |
| 类型 | product |
| 优先级 | P1 |
| 状态 | closed |
| 提出日期 | 2026-09-22 |
| 关联 GitHub Issue | 无 |
| 关联 SPEC / 任务 | 无 |

## 现象

当前三件套将知识库向量与元数据放在国产化 **openGauss DataVec**，业务关系库也复用 openGauss。产品已决定：

1. **知识库采用 RAGFlow**（解析、切块、混合检索、知识库管理）。
2. **RAGFlow 部署时自带文档/向量引擎**，不再外接独立向量库。
3. **业务关系数据改用 MySQL**（需求、项目、版本、审计日志）。

## 证据

- `docs/PRD.md` FR-2 写明「向量与元数据存储用国产化 openGauss DataVec」。
- `docs/ARCHITECTURE.md` 技术栈、部署图、ADR 将向量库与关系库均指向 openGauss。
- `docs/ROADMAP.md` M1/M6 仍要求接入并打包 `opengauss`。

## 影响范围

- 技术冻结：向量库、关系库。
- 文档：PRD、ARCHITECTURE、ROADMAP、README、DOCUMENT_INDEX。
- 不改业务代码（仓库当前无实现代码）。

## 初步判断

独立部署 openGauss DataVec 与 RAGFlow 自带向量引擎职责重叠。关系库改用 MySQL 可降低运维复杂度，并与常见部署习惯对齐。

## 分流结果

文档同步（技术冻结变更）。不新建独立向量库组件；业务库选型改为 MySQL。

## 下一步

1. 更新 PRD FR-2 技术实现口径。
2. 同步 ARCHITECTURE 架构图、技术栈、隔离门、部署、ADR。
3. 同步 ROADMAP 环境搭建与 Docker 打包清单。
4. 回写 README 版本说明与 DOCUMENT_INDEX。

## 验收方式

- 文档中现行口径不再把 openGauss / DataVec 作为向量库或业务关系库。
- 现行口径统一为：RAGFlow 作为知识库并使用其部署自带向量/文档引擎；业务关系库为 MySQL。
- README 历史版本条目（如 v0.2）可保留当时选型，不视为现行口径。

## 处理记录

- 2026-09-22：按本 Issue 完成 v0.4 文档同步。
- 2026-09-22：验收通过，关闭。现行口径为 RAGFlow 自带向量引擎 + MySQL 业务关系库。

## 基线文档同步检查表

1. PRD：已改 FR-2 技术实现，文首升至 v0.4。
2. ARCHITECTURE：已改架构图、技术栈、隔离门、部署、ADR，升至 v0.4。
3. PROJECT_PLAN：无。仓库尚无该文件，本次不新建。
4. TECH_DESIGN：无。仓库尚无该文件，本次不新建。
5. DEVELOPMENT_PLAN：无。仓库尚无该文件，本次不新建。
6. TASK_BOARD：无。仓库尚无该文件，本次不新建。
7. 互链版本：PRD / ARCHITECTURE / ROADMAP 同日升至 v0.4，口径一致。
8. DOCUMENT_INDEX：已创建并登记本次变更。
9. Issue / 交付说明：本文件 + `docs/delivery/2026-09-22-ragflow-mysql-stack.md`。
