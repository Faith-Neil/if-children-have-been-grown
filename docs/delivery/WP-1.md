为什么有这个文件：记录质量整改路线图 WP-1（基线锁定、Windows CP936 编码加固与治理规则固化）的实际完成内容、测试验收与交付记录。

它解决什么问题：解决 Windows 环境下 CP936 代码页导致 Alembic 配置解析与迁移脚本报错中断的隐患，核验数据库迁移链 0001~0011 的连贯性与正确性，并在 AGENTS.md 中固化后端分包、前端按域、API 收敛、测试收口与 Layout First 等架构质量规则，建立可信整改基线。

# WP-1：基线锁定与 Windows CP936 编码加固交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | WP-1 |
| 代码解释 | 修复 alembic.ini 在 Windows CP936 环境下的编码解析隐患；核对 0001~0011 迁移脚本拓扑链；在 AGENTS.md 注入结构冻结与 Layout First 规则。 |
| 验收 | alembic.ini 在 Windows CP936 环境下解析无异常；alembic heads 与 0001~0011 迁移链严格单向拓扑无分叉；AGENTS.md 固化 6 大质量与结构冻结规则；后端 610 passed、前端 344 passed 基线锁定。 |
| 项目进度 | WP-1 闭环；为后续 WP-2 至 WP-7 质量整改提供稳固规范基线。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 分支与提交：`feat/opencode-ICG`，关联提交 `0b2308c`（Alembic 编码加固与迁移核验）、`87c61d8`（AGENTS.md 规则固化与计划锁定）
- 关联规划：`docs/delivery/2026-10-22-quality-remediation-plan.md`（阶段 A / WP-1）
- 关联规则：`AGENTS.md`（质量整改与结构冻结规则）
- 本地验收状态：已通过（Alembic 迁移链解析正常、前后端基线测试全绿、项目治理检查通过）
- 合入 / 发布状态：已推送至远程分支 `origin/feat/opencode-ICG`

## 完成内容与变更文件

### 1. Windows CP936 编码根治
- **问题诊断**：在 Windows 简体中文操作系统（代码页 936 / GBK）下，Alembic 默认使用本地代码页读取 `alembic.ini`，若包含非 ASCII 字符或特定 BOM 头将触发 `UnicodeDecodeError: 'gbk' codec can't decode byte ...`，导致数据库迁移与检查无法运行。
- **加固落地**：对 `backend/bid-core/alembic.ini` 及相关配置进行编码净化，确保所有配置键与注释在 GBK/CP936 环境下安全解析，无异常字符。

### 2. Alembic 迁移链 0001~0011 完整性核对
- 逐一核验 `backend/bid-core/migrations/versions/` 目录下全部 11 个版本迁移脚本（0001 至 0011）：
  - `0001_initial_schema.py`
  - `0002_add_chapter_locks.py`
  - `0003_add_sla_templates.py`
  - `0004_add_idempotency_records.py`
  - `0005_add_compliance_matrices.py`
  - `0006_add_extracted_facts.py`
  - `0007_add_generation_pipeline.py`
  - `0008_add_audit_logs.py`
  - `0009_add_company_mask_settings.py`
  - `0010_add_sla_history_table.py`
  - `0011_add_job_progress_records.py`
- 验证各迁移脚本的 `down_revision` 严格首尾相接，拓扑排序无断链、无环路、无重复 heads。

### 3. AGENTS.md 架构质量与结构冻结规则固化
在项目治理核心准则 `AGENTS.md` 中新增「质量整改与结构冻结规则」专节，明确要求：
1. **后端分包边界**：禁止向 `backend/bid-core/icg_demo/`（或后续 `icg/`）根目录平铺新增文件，必须划分到上下文子包（api/domain/infra/app）。
2. **前端按域分层**：禁止向 `frontend/web/src/` 根目录平铺新增页面文件，必须归入域目录（app/shell/project/editor/library/admin/status/shared）。
3. **UI 与界面设计克制（Layout First）**：*Avoid unnecessary secondary labels and descriptions. Let the layout do the explaining.* 避免在 UI 设计与组件开发时堆砌莫名其妙的次级标签、徽标或说明文字，杜绝将界面做成说明书；依靠清晰的视觉层级、布局与交互流自然表达意图。
4. **API 接口收敛**：新接口只加 `/api/v1`；`/api/demo` 路径标为 deprecated，只读兼容，不再向旧 demo 路径添加新端点。
5. **前端测试权威收口**：前端唯一权威测试套件位于 `frontend/web/tests/`（含 `unit/`，通过 `pnpm --dir frontend/web test` 运行）。根目录 `tests/frontend/` 仅保留兼容历史文档引用的轻量级转发壳，严禁新增第三套测试目录或业务逻辑。
6. **持久化门禁**：生产配置强制 `ICG_REQUIRE_MYSQL=1`；仅在测试环境下允许内存仓储，生产路径严禁静默回落到内存仓储。

## 测试与验收证据

1. **Alembic 迁移链验证**：
   - 检查 `alembic` 迁移脚本拓扑连接，0001 到 0011 链条完备，无断裂。
2. **基线全量测试锁定**：
   - 后端 Pytest：`610 passed, 42 skipped, 0 failed`。
   - 前端测试：`344 passed, 0 failed`。
3. **项目治理检查**：
   - `node scripts/check-project-governance.cjs` 检查通过，无规则违背。
