为什么有这个文件：记录QA对PR #4 / ISSUE-034（REV-M0-T27）R1～R9 的正式签署。

它解决什么问题：在 tip `5eced4f` 上逐条验收，含真实 MySQL 8.4 的 R4/R6/R7，不把 SQLite 探针或跳过冒充实机通过。

# PR #4 / ISSUE-034 R1～R9 QA签署（REV-M0-T27）

- 被验 tip：`5eced4fb91651d6aeb6a23ba5f9d2b5af0143693`（分支 `codex/review-foundation-fixes`；工作树 `/workspace/qa-wt-pr4`）。
- 环境：Linux；Node 24.9.0；Python 3.13；venv `/workspace/qa-venv`；MySQL 8.4.6 监听 `127.0.0.1:33061`，库 `icg`、用户 `icg`，密码只经 `/tmp/qa-mysql-pw` 进环境变量，不进仓库与日志。
- 结论：**R1～R9 全部通过**。**ISSUE-034 / REV-M0-T27 保持 in-review，不标 done / closed，不合入。**

## 逐条对照

| 编号 | 结果 | 证据 |
|---|---|---|
| R1 迟到401不登出新账号 | 通过 | 单测：late company GET 401 / Editor history 401；Playwright `review-regressions` 切账号后迟到401 |
| R2 失败切页后仍确认离开 | 通过 | 单测：failed 500/403 保留脏编辑并再确认；Playwright failed editor-to-matrix |
| R3 SECRET_KEY_UNAVAILABLE 只发1次 | 通过 | `request-layer`：502 MODEL_UNAVAILABLE 与 503 SECRET_KEY_UNAVAILABLE 各1次 |
| R4 同键并发只产生一份片段 | 通过 | `test_snippet_review` 3 passed；真实 MySQL HTTP 双并发同键：两份 200、同一 `snippet-…` id，其一 `Idempotent-Replayed: true` |
| R5 回执不受内存2048裁剪 | 通过 | `test_receipt_review` 2048/2049 重放；`-m mysql` `test_mysql_keeps_more_than_2048_receipts` |
| R6 旧快照清理不删新回执 | 通过 | `test_receipt_review` created_at/fingerprint 两例；真实 MySQL 条件 DELETE：旧条件 rowcount=0 且新指纹保留，匹配条件可删 |
| R7 旧租约不覆盖新锁 | 通过 | `test_lease_review` 8 passed；真实 MySQL：旧续期/释放均 `423 LOCK_LOST`，库中仍为接管方 `lease_token`；`-m mysql` 租约 3 passed |
| R8 证据抽屉重核当前权限 | 通过 | `evidence-orchestration`：撤权后不可写、不发 PATCH；Playwright evidence drawer |
| R9 资料补录走统一导航 | 通过 | `evidence-orchestration`：supplement 走应用历史；脏编辑返回/取消保留序号 |

## 汇总命令结果

| 检查 | 结果 |
|---|---|
| 前端单测 | **113 passed**（0 fail） |
| 前端构建 | 通过；入口 **318.42 kB / gzip 101.83 kB** |
| Playwright | **16/16 passed**（约 55.8s） |
| 治理检查 | 通过：301 Markdown、384 任务、35 Issue；治理/原型等 **35/35** |
| 后台无库 | `env -u ICG_DATABASE_URL` → **371 passed，13 skipped**（mysql 标记） |
| 真实 MySQL `-m mysql` | 清表后 **12 passed** |
| R4/R5/R6/R7 回归文件 | `snippet_review`+`receipt_review`+`lease_review` **16 passed** |

## CI

本 tip `5eced4f` **无** GitHub Actions 记录。`offline-check` 仅监听 `codex/repository-foundation` 的 push / pull_request；`codex/review-foundation-fixes` 推送未触发。不以「无 CI」挡签署；本地证据已齐。合入 foundation 后应有 CI。

## 观察项

- O-1（P3）：全量后台在已设 `ICG_DATABASE_URL` 且库内残留租约/回执时，部分内存假设用例会失败（本轮见 24 failed）；正式基线仍以**未设库 URL** 的 371 passed 为准，MySQL 另跑 `-m mysql` 与专项探针。不挡签署。
- O-2（P3）：片段保障仍限本进程；正文等仍在内存；继续单进程/单副本。属既有限度，本卡不扩大。

## 状态

ISSUE-034、REV-M0-T27 保持 **in-review**，**不标 done**。未合入，未发布。
