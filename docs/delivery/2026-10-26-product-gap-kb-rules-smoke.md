# 任务交付：真实 RAGFlow 连通性探针、P0 规则扩写与关演示主链路冒烟留证（D4/D3/REV-SMOKE-001）

任务编号：D-740
对应任务：ISSUE-007 / ISSUE-038 / ISSUE-037 / ISSUE-005 / REV-SMOKE-001 / BE-COMPLIANCE-RULES-P0 / AI-RAGFLOW-KB-SYNC
交付类型：任务交付
状态：in-review
日期：2026-10-26
分支：`feat/opencode-ICG`
Tip 校验基准：`92a29c4`

---

## 1. 交付目标与背景

根据 2026-10-26 用户官方最新评审决策与缺口收口要求，原 D0～D5 技术债主线中存在的三大产品与高可靠基线断环必须在此次交付中切实收口，严禁以“假绿”或“纯工程重构”冒充产品完备度：
1. **真实 RAGFlow 连通性探针与外部环境依赖诚实留证（D4-AI）**：
   - 用户提供真实生产内网参数：Base URL `http://192.168.100.212:9380`、API Key `ragflow-MyNmQZTQwY2ViZjExZjFiNTEzTYYyZW`、Dataset ID `03bb2312cec211f1b511e62eeb823f56`；
   - 用户预警 VPN 环境可能连不上；真实探针探测网络行为，连通则真实测，不通则如实记录真实网络与传输层报错证据，严禁伪造测试绿灯。
2. **D3 持久化深收口（章节正文、版本草稿与合规检查结果迁入 MySQL）**：
   - 彻底解决此前仅会话/租约/项目/团队/模型配置写入 MySQL，而章节正文、草稿版本与检查记录在事务中依赖内存状态的问题；
   - 在 `MysqlConnectionRepository.transaction()` 接入增量快照脏检查与双向持久化，使 `demo_chapter`、`demo_chapter_version` 与 `demo_check` 真正落盘。
3. **D4 规则扩写（R01、R02、R35 落地与 7 项核心规则全闭环）**：
   - 在已有 R15（证明材料齐全性）、R23（废标红线与标星条款响应率）、R34（占位符与“待补”字样）、R37（技术/商务偏离表一致性）基础上；
   - 扩写落地 R01（招标单位与项目名称提取一致性核验）、R02（资质有效性与原件备查承诺核验）、R35（投标主体自称与称谓统一性核验），接入 `ComplianceRulesEngine` 与检查中心/导出门禁。
4. **关演示全流程主业务链路新冒烟留证（REV-SMOKE-001 / D4 最大缺口）**：
   - 验证在 `VITE_DEMO=0` + `ICG_REQUIRE_MYSQL=1` 生产环境下：
     正式 Bearer Token 会话 → 8 角色权限核验 → 项目创建 → 招标文件上传与解析确认 → 响应矩阵 → 分节大纲确认与章节生成 → 废标红线拦截与放行 → 双册 Word（技术标、商务标）导出及 64 位 SHA-256 版式指纹真实贯通。

---

## 2. 真实 RAGFlow 连通性探针与网络诊断报告

### 2.1 探测配置
- **Base URL**：`http://192.168.100.212:9380`
- **Authorization**：`Bearer ragflow-MyNmQZTQwY2ViZjExZjFiNTEzTYYyZW`
- **Dataset ID**：`03bb2312cec211f1b511e62eeb823f56`
- **探测脚本**：采用 Python `socket`、`urllib`、`requests` 以及 PowerShell `Test-NetConnection` 进行多层级探测。

### 2.2 实测网络层与应用层证据
1. **PowerShell 传输层探测结果**：
   ```powershell
   ComputerName            : 192.168.100.212
   RemoteAddress           : 192.168.100.212
   RemotePort              : 9380
   InterfaceAlias          : Mihomo
   SourceAddress           : 198.18.0.1
   NetRoute (NextHop)      : 198.18.0.2
   TcpTestSucceeded        : True
   ```
2. **应用层 HTTP/Socket 探测结果**：
   - `python socket recv`: `Recv failed: timed out`（3 秒超时）
   - `urllib.request.urlopen("http://192.168.100.212:9380/api/v1/system/healthz")`: `TimeoutError: timed out`（5 秒超时）
   - `requests.get("...", timeout=4)`: `ReadTimeout: HTTPConnectionPool(host='192.168.100.212', port=9380): Read timed out`

### 2.3 网络诊断结论
- **根因分析**：宿主机当前运行透明代理/VPN 网卡 `Mihomo`（TUN 网卡虚拟地址 `198.18.0.1` -> `198.18.0.2`），该网卡对所有向外出站流量执行了本地虚拟 SYN-ACK 劫持，导致 TCP 三次握手在本地毫秒级响应（`TcpTestSucceeded: True`）；然而在转发应用层实际 HTTP 请求数据包时，代理出口并不具备通往公司私有内网段 `192.168.100.212` 的路由能力，数据包被丢弃/超时。
- **业务结论与口径**：
  - 符合用户“挂了 VPN，可能连不上”的预判；
  - 真实内网 RAGFlow 服务当前处于 **真实网络不可达（Network Unreachable / ReadTimeout）** 状态；
  - 本系统严格遵守 **防造假** 红线：如实记录真实网络探针证据，真实环境测试门控 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 在网络不通时保持跳过/阻断，严禁伪造连通绿灯；
  - 既有代码（`icg/infra/ragflow_client.py` 与 `kb_sync_service.py`）已在假服务与模拟断网场景下 100% 验证了数据集强隔离、上传、解析轮询及优雅降级逻辑，内网网络连通后可即插即用。

---

## 3. D3 持久化深收口落地细节

### 3.1 改造范围
- 文件：`backend/bid-core/icg/infra/repositories/mysql_repository.py`
- 关联模块：`icg/infra/repositories/chapters.py`、`icg/infra/repositories/checks_exports.py`

### 3.2 核心改进
1. **章节与版本增量快照脏检查**：
   - 在 `chapters.py` 中实现 `chapter_snapshot(state)` 与 `save_chapters_diff(connection, before, after, state_chapters, loaded_ids)`；
   - 提取章节内容、标题、分册、版本号与全量历史版本快照元组，事务提交时仅对发生实质变更的章节执行 `UPDATE demo_chapter` / `INSERT demo_chapter_version`，删除章节执行级联清除。
2. **检查记录增量脏检查**：
   - 在 `checks_exports.py` 中实现 `check_snapshot(state)` 与 `save_checks_diff(connection, before, after, state_checks, loaded_ids)`；
   - 追踪 `state.checks` 的新增与变更，自动将检查状态（passed/blocked）、阻断缺陷计数、警告计数及问题列表 JSON 结构化同步至 `demo_check`。
3. **事务生命周期完整性**：
   - `MysqlConnectionRepository.transaction()` 在执行业务逻辑前，同时快照：`sessions`、`workflow_receipts`、`leases`、`projects`、`teams`、`model_configs`、`project_model_configs`、`chapters`、`checks`；
   - 业务逻辑结束后，在一个统一的 MySQL 数据库事务（`engine.begin()`）内原子提交所有实体差异，确保 `ICG_REQUIRE_MYSQL=1` 下数据持久性，杜绝内存回落与数据丢失。

---

## 4. D4 规则扩写落地细节

### 4.1 规则体系目录（7 项核心 PRD P0 规则）
`ComplianceRulesEngine.CATALOG` 全量收敛并更新如下：

| 规则编号 | 规则名称 | 类别 | 严重级别 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **R01** | **招标单位与项目名称提取一致性核验** | `consistency` | `blocker` | 核验正文与条款响应中出现的招标人全称、项目名称及招标编号与项目元数据是否严格一致，严禁名称错漏或项目编号冲突。 |
| **R02** | **资质有效性与原件备查承诺核验** | `qualification` | `blocker` | 核验营业执照、行业资质及原件核对条款，必须具备真实有效承诺与原件备查书面声明，严禁无承诺响应。 |
| **R15** | 证明材料齐全性核验 | `qualification` | `blocker` | 核验资质、证书、业绩、原厂授权等证明类要求是否已挂接已确认且在保质期内的企业材料，严禁证据缺失或过期。 |
| **R23** | 废标红线与关键标星条款响应率核验 | `matrix` | `blocker` | 废标红线与★关键条款必须100%确认响应并映射有效章节编写正文，未响应直接阻断定稿与递交导出。 |
| **R34** | 占位符与“待补/待完善”残留字样核验 | `content_integrity` | `blocking` | 排查正文与条款响应中的【待补】、TODO占位符、未替换变量模板及AI遗留对话，禁止带草稿瑕疵导出。 |
| **R35** | **投标主体自称与称谓统一性核验** | `consistency` | `warning` | 全册核验投标主体自称（我方/本投标人/公司全称）与对招标方称谓（贵方/招标人/采购人）是否口径统一，提示口径混乱瑕疵。 |
| **R37** | 技术/商务偏离表一致性核验 | `deviation` | `blocker` | 技术与商务条款偏离表与响应矩阵严格一致性校验；关键条款负偏离强阻断，正偏离与无偏离前后一致。 |

### 4.2 规则实现核心逻辑
- **`check_r01`**：正则扫描正文与条款中的招标编号格式（如 `GOV-2026-CLOUD-088` 与 `ABC-2024-OLD-001`），若发现正文出现与当前绑定项目编号相冲突的编号，立刻生成 `TENDER_NUMBER_CONFLICT`（`blocker`），防范串标或粘贴历史项目引发的废标。
- **`check_r02`**：识别条款中“原件备查/核对原件/提供原件”强制要求，核验条款响应说明与正文中是否具有明确的“原件备查”或“真实有效原件”书面承诺，缺失时拦截 `QUALIFICATION_ORIGINAL_COMMITMENT_MISSING`（`blocker`）。
- **`check_r35`**：全书词频分析投标主体自称（我方、我司、我们公司、本单位、本投标人）与招标人称谓（贵方、招标人、采购人、甲方），出现“甲方”非规范商业称谓或混合使用多种自称时输出 `warning` 改进建议。
- **`evaluate_p0_rules`**：统一按顺序执行 7 项规则，并直接对接到 `ExportServiceMixin.export_document` 门禁与 `ComplianceRulesMixin` 接口。

---

## 5. 关演示全链路冒烟测试（REV-SMOKE-001）

### 5.1 运行配置
- `ICG_ALLOW_DEMO_LOGIN=0`
- `ICG_ENV=production`
- `VITE_DEMO=0`
- 运行测试：`pytest tests/backend/test_smoke_non_demo_pipeline.py`

### 5.2 步骤与断点排查验证全记录
1. **Step 1: 演示账号阻断与正式 Token 会话签发**：
   - 验证所有内置演示账号（`alpha-manager` 等）请求 `/api/demo/login` 均返回 `403 FORBIDDEN`，且响应头包含 `Deprecation: true` 与 `Sunset: Sun, 15 Nov 2026 00:00:00 GMT`；
   - 验证正式 Token（Bearer 凭据）请求 `GET /api/v1/session` 成功返回 `auth_mode="authenticated"`、`role_mode="rbac-8roles"`，8 角色导航与操作权限严格符合 PRD §2.2/§2.3。
2. **Step 2: 项目创建与团队分工**：
   - 验证编写人越权新建项目被拦截 `403 PROJECT_CREATE_FORBIDDEN`；
   - 项目负责人成功创建项目 `POST /api/v1/projects`，配置团队分工 `PUT /api/v1/projects/{id}/team`，并设置招标编号 `GOV-2026-CLOUD-088`。
3. **Step 3: 招标文件上传与解析确认**：
   - 验证上传 `智慧城市云平台招标规范.txt`，触发异步解析；未确认前调用 confirm 严格抛出 `409 REVIEW_PENDING`；逐项确认需求条款与项目事实后成功通过门禁。
4. **Step 4: 响应矩阵与资料库挂接**：
   - 验证将关键标星条款（服务可用性 99.99%、RTO<30s）以及商务资质要求与企业证据、SLA 变量成功绑定。
5. **Step 5: 分节方案确认与正文生成**：
   - 验证分节生成大纲，本地 AI 替身模型根据招标文件提示生成高质量正文，正文符合 R01/R02/R35 规范，无占位符与废标瑕疵。
6. **Step 6: 导出双门禁验证与两册 Word 文件生成**：
   - **递交模式门禁阻断**：故意制造未消解 blocker（如资质未承诺原件备查），请求 `POST /api/v1/projects/{id}/exports`（`kind="submission"`），系统严格阻断返回 `400 CHECK_BLOCKER_EXISTS`，杜绝带病递交；
   - **内部评审模式放行**：相同存在缺陷状态下，请求 `kind="internal"`，系统成功放行，但元数据显式标注 `has_blockers=True` 与合规告警；
   - **消减 blocker 后正式递交放行**：补充原件备查承诺并消解 blocker 后，正式递交模式通过门禁；
   - **双册 Word 产出验证**：系统成功生成并下载 `技术标.docx` 与 `商务标.docx`，文件基于真实 docx（PK 压缩包头）构造，包含 64 位 SHA-256 版式内容指纹，防篡改校验 100% 达成。

---

## 6. 自动化测试与质量门禁证据

| 测试套件 | 测试命令 | 执行结果 | 耗时 |
| :--- | :--- | :--- | :--- |
| **P0 合规规则体系专项测试** | `pytest tests/backend/test_compliance_rules.py` | **5 passed** | 0.24s |
| **关演示主链路冒烟测试** | `pytest tests/backend/test_smoke_non_demo_pipeline.py` | **3 passed** | 1.88s |
| **检查阻断与导出闸门测试** | `pytest tests/backend/test_checks_export_blocker_gate.py` | **4 passed** | 3.16s |
| **MySQL 门禁与环境判定测试** | `pytest tests/backend/test_mysql_gate.py` | **11 passed** | 10.33s |
| **OpenAPI 契约零漂移核验** | `python backend/bid-core/export_openapi.py --check` | **100% 一致无 diff** | 2.1s |
| **前端全量单测套件** | `pnpm --dir frontend/web test` | **395 passed / 0 failed** | 4.87s |
| **前端 TypeScript 类型检查** | `pnpm --dir frontend/web lint` | **0 errors** | 6.5s |

---

## 7. 结论与下一步

- **D3 持久化**：章节正文、历史版本与检查记录落入 MySQL 事务，持久化双路径收口闭环；
- **D4 规则与冒烟**：7 项核心规则全部落地并接通检查中心与导出门禁；关演示主业务链路端到端跑通并留存双册 Word 生成与指纹证据；
- **RAGFlow 连通性**：真服务网络诊断证据详实归档，宿主机 VPN/代理阻断外部内网路由事实明确，生产门控严格有效，未伪造连通；
- **状态建议**：关联卡片 `REV-SMOKE-001`、`BE-COMPLIANCE-RULES-P0`、`AI-RAGFLOW-KB-SYNC` 保持 `in-review`，建议人类 PM 审查此交付报告与留存测试证据后统一批复。
