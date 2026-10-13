为什么有这个文件：记录QA对BE-M0-T16（冻结错误码名字）在 tip `90b2334` 的正式签署。

它解决什么问题：确认 `set(ERROR_STATUS)==FROZEN_NAMES` 与 spec 枚举一致；ISSUE-031 已 closed，本卡仍等项目经理标 done。

# BE-M0-T16 冻结错误码名字 QA签署（REV-M0-T34）

- 被验 tip：`90b2334`。关联 ISSUE-031（已 closed，QA ae6fd10 / REV-M0-T18）。
- 环境：未设数据库连接串；仅合成数据。
- 结论：**通过**。**BE-M0-T16 / 本卡均不标 done**；不重开 ISSUE-031。

## 验收对照

| 检查 | 结果 | 证据 |
|---|---|---|
| `set(ERROR_STATUS) == FROZEN_NAMES` | 通过 | 长度均为 **143**；集合相等 |
| spec `V1Error.code` enum == 冻结名单 | 通过 | `demo-v1.json` 枚举 143 且等于 `FROZEN_NAMES` |
| 契约测试 | 通过 | `test_error_idempotency.py` 含名单断言；专项套件含本文件 **20 passed** |
| 无库全量 | 通过 | **381 passed，13 skipped** |
| 接口约定 | 通过 | `spec/openapi/README.md` 写明增删须同提交更新 `FROZEN_NAMES` |
| 变异（既有） | 沿用 | ISSUE-031 / REV-M0-T18 已证：只改 `errors.py` 再导出会失败；本轮未再改仓库文件做变异 |

## 独立复跑命令

```text
PYTHONPATH=backend/bid-core python -c "from icg_demo.errors import ERROR_STATUS; from icg_demo.frozen_error_codes import FROZEN_NAMES; import json; from pathlib import Path; e=json.loads(Path('spec/openapi/demo-v1.json').read_text())['components']['schemas']['V1Error']['properties']['code']['enum']; assert set(ERROR_STATUS)==FROZEN_NAMES==set(e) and len(ERROR_STATUS)==143"
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend/test_error_idempotency.py -q --tb=line
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend -q --tb=line
node scripts/check-project-governance.cjs
```

## 观察项

- O-1：ISSUE-031 已 closed；本卡仍 in-review，等项目经理设置 done。
- O-2（P3）：总数 143 断言仍主要在 QA live 脚本；pytest 侧靠集合相等。

## 状态

BE-M0-T16、REV-M0-T34 保持 **in-review**，**不标 done**。
