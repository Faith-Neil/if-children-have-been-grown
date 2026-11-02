# ISSUE-046 · APP-M2 规则单卡交付索引

为什么有这个文件：看板中 APP-M2-T203～T242 等规则单卡尚未逐张建立 `docs/delivery/APP-M2-T2xx.md`，避免链接悬空且统一说明编号对齐状态。

| 看板卡 | 规则 | ISSUE-046：编号对齐状态 |
|---|---|---|
| APP-M2-T203 | R01 | **编号已对齐**（2026-11-02，`compliance_prd_checks`）；卡状态 in-progress，待 QA/PD 签署 |
| APP-M2-T204 | R02 | 同上 |
| APP-M2-T206 | R04 | 同上 |
| APP-M2-T207 | R05 | 同上（R05 引擎为 MVP stub，见 BE-ISSUE-046 缺口） |
| APP-M2-T208 | R06 | 编号已对齐 |
| APP-M2-T210 | R08 | 编号已对齐 |
| APP-M2-T214 | R10 | 编号已对齐 |
| APP-M2-T215 | R10 | 编号已对齐 |
| APP-M2-T217 | R12 | 编号已对齐 |
| APP-M2-T218 | R13 | 编号已对齐 |
| APP-M2-T220 | R15 | 编号已对齐 |
| APP-M2-T221 | R16 | 编号已对齐 |
| APP-M2-T222 | R17 | 编号已对齐 |
| APP-M2-T223 | R18 | 编号已对齐（依赖 `similarity_hits`，见缺口） |
| APP-M2-T225 | R20 | 编号已对齐（PRD 二期 stub） |
| APP-M2-T232 | R26 | 编号已对齐 |
| APP-M2-T233 | R27 | 编号已对齐 |
| APP-M2-T234 | R28 | 编号已对齐（引擎占位，章节循环承载完整 R28） |
| APP-M2-T240 | R32 | 编号已对齐 |
| APP-M2-T242 | R34 | 编号已对齐 |

权威映射：[2026-11-02-issue-046-realignment-matrix.md](../decisions/2026-11-02-issue-046-realignment-matrix.md)。实现交付：[BE-ISSUE-046-RULE-REALIGN.md](BE-ISSUE-046-RULE-REALIGN.md)。
