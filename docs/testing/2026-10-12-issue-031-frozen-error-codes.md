为什么有这个文件：留下错误码名字冻结的通过结果，以及一次故意换码后的失败结果。

它解决什么问题：避免只说名单已经冻住，却没有证明换一个名字再导出仍会失败。

# 2026-10-12 错误码名字冻结核对

关联 [ISSUE-031](../../issues/ISSUE-031.md)、[BE-M0-T16](../delivery/BE-M0-T16.md)。状态 in-review。只用合成数据。

## 未替换时

工作目录为仓库根。

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend/test_error_idempotency.py -q
```

结果：9 passed。其中 `set(ERROR_STATUS) == FROZEN_NAMES`，运行中 OpenAPI 与已保存 spec 的 `V1Error.code` 枚举都等于这份名单。名单长度为 143。

全量命令：

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend -q
```

结果：351 passed，8 skipped。QA 脚本另有两条对照：`代码名 == 冻结名单`、`spec V1Error.code enum == 冻结名单`。总数检查仍是 `len(ERROR_STATUS) == 143`。

## 故意替换后

在 `errors.py` 的 503 绑定里，把 `SECRET_KEY_UNAVAILABLE` 换成 `NOT_A_REAL_CODE`。这个旧码没有出现在 `DomainError(...)` 调用里。然后运行：

```text
python3 backend/bid-core/export_openapi.py
```

导出后：`len(ERROR_STATUS)` 仍是 143；spec 枚举等于新的 `ERROR_STATUS`；两边都不等于 `FROZEN_NAMES`。差集是 `NOT_A_REAL_CODE` 与 `SECRET_KEY_UNAVAILABLE`。

同一状态下，`test_literal_domain_errors_use_the_single_frozen_status` 在 `set(ERROR_STATUS) == FROZEN_NAMES` 失败；`test_openapi_declares_v1_error_body_status_table_and_retry` 在枚举集合对照失败。2 failed。

核对结束后已还原 `errors.py` 和 `spec/openapi/demo-v1.json`。仓库里没有 `NOT_A_REAL_CODE`。

## 治理

```text
node scripts/check-project-governance.cjs
```

输出：

```text
治理检查通过：260 份 Markdown、372 项任务、31 项 Issue。
```
