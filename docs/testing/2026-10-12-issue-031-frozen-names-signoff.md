为什么有这个文件：记录QA对ISSUE-031错误码名单冻结（2439616）的变异复核与签署。

它解决什么问题：证明只改 errors.py 再重新导出 spec 不能让测试保持绿色。

# ISSUE-031 错误码名单冻结 QA签署（REV-M0-T18）

- 被验提交：`2439616`；复核基线：`ae91024`；数据：仅合成数据。
- 结论：**通过**。

## 变异（只在本地做，`git checkout` 还原，未提交）

| # | 变异 | pytest | qa_error_idempotency_live_http.py | 结论 |
|---|---|---|---|---|
| 1 | errors.py 把 `SECRET_KEY_UNAVAILABLE` 换成 `QA_FAKE_CODE`，并运行 `export_openapi.py` | `test_literal_domain_errors_use_the_single_frozen_status`、`test_openapi_declares_v1_error_body_status_table_and_retry` 失败 | FAIL：代码名 == 冻结名单、spec 枚举 == 冻结名单；总数仍是 143（PASS） | 拦住 |
| 2 | 只改 `FROZEN_NAMES` | 上述名单断言失败 | FAIL：代码名 == 冻结名单 | 拦住 |
| 3 | errors.py 和 FROZEN_NAMES 同时加 `QA_FAKE_CODE`，再导出 spec | 错误码测试全部通过 | FAIL：code 总数 143 -> 144 | 符合预期：同步更新属于有意变更，只有 QA 脚本里的总数检查能拦住 |

基线：不连数据库跑完整后端测试，351 个通过，8 个跳过。`spec/openapi/README.md` 第 30 行写明了"同一提交更新 FROZEN_NAMES"这条规则。

## 观察项

- O-1（P3）：`export_openapi.py` 导出的 spec 没有 `x-contract-status` 草案操作，会把已保存 spec 里的草案和 deprecated 标注删掉，`test_outline_contract_draft.py` 有 5 条测试因此失败。所以变异结果只看名单断言。重新导出 spec 不会保留草案，这一点需要在文档里写明，或者改导出脚本。
- O-2（P3）：pytest 里没有总数等于 143 的断言，总数只在 QA 实时脚本里检查。
