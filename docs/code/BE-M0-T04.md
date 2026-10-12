为什么有这个文件：说明 v1 编辑权路由接在哪，以及为什么旧入口还在。

它解决什么问题：避免把租约规则重写一遍，或让验证页失去原来的 `/api` 锁接口。

# BE-M0-T04：编辑租约迁到 /api/v1

`backend/bid-core/icg_demo/main.py` 在旧锁路由旁边增加三条 POST：

- `/api/v1/chapters/{chapter_id}/lock`
- `/api/v1/chapters/{chapter_id}/lock/renew`
- `/api/v1/chapters/{chapter_id}/lock/release`

它们调用 `DemoService.acquire_lock`、`renew_lock`、`release_lock`。请求体仍是 `LockRequest` 和 `LeaseRequest`。成功体仍是 `LeaseResponse` 或 `ReleasedResponse`。声明的失败响应使用 `V1Error`。路径以 `/api/v1/` 开头，异常处理器因此返回 `{code, message, details, traceId}`。

旧三条 `/api/chapters/.../lock` 路由没有删除，成功体也没有改成 v1。编辑页和 `/demo` 继续用旧入口。

没有新的错误码，没有新的表，也没有给这三条写入 `Idempotency-Key`。`operationId` 仍由框架生成，BE-M0-T07 再改成 lowerCamelCase。
