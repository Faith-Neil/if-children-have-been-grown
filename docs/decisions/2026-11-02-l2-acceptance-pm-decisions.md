为什么有这个文件：记录项目经理对 L2 目标、R38 一期行为与验收方式的拍板。

它解决什么问题：避免后续任务仍按 L3 或 R38 阻断口径推进，或与「内存演示启动」混淆。

# L2 手动验收拍板（2026-11-02）

关联：`main` @ `36b7e41`（CI 全绿）；[ISSUE-046](../../issues/ISSUE-046.md) 已关闭。

| 项 | 决定 |
|---|---|
| **上线档位** | **L2 一期 MVP**：建项 → 解析确认 → 矩阵 → 生成/编辑 → 检查 → **内部稿 / 内部评审稿**稳定；递交版仅在 **blocker** 时拦截（非 L3「合规全绿即可递交」） |
| **R38（一期）** | **只出 warning**，须项目负责人逐项放行；**不做 OCR/附件文字识别**（二期）；实现口径见 `staff_proof_rules.py` |
| **验收环境** | **MySQL 持久化 + 关演示前端**（`ICG_REQUIRE_MYSQL=1`、`VITE_DEMO=0`），禁止仅用 `Start-Demo.ps1` 内存模式作为 L2 留证 |
| **验收方式** | **人工全链路**一轮 + 重启后数据仍在；自动化冒烟（`smoke_t06`、关演示 pytest）仅作辅助，不替代 GUI 签字 |

## 操作入口

- 持久化启动：[`backend/bid-core/Start-L2.ps1`](../../backend/bid-core/Start-L2.ps1)
- 手动步骤与通过标准：[`docs/testing/2026-11-02-l2-manual-acceptance-runbook.md`](../testing/2026-11-02-l2-manual-acceptance-runbook.md)

## 诚实边界（L2 仍不等于 PRD 全量上线）

- 部分规则仍为 stub 或依赖合成数据（见 [ISSUE-046 矩阵](../decisions/2026-11-02-issue-046-realignment-matrix.md) 备注）。
- 内网 RAGFlow / 本地 Qwen 未接时，生成与知识库能力仍按演示替身或跳过项记录。
- `ICG_ENV=production` 空库路径需 `admin` + `ICG_ADMIN_INITIAL_PASSWORD` 初始化，与「合成 alpha 账号持久化验收」分两条 runbook 节说明。
