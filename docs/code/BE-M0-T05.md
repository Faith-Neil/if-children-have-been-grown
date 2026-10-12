为什么有这个文件：说明单章导出把检查、版本和输入摘要记在哪。

它解决什么问题：避免只凭文件编号把已经过期的导出让人当成当前结果。

# BE-M0-T05：导出快照语义

`DemoService.check` 把 `project_input_fingerprint` 记在检查上。`DemoService.export` 在正文版本和摘要仍匹配之后，再核对这份输入摘要。不一致时返回已有的 409 `CHECK_STALE`。

导出记录保存 `check_id`、`revision`、`content_hash` 和 `input_fingerprint`。`ExportResponse` 原样返回这四项，另有 `excludes_drafts: true`。响应里没有 `stale` 字段。

下载时先按版本和正文摘要拒绝，再按输入摘要拒绝。两种情况都是已有的 409 `EXPORT_STALE`。资料写入会改变同公司项目的输入摘要，因此旧单章文件不能继续下载。

没有新的错误码，没有新的表，也没有把这条路由改成 202。
