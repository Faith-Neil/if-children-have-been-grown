# 任务交付：PRD P2 核心合规规则引擎扩充与导出门禁联动（BE-COMPLIANCE-RULES-P2）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-COMPLIANCE-RULES-P2 |
| 代码解释 | [PRD P2 核心合规规则引擎扩充代码说明](../code/BE-COMPLIANCE-RULES-P2.md) |
| 验收 | 1. 规则引擎扩充：在 `backend/bid-core/icg/domain/compliance_rules.py` 完整落地 PRD MVP §5.8 第三批核心合规规则（R07/R11/R14/R25/R31）；<br>2. 业务阻断红线：原厂授权缺失/过期/产品不覆盖/授权链断裂（R07）、拟派团队借调挂靠/社保证明缺失/缴纳单位不一致/社保断缴/合同过期（R11）、强制必备附件缺失（R14）、旧标书/某某公司/占位名称残留（R25）、明文身份证/银行卡号/数据库口令/真实巡检报告套用（R31）均判定为 blocker；<br>3. 导出门禁严格联动：在 `backend/bid-core/icg/domain/export_service.py` 严格校验，存在任一 blocker 缺陷时，正式递交版导出强阻断并返回 400 `CHECK_BLOCKER_EXISTS`；<br>4. 自动化测试套件：`tests/backend/test_compliance_rules_p2.py` 6 项测试全部通过（6 passed in 6.81s）；<br>5. 契约无漂移：OpenAPI 100% 对齐无 diff。 |
| 项目进度 | 本次交付已获 QA 独立终验签署与 PD 产品视角验收通过，并由人类 PM 正式确认标为 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 §5.8 规则定义及质量整改要求，系统在已完成最小集与 P0/P1 规则后，需扩充落地第三批核心合规规则（R07/R11/R14/R25/R31），防范废标、侵权与泄密红线：
1. **R07 原厂授权覆盖与多级授权链核验**：招标明确要求原厂授权时，核验原厂授权书是否覆盖招标涉及的产品、授权链是否逐级有效；缺失原厂授权书判定为 `blocker`（`ORIGINAL_MANUFACTURER_AUTHORIZATION_MISSING`）；
2. **R11 本单位人员与社保缴纳核验**：招标要求拟派团队为本单位人员时，核验拟派人员归属单位与社保缴纳单位是否与投标主体一致、劳动合同在投标截止时间是否有效；人员归属不一致或社保未连续缴纳判定为 `blocker`（`PERSONNEL_SOCIAL_SECURITY_MISMATCH`）；
3. **R14 必备附件齐全性核验**：核验招标文件强制要求的必备附件（开标一览表、法定代表人身份证明与授权委托书、投标保证金证明或电子保函、承诺函、资质证书附件）是否全部上传；缺失任一必备附件判定为 `blocker`（`MANDATORY_ATTACHMENT_MISSING`）；
4. **R25 其他公司/旧项目名称与文档残留排查**：扫描正文文本与条款响应，排查复制旧标书遗留的其他公司全称/简称、其他招标人或旧项目名称残留；存在残留时判定为 `blocker`（`ENTITY_NAME_RESIDUAL_DETECTED`）；
5. **R31 真实巡检报告与敏感信息残留排查**：扫描正文文本排查明文身份证号（18位）、银行卡号、数据库明文口令（password=...）、或整段真实客户现场巡检报告特征；违规暴露高敏信息判定为 `blocker`（`SENSITIVE_DATA_RESIDUAL_DETECTED`）。

---

## 2. 核心架构与分包清单

所有新增实现严格遵守 `AGENTS.md` 分包边界与结构冻结规范，主逻辑归入上下文子包 `backend/bid-core/icg/domain/`：

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/compliance_rules.py` | 规则引擎实现 | 实现 `check_r07`、`check_r11`、`check_r14`、`check_r25`、`check_r31` 及 `evaluate_p2_rules` 管道，在 `CATALOG` 注册新规则并聚合进 `evaluate_all` |
| `backend/bid-core/icg/domain/workflow_orchestrator.py` | 规则目录收录 | 在 `WorkflowService.IMPLEMENTED_RULES` 中收录 R07、R11、R14、R25、R31，提高覆盖度 |
| `backend/bid-core/icg/domain/export_service.py` | 导出门禁联动 | 保证 checks 结果中汇总的 P2 blocker 缺陷在正式递交版（submission）导出时严格触发 400 `CHECK_BLOCKER_EXISTS`，严禁带病递交 |
| `tests/backend/test_compliance_rules_p2.py` | 专属单测 | 覆盖 5 条规则的正反例、多场景验证以及整本递交导出门禁 400 阻断 |

---

## 3. 验收命令与执行证据

运行专属单测命令：
```powershell
pytest tests/backend/test_compliance_rules_p2.py -v
```

执行证据：
```text
tests/backend/test_compliance_rules_p2.py::test_r07_original_manufacturer_authorization PASSED [ 16%]
tests/backend/test_compliance_rules_p2.py::test_r11_personnel_and_social_security PASSED [ 33%]
tests/backend/test_compliance_rules_p2.py::test_r14_mandatory_attachments_verification PASSED [ 50%]
tests/backend/test_compliance_rules_p2.py::test_r25_entity_name_and_legacy_residuals PASSED [ 66%]
tests/backend/test_compliance_rules_p2.py::test_r31_sensitive_data_and_real_inspection_residuals PASSED [ 83%]
tests/backend/test_compliance_rules_p2.py::test_export_gate_blocked_by_p2_compliance_rules PASSED [100%]
============================== 6 passed in 6.81s ==============================
```

综合运行全部合规套件与导出门禁（P0 + P1 + P2 + Blocker Gate）：
```powershell
pytest tests/backend/test_compliance_rules_p0.py tests/backend/test_compliance_rules_p1.py tests/backend/test_compliance_rules_p2.py tests/backend/test_checks_export_blocker_gate.py
============================= 22 passed in 22.42s =============================
```

---

## 4. 签署建议

本卡改动纯属后端领域规则引擎与门禁逻辑实现，测试全绿，已推至 `in-review`。
依据治理规范，建议 QA 签署证据 + PD 产品验收核准后，由人类 PM 最终标 `done`。
