# QA 独立终验签署报告：Wave 6 核心能力与技术交付批次（共 4 卡）

**签署日期**：2026-10-27  
**验收负责人**：QA｜成长测试 QA subagent  
**验收目标**：对 Wave 6 批次进入 `in-review` 的 4 张任务卡（`APP-M2-T024`、`INT-DICT-CONFIG-RBAC-GLUE`、`BE-COMPLIANCE-RULES-P4`、`AI-OUTLINE-AUTO-TREE-BUILD`）进行独立全量测试复测、质量门禁审计、业务主路径核验与终验签署。  
**前置交付物查验**：已逐项核验 D-788 至 D-795 全部交付文档（delivery）与代码说明（code），内容与实测完全一致。

---

## 一、QA 终验签署汇总表

| 任务卡 ID | 任务名称 | 验收结论 | 核心通过证据 | 是否建议 PM done |
| :--- | :--- | :---: | :--- | :---: |
| **`APP-M2-T024`** | A-03 字典配置页 | **PASS** | 1. 落地 `DictConfigPage.tsx` 与 `dict-config-core.ts`，装配至全局规则导航 `admin.rules`；<br>2. 集中收录 6 大状态码表（26 项核心状态）及 9 项关键业务字段元数据；<br>3. 深度复用 `StatusTag` 组件渲染真实视觉预览并保障 WCAG AA 4.5:1 对比度标准；<br>4. 严格落实核心红线“已使用代码只能停用，不可直接硬删除”（在用与内置代码删除严格禁用并弹出告警拦截）；<br>5. 角色感知与权限保护：仅平台管理员与公司管理员具备启停控制权，非管理员角色呈现只读查看态；<br>6. 前端专属单测 6 项全绿，全量前端单测 **420 passed, 0 failed**，`tsc -b` **0 error**。 | **建议 PM 标 done** |
| **`INT-DICT-CONFIG-RBAC-GLUE`** | 字典配置与元数据停用/角色权限端到端契约联调 | **PASS** | 1. 打通 `/api/v1/metadata/dict/*` 5 大标准 RESTful 端点，建立类型化前端胶水客户端；<br>2. 统一冻结 409 错误码 `DICT_ITEM_IN_USE`（在用/内置防硬删除红线）与 `DICT_CODE_DUPLICATED`（同分类防重复），满足 RFC 7807；<br>3. 严格落实 8 角色 RBAC 权限隔离（非管理员写操作拦截 403 `FORBIDDEN`，未登录拦截 401 `UNAUTHENTICATED`）；<br>4. 公司多租户强隔离（Alpha 公司自定义字典项对 Beta 公司严格不可见）；<br>5. 专属联调单测 `test_dict_config_rbac_glue.py` **7 项全绿**，关联回归套件 34 项全绿，OpenAPI 契约零漂移。 | **建议 PM 标 done** |
| **`BE-COMPLIANCE-RULES-P4`** | PRD P4 核心合规规则引擎扩充与整本导出门禁联动 | **PASS** | 1. 规则引擎扩充：在 `compliance_rules.py` 完整落地 PRD MVP §5.8 第五批核心合规规则（R13/R16/R18/R24/R32），全系统目录与实现规则总数达到 26 项；<br>2. 业务阻断红线：项目经理执业资格/社保缺失（R13）、保证金不足/代缴（R16）、联合体协议缺失/未授权（R18）、法定表单未盖章/签名（R24）、投标有效期缩水/保留撤销权（R32）均严格判定为 blocker；<br>3. 导出门禁联动：在 `export_service.py` 保证上述 blocker 缺陷在正式递交版（submission）导出时严格触发 **400 `CHECK_BLOCKER_EXISTS`**，内部评审版允许导出但附合规警示；<br>4. 专属单测 `test_compliance_rules_p4.py` **6 项全绿**，关联核心回归套件 34 项全绿。 | **建议 PM 标 done** |
| **`AI-OUTLINE-AUTO-TREE-BUILD`** | 招标文件解析驱动的大纲树自动规划构建引擎 | **PASS** | 1. 基于招标文件解析需求矩阵（商务资质、总体架构、实施服务、安全合规、偏离表），自动构建两卷官方投标大纲层级结构（第一卷/第二卷 Level 0、第一章 Level 1、1.1 Level 2 叶子节、1.1.1 Level 3 子节），实现 100% 零未映射条款；<br>2. 叶子章节自动挂接真实条款 ID、评分分值、评分标准、星号条款（★）与废标红线，动态加权目标字数并合成结构化 `writing_points`；<br>3. 条款防编造防幻觉核验：虚构或未核实条款引用直接拦截 **422 `INVALID_REQUIREMENT_REFERENCE`**；<br>4. 租户强隔离（跨公司 404）与 RBAC 只读角色拦截（403 `FORBIDDEN`）；<br>5. 涉密项目本地模型硬门禁（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）；<br>6. preview 纯内存与单事务原子落盘双模式；<br>7. 专属单测 `test_ai_outline_auto_tree_build.py` **11 项全绿**，关联核心回归套件 34 项全绿。 | **建议 PM 标 done** |

---

## 二、自动化复测与质量门禁凭证清单

本 QA subagent 在签署前，在真实生产配置与关演示约束下独立运行了全套权威测试：

### 1. 前端专属单元测试套件
- **命令**：`node --test frontend/web/tests/unit/dict-config-page.test.mjs`
- **执行结果**：
  ```text
  ✔ 1. 字典项初始化加载：涵盖 6 大核心业务状态码表与字段元数据 (1.1294ms)
  ✔ 2. 角色感知与权限判定：区分平台管理员、公司管理员与只读人员 (0.2195ms)
  ✔ 3. 核心红线：“已使用代码只能停用，不可直接硬删除” (0.295ms)
  ✔ 4. 分类汇总与多维检索过滤逻辑验证 (0.3922ms)
  ✔ 5. DictConfigPage.tsx AST 静态契约与组件规范断言 (35.6631ms)
  ✔ 6. GlobalPagesContent.tsx 路由装配断言 (4.3821ms)
  ℹ tests 6, pass 6, fail 0 in 433ms
  ```
- **结论**：6 项全部通过。

### 2. 前端全量权威单元测试套件
- **命令**：`pnpm --dir frontend/web test`
- **执行结果**：
  ```text
  ℹ tests 420
  ℹ suites 0
  ℹ pass 420
  ℹ fail 0
  ℹ cancelled 0
  ℹ skipped 0
  ℹ todo 0
  ℹ duration_ms 4182.195
  ```
- **结论**：420 项全部通过，0 失败。

### 3. 前端 TypeScript 严格静态编译检查
- **命令**：`pnpm --dir frontend/web lint` (`tsc -b --noEmit`)
- **执行结果**：退出码 0，**0 error, 0 warning**。

### 4. 后端 Wave 6 专属专项测试
- **命令 1**：`python -m pytest tests/backend/test_dict_config_rbac_glue.py -v`
  - **结果**：`7 passed in 6.14s`（100% 绿灯）。
- **命令 2**：`python -m pytest tests/backend/test_compliance_rules_p4.py -v`
  - **结果**：`6 passed in 6.71s`（100% 绿灯）。
- **命令 3**：`python -m pytest tests/backend/test_ai_outline_auto_tree_build.py -v`
  - **结果**：`11 passed in 0.95s`（100% 绿灯）。

### 5. 后端核心回归测试套件
- **命令**：`python -m pytest tests/backend/test_dict_config_rbac_glue.py tests/backend/test_compliance_rules_p4.py tests/backend/test_ai_outline_auto_tree_build.py tests/backend/test_checks_export_blocker_gate.py tests/backend/test_workflow_orchestrator_modular.py -v`
- **执行结果**：
  ```text
  ============================= 34 passed in 18.84s =============================
  ```
- **结论**：34 项全部通过，0 失败。

### 6. OpenAPI 契约一致性校验
- **命令**：`python backend/bid-core/export_openapi.py --check`
- **执行结果**：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **结论**：契约零漂移通过。

### 7. 项目工程治理检查与单测
- **命令 1**：`node scripts/check-project-governance.cjs` -> **治理检查通过：588 份 Markdown、427 项任务、38 项 Issue，0 错误**。
- **命令 2**：`node --test tests/governance/*.test.cjs` -> **12 passed, 0 fail in 444ms**。

---

## 三、业务主路径与关键门禁深入核验

### 1. `APP-M2-T024` & `INT-DICT-CONFIG-RBAC-GLUE`：字典配置与防硬删除安全红线
- **数据完整性防线（防硬删除）**：
  - 前端：对在用（`isInUse: true`）或内置（`isBuiltin: true`）代码严格禁用删除操作，点击尝试触发强提示警告 Modal；
  - 后端：在 `DictConfigService.delete_item` 中前置判定，删除在用或内置代码严格拦截抛出 **409 `DICT_ITEM_IN_USE`**，防止破坏历史章节/标书快照的数据外键引用；
- **同分类代码防重**：新建重复 `item_code` 时抛出 **409 `DICT_CODE_DUPLICATED`**；
- **RBAC 角色权限矩阵**：
  - 平台管理员（`platform_admin`）与公司管理员（`company_admin`）具备新增、修改、启停用完整权限；
  - 普通编写人（`bid_writer`）、项目负责人（`project_lead`）、合规审计员（`auditor`）、只读观察员（`viewer`）等角色发起写操作一律拦截 **403 `FORBIDDEN`**；未认证请求拦截 **401 `UNAUTHENTICATED`**；
- **多租户数据隔离**：公司自定义代码项强绑定 `company_id`，Alpha 公司自定义项对 Beta 公司严格隔离不可见。

### 2. `BE-COMPLIANCE-RULES-P4`：核心合规规则引擎扩充与导出门禁联动
- **五大新规则判定（R13/R16/R18/R24/R32）**：
  - **R13 团队人员配置**：项目经理执业资格/连续在缴社保缺失（`TEAM_PROJECT_MANAGER_QUALIFICATION_MISSING`）或团队持证人数不达标（`TEAM_STAFFING_THRESHOLD_UNMET`）判定为 blocker；
  - **R16 投标保证金与保函**：保证金不足额或保函有效期未覆盖（`BID_SECURITY_DEPOSIT_NON_COMPLIANT`）判定为 blocker；
  - **R18 联合体投标协议**：联合体协议缺失、成员未授权或资质不符（`CONSORTIUM_AGREEMENT_INVALID`）判定为 blocker；
  - **R24 法定表单签名盖章**：法定代表人签字盖章缺失或空白表单（`MANDATORY_SEAL_SIGNATURE_MISSING`）判定为 blocker；
  - **R32 投标有效期**：有效期缩水或保留撤销权（`BID_VALIDITY_PERIOD_DEFICIENT`）判定为 blocker；
- **整本导出门禁强联动**：
  - 正式递交版导出（`target="submission"`）：存在任何上述 blocker 缺陷时，`export_service.py` 严格拦截并返回 **400 `CHECK_BLOCKER_EXISTS`**，绝对杜绝带病递交；
  - 内部评审版导出（`target="internal_review"`）：允许导出以便团队核验，但报告元数据显式标明 `has_blockers=True` 并输出合规警示清单。

### 3. `AI-OUTLINE-AUTO-TREE-BUILD`：大纲树自动规划构建引擎
- **多层级大纲规范生成与零未映射条款**：
  - 自动识别商务资质、总体架构、实施服务、安全合规、偏离表及应答表，构建第一卷（商务标）与第二卷（技术标）层级大纲树；
  - 矩阵中全部确认条款 100% 精确映射到叶子章节（`unmapped_requirements_count == 0`）；
- **评分要点与写作指引精准装配**：
  - 挂接真实条款 ID、分值、评分标准、星号条款（★）与废标红线，动态加权生成结构化 `writing_points` 与目标字数（800~3000 字）；
- **条款防编造防幻觉核验**：
  - 虚构或未在解析矩阵中登记的条款 ID 强拦截 **422 `INVALID_REQUIREMENT_REFERENCE`**；
- **租户隔离与涉密项目本地模型硬门禁**：
  - 跨租户项目请求拦截 **404 `NOT_FOUND`**；
  - 只读角色拦截 **403 `FORBIDDEN`**；
  - 涉密项目绑定外部云端模型强拦截 **403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`**，只放行私有化本地模型。

---

## 四、纪律遵从与流转建议

根据 `AGENTS.md` 签署纪律：
1. 本 QA subagent 保持客观中立，严禁自行在 `docs/TASK_BOARD.md` 标 `done`；
2. 上述 4 张任务卡在看板中均保持 `in-review` 状态；
3. 本 QA 签署报告作为官方复测凭据，**正式建议主 Agent 提请人类 PM（项目经理）复核并统一在任务看板中将上述 4 张任务卡标为 `done`**。
