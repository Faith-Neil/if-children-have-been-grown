为什么有这个文件：说明第一批核心合规规则编号体系（R15、R23、R34、R37）的领域模型、核验引擎算法、导出检查集成与 RESTful API 的技术实现与代码设计。

它解决什么问题：落实 PRD v1.8 MVP §5.8 / §5.8.1 / §5.8.5（核心合规规则编号落地）与第二阶段后端 P0 核心缺口，建立结构化合规规则核验引擎。实现：
1. R15 证明材料齐全性核验（排查资质、证书、财务、业绩等证明类要求，拦截证据缺失、过期及未确认）；
2. R23 废标红线与关键标星条款响应率核验（100% 覆盖与非空确认，未响应、被忽略或未映射有效章节赋 blocker）；
3. R34 占位符与“待补/待完善”残留字样核验（正文与条款响应中敏感占位符与草稿瑕疵排查，拦截 blocking/blocker）；
4. R37 技术/商务偏离表一致性核验（关键条款负偏离强阻断 blocker，正偏离与无偏离一致性校验）；
5. 统一数据结构 `{rule_id, title, severity, passed, finding_summary, suggestion, issues, details}`；
6. 深度集成至 `export_service.run_check` 与 `WorkflowService`，并暴露 `/api/v1` 查询与评估端点，保证租户强隔离与 `RULES_INCOMPLETE` 底线门禁。

# BE-COMPLIANCE-RULES-P0：第一批核心合规规则编号落地代码说明

## 1. 业务上下文与设计目标

在招投标编制与递交过程中，合规性是关乎投标能否中标甚至被废标的核心生命线。PRD MVP §5.8 明确规划了 44 项系统合规规则，并要求在第二阶段优先落地第一批核心 P0 级结构化合规规则体系：

1. **R15（证明材料齐全性核验）**：
   - 自动识别资质、证书、证明、业绩、授权、合同、认证、发票、财务报表、纳税凭证、社保记录等证明类条款；
   - 核验是否已挂接公司资料库中已确认（`status == "confirmed"`）的企业证据材料；
   - 严格核验保质期（`valid_until` / `valid_to`），必须覆盖当前项目投标截止日（`project.deadline`），过期拦截；
   - 历史标书资料（`type == "history"`）仅可供参考，禁止作为有效投标证明材料挂接。
2. **R23（废标红线与关键标星条款响应率核验）**：
   - 识别废标红线（`disqualification`）与关键标星（`star` / `★` / `*`）条款；
   - 必须 100% 确认响应并填写实质响应正文（不能残留“待补/待完善”），未响应判定为 blocker；
   - 严禁将关键条款标记为忽略或不适用（`status == "rejected"`），标记忽略直接判定为 blocker；
   - 关键条款必须映射到本项目同分册的有效章节正文中进行响应，未映射判定为 blocker。
3. **R34（占位符与“待补/待完善”残留字样核验）**：
   - 全面扫描各章节正文（`paragraphs`）与各条款实质响应内容（`response`）；
   - 精确识别敏感占位符（如 `【待补】`、`[待补]`、`待补充`、`【待完善】`、`[待确认]`、`TODO`、`FIXME`、`{{变量}}` 占位符、AI 对话残留提示语）；
   - 章节正文或条款响应中检测到残留字样直接赋予 `blocking`（或关键条款 `blocker`），禁止带草稿瑕疵导出。
4. **R37（技术/商务偏离表一致性核验）**：
   - 结构化核对技术与商务条款偏离标记（`deviation_type`：`none` / `positive` / `negative`）；
   - 关键废标红线或标星条款出现负偏离（`negative`）时，直接赋予 blocker 阻断；
   - 偏离说明（`deviation_reason`）完整性与条款响应矩阵一致性校验。
5. **底线门禁与规范约束**：
   - 严禁绕过 `RULES_INCOMPLETE` 假装规则已全量实现；
   - 严格保障多租户与公司强隔离语义，跨租户访问返回 404；
   - 接口严格收敛至 `/api/v1`，严禁平铺巨石。

---

## 2. 架构设计与分包实现

严格遵守《质量整改与结构冻结规则》与工程分层规范，新逻辑全部划分至 `backend/bid-core/icg/` 上下文子包：

```
backend/bid-core/icg/
├── domain/
│   ├── compliance_rules.py        # 核心引擎：R15/R23/R34/R37 算法实现与结构体定义
│   ├── export_service.py          # 导出检查集成：将 P0 规则注入 run_check 门禁
│   └── workflow_orchestrator.py   # 编排层集成：继承 ComplianceRulesMixin，支持偏离表字段
├── api/
│   └── compliance.py              # RESTful API 端点：/api/v1 契约暴露
tests/backend/
└── test_compliance_rules_p0.py   # 专属自动化单测套件（7 项场景全量覆盖）
```

### 2.1 结构化输出模型设计 (`compliance_rules.py`)

严格按契约定义规则检查结果与问题项模型：

```python
@dataclass
class ComplianceRuleIssue:
    id: str
    rule_id: str
    code: str
    severity: Literal["blocker", "blocking", "warning", "info"]
    message: str
    chapter_id: str | None = None
    paragraph_id: str | None = None
    requirement_id: str | None = None
    evidence_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

@dataclass
class ComplianceRuleResult:
    rule_id: str
    title: str
    severity: Literal["blocker", "blocking", "warning", "info"]
    passed: bool
    finding_summary: str
    suggestion: str
    issues: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
```

### 2.2 核心规则检查器实现 (`ComplianceRulesEngine`)

#### 1. R15 证明材料齐全性 (`check_r15`)
- 通过语义与字段双重判定证明类条款（`资质`、`证书`、`证明`、`业绩`、`授权`、`财务`、`纳税` 等）；
- 若 `evidence_ids` 为空，产出 `EVIDENCE_MISSING`；
- 遍历已挂接证据，核验是否存在且属于同公司；
- 核验证据状态必须为 `confirmed`（未确认产出 `EVIDENCE_NOT_USABLE`）；
- 排除历史标书参考材料（`type == "history"`）；
- 调用 `evidence_expired(evidence, project.deadline, today)` 进行有效期截止日核验，过期产出 `EVIDENCE_EXPIRED`。

#### 2. R23 关键条款 100% 响应与章节映射 (`check_r23`)
- 通过 `category in ("disqualification", "star")` 或文本包含 `★` / `*` / `废标` 识别关键条款；
- 状态核对：`status == "pending"` 产出 `REQUIREMENT_PENDING`；`status == "rejected"` 产出 `CRITICAL_REQUIREMENT_REJECTED`（blocker）；
- 章节映射核对：`chapter_id` 必须有效映射到当前项目同分册章节，否则产出 `MATRIX_MAPPING_MISSING`（blocker）；
- 响应内容核验：`response` 不能为空（`MATRIX_RESPONSE_MISSING`，blocker），且响应正文不能含有草稿待补字样（`CRITICAL_RESPONSE_INVALID`，blocker）。

#### 3. R34 占位符与“待补/待完善”残留字样核验 (`check_r34`)
- 使用高性能正则表达式列表匹配敏感占位符：
  ```python
  PLACEHOLDER_REGEXES = [
      re.compile(r"【待补(?:：[^】]*)?】"),
      re.compile(r"\[待补(?:：[^\]]*)?\]"),
      re.compile(r"待补"),
      re.compile(r"【待完善(?:：[^】]*)?】"),
      re.compile(r"\[待完善(?:：[^\]]*)?\]"),
      re.compile(r"待完善"),
      re.compile(r"【待确认(?:：[^】]*)?】"),
      re.compile(r"TODO", re.IGNORECASE),
      re.compile(r"FIXME", re.IGNORECASE),
      re.compile(r"\{\{[^}]+\}\}"),
      re.compile(r"【请填写[^】]*】"),
      re.compile(r"（此处补充[^）]*）"),
  ]
  ```
- 逐章扫描已提交段落文本，发现匹配即产出 `CHAPTER_TEXT_PLACEHOLDER`（blocking / blocker）；
- 逐条扫描条款 `response` 文本，发现匹配产出 `REQUIREMENT_RESPONSE_PLACEHOLDER`。

#### 4. R37 技术/商务偏离表一致性核验 (`check_r37`)
- 提取条款偏离字段：`deviation_type` 与 `deviation_reason`；
- 负偏离阻断：关键废标红线与标星条款若标记为 `negative`，直接判定严重阻断 `CRITICAL_NEGATIVE_DEVIATION`（blocker）；
- 一致性与完整性：标记为 `positive` 或 `negative` 时必须附带非空理由，且响应正文需阐明偏离情况，否则产出 `DEVIATION_REASON_MISSING`。

---

## 3. 编排与系统集成

### 3.1 导出检查引擎无缝集成 (`export_service.py`)

在 `run_check` 中，调用 `ComplianceRulesEngine.evaluate_p0_rules`，并将结构化结果赋给问题项与 check 摘要：
1. 遍历 P0 规则判定的 issue，注入 `rule_id`，并与原有检查问题集统一合并；
2. 保持最高严重度提级逻辑：若存在 blocker 问题，检查整体状态 `passed = False`；
3. 将 P0 规则清单注入 `check["rules"]`，方便前端直接呈现合规规则维度的诊断卡片；
4. 严格保留 `RULES_INCOMPLETE` 底线门禁：
   ```python
   # 架构安全底线：只要存在未完全实现规则，必须如实附带 RULES_INCOMPLETE
   check["coverage"]["complete"] = False
   check["issues"].append({
       "id": new_id("issue"),
       "rule_id": "SYSTEM_GATE",
       "code": "RULES_INCOMPLETE",
       "severity": "info",
       "message": "当前规则引擎已落地 P0 核心规则（R15/R23/R34/R37）；其余次要规则仍在迭代中。",
   })
   ```

### 3.2 RESTful API 契约设计 (`icg/api/compliance.py`)

在 `/api/v1` 下注册统一路由：
- `POST /api/v1/projects/{project_id}/compliance-rules/evaluate`：实时重新触发指定项目分册的合规规则计算（`volume: all | technical | business`）；
- `GET /api/v1/projects/{project_id}/compliance-rules`：获取项目最新合规规则状态；
- `GET /api/v1/compliance-rules/catalog`：获取系统当前已支持规则目录与严重度元数据。

---

## 4. 验证与门禁保护

编写专属自动化测试套件 `tests/backend/test_compliance_rules_p0.py`，共 7 项综合测试：
1. `test_r15_proof_material_completeness`：验证有效挂接通过、未挂接证据拦截（EVIDENCE_MISSING）、有效期过期拦截（EVIDENCE_EXPIRED）及证据条目待审不可用拦截（EVIDENCE_NOT_USABLE）；
2. `test_r23_critical_clauses_100_percent_response`：验证废标红线未响应 blocker、响应待补 blocker、关键标星条款被误标记 rejected blocker、未映射有效章节 blocker；
3. `test_r34_placeholder_and_residual_verification`：验证正文及条款响应中敏感占位符排查与阻断；
4. `test_r37_deviation_table_consistency`：验证关键条款负偏离强阻断（CRITICAL_NEGATIVE_DEVIATION）与理由缺失拦截；
5. `test_compliance_rules_catalog_api`：验证目录 API 返回 4 项 P0 规则与固定属性；
6. `test_compliance_rules_tenant_and_auth_isolation`：验证跨公司账号访问 404 强隔离与未鉴权 401 拦截；
7. `test_run_check_integrates_p0_compliance_rules`：验证导出前置检查 `run_check` 正确整合 P0 规则、严重度提级与保留 RULES_INCOMPLETE 底线。
