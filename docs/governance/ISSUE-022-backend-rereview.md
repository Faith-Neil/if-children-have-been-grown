为什么有这个文件：留下大纲契约的后台复审原文，以及项目经理随后拍板的两条决定。

它解决什么问题：让 ISSUE-022 能指向同一次复审，而不是把决定散落在对话里。

# ISSUE-022 后台复审

日期：2026-10-12。关联 [ISSUE-022](../../issues/ISSUE-022.md)。

## 复审原文

这次排队的说明要求把附件中的后台复审逐字写入本文件。跟进队列只有说明文字，不含附件正文；工作区上传目录里也没有这份复审。因此这里不补写、不转述一份并不存在的复审稿。附件到达后，应原样替换本节。

## 项目经理决定

以下两条附在复审记录末尾。

- B2: keep 423 LOCK_HELD for locked chapter and LOCK_LOST for lost lock, same as legacy routes.
- B3: status-change, progress and terminal SSE event types are added to the contract now, implementation in BE-M0-T06.

B2 与现有草案一致：章节被锁为 423 `LOCK_HELD`，锁丢失为 423 `LOCK_LOST`，与旧路由相同。B3 与现有草案一致：`job.status_changed`、`job.progress` 和终态事件类型已经写进契约，payload 的实现仍在 BE-M0-T06。本记录不改 `spec/openapi/demo-v1.json`。
