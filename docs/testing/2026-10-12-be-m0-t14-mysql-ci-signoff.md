为什么有这个文件：记录QA对BE-M0-T14托管MySQL CI作业的独立验收。

它解决什么问题：用真实Actions日志和本地MySQL 8.4复跑确认作业确实连库、确实会失败，而不是只看工作流文件。

# BE-M0-T14 托管 MySQL CI 作业 QA 签署

日期 2026-10-12（UTC+8）。ISSUE-025 / BE-M0-T14，签署卡 REV-M0-T12，归入 ISSUE-013。分支 `codex/repository-foundation`，被验提交 `ac6ea02`（工作流实质改动在 `763064a`、`b91d331`），核对到 `034b184`。

## 结论

**通过。** AC-01～AC-04 全部满足。BE-M0-T14 与 ISSUE-025 保持 in-review，done 由项目经理设置。另记 3 项 P3 观察（M1～M3），不挡签署。

## 逐条核对

| 编号 | 结果 | 证据 |
|---|---|---|
| AC-01 | 通过 | 作业 `runs-on: ubuntu-24.04`，`python-version: "3.13.5"`，作业级 `permissions: contents: read`，工作流中无 `secrets.` 引用 |
| AC-02 | 通过 | 步骤内 `docker run mysql:8.4`，`--character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci`，库 `icg_demo`；密码 `openssl rand -hex 24` 运行时生成并 `::add-mask::`。日志中 URL 与密码均为 `***`；检查日志里的长十六进制串只有 64 位 sha256（缓存/镜像摘要），无 48 位密码。日志输出 `icg_demo charset collation: utf8mb4	utf8mb4_unicode_ci` |
| AC-03 | 通过 | 日志依次出现 `Running upgrade  -> 0001_baseline, empty baseline` 与 pytest `2 passed, 320 deselected`（ac6ea02）/ `2 passed, 335 deselected`（bde8e9e），即真连 MySQL 执行，不是跳过 |
| AC-04 | 通过 | 把工作流守卫脚本原样抽出，对本地 junit 运行：正常 2/0/0/0 → 0；全部跳过 → 1；连库失败 15 errors → 1；文件缺失 → 1。真实失败样例：`763064a` 的 run 38207182321 启动步骤失败，守卫报 `mysql junit file is missing`，作业 failure。原 `backend` 作业不设 `ICG_DATABASE_URL`（全文件仅 `backend-mysql` 出现该变量） |

## GitHub Actions（offline-check，时间为 UTC+8）

| run | 提交 | backend-mysql | 整体 |
|---|---|---|---|
| 38207182321 | 763064a | failure（MySQL 未就绪，作业正确变红） | failure |
| 38207508936 | b91d331 | success | success |
| 38207956138 | ac6ea02 | success | success（13:26） |
| 38210477624 | bde8e9e | success | success（14:00） |

ac6ea02 之后到 d55d507 的 14 次运行均为 success，另 c6948c0 一次 cancelled（被后续推送取代，非失败）。

## 本地独立复跑

QA 盒子无 docker，用官方 8.4.6 压缩包实例 127.0.0.1:33061、库 `icg`、专用账号 `icg`；密码只从本机文件读进环境变量，未写入仓库或日志。`ICG_REQUIRE_MYSQL=1`。

| 命令 | 结果 |
|---|---|
| `alembic … downgrade base` | `0001_baseline -> ` ，只剩 `alembic_version`（空表） |
| `alembic … upgrade head` / `current` | `0001_baseline (head)`，表仅 `alembic_version` |
| `pytest tests/backend -m mysql --junitxml` | 2 passed、335 deselected |
| 再次 downgrade base → upgrade head | 均成功，可往返 |
| `pytest tests/backend -q`（带 MySQL 环境） | 337 passed |
| 去掉 URL、保留 `ICG_REQUIRE_MYSQL=1` | 2 failed（门禁生效） |
| 去掉 URL 与 REQUIRE | 2 skipped → 守卫判失败 |
| 错误密码 | 15 errors（收集期），守卫判失败 |

`node scripts/check-project-governance.cjs`：治理检查通过：227 份 Markdown、366 项任务、28 项 Issue。

## 观察项（不挡签署）

- **M1（P3）**：CI 只做 `upgrade head`，不做 `downgrade base` 往返。本地已验证可往返；建议有业务表迁移时在作业里加 downgrade→upgrade 一步。负责人：后端/DevOps。
- **M2（P3）**：守卫只在“全部跳过”时失败，部分跳过（如 2 条中 1 条跳过）仍通过。现在有 `ICG_REQUIRE_MYSQL=1` 兜底，风险低；建议改成 `skipped > 0` 即失败。
- **M3（P3）**：`ICG_MYSQL_PASSWORD` 经 `$GITHUB_ENV` 暴露给后续所有步骤（已掩码），后续步骤只需 `ICG_DATABASE_URL`，可去掉。另 BE-M0-T14 交付里的 362 项计数已过时，随下次基线同步更新。

已知遗留：连库失败在收集期报错（Q2）仍归 BE-M0-T11。
