# QA 独立终验签署报告：Wave 9 核心能力与技术交付批次（共 4 卡）

**签署日期**：2026-10-28  
**验收负责人**：QA｜成长测试 QA subagent  
**验收目标**：对 Wave 9 批次进入 `in-review` 的 4 张任务卡（`APP-M2-T027`、`INT-USER-TRANSFER-RBAC-GLUE`、`BE-USER-MANAGEMENT-TRANSFER`、`AI-CHAPTER-AUTO-VALIDATION-GATE`）进行独立全量测试复测、质量门禁审计、业务主路径核验与终验签署。  
**前置交付物查验**：已逐项核验 D-818 至 D-825 全部交付文档（delivery）与代码说明（code），内容与实测完全一致。

---

## 一、QA 终验签署汇总表

| 任务卡 ID | 任务名称 | 验收结论 | 核心通过证据 | 是否建议 PM done |
| :--- | :--- | :---: | :--- | :---: |
| **`APP-M2-T027`** | A-02 用户列表、新增与停用前转交安全表单 | **PASS** | 1. 落地 `UsersPage.tsx` 与 `user-management-core.ts`，多维度呈现 8 大角色用户列表与负责资产标签；<br>2. 严格对齐 PRD §5.10.2 / Q28 密码安全策略（长度>=8位、字符种类>=3类），公司设置“只能调严不能调宽”；<br>3. 落实交接约束 M1-P10-F2 核心红线：“停用前未转交不能停用”，持有在投项目/分册/编写资产用户停用前强制转交抽屉拦截；<br>4. 8 角色 RBAC 细粒度权限控制与多租户数据隔离；<br>5. 专属单测 8 项全绿，全量前端单测 **445 passed, 0 failed**，`tsc -b` **0 error**。 | **建议 PM 标 done** |
| **`INT-USER-TRANSFER-RBAC-GLUE`** | 用户管理与账号停用资产交接端到端契约联调 | **PASS** | 1. 打通 `/api/v1/users*` 全套 RESTful API 契约与前端 API 胶水层；<br>2. 密码哈希（`password_hash`）与加盐（`salt`）完全物理脱敏无泄露；<br>3. 弱密码拦截 422 `PASSWORD_WEAK`；未结清在投资产直接停用严格拦截 409 `USER_TRANSFER_REQUIRED`；<br>4. 传入有效接收人后单一事务原子完成项目总装负责人、分册主编、章节编写人移交、编辑锁安全释放、会话即时作废与账号停用；<br>5. 专属单测 6 项全绿，回归套件 39 项全绿，OpenAPI 契约零漂移。 | **建议 PM 标 done** |
| **`BE-USER-MANAGEMENT-TRANSFER`** | 用户管理与账号停用前业务资产强制交接服务 | **PASS** | 1. 落地用户 CRUD 与 `/status` 状态交接微服务，新增用户 PBKDF2-HMAC-SHA256 加盐哈希安全存储；<br>2. 严格落地 Q28 密码强度（422 `PASSWORD_WEAK`）与 M1-P10-F2 停用前资产交接门禁（409 `USER_TRANSFER_REQUIRED`）；<br>3. 归档项目不阻断停用，在投项目原子转交；<br>4. 多租户 404 `NOT_FOUND` 防嗅探隔离，RBAC 403 权限控制与保护系统超管不可停用；<br>5. 专属单测 7 项全绿，联合核心回归套件 39 项全绿。 | **建议 PM 标 done** |
| **`AI-CHAPTER-AUTO-VALIDATION-GATE`** | 章节生成产物合规性自动即时质检门禁 | **PASS** | 1. 落地 `validate_chapter_candidate`，单章生成与大纲批量生成流水线闭环「生成即质检」（Validation on Generation）；<br>2. 四重即时质检正则引擎：R34 占位符与 AI 对话客套语残留（`PLACEHOLDER_RESIDUAL` / `AI_CONVERSATION_RESIDUAL`）、R37/R28 负偏离（`NEGATIVE_DEVIATION_DETECTED`）、R24 签字盖章槽位缺失（`MANDATORY_SEAL_SIGNATURE_MISSING`）、CITATION_AUTH 证据真实性白名单核验（`FABRICATED_OR_INVALID_EVIDENCE_CITATION`）；<br>3. 0~100 动态健康分与 4 级评级（excellent/good/warning/critical）；<br>4. 涉密项目本地模型硬门禁（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）与多租户隔离（404 `NOT_FOUND`）；<br>5. 专属单测 12 项全绿，全量 AI 核心套件 85 项全绿。 | **建议 PM 标 done** |

---

## 二、自动化复测与质量门禁凭证清单

本 QA subagent 在签署前，在真实生产配置与关演示约束下独立运行了全套权威测试：

### 1. 前端专属单元测试套件
- **命令**：`node --test frontend/web/tests/unit/user-management-page.test.mjs`
- **执行结果**：
  ```text
  ✔ 1. 用户初始数据集与业务资产统计完整性 (0.8339ms)
  ✔ 2. “公司设置只能调严不能调宽”密码策略合规校验 (0.8247ms)
  ✔ 3. 密码强度与字符类别动态核验算法 (0.2911ms)
  ✔ 4. 新增用户表单校验与查重防线 (0.2713ms)
  ✔ 5. 停用前业务资产强制交接合规红线校验（M1-P10-F2） (0.22ms)
  ✔ 6. 执行资产交接与状态停用领域逻辑断言 (6.8904ms)
  ✔ 7. 8 角色 RBAC 细粒度权限感知与多租户隔离过滤 (0.3178ms)
  ✔ 8. UsersPage.tsx 与 GlobalPagesContent.tsx AST 静态契约断言 (1.3464ms)
  ℹ tests 8, pass 8, fail 0 in 264ms
  ```
- **结论**：8 项全部通过。

### 2. 前端全量权威单元测试套件
- **命令**：`pnpm --dir frontend/web test`
- **执行结果**：
  ```text
  ℹ tests 445
  ℹ suites 0
  ℹ pass 445
  ℹ fail 0
  ℹ cancelled 0
  ℹ skipped 0
  ℹ todo 0
  ℹ duration_ms 4608.3865
  ```
- **结论**：445 项全部通过，0 失败。

### 3. 前端 TypeScript 严格静态编译检查
- **命令**：`pnpm --dir frontend/web lint` (`tsc -b --noEmit`)
- **执行结果**：退出码 0，**0 error, 0 warning**。

### 4. 后端 Wave 9 专属专项测试
- **命令 1**：`python -m pytest tests/backend/test_user_transfer_rbac_glue.py -v`
  - **结果**：`6 passed in 6.12s`（100% 绿灯）。
- **命令 2**：`python -m pytest tests/backend/test_user_management_transfer.py -v`
  - **结果**：`7 passed in 7.42s`（100% 绿灯）。
- **命令 3**：`python -m pytest tests/backend/test_ai_chapter_validation_gate.py -v`
  - **结果**：`12 passed in 7.96s`（100% 绿灯）。
- **小计**：**25 passed in 21.50s**。

### 5. 后端核心回归测试套件
- **命令**：`python -m pytest tests/backend/test_user_transfer_rbac_glue.py tests/backend/test_user_management_transfer.py tests/backend/test_ai_chapter_validation_gate.py tests/backend/test_auth_super_admin.py tests/backend/test_compliance_rules_p5.py -v`
- **执行结果**：
  ```text
  ============================= 39 passed in 41.27s =============================
  ```
- **结论**：39 项全部通过，0 失败。

### 6. OpenAPI 契约一致性校验
- **命令**：`python backend/bid-core/export_openapi.py --check`
- **执行结果**：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **结论**：契约零漂移通过。

### 7. 项目工程治理检查与单测
- **命令 1**：`node scripts/check-project-governance.cjs` -> **治理检查通过：617 份 Markdown、437 项任务、38 项 Issue，0 错误**。
- **命令 2**：`node --test tests/governance/*.test.cjs` -> **12 passed, 0 fail in 445ms**。

---

## 三、业务主路径与关键门禁深入核验

### 1. `APP-M2-T027` & `INT-USER-TRANSFER-RBAC-GLUE` & `BE-USER-MANAGEMENT-TRANSFER`：用户管理与资产交接
- **交接约束 M1-P10-F2 停用前业务资产强制交接门禁**：
  - 前端：当用户在未归档项目中担任负责人或编写人时，直接停用按钮触发阻断，引导展开资产强制交接抽屉；
  - 后端：在 `UserManagementService.disable_user` 中前置判定，名下持有未结清资产且未指定有效接交人时，严格拦截并抛出 **HTTP 409 `USER_TRANSFER_REQUIRED`**；
  - 转移事务：指定合法同企业接收人后，在单一事务中原子完成项目总装负责人（`assembly_owner_id`）、分册主编（`owners`）、章节编写人（`assignee_id`）字段变更，安全释放持有编辑锁，留存 `handoffs` 审计记录，并作废待停用用户的全部活跃会话；
  - 归档豁免：已归档项目（`is_archived=True`）不计入活跃交接阻断；
- **PRD §5.10.2 / Q28 密码安全策略与物理脱敏**：
  - 新增用户密码必须满足最少 8 位且包含大写、小写、数字、特殊符号中的至少 3 类，不足直接拦截抛出 **422 `PASSWORD_WEAK`**；
  - 存储采用 PBKDF2-HMAC-SHA256 100,000 轮加盐哈希，接口返回数据对 `password_hash` 与 `salt` 进行物理脱敏过滤，绝不外泄；
- **多租户强隔离与 RBAC 权限守卫**：
  - 跨租户用户访问严格返回 **404 `NOT_FOUND`**，防止攻击者探测企业租户用户存在性；
  - 同企业非管理员修改拦截 **403 `FORBIDDEN`**；系统超级管理员 `admin` 保护免受停用。

### 2. `AI-CHAPTER-AUTO-VALIDATION-GATE`：章节生成产物合规性自动即时质检门禁
- **生成即质检（Validation on Generation）闭环**：
  - 单章生成（`start_chapter_generation`）、批量多章节生成（`batch_generate_chapters`）与流水线调度（`schedule_batch_pipeline`）生成正文后自动触发；
- **四重合规规则即时扫描**：
  - **R34 占位符排查**：草稿占位标记（`【待定】`、`【待补】`、`TODO`、未替换模板变量 `${...}`）与 AI 对话客套语句残留（“希望能帮到您”等）均标定阻断缺陷（`PLACEHOLDER_RESIDUAL` / `AI_CONVERSATION_RESIDUAL`）；
  - **R37/R28 负偏离排查**：排查“不满足”、“无法提供”、“负偏离”等违规用语，标定阻断缺陷（`NEGATIVE_DEVIATION_DETECTED`）；
  - **R24 法定签字盖章槽位排查**：识别法定承诺章节中显式未盖章标记或缺少标准印章槽位，标定阻断缺陷（`MANDATORY_SEAL_SIGNATURE_MISSING`）；
  - **CITATION_AUTH 证据白名单真实性核验**：提取正文中 `[证:eid]` 与 `[片:sid]` 标记，非白名单虚构证据标定阻断（`FABRICATED_OR_INVALID_EVIDENCE_CITATION`），防范模型幻觉；
- **质量健康分与评级体系**：
  - 0 blocker + 0/1 warning -> 100/90 分 `excellent`；0 blocker + 2 warning -> 80 分 `good`；1 blocker -> 55 分 `warning`；>=2 blocker -> <=35 分 `critical`；
- **涉密与多租户隔离**：
  - 跨租户访问强拦截 **404 `NOT_FOUND`**；
  - 涉密项目使用云端模型强门禁拦截 **403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`**。

---

## 四、纪律遵从与流转建议

根据 `AGENTS.md` 签署纪律：
1. 本 QA subagent 保持客观中立，严禁自行在 `docs/TASK_BOARD.md` 标 `done`；
2. 上述 4 张任务卡在看板中均保持 `in-review` 状态；
3. 本 QA 签署报告作为官方复测凭据，**正式建议主 Agent 提请人类 PM（项目经理）复核并统一在任务看板中将上述 4 张任务卡标为 `done`**。
