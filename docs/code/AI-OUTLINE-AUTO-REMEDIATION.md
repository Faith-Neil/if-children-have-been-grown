# AI-OUTLINE-AUTO-REMEDIATION 代码说明：章节合规质检缺陷自动整改建议与局部智能重写引擎

## 1. 架构定位与业务拓扑

本模块作为 PRD MVP v1.8 §5.7.8《批量生成编排》与 §5.10《生成产物合规质检与整改》的核心整改引擎，位于 `backend/bid-core/icg/domain/chapter_generation.py`。
在章节生成产物即时质检门禁（`validate_chapter_candidate`，见 [AI-CHAPTER-AUTO-VALIDATION-GATE](../delivery/AI-CHAPTER-AUTO-VALIDATION-GATE.md)）检出缺陷后，本引擎负责：
1. **自动诊断违规段落**：扫描段落中存在的 R34（占位符/未替换变量/AI客套语）、R37（负偏离）、R24（签字盖章槽位缺失）、CITATION_AUTH（虚构证据引用）；
2. **合成结构化整改指引**：针对每一项缺陷合成针对性 prompt 指令和确定性替换预览；
3. **局部智能重写与原地保全**：仅对检出缺陷的段落调用模型或确定性清洗器，合格段落 100% 原样保全；
4. **多轮自适应收敛迭代**：在 `max_rounds` 限制内自适应收敛，直至阻断缺陷清零且质量健康评分达到 `excellent`（>=90 分）；
5. **流水线无缝集成**：支持单章生成与大纲批量生成流水线中传入 `auto_remediate=True`，在发现缺陷时全自动静默整改闭环。

```mermaid
flowchart TD
    A[开始章节整改: remediate_chapter_candidate] --> B{租户/RBAC/涉密本地模型门禁}
    B -- 阻断 --> C[抛出 404/403 DomainError]
    B -- 放行 --> D[前置合规质检: validate_chapter_candidate]
    D --> E{是否存在阻断项/分值<90?}
    E -- 否(完美合规) --> F[直接返回原候选，无需整改]
    E -- 是 --> G[初始化整改迭代: round = 1]
    
    G --> H[按 [P1]~[Pn] 切分结构化段落]
    H --> I[逐段诊断缺陷: diagnose_paragraph_defects]
    I --> J[合成整改指引方案: synthesize_remediation_plan]
    
    J --> K{段落是否有缺陷?}
    K -- 无缺陷段落 --> L[100% 原样保全原始内容]
    K -- 存在缺陷段落 --> M[根据缺陷类型智能定向重写与清洗]
    M --> M1[事实变量 {{fact:key}} / {{sla:key}} 精确代换]
    M --> M2[负偏离词汇正向承诺翻转映射]
    M --> M3[法定证明章节注入标准印章签名块]
    M --> M4[剔除虚构证据引用，保留白名单依据]
    
    L --> N[组装新章节文本并更新段落序号]
    M1 --> N
    M2 --> N
    M3 --> N
    M4 --> N
    
    N --> O[执行后置即时质检]
    O --> P{阻断清零且得分>=90 或 round>=max_rounds?}
    P -- 否 --> Q[round += 1, 记录历史]
    Q --> H
    P -- 是 --> R[沉淀 remediation_applied 与 remediation_history]
    R --> S[原子更新工作流候选 candidate]
    S --> T[返回整改成果报告]
```

---

## 2. 核心算法实现细节

### 2.1 段落缺陷精准诊断（`diagnose_paragraph_defects`）

逐段扫描文本，检出 4 类核心缺陷：
- **R34 占位符与未代换变量**：识别 `【待定】`、`【待补】`、`TODO`、`FIXME`、`XXXX`，以及未填写的变量宏 `\{\{fact:[^\}]+\}\}`、`\{\{sla:[^\}]+\}\}`；
- **R34 AI 对话客套语**：识别“希望能帮到您”、“作为AI语言模型”等对话残留；
- **R37 负偏离声明**：排查“无法满足”、“负偏离”、“存在差距”、“无法提供”等偏离表述；
- **R24 印章签名槽位缺失**：若为法定承诺/授权类章节（`volume == "business"` 或标题含承诺/投标函），检查是否缺少“法定代表人”签字与“盖单位公章”槽位；
- **CITATION_AUTH 虚构证据引用**：提取文本中所有 `[证:eid]` 标记，对比允许的证据白名单 `allowed_evidence_ids`。

```python
def diagnose_paragraph_defects(
    paragraph_text: str,
    chapter_title: str,
    volume: str,
    allowed_evidence_ids: set[str],
) -> dict[str, Any]:
    # 详见 backend/bid-core/icg/domain/chapter_generation.py
```

### 2.2 确定性文本清洗与反转（`sanitize_and_remediate_paragraph_text`）

针对诊断出的缺陷执行精确修正：
1. **宏变量代换**：提取上下文中的 `facts` 列表，将 `{{fact:项目经理}}` 替换为实际值；
2. **正向翻转映射**：依据 `POSITIVE_RESPONSE_REPLACEMENTS` 常量字典，将否定/负偏离词汇翻转为正面确定性响应（如“目前无法提供” -> “完全响应并提供”）；
3. **清洗客套语与占位符**：剔除对话废话，清除 `【待定】` / `TODO` 残留；
4. **剔除虚构引用**：针对不在 `allowed_evidence_ids` 白名单中的 `[证:fake-xxx]` 标记直接清除，杜绝大模型编造引用；
5. **法定印章签名块注入**：若法定声明章节末尾缺少印章槽位，自动追加 `STANDARD_STATUTORY_SEAL_BLOCK`。

### 2.3 结构化整改指引合成（`synthesize_remediation_plan`）

为每一个存在缺陷的段落生成独立的整改指令（`instruction`），便于大模型定向重写或前端展示整改预览：
- 输入段落编号、原始内容、诊断缺陷项及替换预览；
- 组装具有极强指导性的 prompt 指令：
  - *“请对本段进行局部智能重写，严格满足以下合规要求：将未决占位符替换为明确承诺；将负偏离表述翻转为正向履约承诺；清除对话废话；仅引用合法证据。”*

### 2.4 局部智能重写与原地保全（`remediate_chapter_candidate`）

```python
def remediate_chapter_candidate(
    self,
    project_id: str,
    chapter_id: str,
    principal: Principal,
    content: str | None = None,
    candidate: dict[str, Any] | None = None,
    max_rounds: int = 3,
    auto_save: bool = True,
) -> dict[str, Any]:
```

执行流程：
1. **多租户与 RBAC 校验**：验证租户身份与只读角色拦截；
2. **涉密项目本地模型门禁**：通过 `_check_model_gate` 拦截涉密项目云端模型；
3. **前置质检与退出条件**：若前置质检无阻断项且分值 >= 90，直接跳过重写；
4. **多轮自适应收敛**：
   - 使用 `parse_structured_paragraphs` 将正文拆解为段落；
   - 逐段运行 `diagnose_paragraph_defects`；
   - 无缺陷段落原样保留；
   - 缺陷段落调用模型 `provider.suggest`（或执行确定性清洗器）；
   - 重新缝合并重新编号（`[P1]`~`[Pn]`）；
   - 执行复检 `validate_chapter_candidate`；
   - 记录本轮迭代得分与改动历史；
5. **持久化与输出**：更新 `workflow["candidates"][chapter_id]`，落盘 `remediation_applied: True` 及详细历史。

---

## 3. 核心常量定义

```python
POSITIVE_RESPONSE_REPLACEMENTS = [
    (re.compile(r"无法提供(?P<item>[\u4e00-\u9fa50-9a-zA-Z]+)支持"), r"全面提供\g<item>保障与支持"),
    (re.compile(r"目前无法提供(?P<item>[\u4e00-\u9fa50-9a-zA-Z]+)"), r"承诺完全提供\g<item>"),
    (re.compile(r"无法满足(?P<item>[\u4e00-\u9fa50-9a-zA-Z]+)要求"), r"全面满足并优于\g<item>要求"),
    (re.compile(r"存在差距"), r"完全对标并达到行业领先标准"),
    (re.compile(r"负偏离"), r"完全响应并无偏离"),
    (re.compile(r"不满足"), r"完全满足"),
]

STANDARD_STATUTORY_SEAL_BLOCK = (
    "\n\n投标人（盖单位公章）：_________________________\n"
    "法定代表人或授权委托人（签字或盖章）：_________\n"
    "日期：______年___月___日"
)
```

---

## 4. 自动化测试用例映射

专属测试套件位于 `tests/backend/test_ai_outline_auto_remediation.py`，共 12 项专属测试：

| 测试函数名 | 验证维度 | 对应 PRD / 架构要求 |
|---|---|---|
| `test_diagnose_paragraph_defects_and_synthesize_remediation_plan_r34` | R34 占位符、未填变量宏与 AI 客套语诊断及整改计划合成 | PRD v1.8 §5.10 R34 质检整改 |
| `test_diagnose_and_synthesize_remediation_plan_r37` | R37 负偏离声明识别与正向承诺反转映射验证 | PRD v1.8 §5.10 R37 质检整改 |
| `test_diagnose_and_synthesize_remediation_plan_r24` | R24 法定承诺章节缺少盖章签名槽位诊断与整改指引合成 | PRD v1.8 §5.10 R24 质检整改 |
| `test_diagnose_and_synthesize_remediation_plan_citation_auth` | CITATION_AUTH 虚构证据识别与白名单过滤 | PRD v1.8 §5.10 CITATION_AUTH |
| `test_targeted_in_place_remediation_preserves_untouched_paragraphs` | 局部智能重写：合规段落 100% 原样保全，仅改动违规段落 | PRD v1.8 §5.10.1 局部最小改动原则 |
| `test_multi_round_remediation_convergence` | 多轮自适应收敛迭代：阻断清零且健康分达到 90+ (excellent) | PRD v1.8 §5.10 多轮收敛机制 |
| `test_statutory_form_whole_chapter_seal_block_injection` | 法定表单章节末尾标准印章签名块整体自动注入 | PRD v1.8 §5.10 R24 承诺函盖章 |
| `test_auto_remediate_flag_in_start_chapter_generation` | 单章生成接入 auto_remediate 闭环自动整改 | PRD v1.8 §5.7.8 单章生成闭环 |
| `test_auto_remediate_in_schedule_batch_pipeline` | 大纲批量生成流水线接入 auto_remediate 并汇聚看板 | PRD v1.8 §5.7.8 批量流水线闭环 |
| `test_sensitive_project_airgap_model_gate_on_remediation` | 涉密项目本地模型硬门禁（拦截外部云模型，403） | 架构规范：内网物理隔离红线 |
| `test_multi_tenant_and_rbac_isolation_on_remediation` | 多租户隔离（404 NOT_FOUND）与 RBAC 只读角色拦截（403） | 架构规范：多租户与权限体系 |
| `test_http_api_remediate_candidate_endpoint` | HTTP RESTful API POST /remediate-candidate 端到端契约调用 | API 规范与 OpenAPI 零漂移 |
