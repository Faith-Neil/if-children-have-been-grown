# 产品范围：仅生成技术标

状态：已确认（2026-11-08）。延续 [技术分册 MVP](2026-11-03-technical-volume-mvp.md) 与 [ISSUE-047](../../issues/ISSUE-047.md)。

## 结论

本应用目标是**技术标（技术方案）生成与导出**，不再做商务分册、两册合订、合标负责人与商务路径 UI。

## 实现口径

1. 新建项目 API 仍发送 `volume_mode: technical_only`（后端兼容）。
2. 前端 `technicalOnly` / `projectVolumes` 固定为仅技术方案，不读取 `both` 恢复商务入口。
3. 编辑台统一使用 `PaperEditor`（纸面编辑器），移除商务分册时代的 `TextArea` 正文路径。
4. PRD v1.8 原文中的「技术/商务两册」条目视为历史描述；活动基线以本决定与 [技术分册 MVP](2026-11-03-technical-volume-mvp.md) 为准。原文保留在 `docs/reference/product/` 供对照，不删除档案。

## 不在此轮强制删除

- 后端 `Volume = technical | business` 枚举与旧数据兼容字段（避免破坏迁移中的合成数据）。
- 招标解析里的「商务要求」**条款类别**（招标原文分类，不是商务分册产品能力）。
