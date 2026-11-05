为什么有这个文件：在 MySQL 持久化、关演示 UI 下执行 L2 人工全链路验收。

它解决什么问题：`Start-Demo.ps1` 仅内存仓库，无法验证重启后数据仍在，也不满足 L2 留证口径。

# L2 手动全链路验收 Runbook

拍板见 [2026-11-02-l2-acceptance-pm-decisions.md](../decisions/2026-11-02-l2-acceptance-pm-decisions.md)。

## 0. 前置

1. 本机 **MySQL 8**。2026-11-02 本机 `3306` 已被容器 `rk-mysql` 占用，拉 `mysql:8.4` 超时，已用本地镜像起 **`icg-mysql`（mysql:8.0）映射到 3307**，库 `icg` 已 `alembic upgrade head`（至 `0014`）。示例：

```powershell
docker run -d --name icg-mysql -e MYSQL_ROOT_PASSWORD=localdev -e MYSQL_DATABASE=icg -p 3307:3306 mysql:8.0
$env:ICG_DATABASE_URL = "mysql+pymysql://root:localdev@127.0.0.1:3307/icg?charset=utf8mb4"
```

不要把 ICG 写进 `rk-mysql` 或 RAGFlow 的 `docker-mysql-1`。
2. 仓库根目录已存在 `.venv`（或执行 `Start-L2.ps1 -Install`）。
3. 端口默认 **8710**；浏览器访问 `http://127.0.0.1:8710/`。

## 1. 启动（持久化 + 关演示 UI）

```powershell
# 按需改连接串（勿提交仓库）
$env:ICG_DATABASE_URL = "mysql+pymysql://root:localdev@127.0.0.1:3307/icg?charset=utf8mb4"
& .\backend\bid-core\Start-L2.ps1 -Install   # 首次；后续可省略 -Install
```

验收前确认：

```powershell
Invoke-RestMethod http://127.0.0.1:8710/health
```

期望：`repository` 为 `mysql`，`persistent` 为 `true`；`mode` 为 `development`（合成 alpha 账号落库）或 `production`（空库 admin 初始化，见第 8 节）。

登录（development 路径）：`POST /api/v1/auth/login`，例如 `alpha-manager` / `X_2026`（与 `smoke_demo.authenticate` 一致）。

## 2. L2 主路径（GUI，建议单会话 60～90 分钟）

| 步骤 | 角色 | 操作 | L2 通过标准 |
|---|---|---|---|
| 1 | 项目负责人 | 登录 → 新建项目 → 团队/分册负责人 | 项目出现在列表；刷新后仍在 |
| 2 | 项目负责人 | 上传合成 `.txt` 招标 → 解析 → 确认条款/事实 | 未确认项清零后才能继续 |
| 3 | 编写人 | 矩阵响应 + 商务证据挂接 | 星号/废标条款有映射或明确响应 |
| 4 | 本节编写人 | 方案确认 → 生成候选 → 提交正文（技术+商务） | Word 只含已提交正文 |
| 5 | 项目负责人 | **全册检查** | 出现 R06/R26/R38 等 **warning** 时，在检查页 **逐项填理由放行** |
| 6 | 项目负责人 | 导出 **内部稿**（internal） | 200；两册可下载；`excludes_drafts: true` |
| 7 | 项目负责人 | 导出 **内部评审稿**（internal_review） | 若仍有 blocker：允许下载且带合规警示；无 blocker 时 `has_blockers: false` |
| 8 | 项目负责人 | 尝试 **递交版**（submission） | 未定稿 → `RULES_INCOMPLETE`；有 blocker → `CHECK_BLOCKER_EXISTS`；**仅 warning 且已放行** 不应单独挡递交（仍可能因未定稿被拦，属 L2 预期） |
| 9 | 任意 | **重启后台** 再打开同一项目 | 项目、矩阵、章节正文、检查记录仍在（MySQL 验收核心） |

## 3. R38 一期（只 warning）

- 对「要求截图/证明」的评分项：缺附件或功能点标签不匹配 → 检查项为 **warning**（代码 `PROOF_ATTACHMENT_MISSING` / `FEATURE_PROOF_MISSING`），**不是 blocker**。
- 验收动作：故意少挂一个功能点标签 → 检查不通过 → 负责人放行 warning → 内部稿可导出。
- **不要求** OCR；附件文字识别未接入不算 L2 失败项。

## 4. 建议留证（工作区外）

- `/health` JSON 截图（含 `repository: mysql`）。
- 一次全册检查的 issues 列表（含 R38 warning）。
- 两册 `.docx` 文件名与 SHA（导出元数据或下载响应头）。
- 重启前后同一 `project_id` 的工作区截图。

## 5. 自动化辅助（非签字替代）

```powershell
cd backend\bid-core
python smoke_t06.py
python -m pytest ..\..\tests\backend\test_smoke_non_demo_pipeline.py -q
```

## 6. 不通过时常见断点

| 现象 | 原因 |
|---|---|
| 导出 409 `CHECK_FAILED` | warning 未放行（ISSUE-046 后常态） |
| `/health` 仍 `memory` | 未设 `ICG_DATABASE_URL` 或用了 `Start-Demo.ps1` |
| 登录无 alpha 账号 | `ICG_ENV=production` 空库，改 development 或走第 8 节 admin |
| 递交版一直 409 | 分册未定稿（L2 允许；先完成交叉复核 + finalize 再测递交） |

## 7. L2 vs L3（验收签字口径）

- **L2 签字**：内部稿/评审稿稳定、warning 放行流程可用、持久化重启不丢主数据、递交版仅 blocker/定稿闸门拦截。
- **L3**：在完整规则与定稿齐备下，递交版可出且无 `RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS` 虚假声称。

## 8. 可选：`ICG_ENV=production` 空库

```powershell
$env:ICG_ENV = "production"
$env:ICG_ADMIN_INITIAL_PASSWORD = "<工作区外强口令>"
$env:ICG_ALLOW_DEMO_LOGIN = "0"
```

首次 `admin` / 上述口令登录 → 强制改密 → 再建公司/用户（平台管理员能力）。此路径更贴近上线，但准备时间更长；L2 功能验收可优先用第 1 节 **development + MySQL** 路径。
