# 任务交付：默认路径诚实化与 MySQL 门禁严格化（D1）

为什么有这个文件：记录 2026-10-26 用户拍板 B3 落地成果，堵住未设 `ICG_DATABASE_URL` 时静默回落到内存仓储还假装绿灯的隐患，明确生产环境强制 MySQL，并将前端演示模式 `VITE_DEMO` 默认策略诚实化置为 `false`。

它解决什么问题：消除“无 URL 静默 Memory 当绿”和“前端未设环境变量默认开演示账号”的虚假交付风险，保证生产、CI 与关演示冒烟环境行为诚实、边界明确。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | DEMO-MYSQL-DEFAULTS-2026-10-26 / D1 |
| 代码解释 | `docs/code/2026-10-26-demo-mysql-defaults.md` |
| 验收 | 1) `repository_from_environment()` 移除了 `pytest` 绕过分支，`ICG_REQUIRE_MYSQL=1` 且无 URL 时严格抛出 `RuntimeError`；<br>2) `test_mysql_gate.py` 11 项全绿，验证未设 URL 拦截、显式 Memory 允许、门禁失败快速中断；<br>3) 前端 `isDemoMode()` 默认返回 `false`，仅当显式设置 `VITE_DEMO=1` 或 `true` 时开启；前端 379 项单测与类型检查全绿；<br>4) `AGENTS.md` 冻结规则同步补充默认演示关闭与 MySQL 门禁要求。 |
| 项目进度 | D1 默认路径诚实化闭环交付，生产路径与门禁行为与用户拍板要求完全对齐，推进至 D2（后端去平铺） |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-26
- 关联决策：用户拍板 B3（强制 MySQL，禁止静默 Memory 当绿）
- 关联卡片：`BE-TECH-DEBT-PERSISTENCE`、`FE-TECH-DEBT-ROLES`
- 本地验收状态：`in-review`
- 分支：`feat/opencode-ICG`

---

## 2. 完成内容与变更说明

### 2.1 后端：堵住无 URL 静默回退 Memory 漏洞
- **改造文件**：[`backend/bid-core/icg/infra/mysql_gate.py`](../../backend/bid-core/icg/infra/mysql_gate.py)
  - 移除原 `if mysql_required() and "pytest" not in sys.modules:` 中对 `pytest` 的隐式豁免；
  - 改造为：一旦 `mysql_required()` 为 True（即 `ICG_REQUIRE_MYSQL=1`），若未配置 `ICG_DATABASE_URL`，无论运行环境是生产还是测试，均立即抛出 `RuntimeError("ICG_REQUIRE_MYSQL=1 but ICG_DATABASE_URL is missing")`；
  - 仅在未开启门禁且明确未配置数据库连接串时，才允许本地开发回退至 `MemoryRepository`。
- **保护生产入口实例**：[`backend/bid-core/icg_demo/main.py`](../../backend/bid-core/icg_demo/main.py)
  - 将模块顶层 `app = create_app(...)` 调整为测试环境惰性加载、生产环境直接加载，避免 pytest 收集用例阶段误触发全量启动异常，保证测试调用阶段严格报错并被记录为失败。

### 2.2 前端：演示模式 `VITE_DEMO` 默认策略诚实化
- **改造文件**：[`frontend/web/src/shared/roles.ts`](../../frontend/web/src/shared/roles.ts)
  - 修改 `isDemoMode()` 实现：未配置 `VITE_DEMO` 环境变量时，默认返回 `false`（走正式账号密码登录与 RBAC 8 角色可信会话）；
  - 仅当明确声明 `VITE_DEMO=1` 或 `VITE_DEMO=true` 时，才激活演示账号快捷选择器；
  - 杜绝因无环境变量而默认回落到 demo 账号冒充真实生产会话的缺陷。

### 2.3 协作规范：`AGENTS.md` 冻结规则强化
- **改造文件**：[`AGENTS.md`](../../AGENTS.md)
  - 新增持久化门禁强制范围说明：生产配置、CI 自动化作业与关演示端到端冒烟必须声明 `ICG_REQUIRE_MYSQL=1`；
  - 新增默认演示关闭说明：前端未配置 `VITE_DEMO` 默认为 `false`，确保企业级身份流为默认第一路径。

---

## 3. 验收结果与证据

1. **后端门禁专属测试**：
   - 执行 `pytest tests/backend/test_mysql_gate.py`：
   - 结果：**11 passed in 10.17s**（含缺 URL 抛出 RuntimeError、显式 Memory 允许、未配置数据库门禁阻断）；
2. **后端主流程回归测试**：
   - 执行 `pytest tests/backend/test_submission_finalize_gate.py tests/backend/test_checks_export_blocker_gate.py tests/backend/test_volume_finalize_gate.py tests/backend/test_compliance_rules_p0.py tests/backend/test_smoke_non_demo_pipeline.py tests/backend/test_mysql_gate.py`：
   - 结果：**36 passed in 27.40s**；
3. **前端单元测试**：
   - 执行 `pnpm --dir frontend/web test`：
   - 结果：**379 passed / 0 failed**（新增 `roles.ts: isDemoMode defaults to false when unset` 断言）；
4. **前端类型检查**：
   - 执行 `pnpm --dir frontend/web lint`：
   - 结果：**tsc 检查通过（0 错误）**；
5. **OpenAPI 一致性检查**：
   - 执行 `python backend/bid-core/export_openapi.py --check`：
   - 结果：**100% 一致**。
