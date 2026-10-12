为什么有这个文件：记录QA对ISSUE-022契约冻结（73fde1e + ae91024）的复签。

它解决什么问题：确认上轮唯一不通过项已修复，冻结契约可以作为前后端开发依据。

# ISSUE-022 契约冻结 QA复签（REV-M0-T20）

- 被验提交：冻结 `73fde1e`，修复 `ae91024`；数据：仅合成数据。
- 结论：**通过**。上轮唯一不通过项（`spec/openapi/README.md:42` 写客户端无例外重试 502/503）已修复。

## 证据

- README 第 42 行补上：502 `MODEL_UNAVAILABLE` 与 503 `SECRET_KEY_UNAVAILABLE` 不是瞬时故障，客户端不要自动重试，后端不发送 Retry-After。
- P3 建议已采纳：`components.x-idempotency.retry` 末尾加上"没有 Idempotency-Key 的写入不自动重试。"，测试断言它在 retry 末尾、不在 description 里。
- 全量检索 spec 和 docs：当前依据里再无无例外的 502/503 重试说明；其余命中是交付记录、任务卡、测试记录等历史文字，或模型上游调用的重试（AI-02），不属于客户端重试。
- N9：`ae91024` 未改动任何 `Idempotent-Replayed` 头声明，`73fde1e` 的结论不变。
- 本地：契约测试 15 个通过；完整后端 pytest 351 个通过、8 个跳过（MySQL）；`qa_error_idempotency_live_http.py` 49/49 通过；治理检查通过。
- CI：ae91024 的 run 38217677190，governance、backend、backend-mysql、frontend、e2e 五个 job 全部 success。

## 观察项

- O-1（P3）：`docs/architecture/icg-reference-contract.md` 第 45 行（2026-10-11 写成，早于 N7）仍写"客户端只对网络错误、502和503用同一键自动重试"，没有 N7 两码例外。接口以冻结 JSON 为准，不阻塞；建议下次改这份文件时一并补上。
