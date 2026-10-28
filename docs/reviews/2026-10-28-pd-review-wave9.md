# 2026-10-28 Wave 9 业务功能与核心技术交付产品视角对照验收报告（PD 对照）

- **文档登记**：D-827
- **审查日期**：2026-10-28（Asia/Shanghai）
- **审查人**：PD｜产品验收 subagent
- **目标卡片（共 4 张）**：
  1. `APP-M2-T027`（A-02 用户列表、新增与停用前转交安全表单）
  2. `INT-USER-TRANSFER-RBAC-GLUE`（用户管理与账号停用资产交接端到端契约联调）
  3. `BE-USER-MANAGEMENT-TRANSFER`（用户管理与账号停用前业务资产强制交接服务）
  4. `AI-CHAPTER-AUTO-VALIDATION-GATE`（章节生成产物合规性自动即时质检门禁）
- **审查基准**：
  - PRD MVP v1.8（§2.3 多租户与 8 大标准 RBAC 角色体系、§5.7.8 章节生成即时合规门禁与大纲批量生成流水线闭环、§5.10 合规检查中心与整本导出门禁、§5.10.1 用户账号管理与状态流转、§5.10.2 密码强度安全策略与 Q28 定案、§5.11 依据追溯与防幻觉、§6.4 涉密项目本地模型策略、§6.9 界面布局与交互流、§8 物理租户强隔离）
  - 原型与交接约束 §6.2 M1-P10-F2（“停用前未转交不能停用”核心业务红线）
  - 核心交付与代码说明文档：
    - `docs/delivery/APP-M2-T027.md` & `docs/code/APP-M2-T027.md`（D-818, D-819）
    - `docs/delivery/INT-USER-TRANSFER-RBAC-GLUE.md` & `docs/code/INT-USER-TRANSFER-RBAC-GLUE.md`（D-820, D-821）
    - `docs/delivery/BE-USER-MANAGEMENT-TRANSFER.md` & `docs/code/BE-USER-MANAGEMENT-TRANSFER.md`（D-822, D-823）
    - `docs/delivery/AI-CHAPTER-AUTO-VALIDATION-GATE.md` & `docs/code/AI-CHAPTER-AUTO-VALIDATION-GATE.md`（D-824, D-825）
    - `docs/testing/2026-10-28-wave-9-batch-qa-signoff.md`（D-826，QA 独立终验签署 PASS 报告）

---

## 一、产品视角核心核验点深度核查

### 1. A-02 用户列表、新增与停用前转交安全表单（APP-M2-T027）
- **PRD 与规范对照**：PRD §2.3、§5.10.1、§5.10.2；交接约束 M1-P10-F2（“停用前未转交不能停用”）；平台基线安全红线：“密码策略只能调严不能调宽”；8 大 RBAC 角色权限感知与只读安全保护；主 Agent 第 5 条金标准：拒绝空壳冒充交付（真实落地 A-02 业务界面并挂载于 `GlobalPagesContent.tsx` 的 `admin.rules` Tab）。
- **核验结果**：
  - **真实业务页面落地与 Layout First**：
    - 在 `GlobalPagesContent.tsx` 中正式挂载 `UsersPage.tsx` 与纯逻辑领域层 `user-management-core.ts`，首屏异步分包体积受控（29.50 kB）；
    - 采用顶栏指标统计卡片（总用户数、在职数、停用数、当前密码策略、当前角色权限 Tag）+ 紧凑筛选工具栏（账号/姓名检索、8 角色筛选、状态筛选、企业切换）+ 用户 Table + 侧边抽屉，杜绝说明书式冗余文案堆砌；
  - **M1-P10-F2 停用前业务资产强制交接门禁**：
    - 在用户列表中根据 `hasActiveAssets` 智能分流操作：
      - 对持有未完结资产（担任在投项目负责人、分册主编、编写人或持有资料）的用户，直接停用按钮触发阻断，必须引导拉起「停用前业务资产强制交接」抽屉；
      - 抽屉内详细列出该用户待交接的项目、章节与资料明细；
      - 强制要求下拉指定同公司在职接收人，并录入不少于 5 个字的交接理由，资产全额转移合并并生成审计记录后方允许停用；
      - 对 0 资产用户提供 Popconfirm 二次确认弹窗，确认后直接停用；
  - **Q28 密码安全策略“只能调严不能调宽”前端闭环**：
    - 新增用户表单即时动态核验密码强度（大写、小写、数字、符号 4 类命中数及长度是否满足公司生效策略）；
    - 独立“账号安全设置”抽屉支持管理员调高密码策略（如提高长度至 12 位、要求 4 类全含），一旦低于平台基线（8 位 / 3 类 / 5 次重试）即时拦截并标红警告；
  - **8 大标准 RBAC 角色权限感知**：
    - 仅平台超级管理员与公司管理员具备新增、停用、资产转交与修改策略权限；业务角色（`project_lead`, `bid_writer`, `data_admin`, `auditor`, `viewer`）进入时操作按钮全局禁用并呈现友好只读警示条；
  - **质量证据**：专属单测 `user-management-page.test.mjs` 8 项全绿，全量前端单测 445 项全绿，TypeScript 静态类型检查 0 error，Vite 生产构建顺利通过。
- **判定**：**通过**。

### 2. 用户管理与账号停用资产交接端到端契约联调（INT-USER-TRANSFER-RBAC-GLUE）
- **PRD 与规范对照**：PRD §5.10.1、§5.10.2、§6.9、§8；RFC 7807 统一错误响应规范；冻结错误码 HTTP 409 `USER_TRANSFER_REQUIRED` 与 HTTP 422 `PASSWORD_WEAK`；关演示模式（`VITE_DEMO=0`）端到端主链路打通；机密凭据严格物理脱敏。
- **核验结果**：
  - **RESTful API 契约胶水打通**：
    - 打通 `/api/v1/users`（列表/新增）、`/api/v1/users/{user_id}`（详情/修改）、`/api/v1/users/{user_id}/status`（状态停用/平滑交接）及 `/api/v1/users/{user_id}/transfer`（独立资产批量划转），前端 API 客户端 `user-management-api.ts` 封装完整；
  - **密码凭据绝对物理脱敏**：
    - 用户查询接口（GET 列表/详情）在后端领域层统一经由 `account_to_user_model` 过滤，响应体中彻底剔除 `password_hash` 与 `salt`，无论是超管还是企管调阅均绝不外泄；
  - **弱密码严格拦截（HTTP 422 PASSWORD_WEAK）**：
    - 新增用户密码不足 8 位或字符类别不足 3 类时，统一拦截并抛出 RFC 7807 规范体：`code: PASSWORD_WEAK`、`details.field: password`；
  - **未交接资产停用强拦截（HTTP 409 USER_TRANSFER_REQUIRED）**：
    - 对在投未完结项目的负责人直接发起停用，系统前置校验拦截并返回 HTTP 409 `USER_TRANSFER_REQUIRED`，并在 details 中返回 `untransferred_projects` 与 `untransferred_chapters` 清单；
  - **平滑交接原子事务与会话销毁**：
    - 传入有效同企业接收人（`successor_user_id`）后，在单一事务中原子转移 `assembly_owner_id`、`owners`、`members`、`created_by` 与 `assignee_id`，释放编辑锁，留存 `handoffs` 审计记录，并作废被停用用户全部活跃会话；
  - **多租户防嗅探与 RBAC 隔离**：
    - 跨企业访问用户返回 **HTTP 404 `NOT_FOUND`**，同企业普通成员发起写操作拦截 **HTTP 403 `FORBIDDEN`**；
  - **质量证据**：专属联调测试 `test_user_transfer_rbac_glue.py` 6 项全绿，前端单测 445 项全绿，OpenAPI 契约零漂移（100% consistent）。
- **判定**：**通过**。

### 3. 用户管理与账号停用前业务资产强制交接服务（BE-USER-MANAGEMENT-TRANSFER）
- **PRD 与规范对照**：PRD §2.3、§5.10.1、§5.10.2；DDD 上下文分包规范（严格置于 `icg.api` 与 `icg.domain`，杜绝巨石平铺）；密码加盐哈希（PBKDF2-HMAC-SHA256）；系统超级管理员 `admin` 保护门禁；已归档项目豁免逻辑。
- **核验结果**：
  - **DDD 架构分包与微服务落地**：
    - 在 `backend/bid-core/icg/domain/user_management.py` 落地 `UserManagementService`，并在 `icg/api/users.py` 注册 `/api/v1/users` 路由，完全符合新逻辑进 `icg/` 上下文子包的架构红线；
  - **加盐哈希与密码强度策略实现**：
    - 采用 PBKDF2-HMAC-SHA256 100,000 轮哈希加密存储；严格落地 Q28 密码强度（422 `PASSWORD_WEAK`）；
  - **M1-P10-F2 停用前资产交接门禁算法**：
    - `_find_untransferred_assets` 深度扫描未归档项目中的项目总装负责人（`assembly_owner_id`）、分册主编（`owners`）、编写人、章节编写人（`assignee_id`）以及章节编辑持有锁（`chapter.lock`）；
    - 若项目已归档（`is_archived=True`），则诚实判定为历史归档资产，不阻断人员正常停用，符合工程实务；
    - 若项目处于在投进行中且未指定接交人，严格抛出 **HTTP 409 `USER_TRANSFER_REQUIRED`**；
  - **合法接交人校验与原子交接算法**：
    - `_execute_asset_transfer` 强校验接交人必须存在、同企业租户、非本人、未停用，并在仓储事务中原子过户资产与释放锁；
  - **超管 admin 保护门禁**：
    - 对超级管理员 `admin` 账号发起停用直接拦截 **HTTP 403 `FORBIDDEN`**，防止系统管理死锁；
  - **质量证据**：专属单测 `test_user_management_transfer.py` 7 项全绿，错误码与联合回归 24 项全绿，OpenAPI 契约零漂移。
- **判定**：**通过**。

### 4. 章节生成产物合规性自动即时质检门禁（AI-CHAPTER-AUTO-VALIDATION-GATE）
- **PRD 与规范对照**：PRD MVP v1.8 §5.7.8《章节生成即时合规门禁》、§5.10《合规检查中心与导出门禁》、§5.11《依据追溯与防幻觉》、§6.4《涉密项目本地模型策略》；主 Agent 第 2 条金标准（防编造追溯底线与涉密本地模型门禁）；主 Agent 第 4 条金标准（诚实记录阻断门禁）。
- **核验结果**：
  - **闭环「生成即质检」（Validation on Generation）**：
    - 单章节生成（`start_chapter_generation`）、批量多章节生成（`batch_generate_chapters`）与大纲批量生成流水线（`schedule_batch_pipeline`）在产出候选正文后，无需人工单独点击，自动即时触发多维度合规质量核验，结果直接注入 `candidate` 与 `demo_job` 状态；
  - **四重核心即时质检正则引擎全覆盖**：
    1. **R34 占位符与“待补/待完善”残留排查（阻断 blocker）**：自动排查未替换的草稿标记（`【待定】`、`【待补】`、`待补`、`【待完善】`、`待完善`、`【待确认】`、`待确认`、`【占位】`、`占位符`、`TODO`、`TBD`、`FIXME`、`XXXX`、`${...}` 及非合法变量 `{{...}}`），并排查 AI 对话客套语句残留（“希望能帮到您”、“作为AI语言模型”等），检出即标定阻断；
    2. **R37 / R28 负偏离与无法满足排查（阻断 blocker）**：自动检测正文中负偏离违规关键字（“不满足”、“负偏离”、“无法提供”、“存在差距”、“无法满足”、“未能达到”等），检出即标定阻断，防范 AI 自主表述偏离引发实质性废标；
    3. **R24 签字盖章槽位合规排查（阻断 blocker）**：对法定承诺与证明章节（投标函、法定代表人身份证明、授权委托书、签署页等）排查未盖章标记（“未盖公章”、“未签字”等）或缺少标准公章与签字槽位（`【公章】`、`【法定代表人签字】`），检出即标定阻断；
    4. **CITATION_AUTH 证据真实性白名单防编造核验（阻断 blocker）**：提取行内引用标记 `[证:eid]` 与 `[片:sid]`，依据白名单核验，发现未登记或虚构的假证据立即标定阻断缺陷（`FABRICATED_OR_INVALID_EVIDENCE_CITATION`），未匹配知识库切片标定合规警告（`UNVERIFIED_SNIPPET_CITATION`），坚守防幻觉防编造底线；
  - **0~100 质量健康度评分与 4 级评级（Health Rating）**：
    - 0 blocker + 0/1 warning -> 100/90 分，`excellent`；
    - 0 blocker + 2 warning -> 80 分，`good`；
    - 1 blocker -> 55 分，`warning`，`validation_passed: False`；
    - >=2 blocker -> <=35 分，`critical`，`validation_passed: False`；
  - **自适应整改建议（`remediation_suggestions`）**：
    - 依据命中缺陷代码动态生成占位符清除、负偏离改写、印章槽位补全与真实证据关联建议；
  - **流水线质量看板汇聚与安全隔离**：
    - `schedule_batch_pipeline` 汇聚全局质量看板（`total_validation_passed`、`total_validation_failed`、`total_detected_blockers`、`average_quality_score`）；
    - 涉密项目绑定云端模型拦截 **HTTP 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`**；跨租户项目拦截 **HTTP 404 `NOT_FOUND`**；系统只读角色拦截 **HTTP 403 `FORBIDDEN`**；
  - **质量证据**：专属单测 `test_ai_chapter_validation_gate.py` 12 项全绿，全量 AI 核心套件 85 项全绿，OpenAPI 契约零漂移。
- **判定**：**通过**。

---

## 二、产品对照矩阵表

| 卡ID | PRD 条款 / 规范对应项 | 验收判定（通过/部分通过/阻塞） | 产品依据与证据摘要 | 是否书面认可建议 PM 标 done |
| :--- | :--- | :---: | :--- | :---: |
| **APP-M2-T027** | PRD §2.3、§5.10.1、§5.10.2 / M1-P10-F2 (A-02 用户列表、新增与停用前转交安全表单) | **通过** | 真实落地 UsersPage 与纯逻辑层，挂载于 admin.rules 下 A-02 Tab；践行 Layout First；严格落地 M1-P10-F2 停用前资产强制交接门禁（未转交拦截、抽屉过户）；Q28 密码策略只能调严不能调宽；8 角色 RBAC 权限感知；专属单测 8 项全绿，前端 445 项全绿，构建通过。 | **书面认可**<br>建议 PM 标 done |
| **INT-USER-TRANSFER-RBAC-GLUE** | PRD §5.10.1、§5.10.2、§6.9、§8 / RFC 7807 (用户管理与账号停用资产交接契约联调) | **通过** | 打通 /api/v1/users* 全套 RESTful API；密码哈希绝对物理脱敏；弱密码拦截 422 `PASSWORD_WEAK`；未结清在投资产直接停用拦截 409 `USER_TRANSFER_REQUIRED`；附带接收人原子过户职责并作废会话；多租户 404 防嗅探与 RBAC 403 权限守卫；专属测试 6 项全绿，OpenAPI 零漂移。 | **书面认可**<br>建议 PM 标 done |
| **BE-USER-MANAGEMENT-TRANSFER** | PRD §2.3、§5.10.1、§5.10.2 / M1-P10-F2 (用户管理与账号停用前业务资产强制交接服务) | **通过** | 落地 /api/v1/users* 微服务与 /status 状态端点；PBKDF2 加盐哈希；Q28 密码强度（422 `PASSWORD_WEAK`）；M1-P10-F2 停用前资产交接门禁（409 `USER_TRANSFER_REQUIRED`）；归档项目豁免，在投项目原子转交；系统超管不可停用；专属单测 7 项全绿，回归套件 24 项全绿。 | **书面认可**<br>建议 PM 标 done |
| **AI-CHAPTER-AUTO-VALIDATION-GATE** | PRD §5.7.8、§5.10、§5.11、§6.4 (章节生成产物合规性自动即时质检门禁) | **通过** | 单章与流水线闭环「生成即质检」（Validation on Generation）；四重核心质检正则引擎：R34 占位符/AI客套语、R37 负偏离、R24 签字盖章、CITATION_AUTH 证据真实性白名单；0~100 动态健康分与 4 级评级；自适应整改建议；涉密本地模型 403 门禁与跨租户 404 隔离；专属单测 12 项全绿，全量 AI 核心套件 85 项全绿。 | **书面认可**<br>建议 PM 标 done |

---

## 三、产品视角综合结论与业务价值评估

1. **主路径业务连续性与项目防孤立护城河彻底筑牢**：
   - 伴随 `APP-M2-T027`、`INT-USER-TRANSFER-RBAC-GLUE` 与 `BE-USER-MANAGEMENT-TRANSFER` 的三端贯通，PRD §5.10.1 与交接约束 M1-P10-F2 核心红线“**停用前未转交不能停用**”在前端拦截抽屉、API 契约胶水与后端领域事务中形成了铁壁般的纵深防御；
   - 杜绝了项目经理或分册主编离职调岗导致在投项目无人负责、章节编辑锁死或审批断链的严重生产隐患，实现了在投业务资产向合法同企业在职人员的原子平滑移交，并完整留痕审计日志。
2. **AI 生成即质检（Validation on Generation）将合规风险消灭在源头**：
   - `AI-CHAPTER-AUTO-VALIDATION-GATE` 将原本只能在标书编制后期的被动检查，提前并闭环到了单章生成与大纲批量生成流水线的最前端；
   - 通过对 R34 占位符/AI客套话、R37 负偏离违规、R24 签字盖章槽位缺失与 CITATION_AUTH 虚构证据引用的毫秒级自动即时扫描，带病候选正文在生成完成的瞬间便被打上阻断标记并扣减健康分，极大降低了后续整本导出触发 400 `CHECK_BLOCKER_EXISTS` 废标阻断的概率，彻底贯彻了“防幻觉、不编造、依据可追溯”的核心产品底线。
3. **企业租户安全基线全面收口**：
   - A-02 用户管理真实业务页彻底消除了系统中的占位壳，严格贯彻 Q28 密码安全策略“只能调严不能调宽”；
   - 密码哈希物理脱敏、跨租户 404 NOT_FOUND 防嗅探、RBAC 8 角色权限感知与涉密项目强制本地模型策略全链路坚固。

**终验结论**：Wave 9 批次 4 张任务卡在主 Agent 业务验收五条金标准上全项达成，QA 独立终验签署已确认 PASS（D-826），**PD 正式出具书面认可，建议主 Agent 向人类 PM 推荐将该 4 张任务卡在看板中统一标为 `done`**。
