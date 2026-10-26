# 任务交付：PRD P1 核心合规规则引擎扩充与导出门禁联动（BE-COMPLIANCE-RULES-P1）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-COMPLIANCE-RULES-P1 |
| 代码解释 | [PRD P1 核心合规规则引擎扩充代码说明](../code/BE-COMPLIANCE-RULES-P1.md) |
| 验收 | 1. 规则引擎扩充：在 `backend/bid-core/icg/domain/compliance_rules.py` 完整实现 PRD MVP §5.8 第二批核心合规规则（R03/R04/R09/R10）；<br>2. 业务阻断红线：资质过期/缺失/失信名单（R03）、联合体协议书/成员资质缺失（R04）、服务期未承诺/负偏离（R09）、质保期低于基线/响应时间超标/跨章节承诺自相矛盾（R10）均判定为 blocker；<br>3. 导出门禁严格联动：在 `backend/bid-core/icg/domain/export_service.py` 严格校验，存在任一 blocker 缺陷时，正式递交版导出强阻断并返回 400 `CHECK_BLOCKER_EXISTS`；<br>4. 自动化测试套件：`tests/backend/test_compliance_rules_p1.py` 5 项测试全部通过（5 passed）；<br>5. 契约无漂移：OpenAPI 100% 对齐无 diff。 |
| 项目进度 | 本次交付完成，测试全绿，推至 `in-review`，等待 QA 复测签署与 PD 对照核准，建议人类 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 §5.8 规则定义及质量整改要求，系统在已完成最小集（R15/R23/R34/R37）与 P0 规则（R01/R02/R35）后，需继续闭环 P1 级核心商务与资质合规规则（R03/R04/R09/R10），筑牢废标阻断防线：
1. **R03 资质有效期与信誉核验**：核验营业执照与行业资质证书在投标截止时间 `deadline` 是否有效，且未被列入失信名单；过期或缺失判为 blocker；
2. **R04 联合体投标协议核验**：当项目为联合体投标时，核验是否已附联合体协议书及各成员资质，缺失判为 blocker；独立主体投标自动放行；
3. **R09 服务期/工期与 SLA 承诺核验**：核验服务期与 SLA 承诺指标是否负偏离；工期超出招标要求或 SLA 负偏离强拦截；
4. **R10 质保期与服务响应时间核验**：质保期承诺低于招标基线、故障响应时间负偏离、或各分册/章节间质保承诺自相矛盾时，严格判定为 blocker 并在递交版导出时强阻断。

---

## 2. 核心架构与分包清单

所有改动严格遵守分包边界，逻辑均落地于 `backend/bid-core/icg/domain/`：

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/compliance_rules.py` | 规则引擎实现 | 实现 `check_r03`、`check_r04`、`check_r09`、`check_r10` 及 P1 批次规则管道，集成至统一合规规则评估流程 |
| `backend/bid-core/icg/domain/export_service.py` | 导出门禁联动 | 保证 checks 结果中携带的 P1 blocker 缺陷严格触发 400 `CHECK_BLOCKER_EXISTS`，严禁带病递交 |
| `tests/backend/test_compliance_rules_p1.py` | 专属单测 | 覆盖 R03 正反例、R04 联合体/独立投标、R09 服务期/SLA、R10 质保期跨章矛盾、以及递交导出门禁 400 阻断 |

---

## 3. 验收命令与执行证据

运行命令：
```powershell
pytest tests/backend/test_compliance_rules_p1.py -v
```

执行结果：
```text
tests/backend/test_compliance_rules_p1.py::test_r03_qualification_validity_and_credit PASSED [ 20%]
tests/backend/test_compliance_rules_p1.py::test_r04_consortium_agreement_verification PASSED [ 40%]
tests/backend/test_compliance_rules_p1.py::test_r09_service_period_and_sla_commitment PASSED [ 60%]
tests/backend/test_compliance_rules_p1.py::test_r10_warranty_period_and_response_time PASSED [ 80%]
tests/backend/test_compliance_rules_p1.py::test_export_gate_blocked_by_p1_compliance_rules PASSED [100%]
============================== 5 passed in 4.96s ==============================
```
