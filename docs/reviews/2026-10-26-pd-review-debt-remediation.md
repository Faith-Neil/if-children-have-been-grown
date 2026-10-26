# 2026-10-26 两轮治理与技术债重构批次产品视角对照验收报告（PD 对照）

- **审查日期**：2026-10-26（Asia/Shanghai）
- **审查人**：PD｜产品验收 subagent
- **审查基准**：
  - PRD MVP v1.8（§4.2 主流程验收表、§2.2/§2.3 八角色体系、§5.2~§5.11 核心功能链路、§7.1/§7.5 持久化保障、§8 多租户强隔离）
  - 数据字典 v1.9（`kb-data-dictionary-v1.9.md`：`rule_level`、`export_kind`、`compliance_issue`、`bid_export`、`bid_volume`）
  - PRD 缺口总结（`docs/delivery/2026-10-22-prd-gap-summary.md`，理解 28%~35% 完备度口径与真实缺口）
  - 核心交付物：
    - `docs/delivery/2026-10-26-persistence-and-error-body.md`
    - `docs/delivery/2026-10-26-backend-unflatten-progress.md`
    - `docs/delivery/2026-10-26-frontend-react-router.md`
    - `docs/delivery/2026-10-26-ragflow-kb-sync.md`
    - `docs/delivery/2026-10-26-product-gap-kb-rules-smoke.md`
    - `docs/delivery/INT-VOLUME-FINALIZE-GLUE.md`
  - 用户官方拍板决策：B1（包重命名与分层）、B2（React-Router）、B4（`/api/demo` 废弃与 Sunset 2026-11-15）、B5/B6（内网私有化、无公网依赖）

---

## 一、产品视角核心核验点审查

### 1. 关演示与持久化底线（绝无假数据糊弄）
- **口径核对**：在 `VITE_DEMO=0`、`ICG_ALLOW_DEMO_LOGIN=0` 与 `ICG_REQUIRE_MYSQL=1` 的生产模式下：
  - 系统彻底阻断历史 demo 登录端点 `/api/demo/login`（HTTP 403 `FORBIDDEN`，附带 `Deprecation: true` 与 `Sunset: Sun, 15 Nov 2026 00:00:00 GMT` 响应头）；
  - 会话必须通过正式 Bearer Token 接入，并准确签发 `auth_mode="authenticated"` 与 `role_mode="rbac-8roles"`；
  - 持久化方面，`MysqlConnectionRepository.transaction()` 接入增量快照脏检查，在单个数据库事务中原子同步 `sessions`、`leases`、`projects`、`teams`、`demo_chapter`（正文）、`demo_chapter_version`（版本）与 `demo_check`（检查结果），彻底杜绝了内存回落。

### 2. 导出双门禁体系的强制性（RULES_INCOMPLETE 与 CHECK_BLOCKER_EXISTS）
- **口径核对**：
  - **Blocker 强拦截**：任何未确认响应、未映射章节、映射章节正文为空/包含待补、缺少已核验资质证据的废标红线与关键星号条款，在检查引擎中均被赋予 `blocker` 级别；在正式递交导出（`kind="submission"`）时被严格拦截返回 HTTP 400 `CHECK_BLOCKER_EXISTS`；
  - **分册未定稿拦截**：前端 `canExportSubmission` 与后端分册状态机紧密联动，若导出范围分册未全部定稿，正式递交按钮被强行禁用，拦截提示清晰；
  - **未全量规则诚实底线**：即使消除全部 blocker 并完成分册定稿，由于 PRD 规定的 44 项规则目前仅第一批核心 7 项（R01, R02, R15, R23, R34, R35, R37）落地，系统绝不弄虚作假放行正式递交，严格返回 HTTP 409 `RULES_INCOMPLETE`，守住了严肃的合规底线；
  - **内部评审稿放行**：`kind="internal_review"` 允许放行供团队审阅，但快照必须标记 `has_blockers=True`，并注入强合规警示 notice。

### 3. 知识库防编造与真实内网 RAGFlow 依赖留证
- **口径核对**：
  - 知识库与方案片段管理已在 `frontend/web/src/library/` 真实落地，并以青底深青字 Tag 对 `{{variable_name}}` 占位符进行自动高亮渲染；
  - 数据集强制注入 `${company_id}::` 前缀强隔离，杜绝跨租户数据串扰；
  - **真实连通性诚实留证**：针对真实内网 RAGFlow 服务（`192.168.100.212:9380`），交付文档记录了详实的网络探针诊断结果：由于宿主机 VPN 网卡虚拟 TUN 劫持导致传输层回握手但应用层 ReadTimeout，真实内网处于不可达状态。系统恪守防编造、防伪造红线，门控 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 诚实保持跳过，严禁伪造测试绿灯。

### 4. 两卷（技术卷、商务卷）导出 Word 文件合法性与 SHA-256 防伪指纹
- **口径核对**：
  - 导出下载的文件为真实的 OpenXML 格式 `.docx` 文档（`application/vnd.openxmlformats-officedocument.wordprocessingml.document`）；
  - 解包核验证实包含合法的 `[Content_Types].xml` 与 `word/document.xml`，正文与章节标题真实落地；
  - 快照注入 64 位十六进制 SHA-256 内容哈希指纹（正则匹配 `^[a-f0-9]{64}$`）与完整的 BE-M0-T15 Word 默认版式元数据（A4 纵向、上下 2.54cm / 左右边距、28pt 行距、560 缇缩进、正文仿宋、标题黑体/方正小标宋），防篡改与审计溯源能力完备。

---

## 二、产品对照矩阵表

| 卡ID | PRD 条款 / Gap 对应项 | 验收判定（通过/部分通过/阻塞） | 产品依据与证据摘要 | 是否书面认可建议 PM 标 done |
| :--- | :--- | :---: | :--- | :---: |
| **BE-TECH-DEBT-01** | PRD §7.1、§7.5 / Gap P0-3 (生产持久化收口与双向落库) | **通过** | `ICG_REQUIRE_MYSQL=1` 生产门禁生效，静默 Memory 回退被彻底拦截；章节正文、历史版本与检查记录纳入统一数据库事务落盘；`test_mysql_gate.py` 11 项全绿。 | **书面认可**<br>建议 PM 标 done |
| **BE-TECH-DEBT-02** | 架构分包规范 / 拍板 B1、B4 (架构分包与旧端点废弃门禁) | **通过** | 35 个根级文件降为超轻量 Façade（代码行数锐减 97.1%），主实现迁入 `icg/{api,app,domain,infra}`；旧 `/api/demo` 端点全量注入 RFC 8594 `Sunset: Sun, 15 Nov 2026 00:00:00 GMT` 与 `Deprecation: true` 响应头；统一优先解构标准错误体；OpenAPI 100% 一致。 | **书面认可**<br>建议 PM 标 done |
| **FE-REACT-ROUTER** | PRD §2.2/§2.3、§4.2 / 拍板 B2 (生产路由接入与八域页面挂载) | **通过** | 全面升级为现代 React-Router 体系；支持 `/projects/:projectId/editor/:chapterId` 编辑器深链接；可信 `AuthGuard`（未认证跳转登录、8 角色越权拦截）与 `DirtyGuard`（离开保护）；`VITE_DEMO=0` 默认走真实会话；前端 395 项单测全绿。 | **书面认可**<br>建议 PM 标 done |
| **AI-RAGFLOW-KB-SYNC** | PRD §5.5、§8 / 拍板 B5/B6 / Gap P0-4 (知识库与 RAGFlow 数据集同步机制) | **通过** | 支持方案片段结构化摄入与 `${company_id}::` 强租户前缀隔离；对上游异常实现优雅降级；内网代理强制 `trust_env=False`；真机连通性如实记录网络诊断证据并保持诚实门控，绝无假绿灯；专属测试 10 项全绿。 | **书面认可**<br>建议 PM 标 done |
| **BE-COMPLIANCE-RULES-P0** | PRD §5.8.1、§5.10 / Gap P0-1 (合规规则库 P0 扩充与废标拦截) | **通过** | 落地 R01、R02、R15、R23、R34、R35、R37 七大核心规则；关键条款缺陷严格赋予 `blocker` 并集成至 `run_check`；诚实维持未全量规则 409 `RULES_INCOMPLETE` 底线门禁；`test_compliance_rules.py` 5 项全绿。 | **书面认可**<br>建议 PM 标 done |
| **REV-SMOKE-001** | PRD §4.2、§5.9 / Gap P0-2 (关演示全流程端到端冒烟验证) | **通过** | 在 `VITE_DEMO=0` + `ICG_REQUIRE_MYSQL=1` 环境下，真实跑通「正式 Token 登录与 8 角色鉴权 → 项目创建与团队分工 → 上传与解析确认 → 矩阵与证据挂接 → 分节生成落地 → 真实两卷 Word 导出及 64 位 SHA-256 指纹挂载」；`test_smoke_non_demo_pipeline.py` 3 项全绿。 | **书面认可**<br>建议 PM 标 done |
| **INT-VOLUME-FINALIZE-GLUE** | PRD §5.8.5、§5.9.1 / Gap P0-5 (分册定稿端到端胶水与状态机打通) | **通过** | 分册定稿流转（排他锁、正文空缺、blocker 缺陷前置拦截）与先解锁后修改生命周期闭环；工作台概览与编辑台实时联动定稿徽章，已定稿分册禁用取得编辑权；导出中心未全部定稿前严格禁用递交版生成；测试全绿。 | **书面认可**<br>建议 PM 标 done |

---

## 三、产品视角综合结论与后续建议

1. **综合验收结论**：
   - 经深入对照 PRD MVP v1.8 与数据字典 v1.9，本轮涉及的 **7 张技术债与业务核心卡片全部真实达成产品意图与质量底线**；
   - 绝无“假测试绿灯”、“假演示数据糊弄”或“伪造递交导出”；
   - **PD 正式书面认可上述 7 张任务卡，建议主 Agent 向人类 PM 推荐将这 7 张卡在看板中统一标为 `done`**。

2. **后续里程碑演进建议**：
   - **定稿前交叉复核机制（Cross Review）**：继续深化分册定稿流程，增加非本分册编写人通读并签署确认的交叉复核留痕（PRD §5.8.5 `cross_review_required` 策略）；
   - **合规规则第二批扩写（R09/R10 SLA 与金额承诺、R36 跨分册人员一致性、R39 安全合规事件披露）**：逐步扩大已实现规则集，稳步推进至完全具备正式递交上线条件；
   - **私有化内网环境真机部署**：待协调公司私有网络路由打通（消除 VPN 代理阻断）后，在真实部署节点移除门控，直接连通 `192.168.100.212:9380` 真实 RAGFlow 知识库生产服务。
