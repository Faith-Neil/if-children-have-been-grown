# 代码说明：PRD P5 终批核心合规规则引擎扩充与整本导出门禁全覆盖闭环（BE-COMPLIANCE-RULES-P5）

## 1. 代码变更概览

本任务在后端 `backend/bid-core/icg/domain/` 下扩充落地了 PRD MVP §5.8 第六批（终批）核心合规规则体系（R17, R19, R26, R27, R28），使系统规则总数达到 31 项全覆盖：

```
backend/bid-core/icg/
└── domain/
    ├── compliance_rules.py        # 修改：落地 check_r17, check_r19, check_r26, check_r27, check_r28，更新 CATALOG 与 evaluate_all
    └── workflow_orchestrator.py   # 修改：更新 WorkflowService.IMPLEMENTED_RULES 登记名单（行数控制在 334 行 <= 350 行）
tests/backend/
├── test_compliance_rules.py       # 修改：更新 test_compliance_rules_catalog 预期 31 项已实现规则名单
└── test_compliance_rules_p5.py    # 新增：6 项专属自动化测试（正反例及导出门禁联动验证）
```

---

## 2. 关键代码解析

### 2.1 规则算法实现 (`backend/bid-core/icg/domain/compliance_rules.py`)

#### (1) R17 关联交易与利害关系回避核验 (`check_r17`)
核验投标人与招标人、代理机构之间是否存在单位负责人同一人、控股参股、未回避利害关系等实质性利益冲突：

```python
interest_keywords = ("利害关系", "关联交易", "回避", "利益冲突", "单位负责人为同一人", "控股", "参股", "母子公司", "关联方", "存在利害关系")
negative_conflict_triggers = (
    "存在关联关系", "存在利害关系", "未回避", "存在控股关系", "参股招标代理机构",
    "控股股东为招标人", "单位负责人为同一人", "存在直接利益冲突", "未签署回避声明",
    "构成关联交易未披露", "存在实质性关联", "未满足回避要求", "与招标人存在利害关系",
)
```
存在未回避实质性利害关系或未填写响应承诺判定为 blocker（`CONFLICT_OF_INTEREST_UNRESOLVED`）。

#### (2) R19 环保、节能与绿色采购强制产品认证核验 (`check_r19`)
核验设备耗材是否属于国家强制采购节能品目，并排查有效认证证书与能效标识：

```python
green_keywords = ("节能产品", "节能认证", "环保标志", "绿色采购", "强制节能", "强制采购节能产品", "能效标识", "低碳认证", "环境标志", "中国节能产品认证")
negative_green_triggers = (
    "未取得节能认证", "无绿色采购证书", "强制节能产品未认证", "能效未达标",
    "无环保标志认证", "暂未提供节能证书", "节能认证已过期", "未列入节能品目清单",
    "不满足绿色采购要求", "能效指标不合格", "节能证书缺失",
)
```
强制节能品目未认证或证书缺失判定为 blocker（`MANDATORY_GREEN_CERT_MISSING`）。

#### (3) R26 知识产权与侵权无争议声明核验 (`check_r26`)
核验投标方案与软件产品是否声明自主知识产权，并排查是否提供全额侵权兜底赔偿承诺：

```python
ip_keywords = ("知识产权", "侵权", "免责", "专利", "软件著作权", "自主知识产权", "侵权责任", "侵权赔偿", "兜底承诺", "无争议声明", "知识产权纠纷")
negative_ip_triggers = (
    "不承担侵权责任", "无法承诺无知识产权争议", "第三方侵权免责排除",
    "侵权责任由招标人承担", "未声明自主知识产权", "存在知识产权争议",
    "涉嫌专利侵权", "未承诺无争议兜底", "拒绝承担侵权赔偿", "知识产权归属存疑",
    "不提供侵权赔偿承诺",
)
```
未声明自主知识产权或推卸侵权责任判定为 blocker（`IP_INFRINGEMENT_INDEMNITY_MISSING`）。

#### (4) R27 本地化服务网点与常驻技术力量核验 (`check_r27`)
核验招标文件强制要求的本地售后网点、分支机构及常驻技术工程师清单：

```python
local_keywords = ("本地化服务", "售后网点", "分支机构", "驻场机构", "驻点技术人员", "本地售后", "本地分公司", "本地办事处", "本地服务机构", "常驻技术人员")
negative_local_triggers = (
    "无本地服务机构", "无本地网点", "未设立办事处", "无法驻场",
    "无常驻技术人员", "无本地化支持力量", "不具备本地售后条件", "暂无分支机构",
    "无法提供本地化响应", "未设立本地服务网点", "本地化机构缺失",
)
```
本地化机构缺失或人员配备不达标判定为 blocker（`LOCAL_SERVICE_BRANCH_MISSING`）。

#### (5) R28 关键技术规格实质性负偏离排查 (`check_r28`)
核验技术规格参数偏离表中是否存在招标文件中声明不得负偏离的关键指标负偏离：

```python
tech_keywords = ("技术规格", "关键指标", "关键参数", "实质性要求", "不得负偏离", "参数偏离", "核心技术参数", "关键技术指标", "不可负偏离", "技术参数偏离")
negative_deviation_triggers = (
    "实质性负偏离", "指标不满足", "参数低于要求",
    "关键指标不满足", "关键参数负偏离", "存在重大负偏离", "无法满足技术规格",
    "指标负偏离", "参数有偏离且低于招标要求",
)
# 采用正则反向先行断言严格排除“无负偏离”正向声明
has_neg_deviation = any(t in resp for t in negative_deviation_triggers) or bool(re.search(r"(?<!无)(?<!不)负偏离", resp))
```
字段直接标记 `deviation_type="negative"` 或实质性指标低于招标要求判定为 blocker（`CRITICAL_TECH_SPEC_NEGATIVE_DEVIATION`）。

### 2.2 评估管道与目录聚合 (`evaluate_p5_rules` 与 `evaluate_all`)

```python
@classmethod
def evaluate_p5_rules(cls, state, project, workflow, volume="all", now_ts=None):
    return [
        cls.check_r17(state, project, workflow, volume=volume),
        cls.check_r19(state, project, workflow, volume=volume),
        cls.check_r26(state, project, workflow, volume=volume),
        cls.check_r27(state, project, workflow, volume=volume),
        cls.check_r28(state, project, workflow, volume=volume),
    ]

@classmethod
def evaluate_all(cls, state, project, workflow, volume="all", now_ts=None):
    return (
        cls.evaluate_p0_rules(state, project, workflow, volume=volume, now_ts=now_ts)
        + cls.evaluate_p1_rules(state, project, workflow, volume=volume, now_ts=now_ts)
        + cls.evaluate_p2_rules(state, project, workflow, volume=volume, now_ts=now_ts)
        + cls.evaluate_p3_rules(state, project, workflow, volume=volume, now_ts=now_ts)
        + cls.evaluate_p4_rules(state, project, workflow, volume=volume, now_ts=now_ts)
        + cls.evaluate_p5_rules(state, project, workflow, volume=volume, now_ts=now_ts)
    )
```

---

## 3. 测试覆盖说明

在 `tests/backend/test_compliance_rules_p5.py` 中编写 6 项独立测试函数：
1. `test_r17_conflict_of_interest_compliance`: 验证正向无利害关系承诺放行，未填写、标记 rejected 或披露存在关联交易阻断；
2. `test_r19_mandatory_green_cert_compliance`: 验证具备节能认证证书放行，未填写、标记 rejected 或无节能证书阻断；
3. `test_r26_ip_infringement_indemnity_compliance`: 验证具备自主知识产权与无条件兜底放行，声明缺失或推卸侵权责任阻断；
4. `test_r27_local_service_branch_compliance`: 验证具备本地分公司执照与常驻技术人员放行，未响应或无本地机构阻断；
5. `test_r28_critical_tech_spec_negative_deviation_compliance`: 验证关键指标无负偏离放行，未填响应参数、标记 negative 或参数负偏离阻断；
6. `test_export_gate_blocked_by_p5_compliance_rules`: 验证存在任一 P5 规则 blocker 缺陷时正式递交版导出严格被 400 `CHECK_BLOCKER_EXISTS` 门禁拦截，内部评审版允许导出（`has_blockers=True`），修复后重新导出内部评审版 `has_blockers=False`，且递交版导出严格遵守 409 `RULES_INCOMPLETE` 门禁。
