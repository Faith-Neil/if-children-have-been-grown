# ICG 质量审查与整改方案（交给 Antigravity）
> **历史快照（DOC-SYNC-1）：** 本文记录整改当时目标与验收；**现行**仓库结构与入口约定见 `docs/architecture/repository-layout.md` 与 `AGENTS.md`。

- 审查日期：2026-10-22（Asia/Shanghai）
- 本机路径：`C:\Users\徐佳馨\if-children-have-been-grown`
- 分支：`feat/opencode-ICG`（HEAD `dc2000b`；审查时工作区有大量未提交改动，用户正在 commit/push）
- 基线文档：`ICG/product doc/` 下 PRD MVP v1.8、kb-data-dictionary v1.9；看板 `docs/TASK_BOARD.md`
- 约束：不改技术栈（React/antd/Vite + FastAPI + MySQL 8 + RAGFlow）；先结构债后新功能；每阶段可独立验收

---

## 0. 总判断

功能面铺得很快（章节生成、检索、工作流、八角色测试、大量 delivery/QA 文档），但**产品成熟度被结构债拖住**：

| 维度 | 评级 | 一句话 |
|---|---|---|
| 功能覆盖 | 中高 | 主链路壳子多，能力在涨 |
| 架构可维护性 | 低 | 扁平巨石 + demo 命名 |
| 身份/权限产品化 | 中低 | 后端有八角色测试，前端仍偏三演示角色 |
| 持久化可靠性 | 中 | MySQL/Alembic 在长，默认仍可回落内存 |
| 契约一致性 | 中低 | `/api/demo` 与 `/api/v1`、双错误体并存 |
| 前端工程化 | 低 | 无路由库、无按域目录、App 巨石 |
| 测试与文档 | 中 | 测试不少但目录重复；状态文档滞后 |
| 协作风险 | 高 | 未推脏树极大（审查时） |

**原则：先冻结可协作基线 → 无行为重构分层 → 收敛演示旁路 → 再开新功能。**

---

## 1. 问题清单（含新发现）

### P0 — 立刻会伤协作 / 正确性

| ID | 问题 | 证据 | 为何是问题 |
|---|---|---|---|
| P0-1 | 超大未推工作区 | 审查时约 48 文件改动 +17k/−6.5k，~303 未跟踪 | 远程不可见，评审/CI/回滚失效 |
| P0-2 | Alembic `0005`–`0011` 曾未跟踪 | `backend/bid-core/alembic/versions/` | 他人拉代码无法复现库结构 |
| P0-3 | 默认持久化可回落 Memory | `main.py`/`database.py`：未设 `ICG_DATABASE_URL` → 内存仓 | 「测通」与「生产路径」不一致 |
| P0-4 | 双 API + 双错误体 | `/api/demo/login` 仍在；错误体同时有 `traceId` 与 `error/request_id`（`main.py`） | 前端易踩旧路径，排障困难 |
| P0-5 | OpenAPI 单文件过大且易漂移 | `spec/openapi/demo-v1.json` ≈ 889KB | 契约难审、难 diff、易与代码脱节 |

### P1 — 结构债（你已点名 + 加重）

| ID | 问题 | 证据 | 建议动作 |
|---|---|---|---|
| P1-1 | 前端 `src` 全平铺 | `frontend/web/src` ≈ **81** 文件、0 业务子目录 | 按域物理搬家（无行为变更） |
| P1-2 | 前端巨石组件 | `ProjectPages.tsx`/`EditorPage.tsx` ≈60KB+；`App.tsx` ≈47KB / **613 行**；`EditorPage` **1055 行**；`ProjectPages` **742 行** | 拆页面 + 拆编排 |
| P1-3 | 后端 `icg_demo` 扁平巨石 | `database.py` **~2079 行 / 101KB**；`workflow.py` **~1421 行 / 92KB**；包内 ~35 py | 按限界上下文分包 |
| P1-4 | 包名/路径仍叫 demo | `backend/bid-core/icg_demo/`、`/api/demo/*`、`smoke_demo.py` | 重命名计划 + 兼容期 |
| P1-5 | 前端无正式路由库 | `package.json` 无 `react-router`；靠 `App.tsx` 状态切页 | 引入路由或至少抽路由表模块 |
| P1-6 | 状态全堆在 App | `App.tsx` 大量 `useState` | 按域 Context/store 下沉 |

### P2 — 产品/架构偏移

| ID | 问题 | 证据 | 影响 |
|---|---|---|---|
| P2-1 | 会话仍强制演示模式 | `types.ts` / `session-navigation.ts`：`synthetic-demo` + `legacy-demo-compat` | 无法当正式登录产品 |
| P2-2 | 前端角色模型偏三档 | UI/会话仍 manager/editor/viewer 味道；后端已有八角色归一与测试 | 前后端权限语义分裂 |
| P2-3 | 演示账号硬编码 | `adapters.py` 合成账号 alpha/beta-* | 正式环境数据污染风险 |
| P2-4 | RAG/生成与 demo 壳混装 | `chapter_generation`/`tender_retrieval`/`ragflow_client` 仍在 demo 包；`create_app` 检索接线需再核 | 边界不清，难做开关与降级 |
| P2-5 | 看板/状态文档滞后 | `PROJECT_STATUS` 头信息仍偏 10-13 叙事；关键词统计不可靠 | 进度失真 |
| P2-6 | 交付文档爆炸但结构未还 | 大量 `docs/delivery`/`docs/testing` 10-21/10-22 签收 | 文档债掩盖结构债 |

### P3 — 工程与质量体系

| ID | 问题 | 证据 | 影响 |
|---|---|---|---|
| P3-1 | 前端测试目录双份 | `frontend/web/tests`（28）与 `tests/frontend`（26）高度重叠 | 跑哪套不清楚，易漏 |
| P3-2 | 前端脚本偏少 | `package.json` 仅 `dev/build/preview/e2e`，无 `test`/`lint` 脚本 | 本地门禁弱 |
| P3-3 | CI 仅 offline-check | `.github/workflows/offline-check.yml` | 脏树 push 后需全绿验证 |
| P3-4 | styles 单文件膨胀 | `styles.css` ≈39KB | 主题/页面样式难维护 |
| P3-5 | 字典码表未前端收口 | 状态/角色字符串散落 | 与 v1.9 对齐成本高 |
| P3-6 | 组件级测试弱 | 多 `.mjs` AST/编排测试，少真实组件交互 | 重构时回归信心不足 |

### 逻辑/产品闭环上还要盯的点（整改时验收）

1. **章节编辑锁 / 可恢复任务 / SSE**：后端有 `/api/v1/jobs` 与 `job-progress-sse.ts`，需验证断线重连、同 `idempotency` 再入、取消路径。
2. **导出门禁**：`export-checks-core` 有检查未通过阻断；需与后端 blocker 规则一致。
3. **敏感项目本地模型**：`SECRET_KEY_UNAVAILABLE` / 敏感项目约束；需端到端用例。
4. **跨公司隔离**：后端有测试，前端公司切换/蒙版需对齐。
5. **知识库/写作档案等壳页**：仍有 Pending/禁用导航残留，产品上要标明「未交付」vs「已交付」。

---

## 2. 整改总路线（给 Antigravity 的执行顺序）

### 阶段 A — 冻结基线（0.5–1 天）【用户正在做 push】

**目标**：远程 = 本机可审状态。

1. 提交并推送全部相关改动（含 alembic 0005–0011、新模块、测试、delivery）。
2. 开/更新 PR（建议仍用 `feat/opencode-ICG` → `main`，或新建 `chore/lock-antigravity-snapshot`）。
3. 跑通本地：`pytest`（backend）、前端 build、offline-check 关键关键。
4. 更新 `docs/PROJECT_STATUS.md` 顶部维护日期与「当前 tip/分支」。
5. **冻结规则（写入 AGENTS.md 或 CONTRIBUTING）**：
   - 禁止再向 `icg_demo/` 根目录平铺新文件（新能力必须进子包）。
   - 禁止再向 `frontend/web/src/` 根目录新增页面文件（必须进域目录）。
   - 新接口只加 `/api/v1`；`/api/demo` 只读兼容，不再扩展。

**验收**：远程 tip 含迁移与测试；CI 绿或已知失败有清单。

---

### 阶段 B — 前端无行为物理分层（1–2 天）

**目标**：目录可读，行为 0 变化。

建议目录：

```text
frontend/web/src/
  app/           # App.tsx 编排、lazy-routes、route 表、providers
  shell/         # AppShell、Breadcrumb、RouteGuard、Can
  project/       # ProjectPages、ProjectList、ProjectHeader、settings
  editor/        # EditorPage、conflict、recovery、cite、selection
  library/       # LibraryPages、metadata、tags
  admin/         # AuditLog、CompanyManage、SLA
  status/        # StatusViews、JobProgress、SSE
  shared/        # api.ts、types、styles 拆分入口、hooks
```

**做法**：
1. 只搬家 + 改 import，不改逻辑。
2. 同步移动 `frontend/web/tests` 对应用例路径。
3. 合并/删除与 `tests/frontend` 的重复（保留一套为权威，建议 `frontend/web/tests` + CI 指向它，或反过来，二选一）。
4. `package.json` 增加 `"test": "node --test ..."` 或现有 runner 脚本。

**验收**：`pnpm --dir frontend/web build` 通过；既有 `.mjs` 测试全绿；页面点击路径与搬家前一致（抽查工作台/编辑台/资料库）。

---

### 阶段 C — 拆前端巨石（2–3 天）

优先级：
1. `App.tsx` → 路由表 + SessionProvider + 布局出口（目标 <250 行）。
2. `EditorPage.tsx` → 视图 / 数据钩子 / Diff&AI 面板。
3. `ProjectPages.tsx` → 按 tab 拆文件（overview/tender/…）。
4. `styles.css` → 按域拆 CSS 或 CSS modules（可第二波）。

**验收**：单文件原则上 <400 行（特例需注释说明）；核心 e2e 或手工冒烟通过。

---

### 阶段 D — 后端分包与去 demo 化（3–5 天）

**目标包结构（示例，可微调名）**：

```text
backend/bid-core/icg/   # 或保留 icg_demo 作兼容 re-export 一层
  api/          # routes：session, projects, chapters, jobs, workflow…
  domain/       # 纯领域服务
  infra/        # mysql repo、ragflow_client、openai_model
  app/          # create_app、中间件、错误处理
```

**拆 `database.py` 优先切片**：
1. `mysql_gate` / 连接与 `ICG_*` 环境
2. `repositories/projects.py`、`chapters.py`、`jobs.py`、`library.py`、`model_config.py`…
3. 内存实现单独 `infra/memory_repository.py`（仅测试用）

**拆 `workflow.py`**：编排入口 vs 各步骤服务（outline / generate / export）。

**API 收敛**：
1. 新代码只挂 `/api/v1`。
2. `/api/demo/*` 标记 deprecated，文档写清下线版本。
3. 错误体统一 `{code,message,details,traceId}`；删除或网关层兼容旧 `error/request_id`。

**验收**：import 路径更新后全量 backend 测试绿；OpenAPI 由代码生成并提交（见阶段 E）；默认配置在 CI/`ICG_REQUIRE_MYSQL=1` 下不允许静默 Memory。

---

### 阶段 E — 契约、身份、字典收口（2–3 天）

1. **OpenAPI**：用 `export_openapi.py`（或现有脚本）从运行中 app 生成；禁止手工维护 900KB 巨文件；拆分或按 tag 分组若工具支持。
2. **会话退演示**：
   - 前端去掉强制 `synthetic-demo` / `legacy-demo-compat`（或仅 `VITE_DEMO=1` 开启）。
   - 正式路径走 `/api/v1/session` + 真实账号。
3. **八角色对齐**：前端 `Can`/路由守卫消费与后端同一角色码表（从字典 v1.9 生成 `roles.ts`/`codes.ts`）。
4. **字典驱动**：状态码、章节类型、错误码尽量单源（生成或共享 JSON）。

**验收**：演示模式开关可关；关闭后无合成账号也能完成「登录→项目→编辑→任务进度」；角色拒权有统一提示。

---

### 阶段 F — 产品闭环加固（持续，并行于 D/E 后）

按优先级做「真路径」验收用例（不要只测 Memory）：

1. MySQL 必开：`ICG_DATABASE_URL` + alembic upgrade head
2. 章节锁冲突 / 续租 / 释放
3. 可恢复任务 202 + SSE + 刷新恢复
4. RAGFlow 零命中 / 降级 / skipped 语义
5. 导出前检查阻断
6. 敏感字段蒙版与 reveal 审计

每条补 1 个后端测试 + 1 条前端或 e2e 断言。

---

## 3. Antigravity 工单包（可直接复制执行）

### WP-1 基线锁定
- **做**：确认 push 完整；PR 描述列出迁移与模块清单；修 CI 红。
- **不做**：重构。
- **验收**：远程可 clone 后 `alembic upgrade head` + 测试可跑。

### WP-2 前端目录搬家
- **做**：阶段 B 目录；更新所有 import；统一测试目录。
- **不做**：改 UI 文案/交互。
- **验收**：build + 原测试绿；git diff 以「rename」为主。

### WP-3 拆 App/Editor/ProjectPages
- **做**：阶段 C。
- **验收**：行数达标；关键路径冒烟。

### WP-4 拆 database.py / workflow.py
- **做**：阶段 D 切片；保持对外 API 不变。
- **验收**：backend 测试绿；文件行数显著下降（database 目标先 <600 行/文件）。

### WP-5 API/错误体收敛
- **做**：废弃 demo 扩展；统一错误体；更新前端 api 客户端只认 v1。
- **验收**：契约测试；旧路径仅兼容层。

### WP-6 去演示身份 + 八角色前端收口
- **做**：阶段 E。
- **验收**：关 demo 开关后主路径可用；权限矩阵与 `test_eight_roles_access` 对齐。

### WP-7 OpenAPI 生成化 + 测试脚本
- **做**：生成管道；`package.json` 补 test；去掉重复测试树。
- **验收**：CI 校验「生成结果与提交一致」或直接 CI 内生成。

---

## 4. 明确不要做的事（避免越改越偏）

1. 不要在分层完成前继续堆大功能到 `src/` 根或 `icg_demo/` 根。
2. 不要同时大改 UI 视觉与目录搬家。
3. 不要删 Memory 实现太早——先把它标成测试专用，再在生产配置禁止。
4. 不要 force-push 共享分支。
5. 不要引入未批准新栈（状态库/UI 库等需先拍板）。

---

## 5. 建议的 Definition of Done（整轮结构债）

- [ ] 远程 tip 含完整迁移与测试，CI 绿
- [ ] 前端按域分目录；`src` 根不再堆页面
- [ ] `database.py`/`workflow.py`/`App.tsx`/`EditorPage.tsx` 不再巨石
- [ ] 默认文档写明：生产必须 MySQL；demo API 弃用时间表
- [ ] 前端可关闭演示会话；角色码与字典一致
- [ ] OpenAPI 可生成；测试目录只保留一套
- [ ] PROJECT_STATUS / TASK_BOARD 与 tip 同步

---

## 6. 给用户的拍板项（需要的话再定）

1. 包重命名：`icg_demo` → `icg` 是否本轮做（兼容层多久）？
2. 是否引入 `react-router`（还是只抽路由表模块）？
3. 生产是否 **强制** `ICG_REQUIRE_MYSQL=1`（推荐是）？
4. `/api/demo` 下线窗口（例如下下个迭代）？

---

*本文由成长项目经理基于本机审查编写，供 Antigravity 按 WP 顺序执行；执行中以实际代码为准，完成每 WP 后回传 diff 摘要与测试证据。*
