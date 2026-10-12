为什么有这个文件：留下 503 `SECRET_KEY_UNAVAILABLE` 只发一次的检查方法。

它解决什么问题：避免把普通 503 的重试和这一条例外混在一次手工点击里。

# 2026-10-12 ISSUE-030 密钥不可用重试

日期 2026-10-12。关联 [ISSUE-030](../../issues/ISSUE-030.md)。契约基线 `73fde1e`。

## 方式

仓库根执行 `node --test frontend/web/tests/request-layer.test.mjs`。测试用 `node:test` 替换 `fetch`，不启动后台。新增一条同时覆盖四类响应：

| 响应 | 期望次数 |
|---|---|
| 502 `MODEL_UNAVAILABLE` | 1，追踪号保留 |
| 503 `SECRET_KEY_UNAVAILABLE` | 1，追踪号保留 |
| 503 `UI_NOT_READY` | 3，第三次成功 |
| 裸网关 502 | 3，第三次成功 |

原有请求层用例仍在同一文件里。

## 结果

`frontend/web/tests/request-layer.test.mjs`：15 passed，0 failed。其中新增用例先在未改 `canRetryStatus` 时失败（`SECRET_KEY_UNAVAILABLE` 实际发送 3 次），改判断后通过。随后 `node --test frontend/web/tests/*.test.mjs tests/frontend/*.test.mjs`：93 passed，0 failed。`node scripts/check-project-governance.cjs`：治理检查通过：255 份 Markdown、371 项任务、30 项 Issue。

## 局限

没有请求真实后台，也没有浏览器点击。下载链使用同一 `canRetryStatus`，节点测试没有点下载链接。`spec/openapi/README.md` 的旧句子仍写重试全部 502 和 503；接口字段以 `73fde1e` 的 JSON 为准，本轮不改 README。
