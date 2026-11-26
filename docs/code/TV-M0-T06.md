为什么有这个文件：说明 TV-M0-T06 的矩阵响应写在哪里。

它解决什么问题：下次接历史标书检索时，能看出默认无偏离、逐条确认和失败行是分开的。

# TV-M0-T06 代码说明

规则在 `backend/bid-core/icg/domain/technical_matrix.py`。技术分册抽取成功后，`fill_technical_responses` 给每条技术条款写响应。

命中的一行记下文件名和原文。`judge_deviation` 把本次条款和历史做法交给本地模型，模型只返回无偏离、正偏离或负偏离。公网模型不调用。没有本地模型时这行是 `draft_failed`，不写成无偏离。只有无偏离的历史行走批量确认。

没有命中时用 `local_draft` 写一句无偏离，来源记为 `model`，批量确认会拒绝。检索函数或拟写函数抛错时，来源分别是 `retrieval_failed`、`draft_failed`，响应留空。

确认前的拦截在 `guard_technical_confirm`。正偏离和偏离的说明在 `validate_response`，只对技术条款加严。两册旧项目的批量确认仍会取消目录确认；技术条款的整表确认不会。
