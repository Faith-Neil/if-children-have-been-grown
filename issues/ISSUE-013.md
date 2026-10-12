为什么有这个文件：登记把可信会话真实HTTP复核纳入仓库并记录QA独立复跑结果的变更。

它解决什么问题：原“真实会话HTTP16项”依赖仓库外临时验证器，其他人和CI无法重跑；独立复跑结果也需要可追溯记录。

# ISSUE-013：会话真实HTTP复核入库与QA复跑记录

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-013 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | qa-rerun-3 |
| 关联 Task | [REV-M0-T02](../docs/tasks/REV-M0.md#rev-m0-t02)、[REV-M0-T05](../docs/tasks/REV-M0.md#rev-m0-t05)（QA签署复核）、[REV-M0-T07](../docs/tasks/REV-M0.md#rev-m0-t07)（BE-M0-T02/T03签署）、[REV-M0-T09](../docs/tasks/REV-M0.md#rev-m0-t09)（BE-M0-T08/T10签署）、[REV-M0-T10](../docs/tasks/REV-M0.md#rev-m0-t10)（BE-M0-T15 Word版式签署）、[REV-M0-T11](../docs/tasks/REV-M0.md#rev-m0-t11)（T001/T002复验签署）、[REV-M0-T12](../docs/tasks/REV-M0.md#rev-m0-t12)（BE-M0-T14 MySQL CI签署）、[REV-M0-T13](../docs/tasks/REV-M0.md#rev-m0-t13)（ISSUE-026快照规则签署）、[REV-M0-T14](../docs/tasks/REV-M0.md#rev-m0-t14)（ISSUE-014 ProLayout签署）、[REV-M0-T15](../docs/tasks/REV-M0.md#rev-m0-t15)（ISSUE-020路由分包签署）、[REV-M0-T16](../docs/tasks/REV-M0.md#rev-m0-t16)（ISSUE-016检索骨架签署）、[REV-M0-T08](../docs/tasks/REV-M0.md#rev-m0-t08)（T001签署）；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)，待合入 |
| 本地验收 | 通过；2026-10-12，成长测试QA |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [REV-M0-T02交付](../docs/delivery/REV-M0-T02.md) |
| 代码 / 流程解释 | [REV-M0-T02代码解释](../docs/code/REV-M0-T02.md) |
| 验证记录 | [QA独立复跑](../docs/testing/2026-10-12-qa-rerun.md)；[QA签署复核](../docs/testing/2026-10-12-qa-signoff.md)；[T001签署](../docs/testing/2026-10-12-e2e-t001-signoff.md) |

## 现象与证据

[共同底座阶段验证](../docs/testing/2026-10-11-application-session.md)记载“真实监听会话16项全部通过”，但验证器及结果文件位于作者本机临时目录，仓库内没有可重跑脚本。QA于2026-10-12独立复跑全部测试，并按该文描述重建实时会话检查。

## 影响与分流

- 影响：只增加不被pytest默认收集的验证脚本及验证/交付记录；不改应用代码、接口或产品行为。
- 不涉及：原16项中无法从仓库还原精确清单的部分不虚构；APP-M2-T001状态不变。
- 依赖：无。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| REV-M0-T05 | APP-M2-T008与AI-02签署复跑及基线核对 | `docs/testing/2026-10-12-qa-signoff.md` | AC-04 | done |
| REV-M0-T07 | BE-M0-T02与BE-M0-T03签署复跑、真实HTTP探针及基线核对 | `docs/testing/2026-10-12-be-m0-t02-t03-signoff.md` | AC-04 | done |
| REV-M0-T09 | BE-M0-T08与BE-M0-T10签署复跑、真实MySQL 8.4迁移与门禁核对 | `docs/testing/2026-10-12-be-m0-t10-mysql-signoff.md` | AC-04 | done |
| REV-M0-T10 | BE-M0-T15 Word 默认版式按原文独立核对、样张与 LibreOffice 渲染 | `docs/testing/2026-10-12-be-m0-t15-word-style-signoff.md` | AC-04 | done |
| REV-M0-T11 | APP-M2-T001与APP-M2-T002修复复验、请求计数探针与对比度独立计算 | `docs/testing/2026-10-12-qa-t001-t002-signoff.md` | AC-04 | done |
| REV-M0-T12 | BE-M0-T14托管MySQL CI验收：Actions日志、本地迁移往返与守卫负例 | `docs/testing/2026-10-12-be-m0-t14-mysql-ci-signoff.md` | AC-04 | done |
| REV-M0-T13 | ISSUE-026快照规则签署 | `docs/testing/2026-10-12-issue-026-snapshot-signoff.md` | AC-04 | done |
| REV-M0-T14 | ISSUE-014 ProLayout签署 | `docs/testing/2026-10-12-issue-014-prolayout-signoff.md` | AC-04 | done |
| REV-M0-T15 | ISSUE-020路由分包签署 | `docs/testing/2026-10-12-issue-020-route-split-signoff.md` | AC-04 | done |
| REV-M0-T16 | ISSUE-016检索骨架签署 | `docs/testing/2026-10-12-issue-016-retrieval-signoff.md` | AC-04 | done |
| REV-M0-T02 | 会话实时HTTP复核入库、全套复跑记录 | `tests/backend/session_live_http.py`、`docs/testing/2026-10-12-qa-rerun.md` | AC-01～03 | done |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 脚本自启本机后台于空闲端口、只用合成种子数据、无新依赖，15项全部通过 | 通过；`python tests/backend/session_live_http.py` → TOTAL 15 PASS 15 |
| AC-02 | 默认后台回归不受影响 | 通过；`pytest tests/backend -q` 262 passed |
| AC-03 | 复跑命令、环境、各套件计数及局限有记录；治理检查通过 | 通过；见QA复跑记录与交付 |
| AC-04 | T008与AI-02签署复跑、Actions运行及基线同步核对有记录 | 通过；两卡签署通过，S1～S5登记 |

## 六份基线 impact 与同步表

| 基线 | impact | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响：未改需求或功能范围 | 无 | — / ISSUE-013 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响：未改阶段或里程碑 | 无 | — / ISSUE-013 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响：未改接口、模块或部署结构 | 无 | — / ISSUE-013 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响：新增REV-M0-T02、T05 done | `docs/TASK_BOARD.md` | 0.6 / ISSUE-013 / 2026-10-12 | 已同步 |
| PROJECT_STATUS | 有影响：任务计数与QA复跑结论 | `docs/PROJECT_STATUS.md` 任务进度口径 | — / ISSUE-013 / 2026-10-12 | 已同步 |
| DOCUMENT_INDEX | 有影响：登记D-173～D-177 | `docs/DOCUMENT_INDEX.md` | g1.1 / ISSUE-013 / 2026-10-12 | 已同步 |

WORKFLOW无规则变化，治理块保持g1.1。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | qa-rerun-1 / in-progress | 登记并开工 | 项目经理分配编号 |
| 2026-10-12 | qa-rerun-1 / closed | 脚本入库15/15、后台262、前端72、构建及治理检查通过 | 成长测试QA |
| 2026-10-12 | qa-rerun-2 / closed | 签署T008、AI-02：Actions三次成功，本地292/30/72/35通过；BRIEF未登记等S1～S5 | 成长测试QA |
| 2026-10-12 | qa-rerun-3 / in-review | APP-M2-T001签署（REV-M0-T08）：复跑一致，E2E发现D1～D4，结论不通过；待项目经理确认 | 成长测试QA |
| 2026-10-12 | qa-rerun-4 / in-review | T001重签：D1～D4已修复，新发现E2E-D7（P1，导航无法展开），仍不通过；T002探测19项，502+MODEL_UNAVAILABLE在a844a17会重试，e73523f已改为不重试（探测确认），T002-F1（P2）待定，暂不签；ISSUE-020分包通过；见[记录](../docs/testing/2026-10-12-qa-t001-t002-t020-recheck.md) | 成长测试QA |
| 2026-10-12 | qa-rerun-5 / done | T001/T002复验（REV-M0-T11）：E2E-D7、E2E-D8、T002-F1已修复；92/35、tsc、E2E 13/13、探针27/27、对比度≥5.66:1；两卡签署通过，仍in-review待项目经理确认；O1 P3观察 | 成长测试QA |
| 2026-10-12 | qa-rerun-6 / done | BE-M0-T14签署（REV-M0-T12）：AC-01～04通过，Actions真实连库2 passed、失败样例变红；本地8.4.6往返、337 passed、守卫负例全判失败；M1～M3 P3；T14仍in-review待项目经理确认 | 成长测试QA |
| 2026-10-12 | qa-rerun-7 / done | BE-M0-T15 Q1～Q3复核（REV-M0-T10 复核二，034b184/f989af7）：检查器补Q1缩进、Q2无标题无目录、Q3规格中文；样张69/69、h1左64/64、技术册与商务册50/50、承诺函45/45；样张已覆盖；无新缺陷；T15仍in-review待用户Word/WPS确认 | 成长测试QA |
| 2026-10-12 | qa-rerun-8 / done | ISSUE-026快照规则签署（REV-M0-T13）：AC通过；看板独立重数366项（32/6/7/268/49/4）与快照一致；规则在ISSUE-026、同步表、WORKFLOW第4节；检查程序不比对快照；模拟签收AI-03仍通过；CI 38212117391全绿；ISSUE-026保持in-review，待项目经理设置done | 成长测试QA |
| 2026-10-12 | qa-rerun-9 / done | ISSUE-014 ProLayout签署（REV-M0-T14）：AC-01、AC-02通过；直接依赖仅新增pro-layout 7.22.7；引入前后1334.42→1564.53 kB逐字复现；ISSUE-014保持in-review，待项目经理设置done | 成长测试QA |
| 2026-10-12 | qa-rerun-10 / done | ISSUE-020路由分包签署（REV-M0-T15）：AC-01～03通过；入口317.71 kB/gzip 101.64 kB，预加载合计1081.97 kB低于1334.42 kB；node --test 92/92、tsc、E2E 13 passed；ISSUE-020保持in-review，待项目经理设置done | 成长测试QA |
| 2026-10-12 | qa-rerun-11 / done | ISSUE-016检索骨架签署（REV-M0-T16）：AC-01～05通过；契约7项、补充探针（越界记录、嵌入超时）均回退到A；后台349 passed/6 skipped(mysql)；ISSUE-016与AI-03保持in-review，待项目经理设置done | 成长测试QA |

## 本地验收与后续合入发布

- 本地验收结论与日期：通过，2026-10-12。
- 未覆盖：原16项中有1项无法还原；未做GUI复验。
- PR状态：PR #3待合入；未发布。
