# 任务交付：PRD P3 核心合规规则引擎扩充与导出门禁联动（BE-COMPLIANCE-RULES-P3）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-COMPLIANCE-RULES-P3 |
| 代码解释 | [PRD P3 核心合规规则引擎扩充代码说明](../code/BE-COMPLIANCE-RULES-P3.md) |
| 验收 | 1. 规则引擎扩充：在 `backend/bid-core/icg/domain/compliance_rules.py` 完整落地 PRD MVP §5.8 第四批核心合规规则（R05/R06/R08/R12/R20）；<br>2. 业务阻断红线：资产负债率超标或净利润亏损（R05，`FINANCIAL_METRICS_NON_COMPLIANT`）、业绩案例金额不足/缺盖章/缺验收证明/超出三年年限（R06，`PERFORMANCE_CASE_INSUFFICIENT`）、承诺交付天数超过招标上限或工期负偏离（R08，`DELIVERY_TIMELINE_NEGATIVE_DEVIATION`）、承诺质保期低于基线或现场到达响应超时（R12，`SLA_WARRANTY_NEGATIVE_DEVIATION`）、正文/响应串标特征或报价比例异常一致雷同（R20，`BID_PRICE_COLLUSION_RISK_DETECTED`）均严格判定为 blocker；<br>3. 导出门禁严格联动：在 `backend/bid-core/icg/domain/export_service.py` 保证上述 blocker 缺陷在正式递交版（submission）导出时严格触发 400 `CHECK_BLOCKER_EXISTS`，严禁带病递交；<br>4. 自动化测试套件：`tests/backend/test_compliance_rules_p3.py` 6 项测试全部通过（6 passed in 9.61s），全量 42 项合规测试全部通过；<br>5. 契约无漂移：OpenAPI 100% 对齐无 diff。 |
| 项目进度 | 本次交付处于 `in-review`，建议由 QA 独立签署证据与 PD 产品验收核准后，由人类 PM 最终标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 §5.8 规则定义及质量整改要求，系统在已完成 P0（R01, R02, R15, R23, R34, R35, R37）、P1（R03, R04, R09, R10）与 P2（R07, R11, R14, R25, R31）共 16 条核心规则后，扩充落地第四批核心合规规则（R05, R06, R08, R12, R20），并与整本导出门禁（400 `CHECK_BLOCKER_EXISTS`）深度联动：
1. **R05 财务指标核验（资产负债率、净利润连续性）**：核验企业审计报告中资产负债率是否低于招标最高限额要求（如不超过 70%）、近三年净利润是否为正；严重资不抵债或亏损判定为 `blocker`（`FINANCIAL_METRICS_NON_COMPLIANT`）；
2. **R06 业绩案例核验（合同金额、类似项目与签字盖章页）**：核验提供的业绩案例合同金额是否达到招标门槛金额、签订时间是否在有效年限内（如近3年）、是否附带双方签字盖章页及验收证明；业绩金额不足或缺少盖章页判定为 `blocker`（`PERFORMANCE_CASE_INSUFFICIENT`）；
3. **R08 交付周期与进度计划偏离核验**：招标明确要求交付天数上限（如 60 日历天），投标响应承诺交付周期若超过招标上限，判定为负偏离重大违规 `blocker`（`DELIVERY_TIMELINE_NEGATIVE_DEVIATION`）；
4. **R12 服务响应 SLA 与质保期偏离核验**：招标要求质保期最低年限（如 3 年）及现场到达响应时间（如 2 小时），响应若低于质保期要求或超出到达响应时间，判定为 `blocker`（`SLA_WARRANTY_NEGATIVE_DEVIATION`）；
5. **R20 报价雷同排查（分项报价比例与异常一致性排查）**：排查分项报价清单是否存在异常数字规律、或明显复制其他投标主体的报价结构，排查违规串通投标风险；识别重大异常判定为 `blocker`（`BID_PRICE_COLLUSION_RISK_DETECTED`）。

---

## 2. 核心架构与分包清单

所有新增实现严格遵守 `AGENTS.md` 分包边界与结构冻结规范，主逻辑归入上下文子包 `backend/bid-core/icg/domain/`：

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/compliance_rules.py` | 规则引擎实现 | 实现 `check_r05`、`check_r06`、`check_r08`、`check_r12`、`check_r20` 及 `evaluate_p3_rules` 管道，在 `CATALOG` 注册新规则并聚合进 `evaluate_all`（全系统规则总数提升至 21 项） |
| `backend/bid-core/icg/domain/workflow_orchestrator.py` | 规则目录收录 | 在 `WorkflowService.IMPLEMENTED_RULES` 中收录 R05、R06、R08、R12、R20，扩展覆盖度 |
| `backend/bid-core/icg/domain/export_service.py` | 导出门禁联动 | 保证 checks 结果中汇总的 P3 blocker 缺陷在正式递交版（submission）导出时严格触发 400 `CHECK_BLOCKER_EXISTS`，严禁带病递交 |
| `tests/backend/test_compliance_rules_p3.py` | 专属单测 | 覆盖 5 条规则的正反例、多场景验证以及整本递交导出门禁 400 阻断（6 项测试全部通过） |
| `tests/backend/test_compliance_rules.py` | 目录全集测试 | 同步更新 `expected` 规则目录至 21 项核心规则，测试全部通过 |

---

## 3. 验收命令与执行证据

运行专属单测命令：
```powershell
pytest tests/backend/test_compliance_rules_p3.py -v
```

执行证据：
```text
tests/backend/test_compliance_rules_p3.py::test_r05_financial_metrics_compliance PASSED [ 16%]
tests/backend/test_compliance_rules_p3.py::test_r06_performance_case_sufficiency PASSED [ 33%]
tests/backend/test_compliance_rules_p3.py::test_r08_delivery_timeline_deviation PASSED [ 50%]
tests/backend/test_compliance_rules_p3.py::test_r12_sla_warranty_deviation PASSED [ 66%]
tests/backend/test_compliance_rules_p3.py::test_r20_quotation_collusion_risk_detection PASSED [ 83%]
tests/backend/test_compliance_rules_p3.py::test_export_gate_blocked_by_p3_compliance_rules PASSED [100%]
============================== 6 passed in 9.61s ==============================
```

综合运行全部合规套件大回归（P0 + P1 + P2 + P3 + AI cross check）：
```powershell
pytest tests/backend/test_compliance_rules.py tests/backend/test_compliance_rules_p0.py tests/backend/test_compliance_rules_p1.py tests/backend/test_compliance_rules_p2.py tests/backend/test_compliance_rules_p3.py tests/backend/test_ai_compliance_cross_check.py
============================= 42 passed in 39.85s =============================
```

OpenAPI 契约零漂移核验：
```powershell
python backend/bid-core/export_openapi.py --check
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

工程治理与链接校验：
```powershell
node scripts/check-project-governance.cjs
治理检查通过：556 份 Markdown、417 项任务、38 项 Issue。
```

---

## 4. 签署建议

本卡改动严格限定在后端领域规则引擎与门禁逻辑实现，测试全绿，已推至 `in-review`。
依据项目治理纪律，建议由 QA 执行独立签署核验 + PD 产品对照验收核准后，由人类 PM 最终标 `done`。
