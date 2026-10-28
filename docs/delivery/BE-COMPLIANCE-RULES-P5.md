# 任务交付：PRD P5 终批核心合规规则引擎扩充与整本导出门禁全覆盖闭环（BE-COMPLIANCE-RULES-P5）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-COMPLIANCE-RULES-P5 |
| 代码解释 | [PRD P5 终批核心合规规则引擎扩充代码说明](../code/BE-COMPLIANCE-RULES-P5.md) |
| 验收 | 1. 规则引擎扩充：在 `backend/bid-core/icg/domain/compliance_rules.py` 完整落地 PRD MVP §5.8 第六批（终批）核心合规规则（R17/R19/R26/R27/R28），全系统已实现并纳入目录的合规规则总数达到 **31 项** 全覆盖；<br>2. 业务阻断红线落地：投标人与招标人/招标代理机构实质性利害关系未回避（R17，`CONFLICT_OF_INTEREST_UNRESOLVED`）、强制节能品目未附有效认证证书或未达标（R19，`MANDATORY_GREEN_CERT_MISSING`）、未声明完全自主知识产权或拒绝承担侵权兜底赔偿（R26，`IP_INFRINGEMENT_INDEMNITY_MISSING`）、缺少招标文件要求的本地售后服务机构与驻点技术人员（R27，`LOCAL_SERVICE_BRANCH_MISSING`）、关键技术规格与核心指标存在实质性负偏离（R28，`CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION`）均严格判定为 blocker 废标红线；<br>3. 导出门禁联动与底线坚守：在 `export_service.py` 保证上述 blocker 缺陷在正式递交版（submission）导出时严格触发 400 `CHECK_BLOCKER_EXISTS`；内部评审版允许导出但显式标记 `has_blockers=True`；未完成分册定稿时严格诚实守卫 409 `RULES_INCOMPLETE`，绝不绕过门禁假装可递交；<br>4. 自动化测试套件：专属测试套件 `tests/backend/test_compliance_rules_p5.py` 6 项测试全绿通过，P0~P5 全量合规规则套件 45 项全部通过；<br>5. 契约无漂移：OpenAPI 100% 对齐无漂移；工程治理 100% 通过。 |
| 项目进度 | 本卡实现完成并通过全部专项单元测试、全量规则回归测试与治理检查，状态推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 §5.8 规则定义及质量整改要求，系统在已完成 P0（7 条）、P1（4 条）、P2（5 条）、P3（5 条）及 P4（5 条）共 26 条核心规则后，扩充落地第六批（终批）核心合规规则（R17, R19, R26, R27, R28），使系统核心规则总数达到 **31 项** 全覆盖，并与整本导出门禁（400 `CHECK_BLOCKER_EXISTS`）深度联动：
1. **R17 关联交易与利害关系回避核验**：核验投标人与招标人、招标代理机构是否存在单位负责人为同一人或控股参股等利害关系；存在实质性利害关系未回避判定为 `blocker`（`CONFLICT_OF_INTEREST_UNRESOLVED`）；
2. **R19 环保、节能与绿色采购强制产品认证核验**：核验设备耗材是否属于国家强制节能品目并附有效证书清单；强制品目未提供认证判定为 `blocker`（`MANDATORY_GREEN_CERT_MISSING`）；
3. **R26 知识产权与侵权无争议声明核验**：核验方案/产品是否声明自主知识产权并提供侵权免责与争议兜底承诺；缺少合规声明判定为 `blocker`（`IP_INFRINGEMENT_INDEMNITY_MISSING`）；
4. **R27 本地化服务网点与常驻技术力量核验**：核验招标文件强制要求的本地售后网点或驻场机构证明；要求本地化而无有效网点判定为 `blocker`（`LOCAL_SERVICE_BRANCH_MISSING`）；
5. **R28 关键技术规格实质性负偏离排查**：核验技术规格参数偏离表中是否存在招标文件中声明不得负偏离的关键指标负偏离；存在负偏离判定为 `blocker`（`CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION`）；
6. **整本递交导出门禁联动与底线坚守**：存在任一 blocker 缺陷时，正式递交版导出严格触发 400 `CHECK_BLOCKER_EXISTS`；消减 blocker 后导出内部评审版正常放行（`has_blockers=False`）；分册定稿未完成时严格诚实守卫 409 `RULES_INCOMPLETE`，绝不绕过门禁假装已可递交。

---

## 2. 核心架构与分包清单

所有新增实现严格遵守 `AGENTS.md` 分包边界与结构冻结规范，主逻辑归入上下文子包 `backend/bid-core/icg/domain/`：

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/compliance_rules.py` | 规则引擎实现 | 实现 `check_r17`、`check_r19`、`check_r26`、`check_r27`、`check_r28` 及 `evaluate_p5_rules` 管道，在 `CATALOG` 注册新规则并聚合进 `evaluate_all`（全系统核心规则总数提升至 31 项） |
| `backend/bid-core/icg/domain/workflow_orchestrator.py` | 规则目录收录 | 在 `WorkflowService.IMPLEMENTED_RULES` 中收录 R17、R19、R26、R27、R28，维持总行数 <= 350（实测 334 行） |
| `backend/bid-core/icg/domain/export_service.py` | 导出门禁联动 | 保证 checks 结果中汇总的 P5 blocker 缺陷在正式递交版（submission）导出时严格触发 400 `CHECK_BLOCKER_EXISTS`，严禁带病递交 |
| `tests/backend/test_compliance_rules.py` | 目录单测更新 | 更新 `test_compliance_rules_catalog` 预期名单，完整断言 31 项已落地核心规则目录 |
| `tests/backend/test_compliance_rules_p5.py` | 专属单测 | 覆盖 5 条规则的正反例、多场景验证以及整本递交导出门禁 400 阻断与 409 RULES_INCOMPLETE 诚实守卫（6 项测试全部通过） |

---

## 3. 验收命令与执行证据

### 3.1 专属自动化测试
运行专属自动化测试：
```powershell
pytest tests/backend/test_compliance_rules_p5.py -v
```

执行证据：
```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
plugins: anyio-4.14.2
collected 6 items

tests/backend/test_compliance_rules_p5.py::test_r17_conflict_of_interest_compliance PASSED [ 16%]
tests/backend/test_compliance_rules_p5.py::test_r19_mandatory_green_cert_compliance PASSED [ 33%]
tests/backend/test_compliance_rules_p5.py::test_r26_ip_infringement_indemnity_compliance PASSED [ 50%]
tests/backend/test_compliance_rules_p5.py::test_r27_local_service_branch_compliance PASSED [ 66%]
tests/backend/test_compliance_rules_p5.py::test_r28_critical_tech_spec_negative_deviation_compliance PASSED [ 83%]
tests/backend/test_compliance_rules_p5.py::test_export_gate_blocked_by_p5_compliance_rules PASSED [100%]

============================== 6 passed in 6.37s ==============================
```

### 3.2 P0~P5 全量合规规则联合回归测试
```powershell
pytest tests/backend/test_compliance_rules.py tests/backend/test_compliance_rules_p0.py tests/backend/test_compliance_rules_p1.py tests/backend/test_compliance_rules_p2.py tests/backend/test_compliance_rules_p3.py tests/backend/test_compliance_rules_p4.py tests/backend/test_checks_export_blocker_gate.py tests/backend/test_compliance_rules_p5.py -v
```

执行证据：
```text
============================= 45 passed in 43.60s =============================
```

### 3.3 OpenAPI 契约零漂移核验
```powershell
python backend/bid-core/export_openapi.py --check
```
执行证据：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

### 3.4 工程治理门禁检查
```powershell
node scripts/check-project-governance.cjs
node --test tests/governance/*.test.cjs
```
执行证据：
```text
治理检查通过：602 份 Markdown、432 项任务、38 项 Issue。
✔ 当前治理资料可通过，历史业务版本和模板无需套用当前交付字段 (51.197ms)
...
ℹ pass 12
ℹ fail 0
```

---

## 4. 业务底线与门禁遵守说明

1. **导出门禁严格联动**：凡检测到未回避利害关系、强制节能认证缺失、知识产权无争议声明缺失、本地服务机构缺失或关键技术指标实质性负偏离，检查引擎均给出 `severity="blocker"` 裁决并录入检查快照，导出正式递交版时由 `export_service.py` 严格阻断拦截（400 `CHECK_BLOCKER_EXISTS`）；
2. **RULES_INCOMPLETE 诚实守卫**：在消减上述 blocker 之后，系统因尚未完成分册定稿前置审批流程，导出正式递交版时依旧严格返回 409 `RULES_INCOMPLETE`。交付报告与测试套件诚实记录此阻断，绝不绕过门禁假装规则已全部完成或已达递交上线标准；
3. **状态建议**：本卡实现完整，测试与治理全部通过，状态推至 `in-review`，建议 PM 标 `done`。
