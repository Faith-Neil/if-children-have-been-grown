# 「已签等 PM」in-review 任务清单与签署证据汇总（2026-10-26）

为什么有这个文件：汇总梳理经 QA 测试核验与 PD 产品视角对照签署通过的 in-review 任务卡清单，呈现完整证据链，由人类项目经理（PM）进行最终确认与置 done 操作。

它解决什么问题：落实 AGENTS.md 质量整改冻结规则与“开发者只能把卡片标到 in-review，done 必须由人类 PM 最终确认”铁律，严禁 AI 或协作者擅自越权标 done。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | IN-REVIEW-SIGNED-FOR-PM-2026-10-26 |
| 交付内容 | 汇总最近迭代及 Step ①~④ 交付中经 QA 签署通过、PD 对照认可并建议 PM 标 done 的任务清单与完整证据链 |
| 验收 | 严格遵照 AGENTS.md 与看板规范，所有任务保持 `in-review` 状态，不私自修改看板 `done` 状态 |
| 项目进度 | 审计 B7 项闭环：产出建议 done 列表与证据路径，等待人类 PM 审核决策 |
<!-- task-delivery:end -->

## 1. 签署与验收规则遵从说明

根据本仓库《合作项目维护约定》（[AGENTS.md](../../AGENTS.md)）及主 Agent 业务验收标准：
1. **开发者最高标到 `in-review`**；
2. **`done` 必须经 QA 自动化签署证据 + 涉及主路径/契约时 INT 联调证据 + 涉及业务特性时 PD 产品对照，最后由人类 PM 最终确认并设置**；
3. **完成度看 PRD gap，不看 board done/总数占比**；本报告仅作为工单闭环建议，产品完备度仍以 PRD MVP v1.8 及缺口清单为准。

---

## 2. 核心交付物签署清单（建议 PM 确认后标 done）

| 卡ID | 任务名称 / 业务范围 | 交付文件 | QA / 测试签署证据 | PD 产品对照结论 | 状态建议 |
|---|---|---|---|---|---|
| **BE-CHECKS-EXPORT-ALIGN** | 检查阻断红线与整本导出快照版式核对 | [交付](BE-CHECKS-EXPORT-ALIGN.md) / [代码](../code/BE-CHECKS-EXPORT-ALIGN.md) | `pytest tests/backend/test_checks_export_blocker_gate.py` 全绿；阻断红线（废标/★条款）在 submission 模式严格 400，internal 放行；版式指纹与默认排版正常注入 | 对照 PRD §5.10 / §5.11，确认双导出门禁与防伪造底线落实，无假放行，[审查报告](../reviews/2026-10-22-pd-review-REV-SMOKE-001.md) 书面认可 | **建议 PM 标 done** |
| **BE-M0-T07** | OpenAPI operationId 规范化检查 | [交付](BE-M0-T07.md) / [代码](../code/BE-M0-T07.md) | `pytest tests/backend/test_operation_ids.py` 全绿；操作去除冗余 `_api_`，采用 lowerCamelCase 全局唯一标识 | 契约与运行时 100% 对齐，OpenAPI 门禁 `--check` 通过 | **建议 PM 标 done** |
| **REV-SMOKE-001** | 关演示非 demo 主业务链路冒烟与断点排查 | [交付](REV-SMOKE-001.md) | `pytest tests/backend/test_smoke_non_demo_pipeline.py` 全绿；非 demo 登录、创建项目、解析、矩阵、生成、双导出门禁端到端跑通 | 真实企业级 UX 走通，关演示后主路径可用，[审查报告](../reviews/2026-10-22-pd-review-REV-SMOKE-001.md) 书面认可 | **建议 PM 标 done** |
| **FE-SNIPPET-LIBRARY** | 知识库方案片段管理最小页 | [交付](FE-SNIPPET-LIBRARY.md) / [代码](../code/FE-SNIPPET-LIBRARY.md) | `pnpm test`（`snippet-library-page.test.mjs`）全绿；替换 `nav===knowledge` 占位壳，Layout First，企业隔离与变量高亮完整 | 对照 PRD §5.5，消灭知识库占位壳，企业强隔离无越界，[审查报告](../reviews/2026-10-22-pd-review-BATCH1-M2.md) 书面认可 | **建议 PM 标 done** |
| **BE-VOLUME-FINALIZE-GATE** | 分册定稿状态机与前置检查门禁 | [交付](BE-VOLUME-FINALIZE-GATE.md) / [代码](../code/BE-VOLUME-FINALIZE-GATE.md) | `pytest tests/backend/test_volume_finalize_gate.py` 10 项专属单测全绿；仅 lead/admin 可定稿，未解锁/有 blocker 严格 409 拦截 | 对照 PRD §5.8.5，定稿锁死与责任人追踪落地，不绕过 RULES_INCOMPLETE，[审查报告](../reviews/2026-10-22-pd-review-BATCH1-M2.md) 书面认可 | **建议 PM 标 done** |
| **AI-M0-RAGFLOW-VERIFY** | RAGFlow 端点对接与检索隔离审查 | [交付](AI-M0-RAGFLOW-VERIFY.md) / [代码](../code/AI-M0-RAGFLOW-VERIFY.md) | 离线与回归套件通过；多租户 dataset 隔离、路径 C 过滤与出处追溯健全；未连真实端点诚实记录为 blocked | 防编造与溯源语义真实有效，未谎报生产已接好，[审查报告](../reviews/2026-10-22-pd-review-REV-SMOKE-001.md) 认可 | **建议 PM 标 done** |
| **FE-WRITING-ARCHIVE** | 写作档案与风格规范最小页 | [交付](FE-WRITING-ARCHIVE.md) / [代码](../code/FE-WRITING-ARCHIVE.md) | `pnpm test`（`writing-archive-page.test.mjs`）全绿；消灭全局导航最后占位壳，租户强隔离、禁用词库、实时草稿诊断与样章正常 | 对照 PRD §5.6，导航占位壳清零，[审查报告](../reviews/2026-10-22-pd-review-BATCH2-M2.md) 书面认可 | **建议 PM 标 done** |
| **INT-VOLUME-FINALIZE-GLUE** | 分册定稿与工作台/导出的前后端契约胶水 | [交付](INT-VOLUME-FINALIZE-GLUE.md) / [代码](../code/INT-VOLUME-FINALIZE-GLUE.md) | 前端权威测试全绿；`/volumes` 客户端接入，导出中心定稿徽章联动，未定稿禁止递交版导出 | 前后端契约对齐，消除假通，[审查报告](../reviews/2026-10-22-pd-review-BATCH2-M2.md) 书面认可 | **建议 PM 标 done** |
| **BE-COMPLIANCE-RULES-P0** | 第一批核心合规规则编号落地（R15/R23/R34/R37） | [交付](BE-COMPLIANCE-RULES-P0.md) / [代码](../code/BE-COMPLIANCE-RULES-P0.md) | `pytest tests/backend/test_compliance_rules_p0.py` 7 项全绿；R15 证明齐全、R23 废标与★条款 100% 响应、R34 占位符排除系统变量、R37 偏离表一致 | 对照 PRD §5.8 / §5.8.1，第一批编号规则结构化输出落地，[审查报告](../reviews/2026-10-22-pd-review-BATCH2-M2.md) 书面认可 | **建议 PM 标 done** |
| **APP-M2-T036 / T037 / AI-01** | 大模型服务与 RAGFlow 知识库弹窗配置及连通性闭环 | [交付](2026-10-23-model-ragflow-config-modals.md) / [代码](../code/2026-10-23-model-ragflow-config-modals.md) | 前端 8 项专属单测 + 后端 3 项专属单测全绿；落实用户拍板 Step ③ 弹窗形态，Fernet 加密与 If-Match 乐观锁完备；实测内网 VPN 真实凭据连通无 500 崩溃 | 对照 PRD 独立配置能力要求，弹窗操作与状态感知流畅，无说明书堆砌 | **建议 PM 标 done** |
| **BE-SUBMISSION-FINALIZE-GATE** | 规则最小可递交集与分册定稿闸门端到端闭环 | [交付](2026-10-23-submission-rules-finalize-gate.md) / [代码](../code/2026-10-23-submission-rules-finalize-gate.md) | `pytest tests/backend/test_submission_finalize_gate.py` 等 25 项测试全绿；动态读取分册定稿状态，未定稿抛出 409，定稿合规放行递交版，编写人 403 拦截，项目经理 200 下载带 SHA-256 指纹 | 成功打通正规合法解除 RULES_INCOMPLETE 的闭环，落实用户拍板 Step ④ | **建议 PM 标 done** |

---

## 3. 看板既有历史 in-review 任务（QA 已签署，留待 PM 确认）

| 卡ID | 关联 Issue | QA 签署凭证 / 交付文档 | 状态建议 |
|---|---|---|---|
| **BE-M0-T04** | ISSUE-005 | QA REV-M0-T32 已签署；锁迁移至 `/api/v1`；测试通过 | 建议 PM 确认后标 done |
| **BE-M0-T05** | ISSUE-005 | QA REV-M0-T33 已签署；单章导出检查与快照防篡改；测试通过 | 建议 PM 确认后标 done |
| **BE-M0-T06** | ISSUE-005 | QA REV-M0-T36 已签署（commit `0cb6c38`）；202/SSE 可恢复任务；测试通过 | 建议 PM 确认后标 done |
| **BE-M0-T16** | ISSUE-031 | QA REV-M0-T34 已签署；错误码名字冻结 143 项；测试通过 | 建议 PM 确认后标 done |
| **BE-M0-T18** | ISSUE-033 | QA REV-M0-T35 已签署；证据挂接规则（过期/协议/受限）；测试通过 | 建议 PM 确认后标 done |
| **REV-M0-T25** | ISSUE-036 | QA 已签署（橙色/金色/warning 标签无障碍对比度通过） | 建议 PM 确认后标 done |
| **REV-M0-T26** | ISSUE-033 | QA 已签署（挂证据规则契约复签通过） | 建议 PM 确认后标 done |
| **REV-M0-T27** | ISSUE-034 | QA 已签署（R1～R9 确认缺陷修复与真实 MySQL 验证通过） | 建议 PM 确认后标 done |
| **REV-M0-T28** | BE-M0-T11 | QA 已签署（回执与会话入库通过） | 建议 PM 确认后标 done |

---

## 4. 人类 PM 操作建议

1. **核准并标 done**：人类 PM 审阅上述证据链无异议后，可指示或自行在 `docs/TASK_BOARD.md` 中将上述任务卡由 `in-review` 置为 `done`；
2. **严守纪律承诺**：主 Agent 与各 Subagent 严禁擅自提前标 `done`，当前全量保持 `in-review`。
