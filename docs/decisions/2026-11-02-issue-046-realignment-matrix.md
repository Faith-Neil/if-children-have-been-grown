# ISSUE-046 合规规则 PRD 编号重挂矩阵

| 项目 | 内容 |
|---|---|
| 决策日期 | 2026-11-02 |
| 关联 Issue | [ISSUE-046](../../issues/ISSUE-046.md) |
| 关联任务 | BE-ISSUE-046-RULE-REALIGN |
| PRD 依据 | [PRD MVP v1.8 §5.8.1](../reference/product/prd-mvp-v1.8.md) |
| 代码 | `backend/bid-core/icg/domain/compliance_prd_checks.py`、`compliance_rules.py` |
| 测试 | `tests/backend/test_compliance_rules*.py`（46 passed，2026-11-02 本机） |

| PRD 编号 | PRD 要求（摘要） | 原错误实现 | EXT-* 承接 | PRD 行为来源 | 看板卡 |
|---|---|---|---|---|---|
| R01 | 不可引用的资料禁止引用 | 招标编号一致性 | EXT-CONSISTENCY-TENDER-NAME | `compliance_prd_checks.prd_check_r01`（正文 `[证]` + 资料库状态） | APP-M2-T203 |
| R02 | 资料来源分级与投标主体一致 | 原件备查承诺 | EXT-QUALIFICATION-ORIGINAL | `prd_check_r02` + `LibraryOrchestrator._agreement_present` | APP-M2-T204 |
| R04 | 临期与复审提醒 | 联合体协议 | EXT-CONSORTIUM-AGREEMENT | `prd_check_r04`（30 天临期 info） | APP-M2-T206 |
| R05 | 年审/监督审核有效（二期） | 财务指标 | EXT-FINANCIAL-METRICS | `prd_check_r05`（MVP info stub） | APP-M2-T207 |
| R06 | 持证单位与主体名称一致 | 业绩案例 | EXT-PERFORMANCE-CASE | `prd_check_r06`（录入字段 warning） | APP-M2-T208 |
| R08 | 拟派人员原厂认证 | 交付周期偏离 | EXT-DELIVERY-TIMELINE | `prd_check_r08`（排人数据 warning） | APP-M2-T210 |
| R10 | SLA 承诺全文一致 | 质保/响应条款核验 | EXT-WARRANTY-RESPONSE-LEGACY | `sla.sla_issues` → `prd_check_r10` | APP-M2-T214、T215 |
| R12 | 人员占用/停用离职 | SLA 质保偏离 | EXT-SLA-WARRANTY-DEVIATION | `prd_check_r12` | APP-M2-T217 |
| R13 | 业绩满足资格与评分 | 团队人员配置 | EXT-TEAM-STAFFING | `prd_check_r13` | APP-M2-T218 |
| R15 | 占位符与【待补】清零 | 证明材料齐全 | EXT-PROOF-MATERIAL | `chapter_loop` 占位模式 + `PLACEHOLDER_REGEXES` | APP-M2-T220 |
| R16 | 主体基本资格时效 | 投标保证金 | EXT-BID-SECURITY | `prd_check_r16`（主体状态 warning） | APP-M2-T221 |
| R17 | 使用提示与保密提醒 | 关联交易回避 | EXT-CONFLICT-INTEREST | `prd_check_r17` | APP-M2-T222 |
| R18 | 集团内相似度 | 联合体资质认定 | EXT-CONSORTIUM-QUALIFICATION | `prd_check_r18`（workflow similarity_hits） | APP-M2-T223 |
| R20 | 同一编写人（二期） | 报价雷同 | EXT-QUOTATION-COLLUSION | `prd_check_r20`（phase2 info stub） | APP-M2-T225 |
| R26 | 评分项覆盖度 | 知识产权声明 | EXT-IP-INDEMNITY | `prd_check_r26`（writing_plan 覆盖） | APP-M2-T232 |
| R27 | 项目事实一致 | 本地化网点 | EXT-LOCAL-SERVICE | `prd_check_r27` | APP-M2-T233 |
| R28 | 章节模型评审（辅助） | 关键技术负偏离 | EXT-CRITICAL-TECH-DEVIATION | `prd_check_r28`（引擎占位，主路径 chapter_loop） | APP-M2-T234 |
| R32 | 产品范围一致 | 投标有效期 | EXT-BID-VALIDITY | `prd_check_r32`（清单外品牌 warning） | APP-M2-T240 |
| R34 | AI 痕迹与 Markdown | 占位符/待补（旧合订） | EXT-PLACEHOLDER-LEGACY | `prd_check_r34` + `AI_CONVERSATION_RESIDUALS` | APP-M2-T242 |

R19 已在 APP-M2-T096 中更正为关联投标冲突；绿色采购保留为 `EXT-GREEN`。

`evaluate_p0`～`evaluate_p5` 在 PRD 规则后追加对应 EXT 规则（可选扩展检查，不占用 PRD 编号展示）。
