# PRD MVP v1.8 功能完备性审查与缺陷汇总

- 审查日期：2026-10-22（Asia/Shanghai）
- 权威基线：PRD MVP v1.8、字典 v1.9、`PROJECT_STATUS.md`、`TASK_BOARD.md`
- 代码证据：本机 `C:\Users\徐佳馨\if-children-have-been-grown`，分支 `feat/opencode-ICG`，审查时 tip `92ae99b`（含 WP-1 冻结规则与 WP-2 前端域目录搬家；工作区另有未提交文档/测试路径调整）
- 判定口径：**已交付**＝主路径可用且有可核对测试/交付；**部分交付**＝有真实能力但相对 PRD 明显缺口；**仅壳或演示**＝页面/导航/假数据存在但核心业务未接通；**未做**＝无可用实现或明确 Pending
- 结构债方案（`remediation-plan.md`）只作参考，**不计入功能完成**

---

## 1. 总判断

相对 PRD MVP v1.8，产品**远未完备**：按模块深度粗估完备度约 **28%～35%**（主链路“可演示走通”约四成壳，规则/资料/写作档案/平台运维等大块仍空）。  
看板约 397 项中 done≈52 是**任务卡完成率**，不能当产品完成率；`docs/testing/icg-coverage.md`（2026-10-11）与后续 AI/编辑/导出门禁增量对照后，主结论仍成立。  

**主链路卡点（产品视角）**：  
1）身份仍是 `synthetic-demo` + `legacy-demo-compat`（三角色会话），正式登录/密码策略/OIDC 未产品化；  
2）合规 **R01～R44** 未按编号落地，`IMPLEMENTED_RULES` 仅约 12 条工程门禁名，`UNIMPLEMENTED_RULES` 明确含「分册定稿/交叉复核/公司查重」等，递交版会被 `RULES_INCOMPLETE` 挡住；  
3）知识库、写作档案导航为 **PendingPage**；资料库仍偏基础文字条目；  
4）解析后处理缺「疑似遗漏/星号废标兜底扫描」完整闸门；章节循环进度页、人工队列独立页未接通。  

结论先行：**可做内网主流程演示与联调，不能按 PRD 宣称 MVP 可验收上线。**

---

## 2. 主流程验收表（§4.2）

| 步骤 | 状态 | 证据 | 相对 PRD 的缺口（一句） |
|---|---|---|---|
| 新建项目 | 部分交付 | `App.tsx` 新建弹窗；`/api/v1` 项目创建；`PROJECT_STATUS` 多账号范围 | 缺关联投标冲突 R19、项目大类/行业模板完整、6 张统计卡筛选 |
| 解析招标 | 部分交付 | `workflow` parse/confirm、冲突 resolve；`JobsPage`；上传失败移除 | 抽取后处理（疑似遗漏/兜底扫描/交叉引用）未齐；确认前门禁不全；OCR/扫描 PDF 未做 |
| 响应矩阵 | 部分交付 | Matrix 页、挂证据抽屉 `EvidenceDrawer`、SLA 子集 | 分册分流确认、得分要点子行、客观分→证明清单、偏离表未齐 |
| 资料/知识库 | 部分 / 壳 | `LibraryPages`、证据候选/RAG 测试；`nav===knowledge`→`PendingPage`；`snippet_publication` API | 资料确认/审核/附件槽位不全；方案片段与历史标书导入前端未接通 |
| 分节生成 | 部分交付 | `WritingPlanReview`→plan/confirm；`chapter_generation`+RAG 闭环测试；`/generation/start` 202/SSE | 缺独立章节循环进度页、系统生成五类表格章节、完整 3 轮闭环编排 UI |
| 编辑台 | 部分交付 | `EditorPage`、锁/草稿/版本、选区气泡、AI 建议采纳测试 | 对话助手 3～5 条样例+答案卡前端未完整；四栏布局/版本对比回退不齐 |
| 合规检查 | 部分交付 | Checks 页；`compliance_cross_check`；导出门禁测试；`IMPLEMENTED_RULES` | 非完整 44 规则；分册定稿/全文检查三场景与放行留痕未齐 |
| 导出 Word | 部分交付 | 两册下载、docx 默认版式、递交版 blocker/`SUBMISSION_FORBIDDEN` | 递交版因规则不全被禁；合标核对清单/暗标/完整模板版式未验收 |

---

## 3. 按模块能力对照（§3.1 / §5.1–5.12 / §6–8）

计数口径（MVP 能力块，共 **13**）：已交付 **0** · 部分交付 **9** · 仅壳或演示 **3** · 未做 **1**  
（细化页面级在缺陷清单中展开；无整块可标「已交付」。）

| 模块 | PRD | 状态 | 证据 | 缺口一句话 |
|---|---|---|---|---|
| 投标项目 | 5.1 | 部分交付 | 列表/概览/设置/团队；`test_eight_roles` 等 | 统计卡、复制项目、R19、完整状态机到已递交未齐 |
| 招标文件解析 | 5.2 | 部分交付 | 上传/解析/事实冲突/确认 | 10 类抽取与后处理闸门、点回原文坐标不全 |
| 响应矩阵 | 5.3 | 部分交付 | 矩阵+挂证据+SLA | 分册分流确认、覆盖率闸门、历史标书仅参考组体验需再核 |
| 企业资料库 | 5.4 | 部分交付 | 基础列表/元数据/SLA 模板 | 人员/授权/业绩/安全事件/工具设备等专页未做 |
| 知识库与方案片段 | 5.5 | 仅壳或演示 | 后端 snippet/RAG；前端 knowledge=Pending | 片段库/历史导入/按公司分库产品页未交付 |
| 公司写作档案 | 5.6 | 未做 | `writing`→PendingPage | 任务卡/风格样例/审查清单均无产品页 |
| 分节生成 | 5.7 | 部分交付 | 写作方案确认、生成/建议、输入快照 | 进度页、人工队列页、系统生成章节、观察指标未齐 |
| 合规检查 | 5.8 | 部分交付 | 工程门禁规则名+交叉核验服务+导出阻断 | R01–R44 编号体系与三场景定稿未实现 |
| Word 导出 | 5.9 | 部分交付 | 两册内部稿、版式、递交权限 | 递交版不可用；合标清单/水印策略/命名模板不全 |
| 编辑台与对话助手 | 5.11 | 部分交付 | 编辑锁、建议、`answer_card.py` 与多项测试 | Q27 答案卡/选区多样例前端与会话留痕产品化不足 |
| 管理后台 | 5.10 | 部分交付 | AuditLog、CompanyManage | 用户角色/字典/资料设置/模型开放页大多缺失 |
| 通用与平台运维 | 5.12 | 仅壳或演示 | demo 登录、Jobs 简版、Pending 规则说明 | 正式登录、站内提醒、全局搜索、规则配置、服务状态、品牌未做 |
| 模型与解析配置 | §6 | 部分交付 | `model_config_storage` API、敏感本地门禁测试 | 平台登记页/任务对应表 UI、解析适配器双端产品化不足 |

隔离与合规（§8）：后端有公司隔离与敏感项目本地模型门禁测试，但前端会话仍演示三角色，**不能视为 §8 已验收**。

---

## 4. 按优先级缺陷清单

### P0 — 产品阻断（挡 MVP 验收 / 递交）

| ID | 现象 | PRD | 证据 | 影响 | 建议负责人 |
|---|---|---|---|---|---|
| P0-1 | 合规规则未按 R01–R44 落地；递交导出因规则/分册定稿不全被拒 | 5.8、5.8.5、5.9 | `workflow.IMPLEMENTED_RULES` / `UNIMPLEMENTED_RULES`；`RULES_INCOMPLETE`；`test_checks_export_blocker_gate.py` | 无法出正式递交版 | 后端 + QA |
| P0-2 | 登录/会话强制演示模式，仅 manager/editor/viewer | 5.12.1、2.2、2.3、Q28 | `types.ts`/`session-navigation.ts`：`synthetic-demo`+`legacy-demo-compat`；`/api/demo/login` | 不能当正式私有化产品 | 前端 + 后端 |
| P0-3 | 未设 `ICG_DATABASE_URL` 默认回落 Memory | 7.1、7.5 | `database.repository_from_environment`→`MemoryRepository()`；门禁仅在 `ICG_REQUIRE_MYSQL=1` 时强制 | 「测通」≠可恢复生产路径 | 后端 + OPS |
| P0-4 | 写作档案、知识库产品页未接通 | 5.5、5.6、3.1 | `App.tsx`：`knowledge`/`writing`→`PendingPage` | 生成质量与检索主能力不可用 | 前端 + AI |
| P0-5 | 分册定稿 + 交叉复核 + 全文检查闸门未实现 | 4.2、5.8.5 | `UNIMPLEMENTED_RULES` 含交叉复核和完整分册定稿 | 主流程无法到达「可导出」正轨 | 后端 + PM |

### P1 — 体验与权限

| ID | 现象 | PRD | 证据 | 影响 | 建议负责人 |
|---|---|---|---|---|---|
| P1-1 | 后端八角色归一 vs 前端会话三角色 | 2.2、2.3 | `project_access.py` 八角色；`trustedApplicationSession` 只认 manager/editor/viewer | 权限语义分裂，误授/误拒 | 前端 + 后端 |
| P1-2 | 人工处理队列、章节循环进度为 Pending/缺页 | 5.7.6、5.7.7 | `tab==='manual'`→Pending；coverage 表 | 闭环问题无处集中处理 | 前端 |
| P1-3 | 对话助手答案卡/多样例偏后端，编辑台 UI 不完整 | 5.11、5.11.15 | `answer_card.py`、`test_answer_cards.py`；Editor 仍以整章建议/选区指令为主 | Q27 验收达不到 | 前端 + AI |
| P1-4 | 项目列表无 PRD 六统计卡与筛选 | 5.1.1 | coverage / `ProjectListPage` 现状 | 风险发现效率低 | 前端 |
| P1-5 | 全局搜索、站内提醒、规则配置、服务状态、界面品牌缺失 | 5.12.2～5.12.7 | 无对应完整页；规则 Tab 为说明 Pending | 运维与治理体验空洞 | 前端 + 后端 |
| P1-6 | 演示账号硬编码 alpha/beta | 7.2、8.1 | `adapters.py` Account 列表 | 污染正式环境认知 | 后端 |

### P2 — 范围债（相对 MVP 应有、现为简化）

| ID | 现象 | PRD | 证据 | 影响 | 建议负责人 |
|---|---|---|---|---|---|
| P2-1 | 资料库专类页（人员/授权/业绩/事件/设备等）未做 | 5.4 | coverage K-04～K-14；基础 library 文本 | 证据与资格响应不完整 | 前端 + 后端 |
| P2-2 | 解析后处理疑似遗漏/兜底扫描未齐 | 5.2.4 | 冲突 resolve 有；scan_hit 产品流未见 | 漏抽导致废标风险 | 后端 + AI |
| P2-3 | 系统生成章节（点对点/索引表/偏离表等）未做 | 5.7.2、5.11.8 | coverage「系统生成章节」未实现 | 合标与格式文件缺口 | 后端 |
| P2-4 | 内部稿/递交版命名、合标核对清单、暗标处理不全 | 5.9 | 导出有 kind；清单/暗标未见完整交付 | 商务合标成本高 | 后端 + PM |
| P2-5 | R18/R29 查重、R19 关联投标等未产品化 | 5.8.1、8.2、8.3 | 规则表多为未实现；R 编号代码中极少 | 串通/重复风险失控 | 后端 + QA |
| P2-6 | 模型配置有 API，缺完整平台配置页与解析双适配器产品化 | §6 | `model_config_storage`；coverage A-08～A-10 | 运维无法自助换模 | 前端 + AI |

### P3 — 工程债（不直接等于功能，但拖垮交付可信度）

| ID | 现象 | PRD/工程 | 证据 | 影响 | 建议负责人 |
|---|---|---|---|---|---|
| P3-1 | 包名/`/api/demo` 双轨、双错误体 | 契约、可维护性 | `main.py` demo 路由；remediation P0-4 | 前端易踩旧路径 | 后端 |
| P3-2 | OpenAPI 单文件过大易漂移 | 契约 | remediation：demo-v1≈889KB | 难审难 diff | 后端 |
| P3-3 | 前端测试目录双份 | 质量 | `frontend/web/tests` 与 `tests/frontend` | 漏跑 | QA + 前端 |
| P3-4 | `PROJECT_STATUS` tip 滞后 | 治理 | 文档仍写 `94be240`，实际已过 `9922c42`/`92ae99b` | 进度失真 | PM |
| P3-5 | 后端巨石 `database.py`/`workflow.py`、曾用 demo 平铺 | 可维护性 | remediation；WP-2 仅前端搬家 | 迭代成本高 | 后端 |
| P3-6 | 真实模型/RAG 默认跳过，CI 假服务 | §6、验收 | `ICG_RUN_REAL_*` 门禁；AI-01 in-review | 易误认「已接通生产模型」 | AI + QA |

---

## 5. 「看似有其实不完整」清单

| 表象 | 实际 | 证据 |
|---|---|---|
| 有登录页 | `/api/demo/login` + 合成账号，非 Keycloak/正式密码策略 | `App.tsx` login；adapters 演示账号 |
| 侧栏有「知识库」「写作档案」 | 一律 `PendingPage`「尚未实现」 | `App.tsx` 614 行附近 |
| 后端八角色测试通过 | 前端会话仍强制三角色 legacy | `test_eight_roles_access.py` vs `trustedApplicationSession` |
| MySQL/Alembic 已有 | 未配 URL 仍 Memory；生产需显式 `ICG_REQUIRE_MYSQL` | `repository_from_environment` |
| 有挂证据/RAG/生成闭环 | 默认假模型/假 RAG；真实端点需开关且未验收 done | AI-GENERATION-PIPELINE in-review；CI skip |
| 有合规检查页与导出门禁 | 工程门禁≠44 条规则；递交仍 RULES_INCOMPLETE | IMPLEMENTED/UNIMPLEMENTED_RULES |
| 有答案卡服务与测试 | 编辑台对话助手产品交互未齐（样例数、答案卡插入、知识库开关 UX） | answer_card 后端 vs Editor UI |
| 有任务中心 | 同步任务列表；排队/取消/断点恢复明确未做 | `JobsPage` Alert 文案 |
| 有审计/公司管理入口 | 塞在 `admin.rules` Tabs；规则配置本身仍 Pending | `App.tsx` admin.rules Tabs |
| 有「人工处理」页签 | Pending 说明，非 5.7.7 队列 | `tab==='manual'` |
| 覆盖清单/看板 done 很多 | 任务卡/历史切片，非 PRD 页面验收关闭 | TASK_BOARD；coverage 仍大量「未实现」 |
| WP-2 目录整齐 | 无行为搬家，不增加功能完备度 | tip `92ae99b` 提交说明 |

---

## 6. 建议下一轮产品优先级（最多 8 条，可执行）

1. **定稿闸门产品化**：实现分册检查→交叉复核→分册定稿→全文检查状态机，打通递交前正轨（对应 P0-5/P0-1）。  
2. **规则最小可递交集**：按 PRD ● 项排出第一批（至少 R15/R23/R01 引用门禁、R09/R10 SLA、占位符、导出门禁），编号与检查结果对齐，去掉「用内部稿冒充递交」。  
3. **身份去演示化**：会话改为正式角色模型（八角色），收敛 `/api/demo/login`；密码策略按 Q28 落地或明确「仅内测」。  
4. **生产强制 MySQL**：默认或部署清单强制 `ICG_REQUIRE_MYSQL=1` + URL，禁止静默 Memory。  
5. **写作方案/生成/编辑台主路径 UX**：补章节循环进度与人工队列最小页；对话助手样例+答案卡接到编辑台。  
6. **知识库最小闭环**：方案片段发布/同步页接通已有 `snippet_publication` API；历史标书导入可后置但要标「未交付」。  
7. **解析确认闸门**：补疑似遗漏处理与确认前强制清零冲突/遗漏（5.2.4）。  
8. **看板与 coverage 校准**：按本报告重标页面状态；禁止用任务 done 数对外报「功能完成度」。

---

## 7. 计数摘要（供上报）

| 维度 | 数量 |
|---|---|
| MVP 模块块（§3.1 表） | 13 |
| 已交付 | **0** |
| 部分交付 | **9** |
| 仅壳或演示 | **3** |
| 未做 | **1** |
| 主流程 8 步 | 已交付 0 · 部分 7 · 壳/Pending 1（人工队列步并入生成/检查） |
| P0 / P1 / P2 / P3 缺陷条数 | 5 / 6 / 6 / 6 |
| 后端测试文件（约） | 55 个 `test_*.py`，约 507 条用例（能力≠完备） |

**本文件路径**：`/workspace/prd-audit/2026-10-22-prd-gap-summary.md`
