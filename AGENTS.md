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

## 修改与交付

- 每次需求变更、版本更新和 Bug 修复必须先登记或更新 Issue，关联任务再开工；工程治理、选型和接口变更也登记。细则见 `issues/README.md`。
- 以 `docs/TASK_BOARD.md` 的单个任务推进；每个任务核对任务卡、依赖和验收，再标 `in-progress`。缺基线、接口或其他必要输入时不得标 `ready`。
- 每任务完成必须保存 `docs/delivery/<TASK_ID>.md`，写实际完成内容、验收、项目进度、代码解释及同步记录；有代码变更同时维护 `docs/code/<TASK_ID>.md`。模板在 `docs/templates/`。
- **签署与状态流转纪律**：各 subagent 及开发者最高只能将任务卡推到 `in-review`；`done` 状态必须由 QA 签署证据 + PD 产品验收核准 + 主 Agent 确认后，向人类 PM 推荐，由人类 PM 最终标 `done`（交付文档中明确写「建议 PM 标 done」）。
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
- **持久化门禁**：生产配置、CI 工作流与关演示端到端冒烟强制 `ICG_REQUIRE_MYSQL=1`；章节正文（demo_chapter）、历史版本（demo_chapter_version）与检查结果（demo_check）全部纳入统一 MySQL 事务落盘；仅在未开启门禁的纯本地开发或显式单元测试环境下允许使用内存仓储，生产路径与强制门禁下严禁静默回落到内存仓储。
- **默认演示关闭**：前端 `VITE_DEMO` 未设置时默认为 `false`（走真实账号与标准 RBAC 8 角色会话），仅在显式配置 `VITE_DEMO=1` 或 `true` 时开启演示快捷登录。
