# QA 独立终验签署报告：Wave 8 核心能力与技术交付批次（共 4 卡）

**签署日期**：2026-10-27  
**验收负责人**：QA｜成长测试 QA subagent  
**验收目标**：对 Wave 8 批次进入 `in-review` 的 4 张任务卡（`APP-M2-T025`、`INT-COMPANY-SETTINGS-RBAC-GLUE`、`BE-COMPLIANCE-RULES-P5`、`AI-OUTLINE-BATCH-GENERATION-PIPELINE`）进行独立全量测试复测、质量门禁审计、业务主路径核验与终验签署。  
**前置交付物查验**：已逐项核验 D-808 至 D-815 全部交付文档（delivery）与代码说明（code），以及 D-817（PD 产品验收报告），内容与实测完全一致。

---

## 一、QA 终验签署汇总表

| 任务卡 ID | 任务名称 | 验收结论 | 核心通过证据 | 是否建议 PM done |
| :--- | :--- | :---: | :--- | :---: |
| **`APP-M2-T025`** | 扩展字段与公司设置键表单框架 | **PASS** | 1. 落地 `CompanySettingsPage.tsx` 与 `company-settings-core.ts`，涵盖 5 大设置维度，消除 `PendingPage` 占位壳；<br>2. 严格执行“只能调严不能调宽”安全红线（密码长度>=8、种类>=3，整本导出门禁强制启用）；<br>3. 落实 9.11 排他编辑锁三元联动数学约束（`自动保存 <= 心跳`、`心跳*10 <= 租约超时`、`租约超时 >= 5分钟`）；<br>4. 8 角色 RBAC 细粒度权限控制，业务角色严格只读提示；<br>5. 专属单测 7 项全绿，全量前端单测 **435 passed, 0 failed**，`tsc -b` **0 error**。 | **建议 PM 标 done** |
| **`INT-COMPANY-SETTINGS-RBAC-GLUE`** | 企业设置与安全策略/租户隔离端到端契约联调 | **PASS** | 1. 非演示模式（`VITE_DEMO=0`）打通 `GET / PATCH /api/v1/companies/{company_id}/settings` 端到端契约；<br>2. 超管穿透管理任意企业、企管管理本企业；同企业非管理员修改拦截 403 `FORBIDDEN`；<br>3. 多租户强隔离防嗅探，跨企业访问统一严格拦截返回 404 `NOT_FOUND`；<br>4. 严格校验“只能调严不能调宽”与 9.11 三元约束，越界统一拦截抛出 422 `SETTING_VALUE_OUT_OF_BOUNDS`，符合 RFC 7807；<br>5. 专属单测 6 项全绿，关联回归套件 30 项全绿，OpenAPI 契约零漂移。 | **建议 PM 标 done** |
| **`BE-COMPLIANCE-RULES-P5`** | PRD P5 终批核心合规规则引擎扩充与整本导出门禁全覆盖闭环 | **PASS** | 1. 落地终批 5 大规则（R17 利害关系回避、R19 强制绿色节能认证、R26 知识产权免责承诺、R27 本地化售后网点、R28 关键技术规格负偏离），全系统合规规则目录达 **31 项** 全覆盖闭环；<br>2. 导出门禁联动：正式递交版（submission）导出遇 blocker 缺陷严格拦截 400 `CHECK_BLOCKER_EXISTS`，内部评审版允许导出但附合规警示；<br>3. 分册未定稿状态下导出诚实守卫 409 `RULES_INCOMPLETE`，绝不绕行假装可递交；<br>4. 专属单测 6 项全绿，全量合规规则回归 30 项全绿。 | **建议 PM 标 done** |
| **`AI-OUTLINE-BATCH-GENERATION-PIPELINE`** | 基于优先级推荐队列的大纲多章节批量生成流水线调度引擎 | **PASS** | 1. 落地 `schedule_batch_pipeline`，按 `(-priority_score, -total_score, section_number)` 倒序自适应排序，废标红线与星标必保优先 Stage 1 批次执行；<br>2. 并发门限 1~5 严格受控切片，有效保护本地模型显存（防 VRAM OOM）；<br>3. 坚决落实 PRD §5.7.8 核心红线：未确认方案章节（`PLAN_NOT_CONFIRMED`）隔离跳过，绝对不阻塞后续已确认章节调度与执行；<br>4. 聚合全局 Token 消耗仪表盘与耗时指标，单事务原子落盘；<br>5. 涉密项目本地模型硬门禁（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）与多租户隔离（404 `NOT_FOUND`）；<br>6. 专属单测 9 项全绿，全量 AI 核心回归 21 项全绿。 | **建议 PM 标 done** |

---

## 二、自动化复测与质量门禁凭证清单

本 QA subagent 在签署前，在真实生产配置与关演示约束下独立运行了全套权威测试：

### 1. 前端专属单元测试套件
- **命令**：`node --test frontend/web/tests/unit/company-settings-form.test.mjs`
- **执行结果**：
  ```text
  ✔ 1. 公司设置初始数据集与平台基线定义（buildInitialCompanySettings） (0.7997ms)
  ✔ 2. 核心安全红线：“公司设置只能调严不能调宽”合规校验 (0.4747ms)
  ✔ 3. 规范 9.11 编辑锁心跳三元联动数学约束校验 (0.1874ms)
  ✔ 4. 废标阻断硬门禁与平台参数上下限越界拦截 (0.3039ms)
  ✔ 5. 8 大角色精细化权限感知与只读安全判定（checkCompanySettingsPermission） (0.2734ms)
  ✔ 6. CompanySettingsPage.tsx AST 静态契约与组件规范断言 (36.0081ms)
  ✔ 7. GlobalPagesContent.tsx 路由集成与拒绝空壳断言 (3.2299ms)
  ℹ tests 7, pass 7, fail 0 in 430ms
  ```
- **结论**：7 项全部通过。

### 2. 前端全量权威单元测试套件
- **命令**：`pnpm --dir frontend/web test`
- **执行结果**：
  ```text
  ℹ tests 435
  ℹ suites 0
  ℹ pass 435
  ℹ fail 0
  ℹ cancelled 0
  ℹ skipped 0
  ℹ todo 0
  ℹ duration_ms 4803.4932
  ```
- **结论**：435 项全部通过，0 失败。

### 3. 前端 TypeScript 严格静态编译检查
- **命令**：`pnpm --dir frontend/web lint` (`tsc -b --noEmit`)
- **执行结果**：退出码 0，**0 error, 0 warning**。

### 4. 后端 Wave 8 专属专项测试
- **命令 1**：`python -m pytest tests/backend/test_company_settings_rbac_glue.py -v`
  - **结果**：`6 passed in 6.22s`（100% 绿灯）。
- **命令 2**：`python -m pytest tests/backend/test_compliance_rules_p5.py -v`
  - **结果**：`6 passed in 5.81s`（100% 绿灯）。
- **命令 3**：`python -m pytest tests/backend/test_ai_outline_batch_pipeline.py -v`
  - **结果**：`9 passed in 3.12s`（100% 绿灯）。
- **小计**：**21 passed in 15.15s**。

### 5. 后端核心回归测试套件
- **命令**：`python -m pytest tests/backend/test_company_settings_rbac_glue.py tests/backend/test_compliance_rules_p5.py tests/backend/test_ai_outline_batch_pipeline.py tests/backend/test_compliance_rules.py tests/backend/test_checks_export_blocker_gate.py -v`
- **执行结果**：
  ```text
  ============================= 30 passed in 20.82s =============================
  ```
- **结论**：30 项全部通过，0 失败。

### 6. OpenAPI 契约一致性校验
- **命令**：`python backend/bid-core/export_openapi.py --check`
- **执行结果**：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **结论**：契约零漂移通过。

### 7. 项目工程治理检查与单测
- **命令 1**：`node scripts/check-project-governance.cjs` -> **治理检查通过：608 份 Markdown、434 项任务、38 项 Issue，0 错误**。
- **命令 2**：`node --test tests/governance/*.test.cjs` -> **12 passed, 0 fail in 501ms**。

---

## 三、业务主路径与关键门禁深入核验

### 1. `APP-M2-T025` & `INT-COMPANY-SETTINGS-RBAC-GLUE`：企业设置与安全策略/租户隔离
- **“只能调严不能调宽”安全基线**：
  - 密码最少长度只能 >= 8 位，字符种类只能 >= 3 类；
  - 连续登录失败锁定次数只能 <= 5 次；
  - 导出门禁强制启用项为平台全局红线，置灰锁定且不可关闭；
  - 越界统一拦截并抛出 **422 `SETTING_VALUE_OUT_OF_BOUNDS`**，返回 RFC 7807 统一错误体；
- **规范 9.11 编辑锁三元数学约束**：
  - 自动保存周期必须 <= 心跳续期间隔；
  - 心跳续期间隔 × 10 必须 <= 锁定超时总时长（秒）；
  - 锁定超时时间必须 >= 5 分钟（下限 6 分钟，上限 60 分钟）；
- **RBAC 角色权限矩阵与防嗅探多租户隔离**：
  - 超管跨企业全权限调阅与配置，企管管理本企业；
  - 同企业普通编写人与只读角色仅可只读调阅（用于界面交互与协同），修改拦截 **403 `FORBIDDEN`**；
  - 跨租户请求统一返回 **404 `NOT_FOUND`**，彻底杜绝攻击者利用 403 探测企业租户存在性。

### 2. `BE-COMPLIANCE-RULES-P5`：终批合规规则引擎扩充与导出门禁全覆盖闭环
- **31 项核心规则全覆盖闭环（P0~P5）**：
  - **R17 利害关系回避**：存在关联利害关系未回避判定为 `blocker`（`CONFLICT_OF_INTEREST_UNRESOLVED`）；
  - **R19 节能绿色认证**：强制品目缺少有效认证清单判定为 `blocker`（`MANDATORY_GREEN_CERT_MISSING`）；
  - **R26 知识产权免责承诺**：缺少自主知识产权声明与侵权兜底承诺判定为 `blocker`（`IP_INFRINGEMENT_INDEMNITY_MISSING`）；
  - **R27 本地化售后服务网点**：招标文件要求本地网点而无证明判定为 `blocker`（`LOCAL_SERVICE_BRANCH_MISSING`）；
  - **R28 关键技术规格实质性负偏离**：技术偏离表中关键指标存在负偏离判定为 `blocker`（`CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION`）；
- **整本导出门禁强联动**：
  - 正式递交版（submission）存在任一 blocker 缺陷时，严格返回 **400 `CHECK_BLOCKER_EXISTS`**，坚决杜绝带病递交；
  - 分册未定稿时，整本导出诚实拦截并返回 **409 `RULES_INCOMPLETE`**，绝不假装已可递交。

### 3. `AI-OUTLINE-BATCH-GENERATION-PIPELINE`：大纲多章节批量生成流水线调度引擎
- **优先级复合排序与批次切片**：
  - 依据 `(-priority_score, -total_score, section_number)` 倒序排序，保证废标红线与星标条款（`critical`）前置调度；
  - 受控于 `concurrency_limit`（默认 2，范围 1~5），按阶段批次（Stage 1/2...）切片推进，防本地模型显存崩溃（VRAM OOM）；
- **PRD §5.7.8 关键红线：未确认章节跳过绝不阻塞后续生成**：
  - 未确认方案章节（`PLAN_NOT_CONFIRMED`）自动隔离跳过并记入 `skipped_unconfirmed_chapters`，不阻断后续已确认章节独立生成，状态标定 `partial_completed`；
- **Token 预算与涉密模型硬门禁**：
  - 聚合流水线全局 Token 消耗仪表盘与耗时指标；
  - 涉密项目（`sensitive=True`）使用云端外部模型强门禁拦截 **403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`**，只放行内网私有化本地模型；
  - 跨租户调用拦截 **404 `NOT_FOUND`**。

---

## 四、纪律遵从与流转建议

根据 `AGENTS.md` 签署纪律：
1. 本 QA subagent 保持客观中立，严禁自行在 `docs/TASK_BOARD.md` 标 `done`；
2. 上述 4 张任务卡在看板中均保持 `in-review` 状态；
3. 本 QA 签署报告作为官方复测凭据，**正式建议主 Agent 提请人类 PM（项目经理）复核并统一在任务看板中将上述 4 张任务卡标为 `done`**。
