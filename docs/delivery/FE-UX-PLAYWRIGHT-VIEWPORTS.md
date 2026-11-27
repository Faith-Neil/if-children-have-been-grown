# FE-UX-PLAYWRIGHT-VIEWPORTS 交付记录

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-UX-PLAYWRIGHT-VIEWPORTS |
| 代码解释 | [代码说明](../code/FE-UX-PLAYWRIGHT-VIEWPORTS.md) |
| 验收 | tsc 与生产构建已通过；四视口 Playwright 巡检复跑 1 passed（31.0s）；已改用 SPA 内导航并移除 409 过滤，编辑台不再产生锁接管 409；tsc 与生产构建通过；前端全量单测存在既有 app-orchestration/company-settings/dict-config 陈旧或测试替身失败，未冒充通过 |
| 项目进度 | done。用户验收 PR #54 后按指令收口，ISSUE-057 closed；未发布 |
<!-- task-delivery:end -->

## 实际修改

围绕 ISSUE-057 完成编辑台加载/撰写状态解耦、项目列表服务端排序筛选、覆盖视图白话失败原因、统一视觉 Token、响应式宽度与四视口巡检脚本。

## 局限

后台页面仍有少量表格列宽属于业务可读性保留；截图自审证据以 Playwright 输出目录为准。


## 2026-11-27 复核补充

编辑台 409 已定位为巡检脚本使用整页 `page.goto` 导致前一会话编辑锁未随 SPA 清理释放；请求为 `POST /api/chapters/alpha-tech/lock`，响应 `TAKEOVER_REASON_REQUIRED`。改用 SPA `history.pushState + popstate` 后，离开编辑台会正常释放锁，巡检在不过滤 409 的情况下通过。
