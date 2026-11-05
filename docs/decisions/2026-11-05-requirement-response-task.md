为什么有这个文件：把「模型调用与响应矩阵架构」拍板成仓库内生效决定，承接 ISSUE-047 最短路径后的数据与生成改造。

它解决什么问题：禁止再把一条招标要求硬绑成一章目录标题；明确 Requirement / ResponseTask 两层与分析三步。

# Requirement + ResponseTask 两层矩阵（2026-11-05）

关联：[ISSUE-051](../../issues/ISSUE-051.md)、用户方案（桌面 `模型调用与响应矩阵架构.md`）、[最短主路径](2026-11-05-technical-volume-shortest-path.md)。

状态：已拍板开工；在 `feat/iss-047-technical-volume-mvp` 落地；**不合 main**。

## 业务层模型调用

3 次必要 + 按需生成 + 按需审核。Embedding/Reranker 不计入。

1. 招标要求结构化提取 → Requirement 库（不直接出矩阵）。
2. 响应矩阵 + 技术目录 → ResponseTask + 主题目录映射。
3. 生成计划校验 → 确定性规则优先；不通过回退第 2 步。

生成：每章一次主模型（任务 + 要求 + 废标约束 + RAG + 已生成关联）。RAG 仅：章正文、涉企业事实的对话改文、缺口补充。

## 数据

- Requirement：招标提出了什么（含 `risk_level` + `is_rejection_criterion`）。
- ResponseTask：在哪、怎么响应（`requirement_ids[]`，多对多）。
- 目录标题必须是**方案章节短标题**，禁止条款原文整段作标题。

## 前端

- 技术分册分析页去掉「项目事实 / 取值冲突」主路径块。
- 覆盖视图列：招标要求 | 风险 | 原文出处 | 目标章节 | 响应状态；点行跳编辑台。
- 壳层紧凑：主工作区占满。
