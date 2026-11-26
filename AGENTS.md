为什么有这个文件：让接手项目的协作者了解共同的开发和交付约定。

它解决什么问题：避免修改代码时遗漏验收、交付说明或其他协作者的工作；杜绝以纯工程重构冒充业务交付，防止测绿但产品不可用。

# 合作项目维护约定

## 开工前

1. 阅读 `docs/DOCUMENT_INDEX.md`、`docs/governance/WORKFLOW.md`、`docs/TASK_BOARD.md`、`docs/PROJECT_STATUS.md` 与 `issues/index.md`。
2. 核对工作分支和工作区；保留他人的修改，严禁重置（reset）或强推（force push）合作分支。
3. **产品完备度判断依据**：以 PRD MVP v1.8 缺口（gap / coverage，见 `docs/delivery/2026-10-22-prd-gap-summary.md`）为准，严禁将 `TASK_BOARD.md` 的 done 张数占比等同于产品完备度。可演示联调 ≠ MVP 可上线。
4. 按现有实现工作。静态原型、前端页面与 `backend/bid-core/` 业务后台分别阅读说明；本地开发默认可使用合成演示数据和模型替身，但系统已具备正式 Access Token 凭据登录与 8 大标准 RBAC 角色完整链路。在关闭演示模式（`VITE_DEMO=0`）或启用生产持久化门禁（`ICG_REQUIRE_MYSQL=1`）时，严禁假设只能通过 demo 账号工作。结构与禁令严格以本文与 `docs/architecture/repository-layout.md` 现行骨架为准。

## 文档与目录

- `docs/PRD.md`、`docs/ARCHITECTURE.md`、`docs/ROADMAP.md` 是当前前端实施视图，暂时保留路径。
- `docs/reference/product/` 是原文保存的供评审参考输入（PRD v1.8、字典 v1.9 等）；不得把版本较新等同于已全面对齐。
- `prototypes/bidding-ux/` 保持无构建、可离线打开。移动原型时将同目录资源一起移动。
- 未来代码目录严格以 `docs/architecture/repository-layout.md` 为依据；技术方案未核对前，不建立无实现的应用或微服务。
- `xqr` 的系统文档与 `main` 的前端文档属于不同层级，按 `docs/reviews/pr-1-integration.md` 整合；不直接覆盖。
- 不把真实客户原件、内部历史稿、凭据、环境密钥或运行输出提交到仓库。测试数据使用合成数据。
- 用户本轮明确授权纳入整个 `X:\ICG CO` 中的项目资料，并明确排除两类银行合同根。`ICG/`历史材料保持来源与原版本，通过 `docs/source/WORKSPACE_MATERIALS.md` 登记；它们不自动替代活动基线。合同目录、凭据及运行输出仍不得入库。
- Git 根已提升到工作区根，不在旧子目录重建第二套 Git。自动同步配置和加密令牌保存在工作区外，操作说明见 `docs/operations/workspace-sync.md`。
- **文档路径规范**：所有交付文档、代码说明、状态报告及架构文档中，严禁使用包含用户或本地盘符的绝对文件链接（如 `file:///c:/Users/...`），必须使用标准相对仓库路径（如 `../../backend/bid-core/...` 或 `../../frontend/web/...`），保证跨机器可移植性。
- **超链接与引用零死链红线（Zero Broken Links）**：全库所有 Markdown 链接必须指向具体有效的文件（如 `tasks/README.md`、`DOCUMENT_INDEX.md`）或目标文件中实际存在的 HTML 锚点/标题锚点；严禁使用目录相对路径作为超链接（如 `(tasks/)`、`(templates/)`、`(delivery/)`、`(code/)`），避免在编辑器或 Markdown 预览中点击报目录错误；在表格或任务列表中需要支持跨文档锚点跳转时，必须在目标文档中配置显式 HTML `<a id="..."></a>` 标签；D 编号必须与 `DOCUMENT_INDEX.md` 唯一登记严格一致，严禁错编、重编或虚构。

## 修改与交付

- 每次需求变更、版本更新和 Bug 修复必须先登记或更新 Issue，关联任务再开工；工程治理、选型和接口变更也登记。细则见 `issues/README.md`。
- 以 `docs/TASK_BOARD.md` 的单个任务推进；每个任务核对任务卡、依赖和验收，再标 `in-progress`。缺基线、接口或其他必要输入时不得标 `ready`。
- 每任务完成必须保存 `docs/delivery/<TASK_ID>.md`，写实际完成内容、验收、项目进度、代码解释及同步记录；有代码变更同时维护 `docs/code/<TASK_ID>.md`。模板在 `docs/templates/`。
- **签署与状态流转纪律**：各 subagent 及开发者最高只能将任务卡推到 `in-review`；`done` 状态必须由 QA 签署证据 + PD 产品验收核准 + 主 Agent 确认后，向人类 PM 推荐，由人类 PM 最终标 `done`（交付文档中明确写「建议 PM 标 done」）。
- **任务看板与任务卡双向原子一致性**：`TASK_BOARD.md` 的 Task ID 列必须指向 `tasks/<MODULE>.md#<task-id>` 对应的具体任务卡；严禁仅在看板平铺新任务行而不补齐对应的 `docs/tasks/<MODULE>.md` 任务卡定义；PM 标 done 或流转状态时，看板、任务卡、Issue 以及 delivery 文档必须四处同步变更为对应状态，严禁出现看板已 done 但任务卡仍为 in-review 的割裂。
- 每个变更必须检查 PRD、ROADMAP、ARCHITECTURE、Issue看板/详情的影响并对齐，连同 TASK_BOARD、PROJECT_STATUS、DOCUMENT_INDEX 一起更新。无影响在 Issue 和交付同步表说明原因，禁止默默跳过。
- 三件套与 Issue 看板的治理块和 `docs/governance/WORKFLOW.md` 保持同一版本、日期与 Issue；业务版本按实际变化独立维护，参考原文不改。
- 自动 WIP 快照只保存进行中的文件，不标任务 done/Issue closed；人工 Git 暂存、分支切换或整合前先停止同步。双方分叉保留现场，不强推或重置覆盖。
- 源文件使用 UTF-8；提交信息用英文。只改任务相关文件。
- 行为变更运行针对实际脚本的必要验证。静态原型至少检查资源引用、JavaScript 语法和受影响交互。
- 编辑锁与写入确认要同时校验；不能只依赖按钮禁用或 `contenteditable`。
- 在 `docs/testing/` 记录验证方式与局限，在 `docs/delivery/` 记录交付，并同步文档索引。
- 收尾运行 `node scripts/check-project-governance.cjs`；检查程序只能验证记录一致性，实际功能仍按任务验收。检查程序修改时运行 `node --test tests/governance/*.test.cjs`。
- 生成的 API SDK 后续从 `spec/openapi/` 契约生成，避免手改生成文件。

## 主 Agent 业务验收五条金标准（不仅测绿）

主 Agent 对任何 subagent 交付进行验收时，必须依据以下五条金标准执行业务核准：
1. **主路径推进**：改动必须实质性推进或保护端到端主业务路径（建项 → 解析确认 → 矩阵响应 → 分节生成 → 编辑锁定 → 检查拦截 → 两卷导出），严禁以无业务推进作用的纯工程重构冒充产品进度。
2. **安全与隔离底线**：严禁破坏「不编造/依据可追溯（.cite 与知识库关联）」、「公司多租户强隔离（${company_id}:: 命名空间）」、「涉密项目强制本地模型」以及「废标红线导出门禁」。
3. **关演示正式可用**：在 `VITE_DEMO=0` 且 `ICG_REQUIRE_MYSQL=1` 的生产模式下必须能独立通畅走通全链路；演示模式（demo 账号/假数据）通过绝不能单独作为正式通过凭据。
4. **诚实记录阻断门禁**：在声称「可递交/规则完成」时，必须如实核查系统是否仍被 `RULES_INCOMPLETE`（规则不全）或 `CHECK_BLOCKER_EXISTS`（存在废标阻断）拦截；若存在必须诚实记入 delivery，严禁虚假声称已达递交上线标准。
5. **拒绝空壳冒充交付**：知识库方案片段管理、写作档案与风格规范、模型配置等若界面仍为 `PendingPage` 或后端未接通，严禁写成已完成交付。

## 六大角色（Subagent）分工与执行规范

所有业务工单必须通过专业角色 Subagent 派发执行，主 Agent 负责分工派发、契约协调与终验把关：

1. **FE｜成长前端 subagent**：
   - 范围：严格限定在 `frontend/web/src` 8 大业务域（`app`, `shell`, `project`, `editor`, `library`, `admin`, `status`, `shared`）；
   - 测试权威路径：`frontend/web/tests/`（含 `unit/`），通过 `pnpm --dir frontend/web test` 运行；
   - 禁令：严禁在 `src` 根目录平铺文件；严禁动 backend 代码；严禁私自标 done；严禁派发/修改 `FE-M0-T04～T10`；
   - 准则：严格践行 **Layout First** 原则，以布局层级与交互自然表达意图，杜绝堆砌说明书式的次级标签与文字；主导航页面必须提供真实实现，杜绝占位壳冒充交付。
2. **BE｜成长后端 subagent**：
   - 范围：新逻辑必须划分至 `backend/bid-core/icg/{api,app,domain,infra}` 上下文子包；`icg_demo` 仅保留超轻量兼容 Façade（代码量必须严格受控在 400 行以内）；
   - API 规范：新端点只能注册至 `/api/v1`；严禁再向 `/api/demo` 新增接口；
   - 禁令：严禁将巨石逻辑堆回 `icg_demo`；严禁私自标 done；严禁绕过 `RULES_INCOMPLETE` 假装可递交；
   - 准则：必须保证错误响应符合 RFC 7807 统一体；导出门禁与租户隔离语义必须严格落盘测试。
3. **AI｜成长 AI 与 RAG subagent**：
   - 范围：知识库 RAGFlow 对接、端点对接规范、真实环境依赖隔离及防编造追溯；
   - 禁令：严禁在无真实证据时声称“生产模型对接已完成”；严禁伪造测试绿灯；
   - 准则：事实依据来源追溯（`.cite` 与知识库条目 ID 关联，禁止虚构依据写入正文）；租户数据集强制绑定 `${company_id}::` 前缀；真实探针受阻时（如透明代理 VPN 产生 ReadTimeout）必须如实留存网络诊断证据，门控 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 诚实跳过。
4. **INT｜前后端联调 subagent**：
   - 范围：打通 `/api/v1` 与前端调用的契约胶水，标准 8 角色 RBAC 会话，非演示模式全流程冒烟联调（登录 → 创建项目 → 招标文件上传与解析确认 → 响应矩阵 → 分节生成/大纲方案 → 两卷 Word 导出）；
   - 禁令：不单独开大型业务特性；严禁把逻辑堆回 `icg_demo`；严禁私自标 done；
   - 准则：真实记录请求/响应、断点定位与联调证据，主 Agent 验收看主路径是否真正打通。
5. **QA｜测试签署 subagent**：
   - 职责：独立执行全套测试复测、端到端冒烟核验与质量门禁审计；
   - 范围：运行核心后端测试套件、前端权威单元测试（`pnpm --dir frontend/web test`）、TypeScript 静态类型检查（`pnpm --dir frontend/web lint`）、OpenAPI 契约零漂移核验（`export_openapi.py --check`）以及工程治理检查（`check-project-governance.cjs`）；
   - 禁令：严禁自行在 TASK_BOARD 标 done；
   - 输出：生成独立 QA 签署报告（包含标准表格：`| 卡ID | 结论 | 证据 | 是否建议 PM done |`），明确给出是否书面建议 PM 标 done。
6. **PD｜产品验收 subagent（默认不写业务代码）**：
   - 职责：以 PRD MVP v1.8 与数据字典 v1.9 为准绳执行产品对照验收，防止「测绿但产品不可用」；
   - 范围：对照 PRD 主流程（§4.2）、规则阻断门禁（RULES_INCOMPLETE / CHECK_BLOCKER_EXISTS）、八角色权限感知、双卷 Word 导出及 64 位 SHA-256 防伪指纹，评估 PRD 真实 Gap 覆盖度；
   - 禁令：不写业务代码；无 PRD 依据不得建议 done；严禁将工单 done 数当作产品完成度；
   - 输出：生成独立产品对照报告（`| 卡ID | PRD 条款 / Gap 对应项 | 验收判定（通过/部分通过/阻塞） | 产品依据与证据摘要 | 是否书面认可建议 PM 标 done |`）。

## 质量整改与结构冻结规则

- **后端分包边界**：禁止再向 `backend/bid-core/icg_demo/` 根目录平铺新增文件，新能力必须划分到 `backend/bid-core/icg/` 上下文子包（api/app/domain/infra）；`icg_demo/` 保持薄层 Façade。
- **前端按域分层**：禁止再向 `frontend/web/src/` 根目录平铺新增页面文件，必须归入域目录（app/shell/project/editor/library/admin/status/shared）。
- **UI 与界面设计克制（Layout First）**：Avoid unnecessary secondary labels and descriptions. Let the layout do the explaining. 避免在 UI 设计与组件开发时堆砌莫名其妙的次级标签、徽标或说明文字，杜绝将界面做成说明书；依靠清晰的视觉层级、布局与交互流自然表达意图。
- **API 接口收敛与废弃生命周期**：新接口只加 `/api/v1`；`/api/demo` 路径已标为 deprecated，严格落实 RFC 8594 标准在响应头注入 `Sunset: Sun, 15 Nov 2026 00:00:00 GMT` 与 `Deprecation: true`，只读兼容至 2026-11-15 窗口期，之后予以清理下线；严禁再向旧 demo 路径添加新端点。
- **前端测试权威收口**：前端唯一权威测试套件位于 `frontend/web/tests/`（含 `unit/`，通过 `pnpm --dir frontend/web test` 运行）。根目录 `tests/frontend/` 仅保留兼容历史文档引用的轻量级转发壳（re-export），严禁在此新增或扩展第三套测试目录，严禁在 `tests/frontend/` 中编写实际业务测试逻辑。
- **持久化门禁**：生产配置、CI 工作流与关演示端到端冒烟强制 `ICG_REQUIRE_MYSQL=1`；章节正文（demo_chapter）、历史版本（demo_chapter_version）与检查结果（demo_check）全部纳入统一 MySQL 事务落盘；仅在未开启门禁的纯本地开发或显式单元测试环境下允许使用内存仓储，生产路径与强制门禁下严禁静默回落到内存仓储；非显式单元测试环境缺失 `ICG_DATABASE_URL` 时，启动必须直接报错退出。
- **默认演示关闭**：前端 `VITE_DEMO` 未设置时默认为 `false`（走真实账号与标准 RBAC 8 角色会话），仅在显式配置 `VITE_DEMO=1` 或 `true` 时开启演示快捷登录。
- **内网物理隔离与外部模型零外泄红线（Airgap Boundary）**：用户明确拍板（决策 B5/B6），客户招标文件、投标正文、Prompt 组装内容、事实与方案片段，严禁发往任何公网外部服务或公有云大模型；生产环境严格限定内网私有化部署：MySQL 8 + 内网本地 Qwen + 自建私有 RAGFlow；后端针对内网服务（RAGFlow、本地大模型）的 HTTP 客户端必须显式设置 `trust_env=False`，防止操作系统透明代理（如 VPN）拦截或劫持内网请求。
- **离线 CI 门禁与真实生产依赖隔离**：托管 CI 环境物理断开公司内网，严禁在 CI 中尝试连接内网真实服务；真实连通性测试必须通过显式环境变量（`ICG_RUN_REAL_RAGFLOW_TESTS=1`、`ICG_RUN_REAL_MODEL_TESTS=1`）门控；在假服务/Mock 服务下测绿，绝不能伪造或声称生产环境对接已完成；受阻时必须诚实记录依赖 blocked。
# 项目工程开发与验收硬规则（AI 标书生成系统）

## 一、后端数据流与状态一致性红线（Backend Invariants）

1. **禁止静默丢字段与覆盖正文**
   - 任何修改草稿快照、提交白名单（如 `_apply_technical_volume`）或持久化逻辑的 PR，必须核对所有新增结构化字段（如 `chapter_summaries`、`technical_verify`、`fact_sheet`）已纳入白名单并有落盘单测。
   - 目录结构调整（如 `replace_outline` 重排/重挂/删节）严禁以空标题骨架覆盖已有 `chapter.content`；必须按 `task_id` / 标题迁移保留既有正文。
   - 删除或合并目录节点时，其下挂载的需求/评分点必须退回 `unassigned_requirements`（未挂载池），严禁直接丢弃；`confirm_directory` 必须保留后端 409 门禁。

2. **单向数据真相源（SSOT）**
   - 前端编辑台与主流程导出器（`.docx`）必须读取同一份章节正文真相源，确保所见即所得，严禁目录重复渲染。
   - 《技术偏离表》与《响应追溯表》必须**单向提炼自本标已生成正文 + Global Fact Sheet**，彻底禁止拿招标条款直接比对历史标书填表（严禁出现“历史做法”口吻或跨厂商串标）。
   - 偏离表核心实质性条款禁止模型擅自判定“负偏离”（资料缺口标“无偏离”并附人工确认提示）；偏离表“投标文件对应页码”列必须指向本标章节号，不得错填招标文件的 `source.page`。

3. **导出前确定性净化门禁（Export Sanitizer）**
   - 所有对外导出的 `.docx` 必须经过净化管道：剥离正文首行重复输出的节标题；彻底清除 `[标:...]`、`[片:...]`、`[证:...]`、`[medium]`、32 位十六进制 ID、`需要核对` 等内部标记；所有 Markdown 表格、`<br>`、`**`、`---`、`$$` 必须正确转为 Word 原生格式，严禁源码裸露。
   - 后处理防幻觉正则（如缺失占位符替换）必须设边界保护，严禁把常规交付物名称或中文书名号 `《...》` 批量误杀替换为 `【待补】`。

4. **严禁吞错与静默降级**
   - 解析降级（如回落 `local`）、目录编排降级（如 `rule_fallback`）、并发检索异常（如超时、业务错误码）必须显式记录真实异常堆栈与错误原因到审计字段并上浮状态，严禁 `try/except` 静默吞错。

---

## 二、RAGFlow 1.0 与本地 Qwen 模型硬约束（Infra & LLM）

1. **RAGFlow 1.0 真实协议限制（Mock 测不出的坑）**
   - **Reranker 上限**：检索 `page_size` 硬上限为 `32`（超限会稳定触发 `RAGFlow business error 102`）。
   - **不可靠算子禁用**：真实 RAGFlow 的 `contains` 非子串匹配、`not is` 负向过滤不可靠；型号过滤必须走“精确 → 变体 OR → `doc_type` 级 → 无过滤”放宽阶梯，排他规则一律在应用侧执行（且 `history` 库防串标排他作为安全底线永不放宽，配合超额召回防滤空）。
   - **分路可观测性**：多路检索审计必须为每一路强制记录 `query`（非空校验）、`status`（`ok/empty/filtered_empty/error`）、`raw_hits`、`post_filter_hits`、`top_score`、`error_detail`。
   - **租户与脏数据隔离**：测试/合成文档（如 `Model-X800` 等）必须与生产知识库租户物理隔离；存在占位 `dataset_id` 时必须显性告警。
   - **陈旧 `document_id` 同步检测**：知识库同步或检索层必须校验本端索引引用的远端 `document_id` 是否仍存在；重建 Dataset 后若出现批量失效引用，必须显性告警并触发重映射/自愈提示，严禁静默归零后继续生成。

2. **本地 Qwen 30B 推理约束**
   - 章节生成并发度必须通过 `ICG_SECTION_CONCURRENCY` 可配，默认不超过 `2`，防止打满本地推理队列导致意图拆解/摘要超时降级。
   - 意图拆解、章间摘要、后置核验等轻调用关闭思考模式时，**严禁向推理接口透传 `thinking_budget` 等思考参数**。
   - 必须按章节权重差异化分配 `max_tokens`（高分核心节 4096 / 普通节 2048 / 简明节 1200），并检查 `finish_reason == "length"` 及末尾句读/表格闭合状态，未闭合自动续写收尾。
   - 关键约束不能只靠 Prompt 祈祷：检索领域锚点固定、商务条款分册拦截、案例一次性配额、反八股/防串标校验必须有确定性代码兜底。

---

## 三、前端开发与前后端契约规范（Frontend & API）

1. **强契约同步**
   - 后端任何路由、请求体或响应 Schema 变更（如 `fact_sheet` 字段扩展、新接口端点），必须同步执行 `export_openapi.py --check` 重新导出契约，并确保前端 `tsc -b --noEmit` 零错误。
2. **Antd v5+ 零告警规范**
   - 禁止使用已废弃属性（如 `bodyStyle`、`destroyOnClose`、`addonAfter` 等）和静态 `message.*` 调用（统一通过 `App.useApp()` 获取实例），保证构建与浏览器控制台零 Antd 告警。
3. **用户态透明与交互闭环**
   - 面向业务用户的界面文案必须清晰直观，避免直接暴露内部技术代号（如 `filtered_empty`、`L0/L1`、`chunk_id`）。
   - 解析降级、未挂载评分点、占位知识库 ID 必须在界面给明确拦截或提示，不允许静默放行。
   - 核验警示（`verify_warnings`）必须支持人工“已核无误，消除警示”交互并记录操作人与时间留档（`dismissed_warnings`），不得物理删除核验证据，也不可让合理规则误报永久挂红标阻塞终审。

---

## 四、Devin 编码、验证与汇报纪律（Execution Protocol）

1. **严禁“无效前提下的虚假达标”**
   - 验收下游效果前必须先核验上游前提生效。例如：`history` 路 `raw_hits=0` 或 `filtered_empty` 时，**禁止**将“零串标”标注为“注入后达标”；`fact_sheet` 报 422 未注入时，不得宣称 SLA 约束验证通过。
2. **诚实区分 Mock 与真机验证**
   - 基于 `FakeRagflow` / 模型替身的绿灯仅代表单测通过，不得作为端到端验收结论；涉及 RAGFlow、本地模型、导出链路的修复必须在汇报中明确区分「单测通过」与「真机门控验证（`ICG_RUN_REAL_RAGFLOW_TESTS=1` / `ICG_RUN_REAL_MODEL_TESTS=1`）」。
3. **重启确认与“先定向、后全量”**
   - 修改后端代码或 API Schema 后，执行真机验证前必须确认后端进程已重启并加载最新代码。
   - 修复单点缺陷（如目录拟定、单路检索、偏离表导出拆分）时，先复用已有项目数据做秒级定向验证并贴出实证日志，全部确认通过后再触发耗时较长的全量正文生成。
4. **基线对照与文档同步**
   - 遇到回归失败需与 `HEAD` 基线对照区分存量与新引入问题；每次交付同步更新任务卡、交付文档与 OpenAPI 契约，未完成真机门槛前任务保持 `in-review`，不擅自标 `done`。

---

### 五、全局净化/导出层严禁硬编码单项目业务事实（Anti-Hardcoding Redline）

- **严禁事项（零容忍）**：
  - 严禁在全局后处理、净化器或导出器（如 `export_sanitizer.py`、Word/Excel 渲染层）中，硬编码任何特定项目的业务参数、数字替换规则或固定文档/机构名称——例如将 `15人→7人`、`48小时→24小时`、`二级40分钟→2小时`、`近三年→近两年` 写死为正则替换，或将特定合同/协议名（如《XX安全协议书》）写死回填表格单元格。
  - 严禁通过“导出层正则硬改正文数字”来伪造验收指标归零，防止静默篡改后续其他项目的合法业务参数。
- **全局净化层唯一合法职责**：
  - 仅做**与业务事实无关的通用格式/语法净化**：剥离重复节标题、清除内部标签（`[标:]`/`[片:]`/`[证:]`/`[medium]`/`T-xx`/`S-xx`/32位hex）、清理裸露 Markdown 符号（`>`、`**`、`---`、`<br>`、`$$`）、修复剥离标签后残留的空括号/语病、保护合法技术符号（如 `v$parameter`）、按完整句边界截断。
  - 针对特定表格的单元格修复（如补齐合规表「依据来源」列）必须严格限定表格类型作用域，严禁跨表误伤《技术偏离表》页码列等其他表格。
- **项目事实一致性的唯一正确链路**：
  - **生成前**：所有 SLA 时限、服务周期、团队人数、资产清单、评分决策、基准年份统一维护在 `Global Fact Sheet`，动态注入生成 Prompt。
  - **生成后**：由 `technical_verifier.py` 动态读取当前项目的 `Global Fact Sheet` 执行跨节事实比对，检出冲突后落入 `verify_warnings` 告警或触发对应章节局部重写，绝不在导出层静默硬改。
- **偏离表 LLM 兜底缓存防毒**：
  - `technical_deviation_llm_cache` 只有在同一指纹下全部兜底条款都通过门禁后才允许写入；任一单条失败、超短、外实体、负偏离或未支撑绝对化承诺时，严禁把部分结果包装成完成态缓存，防止错误响应在后续导出中被永久复用。
  - 缓存命中审计必须区分本次 `calls=0` 与原始 `cached_calls`；模型、正文、Fact Sheet 或 Prompt 指纹变化后必须失效重算。
- **单测门禁**：
  - `export_sanitizer` 相关单元测试禁止断言具体业务数字/年限/机构名的硬编码改写；业务一致性测试必须通过构造不同的 `Global Fact Sheet` 动态输入来验证。