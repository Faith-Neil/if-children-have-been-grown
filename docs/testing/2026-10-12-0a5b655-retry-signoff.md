为什么有这个文件：记录QA对前端请求层重试修复（0a5b655）的签署。

它解决什么问题：确认冻结契约里不可重试的两个错误码只发一次请求，其余重试规则不变。

# 0a5b655 请求层重试修复 QA签署（REV-M0-T21）

- 被验提交：`0a5b655`（fix: do not retry 503 SECRET_KEY_UNAVAILABLE）；关联 ISSUE-030；数据：仅合成数据。
- 结论：**通过**，未发现缺陷。

## 证据

- 探针 `/workspace/qa-tools/t0a5b655_probe.mjs`（QA本地工具，未入库）对本地假 HTTP 服务逐项请求：34/34 符合预期。
- 502 `MODEL_UNAVAILABLE`：1 次请求，不自动重试。
- 503 `SECRET_KEY_UNAVAILABLE`：1 次请求，不自动重试。
- 普通 503 和不带错误体的 502：按原规则带同一 Idempotency-Key 重试。
- 不带 Idempotency-Key 的写请求：任何状态都不重试。
- 本地：Node 24.9.0 前端单测 97/97 通过（被验提交当时的数量）。

## 观察项

- 无。ISSUE-030 与被验卡状态不变，等项目经理设置。
