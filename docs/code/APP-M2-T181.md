# 为什么有这个文件：说明智能对话助手答案卡（结构化直查与意图分流，APP-M2-T181）的技术实现、架构设计与门禁规则。
# 它解决什么问题：
# 1. 意图分流与路由：根据用户提问精准识别直查意图，区分本项目数据类与本公司资料类，裁决 direct_query、kb_retrieval 或 no_retrieval；
# 2. 知识库开关联动：知识库关闭时本项目数据依然可直查且标注来源，公司资料直查跳过并标记 library_query_skipped=True，普通问答退化为无检索；
# 3. 敏感信息自动掩码：18 位身份证号码自动掩码脱敏为 110101********1234；
# 4. 答案卡防篡改与插入门禁：本项目结构化数据卡一律 can_insert=False，仅已确认且未过期的本公司资料卡可标记 can_insert=True。

# APP-M2-T181 智能对话助手答案卡代码解释

- 任务编号：[APP-M2-T181](../tasks/APP-M2.md#app-m2-t181)
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 规范出处：[PRD v1.8 §5.11.15](../../docs/reference/product/prd-mvp-v1.8.md#51115-结构化直查与答案卡v15v17-按-q27-定案扩展到本项目数据)、[数据字典 v1.9 §3.9.2 与 §4.16](../../docs/reference/product/kb-data-dictionary-v1.9.md)
- 交付报告：[APP-M2-T181 交付](../delivery/APP-M2-T181.md)
- 核心代码路径：
  - `backend/bid-core/icg_demo/answer_card.py`
  - `backend/bid-core/icg_demo/workflow.py`
  - `tests/backend/test_answer_cards.py`

---

## 1. 架构总览与工作流

当用户在智能对话助手输入提问时，系统通过 `AnswerCardService.process_query` 调度意图分类、取数路由裁决、结构化直查数据装配、脱敏与插入门禁校验，数据流如下：

```
                    [用户在对话助手提问 query]
                               │
                               ▼
                 [意图识别 classify_query_intent]
               (基于 direct_query_intents v1 词表)
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
     [本项目数据类意图]    [本公司资料类意图]     [未命中直查意图]
    - tender_requirement - person / person_cert  - 常规自由问答
    - project_fact       - qualification        - 润色/方案撰写咨询
    - response_matrix    - contract
    - check_result       - sla
            │                  │                  │
            └──────────┬───────┴──────────────────┘
                       ▼
        [路由与开关联动裁决 resolve_assistant_query_route]
      ┌─────────────────────────────────────────────────────────┐
      │ 知识库开关 kb_enabled 状态联动判断：                      │
      │ • 项目类 + 开启 ──► direct_query, skipped=False         │
      │ • 项目类 + 关闭 ──► direct_query, skipped=False,        │
      │                    注: "知识库已关闭，本卡来自本项目结构化数据" │
      │ • 公司类 + 开启 ──► direct_query, skipped=False         │
      │ • 公司类 + 关闭 ──► no_retrieval, skipped=True,          │
      │                    提示: "知识库已关闭，未查询公司资料库"   │
      │ • 常规类 + 开启 ──► kb_retrieval, skipped=False         │
      │ • 常规类 + 关闭 ──► no_retrieval, skipped=False         │
      └──────────────────────────┬──────────────────────────────┘
                                 │
                   (若 query_route == direct_query)
                                 ▼
             [装配结构化答案卡 assemble_answer_card]
      ┌─────────────────────────────────────────────────────────┐
      │ 1. 租户隔离：严格检查 principal.user.company_id          │
      │ 2. 权限隔离：受限资料 (is_restricted) 无权者过滤不泄露   │
      │ 3. 冲突展示：项目事实存在抽取冲突时并列展示备选项及页码   │
      │ 4. 插入门禁 (can_insert):                               │
      │    - 本项目数据卡 ──► 一律 can_insert=False              │
      │    - 公司资料卡:                                        │
      │      • confirmed 且有效 ──► can_insert=True             │
      │      • pending (待确认)  ──► can_insert=False ("未确认")│
      │      • expired (已过期)  ──► can_insert=False ("已过期")│
      │ 5. 敏感掩码 (mask_sensitive_payload):                   │
      │    - 18位身份证号全量掩码: 110101********1234           │
      └──────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
                    [返回结构化结果 AssistantReply]
```

---

## 2. 核心模块与实现细节

### 2.1 意图识别 (`classify_query_intent`)
严格按照 PRD v1.8 §5.11.15 与字典 4.17 节平台设置 `direct_query_intents`（版本号 `DIRECT_QUERY_INTENT_VERSION = 1`）维护两组直查领域：
1. **本项目数据类 (`category = "project"`)**：
   - `tender_requirement` (招标要求)：涵盖“投标保证金”、“开标时间”、“星号条款”、“废标条款”等；
   - `project_fact` (项目事实)：涵盖“服务期限”、“最高限价”、“建设单位”、“采购人”、“交付地点”等；
   - `response_matrix` (响应矩阵)：涵盖“响应矩阵”、“未分配章节”、“偏离表”等；
   - `check_result` (检查结果)：涵盖“检查结果”、“阻断项”、“合规问题”等。
2. **本公司资料类 (`category = "company"`)**：
   - `person_cert` / `person` (人员证书/人员)：涵盖“人员”、“证书”、“工程师”、“张三”、“李四”、“OCP”、“PMP”、“软考”等；
   - `qualification` (企业资质)：涵盖“资质”、“ISO”、“CMMI”、“认证”等；
   - `contract` (企业业绩)：涵盖“业绩”、“合同”、“历史项目”、“案例”等；
   - `sla` (SLA服务承诺)：涵盖“SLA”、“响应时限”、“恢复时限”、“到场时限”等。

### 2.2 知识库开关联动路由 (`resolve_assistant_query_route`)
按照 PRD §5.11.15 第 1、2 部分定案，建立四种组合与常规问答表格：

| 提问意图类别 | 知识库开关 (`kb_enabled`) | `query_route` | `library_query_skipped` | 答案卡生成 | 提示/标注信息 |
|---|---|---|---|---|---|
| 本项目数据 (`project`) | True (开启) | `direct_query` | False | 是 (`can_insert=False`) | 数据来源为本项目数据 |
| 本项目数据 (`project`) | False (关闭) | `direct_query` | False | 是 (`can_insert=False`) | 注明“知识库已关闭，本卡来自本项目结构化数据” |
| 本公司资料 (`company`) | True (开启) | `direct_query` | False | 是 (合法记录可插入) | 数据来源为本公司资料库 |
| 本公司资料 (`company`) | False (关闭) | `no_retrieval` | True | 否 (跳过查询) | 提示“知识库已关闭，未查询公司资料库” |
| 常规提问 (无直查意图) | True (开启) | `kb_retrieval` | False | 否 (转入RAGFlow检索) | 走检索增强回答 |
| 常规提问 (无直查意图) | False (关闭) | `no_retrieval` | False | 否 (转入大模型凭自身能力) | 无知识库检索来源 |

### 2.3 敏感信息自动掩码 (`mask_id_card` / `mask_sensitive_payload`)
- 规则：针对 18 位中国居民身份证号码，使用前向与后向非字母数字断言进行严谨匹配：
  ```python
  ID_CARD_REGEX = re.compile(r"(?<![0-9A-Za-z])([1-9]\d{5})(?:\d{8})(\d{3}[0-9Xx])(?![0-9A-Za-z])")
  ```
- 效果：脱敏中间 8 位出生年月日数字为星号，保留前 6 位地址码和后 4 位识别码（如 `110101********1234`）。
- 递归装配：`mask_sensitive_payload` 对卡片字典、列表及文本嵌套字段做深度遍历脱敏，确保明文身份证号码零泄漏。

### 2.4 答案卡装配与防篡改/插入门禁 (`assemble_answer_card`)
1. **本项目结构化数据卡**：
   - 招标要求、项目事实、响应矩阵、检查结果直查卡统一标记 `can_insert=False`，`insert_disabled_reason="本项目数据不插入正文"`。
   - 针对项目事实的抽取冲突（`workflow["conflicts"]`），检测到冲突时将确认状态标为 `"有冲突，待项目负责人选定"`，并在记录中并列给出各来源方取值与原文页码。
2. **本公司资料卡**：
   - 租户隔离：只读取当前账号所属公司（`principal.user.company_id`）的资料；
   - 权限隔离：对于 `is_restricted=True` 的受限资料，未获授权的普通用户无法查看，且不泄露其存在；
   - 插入门禁（逐条记录与整卡双重校验）：
     - `confirm_status != "confirmed"` ──► `can_insert=False`, `insert_disabled_reason="未确认"`
     - 有效期早于项目截止日期（`evidence_expired`） ──► `can_insert=False`, `insert_disabled_reason="已过期"`
     - `confirm_status == "confirmed"` 且未过期 ──► `can_insert=True`, `insert_disabled_reason=""`
   - 卡片整体 `can_insert` 只有在至少存在一条合法可引用的有效记录时才置为 `True`。

### 2.5 服务集成 (`WorkflowService`)
在 `WorkflowService` 初始化时挂载 `AnswerCardService`：
```python
self.answer_card = AnswerCardService(demo)

def assistant_query(self, principal: Principal, project_id: str, query: str,
                    knowledge_base_enabled: bool = True) -> dict:
    return self.answer_card.process_query(principal, project_id, query, knowledge_base_enabled)
```

---

## 3. 测试覆盖说明

专属测试集 `tests/backend/test_answer_cards.py` 提供 13 项完整的自动化测试用例：
1. `test_intent_category_and_kb_switch_matrix`：涵盖意图类别 × 知识库开关的 4 种直查组合及 2 种常规提问对照组的表格驱动测试；
2. `test_kb_disabled_project_data_available_and_library_skipped`：验证关闭知识库时项目事实正常直出而公司资料标注 `library_query_skipped=True`；
3. `test_id_card_masking_function` & `test_id_card_masking_in_answer_card`：验证 18 位身份证号码脱敏算法及卡片装配中的全字段掩码；
4. `test_can_insert_gates_for_project_and_company_records`：验证本项目数据禁止插入正文，以及公司资料中未确认、已过期、有效已确认三类状态的插入门禁；
5. `test_project_fact_conflict_display`：验证项目事实存在冲突时并列展示取值与页码；
6. `test_restricted_evidence_and_cross_company_isolation`：验证受限资料权限阻断与跨租户数据隔离；
7. `test_workflow_service_assistant_query_delegation`：验证 `WorkflowService` 业务层委托调用。
