# 为什么有这个文件：说明智能对话助手直查未命中与常规回答回退机制（APP-M2-T182）的技术实现、架构设计与门禁规则。
# 它解决什么问题：
# 1. 结构化直查未命中优雅降级：当命中直查意图但在项目事实/招标文件/公司资料中查无对应条目时，严禁编造虚假卡片，优雅回退为常规问答；
# 2. 回退路由与提示规范：区分本项目数据未命中与本公司资料未命中，联动知识库开关裁决 kb_retrieval 与 no_retrieval 路由并注入规范提示；
# 3. 知识库关闭常驻说明一致性：在常规回复或回退问答中，如遇知识库关闭，一律携带常驻说明“知识库已关闭，未查询公司资料库”；
# 4. 实体级精确过滤：对人名、证书名、资质名、业绩关键词、SLA故障等级及项目事实键进行针对性实体过滤，未命中即产生空记录以触发降级。

# APP-M2-T182 智能对话助手直查未命中与常规回答回退代码解释

- 任务编号：[APP-M2-T182](../tasks/APP-M2.md#app-m2-t182)
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 规范出处：[PRD v1.8 §5.11.15](../../docs/reference/product/prd-mvp-v1.8.md#51115-结构化直查与答案卡v15v17-按-q27-定案扩展到本项目数据)、[数据字典 v1.9 §3.9.2 与 §4.16](../../docs/reference/product/kb-data-dictionary-v1.9.md)
- 交付报告：[APP-M2-T182 交付](../delivery/APP-M2-T182.md)
- 核心代码路径：
  - `backend/bid-core/icg_demo/answer_card.py`
  - `backend/bid-core/icg_demo/workflow.py`
  - `tests/backend/test_direct_query_fallback.py`
  - `tests/backend/test_answer_cards.py`

---

## 1. 架构总览与回退数据流

当用户在智能对话助手输入提问时，系统通过 `AnswerCardService.process_query` 调度意图识别、直查装配及未命中降级判断。整体流转逻辑如下：

```
                    [用户在对话助手提问 query]
                               │
                               ▼
                 [意图识别 classify_query_intent]
               (基于 direct_query_intents v1 词表)
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
     [命中直查意图 direct_query]            [未命中直查意图]
            │                                     │
            ▼                                     ▼
     [装配答案卡 assemble_answer_card]     [按开关裁决常规路由]
     (实体过滤：人名/证书/事实键/SLA等级)   • KB开启: kb_retrieval
            │                              • KB关闭: no_retrieval
            ▼                                        + 常驻关闭提示
   [判断记录数 len(records) > 0 ?]
            │
      ┌─────┴─────────────────────────────────┐
      ▼ (len > 0)                             ▼ (len == 0 直查未命中)
 [命中有效记录]                        [触发优雅降级 fallback_to_general=True]
 • 包装答案卡 to_dict()                • 严禁编造卡片: answer_card = None
 • 执行脱敏与 can_insert 门禁          • 按照意图类别与 KB 开关回退路由与提示：
 • 返回 AnswerCard                    ┌──────────────────────────────────────┐
                                      │ 1. 本项目数据未命中:                   │
                                      │   - KB开: kb_retrieval               │
                                      │     提示: "本项目结构化数据中未查询到   │
                                      │           对应条目，已转入常规助手解答" │
                                      │   - KB关: no_retrieval               │
                                      │     提示: "本项目结构化数据中未查询到   │
                                      │           对应条目，已转入常规助手解答。│
                                      │           知识库已关闭，未查询公司资料库"│
                                      │ 2. 本公司资料未命中:                   │
                                      │   - KB开: kb_retrieval               │
                                      │     提示: "本公司资料库中未查询到对应  │
                                      │           结构化记录，已转入知识库检索解答"│
                                      │   - KB关: no_retrieval, skipped=True │
                                      │     提示: "知识库已关闭，未查询公司资料库"│
                                      └──────────────────────────────────────┘
```

---

## 2. 核心模块与实现细节

### 2.1 未命中判定与降级裁决 (`AnswerCardService.process_query`)

在 `answer_card.py` 中，当初筛判定为 `direct_query` 后，装配阶段如果未查到任何记录（`len(card.records) == 0`），触发降级回退处理：

```python
if route.query_route == "direct_query":
    card = self.assemble_answer_card(principal, project_id, query, route)
    if card is None or len(card.records) == 0:
        # 直查未命中！触发优雅降级与常规回答回退，绝不编造虚假卡片
        fallback_to_general = True
        card_dict = None
        if route.intent_category == "project":
            # 本项目数据未命中
            if knowledge_base_enabled:
                final_query_route = "kb_retrieval"
                final_notice = "本项目结构化数据中未查询到对应条目，已转入常规助手解答"
            else:
                final_query_route = "no_retrieval"
                final_notice = "本项目结构化数据中未查询到对应条目，已转入常规助手解答。知识库已关闭，未查询公司资料库"
        else:
            # 本公司资料未命中
            if knowledge_base_enabled:
                final_query_route = "kb_retrieval"
                final_notice = "本公司资料库中未查询到对应结构化记录，已转入知识库检索解答"
            else:
                final_query_route = "no_retrieval"
                library_query_skipped = True
                final_notice = "知识库已关闭，未查询公司资料库"
    else:
        card_dict = card.to_dict()
        final_notice = card.notice
```

### 2.2 知识库关闭常驻说明一致性保障

根据 PRD v1.8 §5.11.15 第 2 部分与数据字典 3.9.2 约定，在所有常规回答或降级回退为无检索的场景下，只要知识库处于关闭状态，必须携带常驻说明：

```python
else:
    final_query_route = route.query_route
    final_notice = route.notice
    # 常驻说明一致性：在常规回复中如遇知识库关闭，一律携带常驻说明“知识库已关闭，未查询公司资料库”
    if not knowledge_base_enabled and final_query_route == "no_retrieval":
        if not final_notice:
            final_notice = "知识库已关闭，未查询公司资料库"
        elif "知识库已关闭，未查询公司资料库" not in final_notice:
            final_notice = f"{final_notice}。知识库已关闭，未查询公司资料库"
```

### 2.3 实体级精确过滤装配逻辑

为避免向用户输出无关或虚构的直查卡片，对两大类数据源实施实体级精确提取与过滤：

1. **项目事实装配 (`_assemble_project_card`)**：
   - 提取查询词中的核心事实键：`("服务期限", "服务期", "最高限价", "限价", "建设单位", "交付地点", "采购人", "项目金额")`；
   - 若用户指定了具体事实键（如“交付地点”），仅保留 key/label 匹配的事实项。若项目中未包含该事实项，`matched_facts` 结算为空列表，触发降级；
   - 若用户为宽泛提问（如“项目事实有哪些”），则默认保留全部项目事实并按相关度排序展示。

2. **招标文件要求装配 (`_assemble_project_card`)**：
   - 提取条款目标关键词：`("保证金", "投标保证金", "星号", "★", "开标时间", "开标", "服务期", "废标", "付款方式")`；
   - 过滤已替代条款后，按关键词匹配条款正文。如提问“开标时间”但招标文件未录入开标时间要求，`filtered_reqs` 结算为空列表，触发降级。

3. **公司资料库装配 (`_assemble_company_card`)**：
   - **人员与证书**：提取目标人名（常见人名与正则动态抽取）与目标证书类别（`oracle`, `ocp`, `pmp`, `cisp`, `软考`, `建造师` 等）。当查询指定了具体人名（如“赵六”）或证书（如“CISP”）但库中不存在对应记录时，`records` 为空列表；
   - **企业资质**：提取目标资质名称（`iso`, `cmmi`, `高新`, `涉密` 等），无对应资质时产生空列表；
   - **同类业绩**：提取业绩关键词（`三甲`, `医院`, `银行`, `高校` 等），无对应合同业绩时产生空列表；
   - **SLA 服务承诺**：提取目标故障等级（`一级`, `二级`, `特级` 等），无对应等级或无 SLA 模板时产生空列表。

---

## 3. 契约表格驱动矩阵

| 意图类别 | 直查状态 | 知识库开关 | 最终 `query_route` | `fallback_to_general` | `library_query_skipped` | `answer_card` | 最终提示 `notice` |
|---|---|---|---|---|---|---|---|
| 本项目数据 (`project`) | 命中条目 | 开启 (True) | `direct_query` | False | False | AnswerCard 字典 | None |
| 本项目数据 (`project`) | 命中条目 | 关闭 (False) | `direct_query` | False | False | AnswerCard 字典 | "知识库已关闭，本卡来自本项目结构化数据" |
| 本项目数据 (`project`) | 未命中 (0条) | 开启 (True) | `kb_retrieval` | True | False | None (严禁编造) | "本项目结构化数据中未查询到对应条目，已转入常规助手解答" |
| 本项目数据 (`project`) | 未命中 (0条) | 关闭 (False) | `no_retrieval` | True | False | None (严禁编造) | "本项目结构化数据中未查询到对应条目，已转入常规助手解答。知识库已关闭，未查询公司资料库" |
| 本公司资料 (`company`) | 命中条目 | 开启 (True) | `direct_query` | False | False | AnswerCard 字典 | None |
| 本公司资料 (`company`) | 命中条目 | 关闭 (False) | `no_retrieval` | False | True | None | "知识库已关闭，未查询公司资料库" |
| 本公司资料 (`company`) | 未命中 (0条) | 开启 (True) | `kb_retrieval` | True | False | None (严禁编造) | "本公司资料库中未查询到对应结构化记录，已转入知识库检索解答" |
| 本公司资料 (`company`) | 未命中 (0条) | 关闭 (False) | `no_retrieval` | False | True | None | "知识库已关闭，未查询公司资料库" |
| 常规提问 (None) | N/A | 开启 (True) | `kb_retrieval` | False | False | None | None |
| 常规提问 (None) | N/A | 关闭 (False) | `no_retrieval` | False | False | None | "知识库已关闭，未查询公司资料库" |

---

## 4. 安全门禁与错误码规范

1. **绝对不编造假卡**：
   在所有回退路径中，响应体字典的 `answer_card` 字段绝对置为 `None`，不返回带伪造字段的空结构卡片；
2. **冻结 143 错误码集守卫**：
   跨租户访问项目（例如乙公司编写人尝试访问甲公司项目）抛出标准的 `DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")`，绝不绕过租户检查；
3. **敏感信息与受限资料权限**：
   受限资料（`is_restricted=True`）在装配阶段由 `WorkflowService._restricted_allowed` 进行鉴权，无权人员不展示且不泄露记录存在；
4. **离线 CI 纯洁性**：
   本机制纯依赖内存数据结构与离线测试桩，无外部网络依赖，测试执行稳定高效。
