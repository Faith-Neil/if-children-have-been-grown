为什么有这个文件：集中跟踪第一期范围和前后端约定中尚未解决的关键问题。

它解决什么问题：避免不同模块按不同口径开发，最终无法连成可用的投标流程。

# ISSUE-005：冻结业务范围与前后端契约门禁

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-005 |
| 类型 | decision |
| 优先级 | P0 |
| 状态 | in-progress |
| 登记 / 更新日期 | 2026-10-09 / 2026-10-12 |
| revision | progress-6 |
| 来源 | ISSUE-004 / REV-M0-T01的业务与技术审查；DG-05卡片已获批准 |
| 关联Task | FE-M0-T03 / FE-M0-T04；BE-M0-T02～T07；APP-M2-T002为 in-review |
| 本地验收 | DG-05卡片(a)(b)已由项目经理于 10-12 12:28 在 QA 签署后确认。T04 与 T05 为 in-review，T06～T07 仍 ready，本 Issue 保持 in-progress，不关闭 |
| 合入 / 发布 | 本轮直接提交在`codex/repository-foundation`；PR #3未合入 / 未发布 |

## 具体待决事项与关闭证据

| 编号 | 决定 | 主要依据 | 关闭证据 |
|---|---|---|---|
| DG-01 | 一期技术/商务/资格范围、首稿生成单位、Word后人工交付边界 | 业务BR-02/11；BG-02/03 | 共同确认的试点范围、角色、输入/产物及系统外动作表 |
| DG-02 | 原文独立标注与漏抽验收；关键引用缺失的确认门禁 | 业务BR-03/04 | 含补遗/扫描/跨附件要求的样本和分级门禁验收 |
| DG-03 | SLA三列、敏感字段场景矩阵、知识库关闭与项目直查 | 业务BR-05/08/09；技术TR-05 | 前端场景、服务端权限/路由及显示/承诺验收表 |
| DG-04 | 事实/证据/附件/规则/模板的依赖指纹、检查/导出失效；放行继承 | 业务BR-06/07；技术TR-06 | 定稿后分别修改依赖，旧检查/输出不能被当成当前有效结果 |
| DG-05 | API字段/状态、租约/接管、草稿/选区/幂等和后台任务恢复 | 技术TR-01～04；2026-10-12已批准提案 | 错误体与24小时幂等已有[验证](../docs/testing/2026-10-12-error-idempotency.md)；租约迁移与导出快照为 in-review，202/SSE、operationId仍 ready |
| DG-06 | 单业务核心/worker/适配器与部署、默认资产和试点样本 | 业务BR-12；技术目录对照 | 技术决策、可运行小切片、版本资产/输入清单及实际启动/恢复证据 |

证据：[业务报告](../docs/reviews/2026-10-09-business-readiness.md)、[技术报告](../docs/reviews/2026-10-09-technical-readiness.md)、[基线差异](../docs/decisions/baseline-gaps.md)、[FE-M0任务](../docs/tasks/FE-M0.md)。P0表示相关生产实现/业务验收前必须解决，不意味着立即扩张全部可选功能。

## 依赖与影响

2026-10-10：FE-M0-T03进入评审准备，形成 [一期交付建议](../docs/decisions/phase-one-scope.md)，用户确认技术、商务两册。其他生产边界仍待决定；本地后端demo按 [ISSUE-006](ISSUE-006.md) 独立实施，模型和数据库先用可替换演示实现，不以demo验收代替本Issue全部门禁。

2026-10-12：对话模型、嵌入、重排、向量库、业务库和内网验证方式另记 [ISSUE-010](ISSUE-010.md)。同日用户决定业务库为 MySQL 8，对话模型由配置页提供，嵌入与向量库用 RAGFlow 自带能力，生产生成只在内网（user decision, relayed by PM）。ISSUE-010 已 closed。适配器未实现。本聚合门禁不因此关闭。

需要产品负责人、前后端责任方共同确认；技术方案v1.4.2/有效设计版本未取得，或需留下经评审替代依据。当前不擅自选择MySQL/其他关系库、React/Vue、LangGraph/Dify或集群部署。

PRD、ROADMAP、ARCHITECTURE将按每项最终决定同步业务正文及版本。本次仅新增发现/门禁和关联入口，没有把建议标为已采纳。Task/Issue/PROJECT_STATUS/DOCUMENT_INDEX登记未决状态；旧BG项及FE-M0-T03/04继续待评审/blocked，不因审查文档完成而关闭。

后续每项可拆独立变更Issue，回链本聚合门禁；验收完成需逐项给出实际决定、实施契约、测试、交付与状态，保留原来源和历史。

## 2026-10-12：DG-05拆卡

已批准提案把DG-05拆成六张不超过4小时的卡，先写契约再改代码。本轮没有新增 Issue。ISSUE-011 的兼容适配器保持原样；`MODEL_UNAVAILABLE` 继续是 502。`/api/v1` 使用统一错误体，旧 `/api` 章节建议仍用原来的 `error` 体，以便已有适配器测试不用改口。

2026-10-12 项目经理决定业务库为 MySQL 8。这取代上文“当前不擅自选择MySQL”和“业务库仍等待决定”里关于业务库的那一句；向量库、嵌入、重排和内网端点仍未决定。本轮不加入驱动、迁移或表结构，测试继续使用内存仓库。同日并行提交已把该决定写入 ISSUE-010；本轮不再改那个文件，也不加入数据库代码。

| 卡片 | 任务 | 状态 | 本轮 |
|---|---|---|---|
| (a) 错误体与状态码表 | [BE-M0-T02](../docs/tasks/BE-M0.md#be-m0-t02) | done | 项目经理于 10-12 12:28 在 QA 签署后确认 |
| (b) 幂等，回执24小时 | [BE-M0-T03](../docs/tasks/BE-M0.md#be-m0-t03) | done | 项目经理于 10-12 12:28 在 QA 签署后确认 |
| (c) 编辑租约迁到 /api/v1 | [BE-M0-T04](../docs/tasks/BE-M0.md#be-m0-t04) | in-review | 已提交复查，不标 done |
| (d) 导出快照 | [BE-M0-T05](../docs/tasks/BE-M0.md#be-m0-t05) | in-review | 已提交复查，不标 done |
| (e) 可恢复任务 202+SSE | [BE-M0-T06](../docs/tasks/BE-M0.md#be-m0-t06) | ready | 未开工 |
| (f) operationId检查 | [BE-M0-T07](../docs/tasks/BE-M0.md#be-m0-t07) | ready | 未开工 |

`VOLUME_OWNER_REQUIRED`固定403，`TWO_VOLUMES_REQUIRED`固定422，`MODEL_UNAVAILABLE`固定502。幂等范围是scope、账号和键；失败不保存；内存最多2048条。旧章节提交仍接受正文字段。前端请求层 APP-M2-T002 已按冻结契约提交 in-review，挂在 ISSUE-009；请求头与正文 `idempotency_key` 使用同一把键。DG-01～DG-04、DG-06以及DG-05的后四张卡未关闭。其中租约迁移与导出快照为 in-review，其余两张仍 ready。本Issue保持 in-progress，不标 closed。同步表见[ISSUE-005本轮同步](../docs/governance/ISSUE-005-sync.md)。

## 2026-10-12：基线正文

接口细节写在[主流程约定](../docs/architecture/icg-reference-contract.md)和 OpenAPI。该约定已补登到同步表。基线改动逐项记在同步表；PRD 与 ROADMAP 本轮未改。ARCHITECTURE 只补 ISSUE-005 一句。
