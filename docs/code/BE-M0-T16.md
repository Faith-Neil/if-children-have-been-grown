为什么有这个文件：说明错误码名字名单和运行时状态表是两份东西。

它解决什么问题：避免把“导出后 spec 与代码一致”当成“名字没有被换掉”。

# BE-M0-T16 代码解释

关联 [ISSUE-031](../../issues/ISSUE-031.md)。状态 in-review。

## 入口

`backend/bid-core/icg_demo/frozen_error_codes.py` 里的 `FROZEN_ERROR_CODE_NAMES` 是按字母序写下的 143 个名字。`FROZEN_NAMES` 是它的 `frozenset`。这份文件不由 `export_openapi.py` 生成。

`errors.py` 的 `ERROR_STATUS` 仍是每个名字到 HTTP 状态的运行时表。本卡没有改这张表里的任何一个名字或状态。

## 调用顺序

1. 测试导入 `ERROR_STATUS` 和 `FROZEN_NAMES`。
2. `set(ERROR_STATUS) == FROZEN_NAMES` 只比较名字，不比较状态。
3. `create_app().openapi()` 里的 `V1Error.code` 枚举来自 `sorted(ERROR_STATUS)`。测试再要求这个枚举的集合等于 `FROZEN_NAMES`。
4. 已保存的 `spec/openapi/demo-v1.json` 用同一条规则核对。导出脚本把运行时表写进这份 JSON，不会改冻结名单。

QA 脚本 `tests/backend/qa_error_idempotency_live_http.py` 在原有的“spec 状态表等于代码表”和“总数 143”之外，增加“代码名等于冻结名单”和“spec 枚举等于冻结名单”。

## 关键判断

删一个旧名字、加一个新名字之后，`len(ERROR_STATUS)` 仍可以是 143。重新导出后，spec 枚举会等于新的 `ERROR_STATUS`。这两项都过，是因为它们跟着运行时表走。只有冻结名单还留着旧名字，集合不相等，测试失败。

要让测试通过，同一提交必须改三处：`errors.py` 的表、重新导出的 spec，以及 `frozen_error_codes.py`。规则写在 `spec/openapi/README.md`。

## 限制

名单不记录 HTTP 状态。状态仍由 `ERROR_STATUS` 和 `x-error-status` 核对。本卡不决定将来能不能增加错误码，只要求增加或删除时把名单一起改。
