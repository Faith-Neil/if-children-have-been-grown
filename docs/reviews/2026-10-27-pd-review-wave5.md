# 2026-10-27 Wave 5 业务功能与核心技术交付产品视角对照验收报告（PD 对照）

- **文档登记**：D-787
- **审查日期**：2026-10-27（Asia/Shanghai）
- **审查人**：PD｜产品验收 subagent
- **目标卡片（共 4 张）**：
  1. `APP-M2-T023`（StatusTag 状态注册表（9.3 全部代码表））
  2. `INT-STATUS-TAG-METADATA-GLUE`（状态注册表与元数据接口端到端契约联调）
  3. `BE-TECH-DEBT-03`（workflow_orchestrator 巨石解耦与领域子编排服务细化）
  4. `AI-OUTLINE-GENERATE-EXPAND`（章节写作方案多段落结构化批量生成引擎）
- **审查基准**：
  - PRD MVP v1.8（§5.7.2 章节写作方案生成、§5.7.8 多段落结构化批量生成引擎、§5.10.3 状态展示体系与检查结果可视化、§5.11 依据追溯与防幻觉、§6.4 涉密本地模型策略、§6.9/设计规范 9.3 视觉与状态代码表、§8 多租户强隔离与 RBAC 8 角色体系）
  - 数据字典 v1.9（`kb-data-dictionary-v1.9.md`：`rule_level`、`compliance_issue`、`JobRecord`、`JobStatus`、`allowedActions`、`field_metadata`）
  - 核心交付与代码说明文档：
    - `docs/delivery/APP-M2-T023.md` & `docs/code/APP-M2-T023.md`（D-778, D-779）
    - `docs/delivery/INT-STATUS-TAG-METADATA-GLUE.md` & `docs/code/INT-STATUS-TAG-METADATA-GLUE.md`（D-780, D-781）
    - `docs/delivery/BE-TECH-DEBT-03.md` & `docs/code/BE-TECH-DEBT-03.md`（D-782, D-783）
    - `docs/delivery/AI-OUTLINE-GENERATE-EXPAND.md` & `docs/code/AI-OUTLINE-GENERATE-EXPAND.md`（D-784, D-785）

---

## 一、产品视角核心核验点深度核查

### 1. 全局状态代码表收口与 WCAG 对比度设计规范（APP-M2-T023）
- **PRD 与规范对照**：PRD §5.10.3、§6.9 与系统设计规范 9.3《全部代码表》；Layout First 克制化原则；WCAG AA 4.5:1 文本对比度标准；AI 紫色色彩隔离红线。
- **核验结果**：
  - **6 大业务域状态全面收口**：在 `frontend/web/src/shared/status-registry.ts` 纯逻辑注册表中统一收敛定义：
    1. `project`（5 项）：`draft`（筹备中）、`in_progress`（编写中）、`review`（审核中）、`completed`（已完成）、`archived`（已归档）；
    2. `chapter`（5 项）：`not_started`（未开始）、`generating`（生成中 - 唯一允许 AI 紫）、`draft`（草稿）、`reviewed`（已复核）、`approved`（已定稿）；
    3. `job`（5 项）：`queued`（排队中）、`running`（进行中）、`completed`（已完成）、`failed`（异常失败）、`cancelled`（已取消）；
    4. `check`（3 项）：`passed`（合规通过）、`warning`（合规提醒）、`blocker`（废标阻断）；
    5. `export`（4 项）：`idle`（待导出）、`processing`（排版中）、`completed`（已生成）、`failed`（导出失败）；
    6. `lock`（4 项）：`unlocked`（空闲可编辑）、`locked_self`（本人编辑中）、`locked_other`（他人占用）、`expired`（租约过期）；
  - **WCAG AA 4.5:1 文本对比度严格达标**：内置 `luminance` 与 `contrastRatio` 相对亮度对比度验证算法；实测 subtle、solid、outline 调色板在全状态下对比度范围为 **5.4:1 ～ 8.9:1**，远高于 4.5:1 门槛，根治了低对比度发虚不可读问题；
  - **AI 紫色强隔离红线**：除章节 AI 生成中（`chapter:generating`）赋予专属紫色（`#722ed1`）外，其余所有业务状态严禁使用紫色，色彩语义清晰纯粹；
  - **容错映射与未知降级**：支持大小写归一化、历史别名自动转换（`pending` -> `queued`, `hint` -> `warning`, `disqualification` -> `blocker` 等）；遇到非法或未知状态码自动降级为 neutral 灰色安全对象，系统永不崩溃；
  - **表现层高内聚封装（StatusTag.tsx）**：提供 `subtle`、`solid`、`outline` 三种视觉变体，`default`、`small` 两种尺寸，支持圆点徽标（`showBadge`）、自动 Ant Design 图标（`showIcon`）与悬浮提示（`tooltip`），并声明 `role="status"` 及完整无障碍元数据属性；
  - **质量证据**：专属单测 `status-tag.test.mjs` 6 项全绿，全量前端单测 414 项全绿，TypeScript 0 error，Vite 生产构建 1.40s 成功。
- **判定**：**通过**。

### 2. 状态代码表与元数据字典端到端契约联调（INT-STATUS-TAG-METADATA-GLUE）
- **PRD 与规范对照**：PRD §5.10.3、§6.9 与数据字典 v1.9 §4.16；8 大 RBAC 角色字段编辑权限自适应；RFC 7807 统一错误体与 OpenAPI 零漂移。
- **核验结果**：
  - **前后端业务状态枚举与代码表 100% 对齐**：后端 `/api/v1/metadata/fields/status`、`/api/v1/metadata/fields/statuses` 与领域专用接口（`/chapter`, `/job`, `/check`, `/export`, `/lock`）完整提供 6 大业务状态的规范选项（包含中文 label 与规范 code）；前端注册表扩展别名表（如 `opened`, `confirmed`, `queued`, `generating`, `expired`, `locked`, `taken_over`），主流程状态 100% 映射成功，杜绝未知英文裸显；
  - **全量字段元数据聚合端点**：实现 `GET /api/v1/metadata/fields/all`，一次性聚合 9 大分类字段元数据字典，方便前端冷启动；
  - **8 大标准 RBAC 角色字段编辑权限动态自适应（editable）**：
    - 在非演示模式（`VITE_DEMO=0`）及真实 JWT 会话下，后端依据 Principal 角色动态自适应计算字典的 `editable` 属性；
    - 系统只读角色（`viewer` 访客、`auditor` 审计员、`platform_admin` 平台运维、`group_admin` 集团管理）调阅元数据时，原本可编辑的业务字段（如 `project_name`）被强行封退为 `editable: false`，确保前端表单自动置灰或渲染为只读纯文本；
    - 写作者角色（`project_lead`, `bid_writer`, `company_admin`, `data_admin`）调阅时，忠实保留其原生编辑资质；
  - **统一错误响应与安全拦截**：未知分类严格返回 404 `NOT_FOUND`，未认证请求返回 401 `UNAUTHENTICATED`，均符合 RFC 7807 统一错误体标准；OpenAPI 契约零漂移（一致性 100%）；
  - **质量证据**：专属联调测试 `test_status_tag_metadata_glue.py` 4 项全绿，元数据套件 10 项全绿。
- **判定**：**通过**。

### 3. workflow_orchestrator 巨石解耦与领域子编排服务细化（BE-TECH-DEBT-03）
- **PRD 与架构规范对照**：`docs/architecture/repository-layout.md`（后端架构分包与 DDD 限界上下文规范）、`AGENTS.md`（核心服务单文件行数硬门禁 <= 350 行、平滑兼容准则）。
- **核验结果**：
  - **单文件行数治理严格达标**：`backend/bid-core/icg/domain/workflow_orchestrator.py` 从原 983 行巨石彻底解耦重构至 **330 行** 高内聚门面（严格低于 350 行治理红线，缩减率 66.4%）；
  - **5 大领域子编排器独立抽离且职责清晰**：
    1. `outline_orchestrator.py`（大纲子编排器）：负责大纲树构建（`build_outline_tree`）、章节编号规范化、大纲计划确认、章节增删改、大纲定稿就绪检查（`check_outline_finalization_readiness`）；
    2. `generation_orchestrator.py`（章节生成子编排器）：负责写作提示词预算组装（`assemble_writing_prompt_plan`，集成 `DynamicPromptContextManager`）、涉密项目本地模型硬门禁（`check_sensitive_model_gate`）、章节生成任务创建（`start_chapter_generation`）、候选结果归档与 AI 伴写；
    3. `check_orchestrator.py`（合规检查子编排器）：负责全量合规规则评估（`ComplianceRulesEngine.evaluate_all`）、阻断缺陷汇总（`aggregate_blockers`）、废标星号条款门禁（`CheckBlockerError`）、增量复检队列管理（`schedule_incremental_recheck`）；
    4. `tender_orchestrator.py`（标书解析与响应矩阵子编排器）：负责招标文件上传/预览/删除、文本提取、响应矩阵维护、事实冲突消解与解析确认；
    5. `library_orchestrator.py`（知识库与任务审计子编排器）：负责企业资料库查询与重新确认、ACL 权限鉴权与合作方协议校验、后台异步任务脱敏视图；
  - **既有业务与调用方零断裂兼容**：`outline_service.py`、`generation_service.py` 与 `export_service.py` 转化为薄兼容继承门面，所有既有类、方法签名与返回值 100% 保持向后兼容，业务主路径零回归；
  - **质量证据**：专属测试 `test_workflow_orchestrator_modular.py` 6 项全绿（包含单文件行数 <= 350 硬断言），核心关联套件 55 项全绿，OpenAPI 零漂移，工程治理检查全部通过。
- **判定**：**通过**。

### 4. 章节写作方案多段落结构化批量生成引擎（AI-OUTLINE-GENERATE-EXPAND）
- **PRD 与规范对照**：PRD §5.7.2（章节写作方案生成）、§5.7.8（多段落结构化批量生成引擎）、§5.11（依据追溯与防幻觉）、§6.4（涉密项目本地模型强制门禁）；PRD §5.7.8 关键红线：“未确认分册或未确认章节绝对不阻塞已确认章节独立生成”。
- **核验结果**：
  - **`[P1]`~`[Pn]` 多段落结构化精准解析（parse_structured_paragraphs）**：
    - 大模型生成正文被精准切分为带有编号、段落标签、小标题与评分要点绑定的结构化段落列表；
    - 每个段落包含 `id`、`paragraph_id`、`order`、`label`（`[P1]`）、`subheading`（Markdown 标题行）、`title`（清洗后的标题纯文本）、`text`（正文）、`content`（带标签格式）、`scoring_point`（对齐的评分要点）、`variables`（抽取的变量名列表）与 `char_length`；
    - 针对未显式输出 `[Pn]` 标签的模型文本，引擎自适应按段落顺序分配标签并与评分要点自动对齐；
  - **行内引用提取与白名单防幻觉核验（extract_paragraph_citations）**：
    - 精准提取段落正文中的 `[证:xxx]`（企业证据）与 `[片:xxx]`（知识库/招标文件切片）引用胶囊；
    - 严格对照 `allowed_evidence_ids` 与 `allowed_snippet_ids` 白名单核验，对于白名单外的虚构引用直接标记 `valid=False`（`unverified`），从算法层面彻底堵死模型幻觉编造伪证；
  - **结构化 Markdown 规范还原（format_structured_chapter_content）**：
    - 将结构化段落列表逆向还原为干净规范的 Markdown 章节正文，支持小标题层级规范聚合，避免冗余重复输出标题；
  - **单章生成成果丰富化**：同步执行模式下，候选产物字典自动丰富 `paragraphs`、`structured_content`、`scoring_subheadings`，为后续前端精细化段落渲染与编辑提供完备数据底座；
  - **跨章节独立批量生成与容错编排（batch_generate_chapters）**：
    - **严格落实 PRD §5.7.8 核心红线**：未确认分册或未确认方案的章节独立记入 `failed_chapters[cid]`（错误码 `PLAN_NOT_CONFIRMED`），**绝对不阻塞**其他已确认方案的章节独立启动异步生成任务；
    - 批量返回汇聚各章节异步长任务 `jobs`、16 位不可逆 SHA-256 上下文防伪指纹 `fingerprints` 及全局 Token 预算消耗统计 `token_budget_usage_summary`；
  - **物理隔离安全底线**：涉密项目（`sensitive=True`）企图调用云端模型强行阻断并返回 **HTTP 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`**；只读角色调用拦截 **403 `PROJECT_WRITER_REQUIRED`**；跨租户项目请求拦截 **404 `NOT_FOUND`**；
  - **质量证据**：专属测试 `test_ai_outline_generation_expand.py` 11 项全绿，全量 AI 联合测试 156 passed 2 skipped 全绿，OpenAPI 契约一致性 100% 保持。
- **判定**：**通过**。

---

## 二、产品对照矩阵表

| 卡ID | PRD 条款 / Gap 对应项 | 验收判定（通过/部分通过/阻塞） | 产品依据与证据摘要 | 是否书面认可建议 PM 标 done |
| :--- | :--- | :---: | :--- | :---: |
| **APP-M2-T023** | PRD §5.10.3、§6.9 / 设计规范 9.3 (StatusTag 状态注册表（9.3 全部代码表）) | **通过** | 收敛 6 大业务状态码表（项目/章节/长任务/检查/导出/租约）；纯算法验证对比度达 5.4:1~8.9:1（满足 WCAG AA 4.5:1）；AI 紫色强隔离；别名兼容与未知状态优雅降级；专属单测 6 项全绿，前端 414 项单测全绿。 | **书面认可**<br>建议 PM 标 done |
| **INT-STATUS-TAG-METADATA-GLUE** | PRD §5.10.3、§6.9 / 数据字典 §4.16 (状态注册表与元数据接口端到端契约联调) | **通过** | 前后端 6 大核心状态枚举 100% 对齐；支持 GET /api/v1/metadata/fields/all 全量聚合；8 大 RBAC 角色字段字典 editable 权限自适应（只读系统角色封退 editable=False）；RFC 7807 统一错误响应；专属联调测试 4 项全绿。 | **书面认可**<br>建议 PM 标 done |
| **BE-TECH-DEBT-03** | 架构分包规范 / AGENTS.md (workflow_orchestrator 巨石解耦与领域子编排) | **通过** | workflow_orchestrator.py 由 983 行精简至 **330 行** 高内聚门面（<= 350 行硬门禁达标）；抽离 Outline、Generation、Check、Tender、Library 5 大子编排服务；既有调用 100% 平滑兼容；专项单测 6 项全绿，核心套件 55 项全绿。 | **书面认可**<br>建议 PM 标 done |
| **AI-OUTLINE-GENERATE-EXPAND** | PRD §5.7.2、§5.7.8、§5.11、§6.4 (章节写作方案多段落结构化批量生成引擎) | **通过** | [P1]~[Pn] 结构化段落切分与评分要点映射；引用白名单防幻觉核验；跨章节独立批量生成（PRD §5.7.8 未确认章节绝不阻塞已确认章节生成）；涉密项目 403 本地模型硬门禁；只读 403 / 跨租户 404；专属单测 11 项全绿，AI 套件 156 passed 全绿。 | **书面认可**<br>建议 PM 标 done |

---

## 三、产品视角综合结论与覆盖度评估

1. **业务主路径实质性推进**：
   - Wave 5 的交付在主业务路径的「大纲分节方案多段落批量扩写生成」上取得了关键突破，真正落地了 `[P1]`~`[Pn]` 结构化分块与评分要点小标题对齐，且严格落实了 PRD §5.7.8 核心红线（未确认章节不阻塞已确认章节），使项目编写团队能够真正进行高并发、高鲁棒性的标书大纲方案扩写；
   - 引用胶囊与白名单核验机制（`extract_paragraph_citations`）彻底切断了大模型无中生有编造虚假资质与伪造切片的可能性，筑牢了「不编造/依据可追溯」的生命线；
   - 全站 6 大核心业务状态码表实现单源收口与 WCAG AA 4.5:1 对比度保证，消除了散落各处的硬编码与魔法字符串；8 大 RBAC 角色字段只读自适应防护，杜绝了只读用户界面的越权错觉；
   - 后端核心 `workflow_orchestrator.py` 由 983 行瘦身至 330 行，5 大领域子编排器独立解耦，彻底消除了长期困扰团队的巨石技术债，保障了后续业务迭代的敏捷与稳健。
2. **签署与流转建议**：
   - 本批次 4 张卡片在**业务主路径推进、安全与隔离底线、关演示正式可用性、诚实记录阻断门禁、拒绝空壳冒充交付**等主 Agent 业务验收五条金标准上全项达成，测试覆盖全面，证据真实完整；
   - **PD 正式书面认可上述 4 张任务卡，建议主 Agent 向人类 PM 推荐将这 4 张卡在看板中统一标为 `done`**。
