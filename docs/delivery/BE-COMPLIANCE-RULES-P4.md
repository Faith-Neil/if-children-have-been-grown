# 任务交付：PRD P4 核心合规规则引擎扩充与整本导出门禁联动（BE-COMPLIANCE-RULES-P4）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-COMPLIANCE-RULES-P4 |
| 代码解释 | [PRD P4 核心合规规则引擎扩充代码说明](../code/BE-COMPLIANCE-RULES-P4.md) |
| 验收 | 1. 规则引擎扩充：在 `backend/bid-core/icg/domain/compliance_rules.py` 完整落地 PRD MVP §5.8 第五批核心合规规则（R13/R16/R18/R24/R32），全系统目录与实现规则总数达到 26 项；<br>2. 业务阻断红线：项目经理执业资格/社保缺失或团队人数不达标（R13，`TEAM_PROJECT_MANAGER_QUALIFICATION_MISSING` / `TEAM_STAFFING_THRESHOLD_UNMET`）、投标保证金/保函不足或第三方代缴（R16，`BID_SECURITY_DEPOSIT_NON_COMPLIANT`）、联合体投标协议缺失/牵头人未授权（R18，`CONSORTIUM_AGREEMENT_INVALID`）、法定表单未盖章/未签名/空表单（R24，`MANDATORY_SEAL_SIGNATURE_MISSING`）、投标有效期缩水或保留撤销权（R32，`BID_VALIDITY_PERIOD_DEFICIENT`）均严格判定为 blocker；<br>3. 导出门禁联动：在 `backend/bid-core/icg/domain/export_service.py` 保证上述 blocker 缺陷在正式递交版（submission）导出时严格触发 400 `CHECK_BLOCKER_EXISTS`，内部评审版允许导出但显式标记 `has_blockers=True` 与合规警示；<br>4. 自动化测试套件：`tests/backend/test_compliance_rules_p4.py` 6 项测试全部通过，回归套件 37 项全部通过；<br>5. 契约无漂移：OpenAPI 100% 对齐无 diff。 |
| 项目进度 | 本卡实现完成并通过全部专项单元测试与大回归测试，状态推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 §5.8 规则定义及质量整改要求，系统在已完成 P0（7 条）、P1（4 条）、P2（5 条）及 P3（5 条）共 21 条核心规则后，扩充落地第五批核心合规规则（R13, R16, R18, R24, R32），并与整本导出门禁（400 `CHECK_BLOCKER_EXISTS`）深度联动：
1. **R13 团队人员配置核验（项目经理执业资格、持证人数门槛）**：核验拟派项目经理执业资格证书（一级建造师、PMP 等）、连续在缴社保证明以及常驻专业技术团队持证人数最低门槛；资质缺失或人数不足判定为 `blocker`（`TEAM_PROJECT_MANAGER_QUALIFICATION_MISSING`、`TEAM_STAFFING_THRESHOLD_UNMET`）；
2. **R16 投标保证金与保函有效性核验**：核验投标保证金金额是否满足招标文件金额或比例要求、保函有效期是否覆盖投标有效期、出账账户是否与投标主体完全一致（基本户转出）；保证金不足或第三方代缴判定为 `blocker`（`BID_SECURITY_DEPOSIT_NON_COMPLIANT`）；
3. **R18 联合体投标协议与资质认定核验**：若声明联合体投标，核验是否签署正式有效的联合体协议书、明确牵头人法定授权及各成员资质分工；非联合体投标免检放行；若联合体协议缺失或资质不符判定为 `blocker`（`CONSORTIUM_AGREEMENT_INVALID`）；
4. **R24 响应格式排版与强制表单签名盖章完整性核验**：核验法定代表人或授权委托人签字盖章页、投标函等关键法定表单的签名盖章完整性；缺少签名或盖章占位标记判定为 `blocker`（`MANDATORY_SEAL_SIGNATURE_MISSING`）；
5. **R32 投标有效期与承诺不可撤销性核验**：核验投标函中承诺的投标有效期是否小于招标文件规定的日历天数（如 90 天）；承诺有效期缩水或附带可撤销条件判定为重大负偏离 `blocker`（`BID_VALIDITY_PERIOD_DEFICIENT`）。

---

## 2. 核心架构与分包清单

所有新增实现严格遵守 `AGENTS.md` 分包边界与结构冻结规范，主逻辑归入上下文子包 `backend/bid-core/icg/domain/`：

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/compliance_rules.py` | 规则引擎实现 | 实现 `check_r13`、`check_r16`、`check_r18`、`check_r24`、`check_r32` 及 `evaluate_p4_rules` 管道，在 `CATALOG` 注册新规则并聚合进 `evaluate_all`（全系统规则总数提升至 26 项） |
| `backend/bid-core/icg/domain/workflow_orchestrator.py` | 规则目录收录 | 在 `WorkflowService.IMPLEMENTED_RULES` 中收录 R13、R16、R18、R24、R32，维持总行数 <= 350（实测 334 行） |
| `backend/bid-core/icg/domain/export_service.py` | 导出门禁联动 | 保证 checks 结果中汇总的 P4 blocker 缺陷在正式递交版（submission）导出时严格触发 400 `CHECK_BLOCKER_EXISTS`，严禁带病递交 |
| `tests/backend/test_compliance_rules_p4.py` | 专属单测 | 覆盖 5 条规则的正反例、多场景验证以及整本递交导出门禁 400 阻断（6 项测试全部通过） |

---

## 3. 验收命令与执行证据

运行专属单测命令：
```powershell
pytest tests/backend/test_compliance_rules_p4.py -v
```

执行证据：
```text
tests/backend/test_compliance_rules_p4.py::test_r13_team_staffing_compliance PASSED [ 16%]
tests/backend/test_compliance_rules_p4.py::test_r16_bid_security_deposit_compliance PASSED [ 33%]
tests/backend/test_compliance_rules_p4.py::test_r18_consortium_agreement_compliance PASSED [ 50%]
tests/backend/test_compliance_rules_p4.py::test_r24_mandatory_seal_signature_compliance PASSED [ 66%]
tests/backend/test_compliance_rules_p4.py::test_r32_bid_validity_period_compliance PASSED [ 83%]
tests/backend/test_compliance_rules_p4.py::test_export_gate_blocked_by_p4_compliance_rules PASSED [100%]
============================== 6 passed in 6.72s ==============================
```

核心与跨领域回归测试：
```powershell
pytest tests/backend/test_compliance_rules_p3.py tests/backend/test_checks_export_blocker_gate.py tests/backend/test_workflow_orchestrator_modular.py tests/backend/test_reference_flow.py -v
============================= 37 passed in 31.86s =============================
```

OpenAPI 契约零漂移核验：
```powershell
python backend/bid-core/export_openapi.py --check
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

工程治理与链接校验：
```powershell
node scripts/check-project-governance.cjs
治理检查通过：582 份 Markdown、425 项任务、38 项 Issue。
```

---

## 4. 交付总结与建议

- 本次交付完整覆盖 PRD MVP §5.8 第五批核心合规规则（R13/R16/R18/R24/R32），全部代码严格落盘在 `icg/domain/` 上下文包；
- 导出门禁无缝拦截任何 blocker 缺陷，阻断违规导出正式递交文件；
- 建议 PM 在后续验收通过后将 `BE-COMPLIANCE-RULES-P4` 标为 `done`。
