为什么有这个文件：汇总项目目前已有的成果、未完成事项和下一步。

它解决什么问题：避免把计划、静态演示或文档完成误认为真实功能已经可用。

# 项目状态

维护日期：2026-10-28（UTC+8）。分支 `feat/opencode-ICG` 位于 tip `4985a9d`（相对 `main` 超前 71 个提交）；Wave 11 在分支 `feat/wave-11-main-path` 开发，经 [PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) 并回；初次接手从 `main` 的 `ce064f6` 开始维护；main/xqr分支情况保留2026-10-09核对快照。已补齐 WP-1 独立交付文档（D-696），对齐 RoleMode 枚举，登记整改后结构债务收敛 ISSUE-038（D-697），完成 DOC-SYNC-1（D-698）与 DOC-SYNC-1.1（D-699）活文档实树校准。完成 CI 工作流触发分支修复（D-721）、已签等 PM 清单汇总（D-722）与关演示主链路冒烟留证（D-723）、大模型与 RAGFlow 弹窗配置及实测（D-724/D-725）、规则最小可递交集与分册定稿闸门端到端闭环（D-726/D-727）、以及 2026-10-26 规划未落地债审计与看板状态校准（D-728/D-729）。新增 R01/R02/R35 规则扩写落地与 7 大核心规则闭环、MySQL 章节/草稿/检查双向持久化、真实内网 RAGFlow 连通性网络探针证据归档与关演示全业务链路新冒烟留证（D-740/D-741）。Wave 2 批次（D-746～D-753）、Wave 3 批次（D-756～D-763）与 Wave 4 批次（FE-TECH-DEBT-02 App.tsx 瘦身至 394 行、APP-M2-T022 平台管理员脱敏长任务、BE-COMPLIANCE-RULES-P3 P3 规则扩充至 21 项与导出门禁、AI-DYNAMIC-PROMPT-CONTEXT 自适应 Prompt 预算与指纹、INT-APP-SLIM-ROUTING 路由分层与脱敏联调）（D-766～D-775）经 QA 独立终验签署（D-754/D-764/D-776 PASS）与 PD 产品验收（D-755/D-765/D-777 认可），已获人类 PM 正式批准标为 done。当前共 444 项中 96 done、65 in-review、7 in-progress、228 planned、41 blocked、7 cancelled、0 ready，2026-10-28 逐行统计）。Wave 9 批次（APP-M2-T027、INT-USER-TRANSFER-RBAC-GLUE、BE-USER-MANAGEMENT-TRANSFER、AI-CHAPTER-AUTO-VALIDATION-GATE）与 Wave 10 核心批次（APP-M2-T028 用户角色分配与账号解锁 D-828/D-829、BE-USER-SECURITY-OPS 用户安全运维服务 D-830/D-831、INT-USER-SECURITY-OPS-GLUE 账号安全契约联调 D-832/D-833、AI-OUTLINE-AUTO-REMEDIATION 质检缺陷自动整改建议与局部智能重写引擎 D-834/D-835）经 QA 独立复测终验（D-836 PASS）与 PD 产品验收（D-837 认可），已获人类 PM 正式批准标为 done。

## Wave 11 主路径补环（2026-10-28）

- 已交付并 in-review：人工处理队列（APP-M2-T133，替换最后一个主导航占位页）、分册交叉复核与定稿门禁（APP-M2-T144）、星号/废标兜底扫描与疑似遗漏（APP-M2-T111）、整改引擎不编造（AI-REMEDIATION-NO-FABRICATION）、新聚合 MySQL 持久化（BE-WORKFLOW-STATE-PERSIST）。交付见各卡 `docs/delivery/`，验证见 [Wave 11 验证](testing/2026-10-28-wave-11-verification.md)。
- `UNIMPLEMENTED_RULES` 移除“交叉复核和完整分册定稿”，余 4 组；递交版仍可能被 `RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS` 拦截，不宣称可递交。
- 新发现：[ISSUE-039](../issues/ISSUE-039.md) Wave 10 整改引擎会把“无法满足”改成“完全满足”、把【待补】改成空泛承诺，已撤回；[ISSUE-041](../issues/ISSUE-041.md) MySQL 模式下工作流主体仍只在进程内存，生产路径重启会丢解析与矩阵数据；[ISSUE-042](../issues/ISSUE-042.md) offline-check 的 e2e 必需作业自 `e56d225` 起每次失败，tip `4985a9d` 的 backend 作业也失败（`auto_remediate` 未透传，已在 `1758920` 修复）。
- 产品完备度按 [缺口增量](delivery/2026-10-28-prd-gap-delta.md) 粗估约 40%～45%，不是 MVP 可上线。

## 现行工程结构现状与规划未落地债审计（2026-10-26 纠偏）

分支 `feat/opencode-ICG` 前端八域物理分层已切实落地；但经 2026-10-26 深度审计确认，原“WP-1～7 完全收官”口径存在虚高，后端 `icg_demo` 根目录仍有 35 个业务 py 平铺承载主流量，Memory 旁路与 MySQL 双路径仍存，`/api/demo` 兼容窗口至 2026-11-15。根据用户 2026-10-26 官方拍板决定（B1~B6），正式启动 D1～D5 规划未落地债收口：
1. **前端 8 域物理分层**：`frontend/web/src/` 根目录仅保留 `main.tsx`，所有代码按 `app/`、`shell/`、`project/`、`editor/`、`library/`、`admin/`、`status/`、`shared/` 组织，巨石组件拆解完成，全界面严格落实 **Layout First** 原则。
2. **后端模块解耦与分包**：`backend/bid-core/icg/` 建立 `infra/`（含 `memory_repository.py`、`mysql_gate.py` 及 `repositories/` 下 8 大持久化仓储）与 `domain/`（`workflow_orchestrator`、`export_service`、`generation_service`、`outline_service` 4 大服务）；`icg_demo/` 下的 `database.py`（76行）与 `workflow.py`（29行）为向后兼容转接壳（façade），`adapters.py` 保留 `DemoModelProvider` 替身实现。
3. **接口与角色收口**：主流程收敛至 `/api/v1` 路径；旧 `/api/demo` 端点标记为 Deprecated；前端由 `roles.ts`（8 大标准角色）与 `codes.ts` 单源驱动；支持凭据登录与 `VITE_DEMO=0` 演示关闸；生产环境配置（`ICG_REQUIRE_MYSQL=1`）强行阻断演示账号。
4. **门禁与测试权威收口**：前端唯一权威测试套件位于 `frontend/web/tests/`（370 项全绿）；后端全量通过（630 passed / 42 skipped）；CI 接入 OpenAPI 一致性校验（`--check`）与前端 lint 门禁；治理检查 100% 合规。
现行仓库骨架详见 [工程目录方案](architecture/repository-layout.md) 与 [AGENTS.md](../AGENTS.md)。

## 模型与数据库待决

ISSUE-010 已 closed。2026-10-12 用户决定业务库为 MySQL 8，对话模型由配置页提供，嵌入与向量库用 RAGFlow 自带能力，生产生成只在内网（user decision, relayed by PM）。pgvector 不再作为同库选项。重排使用 RAGFlow 自带的重排器，重排模型在 RAGFlow 内配置（用户 10-12 14:34 确认）。AI-01 为 in-review，真实端点未验收。ISSUE-028 对话模型运行时动态路由、启动快照、流式/JSON透传与 AC-04 敏感门禁（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）已实现并通过测试（test_model_config_provider.py 11 passed 1 skipped），状态为 in-review，不标 closed。CI 使用记录请求头的假对话服务，连真实地址须 `ICG_RUN_REAL_MODEL_TESTS=1`，默认跳过。连接配置和空基线迁移已由项目经理在 QA 签署 `98c5129` 后确认。回执和登录会话由 [BE-M0-T11](delivery/BE-M0-T11.md) 依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done。编辑租约由 [BE-M0-T12](delivery/BE-M0-T12.md) 依据 QA ae6fd10，PM 15:32 确认 done。业务聚合仍未入库。未设置 `ICG_DATABASE_URL` 时单元测试继续使用内存实现。托管 CI 不能访问公司内网。原 `backend` 作业仍不跑 MySQL；ISSUE-025 的 `backend-mysql` 作业在运行器上启动 `mysql:8.4`，密码运行时生成，不进仓库。ISSUE-023 已由项目经理在 QA 签署 16cf971 后确认，状态为 closed。

ISSUE-011 已 closed，AI-02 为 done：项目经理于 10-12 12:10 在 QA 签署后确认。OpenAI 兼容适配器默认仍是演示替身，只有显式配置才启用；失败返回现有 502，敏感项目门禁保持不变。契约测试使用假 HTTP，没有调用真实端点。ISSUE-010 已 closed，真实端点仍未验收。详见[验证](testing/2026-10-12-openai-compatible-model.md)。

ISSUE-016 已依据 QA 签署 2fe6198（REV-M0-T16）标为 closed，AI-03 为 done。嵌入、重排和向量检索只有内存实现。证据候选分已确认资料、按公司检索的片段，以及不可附着的历史投标。知识库关闭或后两条失败时保留第一条并记录原因。该服务不连接 MySQL，也不连接 RAGFlow。详见[验证](testing/2026-10-12-evidence-candidates.md)与[签署](testing/2026-10-12-issue-016-retrieval-signoff.md)。

ISSUE-037 为 in-progress，ISSUE-029 保持 closed。AI-04、AI-05 与 AI-06 均为 in-review：AI-04 提供 CI 假 RAGFlow 服务并覆盖多种模式；AI-05 提供只读检索客户端并严格封装异常与零命中；AI-06 将 EvidenceCandidateService 的路径 B/C 切换为调用 RAGFlow，实现跨公司注入 dataset 隔离、路径 C 查询词过滤与不可附着、零命中/异常安全回退降级，离线单测 14 passed 1 skipped，全套回归 55 passed 3 skipped；并且打通章节 AI 生成与建议端到端闭环（test_chapter_generation_rag_flow.py 7 passed，全链路回归 75 passed 2 skipped），详见 [AI 流水线交付](delivery/AI-GENERATION-PIPELINE.md)。数据集生命周期和 `kb_sync` 不在本 Issue。重排使用 RAGFlow 的 `rerank_id`，不新增依赖。详见[AI-06 交付](delivery/AI-06.md)。

## 当前共同底座阶段

ISSUE-009 / APP-M2-T001已接可信会话和页面守卫：后台当前身份、导航/动作及最小项目权限真实读取，页面先核对再取业务数据；独立发现的撤权/迟到读取/连续切页问题已修复。262后台、72前端、真实会话HTTP16项、最终类型/构建及GUI通过，真实两册文件不含个人私稿，见[阶段交付](delivery/APP-M2-T001.md)。ProLayout、浏览器地址和编辑台未保存离开已由 QA 在 REV-M0-T11 签署通过。项目经理在群里确认后，APP-M2-T001 标为 done。ISSUE-009 已由项目经理在 QA 签署 d55d507（REV-M0-T11）后确认 closed。ISSUE-014 已由项目经理在 QA 签署 173c39f（REV-M0-T14）后确认 closed。资料列表/详情T046/047依赖的元数据表格/表单与敏感展示仍未验收，继续planned。业务库已决定为 MySQL 8，对话模型与 RAGFlow 的决定已登记，运行仍用内存和演示模型。未设置 `ICG_DATABASE_URL` 时同样如此，OIDC另在T010验收。证据见[布局复核](testing/2026-10-12-prolayout-routes.md)。QA 在 `200a105` 签署该切片不通过。浅色内容、顶栏和前进/后退已修复并再次提交 in-review。E2E-D7：侧栏默认仍收起，展开按钮已移到 logo 右侧，1280/1440/1680 浅色和深色可点开菜单。E2E-D8：次要文字对比度至少 4.5:1。见[修复复核](testing/2026-10-12-t001-layout-history.md)。ISSUE-020 已把外壳和项目页改为按路由加载，首屏主块 315.94 kB，低于引入 ProLayout 前的 1334.42 kB；项目经理在 QA 签署 dcca509（REV-M0-T15）后确认该 Issue closed。关联卡 APP-M2-T001 已为 done。见[分包复核](testing/2026-10-12-route-chunks.md)。

## 内网部署草案

ISSUE-017 / OPS-M0-T02 写了内网部署草案：现有单进程 uvicorn 提供接口和 `frontend/web/dist`，深链接由同一进程回到 `index.html`。业务库按 ISSUE-010 已登记的 MySQL 8、`utf8mb4` 书写备份与迁移回滚。向量库与对话模型的决定已写入已关闭的 ISSUE-010，适配器仍未实现。AI-03 的内存检索不因此改成 RAGFlow 客户端。重排定为 RAGFlow 自带，在 RAGFlow 内配置。没有环境、容器或新的 CI 步骤。BE-M0-T11 已依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done，多个进程可以共享这两类数据。编辑租约已提交复查。业务聚合仍未入库。ISSUE-017 已由用户 10-12 14:34 确认并 closed，OPS-M0-T02 为 done，不是已部署。见[草案](operations/intranet-deployment-plan.md)。

## 离线 CI 门禁

ISSUE-012 / APP-M2-T008 已把现有离线检查放进 GitHub Actions，并在提交 `cf2c2a1` 上跑通：pytest 262、会话 HTTP 15、`smoke_t06.py` 12、前端函数 72、构建、`.cjs` 35 与治理检查。Python 3.13.5，Node 24.9.0，pnpm 11.25.0。工作流不使用密钥或外网模型，也不调用 soffice。项目经理于 10-12 12:10 在 QA 签署后确认，卡片为 done，ISSUE-012 为 closed。这不是已部署，也不是已合入。`buildTheme` 仍未实现。见[验证](testing/2026-10-12-offline-ci.md)。ISSUE-025 / BE-M0-T14 另加 `backend-mysql`，已依据 QA 签署 `b20b844` 标为 done：运行器上的 `mysql:8.4` 只跑空迁移和 mysql 标记测试，密码不进仓库。junit 有任一跳过即失败。见[核对](testing/2026-10-12-backend-mysql-ci.md)。

## QA独立复跑

ISSUE-013 / REV-M0-T02于2026-10-12在独立Linux环境复跑：后台262、前端72、构建、治理/原型/同步/旧页及5个真实HTTP冒烟通过；会话实时HTTP按原描述重建15项并入库为[可重跑脚本](../tests/backend/session_live_http.py)，原16项为间接复核。前端测试需Node 24。见[复跑记录](testing/2026-10-12-qa-rerun.md)。

ISSUE-015 / REV-M0-T03已编制[APP-M1-T06验收计划](testing/2026-10-12-app-m1-t06-acceptance-plan.md)并评审通过；REV-M0-T04新增自启服务的`smoke_t06.py`（12/12）并首次在Linux渲染Word留证，发现无标题/编号/目录/页眉页脚等W1～W4，见[记录](testing/2026-10-12-t06-smoke-word-render.md)；T06本身仍in-progress。W1～W4 由 [BE-M0-T15](delivery/BE-M0-T15.md) 提交默认版式，用户已在 Word/WPS 目视 OK，PM 18:01 确认 done，ISSUE-027 已 closed。贯通脚本及其他缺口仍在。

## 当前契约阶段（2026-10-12）

ISSUE-005的DG-05拆成六张后端卡。错误体与单一状态码表[BE-M0-T02](delivery/BE-M0-T02.md)、24小时幂等回执[BE-M0-T03](delivery/BE-M0-T03.md)已由项目经理于 10-12 12:28 在 QA 签署后确认，标为 done。ISSUE-005 保持 in-progress：编辑租约迁到`/api/v1` 的 BE-M0-T04 为 in-review，导出快照 BE-M0-T05 为 in-review，202与SSE 的 BE-M0-T06 为 in-review，operationId 检查 BE-M0-T07 为 in-review，该 Issue 不关闭。`MODEL_UNAVAILABLE`固定502；`/api/v1`返回`{code, message, details, traceId}`，旧`/api`章节建议仍用`error`加`request_id`。前端请求层 APP-M2-T002 已由项目经理在群里确认、QA 签署后标为 done：追踪号优先读 `X-Request-ID`，章节版本提交的请求头与正文 `idempotency_key` 相同。带统一错误体且 code 为 MODEL_UNAVAILABLE 的 502，以及 code 为 SECRET_KEY_UNAVAILABLE 的 503，不自动重试，页面立刻用追踪号提示。只有 GET 和已经带 Idempotency-Key 的写入，才对网络错误、没有统一错误体的 502 和其他 503 重试。ISSUE-030 为 in-review，T002 仍为 done。没有键的旧写入第一次失败就停止；ISSUE-021 给这些接口补键之后这条限制解除。见[交付](delivery/APP-M2-T002.md)。业务库已决定为MySQL 8。[持久化方案](architecture/mysql-8-persistence-plan.md)已由项目经理批准，ISSUE-018 为 in-progress。[连接与空迁移](delivery/BE-M0-T10.md)与方案卡 BE-M0-T08 已由项目经理在 QA 签署 98c5129 后确认，标为 done。设置 `ICG_DATABASE_URL` 即可连接，未设置时测试仍用内存仓库。回执和登录会话由 [BE-M0-T11](delivery/BE-M0-T11.md) 依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done。编辑租约由 BE-M0-T12 依据 QA ae6fd10，PM 15:32 确认 done。聚合表仍未做。旧 `/api` 统一错误体登记为 ISSUE-021，任务 planned，排在该方案之后；其中 E2E-D5（`/API/...` 返回页面壳）也只登记，本轮不改兜底路由。向量库已定为 RAGFlow 自带，客户端未实现。PR #3 已合入。

ISSUE-019 / REV-M0-T06新增Playwright端到端检查（`pnpm --dir frontend/web e2e`，约40秒）；ISSUE-013 / REV-M0-T08对APP-M2-T001本切片签署**不通过**，见[记录](testing/2026-10-12-e2e-t001-signoff.md)。该签署结论保留。前端随后修复 D1–D4 并写明 D6。QA 重签新增 E2E-D7 后，展开按钮已可点，端到端 12 项通过。随后 REV-M0-T11 签署通过，项目经理在群里确认后 T001 标为 done，见[修复复核](testing/2026-10-12-t001-layout-history.md)。用户与项目经理确认 D3/D4 修复后，offline-check 的 `e2e` 作业改为必需，失败会阻断工作流。REV-M0-T06 与 REV-M0-T08 仍为 in-review。

## 用户指定的最新分支复核

2026-10-12以73fde1e隔离审查，复核快照9c178782，随后并入 foundation 9e3fcdd，保留后来新增的租约/项目持久化、证据抽屉、错误码、T114 冲突刷新、ISSUE-036 对比修正和 QA 交付。ISSUE-034 / REV-M0-T27 修复八项身份、导航、回执、租约和证据权限缺陷；密钥503重试由上游0a5b655修复，本轮保留验证。ISSUE-033 仍是挂证据规则，REV-M0-T22 仍是 T114 QA 且 done。部署旧说明已纠正，正文等仍在内存，继续单进程/单副本。本轮只复核与纠错，独立PR待审核，不改原里程碑签署事实，不把本卡标 done。实际证据见[复核](reviews/2026-10-12-foundation-review.md)与[验证](testing/2026-10-12-foundation-review.md)。

## 任务进度口径

治理版本g1.1，当前实际开发关联ISSUE-007及资料保护ISSUE-008；契约门禁关联ISSUE-005；模型与向量库决定已记入已关闭的 ISSUE-010，业务库已决定为 MySQL 8。项目412项中61done、13in-review、7in-progress、273planned、45blocked、13cancelled、0ready。OPS-M0-T02 已由用户 10-12 14:34 确认并标为 done。PRD、ROADMAP、PROJECT_BRIEF 改为里程碑快照 as of commit 3bb311ad3ab86c0de2f871876a50c7d50f9bb985，并计入 T001 与 T002 标为 done：389项52done、14in-review、7in-progress、265planned、48blocked、3ready。活计数以看板为准，现为 397 项、24 in-review（含 REV-M0-T32～T36、BE-M0-T06、BE-M0-T07、AI-04、AI-05 与 AI-06）。任务看板是准绳，三份基线只在里程碑更新。ISSUE-026 已把三份基线写成 8in-review、49blocked；本卡新增 BE-M0-T15 后 in-review 为 9。APP-M1的16项中9项本地done：T07范围拆分及T09～16限定子任务；T01～06完整父任务继续，T08最终审计planned，T16资料及模板旧表单保护本地done。[APP-M2的259项](tasks/APP-M2.md)中T001布局、路由和离开保护为 done，T002请求层为 done，T008离线CI为 done，T078 内存发布为 done（QA 19c4862，PM 17:20 确认）。页面未做，不挡住本卡。T114 挂证据抽屉为 done（QA f521950，PM 17:13 确认）。T124 仍为 ready，页面本轮不实现。ISSUE-022 已依据 QA 0254102（REV-M0-T20），PM 15:36 确认 closed。大纲 getOutlinePlan 与 confirmOutlinePlan 仍未接通。startGeneration 由 BE-M0-T06 提交 in-review。其余253项planned，覆盖47组页面和44规则，不代表软件已实现。BE-M0现为19项，其中T01～T03、T08、T10、T11、T12、T13、T14、T15为done，T15 Word 默认版式已由项目经理于 18:01 确认 done。用户已在 Word/WPS 目视确认。ISSUE-027 已 closed。T16 错误码名字为 in-review（QA REV-M0-T34 已签，等 PM），T04 编辑租约与 T05 导出快照为 in-review（QA REV-M0-T32/T33 已签，等 PM），T06 为 in-review（QA REV-M0-T36 tip `0cb6c38` 已签，等 PM），T07 为 in-review，T11 回执与会话已依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done，T12 编辑租约已依据 QA ae6fd10，PM 15:32 确认 done，T13 项目聚合已依据 QA ae38ec3，PM 17:16 确认 done，T17 编辑锁对齐字典为 planned，T18 证据挂接规则为 in-review（QA REV-M0-T35 已签，等 PM），T19 项目表对齐字典为 planned，T09 planned。T14 依据 QA 签署 `b20b844`。ISSUE-025 已 closed。ISSUE-023 已由项目经理在 QA 签署 16cf971 后确认，状态为 closed。T02与T03由项目经理于 10-12 12:28 在 QA 签署后确认。T08与T10由项目经理在 QA 签署 98c5129 后确认。ISSUE-005 保持 in-progress，不关闭。AI-01为in-review，AI-02为done，AI-03为done且不连接 MySQL 或 RAGFlow，AI-04、AI-05与AI-06为in-review，OPS-M0-T02内网部署草案已由用户 10-12 14:34 确认并标为 done，不是已部署。REV-M0-T05已记录QA签署；项目经理于 10-12 12:10 在 QA 签署后确认 AI-02 与 T008。REV-M0-T07已记录QA对BE-M0-T02/T03的签署。e2e 作业已改为必需。REV-M0-T06 与 REV-M0-T08 仍为 in-review。REV-M0-T11 已记录 QA 对 T001、T002 的复验签署通过。项目经理在群里确认后，这两张卡标为 done。REV-M0-T12 已记录 QA 对 BE-M0-T14 的签署通过，T14 已标为 done。REV-M0-T13 已记录 QA ISSUE-026快照规则签署，通过。项目经理在 QA 签署 9bcde17 后确认 ISSUE-026 closed，不新增任务卡。REV-M0-T14 已记录 QA ISSUE-014 ProLayout签署，通过。项目经理在 QA 签署 173c39f 后确认 ISSUE-014 closed，关联卡 APP-M2-T001 已为 done。REV-M0-T15 已记录 QA ISSUE-020路由分包签署，通过。项目经理在 QA 签署 dcca509 后确认 ISSUE-020 closed，关联卡 APP-M2-T001 已为 done。REV-M0-T16 已记录 QA ISSUE-016检索骨架签署，通过（被验对象状态待项目经理确认）。REV-M0-T17 已记录 QA ISSUE-028模型配置设计签署，通过（附P2）（被验对象状态待项目经理确认）。REV-M0-T18 已记录 QA ISSUE-031错误码名单冻结签署，通过。ISSUE-031 已依据 QA ae6fd10，PM 15:32 确认 closed。BE-M0-T16 仍 in-review（QA REV-M0-T34 已签 tip deca9de，等 PM）。REV-M0-T19 已记录 QA BE-M0-T12编辑租约入库签署，通过。BE-M0-T12 已依据 QA ae6fd10，PM 15:32 确认 done。REV-M0-T20 已记录 QA ISSUE-022契约冻结复签，通过（被验对象状态待项目经理确认）。REV-M0-T21 已依据 QA 3e91aee，PM 恢复确认 done。REV-M0-T22 已依据 QA f521950，PM 17:13 确认 done。缺协议、受限、智能匹配和规则 2 端到端仍挂 ISSUE-033，不关闭。REV-M0-T23 已依据 QA ae38ec3，PM 17:16 确认 done。BE-M0-T13 同步为 done。演示表对齐仍见 ISSUE-035。ISSUE-018 仍为 in-progress。REV-M0-T24 已依据 QA 19c4862，PM 17:20 确认 done。页面未做，不挡住 APP-M2-T078。REV-M0-T25 已记录 QA ISSUE-036 橙色标签对比签署，通过（被验 Issue 不标 done）。REV-M0-T26 已记录 QA ISSUE-033 规格增量契约复签，通过（当时运行时待后端；本提交已接通，ISSUE-033 改为 in-review，不标 closed）。REV-M0-T35 已记录 QA 对 tip `90b2334` 运行时重签，通过；ISSUE-033 / BE-M0-T18 仍 in-review，不标 closed。REV-M0-T27 / ISSUE-034：QA 已对 tip `5eced4f` 正式签署 R1～R9 通过（含真实 MySQL R4/R6/R7），状态仍 in-review，不标 done。REV-M0-T28 已记录 QA 对 BE-M0-T11（631d4c9）回执与会话入库签署，通过。BE-M0-T11 已依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done。ISSUE-018 仍为 in-progress。REV-M0-T28 仍为 in-review。REV-M0-T29 已记录 QA 对 ISSUE-028 AC-02 假端点夹具（9e3fcdd）签署，通过（ISSUE-028 / AI-01 不标 done；路径规范化 hold）。REV-M0-T30 已记录 QA 对 ISSUE-028 AC-03（证据 tip be3ce98 / 夹具 9e3fcdd）签署，通过（ISSUE-028 / AI-01 不标 done；AC-04 仍等 ISSUE-024）。ISSUE-030 仍为 in-review。PR待合入、未发布；BE-M0-T01只证明局部后台基础，FE-M0-T03继续来源评审，生产一期尚未验收。344项、20done、2in-review、7in-progress 是加入契约六张卡之前的计数。

资料库专项审查确认：当前只支持基础文字资料，确认声明、审核、受限名单、真实附件槽位、历史和引用版本仍缺。T16已修复资料及公司模板旧表单借刷新版本覆盖新内容的问题；完整C01/C06各卡继续planned，不能以修复代替其验收。

已完成首轮目录/原型修复FE-M0-T01和任务交付治理FE-M0-T02。前端59项中2项本地done、1项in-progress、8项planned、48项blocked；FE-M0完成2/10。两项交付均已在 PR #3 合入。任务计数不代表按工时加权的产品完成率。

每个done任务必须有交付、验收、代码解释和文档同步记录；PR合入/发布独立记录。逐任务证据见 [T01交付](delivery/FE-M0-T01.md)、[T02交付](delivery/FE-M0-T02.md)，规则见 [WORKFLOW](governance/WORKFLOW.md)。

T12/T13限定范围已本地验收：本章事实选择、要点与字数目标进入生成/整章建议共享输入，页面展示真实当次来源，变量写入、源改失效和两册内容实际验证通过。完整父任务继续，PR未合入。

## 已有实现

- 前端产品、架构、路线图和 UX 文档。
- 工作台、项目概览、响应矩阵、章节编辑四个静态视图。
- 矩阵筛选、抽屉、AI 建议与 Diff 确认、模拟保存、编辑锁与填写理由接管演示。

首个[后端demo](delivery/BE-M0-T01.md)已本地验收：真实公司权限、编辑权、草稿、版本、操作记录、基础检查和单章Word下载；模型/数据库有独立替换接口，当前为演示实现。该次31项后台测试、7项页面回归、12项记录检查测试、独立HTTP与页面下载通过，是旧交付证据。

当前[ICG接口约定](architecture/icg-reference-contract.md)对应正式构建的同源页面和后台。主流程已实际接通：上传、文字提取、人工确认、矩阵、候选、检查和两册下载；后台77项、前端9项、旧页7项及治理12项回归、实际HTTP和GUI均有[阶段验证](testing/2026-10-10-icg-reference.md)。新增旧草稿安全恢复、坏上传移除、北京时间边界和候选/资料重新核对保护。T06进入验收，各完整任务尚不计done。

其他47个来源页面/能力分组、完整规则、结构化编辑、正式定稿及版式仍须逐项交付，见[覆盖清单](testing/icg-coverage.md)。两册是内部稿，内容正确已核对，Word渲染失败导致视觉版式尚未验收。模型和数据库继续保留接口，内存数据重启清空。

## 本次数值服务承诺交付

模板、三方数值比较、保护式按招标取值、负责人核对、只读派生事实、正文变量及内部承诺函表格已经接通。后台119项（含42项独立SLA）、前端13项、最终服务实际HTTP及页面/Word内容验证通过，见[验收记录](testing/2026-10-10-sla.md)和[T09](delivery/APP-M1-T09.md)、[T10](delivery/APP-M1-T10.md)、[T11](delivery/APP-M1-T11.md)。概览现在计入需重新核对事实；旧单章出口不能绕过项目门禁。

完整故障等级、服务时段、独立承诺事实、完整R09/R10/R30及其他规则、结构化编辑和Word视觉仍未完成，原父任务不关闭。旧77/9是此前主流程阶段证据，当前测试数不能当产品完成比例。

## 本次写作输入交付

本章选定可选事实及全部必备事实、当前服务承诺、合格证据版本与内容已经进入模型接口实际输入；生成和整章修改建议共用一套组装逻辑。页面可以确认要点/字数、查看当次快照并插入事实变量。来源或方案变化后旧候选不可采用，旧检查/下载失效。后台168项、前端22项、构建、真实HTTP、页面操作与两册Word内容通过，见[验收记录](testing/2026-10-10-writing-input.md)及[T12](delivery/APP-M1-T12.md)、[T13](delivery/APP-M1-T13.md)。

上述168/22是T12/T13历史证据；当时manager统一确认的限制现由T14/T15补齐。输入快照仍为整章清单，完整知识片段、段落来源、选区助手与全文事实语义规则仍未完成；人工事实与原文语义矛盾不能靠当前来源页校验自动发现。模型为替身、数据库为内存，正式Word视觉和递交未验收。

## 本次多人协作交付

项目成员、参与分册、两册负责人、合标人和本节编写人已接通。项目负责人管全项目、分册负责人管本册、编写人办理本节；同公司未加入也不可读取。交接撤销旧编辑权，正文、历史及本人草稿保留，接手人看不到别人的私人草稿。各章独立保存/确认，不让未确认的商务章拖住已确认技术章。

后台210项、前端36项及构建通过；真实HTTP与多账号页面验证范围、冲突、撤权保留文字和两个Word下载。旧团队/基本信息/方案表单均保护已读依据；真实650→900并发反例通过。最终由合标人下载的技术1940字节、商务1943字节，已读文件内容确认只含各自已提交正文，不含私人草稿。见[验收记录](testing/2026-10-10-project-assignments.md)、[T14](delivery/APP-M1-T14.md)、[T15](delivery/APP-M1-T15.md)。规则和Word版式未因此计完成。

[T07范围交付](delivery/APP-M1-T07.md)保留190原WBS细项，补13独立资料/章节/文件产物及56规则实施验收单位；其中公司年度划型原WBS漏列，新增独立卡。原44规则的一期完整/简化/二期36/3/5范围保留。下一步按依赖接完整资料列表/详情、确认版本，再补各类别、片段、结构化编辑、循环任务和正式输出。

## 本次资料及模板旧表单保护

T16保留表单真正读到的公司、内容和版本；冲突保留填写，新旧并列核对；确认载入真实重新读取，二次变更仍拒绝。普通资料和模板各自保存同一次GET的集合及版本，切公司清除旧数据并防止迟到读取回填。全后台229、前端58项、类型/构建与独立复核通过；实际多人资料及模板反例和切乙公司空集合通过，6张截图见[验证](testing/2026-10-11-library-basis.md)及[交付](delivery/APP-M1-T16.md)。网络故障只做函数回归，没有在页面注入；完整审核、受限资料、附件和模板能力仍未完成。ISSUE-008本地closed，产品ISSUE-007继续，PR待合入、未发布。

## 首轮维护

将 UX 文档归入 `docs/design/`，将完整静态原型归入 `prototypes/bidding-ux/`；保留三个已有前端文档入口。新增目录方案、文档索引、已脱敏产品参考与差异清单。修复编辑锁期间 AI Diff 确认仍可写入的缺陷，验收见 [ISSUE-002](../issues/ISSUE-002.md)。

## 合作分支

[PR #1](https://github.com/Faith-Neil/if-children-have-been-grown/pull/1) 的 `xqr` 分支以系统三件套和技术选型为主，`main` 后续把同名三件套替换成了前端文档。PR 截至本轮读取仍未合并。需要先分别保存系统设计和前端实施视图，再核对技术决策与治理规则；评审见 [整合记录](reviews/pr-1-integration.md)。

本轮新增文档索引与 `xqr` 新增的同名索引整合时可能产生 add/add 冲突，按当前目录合并条目，保留其有效历史交付记录。

## 下一轮任务顺序

已确认一期交技术、商务两册，[一期交付建议](decisions/phase-one-scope.md)提供主流程与实施顺序。首个后端demo先验证账号、公司隔离、编辑权、草稿、版本、基础检查和Word；外部业务服务及生产环境在真正接入前另行明确。

1. 保留ICG示例布局，贯通项目、解析确认、响应矩阵、编辑、检查和技术/商务两册Word。
2. 对真实页面操作、权限、版本冲突、失效检查和导出文件做独立验收，逐任务形成交付与代码解释。
3. 按原始交接清单补齐其他页面、结构化编辑、一期完整/简化规则及分册定稿，未完成部分保留真实状态。
4. 示例不合理之处登记[差异记录](decisions/icg-reference-deviations.md)，完成对应流程后再修正；生产身份与部署另有明确验收门禁，模型和数据库本轮只保留接口。

具体目录和阶段验收见 [目录方案](architecture/repository-layout.md)。截至 2026-10-16，业务库已决定为 MySQL 8，嵌入与向量库定为 RAGFlow 自带。CI 假服务（AI-04）与只读检索客户端（AI-05）已提交 in-review，接线留待 AI-06。也未合并合作分支。AI-02 为 done：项目经理于 10-12 12:10 在 QA 签署后确认。它只增加可显式关闭的兼容适配器，默认模型仍是替身。AI-03 为 done，ISSUE-016 已依据 QA 签署 2fe6198（REV-M0-T16）标为 closed。检索口只在内存中运行，不连接 MySQL。运行数据仍在内存中。

## 全工作区与接手审查

本地Git根已提升到X:\ICG CO，原远端相对路径和历史保持；ICG34份项目资料原指纹34/34一致，两个银行合同根由用户明确排除，令牌/runtime在工作区外。同步工具已通过10项真实bare remote回归，治理回归现为12项通过；真实GitHub自动推送、远端修改快进获取及删除同步已验证，隐藏持续进程和Windows登录启动已配置，实际运行状态见 [操作说明](operations/workspace-sync.md)。

[接手brief](PROJECT_BRIEF.md)和业务/技术报告已形成：主要待定点是范围/生成单位、漏抽及关键引用门禁、SLA/敏感显示、依赖变更失效、API/租约/幂等/任务和导出快照。它们登记在 [ISSUE-005](../issues/ISSUE-005.md)，仍需共同确认与真实验证；完成审查不意味着产品或接口已经冻结。

2026-10-13增量复核固定b7b3191，REV-M0-T31 / ISSUE-034；11项必要后端专项通过，无新增确认阻断。复用原QA，不重复全套构建/浏览器/数据库/模型验收，标记见[本轮复核](reviews/2026-10-13-incremental-review.md)。PR #4已合入 foundation（merge `90b2334`）。QA 已对 tip `90b2334` 签署 BE-M0-T04/T05/T16/T18（REV-M0-T32～T35），均不标 done，等项目经理设置。QA 已对 tip `0cb6c38` 签署 BE-M0-T06（REV-M0-T36），不标 done，等项目经理设置。
