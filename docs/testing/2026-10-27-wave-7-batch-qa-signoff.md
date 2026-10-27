# QA 独立终验签署报告：Wave 7 核心能力与技术交付批次（共 4 卡）

**签署日期**：2026-10-27  
**验收负责人**：QA｜成长测试 QA subagent  
**验收目标**：对 Wave 7 批次进入 `in-review` 的 4 张任务卡（`FE-LOGIN-ACCOUNT-PASSWORD`、`BE-AUTH-SUPER-ADMIN`、`INT-AUTH-LOGIN-RBAC-GLUE`、`AI-OUTLINE-SCORE-WEIGHT-CALC`）进行独立全量测试复测、质量门禁审计、业务主路径核验与终验签署。  
**前置交付物查验**：已逐项核验 D-798 至 D-805 全部交付文档（delivery）与代码说明（code），内容与实测完全一致。

---

## 一、QA 终验签署汇总表

| 任务卡 ID | 任务名称 | 验收结论 | 核心通过证据 | 是否建议 PM done |
| :--- | :--- | :---: | :--- | :---: |
| **`FE-LOGIN-ACCOUNT-PASSWORD`** | 生产环境正式账号密码登录表单与超级管理员接入 | **PASS** | 1. 全面切换为现代企业级账号密码卡片登录屏，彻底移除旧版 demo Tabs 与下拉框；<br>2. 落地轻量防空即时校验与密码可见性切换；<br>3. 接入内置超级管理员（`admin` / `X_2026`）快捷填入与登录认证；<br>4. 优先调用生产端点 `POST /api/v1/auth/login` 并支持离线安全凭据回退，保留令牌直登扩展槽（`onTokenLogin`）；<br>5. `App.tsx` 单文件行数实测 397 行，严格守卫 `<= 400` 行架构门禁；<br>6. 专属单测 6 项全绿，全量前端单测 **426 passed, 0 failed**，`tsc -b` **0 error**。 | **建议 PM 标 done** |
| **`BE-AUTH-SUPER-ADMIN`** | 正式账号密码认证机制与全系统超级管理员内置 | **PASS** | 1. 落地 PBKDF2-HMAC-SHA256（100,000次迭代 + 账号随机16字节盐）加盐哈希，`hmac.compare_digest` 常量时间核验防时序侧信道攻击；<br>2. 注册 `POST /api/v1/auth/login` 端点，强制注入 `Cache-Control: no-store, no-cache, must-revalidate` 与 `Pragma: no-cache` 防缓存安全响应头；<br>3. 密码错误或未知用户严格拦截 401 `INVALID_CREDENTIALS`，符合 RFC 7807；<br>4. 内置全权限超级管理员（`admin` / `X_2026`，`platform_admin`），穿透公司租户边界享有全 11 项路由写入权限、全套项目管理权限与双卷导出资格；<br>5. 生产模式（`ICG_ALLOW_DEMO_LOGIN=0`）下 demo 路径严格阻断（403），正式认证通畅；<br>6. 专属单测 `test_auth_super_admin.py` **8 项全绿**。 | **建议 PM 标 done** |
| **`INT-AUTH-LOGIN-RBAC-GLUE`** | 账号密码认证与超级管理员端到端契约联调 | **PASS** | 1. 非演示模式（`VITE_DEMO=0`）打通 `POST /api/v1/auth/login` 与 `GET /api/v1/session` 会话签发与加载闭环；<br>2. 凭据错误严格拦截 401 `INVALID_CREDENTIALS`，统一 RFC 7807 错误格式；<br>3. 超级管理员系统级四大能力端到端打通：全量长任务脱敏审计（`/jobs?masked=true`）、A-03 字典读写、26 项合规规则全目录调阅、跨公司审计权；<br>4. 企业正式账号密码登录与工作台加载兼容；<br>5. 专属联调单测 `test_auth_login_rbac_glue.py` **6 项全绿**，OpenAPI 契约零漂移。 | **建议 PM 标 done** |
| **`AI-OUTLINE-SCORE-WEIGHT-CALC`** | 大纲评分项分值权重加权与章节优先级智能排序引擎 | **PASS** | 1. 真实评分条款统计：自动计算章节累计分值 `total_score`、全标权重 `score_weight` 与分册权重 `volume_score_weight`，内建除零容错保护；<br>2. 星号条款（★，bonus=60）与一票否决废标红线（disqualified，bonus=100）加权，综合优先级得分 `priority_score` 精准分级；<br>3. 推荐多章节批量生成执行队列 `recommended_writing_order` 排序与行动指引输出；<br>4. 跨租户强隔离（404）、只读 RBAC 门禁（403）与涉密项目云端模型硬拦截（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）；<br>5. 专属单测 `test_ai_outline_score_weight.py` **8 项全绿**，大纲回归 25 项全绿，全量 AI 套件 64 项全绿。 | **建议 PM 标 done** |

---

## 二、自动化复测与质量门禁凭证清单

本 QA subagent 在签署前，在真实生产配置与关演示约束下独立运行了全套权威测试：

### 1. 前端专属单元测试套件
- **命令**：`node --test frontend/web/tests/unit/login-screen-form.test.mjs frontend/web/tests/unit/app-slim-and-platform-admin.test.mjs`
- **执行结果**：
  ```text
  ✔ FE-TECH-DEBT-02: App.tsx line count is strictly below 400 lines (1.8925ms)
  ✔ FE-TECH-DEBT-02: Extracted shell & app domain components exist and export properly (0.8274ms)
  ✔ APP-M2-T022: isPlatformAdminRole correctly identifies platform administrator (0.1681ms)
  ✔ APP-M2-T022: sanitizePlatformAdminTitle masks tender file names and project sensitive words (0.2321ms)
  ✔ APP-M2-T022: maskTaskForPlatformAdmin enforces security and ops-view masking invariants (0.6207ms)
  ✔ 1. 登录表单校验规则：即时轻量防空校验（validateLoginForm） (0.6406ms)
  ✔ 2. 超级管理员凭据（admin / X_2026）规范与识别 (0.1164ms)
  ✔ 3. 账号密码认证胶水函数（authenticateUser）网络交互与异常处理 (0.611ms)
  ✔ 4. 错误提示格式化（formatLoginErrorMessage） (0.1043ms)
  ✔ 5. LoginScreen.tsx AST 静态契约与 Layout First 规范断言 (14.288ms)
  ✔ 6. App.tsx 集成装配与单文件架构门禁（<= 400 行） (21.8183ms)
  ℹ tests 11, pass 11, fail 0 in 417ms
  ```
- **结论**：11 项全部通过，`App.tsx` 严格守卫 <= 400 行架构门禁。

### 2. 前端全量权威单元测试套件
- **命令**：`pnpm --dir frontend/web test`
- **执行结果**：
  ```text
  ℹ tests 426
  ℹ suites 0
  ℹ pass 426
  ℹ fail 0
  ℹ cancelled 0
  ℹ skipped 0
  ℹ todo 0
  ℹ duration_ms 3959.6553
  ```
- **结论**：426 项全部通过，0 失败。

### 3. 前端 TypeScript 严格静态编译检查
- **命令**：`pnpm --dir frontend/web lint` (`tsc -b --noEmit`)
- **执行结果**：退出码 0，**0 error, 0 warning**。

### 4. 后端 Wave 7 专属专项测试
- **命令**：`python -m pytest tests/backend/test_auth_super_admin.py tests/backend/test_auth_login_rbac_glue.py tests/backend/test_ai_outline_score_weight.py -v`
- **执行结果**：
  ```text
  tests/backend/test_auth_super_admin.py (8 passed)
  tests/backend/test_auth_login_rbac_glue.py (6 passed)
  tests/backend/test_ai_outline_score_weight.py (8 passed)
  ============================= 22 passed in 10.42s =============================
  ```
- **结论**：22 项全部通过，0 失败。

### 5. 后端核心回归测试套件
- **命令**：`python -m pytest tests/backend/test_auth_super_admin.py tests/backend/test_auth_login_rbac_glue.py tests/backend/test_ai_outline_score_weight.py tests/backend/test_application_session.py tests/backend/test_ai_outline_auto_tree_build.py -v`
- **执行结果**：
  ```text
  ============================= 67 passed in 37.50s =============================
  ```
- **结论**：67 项全部通过，0 失败。

### 6. OpenAPI 契约一致性校验
- **命令**：`python backend/bid-core/export_openapi.py --check`
- **执行结果**：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **结论**：契约零漂移通过。

### 7. 项目工程治理检查与单测
- **命令 1**：`node scripts/check-project-governance.cjs` -> **治理检查通过：598 份 Markdown、431 项任务、38 项 Issue，0 错误**。
- **命令 2**：`node --test tests/governance/*.test.cjs` -> **12 passed, 0 fail in 524ms**。

---

## 三、业务主路径与关键门禁深入核验

### 1. `FE-LOGIN-ACCOUNT-PASSWORD` & `BE-AUTH-SUPER-ADMIN` & `INT-AUTH-LOGIN-RBAC-GLUE`：生产认证体系与超级管理员
- **告别 demo 模式与用户最新指示践行**：
  - 前端：全面移除体验账号下拉框与 demo Tabs，以现代企业级「账号 + 密码」卡片呈现，支持用户名密码即时防空校验与密码显示隐藏切换；
  - 超级管理员快捷通道：内置 `admin` / `X_2026` 快捷填入，优先打通真实 `POST /api/v1/auth/login` 端点并支持离线安全凭据签发；
- **加密与抗侧信道安全**：
  - PBKDF2-HMAC-SHA256 100,000 轮加盐哈希，配合账号独立 16 字节高熵盐；
  - 比对采用 `hmac.compare_digest` 常量时间判定，彻底抵御时序侧信道攻击；
  - 响应对象严格剥离 `password_hash` 与 `salt`，杜绝凭据信息外泄；
- **防缓存安全响应头**：
  - `POST /api/v1/auth/login` 端点响应强制注入 `Cache-Control: no-store, no-cache, must-revalidate` 与 `Pragma: no-cache`；
- **错误统一拦截**：
  - 密码错误或未知用户统一返回 HTTP 401 `INVALID_CREDENTIALS`，严格符合 RFC 7807 统一错误体；
- **超级管理员全权限穿透**：
  - 超管会话（`primary_role="platform_admin"`，`company_id="system"`）突破项目与租户所属限制；
  - 具备全 11 条路由可写权限、全量长任务脱敏审计（`/jobs?masked=true`）、A-03 字典配置读写、合规规则全目录（26 项）调阅以及双卷导出资格；
- **关演示模式可用性**：
  - 在生产模式（`ICG_ALLOW_DEMO_LOGIN=0`）下，旧 `/api/demo/login` 端点严格被阻断（403 `FORBIDDEN`），正式账号密码认证通畅可用。

### 2. `AI-OUTLINE-SCORE-WEIGHT-CALC`：大纲评分项分值权重加权与章节优先级引擎
- **评分条款真实加权**：
  - 严格溯源自真实招标文件条款的 `score` 字段，精确计算 `total_score`、全标权重比 `score_weight`（0.0 ~ 1.0）及分册权重比 `volume_score_weight`（0.0 ~ 1.0）；
  - 内建除零容错保护，当无明确分值时平稳回退 0.0；
- **星号条款与废标红线综合优先级**：
  - 一票否决废标红线（`disqualified`）：`priority="critical"`，加权附加分 `bonus=100.0`；
  - ★关键必保条款（`asterisk`）：`priority="critical"`，加权附加分 `bonus=60.0`；
  - 高分值章节（>= 15分）：`priority="high"`，`bonus=30.0`；中分值章节（>= 5分）：`priority="medium"`，`bonus=15.0`；
- **推荐批量写作执行队列**：
  - 输出 `recommended_writing_order`，按优先级分、总分与章节号多级排序，指导分节独立批量写作；
- **内网物理隔离与涉密项目硬门禁**：
  - 跨租户访问强拦截 404 `NOT_FOUND`；
  - 只读角色强拦截 403 `FORBIDDEN`；
  - 涉密项目（`sensitive=True`）使用云端外部模型强门禁拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，坚决保证评分数据与大纲权重不外泄至公网。

---

## 四、纪律遵从与流转建议

根据 `AGENTS.md` 签署纪律：
1. 本 QA subagent 保持客观中立，严禁自行在 `docs/TASK_BOARD.md` 标 `done`；
2. 上述 4 张任务卡在看板中均保持 `in-review` 状态；
3. 本 QA 签署报告作为官方复测凭据，**正式建议主 Agent 提请人类 PM（项目经理）复核并统一在任务看板中将上述 4 张任务卡标为 `done`**。
