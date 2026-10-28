# QA 独立终验签署报告：Wave 10 核心能力与技术交付批次（共 4 卡）

**签署日期**：2026-10-28  
**验收负责人**：QA｜成长测试 QA subagent  
**验收目标**：对 Wave 10 批次进入 `in-review` 的 4 张任务卡（`APP-M2-T028`、`INT-USER-SECURITY-OPS-GLUE`、`BE-USER-SECURITY-OPS`、`AI-OUTLINE-AUTO-REMEDIATION`）进行独立全量测试复测、质量门禁审计、业务主路径核验与终验签署。  
**前置交付物查验**：已逐项核验 D-828 至 D-835 全部交付文档（delivery）与代码说明（code），内容与实测完全一致。

---

## 一、QA 终验签署汇总表

| 任务卡 ID | 任务名称 | 验收结论 | 核心通过证据 | 是否建议 PM done |
| :--- | :--- | :---: | :--- | :---: |
| **`APP-M2-T028`** | A-02 用户角色分配、锁定/解锁与重置密码表单 | **PASS** | 1. 落地 `UsersPage.tsx` 与 `user-management-core.ts` 角色调配、密码重置与锁定/解锁能力；<br>2. 严格执行角色安全防线：超管 `admin` 角色受保护不可篡改，企管越权提权（platform_admin/group_admin）被拦截，项目负责人降级活动项目预警；<br>3. 落实交接约束 M1-P10-F3 核心红线：“`user_status = locked` 显示解锁”，解锁一键恢复活跃（`active`），重置密码自动解除锁定；<br>4. 密码重置强制 Q28 安全策略并提供全 4 类字符随机强密码生成器；<br>5. 专属单测 8 项全绿，全量前端单测 **455 passed, 0 failed**，`tsc -b` **0 error**。 | **建议 PM 标 done** |
| **`INT-USER-SECURITY-OPS-GLUE`** | 用户角色分配、重置密码与账号解锁端到端契约联调 | **PASS** | 1. 打通 `/api/v1/users/{user_id}/reset-password`、`/unlock` 与 `/role` 端到端契约胶水层；<br>2. 弱密码拦截 422 `PASSWORD_WEAK`；重置成功后历史 Token 即刻失效（401 `UNAUTHENTICATED`）；<br>3. 连续 5 次输错密码自动置锁并返回 423 `ACCOUNT_LOCKED`；管理员一键解锁（status 恢复 active，is_locked 置 False，失败计数清零）；<br>4. 8 角色切换与超管保护（403 `SUPER_ADMIN_PROTECTED`）、自降权保护（403 `CANNOT_DEMOTE_SELF`）；<br>5. 多租户防嗅探隔离（404 `NOT_FOUND`）与 RBAC 403 权限隔离；专属单测 6 项全绿，全量用户测试 19 项全绿，OpenAPI 契约零漂移。 | **建议 PM 标 done** |
| **`BE-USER-SECURITY-OPS`** | 用户角色调配、密码强制重置与登录失败锁定/解锁服务 | **PASS** | 1. 落地 reset-password、unlock 与 role 微服务端点，新增与重置采用加盐哈希更新；<br>2. 强校验 Q28 密码安全策略（不足拦截 422 `PASSWORD_WEAK`）并即时作废该用户全部活跃会话；<br>3. 连续登录失败达到阈值自动置锁并返回 423 `ACCOUNT_LOCKED`，管理员调用解锁端点一键解除锁定；<br>4. 8 角色调整落地超管 `admin` 保护（403 `SUPER_ADMIN_PROTECTED`）与管理员防自降权保护（403 `CANNOT_DEMOTE_SELF`）；<br>5. 多租户 404 `NOT_FOUND` 防嗅探隔离与 RBAC 403 权限守卫；专属单测 3 项全绿，联合回归套件 40 项全绿。 | **建议 PM 标 done** |
| **`AI-OUTLINE-AUTO-REMEDIATION`** | 章节合规质检缺陷自动整改建议与局部智能重写引擎 | **PASS** | 1. 落地 `diagnose_paragraph_defects`、`synthesize_remediation_plan` 与 `remediate_chapter_candidate`；<br>2. 四重缺陷精准诊断：R34 占位符/未替换变量/AI客套语、R37/R28 负偏离、R24 签字盖章槽位缺失与 CITATION_AUTH 虚构证据引用；<br>3. 局部定位最小改动原则：100% 原样保留所有质检合格的合规段落，仅对违规段落发起定向重写与清洗；<br>4. 多轮自适应收敛迭代（最多 3 轮），直至阻断项完全清零且健康分达到 excellent（>=90分）；<br>5. 单章生成与大纲批量生成流水线闭环集成（`auto_remediate=True`）及全局质量看板汇总；<br>6. 涉密项目本地模型硬门禁（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）与多租户/RBAC 隔离（404/403）；专属单测 12 项全绿，全量 AI 核心套件 97 项全绿。 | **建议 PM 标 done** |

---

## 二、自动化复测与质量门禁凭证清单

本 QA subagent 在签署前，在真实生产配置与关演示约束下独立运行了全套权威测试：

### 1. 前端专属单元测试套件
- **命令**：`node --test frontend/web/tests/unit/user-role-reset-unlock.test.mjs`
- **执行结果**：
  ```text
  ✔ 1. 角色分配安全校验：超管保护、企业管理员越权提权拦截与同角色校验 (0.9004ms)
  ✔ 2. 降级项目负责人时的进行中项目强预警提示 (0.173ms)
  ✔ 3. 角色分配执行不可变更新 (0.1492ms)
  ✔ 4. 重置密码合规校验：符合企业密码策略与确认一致性 (0.3246ms)
  ✔ 5. 随机合规密码生成器：必含全部4类字符且满足长度策略 (0.3381ms)
  ✔ 6. 重置密码执行与锁定账号自动恢复活跃（M1-P10-F3） (0.1507ms)
  ✔ 7. 账号手动锁定与解锁逻辑（M1-P10-F3：锁定状态显示解锁按钮） (0.4261ms)
  ✔ 8. UsersPage.tsx AST 静态契约断言：角色表单、重置密码、锁定/解锁交互元素 (0.6849ms)
  ℹ tests 8, pass 8, fail 0 in 172ms
  ```
- **结论**：8 项全部通过。

### 2. 前端全量权威单元测试套件
- **命令**：`pnpm --dir frontend/web test`
- **执行结果**：
  ```text
  ℹ tests 455
  ℹ suites 0
  ℹ pass 455
  ℹ fail 0
  ℹ cancelled 0
  ℹ skipped 0
  ℹ todo 0
  ℹ duration_ms 5613.9578
  ```
- **结论**：455 项全部通过，0 失败。

### 3. 前端 TypeScript 严格静态编译检查
- **命令**：`pnpm --dir frontend/web lint` (`tsc -b --noEmit`)
- **执行结果**：退出码 0，**0 error, 0 warning**。

### 4. 后端 Wave 10 专属专项测试
- **命令 1**：`python -m pytest tests/backend/test_user_security_ops_glue.py -v`
  - **结果**：`6 passed in 6.05s`（100% 绿灯）。
- **命令 2**：`python -m pytest tests/backend/test_user_security_ops.py -v`
  - **结果**：`3 passed in 5.82s`（100% 绿灯）。
- **命令 3**：`python -m pytest tests/backend/test_ai_outline_auto_remediation.py -v`
  - **结果**：`12 passed in 2.11s`（100% 绿灯）。
- **小计**：**21 passed in 12.56s**。

### 5. 后端核心回归测试套件
- **命令**：`python -m pytest tests/backend/test_user_security_ops_glue.py tests/backend/test_user_security_ops.py tests/backend/test_ai_outline_auto_remediation.py tests/backend/test_ai_chapter_validation_gate.py tests/backend/test_user_management_transfer.py -v`
- **执行结果**：
  ```text
  ============================= 40 passed in 22.49s =============================
  ```
- **结论**：40 项全部通过，0 失败。

### 6. OpenAPI 契约一致性校验
- **命令**：`python backend/bid-core/export_openapi.py --check`
- **执行结果**：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **结论**：契约零漂移通过。

### 7. 项目工程治理检查与单测
- **命令 1**：`node scripts/check-project-governance.cjs` -> **治理检查通过：627 份 Markdown、440 项任务、38 项 Issue，0 错误**。
- **命令 2**：`node --test tests/governance/*.test.cjs` -> **12 passed, 0 fail in 419ms**。

---

## 三、业务主路径与关键门禁深入核验

### 1. `APP-M2-T028` & `INT-USER-SECURITY-OPS-GLUE` & `BE-USER-SECURITY-OPS`：用户安全运维
- **密码强制重置与会话即时作废**：
  - 强校验 Q28 密码安全策略（长度>=8位，字符种类>=3类），不足拦截 **422 `PASSWORD_WEAK`**；
  - 重置成功后采用 PBKDF2 加盐哈希安全更新密码，并**原子作废该用户所有活跃 Token**，旧会话即刻触发 **401 `UNAUTHENTICATED`**，杜绝被盗会话持续驻留；
- **连续输错自动置锁与一键解锁（M1-P10-F3）**：
  - 连续输错 5 次密码自动触发锁定，状态置为 `locked`，后续登录即便使用正确密码也严格拦截 **423 `ACCOUNT_LOCKED`**；
  - 前端表格中锁定账号直观渲染警示黄色 Badge 并呈现「解锁」按钮；
  - 管理员调用 `/unlock` 端点一键恢复为 `active` 并清零失败计数；重置密码亦自动联动解除锁定；
- **角色安全防线与自降权防护**：
  - 超管 `admin` 角色受强制保护，修改拦截 **403 `SUPER_ADMIN_PROTECTED`**；
  - 管理员账号禁止自我降权，拦截 **403 `CANNOT_DEMOTE_SELF`**，防止出现租户管理员空缺死锁；
  - 项目总负责人角色降级时触发活动项目资产预警，防止项目责任断链；
  - 多租户防嗅探隔离：跨企业用户运维请求一律严格返回 **404 `NOT_FOUND`**。

### 2. `AI-OUTLINE-AUTO-REMEDIATION`：章节合规质检缺陷自动整改建议与局部智能重写引擎
- **缺陷精准诊断与建议指引合成**：
  - 逐段精准扫描并诊断 R34 占位符/未替换变量/AI客套语、R37/R28 负偏离声明、R24 签字盖章槽位缺失与 CITATION_AUTH 虚构证据引用四重缺陷；
  - 智能合成明确指令、规则清单与确定性正向承诺替换预览；
- **局部定位最小改动原则**：
  - 严格仅对检出违规的段落发起定向重写与清洗；
  - **100% 原样保留所有质检合格的合规段落**，彻底杜绝盲目全篇重写导致的内容损失与 Token 浪费；
  - 重组后各段落序号（`[P1]`、`[P2]`...）全局连续且与小标题严格对齐；
- **多轮自适应收敛闭环**：
  - 支持最多 3 轮迭代自适应重写与复验，直至 blocker 清零且健康分达到 `excellent`（>=90 分）；
  - 记录细粒度整改前后分值对比（`pre_remediation_score` vs `post_remediation_score`）；
- **全链路集成与安全红线**：
  - 单章生成与批量流水线闭环集成（`auto_remediate=True`），质量看板统计 `total_remediated_chapters`；
  - 涉密项目（`sensitive=True`）使用云端外部模型强门禁拦截 **403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`**，只放行内网私有化本地模型；
  - 跨租户访问强拦截 **404 `NOT_FOUND`**。

---

## 四、纪律遵从与流转建议

根据 `AGENTS.md` 签署纪律：
1. 本 QA subagent 保持客观中立，严禁自行在 `docs/TASK_BOARD.md` 标 `done`；
2. 上述 4 张任务卡在看板中均保持 `in-review` 状态；
3. 本 QA 签署报告作为官方复测凭据，**正式建议主 Agent 提请人类 PM（项目经理）复核并统一在任务看板中将上述 4 张任务卡标为 `done`**。
