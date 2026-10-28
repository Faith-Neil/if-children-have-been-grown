为什么有这个文件：集中显示每个任务的状态、依赖和交付入口。

它解决什么问题：帮助判断现在能做什么、卡在哪里、完成后有什么证据。

# 项目任务看板

任务版本：0.7；治理版本：g1.1；更新日期：2026-10-27；当前实现 Issue：[ISSUE-007](../issues/ISSUE-007.md)；结构收官：[ISSUE-038](../issues/ISSUE-038.md)；离线检查：[ISSUE-012](../issues/ISSUE-012.md)；生产门禁：[ISSUE-005](../issues/ISSUE-005.md)；模型决定：[ISSUE-010](../issues/ISSUE-010.md)（closed）；tip：deca9de。

将 [前端 ROADMAP](ROADMAP.md) 的 Phase 0～8 与发布 Milestone 1～5 拆为 **59 张任务卡**，由 FE-M0～FE-M8 管理。前缀 FE 表示前端合作交付；这些编号与参考全系统 M0～M8 的门禁、周期和范围独立。

项目 434 项中（以表内实时状态为准：done 84、in-review 64、in-progress 7、planned 231、blocked 41、cancelled 7、ready 0），挂上 ISSUE-038 三项结构债）。APP-M1的16项中，T01～05继续实现，T06继续完整联调验收，T07已完成范围拆分，T08等待最终审计；T09～16限定子任务已本地验收，T16完成资料及公司模板旧表单保护。APP-M2的259卡中T001布局、路由和离开保护为 done，T002请求层为 done。项目经理在群里确认 QA 签署后标为 done，T008离线CI为 done，T078 内存发布为 done（QA 19c4862，PM 17:20 确认），页面未做不挡住本卡，T114 挂证据抽屉为 done（QA f521950，PM 17:13 确认），T124 改为 ready，本轮不实现，其 OpenAPI 契约已冻结且 ISSUE-022 已依据 QA 0254102，PM 15:36 确认 closed，APP-M2-T021 已依据 QA 签署（D-764）与 PD 验收（D-765）由 PM 确认为 done，其余252卡planned，47组页面、190原WBS细项及44规则已逐项映射，见[完整后续卡](tasks/APP-M2.md)与[来源核对](testing/icg-task-mapping.md)。BE-M0现为19项：T01已验收；T02与T03由项目经理于 10-12 12:28 在 QA 签署后确认，标为 done；MySQL 8 方案与连接空迁移由项目经理在 QA 签署 98c5129 后确认，标为 done；锁迁移 BE-M0-T04 与导出快照 BE-M0-T05 为 in-review（QA REV-M0-T32/T33 已签，等 PM），202/SSE BE-M0-T06 为 in-review（QA REV-M0-T36 tip `0cb6c38` 已签，等 PM），operationId BE-M0-T07 为 in-review；旧接口错误体为 planned。按聚合迁移的项目聚合已依据 QA ae38ec3，PM 17:16 确认 done。T11 回执与会话已依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done。T12 编辑租约已依据 QA ae6fd10，PM 15:32 确认 done。T13 项目聚合已依据 QA ae38ec3，PM 17:16 确认 done。T14 托管 MySQL 作业已依据 QA 签署 b20b844 标为 done。Word 默认版式 BE-M0-T15 已由项目经理于 18:01 确认 done。用户已在 Word/WPS 目视确认。ISSUE-027 已 closed。错误码名字冻结 BE-M0-T16 为 in-review（QA REV-M0-T34 已签，等 PM）。编辑锁对齐字典 BE-M0-T17 为 planned，排在 T13 之后。证据挂接规则 BE-M0-T18 为 in-review（QA REV-M0-T35 已签，等 PM）。项目表对齐字典 BE-M0-T19 为 planned，等正式项目表和成员表存在后再迁移，保留历史行。ISSUE-033 为 in-review。旧接口含 E2E-D5 的大小写 `/api` 前缀。ISSUE-005 保持 in-progress，T04、T05、T06 与 T07 均为 in-review（T06 QA REV-M0-T36 已签，等 PM），不关闭。旧FE59项保留来源，OPS 2项中 T01 已本地验收、T02 已由用户 10-12 14:34 确认并标为 done，未部署，REV 36项中26项已本地验收，T31为增量审查in-review；T32～T35 为 BE-M0-T04/T05/T16/T18 QA签署 in-review；T36 为 BE-M0-T06 QA签署 in-review（含 T23、T25、T26、T28、T29、T30；REV-M0-T22 已依据 QA f521950，PM 17:13 确认 done；REV-M0-T24 已依据 QA 19c4862，PM 17:20 确认 done；T06、T08、T25、T26、T27、T28、T29 与 T30 为 in-review。REV-M0-T27 / ISSUE-034 已由 QA 签署 R1～R9，不标 done）（REV-M0-T02为ISSUE-013 QA复跑，REV-M0-T03/T04为ISSUE-015，REV-M0-T05为T008与AI-02的QA签署，REV-M0-T07为T02/T03的QA签署）。AI-01改为 in-review：对话模型由配置页提供，嵌入与向量库用 RAGFlow 自带，生产生成仅内网；真实端点另计验收。业务库已定为 MySQL 8，方案与连接空迁移已由项目经理在 QA 签署 98c5129 后确认 done，回执和登录会话由 T11 已依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done，编辑租约由 T12 依据 QA ae6fd10，PM 15:32 确认 done，项目聚合由 T13 依据 QA ae38ec3，PM 17:16 确认 done，章节及其他聚合仍在内存；AI-02 与 T008 均已由项目经理于 10-12 12:10 在 QA 签署后确认，标为 done。AI-03 为 done，只使用内存检索。AI-M0 现为 6 项：AI-04、AI-05 与 AI-06 为 in-review。ISSUE-037 为 in-progress，ISSUE-029 保持 closed。开发者只能把卡片标到 in-review，done 由项目经理在 QA 签署后设置。ISSUE-009 已由项目经理在 QA 签署 d55d507（REV-M0-T11）后确认 closed。ISSUE-014 已由项目经理在 QA 签署 173c39f（REV-M0-T14）后确认 closed。T001 与 T002 已为 done。QA 于 2026-10-12 签署 T001 本切片不通过；浅色内容、顶栏和前进/后退修复后，REV-M0-T11 签署通过。ISSUE-020 已由项目经理在 QA 签署 dcca509（REV-M0-T15）后确认 closed。ISSUE-018 已批准并改为 in-progress：方案与连接空迁移已 done，T11 回执与会话已依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done，T12 已依据 QA ae6fd10，PM 15:32 确认 done，T13 项目聚合已依据 QA ae38ec3，PM 17:16 确认 done。ISSUE-023 已由项目经理在 QA 签署 16cf971 后确认，状态为 closed。ISSUE-021 排队且任务为 planned，ISSUE-022 已依据 QA 0254102（REV-M0-T20），PM 15:36 确认 closed，契约文本已冻结，T124 已按 PM 17:20 改为 ready，本轮不实现。PR #3 已合入，foundation 分支已删。ISSUE-026 已由项目经理在 QA 签署 9bcde17（REV-M0-T13）后确认 closed。PRD、ROADMAP 与 PROJECT_BRIEF 的任务计数是里程碑快照 as of commit 3bb311ad3ab86c0de2f871876a50c7d50f9bb985，并计入本提交将 T001 与 T002 标为 done：366 项、32 done、6 in-review、7 in-progress、268 planned、49 blocked、4 ready。任务看板是准绳，三份基线只在里程碑更新。这些数量不是产品完成率。

59张前端卡片估算合计 209 小时，单卡 2～4 小时，处于 0.5～4 小时的任务粒度目标内。该总和是已有基线/接口条件下的前端增量估算，不是项目排期，不含后端、模型、取得输入、评审或等待时间。开工若预计超 4 小时，先继续拆卡并登记 Issue/版本变更，保留原任务 ID 的历史。

## 结构债收官指针（2026-10-26 · 勿忽略）

- **WP-1～WP-7 真实进展与口径纠偏（2026-10-26 审计）**：前端八域物理分层完成；后端分包进行中 / 双路径未收口（`icg_demo` 根级仍有 35 个业务 py 平铺，Memory 旁路与 MySQL 双路径仍存，`/api/demo` 兼容窗口至 2026-11-15）。用户 2026-10-26 已官方拍板 B1～B6，全面开启 D0～D5 规划未落地债收口。
- **DOC-SYNC-1 与 DOC-SYNC-1.1 已落地**（tip：`7b3c196`）；活文档已与代码实树全面对齐，禁止抄假模块名。
- **禁止把 FE-M0-T04～T10 当绿野开工**（正式工程脚手架/登录/Shell/路由等能力已被 WP + APP-M2 路径覆盖）。相关卡在看板标为 `cancelled`（`superseded-by-WP`），禁止重建工程，仅允许补充验收交付。
- **结构债后续**：`issues/ISSUE-038.md`（双错误体 / 巨石继续瘦身 / 空 `icg.api|app`）→ 见板内 `BE-TECH-DEBT-*` / `FE-TECH-DEBT-*`（P2，勿压过 PRD P0）。
- **完成度口径**：board `done` 张数 ≠ 产品完成度；产品以 PRD v1.8 + `docs/delivery/2026-10-22-prd-gap-summary.md` 为准。
- **前四项拍板任务已交付**（①～④ 全部闭环）：
  - ① CI 分支修复与 5 大作业自动运行（[D-721](delivery/2026-10-23-ci-offline-check-branches.md)）
  - ② tip 对齐与非 demo 冒烟留证（[D-722](delivery/2026-10-23-in-review-signed-for-pm.md)、[D-723](delivery/2026-10-23-non-demo-smoke-evidence.md)）
  - ③ 模型与 RAGFlow 弹窗配置及内网真服务连通（[D-724](delivery/2026-10-23-model-ragflow-config-modals.md)、[D-725](code/2026-10-23-model-ragflow-config-modals.md)）
  - ④ 规则最小集与分册定稿闸门（[D-726](delivery/2026-10-23-submission-rules-finalize-gate.md)、[D-727](code/2026-10-23-submission-rules-finalize-gate.md)）
- **下一棒默认顺序（D0～D5 执行路线图，按序推进）**：
  - D0 治理回写：**【已完成】** 实 tip `e586f26` 回写，WP1～7 纠偏，B1～B6 拍板落地，产出 [D-728](delivery/2026-10-26-debt-backlog-board-sync.md) 与 [D-729](delivery/2026-10-26-signed-awaiting-pm.md)。
  - D1 默认路径诚实化：**【已完成】** 启动脚本与文档明确生产必用 MySQL；关演示冒烟与 CI 强制 `ICG_REQUIRE_MYSQL=1`；堵住无 URL 静默 Memory 当绿；前端明确 `VITE_DEMO` 诚实默认策略为 `false`（关演示走正式账号与可信会话），仅显式 `VITE_DEMO=1` 开启演示；测试全绿，交付见 [D-730](delivery/2026-10-26-demo-mysql-defaults.md) 与 [D-731](code/2026-10-26-demo-mysql-defaults.md)（in-review）。
  - D2 后端去平铺（包重命名与迁移）：**【已完成主实现分层迁移与 Façade 瘦身】** 落实 B1 拍板，主实现迁入 ackend/bid-core/icg/{api,app,domain,infra}，icg_demo 降为薄兼容（由 12,589 行锐减至 364 行，压缩率 97.11%），填满 icg/api 与 icg/app；测试与 OpenAPI check 全绿，交付见 [D-738](delivery/2026-10-26-backend-unflatten-progress.md) 与 [D-739](code/2026-10-26-backend-unflatten-progress.md)（in-review）。
  - D3 持久化与双错误体收口：**【已完成契约与错误体收口联调】** 落实 B4 拍板 `/api/demo` 标 deprecated 与 RFC 8594 Sunset 响应头；全站统一规范错误体 `{code,message,details,traceId}` 并严格优先解构；后端与前端双错误体与废弃声明专属测试全绿；交付见 [D-732](delivery/2026-10-26-persistence-and-error-body.md) 与 [D-733](code/2026-10-26-persistence-and-error-body.md)（in-review）。
  - D4 产品断环（RAGFlow 知识库摄入）：**【已完成知识库摄入闭环】** 落实 B5/B6 拍板，补齐 RAGFlow dataset/kb_sync 摄入闭环，实现多租户命名空间强隔离、文档上传、内置解析轮询、状态映射与优雅降级；专属单测 10 项全绿通过（9 passed 1 skipped），联合回归 71 项全绿通过；交付见 [D-734](delivery/2026-10-26-ragflow-kb-sync.md) 与 [D-735](code/2026-10-26-ragflow-kb-sync.md)（in-review）。推进下一批高优先 PRD 合规规则与关演示主链路端到端人工冒烟留证。
  - D5 二次瘦身与低优先：落实 B2 拍板引入 react-router；App.tsx / EditorPage.tsx 拆解瘦身；OpenAPI / styles.css 拆分；清理 tests/frontend 转发壳。

## 规划未落地债收口与用户拍板纪要（2026-10-26）

### 一、实施审计总判断
- 前端八域搬家、CI触发修复、OpenAPI check、八角色码表已切实闭环。
- “WP-1～7完全收官”口径虚高：实为前端八域分层完成；后端主实现仍平铺在 `icg_demo/`（35个业务py），Memory 旁路与 MySQL 双路径仍存，`/api/demo` 与双错误体未收口，章节正文等聚合点仍偏 Memory。
- 产品口令①已解决；②③④均为部分完成（tip滞后、dataset/kb_sync摄入断环、规则库仅为最小集而非R01–44）。
- 看板 `done` 张数（52/404）≠ 产品完备度（约28%～35%）。

### 二、用户针对审计 B 类的官方拍板结论（必须按此执行）
1. **B1. 包重命名**：**【已拍板】确定本轮重命名**。将 `icg_demo` 推进至 `icg` 命名体系，主实现进入 `icg/{api,app,domain,infra}`，`icg_demo` 保留薄层转接兼容下游。
2. **B2. 路由方案**：**【已拍板】确定引入 React-router**。替换简易字符串匹配，规范路由表与守卫。
3. **B3. 持久化门禁**：**【已拍板】强制。生产、关演示冒烟、CI 均强制 `ICG_REQUIRE_MYSQL=1`**。本地单测允许显式指定 Memory，但绝对禁止无 URL 时静默回落到 Memory 还当绿灯。
4. **B4. `/api/demo` 下线窗口**：**【已拍板】立即 deprecated，不再加新接口；兼容截止 2026-11-15，之后删除**（未迁调用须先迁至 `/api/v1`）。
5. **B5. 数据与模型边界**：**【已拍板】严禁发外网**。招标/投标内容仅走内网本地 Qwen 与自建 RAGFlow，数据不出公网。
6. **B6. 交付目标环境**：**【已拍板】公司内网私有化、可离线**；OS 以 Windows 为主、兼顾内网 Linux；MySQL 8 + 内网 Qwen + 自建 RAGFlow。
7. **B7. 已签等 PM 清单**：**【已拍板】仅产出清单与证据路径，等用户 PM 最终确认后再标 done**（详见 [D-729](delivery/2026-10-26-signed-awaiting-pm.md)）。

### 三、本轮执行路线图（D0～D5）
详见上文“下一棒默认顺序”与交付文档 [D-728](delivery/2026-10-26-debt-backlog-board-sync.md)。

## 额度暂停期审查纪要（2026-10-23）

### 一、前因与审查总判断
- **工单完成率 vs 产品完备度**：看板任务 done≈52/404（约 13%）为工单任务完成率，产品完备度经深度审查粗估仅约 28%～35%（详见 `docs/delivery/2026-10-22-prd-gap-summary.md`）。任务卡通过单测不能等同于 MVP 达到上线标准。
- **主链路交付现状**：主链路（建项→解析→矩阵→生成→编辑→检查→导出）绝大部分仍为部分交付或演示兼容壳；递交版导出仍因全量合规规则不齐及分册定稿未完成被 `RULES_INCOMPLETE` 强门禁拦截。

#### 六点专项审查结论（模型配置与知识库 / RAGFlow）
| 专项项 | 审查结论 | 现状说明 |
|---|---|---|
| **模型配置前端页** | **无** | 无独立路由与交互入口；APP-M2-T036～T041 多处于 planned，前端未做连接表单 |
| **模型后端运行时** | **部分** | 后端已有 `/api/v1/model-configs` CRUD、测试连接及项目绑定能力；ISSUE-028/AI-01 为 in-review；仅假服务跑通 |
| **模型前后端联调（含 UI）** | **无** | 前端完全未调用 `/api/v1/model-configs`，无联调界面 |
| **RAGFlow 前端配置页** | **无** | 无任何针对 RAGFlow 端点、密钥、知识库数据集绑定的前端管理界面 |
| **RAGFlow 后端检索** | **部分** | 客户端具备 env 门控；AI-04/05/06 为 in-review；章节 AI 闭环仅在假 RAG 服务下跑通 |
| **RAGFlow 配置联调（含 UI）** | **无** | 缺乏前后端真实配置联动，配置当前仅依赖环境变量，未对齐真实数据集 |

#### ICG 前后端审查意见摘要（只读审查）
- **后端意见**：主流量与多数聚合调用仍在 `icg_demo/`；Memory 旁路与 MySQL 存在双路径隐患，是首要质量风险；demo 命名与 `/api/demo` + `/api/v1` 双前缀尚未完全收口；前端未调用 model-configs。
- **前端意见**：无独立模型与 RAGFlow 配置入口；公司设置页中的只读展示字段不等于联调完成。
- **AI 意见**：当前仅在假服务假数据下全绿；真 RAGFlow 服务从未实际验收；缺少 dataset 绑定与 kb_sync 导致知识摄入闭环缺失；配置目前仅靠环境变量硬编码。
- **QA 意见**：单测绿不等于产品可验收；看板上积压多张 in-review；关演示真实环境（`VITE_DEMO=0` + `ICG_REQUIRE_MYSQL=1`）必须具备独立端到端人工冒烟证据。
- **DevOps 意见**：`.github/workflows/offline-check.yml` 的 `on.push` / `pull_request` 分支仅配置了已删除的 `codex/repository-foundation`，导致向 `feat/opencode-ICG` 与 `main` 推送代码时根本不会触发 CI；远程 tip 处于 checks=0 状态；分支保护未开启；看板上仍残留「PR #3待合入」的陈旧叙述。

### 二、用户决策（必须按此执行）
1. **严格按序执行四项任务**：① → ② → ③ → ④（不要跳序）：
   - **① 修 CI 工作流**：修复 `.github/workflows/offline-check.yml`，分支覆盖 `main` 与 `feat/opencode-ICG`，推送后确认 Actions 五大作业全绿并编写交付报告；
   - **② 对齐 tip 与真实冒烟**：回写看板与 PROJECT_STATUS 真实 tip；梳理「已签等 PM」清单交由用户/PM确认；在 `VITE_DEMO=0` + `ICG_REQUIRE_MYSQL=1` 下完成主路径人工冒烟留证；
   - **③ 前端弹窗配置与真 RAGFlow 接入**：模型配置与 RAGFlow 配置前端形态明确采用**弹窗配置页**；对接 `/api/v1/model-configs`；接入真实 RAGFlow 服务（参考 https://github.com/infiniflow/ragflow）；假服务仅保留供 CI 离线回归；真实端点/Key 向用户索取，严禁编造；
   - **④ 规则最小可递交集 + 分册定稿闸门**：推进合规规则编号集与定稿锁定闭环。
2. **配置交互形态**：模型配置与知识库/RAGFlow 配置前端形态定为**弹窗配置页**（不是只靠环境变量或整页大重构）。
3. **真实服务底线**：RAGFlow 必须接入真实运行服务；假服务仅保留给 CI 离线检查使用。
4. **代码编写权**：写码由用户本人通过 Antigravity 完成；ICG bot 仅执行只读审查。

## 状态与完成条件

| 状态 | 含义 |
|---|---|
| `planned` | 已分解，尚未启动；范围/优先级或前置条件仍待核对 |
| `blocked` | 明确等待已列出的基线、任务依赖、契约或真实服务 |
| `ready` | 已关联 Issue，基线、依赖、范围、验收与接口条件均已满足，尚未开工 |
| `in-progress` | 正在实施或验收；不能以文件已创建等同完成 |
| `in-review` | 实现及完成材料已提交，等待任务验收 |
| `done` | 验收通过、专属交付文件与代码/文档解释存在，Issue/进度/文档/索引已同步 |
| `cancelled` | 已有明确取舍；链接关联 Issue 的取消决定，保留历史 |

每张卡完成时必须新增自己的 `docs/delivery/<TASK_ID>.md`，说明变更结果、实际文件、验证命令及结果、未实现项和限制。有代码修改时，同时创建独立 `docs/code/<TASK_ID>.md` 并在交付中链接，解释入口、调用顺序、数据/状态流、关键判断与异常、依赖及限制；无代码修改在交付中明确写“无”并说明文档目的。随后同步统一 Issue、任务看板、项目进度、PRD/ROADMAP/ARCHITECTURE 的影响核对和文档索引。相关文档无需修改时，交付中逐项记录所核对章节与理由。

只有任务专属交付文件存在、验收证据齐全且状态同步后才能标 `done`；本地已验收与已合入/已发布分别记录。待产出的路径使用代码文本，不创建虚假的交付链接。

统一 Issue 用于需求变更、版本更新和 Bug；一个 Issue 可关联多张实现任务卡，任务不能替代 Issue 的决定与关闭记录。表中“—”表示尚未登记，开工前必须补真实关联，避免伪造 Issue 编号。

## 里程碑映射

| 前端里程碑 | 原路线图来源 | 任务数 | 当前完成 | 可并行关系 |
|---|---|---|---|---|
| [FE-M0 基线与基础](tasks/FE-M0.md) | ROADMAP Phase 0；发布 Milestone 1～5 的共用基础 | 10 | 2 done / 7 cancelled | T01/T02已验收；T04～T10已由 WP-1～7 质量整改覆盖（superseded-by-WP，标为 cancelled，禁止绿野重建）。 |
| [FE-M1 项目主流程](tasks/FE-M1.md) | ROADMAP Phase 1；发布 Milestone 1 | 7 | 0/7 | 项目创建、解析与资料列表依各自基础卡启动；事实不必等待全部矩阵界面。 |
| [FE-M2 章节生成](tasks/FE-M2.md) | ROADMAP Phase 2；发布 Milestone 2 | 5 | 0/5 | 章节树与方案接入按矩阵/事实依赖推进；任务卡默认能力依契约，不等待管理界面完成。 |
| [FE-M3 编辑台](tasks/FE-M3.md) | ROADMAP Phase 3；发布 Milestone 3 | 9 | 0/9 | 文档模型、草稿和锁可在全部章节闭环之前开发；来源与助手按数据依赖接入。 |
| [FE-M4 检查导出](tasks/FE-M4.md) | ROADMAP Phase 4；发布 Milestone 4 | 6 | 0/6 | 检查中心可与生成结果及编辑器联调并行；真实导出等待有效检查与权限。 |
| [FE-M5 资料写作管理](tasks/FE-M5.md) | ROADMAP Phase 5～6；发布 Milestone 5；参考 PRD 通用与运维页面补差异 | 11 | 0/11 | 资料库在基础客户端/Shell 到位后可与 FE-M1 并行；管理模块按具体接口拆开。 |
| [FE-M6 协作](tasks/FE-M6.md) | ROADMAP Phase 7；一期可延后范围 | 4 | 0/4 | 后续范围确认后按负责人、评论、引用等具体依赖推进，彼此无需整阶段串行。 |
| [FE-M7 效率](tasks/FE-M7.md) | ROADMAP Phase 8；一期可延后范围 | 4 | 0/4 | 可选效率增强按相关模块依赖推进，不是一期发布前置。 |
| [FE-M8 发布门禁](tasks/FE-M8.md) | ROADMAP §11 MVP Cut Line、§13 Gate A/B/C；贯穿发布 Milestone 1～5 | 3 | 0/3 | 发布验证覆盖一期必需任务；无需等待可选 FE-M6/FE-M7。 |
| [OPS-M0 工作区运维](tasks/OPS-M0.md) | ISSUE-004工作区同步；ISSUE-017内网部署草案 | 2 | 2/2 | T01同步已验收。T02 已由用户 10-12 14:34 确认，标为 done，未部署。多副本仍 blocked 在 ISSUE-018。 |
| [REV-M0 接手审查](tasks/REV-M0.md) | ISSUE-004目录与业务/技术审查；ISSUE-013 QA复跑；ISSUE-015 T06计划；ISSUE-013 签署；ISSUE-019 E2E、T001签署；ISSUE-034 最新分支复核 | 36 | 26/36 | 审查/brief交付完成，设计决定留ISSUE-005；QA复跑、T06计划及贯通冒烟/Word渲染完成。T22 为 T114 冲突刷新 QA，已 done。T23 与 T24 已 done。T06、T08、T25、T26、T27、T28、T29、T30、T31、T32、T33、T34、T35、T36 为 in-review。T32～T35 为 tip 90b2334 上 T04/T05/T16/T18 QA签署；T36 为 tip 0cb6c38 上 T06 QA签署，不标 done。 |
| [BE-M0 后端链路](tasks/BE-M0.md) | ISSUE-006本地后端demo；ISSUE-005契约卡；ISSUE-018实施中；ISSUE-023已关闭；ISSUE-025托管MySQL作业；ISSUE-027版式；ISSUE-031错误码名字；ISSUE-032编辑锁对齐；ISSUE-033挂证据规则；ISSUE-035项目表对齐；ISSUE-021排队 | 19 | 10/19 | T01～T03已验收。T02与T03由项目经理于 10-12 12:28 在 QA 签署后确认。T08与T10由项目经理在 QA 签署 98c5129 后确认，标为 done；T04 与 T05 为 in-review（QA REV-M0-T32/T33 已签，等 PM），T06 为 in-review（QA REV-M0-T36 tip `0cb6c38` 已签，等 PM），T07 为 in-review；T09 planned。T11 回执与会话已依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done。T12 编辑租约已依据 QA ae6fd10，PM 15:32 确认 done。T13 项目聚合已依据 QA ae38ec3，PM 17:16 确认 done。T14 已依据 QA 签署 b20b844 标为 done。T15 Word 默认版式已由项目经理于 18:01 确认 done。用户已在 Word/WPS 目视确认。ISSUE-027 已 closed。T16 错误码名字为 in-review（QA REV-M0-T34 已签，等 PM）。T17 编辑锁对齐字典为 planned。T18 证据挂接规则为 in-review（QA REV-M0-T35 已签，等 PM）。T19 项目表对齐字典为 planned。ISSUE-005 仍 in-progress。ISSUE-023 已 closed。 |
| [APP-M1 示例实现](tasks/APP-M1.md) | ISSUE-007示例与后台联调；ISSUE-008资料保护 | 16 | 9/16 | T07及T09～16已本地验收；完整父任务继续。 |
| [AI-M0 模型接入准备](tasks/AI-M0.md) | ISSUE-010已关闭；ISSUE-011兼容适配器；ISSUE-016内存检索；ISSUE-037检索实现 | 6 | 2/6 | AI-01为in-review；AI-02为done，项目经理于 10-12 12:10 在 QA 签署后确认；AI-03为done，依据 QA 签署 2fe6198（REV-M0-T16）。AI-04、AI-05 与 AI-06 为 in-review：CI 假 RAGFlow 已记录 Authorization 与 base_url，只读客户端与证据候选改走 RAGFlow 接线完成，章节 AI 生成与建议端到端闭环贯通（test_chapter_generation_rag_flow.py 7 passed），真实连接须 ICG_RUN_REAL_RAGFLOW_TESTS=1，默认跳过。对话模型假服务仍须 ICG_RUN_REAL_MODEL_TESTS=1。不改 ISSUE-028/AI-01 为 done。ISSUE-029 保持 closed。 |

发布 Milestone 1～5 分别映射 FE-M1～FE-M5；FE-M0 为共用基础，FE-M6/FE-M7 为原 Phase 7/8 的可选增强，FE-M8 为贯穿原 Gate A/B/C 的发布验收。

依赖按**任务**记录：只等待表中所列任务及其真实接口，不要求先完成上一整个里程碑。MVP Cut Line 以已评审范围为准；推迟任务需在 Issue、路线图和交付中保留原因，不能将未实现卡改为 done。

## 总看板

<!-- task-board:start -->
| 任务ID | 任务 | 状态 | 依赖 | 关联Issue | 交付文档 |
|---|---|---|---|---|---|
| [FE-M0-T01](tasks/FE-M0.md#fe-m0-t01) | 仓库整理与原型编辑锁修复 | done | — | [ISSUE-002](../issues/ISSUE-002.md) | [交付](delivery/FE-M0-T01.md) |
| [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | 任务治理与交付闭环 | done | [FE-M0-T01](tasks/FE-M0.md#fe-m0-t01) | [ISSUE-003](../issues/ISSUE-003.md) | [交付](delivery/FE-M0-T02.md) |
| [FE-M0-T03](tasks/FE-M0.md#fe-m0-t03) | 评审系统与前端来源边界 | in-progress | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-005](../issues/ISSUE-005.md) | `docs/delivery/FE-M0-T03.md` |
| [FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | 确认选型与首批接口边界（superseded-by-WP，已收口至 /api/v1 契约；禁止重建；仅允许补交付/验收） | cancelled | [FE-M0-T03](tasks/FE-M0.md#fe-m0-t03) | [ISSUE-005](../issues/ISSUE-005.md) | `docs/delivery/FE-M0-T04.md` |
| [FE-M0-T05](tasks/FE-M0.md#fe-m0-t05) | 建立正式前端最小运行工程（superseded-by-WP，八域工程已建立；禁止重建；仅允许补交付/验收） | cancelled | [FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | [ISSUE-038](../issues/ISSUE-038.md) | `docs/delivery/FE-M0-T05.md` |
| [FE-M0-T06](tasks/FE-M0.md#fe-m0-t06) | 登录与权限导航最小接入（superseded-by-WP，凭据登录与8角色已落地；禁止重建；仅允许补交付/验收） | cancelled | [FE-M0-T05](tasks/FE-M0.md#fe-m0-t05)、[FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | [ISSUE-038](../issues/ISSUE-038.md) | `docs/delivery/FE-M0-T06.md` |
| [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07) | 全局与项目 Shell 及路由（superseded-by-WP，shell/ 与 app/ 已建立；禁止重建；仅允许补交付/验收） | cancelled | [FE-M0-T05](tasks/FE-M0.md#fe-m0-t05)、[FE-M0-T06](tasks/FE-M0.md#fe-m0-t06) | [ISSUE-038](../issues/ISSUE-038.md) | `docs/delivery/FE-M0-T07.md` |
| [FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | API 客户端与错误审计通路（superseded-by-WP，api.ts 与统一错误体已落地；禁止重建；仅允许补交付/验收） | cancelled | [FE-M0-T04](tasks/FE-M0.md#fe-m0-t04)、[FE-M0-T05](tasks/FE-M0.md#fe-m0-t05) | [ISSUE-038](../issues/ISSUE-038.md) | `docs/delivery/FE-M0-T08.md` |
| [FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | 基础组件与离线资源（superseded-by-WP，shared/ 与组件已建立；禁止重建；仅允许补交付/验收） | cancelled | [FE-M0-T05](tasks/FE-M0.md#fe-m0-t05)、[FE-M0-T07](tasks/FE-M0.md#fe-m0-t07) | [ISSUE-038](../issues/ISSUE-038.md) | `docs/delivery/FE-M0-T09.md` |
| [FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | 统一长任务状态组件（superseded-by-WP，status/JobProgress 与 SSE 已落地；禁止重建；仅允许补交付/验收） | cancelled | [FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | [ISSUE-038](../issues/ISSUE-038.md) | `docs/delivery/FE-M0-T10.md` |
| [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01) | 项目列表与创建入口 | blocked | [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | — | `docs/delivery/FE-M1-T01.md` |
| [FE-M1-T02](tasks/FE-M1.md#fe-m1-t02) | 项目概览与分册风险 | blocked | [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M1-T02.md` |
| [FE-M1-T03](tasks/FE-M1.md#fe-m1-t03) | 招标文件上传与解析任务 | blocked | [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M1-T03.md` |
| [FE-M1-T04](tasks/FE-M1.md#fe-m1-t04) | 原文查看与页码定位 | blocked | [FE-M1-T03](tasks/FE-M1.md#fe-m1-t03) | — | `docs/delivery/FE-M1-T04.md` |
| [FE-M1-T05](tasks/FE-M1.md#fe-m1-t05) | 解析后处理与确认门 | blocked | [FE-M1-T03](tasks/FE-M1.md#fe-m1-t03)、[FE-M1-T04](tasks/FE-M1.md#fe-m1-t04)、[FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | — | `docs/delivery/FE-M1-T05.md` |
| [FE-M1-T06](tasks/FE-M1.md#fe-m1-t06) | 响应矩阵最小编辑与证据 | blocked | [FE-M1-T05](tasks/FE-M1.md#fe-m1-t05)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M1-T06.md` |
| [FE-M1-T07](tasks/FE-M1.md#fe-m1-t07) | 项目事实编辑与确认 | blocked | [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M1-T05](tasks/FE-M1.md#fe-m1-t05)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M1-T07.md` |
| [FE-M2-T01](tasks/FE-M2.md#fe-m2-t01) | 章节树与状态导航 | blocked | [FE-M1-T06](tasks/FE-M1.md#fe-m1-t06)、[FE-M0-T07](tasks/FE-M0.md#fe-m0-t07) | — | `docs/delivery/FE-M2-T01.md` |
| [FE-M2-T02](tasks/FE-M2.md#fe-m2-t02) | 写作方案查看确认与启动 | blocked | [FE-M2-T01](tasks/FE-M2.md#fe-m2-t01)、[FE-M1-T07](tasks/FE-M1.md#fe-m1-t07)、[FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | — | `docs/delivery/FE-M2-T02.md` |
| [FE-M2-T03](tasks/FE-M2.md#fe-m2-t03) | 生成轮次与长任务 Timeline | blocked | [FE-M2-T02](tasks/FE-M2.md#fe-m2-t02)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M2-T03.md` |
| [FE-M2-T04](tasks/FE-M2.md#fe-m2-t04) | 检查与定位修正结果 | blocked | [FE-M2-T03](tasks/FE-M2.md#fe-m2-t03)、[FE-M1-T04](tasks/FE-M1.md#fe-m1-t04) | — | `docs/delivery/FE-M2-T04.md` |
| [FE-M2-T05](tasks/FE-M2.md#fe-m2-t05) | 停止条件与人工处理交接 | blocked | [FE-M2-T04](tasks/FE-M2.md#fe-m2-t04)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M2-T05.md` |
| [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01) | 编辑文档模型与段落元数据 | blocked | [FE-M0-T04](tasks/FE-M0.md#fe-m0-t04)、[FE-M0-T05](tasks/FE-M0.md#fe-m0-t05)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M3-T01.md` |
| [FE-M3-T02](tasks/FE-M3.md#fe-m3-t02) | 长文基础编辑与只读保护 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | — | `docs/delivery/FE-M3-T02.md` |
| [FE-M3-T03](tasks/FE-M3.md#fe-m3-t03) | 草稿自动保存与并发冲突 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M3-T03.md` |
| [FE-M3-T04](tasks/FE-M3.md#fe-m3-t04) | 真实编辑锁与心跳接管 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M0-T06](tasks/FE-M0.md#fe-m0-t06)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M3-T04.md` |
| [FE-M3-T05](tasks/FE-M3.md#fe-m3-t05) | 段落来源与问题抽屉 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M1-T04](tasks/FE-M1.md#fe-m1-t04)、[FE-M1-T07](tasks/FE-M1.md#fe-m1-t07) | — | `docs/delivery/FE-M3-T05.md` |
| [FE-M3-T06](tasks/FE-M3.md#fe-m3-t06) | 普通问答与结构化答案卡 | blocked | [FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M1-T07](tasks/FE-M1.md#fe-m1-t07)、[FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M3-T06.md` |
| [FE-M3-T07](tasks/FE-M3.md#fe-m3-t07) | 选区样例与上下文快照 | blocked | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M3-T04](tasks/FE-M3.md#fe-m3-t04)、[FE-M3-T06](tasks/FE-M3.md#fe-m3-t06) | — | `docs/delivery/FE-M3-T07.md` |
| [FE-M3-T08](tasks/FE-M3.md#fe-m3-t08) | Diff 确认与安全写入 | blocked | [FE-M3-T07](tasks/FE-M3.md#fe-m3-t07)、[FE-M3-T03](tasks/FE-M3.md#fe-m3-t03)、[FE-M3-T04](tasks/FE-M3.md#fe-m3-t04) | — | `docs/delivery/FE-M3-T08.md` |
| [FE-M3-T09](tasks/FE-M3.md#fe-m3-t09) | 版本比较与回退 | blocked | [FE-M3-T03](tasks/FE-M3.md#fe-m3-t03)、[FE-M3-T04](tasks/FE-M3.md#fe-m3-t04)、[FE-M3-T08](tasks/FE-M3.md#fe-m3-t08) | — | `docs/delivery/FE-M3-T09.md` |
| [FE-M4-T01](tasks/FE-M4.md#fe-m4-t01) | 检查中心筛选与问题定位 | blocked | [FE-M0-T10](tasks/FE-M0.md#fe-m0-t10)、[FE-M3-T05](tasks/FE-M3.md#fe-m3-t05) | — | `docs/delivery/FE-M4-T01.md` |
| [FE-M4-T02](tasks/FE-M4.md#fe-m4-t02) | 编辑后增量复查反馈 | blocked | [FE-M3-T08](tasks/FE-M3.md#fe-m3-t08)、[FE-M4-T01](tasks/FE-M4.md#fe-m4-t01) | — | `docs/delivery/FE-M4-T02.md` |
| [FE-M4-T03](tasks/FE-M4.md#fe-m4-t03) | 分册检查定稿与解锁 | blocked | [FE-M4-T01](tasks/FE-M4.md#fe-m4-t01)、[FE-M2-T05](tasks/FE-M2.md#fe-m2-t05)、[FE-M3-T09](tasks/FE-M3.md#fe-m3-t09) | — | `docs/delivery/FE-M4-T03.md` |
| [FE-M4-T04](tasks/FE-M4.md#fe-m4-t04) | 全文检查与跨分册门禁 | blocked | [FE-M4-T03](tasks/FE-M4.md#fe-m4-t03)、[FE-M1-T06](tasks/FE-M1.md#fe-m1-t06) | — | `docs/delivery/FE-M4-T04.md` |
| [FE-M4-T05](tasks/FE-M4.md#fe-m4-t05) | 内部稿与递交版导出入口 | blocked | [FE-M4-T04](tasks/FE-M4.md#fe-m4-t04)、[FE-M0-T06](tasks/FE-M0.md#fe-m0-t06)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M4-T05.md` |
| [FE-M4-T06](tasks/FE-M4.md#fe-m4-t06) | 导出历史下载与版式核对 | blocked | [FE-M4-T05](tasks/FE-M4.md#fe-m4-t05) | — | `docs/delivery/FE-M4-T06.md` |
| [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | 资料库列表与治理状态 | blocked | [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | — | `docs/delivery/FE-M5-T01.md` |
| [FE-M5-T02](tasks/FE-M5.md#fe-m5-t02) | 主体资质与附件表单切片 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M5-T02.md` |
| [FE-M5-T03](tasks/FE-M5.md#fe-m5-t03) | 人员证书与授权关联 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01)、[FE-M5-T02](tasks/FE-M5.md#fe-m5-t02) | — | `docs/delivery/FE-M5-T03.md` |
| [FE-M5-T04](tasks/FE-M5.md#fe-m5-t04) | 业绩与能力资料首批视图 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01)、[FE-M5-T02](tasks/FE-M5.md#fe-m5-t02) | — | `docs/delivery/FE-M5-T04.md` |
| [FE-M5-T05](tasks/FE-M5.md#fe-m5-t05) | 方案片段与历史参考管理 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01)、[FE-M1-T04](tasks/FE-M1.md#fe-m1-t04) | — | `docs/delivery/FE-M5-T05.md` |
| [FE-M5-T06](tasks/FE-M5.md#fe-m5-t06) | 公司写作档案与模板风格 | blocked | [FE-M5-T01](tasks/FE-M5.md#fe-m5-t01)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08) | — | `docs/delivery/FE-M5-T06.md` |
| [FE-M5-T07](tasks/FE-M5.md#fe-m5-t07) | 任务卡版本与模型参数管理 | blocked | [FE-M5-T06](tasks/FE-M5.md#fe-m5-t06)、[FE-M0-T04](tasks/FE-M0.md#fe-m0-t04) | — | `docs/delivery/FE-M5-T07.md` |
| [FE-M5-T08](tasks/FE-M5.md#fe-m5-t08) | 用户角色与公司设置 | blocked | [FE-M0-T06](tasks/FE-M0.md#fe-m0-t06)、[FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M5-T08.md` |
| [FE-M5-T09](tasks/FE-M5.md#fe-m5-t09) | 站内提醒与一期全局搜索 | blocked | [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07)、[FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M5-T01](tasks/FE-M5.md#fe-m5-t01) | — | `docs/delivery/FE-M5-T09.md` |
| [FE-M5-T10](tasks/FE-M5.md#fe-m5-t10) | 规则配置与兜底扫描版本 | blocked | [FE-M0-T08](tasks/FE-M0.md#fe-m0-t08)、[FE-M5-T08](tasks/FE-M5.md#fe-m5-t08)、[FE-M1-T05](tasks/FE-M1.md#fe-m1-t05) | — | `docs/delivery/FE-M5-T10.md` |
| [FE-M5-T11](tasks/FE-M5.md#fe-m5-t11) | 服务状态品牌与任务中心入口 | blocked | [FE-M0-T10](tasks/FE-M0.md#fe-m0-t10)、[FE-M5-T08](tasks/FE-M5.md#fe-m5-t08)、[FE-M0-T09](tasks/FE-M0.md#fe-m0-t09) | — | `docs/delivery/FE-M5-T11.md` |
| [FE-M6-T01](tasks/FE-M6.md#fe-m6-t01) | 章节负责人分派与待办 | planned | [FE-M2-T01](tasks/FE-M2.md#fe-m2-t01)、[FE-M5-T08](tasks/FE-M5.md#fe-m5-t08) | — | `docs/delivery/FE-M6-T01.md` |
| [FE-M6-T02](tasks/FE-M6.md#fe-m6-t02) | 评论批注与提及解决 | planned | [FE-M3-T01](tasks/FE-M3.md#fe-m3-t01)、[FE-M3-T05](tasks/FE-M3.md#fe-m3-t05)、[FE-M5-T09](tasks/FE-M5.md#fe-m5-t09) | — | `docs/delivery/FE-M6-T02.md` |
| [FE-M6-T03](tasks/FE-M6.md#fe-m6-t03) | 知识引用地图 | planned | [FE-M3-T05](tasks/FE-M3.md#fe-m3-t05)、[FE-M5-T05](tasks/FE-M5.md#fe-m5-t05) | — | `docs/delivery/FE-M6-T03.md` |
| [FE-M6-T04](tasks/FE-M6.md#fe-m6-t04) | 项目模板复制 | planned | [FE-M1-T01](tasks/FE-M1.md#fe-m1-t01)、[FE-M1-T06](tasks/FE-M1.md#fe-m1-t06)、[FE-M5-T06](tasks/FE-M5.md#fe-m5-t06) | — | `docs/delivery/FE-M6-T04.md` |
| [FE-M7-T01](tasks/FE-M7.md#fe-m7-t01) | 快捷命令与跳转 | planned | [FE-M0-T07](tasks/FE-M0.md#fe-m0-t07)、[FE-M5-T09](tasks/FE-M5.md#fe-m5-t09) | — | `docs/delivery/FE-M7-T01.md` |
| [FE-M7-T02](tasks/FE-M7.md#fe-m7-t02) | 能力与写作质量指标视图 | planned | [FE-M5-T04](tasks/FE-M5.md#fe-m5-t04)、[FE-M5-T06](tasks/FE-M5.md#fe-m5-t06)、[FE-M2-T03](tasks/FE-M2.md#fe-m2-t03) | — | `docs/delivery/FE-M7-T02.md` |
| [FE-M7-T03](tasks/FE-M7.md#fe-m7-t03) | 历史复用推荐预览 | planned | [FE-M5-T05](tasks/FE-M5.md#fe-m5-t05)、[FE-M3-T07](tasks/FE-M3.md#fe-m3-t07)、[FE-M3-T08](tasks/FE-M3.md#fe-m3-t08) | — | `docs/delivery/FE-M7-T03.md` |
| [FE-M7-T04](tasks/FE-M7.md#fe-m7-t04) | 高频批量操作 | planned | [FE-M1-T06](tasks/FE-M1.md#fe-m1-t06)、[FE-M2-T02](tasks/FE-M2.md#fe-m2-t02)、[FE-M0-T10](tasks/FE-M0.md#fe-m0-t10) | — | `docs/delivery/FE-M7-T04.md` |
| [FE-M8-T01](tasks/FE-M8.md#fe-m8-t01) | 一期完整主链路联调 | blocked | [FE-M1-T07](tasks/FE-M1.md#fe-m1-t07)、[FE-M2-T05](tasks/FE-M2.md#fe-m2-t05)、[FE-M3-T09](tasks/FE-M3.md#fe-m3-t09)、[FE-M4-T06](tasks/FE-M4.md#fe-m4-t06)、[FE-M5-T07](tasks/FE-M5.md#fe-m5-t07)、[FE-M5-T08](tasks/FE-M5.md#fe-m5-t08)、[FE-M5-T09](tasks/FE-M5.md#fe-m5-t09)、[FE-M5-T10](tasks/FE-M5.md#fe-m5-t10)、[FE-M5-T11](tasks/FE-M5.md#fe-m5-t11) | — | `docs/delivery/FE-M8-T01.md` |
| [FE-M8-T02](tasks/FE-M8.md#fe-m8-t02) | 安全离线长文与恢复验证 | blocked | [FE-M0-T09](tasks/FE-M0.md#fe-m0-t09)、[FE-M3-T02](tasks/FE-M3.md#fe-m3-t02)、[FE-M3-T03](tasks/FE-M3.md#fe-m3-t03)、[FE-M3-T04](tasks/FE-M3.md#fe-m3-t04)、[FE-M4-T05](tasks/FE-M4.md#fe-m4-t05)、[FE-M8-T01](tasks/FE-M8.md#fe-m8-t01) | — | `docs/delivery/FE-M8-T02.md` |
| [FE-M8-T03](tasks/FE-M8.md#fe-m8-t03) | 版本发布与交付资料封版 | blocked | [FE-M8-T01](tasks/FE-M8.md#fe-m8-t01)、[FE-M8-T02](tasks/FE-M8.md#fe-m8-t02)、[FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | — | `docs/delivery/FE-M8-T03.md` |
| [OPS-M0-T01](tasks/OPS-M0.md#ops-m0-t01) | 全工作区云端同步 | done | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-004](../issues/ISSUE-004.md) | [交付](delivery/OPS-M0-T01.md) |
| [OPS-M0-T02](tasks/OPS-M0.md#ops-m0-t02) | 内网部署草案 | done | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-017](../issues/ISSUE-017.md) | [交付](delivery/OPS-M0-T02.md) |
| [REV-M0-T01](tasks/REV-M0.md#rev-m0-t01) | 目录、业务与技术审查及brief | done | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-004](../issues/ISSUE-004.md) | [交付](delivery/REV-M0-T01.md) |
| [REV-M0-T02](tasks/REV-M0.md#rev-m0-t02) | QA独立复跑与会话真实HTTP复核入库 | done | [APP-M2-T001](tasks/APP-M2.md#app-m2-t001) | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T02.md) |
| [REV-M0-T03](tasks/REV-M0.md#rev-m0-t03) | APP-M1-T06端到端验收计划 | done | [APP-M1-T06](tasks/APP-M1.md#app-m1-t06) | [ISSUE-015](../issues/ISSUE-015.md) | [交付](delivery/REV-M0-T03.md) |
| [REV-M0-T04](tasks/REV-M0.md#rev-m0-t04) | T06贯通冒烟与Word渲染 | done | [REV-M0-T03](tasks/REV-M0.md#rev-m0-t03) | [ISSUE-015](../issues/ISSUE-015.md) | [交付](delivery/REV-M0-T04.md) |
| [REV-M0-T05](tasks/REV-M0.md#rev-m0-t05) | APP-M2-T008与AI-02 QA签署复核 | done | APP-M2-T008、AI-02 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T05.md) |
| [REV-M0-T07](tasks/REV-M0.md#rev-m0-t07) | BE-M0-T02与BE-M0-T03 QA签署复核 | done | BE-M0-T02、BE-M0-T03 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T07.md) |
| [REV-M0-T09](tasks/REV-M0.md#rev-m0-t09) | BE-M0-T08与BE-M0-T10 QA签署复核 | done | BE-M0-T08、BE-M0-T10 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T09.md) |
| [REV-M0-T10](tasks/REV-M0.md#rev-m0-t10) | BE-M0-T15 Word 默认版式 QA 签署复核 | done | BE-M0-T15 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T10.md) |
| [REV-M0-T11](tasks/REV-M0.md#rev-m0-t11) | APP-M2-T001与APP-M2-T002 QA复验签署 | done | APP-M2-T001、APP-M2-T002 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T11.md) |
| [REV-M0-T12](tasks/REV-M0.md#rev-m0-t12) | BE-M0-T14 托管 MySQL CI QA签署 | done | BE-M0-T14 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T12.md) |
| [REV-M0-T13](tasks/REV-M0.md#rev-m0-t13) | ISSUE-026 基线快照规则 QA签署 | done | ISSUE-026 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T13.md) |
| [REV-M0-T14](tasks/REV-M0.md#rev-m0-t14) | ISSUE-014 ProLayout依赖与体积 QA签署 | done | ISSUE-014 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T14.md) |
| [REV-M0-T15](tasks/REV-M0.md#rev-m0-t15) | ISSUE-020 路由分包 QA签署 | done | ISSUE-020 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T15.md) |
| [REV-M0-T16](tasks/REV-M0.md#rev-m0-t16) | ISSUE-016 检索层内存骨架 QA签署 | done | ISSUE-016、AI-03 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T16.md) |
| [REV-M0-T17](tasks/REV-M0.md#rev-m0-t17) | ISSUE-028 配置驱动对话模型设计 QA签署 | done | ISSUE-028 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T17.md) |
| [REV-M0-T18](tasks/REV-M0.md#rev-m0-t18) | ISSUE-031错误码名单冻结 QA签署 | done | ISSUE-031 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T18.md) |
| [REV-M0-T19](tasks/REV-M0.md#rev-m0-t19) | BE-M0-T12编辑租约入库 QA签署 | done | BE-M0-T12、ISSUE-018 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T19.md) |
| [REV-M0-T20](tasks/REV-M0.md#rev-m0-t20) | ISSUE-022契约冻结 QA复签 | done | ISSUE-022 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T20.md) |
| [REV-M0-T21](tasks/REV-M0.md#rev-m0-t21) | 0a5b655请求层重试修复 QA签署 | done | ISSUE-030 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T21.md) |
| [REV-M0-T22](tasks/REV-M0.md#rev-m0-t22) | APP-M2-T114 e691405 冲突刷新 QA签署 | done | APP-M2-T114 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T22.md) |
| [REV-M0-T23](tasks/REV-M0.md#rev-m0-t23) | BE-M0-T13项目聚合入库 QA签署 | done | BE-M0-T13、ISSUE-018 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T23.md) |
| [REV-M0-T24](tasks/REV-M0.md#rev-m0-t24) | APP-M2-T078 内存片段发布 QA签署 | done | APP-M2-T078、ISSUE-022 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T24.md) |
| [REV-M0-T25](tasks/REV-M0.md#rev-m0-t25) | ISSUE-036 橙色标签对比 QA签署 | in-review | ISSUE-036 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T25.md) |
| [REV-M0-T26](tasks/REV-M0.md#rev-m0-t26) | ISSUE-033 规格增量契约复签 | in-review | ISSUE-033 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T26.md) |
| [REV-M0-T27](tasks/REV-M0.md#rev-m0-t27) | 最新分支复核与限定修复 | in-review | tip `5eced4f`；QA R1～R9 已签（含真实 MySQL） | [ISSUE-034](../issues/ISSUE-034.md) | [交付](delivery/REV-M0-T27.md) |
| [REV-M0-T28](tasks/REV-M0.md#rev-m0-t28) | BE-M0-T11 回执与会话入库 QA签署 | in-review | BE-M0-T11 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T28.md) |
| [REV-M0-T29](tasks/REV-M0.md#rev-m0-t29) | ISSUE-028 AC-02 假端点夹具 QA签署 | in-review | ISSUE-028 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T29.md) |
| [REV-M0-T30](tasks/REV-M0.md#rev-m0-t30) | ISSUE-028 AC-03 OpenAPI/依赖/演示替身 QA签署 | in-review | ISSUE-028 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T30.md) |
| [REV-M0-T31](tasks/REV-M0.md#rev-m0-t31) | 最新增量复核与验证标记 | in-review | b7b3191及PR #4 / 9986747 | [ISSUE-034](../issues/ISSUE-034.md) | [交付](delivery/REV-M0-T31.md) |
| [REV-M0-T32](tasks/REV-M0.md#rev-m0-t32) | BE-M0-T04 编辑租约 v1 QA签署 | in-review | BE-M0-T04 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T32.md) |
| [REV-M0-T33](tasks/REV-M0.md#rev-m0-t33) | BE-M0-T05 导出快照 QA签署 | in-review | BE-M0-T05 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T33.md) |
| [REV-M0-T34](tasks/REV-M0.md#rev-m0-t34) | BE-M0-T16 错误码名字冻结 QA签署 | in-review | BE-M0-T16 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T34.md) |
| [REV-M0-T35](tasks/REV-M0.md#rev-m0-t35) | BE-M0-T18 / ISSUE-033 挂证据运行时 QA签署 | in-review | BE-M0-T18、ISSUE-033 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T35.md) |
| [REV-M0-T36](tasks/REV-M0.md#rev-m0-t36) | BE-M0-T06 可恢复任务 QA签署 | in-review | BE-M0-T06 | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T36.md) |
| [REV-M0-T06](tasks/REV-M0.md#rev-m0-t06) | Playwright浏览器端到端检查 | in-review | [APP-M2-T001](tasks/APP-M2.md#app-m2-t001) | [ISSUE-019](../issues/ISSUE-019.md) | [交付](delivery/REV-M0-T06.md) |
| [REV-M0-T08](tasks/REV-M0.md#rev-m0-t08) | APP-M2-T001 QA签署复核 | in-review | [REV-M0-T06](tasks/REV-M0.md#rev-m0-t06) | [ISSUE-013](../issues/ISSUE-013.md) | [交付](delivery/REV-M0-T08.md) |
| [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | 后端开发准备与本地demo | done | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02) | [ISSUE-006](../issues/ISSUE-006.md) | [交付](delivery/BE-M0-T01.md) |
| [BE-M0-T02](tasks/BE-M0.md#be-m0-t02) | v1统一错误体与HTTP状态码表 | done | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-005](../issues/ISSUE-005.md) | [交付](delivery/BE-M0-T02.md) |
| [BE-M0-T03](tasks/BE-M0.md#be-m0-t03) | v1幂等键与24小时回执 | done | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02) | [ISSUE-005](../issues/ISSUE-005.md) | [交付](delivery/BE-M0-T03.md) |
| [BE-M0-T04](tasks/BE-M0.md#be-m0-t04) | 编辑租约迁到 /api/v1 | in-review | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02)、[BE-M0-T03](tasks/BE-M0.md#be-m0-t03) | [ISSUE-005](../issues/ISSUE-005.md) | [交付](delivery/BE-M0-T04.md) |
| [BE-M0-T05](tasks/BE-M0.md#be-m0-t05) | 导出快照语义 | in-review | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02)、[BE-M0-T03](tasks/BE-M0.md#be-m0-t03) | [ISSUE-005](../issues/ISSUE-005.md) | [交付](delivery/BE-M0-T05.md) |
| [BE-M0-T06](tasks/BE-M0.md#be-m0-t06) | 可恢复任务（202 与 SSE） | in-review | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02)、[BE-M0-T03](tasks/BE-M0.md#be-m0-t03) | [ISSUE-005](../issues/ISSUE-005.md) | [交付](delivery/BE-M0-T06.md) |
| [BE-M0-T07](tasks/BE-M0.md#be-m0-t07) | operationId 检查 | in-review | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02) | [ISSUE-005](../issues/ISSUE-005.md) | [交付](delivery/BE-M0-T07.md) |
| [BE-M0-T08](tasks/BE-M0.md#be-m0-t08) | MySQL 8 持久化方案 | done | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-018](../issues/ISSUE-018.md) | [交付](delivery/BE-M0-T08.md) |
| [BE-M0-T09](tasks/BE-M0.md#be-m0-t09) | 旧 /api 统一错误体与幂等 | planned | [BE-M0-T08](tasks/BE-M0.md#be-m0-t08) | [ISSUE-021](../issues/ISSUE-021.md) | `docs/delivery/BE-M0-T09.md` |
| [BE-M0-T10](tasks/BE-M0.md#be-m0-t10) | 连接配置与迁移骨架 | done | [BE-M0-T08](tasks/BE-M0.md#be-m0-t08) | [ISSUE-023](../issues/ISSUE-023.md) | [交付](delivery/BE-M0-T10.md) |
| [BE-M0-T11](tasks/BE-M0.md#be-m0-t11) | 幂等回执与登录会话入库 | done | [BE-M0-T10](tasks/BE-M0.md#be-m0-t10) | [ISSUE-018](../issues/ISSUE-018.md) | [交付](delivery/BE-M0-T11.md) |
| [BE-M0-T12](tasks/BE-M0.md#be-m0-t12) | 编辑租约入库 | done | [BE-M0-T11](tasks/BE-M0.md#be-m0-t11) | [ISSUE-018](../issues/ISSUE-018.md) | [交付](delivery/BE-M0-T12.md) |
| [BE-M0-T13](tasks/BE-M0.md#be-m0-t13) | 按聚合迁移仓库 | done | [BE-M0-T12](tasks/BE-M0.md#be-m0-t12) | [ISSUE-018](../issues/ISSUE-018.md) | [交付](delivery/BE-M0-T13.md) |
| [BE-M0-T14](tasks/BE-M0.md#be-m0-t14) | 托管 MySQL CI 作业 | done | [BE-M0-T10](tasks/BE-M0.md#be-m0-t10) | [ISSUE-025](../issues/ISSUE-025.md) | [交付](delivery/BE-M0-T14.md) |
| [BE-M0-T15](tasks/BE-M0.md#be-m0-t15) | Word 导出默认版式 | done | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/BE-M0-T15.md) |
| [BE-M0-T16](tasks/BE-M0.md#be-m0-t16) | 冻结错误码名字 | in-review | [BE-M0-T02](tasks/BE-M0.md#be-m0-t02) | [ISSUE-031](../issues/ISSUE-031.md) | [交付](delivery/BE-M0-T16.md) |
| [BE-M0-T17](tasks/BE-M0.md#be-m0-t17) | chapter_lease 对齐字典 edit_lock | planned | [BE-M0-T13](tasks/BE-M0.md#be-m0-t13) | [ISSUE-032](../issues/ISSUE-032.md) | `docs/delivery/BE-M0-T17.md` |
| [BE-M0-T18](tasks/BE-M0.md#be-m0-t18) | 挂证据拒绝过期、缺协议和受限资料 | in-review | [BE-M0-T13](tasks/BE-M0.md#be-m0-t13) | [ISSUE-033](../issues/ISSUE-033.md) | [交付](delivery/BE-M0-T18.md) |
| [BE-M0-T19](tasks/BE-M0.md#be-m0-t19) | demo_project 对齐字典 bid_project | in-review | [BE-M0-T13](tasks/BE-M0.md#be-m0-t13) | [ISSUE-035](../issues/ISSUE-035.md) | [BE-M0-T19](delivery/BE-M0-T19.md) |
| [BE-CHECKS-EXPORT-ALIGN](tasks/BE-M0.md#be-checks-export-align) | 检查阻断红线与整本导出快照版式核对 | in-review | [BE-M0-T15](tasks/BE-M0.md#be-m0-t15) | [ISSUE-006](../issues/ISSUE-006.md)；[ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/BE-CHECKS-EXPORT-ALIGN.md) |
| [BE-VOLUME-FINALIZE-GATE](tasks/BE-M0.md#be-volume-finalize-gate) | 分册定稿状态机与前置检查门禁 | in-review | [BE-CHECKS-EXPORT-ALIGN](tasks/BE-M0.md#be-checks-export-align) | [ISSUE-006](../issues/ISSUE-006.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/BE-VOLUME-FINALIZE-GATE.md) |
| [BE-COMPLIANCE-RULES-P0](tasks/BE-M0.md#be-compliance-rules-p0) | 核心合规规则补齐（R01/R02/R15/R23/R34/R35/R37等） | done | [BE-CHECKS-EXPORT-ALIGN](tasks/BE-M0.md#be-checks-export-align) | [ISSUE-006](../issues/ISSUE-006.md)、[ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/BE-COMPLIANCE-RULES-P0.md) |
| [BE-SUBMISSION-FINALIZE-GATE](delivery/2026-10-23-submission-rules-finalize-gate.md) | 规则最小可递交集与分册定稿闸门端到端闭环 | in-review | [BE-VOLUME-FINALIZE-GATE](tasks/BE-M0.md#be-volume-finalize-gate)、[BE-COMPLIANCE-RULES-P0](tasks/BE-M0.md#be-compliance-rules-p0) | [ISSUE-006](../issues/ISSUE-006.md)、[ISSUE-007](../issues/ISSUE-007.md)、[ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/2026-10-23-submission-rules-finalize-gate.md) |
| [APP-M1-T01](tasks/APP-M1.md#app-m1-t01) | 示例外壳与项目工作台 | in-progress | BE-M0-T01 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T01.md` |
| [APP-M1-T02](tasks/APP-M1.md#app-m1-t02) | 上传解析与确认 | in-progress | APP-M1-T01工作区接口 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T02.md` |
| [APP-M1-T03](tasks/APP-M1.md#app-m1-t03) | 矩阵事实与证据 | in-progress | APP-M1-T02条款结构 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T03.md` |
| [APP-M1-T04](tasks/APP-M1.md#app-m1-t04) | 大纲章节与示例编辑台 | in-progress | APP-M1-T03映射接口 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T04.md` |
| [APP-M1-T05](tasks/APP-M1.md#app-m1-t05) | 检查与两册输出 | in-progress | APP-M1-T03/04数据结构 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T05.md` |
| [APP-M1-T06](tasks/APP-M1.md#app-m1-t06) | 核心流程端到端验收 | in-progress | APP-M1-T01～05 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T06.md` |
| [APP-M1-T07](tasks/APP-M1.md#app-m1-t07) | 其他页面和完整规则拆分 | done | 核心结构验证 | [ISSUE-007](../issues/ISSUE-007.md) | [本地交付](delivery/APP-M1-T07.md) |
| [APP-M1-T08](tasks/APP-M1.md#app-m1-t08) | 完整示例交付审计 | planned | 核心与后续任务完成 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M1-T08.md` |
| [APP-M1-T09](tasks/APP-M1.md#app-m1-t09) | 服务承诺模板与公司能力 | done | 公司资料接口已接通 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T09.md) |
| [APP-M1-T10](tasks/APP-M1.md#app-m1-t10) | 三方对照、判断与事实引用 | done | T09模板、T03原文要求 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T10.md) |
| [APP-M1-T11](tasks/APP-M1.md#app-m1-t11) | 承诺变量、检查与承诺函 | done | T10取值、T04/05正文输出 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T11.md) |
| [APP-M1-T12](tasks/APP-M1.md#app-m1-t12) | 本章事实写作输入与保护 | done | T03/10事实、T04方案接口 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T12.md) |
| [APP-M1-T13](tasks/APP-M1.md#app-m1-t13) | 本章方案与候选来源预览 | done | T12共同字段、现有编辑台 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M1-T13.md) |
| [APP-M1-T14](tasks/APP-M1.md#app-m1-t14) | 项目成员与分册分工 | done | T01项目、T04章节、T12方案 | [ISSUE-007](../issues/ISSUE-007.md) | [本地交付](delivery/APP-M1-T14.md) |
| [APP-M1-T15](tasks/APP-M1.md#app-m1-t15) | 逐章分工与独立方案确认 | done | T14成员分册、T12输入 | [ISSUE-007](../issues/ISSUE-007.md) | [本地交付](delivery/APP-M1-T15.md) |
| [APP-M1-T16](tasks/APP-M1.md#app-m1-t16) | 资料库旧表单依据保护 | done | 已有公司资料版本接口；T14/15保护经验 | [ISSUE-008](../issues/ISSUE-008.md) | [交付](delivery/APP-M1-T16.md) |
| [APP-M2-T001](tasks/APP-M2.md#app-m2-t001) | ProLayout 布局、路由、权限守卫、请求层 | done | BE-M0-T01 | [ISSUE-009](../issues/ISSUE-009.md) | [交付](delivery/APP-M2-T001.md) |
| [APP-M2-T002](tasks/APP-M2.md#app-m2-t002) | 请求层细化：错误体、traceId 复制、Idempotency-Key 注入、重试策略 | done | BE-M0-T01、BE-M0-T02、BE-M0-T03、APP-M2-T001 | [ISSUE-009](../issues/ISSUE-009.md) | [交付](delivery/APP-M2-T002.md) |
| [APP-M2-T003](tasks/APP-M2.md#app-m2-t003) | 通用状态组件（骨架、空态、错误、无权限、已过期、只读） | in-review | BE-M0-T01、APP-M2-T001 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T003.md) |
| [APP-M2-T004](tasks/APP-M2.md#app-m2-t004) | 业务小组件：LevelTag、AiTag、DirectTag、Cite、SourceBar | in-review | BE-M0-T01、APP-M2-T003 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T004.md) |
| [APP-M2-T005](tasks/APP-M2.md#app-m2-t005) | 元数据驱动表格（ProTable 封装、列合并、无横滚优先） | in-review | BE-M0-T01、APP-M2-T003、APP-M2-T004 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T005.md) |
| [APP-M2-T006](tasks/APP-M2.md#app-m2-t006) | 元数据驱动表单（★ 字段、系统键两行标签、不支持字段置灰） | in-review | BE-M0-T01、APP-M2-T003 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T006.md) |
| [APP-M2-T007](tasks/APP-M2.md#app-m2-t007) | 表单通用：底部保存条、离开未保存提示、就近报错 | in-review | BE-M0-T01、APP-M2-T006 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T007.md) |
| [APP-M2-T008](tasks/APP-M2.md#app-m2-t008) | 主题运行时接口位与离线检查纳入 CI（应用级） | done | BE-M0-T01、APP-M2-T001 | [ISSUE-012](../issues/ISSUE-012.md) | [交付](delivery/APP-M2-T008.md) |
| [APP-M2-T009](tasks/APP-M2.md#app-m2-t009) | 断点与侧栏记忆（1280 / 1440 / 1680）、面包屑 | in-review | BE-M0-T01、APP-M2-T001 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T009.md) |
| [APP-M2-T010](tasks/APP-M2.md#app-m2-t010) | OIDC 登录跳转、会话续期、401 回登录并返回原页 | planned | APP-M2-T001 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T010.md` |
| [APP-M2-T011](tasks/APP-M2.md#app-m2-t011) | 会话超时处理、用户菜单与退出登录 | planned | APP-M2-T001、APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T011.md` |
| [APP-M2-T012](tasks/APP-M2.md#app-m2-t012) | Keycloak 自定义登录主题（离线；错误、锁定、超时，已有示例卡） | planned | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T012.md` |
| [APP-M2-T013](tasks/APP-M2.md#app-m2-t013) | 登录主题：首次登录强制改密、公司停用提示、读取品牌设置 | planned | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T013.md` |
| [APP-M2-T014](tasks/APP-M2.md#app-m2-t014) | 路由守卫与 403 页 | in-review | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T014.md) |
| [APP-M2-T015](tasks/APP-M2.md#app-m2-t015) | 权限指令 `<Can>` 与按钮隐藏 | in-review | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T015.md) |
| [APP-M2-T016](tasks/APP-M2.md#app-m2-t016) | 数据权限的前端表现：只读态切换（项目 / 分册 / 章节） | in-review | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T016.md) |
| [APP-M2-T017](tasks/APP-M2.md#app-m2-t017) | MaskedField 与“查看完整值”弹窗（原因必填） | in-review | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T017.md) |
| [APP-M2-T018](tasks/APP-M2.md#app-m2-t018) | 掩码规则读取与查看留痕提示 | in-review | APP-M2-T014、APP-M2-T017 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T018.md) |
| [APP-M2-T019](tasks/APP-M2.md#app-m2-t019) | JobProgress：步骤、子进度、AI 紫进度条 | in-review | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T019.md) |
| [APP-M2-T020](tasks/APP-M2.md#app-m2-t020) | JobProgress：SSE 订阅、断线提示与轮询回退 | planned | APP-M2-T014、APP-M2-T019 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T020.md` |
| [APP-M2-T021](tasks/APP-M2.md#app-m2-t021) | 任务中心页基础 + 顶栏任务角标与抽屉 | done | APP-M2-T014、APP-M2-T019、APP-M2-T020 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T021.md) |
| [APP-M2-T022](tasks/APP-M2.md#app-m2-t022) | 平台管理员脱敏视图；从失败步骤重试、取消权限 | done | APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T022.md) |
| [APP-M2-T023](tasks/APP-M2.md#app-m2-t023) | StatusTag 状态注册表（9.3 全部代码表） | done | APP-M2-T005 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T023.md) |
| [APP-M2-T024](tasks/APP-M2.md#app-m2-t024) | A-03 字典配置页 | done | APP-M2-T005 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T024.md) |
| [APP-M2-T025](tasks/APP-M2.md#app-m2-t025) | 扩展字段与公司设置键表单框架 | in-review | APP-M2-T005、APP-M2-T024 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T025.md) |
| [APP-M2-T026](tasks/APP-M2.md#app-m2-t026) | A-01 公司管理 | in-review | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | [APP-M2-T026 交付](delivery/APP-M2-T026.md) |
| [APP-M2-T027](tasks/APP-M2.md#app-m2-t027) | A-02 用户列表、新增、停用前转交；“账号安全设置”面板（公司密码策略，只能调严） | planned | APP-M2-T014、APP-M2-T026 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T027.md` |
| [APP-M2-T028](tasks/APP-M2.md#app-m2-t028) | A-02 角色分配、解锁、重置密码 | planned | APP-M2-T014、APP-M2-T027 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T028.md` |
| [APP-M2-T029](tasks/APP-M2.md#app-m2-t029) | 顶栏铃铛与未读数 | planned | APP-M2-T010 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T029.md` |
| [APP-M2-T030](tasks/APP-M2.md#app-m2-t030) | 提醒下拉：最近 7 条、标已读、全部已读 | planned | APP-M2-T010、APP-M2-T029 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T030.md` |
| [APP-M2-T031](tasks/APP-M2.md#app-m2-t031) | G-02 站内提醒列表页（筛选、已读 / 未读、合并显示） | planned | APP-M2-T029 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T031.md` |
| [APP-M2-T032](tasks/APP-M2.md#app-m2-t032) | 17 类提醒的跳转目标映射与“对象已不存在”提示 | planned | APP-M2-T029、APP-M2-T031 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T032.md` |
| [APP-M2-T033](tasks/APP-M2.md#app-m2-t033) | BrandProvider 运行时主题 + 品牌校验函数（对比度、ΔE） | planned | APP-M2-T008 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T033.md` |
| [APP-M2-T034](tasks/APP-M2.md#app-m2-t034) | A-12 界面品牌页（表单 + 预览 + 恢复默认） | planned | APP-M2-T008、APP-M2-T033 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T034.md` |
| [APP-M2-T035](tasks/APP-M2.md#app-m2-t035) | 全局搜索：顶栏下拉与结果页 | planned | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T035.md` |
| [APP-M2-T036](tasks/APP-M2.md#app-m2-t036) | A-08 模型列表与 `service_status`（用户要求弹窗配置；后端 API 已有、前端未接） | planned | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T036.md` |
| [APP-M2-T037](tasks/APP-M2.md#app-m2-t037) | 模型登记表单与测试连接（用户要求弹窗配置；后端 API 已有、前端未接） | planned | APP-M2-T014、APP-M2-T036 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T037.md` |
| [APP-M2-T038](tasks/APP-M2.md#app-m2-t038) | 模型配置版本与回滚（用户要求弹窗配置；后端 API 已有、前端未接） | planned | APP-M2-T014、APP-M2-T037 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T038.md` |
| [APP-M2-T039](tasks/APP-M2.md#app-m2-t039) | A-09 文档解析服务配置（用户要求弹窗配置；后端 API 已有、前端未接） | planned | APP-M2-T014、APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T039.md` |
| [APP-M2-T040](tasks/APP-M2.md#app-m2-t040) | A-10 任务与模型对应表（用户要求弹窗配置；后端 API 已有、前端未接） | planned | APP-M2-T036 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T040.md` |
| [APP-M2-T041](tasks/APP-M2.md#app-m2-t041) | A-05 公司模型开放（用户要求弹窗配置；后端 API 已有、前端未接） | planned | APP-M2-T036 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T041.md` |
| [APP-M2-T042](tasks/APP-M2.md#app-m2-t042) | A-11 部署与服务状态页 | planned | APP-M2-T036 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T042.md` |
| [APP-M2-T043](tasks/APP-M2.md#app-m2-t043) | CrossFieldHint 组件与 9.11 规则函数 | planned | APP-M2-T025 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T043.md` |
| [APP-M2-T044](tasks/APP-M2.md#app-m2-t044) | A-05 生成闭环参数 | planned | APP-M2-T025、APP-M2-T043 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T044.md` |
| [APP-M2-T045](tasks/APP-M2.md#app-m2-t045) | 编辑台与对话助手参数（自动保存、心跳 15～120、锁超时） | planned | APP-M2-T025、APP-M2-T043 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T045.md` |
| [APP-M2-T046](tasks/APP-M2.md#app-m2-t046) | 资料列表通用页 | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T046.md` |
| [APP-M2-T047](tasks/APP-M2.md#app-m2-t047) | 资料详情通用页（附件槽位、来源） | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T047.md` |
| [APP-M2-T048](tasks/APP-M2.md#app-m2-t048) | 确认 / 审核状态机界面（★ 字段重确认） | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017、APP-M2-T047、APP-M2-T203 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T048.md` |
| [APP-M2-T049](tasks/APP-M2.md#app-m2-t049) | 受限资料与转交 | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017、APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T049.md` |
| [APP-M2-T050](tasks/APP-M2.md#app-m2-t050) | 变更历史与被引用情况 | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017、APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T050.md` |
| [APP-M2-T051](tasks/APP-M2.md#app-m2-t051) | 厂商产品树 | planned | APP-M2-T024 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T051.md` |
| [APP-M2-T052](tasks/APP-M2.md#app-m2-t052) | 证书类别与附件槽位 | planned | APP-M2-T024、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T052.md` |
| [APP-M2-T053](tasks/APP-M2.md#app-m2-t053) | 中小企业划型标准 | planned | APP-M2-T024、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T053.md` |
| [APP-M2-T054](tasks/APP-M2.md#app-m2-t054) | 公司主体（含关联关系） | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T054.md` |
| [APP-M2-T055](tasks/APP-M2.md#app-m2-t055) | 证明材料 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T055.md` |
| [APP-M2-T056](tasks/APP-M2.md#app-m2-t056) | 资质证书 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T056.md` |
| [APP-M2-T057](tasks/APP-M2.md#app-m2-t057) | 安全与合规事件 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T057.md` |
| [APP-M2-T058](tasks/APP-M2.md#app-m2-t058) | 工具与设备 | planned | APP-M2-T047、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T058.md` |
| [APP-M2-T059](tasks/APP-M2.md#app-m2-t059) | 附件库 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T059.md` |
| [APP-M2-T060](tasks/APP-M2.md#app-m2-t060) | 人员列表 | planned | APP-M2-T047、APP-M2-T059 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T060.md` |
| [APP-M2-T061](tasks/APP-M2.md#app-m2-t061) | 人员详情（MaskedField） | planned | APP-M2-T047、APP-M2-T059、APP-M2-T017 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T061.md` |
| [APP-M2-T062](tasks/APP-M2.md#app-m2-t062) | 人员证书 | planned | APP-M2-T047、APP-M2-T059、APP-M2-T061、APP-M2-T052 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T062.md` |
| [APP-M2-T063](tasks/APP-M2.md#app-m2-t063) | 占用（R12）与离职提示 | planned | APP-M2-T047、APP-M2-T059、APP-M2-T060 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T063.md` |
| [APP-M2-T064](tasks/APP-M2.md#app-m2-t064) | 授权列表 | planned | APP-M2-T047、APP-M2-T051、APP-M2-T054 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T064.md` |
| [APP-M2-T065](tasks/APP-M2.md#app-m2-t065) | 授权详情 | planned | APP-M2-T047、APP-M2-T051、APP-M2-T054 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T065.md` |
| [APP-M2-T066](tasks/APP-M2.md#app-m2-t066) | 授权链图（不满足节点标红、上游未登记虚线） | planned | APP-M2-T047、APP-M2-T051、APP-M2-T054、APP-M2-T065 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T066.md` |
| [APP-M2-T067](tasks/APP-M2.md#app-m2-t067) | 业绩列表与详情 | planned | APP-M2-T047、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T067.md` |
| [APP-M2-T068](tasks/APP-M2.md#app-m2-t068) | 业绩成员与产品 | planned | APP-M2-T047、APP-M2-T051、APP-M2-T067、APP-M2-T060 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T068.md` |
| [APP-M2-T069](tasks/APP-M2.md#app-m2-t069) | SLA 模板（等级、变量） | planned | APP-M2-T047、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T069.md` |
| [APP-M2-T070](tasks/APP-M2.md#app-m2-t070) | 全局变量 | planned | APP-M2-T047、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T070.md` |
| [APP-M2-T071](tasks/APP-M2.md#app-m2-t071) | 资料库首页健康度卡片 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T071.md` |
| [APP-M2-T072](tasks/APP-M2.md#app-m2-t072) | Excel 批量导入与逐条 / 按批确认 | planned | APP-M2-T047、APP-M2-T046 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T072.md` |
| [APP-M2-T073](tasks/APP-M2.md#app-m2-t073) | 有效期提醒与 A-04 资料库设置 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T073.md` |
| [APP-M2-T074](tasks/APP-M2.md#app-m2-t074) | 附件识别上传与进度 | planned | APP-M2-T047、APP-M2-T039 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T074.md` |
| [APP-M2-T075](tasks/APP-M2.md#app-m2-t075) | 识别结果核对（“待核对”标记） | planned | APP-M2-T047、APP-M2-T039、APP-M2-T074 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T075.md` |
| [APP-M2-T076](tasks/APP-M2.md#app-m2-t076) | 片段列表 | planned | APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T076.md` |
| [APP-M2-T077](tasks/APP-M2.md#app-m2-t077) | 片段编辑（变量校验） | planned | APP-M2-T047、APP-M2-T076、APP-M2-T070 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T077.md` |
| [APP-M2-T078](tasks/APP-M2.md#app-m2-t078) | 版本对比与发布（R31 拦截原因） | done | APP-M2-T047、APP-M2-T077、APP-M2-T238 | [ISSUE-022](../issues/ISSUE-022.md) | [交付](delivery/APP-M2-T078.md) |
| [APP-M2-T079](tasks/APP-M2.md#app-m2-t079) | 同步状态与重新同步 | planned | APP-M2-T047、APP-M2-T078 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T079.md` |
| [APP-M2-T080](tasks/APP-M2.md#app-m2-t080) | 历史标书单个 / 批量导入 | planned | APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T080.md` |
| [APP-M2-T081](tasks/APP-M2.md#app-m2-t081) | 入库状态派生显示与摘取为片段 | planned | APP-M2-T021、APP-M2-T080 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T081.md` |
| [APP-M2-T082](tasks/APP-M2.md#app-m2-t082) | 版本条（发布、回滚） | planned | APP-M2-T025 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T082.md` |
| [APP-M2-T083](tasks/APP-M2.md#app-m2-t083) | 章节模板 | planned | APP-M2-T025、APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T083.md` |
| [APP-M2-T084](tasks/APP-M2.md#app-m2-t084) | 叫法术语、语气称呼 | planned | APP-M2-T025、APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T084.md` |
| [APP-M2-T085](tasks/APP-M2.md#app-m2-t085) | 句式规则 | planned | APP-M2-T025、APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T085.md` |
| [APP-M2-T086](tasks/APP-M2.md#app-m2-t086) | Word 模板与导出命名 | planned | APP-M2-T025、APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T086.md` |
| [APP-M2-T087](tasks/APP-M2.md#app-m2-t087) | 预览抽屉 | planned | APP-M2-T025、APP-M2-T083、APP-M2-T084、APP-M2-T085 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T087.md` |
| [APP-M2-T088](tasks/APP-M2.md#app-m2-t088) | 任务卡列表与版本 | planned | APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T088.md` |
| [APP-M2-T089](tasks/APP-M2.md#app-m2-t089) | 提示词模板编辑与发布校验 | planned | APP-M2-T082、APP-M2-T088 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T089.md` |
| [APP-M2-T090](tasks/APP-M2.md#app-m2-t090) | 平台默认与公司覆盖对照 | planned | APP-M2-T082、APP-M2-T089 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T090.md` |
| [APP-M2-T091](tasks/APP-M2.md#app-m2-t091) | 审查清单 | planned | APP-M2-T082 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T091.md` |
| [APP-M2-T092](tasks/APP-M2.md#app-m2-t092) | 风格样例卡片墙（启用开关） | planned | APP-M2-T082、APP-M2-T081 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T092.md` |
| [APP-M2-T093](tasks/APP-M2.md#app-m2-t093) | 入库脱敏扫描结果展示 | planned | APP-M2-T082、APP-M2-T092、APP-M2-T230、APP-M2-T238、APP-M2-T243 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T093.md` |
| [APP-M2-T094](tasks/APP-M2.md#app-m2-t094) | ProjectHeader 摘要条与页签（无“资料匹配”） | planned | APP-M1-T14 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T094.md` |
| [APP-M2-T095](tasks/APP-M2.md#app-m2-t095) | 项目列表 | planned | APP-M1-T14 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T095.md` |
| [APP-M2-T096](tasks/APP-M2.md#app-m2-t096) | 新建项目与 R19 提示 | planned | APP-M1-T14、APP-M2-T224 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T096.md` |
| [APP-M2-T097](tasks/APP-M2.md#app-m2-t097) | 项目概览（待办、分册、状态操作） | planned | APP-M1-T14、APP-M2-T094 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T097.md` |
| [APP-M2-T098](tasks/APP-M2.md#app-m2-t098) | 项目基本字段和合作方协议（成员复用T14） | planned | APP-M1-T14、APP-M2-T054 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T098.md` |
| [APP-M2-T099](tasks/APP-M2.md#app-m2-t099) | 项目设置：拟派人员、SLA 取值、规则覆盖 | planned | APP-M1-T14、APP-M2-T060、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T099.md` |
| [APP-M2-T100](tasks/APP-M2.md#app-m2-t100) | 分册格式、闭环及导出设置（分工复用T14） | planned | APP-M1-T14、APP-M2-T044、APP-M2-T045、APP-M2-T086 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T100.md` |
| [APP-M2-T101](tasks/APP-M2.md#app-m2-t101) | 招标文件上传与版本链 | planned | APP-M1-T02、APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T101.md` |
| [APP-M2-T102](tasks/APP-M2.md#app-m2-t102) | 解析进度页（JobProgress 接入） | planned | APP-M1-T02、APP-M2-T021、APP-M2-T101 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T102.md` |
| [APP-M2-T103](tasks/APP-M2.md#app-m2-t103) | PdfLocator（PDF.js 本地 Worker、跳页高亮） | planned | APP-M1-T02、APP-M2-T101 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T103.md` |
| [APP-M2-T104](tasks/APP-M2.md#app-m2-t104) | 解析结果三栏布局与分类树 | planned | APP-M1-T02、APP-M2-T103 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T104.md` |
| [APP-M2-T105](tasks/APP-M2.md#app-m2-t105) | 条目卡片编辑与逐条确认 | planned | APP-M1-T02、APP-M2-T104 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T105.md` |
| [APP-M2-T106](tasks/APP-M2.md#app-m2-t106) | 批量确认（星号 / 废标 / 资格禁用）与置信度高亮 | planned | APP-M1-T02、APP-M2-T105 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T106.md` |
| [APP-M2-T107](tasks/APP-M2.md#app-m2-t107) | 重抽不覆盖与补遗差异 | planned | APP-M1-T02、APP-M2-T105、APP-M2-T101 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T107.md` |
| [APP-M2-T108](tasks/APP-M2.md#app-m2-t108) | “确认解析结果”闸门（悬停列未满足项） | planned | APP-M1-T02、APP-M2-T106、APP-M2-T107、APP-M2-T109、APP-M2-T110、APP-M2-T111 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T108.md` |
| [APP-M2-T109](tasks/APP-M2.md#app-m2-t109) | 后处理条与合并条目（“已合并 N 条 · 拆分”、多位置切换） | planned | APP-M2-T104、APP-M2-T019 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T109.md` |
| [APP-M2-T110](tasks/APP-M2.md#app-m2-t110) | 冲突待选定页签（并列取值、理由必填） | planned | APP-M2-T104、APP-M2-T109 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T110.md` |
| [APP-M2-T111](tasks/APP-M2.md#app-m2-t111) | 疑似遗漏（无批量、排除须理由）与引用未解析页签 | planned | APP-M2-T104、APP-M2-T148、APP-M2-T109 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T111.md` |
| [APP-M2-T112](tasks/APP-M2.md#app-m2-t112) | 矩阵表格与筛选（风险提示） | planned | APP-M1-T03 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T112.md` |
| [APP-M2-T113](tasks/APP-M2.md#app-m2-t113) | 行编辑（响应方式、要点、负责人） | planned | APP-M1-T03、APP-M2-T112 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T113.md` |
| [APP-M2-T114](tasks/APP-M2.md#app-m2-t114) | EvidenceDrawer | done | APP-M1-T03、APP-M2-T048、APP-M2-T204、APP-M2-T205 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T114.md) |
| [APP-M2-T115](tasks/APP-M2.md#app-m2-t115) | 批量智能匹配与逐行确认 | planned | APP-M1-T03、APP-M2-T118 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T115.md` |
| [APP-M2-T116](tasks/APP-M2.md#app-m2-t116) | P-18 分册分流确认 | planned | APP-M1-T03、APP-M1-T14 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T116.md` |
| [APP-M2-T117](tasks/APP-M2.md#app-m2-t117) | Excel 导出与确认闸门 | planned | APP-M1-T03、APP-M2-T113、APP-M2-T114、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T117.md` |
| [APP-M2-T118](tasks/APP-M2.md#app-m2-t118) | 挂证据候选的三路显示（结构化规则匹配 / 片段检索 / 历史标书仅参考） | planned | APP-M2-T114、APP-M2-T078、APP-M2-T081 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T118.md` |
| [APP-M2-T119](tasks/APP-M2.md#app-m2-t119) | SLA 矩阵表与判定 | planned | APP-M1-T10、APP-M1-T12、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T119.md` |
| [APP-M2-T120](tasks/APP-M2.md#app-m2-t120) | 模板取值与承诺函导出 | planned | APP-M1-T10、APP-M1-T12、APP-M2-T119 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T120.md` |
| [APP-M2-T121](tasks/APP-M2.md#app-m2-t121) | 项目事实表 | planned | APP-M1-T10、APP-M1-T12 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T121.md` |
| [APP-M2-T122](tasks/APP-M2.md#app-m2-t122) | “需复核”传播提示 | planned | APP-M1-T10、APP-M1-T12、APP-M2-T119、APP-M2-T121 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T122.md` |
| [APP-M2-T123](tasks/APP-M2.md#app-m2-t123) | 大纲排序、章节类型和增值理由（分工复用T15） | in-review | APP-M1-T15、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T123.md) |
| [APP-M2-T124](tasks/APP-M2.md#app-m2-t124) | 完整证据、片段及评分写作计划（确认复用T15） | in-review | APP-M1-T15已具备；APP-M2-T078 已 done（QA 19c4862，PM 17:20 确认），APP-M2-T114 已 done（QA f521950，PM 17:13 确认）。写作方案Prompt输入上下文完整组装 | [ISSUE-022](../issues/ISSUE-022.md) | [交付](delivery/APP-M2-T126.md) |
| [APP-M2-T125](tasks/APP-M2.md#app-m2-t125) | 招标原文预览联动与 R26 提示 | planned | APP-M1-T15、APP-M2-T123、APP-M2-T232 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T125.md` |
| [APP-M2-T126](tasks/APP-M2.md#app-m2-t126) | 按逐节确认结果启动生成（确认复用T15） | in-review | APP-M1-T15、APP-M2-T124、APP-M2-T125 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T126.md) |
| [APP-M2-T127](tasks/APP-M2.md#app-m2-t127) | 五类系统生成章节预览 | planned | APP-M1-T04、APP-M2-T191、APP-M2-T192、APP-M2-T193、APP-M2-T194、APP-M2-T195 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T127.md` |
| [APP-M2-T128](tasks/APP-M2.md#app-m2-t128) | 锁定提示与“去数据源修改” | planned | APP-M1-T04、APP-M2-T127、APP-M2-T163 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T128.md` |
| [APP-M2-T129](tasks/APP-M2.md#app-m2-t129) | 章节列表（编辑台入口） | planned | APP-M2-T126、APP-M2-T021 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T129.md` |
| [APP-M2-T130](tasks/APP-M2.md#app-m2-t130) | 章节循环进度页 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T044、APP-M2-T234、APP-M2-T237、APP-M2-T238、APP-M2-T254、APP-M2-T244、APP-M2-T245、APP-M2-T246、APP-M2-T247、APP-M2-T248、APP-M2-T249 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T130.md` |
| [APP-M2-T131](tasks/APP-M2.md#app-m2-t131) | 轮次时间线 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T130 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T131.md` |
| [APP-M2-T132](tasks/APP-M2.md#app-m2-t132) | 版本对比（复用 DiffView） | planned | APP-M2-T126、APP-M2-T021、APP-M2-T175 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T132.md` |
| [APP-M2-T133](tasks/APP-M2.md#app-m2-t133) | 人工处理队列列表 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T130 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T133.md` |
| [APP-M2-T134](tasks/APP-M2.md#app-m2-t134) | 队列详情单段编辑 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T133、APP-M2-T174 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T134.md` |
| [APP-M2-T135](tasks/APP-M2.md#app-m2-t135) | 一键重新检查 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T134 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T135.md` |
| [APP-M2-T136](tasks/APP-M2.md#app-m2-t136) | 异常中断与重试 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T130 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T136.md` |
| [APP-M2-T137](tasks/APP-M2.md#app-m2-t137) | W-03 公司级写作观察统计 | planned | APP-M2-T131、APP-M2-T189 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T137.md` |
| [APP-M2-T138](tasks/APP-M2.md#app-m2-t138) | P-17 项目级折叠区 | planned | APP-M2-T131、APP-M2-T189 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T138.md` |
| [APP-M2-T139](tasks/APP-M2.md#app-m2-t139) | 图表组件（AntV G2，待技术确认） | planned | APP-M2-T131、APP-M2-T189 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T139.md` |
| [APP-M2-T140](tasks/APP-M2.md#app-m2-t140) | RuleIssueList | planned | APP-M1-T05 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T140.md` |
| [APP-M2-T141](tasks/APP-M2.md#app-m2-t141) | 合规检查页布局与结论条 | planned | APP-M1-T05、APP-M2-T140 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T141.md` |
| [APP-M2-T142](tasks/APP-M2.md#app-m2-t142) | 警告放行（理由必填，阻断无放行） | planned | APP-M1-T05、APP-M2-T140 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T142.md` |
| [APP-M2-T143](tasks/APP-M2.md#app-m2-t143) | R18 段落相似度并排对比 | planned | APP-M1-T05、APP-M2-T223 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T143.md` |
| [APP-M2-T144](tasks/APP-M2.md#app-m2-t144) | 分册检查 / 定稿 / 解锁 / 交叉复核 | planned | APP-M1-T05、APP-M2-T142、APP-M2-T228、APP-M2-T229、APP-M2-T250、APP-M2-T251、APP-M2-T252、APP-M2-T255、APP-M2-T256、APP-M2-T257、APP-M2-T258 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T144.md` |
| [APP-M2-T145](tasks/APP-M2.md#app-m2-t145) | 全文检查与“结果已过期”提示 | planned | APP-M1-T05、APP-M2-T144 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T145.md` |
| [APP-M2-T146](tasks/APP-M2.md#app-m2-t146) | 合规规则页签（不可关闭锁、R43 无阻断） | planned | APP-M2-T025 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T146.md` |
| [APP-M2-T147](tasks/APP-M2.md#app-m2-t147) | 规则参数、恢复平台默认、修改历史 | planned | APP-M2-T025、APP-M2-T146 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T147.md` |
| [APP-M2-T148](tasks/APP-M2.md#app-m2-t148) | 兜底扫描词表（草稿、试扫、发布） | planned | APP-M2-T025、APP-M2-T146 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T148.md` |
| [APP-M2-T149](tasks/APP-M2.md#app-m2-t149) | 导出前提检查 | planned | APP-M1-T05、APP-M2-T145 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T149.md` |
| [APP-M2-T150](tasks/APP-M2.md#app-m2-t150) | 导出类型、模板与命名 | planned | APP-M1-T05、APP-M2-T196、APP-M2-T197、APP-M2-T198 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T150.md` |
| [APP-M2-T151](tasks/APP-M2.md#app-m2-t151) | 导出历史与下载（`export_status` 含排队） | planned | APP-M1-T05、APP-M2-T202 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T151.md` |
| [APP-M2-T152](tasks/APP-M2.md#app-m2-t152) | 递交版：仅项目负责人可见、已确认完整值类别展示、内部稿掩码说明 | planned | APP-M2-T149、APP-M2-T100、APP-M2-T017、APP-M2-T196 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T152.md` |
| [APP-M2-T153](tasks/APP-M2.md#app-m2-t153) | 工作台 6 张统计卡（点击即筛选） | planned | APP-M2-T095 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T153.md` |
| [APP-M2-T154](tasks/APP-M2.md#app-m2-t154) | 概览底部折叠区 | planned | APP-M2-T095 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T154.md` |
| [APP-M2-T155](tasks/APP-M2.md#app-m2-t155) | 集团管理员公司切换与只读视图 | planned | APP-M2-T016 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T155.md` |
| [APP-M2-T156](tasks/APP-M2.md#app-m2-t156) | 集团统计 | planned | APP-M2-T016 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T156.md` |
| [APP-M2-T157](tasks/APP-M2.md#app-m2-t157) | A-06 审计日志页 | in-review | APP-M2-T014 | [ISSUE-007](../issues/ISSUE-007.md) | [APP-M2-T157 交付](delivery/APP-M2-T157.md) |
| [APP-M2-T158](tasks/APP-M2.md#app-m2-t158) | 云端调用审计展开 | planned | APP-M2-T014、APP-M2-T157、APP-M2-T037 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T158.md` |
| [APP-M2-T159](tasks/APP-M2.md#app-m2-t159) | 服务健康基础与 A-11（M1-J01a）对齐 | planned | APP-M2-T014、APP-M2-T042 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T159.md` |
| [APP-M2-T160](tasks/APP-M2.md#app-m2-t160) | 编辑台布局与三档断点（四栏 / 三栏 / 紧凑） | planned | APP-M1-T15 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T160.md` |
| [APP-M2-T161](tasks/APP-M2.md#app-m2-t161) | 章节加载与段落键 | planned | APP-M1-T15 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T161.md` |
| [APP-M2-T162](tasks/APP-M2.md#app-m2-t162) | SourceBar 来源标记 | in-review | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | [APP-M2-T162 交付](delivery/APP-M2-T162.md) |
| [APP-M2-T163](tasks/APP-M2.md#app-m2-t163) | 锁定内容 | planned | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T163.md` |
| [APP-M2-T164](tasks/APP-M2.md#app-m2-t164) | 变量节点 | planned | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T164.md` |
| [APP-M2-T165](tasks/APP-M2.md#app-m2-t165) | 证据节点与 `.cite` | in-review | APP-M1-T15、APP-M2-T161、APP-M2-T048 | [ISSUE-007](../issues/ISSUE-007.md) | [APP-M2-T165 交付](delivery/APP-M2-T165.md) |
| [APP-M2-T166](tasks/APP-M2.md#app-m2-t166) | 问题标注与侧栏联动 | planned | APP-M1-T15、APP-M2-T161、APP-M2-T140 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T166.md` |
| [APP-M2-T167](tasks/APP-M2.md#app-m2-t167) | 选区悬浮工具条 | in-review | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | [APP-M2-T167 交付](delivery/APP-M2-T167.md) |
| [APP-M2-T168](tasks/APP-M2.md#app-m2-t168) | 目录树与章节切换 | in-review | APP-M1-T15、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | [APP-M2-T168 交付](delivery/APP-M2-T168.md) |
| [APP-M2-T169](tasks/APP-M2.md#app-m2-t169) | 工具栏紧凑模式（“格式”下拉） | planned | APP-M1-T15、APP-M2-T160 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T169.md` |
| [APP-M2-T170](tasks/APP-M2.md#app-m2-t170) | 只读态（他人编辑中） | planned | APP-M1-T15、APP-M2-T173 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T170.md` |
| [APP-M2-T171](tasks/APP-M2.md#app-m2-t171) | 长章节性能 | planned | APP-M1-T15、APP-M2-T161、APP-M2-T166、APP-M2-T167 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T171.md` |
| [APP-M2-T172](tasks/APP-M2.md#app-m2-t172) | 自动保存草稿 | planned | APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T172.md` |
| [APP-M2-T173](tasks/APP-M2.md#app-m2-t173) | EditLockBadge、心跳、超时提示、接管 | planned | APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T173.md` |
| [APP-M2-T174](tasks/APP-M2.md#app-m2-t174) | 提交版本与版本历史 | planned | APP-M2-T161、APP-M2-T172、APP-M2-T173 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T174.md` |
| [APP-M2-T175](tasks/APP-M2.md#app-m2-t175) | 版本对比与回退 | planned | APP-M2-T161、APP-M2-T174 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T175.md` |
| [APP-M2-T176](tasks/APP-M2.md#app-m2-t176) | 对话面板与会话列表 | planned | APP-M2-T167、APP-M2-T089 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T176.md` |
| [APP-M2-T177](tasks/APP-M2.md#app-m2-t177) | 流式输出、模型标识、降级提示 | planned | APP-M2-T167、APP-M2-T089、APP-M2-T176、APP-M2-T040 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T177.md` |
| [APP-M2-T178](tasks/APP-M2.md#app-m2-t178) | 建议卡片（写法、差异、来源、预检） | planned | APP-M2-T167、APP-M2-T089、APP-M2-T176、APP-M2-T242、APP-M2-T243、APP-M2-T244、APP-M2-T248 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T178.md` |
| [APP-M2-T179](tasks/APP-M2.md#app-m2-t179) | 自由问答（只“复制”） | in-review | APP-M2-T167、APP-M2-T089、APP-M2-T181 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T179.md) |
| [APP-M2-T180](tasks/APP-M2.md#app-m2-t180) | 上下文与样例任务卡选择 | planned | APP-M2-T167、APP-M2-T089、APP-M2-T176、APP-M2-T124 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T180.md` |
| [APP-M2-T181](tasks/APP-M2.md#app-m2-t181) | 资料库与本项目数据答案卡 | in-review | APP-M2-T176、APP-M2-T047、APP-M2-T112 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T181.md) |
| [APP-M2-T182](tasks/APP-M2.md#app-m2-t182) | 直查未命中与常规回答回退 | in-review | APP-M2-T176、APP-M2-T047、APP-M2-T112、APP-M2-T181 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T182.md) |
| [APP-M2-T183](tasks/APP-M2.md#app-m2-t183) | 插入为引用：差异视图、写入、引用标记 | in-review | APP-M2-T181、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/APP-M2-T183.md) |
| [APP-M2-T184](tasks/APP-M2.md#app-m2-t184) | 本项目招标文件轻量索引的检索结果展示 | in-review | APP-M2-T181 | [ISSUE-007](../issues/ISSUE-007.md) / [ISSUE-037](../issues/ISSUE-037.md) | [交付](delivery/APP-M2-T184.md) |
| [APP-M2-T185](tasks/APP-M2.md#app-m2-t185) | 差异确认写入 | in-review | APP-M2-T167、APP-M2-T178 | [ISSUE-007](../issues/ISSUE-007.md) / [ISSUE-037](../issues/ISSUE-037.md) | [交付](delivery/APP-M2-T185.md) |
| [APP-M2-T186](tasks/APP-M2.md#app-m2-t186) | “我已逐字核对”二次确认（星号 / 废标 / 偏离 / 披露） | planned | APP-M2-T167、APP-M2-T178、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T186.md` |
| [APP-M2-T187](tasks/APP-M2.md#app-m2-t187) | 冲突校验与重新定位提示 | planned | APP-M2-T167、APP-M2-T178、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T187.md` |
| [APP-M2-T188](tasks/APP-M2.md#app-m2-t188) | 粘贴识别 | planned | APP-M2-T167、APP-M2-T178、APP-M2-T185、APP-M2-T242、APP-M2-T243 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T188.md` |
| [APP-M2-T189](tasks/APP-M2.md#app-m2-t189) | 对话助手观察指标 | planned | APP-M2-T174、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T189.md` |
| [APP-M2-T190](tasks/APP-M2.md#app-m2-t190) | 人工修改率分项 | planned | APP-M2-T174、APP-M2-T185 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T190.md` |
| [APP-M2-T191](tasks/APP-M2.md#app-m2-t191) | 点对点应答确定性章节 | planned | APP-M2-T113、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T191.md` |
| [APP-M2-T192](tasks/APP-M2.md#app-m2-t192) | 评审索引确定性章节 | planned | APP-M2-T113、APP-M2-T123 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T192.md` |
| [APP-M2-T193](tasks/APP-M2.md#app-m2-t193) | 偏离表确定性章节 | planned | APP-M2-T113、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T193.md` |
| [APP-M2-T194](tasks/APP-M2.md#app-m2-t194) | 年度服务计划确定性章节 | planned | APP-M2-T121、APP-M2-T113 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T194.md` |
| [APP-M2-T195](tasks/APP-M2.md#app-m2-t195) | 证明材料清单确定性章节 | in-review | APP-M2-T114、APP-M2-T059、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | [APP-M2-T195 交付](delivery/APP-M2-T195.md) |
| [APP-M2-T196](tasks/APP-M2.md#app-m2-t196) | Word模板与正文样式渲染 | in-review | APP-M2-T086、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | [APP-M2-T196 交付](delivery/APP-M2-T196.md) |
| [APP-M2-T197](tasks/APP-M2.md#app-m2-t197) | 分册封面、目录与页码 | planned | APP-M2-T196、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T197.md` |
| [APP-M2-T198](tasks/APP-M2.md#app-m2-t198) | 指定附件页与敏感水印 | planned | APP-M2-T196、APP-M2-T059 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T198.md` |
| [APP-M2-T199](tasks/APP-M2.md#app-m2-t199) | Word属性修订与批注清理 | planned | APP-M2-T196 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T199.md` |
| [APP-M2-T200](tasks/APP-M2.md#app-m2-t200) | 同批合标核对清单输出 | planned | APP-M2-T149、APP-M2-T197、APP-M2-T192、APP-M2-T193 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T200.md` |
| [APP-M2-T201](tasks/APP-M2.md#app-m2-t201) | 内部响应追溯Excel | planned | APP-M2-T117、APP-M2-T162、APP-M2-T165 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T201.md` |
| [APP-M2-T202](tasks/APP-M2.md#app-m2-t202) | 递交批次原子输出和历史快照 | planned | APP-M2-T152、APP-M2-T197、APP-M2-T198、APP-M2-T199、APP-M2-T200 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T202.md` |
| [APP-M2-T203](tasks/APP-M2.md#app-m2-t203) | R01 不可引用的资料禁止引用 | planned | APP-M2-T047、APP-M2-T077 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T203.md` |
| [APP-M2-T204](tasks/APP-M2.md#app-m2-t204) | R02 资料来源分级与投标主体一致 | planned | APP-M2-T054、APP-M2-T098 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T204.md` |
| [APP-M2-T205](tasks/APP-M2.md#app-m2-t205) | R03 有效期覆盖投标截止时间 | planned | APP-M2-T047、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T205.md` |
| [APP-M2-T206](tasks/APP-M2.md#app-m2-t206) | R04 临期与复审提醒 | planned | APP-M2-T073、APP-M2-T031 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T206.md` |
| [APP-M2-T207](tasks/APP-M2.md#app-m2-t207) | R05 年审/监督审核有效 | planned | APP-M2-T056 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T207.md` |
| [APP-M2-T208](tasks/APP-M2.md#app-m2-t208) | R06 持证单位与主体名称一致 | planned | APP-M2-T056、APP-M2-T075 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T208.md` |
| [APP-M2-T209](tasks/APP-M2.md#app-m2-t209) | R07 原厂授权覆盖招标涉及的全部产品，授权链逐级有效，地域覆盖到地 | planned | APP-M2-T066、APP-M2-T051 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T209.md` |
| [APP-M2-T210](tasks/APP-M2.md#app-m2-t210) | R08 拟派人员持有招标涉及产品的有效原厂认证 | planned | APP-M2-T062、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T210.md` |
| [APP-M2-T211](tasks/APP-M2.md#app-m2-t211) | R09 故障等级与服务时段 | planned | APP-M2-T119、APP-M2-T121、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T211.md` |
| [APP-M2-T212](tasks/APP-M2.md#app-m2-t212) | R09 全类别SLA及能力比较 | planned | APP-M2-T119、APP-M2-T121、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T212.md` |
| [APP-M2-T213](tasks/APP-M2.md#app-m2-t213) | R09 模板外承诺类事实 | planned | APP-M2-T119、APP-M2-T121、APP-M2-T069 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T213.md` |
| [APP-M2-T214](tasks/APP-M2.md#app-m2-t214) | R10 手写与自然表达全文承诺 | planned | APP-M2-T119、APP-M2-T164、APP-M2-T193 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T214.md` |
| [APP-M2-T215](tasks/APP-M2.md#app-m2-t215) | R10 结构节点及确定性输出 | planned | APP-M2-T119、APP-M2-T164、APP-M2-T193 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T215.md` |
| [APP-M2-T216](tasks/APP-M2.md#app-m2-t216) | R11 本单位人员与社保核对 | planned | APP-M2-T061、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T216.md` |
| [APP-M2-T217](tasks/APP-M2.md#app-m2-t217) | R12 人员占用冲突 | planned | APP-M2-T063、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T217.md` |
| [APP-M2-T218](tasks/APP-M2.md#app-m2-t218) | R13 业绩满足资格与评分条件 | planned | APP-M2-T067、APP-M2-T068 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T218.md` |
| [APP-M2-T219](tasks/APP-M2.md#app-m2-t219) | R14 必备附件齐全 | planned | APP-M2-T059、APP-M2-T195、APP-M2-T198 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T219.md` |
| [APP-M2-T220](tasks/APP-M2.md#app-m2-t220) | R15 占位符与【待补】清零 | planned | APP-M2-T164、APP-M2-T165 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T220.md` |
| [APP-M2-T221](tasks/APP-M2.md#app-m2-t221) | R16 主体基本资格与证明材料时效 | planned | APP-M2-T054、APP-M2-T055 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T221.md` |
| [APP-M2-T222](tasks/APP-M2.md#app-m2-t222) | R17 使用提示与保密项目提醒 | planned | APP-M2-T047、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T222.md` |
| [APP-M2-T223](tasks/APP-M2.md#app-m2-t223) | R18 相似度检查 | planned | APP-M2-T095、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T223.md` |
| [APP-M2-T224](tasks/APP-M2.md#app-m2-t224) | R19 关联投标冲突 | planned | APP-M1-T01、APP-M2-T054 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T224.md` |
| [APP-M2-T225](tasks/APP-M2.md#app-m2-t225) | R20 同一编写人 | planned | APP-M2-T028、APP-M2-T174 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T225.md` |
| [APP-M2-T226](tasks/APP-M2.md#app-m2-t226) | R21 不同公司同一项目拟派人员为同一人 | planned | APP-M2-T061、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T226.md` |
| [APP-M2-T227](tasks/APP-M2.md#app-m2-t227) | R22 不同公司同一项目的保证金转出账户相同 | planned | APP-M2-T054、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T227.md` |
| [APP-M2-T228](tasks/APP-M2.md#app-m2-t228) | R23 星号条款、废标条款全部已确认响应 | planned | APP-M2-T105、APP-M2-T113 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T228.md` |
| [APP-M2-T229](tasks/APP-M2.md#app-m2-t229) | R24 格式要求 | planned | APP-M2-T191、APP-M2-T192、APP-M2-T193、APP-M2-T197 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T229.md` |
| [APP-M2-T230](tasks/APP-M2.md#app-m2-t230) | R25 名称机构残留 | planned | APP-M2-T161、APP-M2-T199 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T230.md` |
| [APP-M2-T231](tasks/APP-M2.md#app-m2-t231) | R25 Word元数据残留 | planned | APP-M2-T161、APP-M2-T199 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T231.md` |
| [APP-M2-T232](tasks/APP-M2.md#app-m2-t232) | R26 评分项覆盖度 | planned | APP-M2-T123、APP-M2-T113、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T232.md` |
| [APP-M2-T233](tasks/APP-M2.md#app-m2-t233) | R27 项目事实一致 | planned | APP-M2-T121、APP-M2-T164 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T233.md` |
| [APP-M2-T234](tasks/APP-M2.md#app-m2-t234) | R28 章节模型评审 | planned | APP-M2-T091、APP-M2-T089、APP-M2-T044、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T234.md` |
| [APP-M2-T235](tasks/APP-M2.md#app-m2-t235) | R29 本公司查重 | planned | APP-M2-T081、APP-M2-T078、APP-M2-T073、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T235.md` |
| [APP-M2-T236](tasks/APP-M2.md#app-m2-t236) | R30 无条款段落及范围外服务 | planned | APP-M2-T123、APP-M2-T121、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T236.md` |
| [APP-M2-T237](tasks/APP-M2.md#app-m2-t237) | R30 额外数值承诺 | planned | APP-M2-T123、APP-M2-T121、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T237.md` |
| [APP-M2-T238](tasks/APP-M2.md#app-m2-t238) | R31 正文敏感值与真实报告 | planned | APP-M2-T161、APP-M2-T059 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T238.md` |
| [APP-M2-T239](tasks/APP-M2.md#app-m2-t239) | R31 插图识别文字与报告附件 | planned | APP-M2-T161、APP-M2-T059 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T239.md` |
| [APP-M2-T240](tasks/APP-M2.md#app-m2-t240) | R32 产品范围一致 | planned | APP-M2-T051、APP-M2-T099、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T240.md` |
| [APP-M2-T241](tasks/APP-M2.md#app-m2-t241) | R33 拟派人员条件 | planned | APP-M2-T061、APP-M2-T062、APP-M2-T105、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T241.md` |
| [APP-M2-T242](tasks/APP-M2.md#app-m2-t242) | R34 AI 痕迹与格式符号残留 | planned | APP-M2-T161、APP-M2-T089 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T242.md` |
| [APP-M2-T243](tasks/APP-M2.md#app-m2-t243) | R35 称呼一致 | planned | APP-M2-T084、APP-M2-T098、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T243.md` |
| [APP-M2-T244](tasks/APP-M2.md#app-m2-t244) | R43 套话空泛词密度 | planned | APP-M2-T084、APP-M2-T085、APP-M2-T092、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T244.md` |
| [APP-M2-T245](tasks/APP-M2.md#app-m2-t245) | R43 七类句式及总结策略 | planned | APP-M2-T084、APP-M2-T085、APP-M2-T092、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T245.md` |
| [APP-M2-T246](tasks/APP-M2.md#app-m2-t246) | R43 注入风格样例照抄 | planned | APP-M2-T084、APP-M2-T085、APP-M2-T092、APP-M2-T162 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T246.md` |
| [APP-M2-T247](tasks/APP-M2.md#app-m2-t247) | R44 得分要点事实密度 | planned | APP-M2-T124、APP-M2-T162、APP-M2-T165、APP-M1-T12 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T247.md` |
| [APP-M2-T248](tasks/APP-M2.md#app-m2-t248) | R44 逐事实锚点与段落归属 | planned | APP-M2-T124、APP-M2-T162、APP-M2-T165、APP-M1-T12 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T248.md` |
| [APP-M2-T249](tasks/APP-M2.md#app-m2-t249) | R44 未登记关键事实前后矛盾 | planned | APP-M2-T124、APP-M2-T162、APP-M2-T165、APP-M1-T12 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T249.md` |
| [APP-M2-T250](tasks/APP-M2.md#app-m2-t250) | R36 人员资质证明跨册一致 | planned | APP-M2-T195、APP-M2-T193、APP-M2-T099、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T250.md` |
| [APP-M2-T251](tasks/APP-M2.md#app-m2-t251) | R36 偏离和证据版本跨册一致 | planned | APP-M2-T195、APP-M2-T193、APP-M2-T099、APP-M2-T116 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T251.md` |
| [APP-M2-T252](tasks/APP-M2.md#app-m2-t252) | R37 偏离表一致性 | planned | APP-M2-T193、APP-M2-T113 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T252.md` |
| [APP-M2-T253](tasks/APP-M2.md#app-m2-t253) | R38 证明材料与评分要点对应 | planned | APP-M2-T058、APP-M2-T059、APP-M2-T114、APP-M2-T075 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T253.md` |
| [APP-M2-T254](tasks/APP-M2.md#app-m2-t254) | R39 披露类条款 | planned | APP-M2-T057、APP-M2-T105、APP-M2-T161 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T254.md` |
| [APP-M2-T255](tasks/APP-M2.md#app-m2-t255) | R40 评审索引表 | planned | APP-M2-T192、APP-M2-T123 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T255.md` |
| [APP-M2-T256](tasks/APP-M2.md#app-m2-t256) | R41 证明材料齐全与盖章 | planned | APP-M2-T195、APP-M2-T059、APP-M2-T099 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T256.md` |
| [APP-M2-T257](tasks/APP-M2.md#app-m2-t257) | R42 暗标正文节点 | planned | APP-M2-T197、APP-M2-T198、APP-M2-T199、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T257.md` |
| [APP-M2-T258](tasks/APP-M2.md#app-m2-t258) | R42 暗标输出全部位置 | planned | APP-M2-T197、APP-M2-T198、APP-M2-T199、APP-M2-T100 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T258.md` |
| [APP-M2-T259](tasks/APP-M2.md#app-m2-t259) | 公司年度中小企业划型记录及声明取值 | planned | APP-M2-T053、APP-M2-T054、APP-M2-T047 | [ISSUE-007](../issues/ISSUE-007.md) | `docs/delivery/APP-M2-T259.md` |
| [AI-01](tasks/AI-M0.md#ai-01) | 登记模型、向量、业务库和内网访问待决项（后端已有 /api/v1/model-configs，用户要求弹窗配置，前端未接；保持 in-review） | in-review | [FE-M0-T02](tasks/FE-M0.md#fe-m0-t02)；真实端点另计验收 | [ISSUE-010](../issues/ISSUE-010.md)；[ISSUE-028](../issues/ISSUE-028.md) | [登记交付](delivery/AI-01.md) / [ISSUE-028交付](delivery/ISSUE-028.md) |
| [AI-02](tasks/AI-M0.md#ai-02) | OpenAI 兼容对话适配器 | done | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-011](../issues/ISSUE-011.md) | [交付](delivery/AI-02.md) |
| [AI-03](tasks/AI-M0.md#ai-03) | 检索层内存骨架 | done | [BE-M0-T01](tasks/BE-M0.md#be-m0-t01) | [ISSUE-016](../issues/ISSUE-016.md) | [交付](delivery/AI-03.md) |
| [AI-04](tasks/AI-M0.md#ai-04) | CI 假 RAGFlow 检索服务（保持 in-review；真 RAGFlow 列入 ③，假服务仅限 CI，勿标生产已接好） | in-review | [AI-03](tasks/AI-M0.md#ai-03) | [ISSUE-037](../issues/ISSUE-037.md) | [交付](delivery/AI-04.md) |
| [AI-05](tasks/AI-M0.md#ai-05) | RAGFlow 检索客户端（保持 in-review；真 RAGFlow 列入 ③，假服务仅限 CI，勿标生产已接好） | in-review | [AI-04](tasks/AI-M0.md#ai-04) | [ISSUE-037](../issues/ISSUE-037.md) | [交付](delivery/AI-05.md) |
| [AI-06](tasks/AI-M0.md#ai-06) | 证据候选改走 RAGFlow 检索（保持 in-review；真 RAGFlow 列入 ③，假服务仅限 CI，勿标生产已接好） | in-review | [AI-05](tasks/AI-M0.md#ai-05) | [ISSUE-037](../issues/ISSUE-037.md) | [交付](delivery/AI-06.md) / [流水线交付](delivery/AI-GENERATION-PIPELINE.md) |
| [AI-COMPLIANCE-CROSS-CHECK](tasks/AI-M0.md#ai-compliance-cross-check) | AI 合规检查依据交叉核验与差距诊断 | done | [APP-M2-T185](tasks/APP-M2.md#app-m2-t185) | [ISSUE-037](../issues/ISSUE-037.md)；[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/AI-COMPLIANCE-CROSS-CHECK.md) |
| [AI-M0-RAGFLOW-VERIFY](tasks/AI-M0.md#ai-m0-ragflow-verify) | RAGFlow 端点对接与检索隔离审查 | in-review | [AI-04](tasks/AI-M0.md#ai-04)、[AI-05](tasks/AI-M0.md#ai-05)、[AI-06](tasks/AI-M0.md#ai-06) | [ISSUE-037](../issues/ISSUE-037.md)；[ISSUE-010](../issues/ISSUE-010.md) | [交付](delivery/AI-M0-RAGFLOW-VERIFY.md) |
| [AI-RAGFLOW-KB-SYNC](tasks/AI-M0.md#ai-ragflow-kb-sync) | RAGFlow 知识库同步闭环（dataset/kb_sync、多租户隔离与方案片段同步落地，用户拍板 B5/B6） | done | [AI-M0-RAGFLOW-VERIFY](tasks/AI-M0.md#ai-m0-ragflow-verify) | [ISSUE-037](../issues/ISSUE-037.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/2026-10-26-ragflow-kb-sync.md) |
| [AI-SNIPPET-RETRIEVAL-MATCH](tasks/AI-M0.md#ai-snippet-retrieval-match) | 方案片段智能检索与上下文精准匹配（多租户强隔离、事实变量自动对齐填充、.cite 溯源与涉密本地模型守卫） | done | [AI-RAGFLOW-KB-SYNC](tasks/AI-M0.md#ai-ragflow-kb-sync) | [ISSUE-037](../issues/ISSUE-037.md)、[ISSUE-010](../issues/ISSUE-010.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/AI-SNIPPET-RETRIEVAL-MATCH.md) |
| [BE-TECH-DEBT-01](tasks/BE-M0.md#be-tech-debt-01) | suggestions 双错误体统一规范体解构并引入单测 | done | [WP-5](delivery/WP-5.md) | [ISSUE-038](../issues/ISSUE-038.md) | [交付](delivery/2026-10-26-persistence-and-error-body.md) |
| [FE-TECH-DEBT-01](tasks/FE-M0.md#fe-tech-debt-01) | EditorPage 等巨石二次瘦身（<400/600 精神，抽离 hooks 与子面板） | done | [WP-3](delivery/WP-3.md) | [ISSUE-038](../issues/ISSUE-038.md) | [交付](delivery/FE-TECH-DEBT-01.md) |
| [BE-TECH-DEBT-02](tasks/BE-M0.md#be-tech-debt-02) | 补齐 icg/api 与 icg/app，业务实现迁移至 icg 上下文分包体系（去平铺命名体系规范化） | done | [WP-4](delivery/WP-4.md) | [ISSUE-038](../issues/ISSUE-038.md) | [交付](delivery/2026-10-26-backend-unflatten-progress.md) |
| [BE-TECH-DEBT-03](tasks/BE-M0.md#be-tech-debt-03) | workflow_orchestrator 巨石解耦与领域子编排服务细化（代码行数严格控制 <= 350 行） | done | [BE-TECH-DEBT-02](tasks/BE-M0.md#be-tech-debt-02) | [ISSUE-038](../issues/ISSUE-038.md)、[ISSUE-006](../issues/ISSUE-006.md) | [交付](delivery/BE-TECH-DEBT-03.md) |
| [REV-SMOKE-001](tasks/REV-M0.md#rev-smoke-001) | 关演示全流程冒烟断点排查（6阶段端到端闭环验证与双册Word真实验证） | done | [WP-5](delivery/WP-5.md)、[WP-6](delivery/WP-6.md)、[WP-7](delivery/WP-7.md) | [ISSUE-005](../issues/ISSUE-005.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/REV-SMOKE-001.md) |
| [FE-SNIPPET-LIBRARY](tasks/FE-M0.md#fe-snippet-library) | 知识库方案片段管理最小页（真实列表/详情/变量展示与公司隔离） | in-review | [WP-2](delivery/WP-2.md)、[APP-M2-T078](delivery/APP-M2-T078.md) | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/FE-SNIPPET-LIBRARY.md) |
| [FE-WRITING-ARCHIVE](tasks/FE-M0.md#fe-writing-archive) | 写作档案与风格规范最小页（语气偏好/禁用词/公文排版/标杆样章与公司隔离） | in-review | [WP-2](delivery/WP-2.md)、[FE-SNIPPET-LIBRARY](delivery/FE-SNIPPET-LIBRARY.md) | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/FE-WRITING-ARCHIVE.md) |
| [INT-VOLUME-FINALIZE-GLUE](tasks/BE-M0.md#int-volume-finalize-glue) | 分册定稿与工作台/导出前后端契约胶水打通（定稿状态流转/锁定/递交导出前置门禁） | done | [BE-VOLUME-FINALIZE-GATE](tasks/BE-M0.md#be-volume-finalize-gate)、[REV-SMOKE-001](tasks/REV-M0.md#rev-smoke-001) | [ISSUE-005](../issues/ISSUE-005.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/INT-VOLUME-FINALIZE-GLUE.md) |
| [FE-REACT-ROUTER](tasks/FE-M0.md#fe-react-router) | React-Router 现代化路由体系落地（落实用户拍板决策 B2） | done | [WP-6](delivery/WP-6.md)、[FE-WRITING-ARCHIVE](delivery/FE-WRITING-ARCHIVE.md) | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/2026-10-26-frontend-react-router.md) |
| [BE-COMPLIANCE-RULES-P1](tasks/BE-M0.md#be-compliance-rules-p1) | 核心合规规则第二批编号落地（R03/R04/R09/R10 结构化裁决与导出校验） | done | [BE-COMPLIANCE-RULES-P0](tasks/BE-M0.md#be-compliance-rules-p0) | [ISSUE-006](../issues/ISSUE-006.md)；[ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/BE-COMPLIANCE-RULES-P1.md) |
| [INT-MODEL-CONFIG-MODAL](tasks/BE-M0.md#int-model-config-modal) | 大模型与 RAGFlow 弹窗配置前后端契约打通（落实用户拍板弹窗配置） | done | [AI-RAGFLOW-KB-SYNC](tasks/AI-M0.md#ai-ragflow-kb-sync) | [ISSUE-010](../issues/ISSUE-010.md)；[ISSUE-028](../issues/ISSUE-028.md) | [交付](delivery/INT-MODEL-CONFIG-MODAL.md) |
| [BE-COMPLIANCE-RULES-P2](tasks/BE-M0.md#be-compliance-rules-p2) | 核心合规规则第三批编号落地（R07/R11/R14/R25/R31 结构化裁决与导出阻断联动） | done | [BE-COMPLIANCE-RULES-P1](tasks/BE-M0.md#be-compliance-rules-p1) | [ISSUE-006](../issues/ISSUE-006.md)；[ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/BE-COMPLIANCE-RULES-P2.md) |
| [INT-TASK-CENTER-GLUE](tasks/BE-M0.md#int-task-center-glue) | 异步任务中心与长任务流式通知前后端联调（创建/持久化/推流/降级/取消与重试） | done | [BE-M0-T06](tasks/BE-M0.md#be-m0-t06)、[APP-M2-T020](tasks/APP-M2.md#app-m2-t020) | [ISSUE-006](../issues/ISSUE-006.md)；[ISSUE-038](../issues/ISSUE-038.md) | [交付](delivery/INT-TASK-CENTER-GLUE.md) |
| [BE-COMPLIANCE-RULES-P3](tasks/BE-M0.md#be-compliance-rules-p3) || done | [BE-COMPLIANCE-RULES-P2](tasks/BE-M0.md#be-compliance-rules-p2) | [ISSUE-006](../issues/ISSUE-006.md)；[ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/BE-COMPLIANCE-RULES-P3.md) |
| [AI-DYNAMIC-PROMPT-CONTEXT](tasks/AI-M0.md#ai-dynamic-prompt-context) || done | [AI-SNIPPET-RETRIEVAL-MATCH](tasks/AI-M0.md#ai-snippet-retrieval-match) | [ISSUE-037](../issues/ISSUE-037.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/AI-DYNAMIC-PROMPT-CONTEXT.md) |
| [INT-APP-SLIM-ROUTING](tasks/BE-M0.md#int-app-slim-routing) || done | [INT-TASK-CENTER-GLUE](tasks/BE-M0.md#int-task-center-glue)、[APP-M2-T021](tasks/APP-M2.md#app-m2-t021)、[APP-M2-T022](tasks/APP-M2.md#app-m2-t022) | [ISSUE-007](../issues/ISSUE-007.md)、[ISSUE-038](../issues/ISSUE-038.md) | [交付](delivery/INT-APP-SLIM-ROUTING.md) |
| [FE-TECH-DEBT-02](tasks/FE-M0.md#fe-tech-debt-02) || done | [FE-TECH-DEBT-01](tasks/FE-M0.md#fe-tech-debt-01) | [ISSUE-038](../issues/ISSUE-038.md) | [交付](delivery/FE-TECH-DEBT-02.md) |
| [INT-STATUS-TAG-METADATA-GLUE](tasks/BE-M0.md#int-status-tag-metadata-glue) | 状态注册表与元数据接口端到端契约联调（6大状态码表对齐/all聚合/8角色自适应权限/零漂移） | done | [INT-APP-SLIM-ROUTING](tasks/BE-M0.md#int-app-slim-routing)、[APP-M2-T023](tasks/APP-M2.md#app-m2-t023) | [ISSUE-007](../issues/ISSUE-007.md)、[ISSUE-038](../issues/ISSUE-038.md) | [交付](delivery/INT-STATUS-TAG-METADATA-GLUE.md) |
| [AI-OUTLINE-GENERATE-EXPAND](tasks/AI-M0.md#ai-outline-generate-expand) | 章节写作方案多段落结构化批量生成引擎（[P1]~[Pn]分段/得分小标题/白名单引用溯源/多章独立启动/预算汇聚） | done | [AI-DYNAMIC-PROMPT-CONTEXT](tasks/AI-M0.md#ai-dynamic-prompt-context) | [ISSUE-037](../issues/ISSUE-037.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/AI-OUTLINE-GENERATE-EXPAND.md) |
| [INT-DICT-CONFIG-RBAC-GLUE](tasks/BE-M0.md#int-dict-config-rbac-glue) | 字典配置与元数据停用/角色权限端到端契约联调（CRUD/停用保护红线/重复代码409/8角色RBAC） | done | [INT-STATUS-TAG-METADATA-GLUE](tasks/BE-M0.md#int-status-tag-metadata-glue)、[APP-M2-T024](tasks/APP-M2.md#app-m2-t024) | [ISSUE-007](../issues/ISSUE-007.md)、[ISSUE-038](../issues/ISSUE-038.md) | [交付](delivery/INT-DICT-CONFIG-RBAC-GLUE.md) |
| [BE-COMPLIANCE-RULES-P4](tasks/BE-M0.md#be-compliance-rules-p4) | 核心合规规则第五批编号落地（R13/R16/R18/R24/R32 结构化裁决与导出阻断联动） | done | [BE-COMPLIANCE-RULES-P3](tasks/BE-M0.md#be-compliance-rules-p3) | [ISSUE-006](../issues/ISSUE-006.md)；[ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/BE-COMPLIANCE-RULES-P4.md) |
| [AI-OUTLINE-AUTO-TREE-BUILD](tasks/AI-M0.md#ai-outline-auto-tree-build) | 招标文件解析驱动的大纲树自动规划构建引擎（卷/册/编/章/节多层级自动衍生/评分要点挂接/防编造追溯/涉密本地模型门禁） | done | [AI-OUTLINE-GENERATE-EXPAND](tasks/AI-M0.md#ai-outline-generate-expand) | [ISSUE-037](../issues/ISSUE-037.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/AI-OUTLINE-AUTO-TREE-BUILD.md) |
| [FE-LOGIN-ACCOUNT-PASSWORD](tasks/FE-M0.md#fe-login-account-password) | 生产环境正式账号密码登录表单与超级管理员接入（admin/X_2026/Layout First/令牌直登） | done | [FE-TECH-DEBT-02](tasks/FE-M0.md#fe-tech-debt-02) | [ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/FE-LOGIN-ACCOUNT-PASSWORD.md) |
| [BE-AUTH-SUPER-ADMIN](tasks/BE-M0.md#be-auth-super-admin) | 正式账号密码认证机制与全系统超级管理员内置（PBKDF2加盐哈希/admin系统超管/跨公司全路由/防缓存响应头） | done | [BE-COMPLIANCE-RULES-P4](tasks/BE-M0.md#be-compliance-rules-p4) | [ISSUE-006](../issues/ISSUE-006.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/BE-AUTH-SUPER-ADMIN.md) |
| [INT-AUTH-LOGIN-RBAC-GLUE](tasks/BE-M0.md#int-auth-login-rbac-glue) | 账号密码认证与超级管理员端到端契约联调（admin/X_2026/401拦截/会话全权限/跨公司审计） | done | [FE-LOGIN-ACCOUNT-PASSWORD](tasks/FE-M0.md#fe-login-account-password)、[BE-AUTH-SUPER-ADMIN](tasks/BE-M0.md#be-auth-super-admin) | [ISSUE-007](../issues/ISSUE-007.md)、[ISSUE-038](../issues/ISSUE-038.md) | [交付](delivery/INT-AUTH-LOGIN-RBAC-GLUE.md) |
| [AI-OUTLINE-SCORE-WEIGHT-CALC](tasks/AI-M0.md#ai-outline-score-weight-calc) | 大纲评分项分值权重加权与章节优先级智能排序引擎（分值加权/星号与废标红线加权得分/推荐编写队列） | done | [AI-OUTLINE-AUTO-TREE-BUILD](tasks/AI-M0.md#ai-outline-auto-tree-build) | [ISSUE-037](../issues/ISSUE-037.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/AI-OUTLINE-SCORE-WEIGHT-CALC.md) |
| [INT-COMPANY-SETTINGS-RBAC-GLUE](tasks/BE-M0.md#int-company-settings-rbac-glue) | 企业设置与安全策略/租户隔离端到端契约联调（GET/PATCH/只能调严422/跨租户404/RBAC） | in-review | [APP-M2-T025](tasks/APP-M2.md#app-m2-t025)、[BE-AUTH-SUPER-ADMIN](tasks/BE-M0.md#be-auth-super-admin) | [ISSUE-007](../issues/ISSUE-007.md)、[ISSUE-006](../issues/ISSUE-006.md) | [交付](delivery/INT-COMPANY-SETTINGS-RBAC-GLUE.md) |
| [BE-COMPLIANCE-RULES-P5](tasks/BE-M0.md#be-compliance-rules-p5) | PRD P5 终批核心合规规则引擎扩充（R17/R19/R26/R27/R28）与整本导出门禁全覆盖闭环 | in-review | [BE-COMPLIANCE-RULES-P4](tasks/BE-M0.md#be-compliance-rules-p4) | [ISSUE-006](../issues/ISSUE-006.md)；[ISSUE-027](../issues/ISSUE-027.md) | [交付](delivery/BE-COMPLIANCE-RULES-P5.md) |
| [AI-OUTLINE-BATCH-GENERATION-PIPELINE](tasks/AI-M0.md#ai-outline-batch-generation-pipeline) | 基于优先级推荐队列的大纲多章节批量生成流水线调度引擎（并发受控切片/PRD §5.7.8未确认不阻塞/Token仪表盘/单事务原子落盘） | in-review | [AI-OUTLINE-SCORE-WEIGHT-CALC](tasks/AI-M0.md#ai-outline-score-weight-calc) | [ISSUE-037](../issues/ISSUE-037.md)、[ISSUE-007](../issues/ISSUE-007.md) | [交付](delivery/AI-OUTLINE-BATCH-GENERATION-PIPELINE.md) |
<!-- task-board:end -->

## 每次推进的同步顺序

1. 读取关联 Issue、任务卡、项目状态与当前版本；确认范围变化是否需要新需求/版本 Issue。
2. 确认任务依赖、API 和基线后转 ready，开工转 in-progress；阻塞时写具体原因和所需输入。
3. 完成实际变更与必要验证，先写 `docs/delivery/<TASK_ID>.md` 的结果、证据和限制；有代码修改时创建并链接 `docs/code/<TASK_ID>.md`，再转 in-review 等待验收。
4. 同步 PRD/ROADMAP/ARCHITECTURE 的受影响章节，或在交付中逐项记录无需修改的核对依据。
5. 更新 Issue、任务卡和本看板状态、PROJECT_STATUS 进度，最后登记 DOCUMENT_INDEX；检查链接/状态一致后转 done。
6. 把本地验收、合入、发布分别记录；功能只有真实接口联调通过才计生产完成。

当前优先：APP-M1按ICG示例实施和联调，来源差异同步核对；模型与向量库保留接口不阻止本地产品流程开发。ISSUE-010 已 closed：业务库为 MySQL 8，对话模型由配置页提供，嵌入与向量库用 RAGFlow 自带，生产生成仅内网。AI-01 为 in-review。ISSUE-028 的运行时配置动态路由与 AC-04 敏感门禁已落地（test_model_config_provider.py 11 passed 1 skipped），配置运行时已接通，ISSUE-028 仍 in-review，ISSUE-010 仍 closed。AI-02已由项目经理于 10-12 12:10 在 QA 签署后确认为 done。AI-03 已依据 QA 签署 2fe6198（REV-M0-T16）标为 done，不连接 MySQL。ISSUE-037 为 in-progress：AI-04、AI-05 与 AI-06 为 in-review，章节生成与建议端到端贯通（test_chapter_generation_rag_flow.py 7 passed）；AI-M0-RAGFLOW-VERIFY 审查核验已推进至 in-review，端点对接规范、租户强隔离语义与出处防虚构机制核验通过，测试 41 passed 2 skipped + 14 passed 1 skipped 全过，真实端点依赖受 ICG_RUN_REAL_RAGFLOW_TESTS=1 保护，生产对接诚实记录为 blocked。ISSUE-029 保持 closed。ISSUE-005 保持 in-progress：错误体与幂等已由项目经理于 10-12 12:28 在 QA 签署后确认，T04、T05 与 T06 为 in-review，T07 仍 ready，该 Issue 不关闭。生产门禁继续验证，不能用主链路内部稿替代完整交付。