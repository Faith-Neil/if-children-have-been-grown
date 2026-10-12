为什么有这个文件：集中查看需求变化、版本更新、问题修复和待定事项。

它解决什么问题：避免重复处理同一问题，或遗漏修改后的验收和后续状态。

# Issue 看板

<!-- governance-baseline:start -->
| 项目 | 内容 |
|---|---|
| 治理版本 | g1.1 |
| 更新日期 | 2026-10-11 |
| 关联 Issue | ISSUE-007 |
<!-- governance-baseline:end -->

管理规则见 [Issue 说明](README.md) 与 [协作工作流](../docs/governance/WORKFLOW.md)。每次需求变更、版本更新或 Bug 必须先登记 Issue；详情使用 [模板](template.md)。任务与进度见 [任务看板](../docs/TASK_BOARD.md)。

<!-- issue-board:start -->
| 编号 | 类型 | 优先级 | 状态 | 验收证据 | 合入状态 | 发布状态 | 事项 | 下一步 |
|---|---|---|---|---|---|---|---|---|
| [ISSUE-001](ISSUE-001.md) | decision | P1 | blocked | 本地整合未验收；[分支评审](../docs/reviews/pr-1-integration.md) | PR #1 未合入 | 未发布 | xqr 系统选型与治理记录待整合 | 等待文档分层、基线材料与技术决策核对，不覆盖 main 前端文档 |
| [ISSUE-002](ISSUE-002.md) | bug | P1 | closed | [6 项回归通过](../docs/testing/2026-10-09-repository-foundation.md) | PR #3 待合入 | 未发布 | 原型编辑锁未阻止 AI Diff 确认写入 | FE-M0-T01 本地验收完成；浏览器、合入与发布分别记录 |
| [ISSUE-003](ISSUE-003.md) | workflow | P1 | closed | 四项验收及独立复核通过；[交付记录](../docs/delivery/FE-M0-T02.md) | PR #3 本轮变更待合入 | 未发布 | Issue 前置、六份基线同步与任务交付治理 | 合入后记录实际提交；后续按新规则逐任务推进 |
| [ISSUE-004](ISSUE-004.md) | workflow | P1 | closed | [双向同步与审查验收](../docs/testing/2026-10-09-workspace-sync.md) | PR #3 待合入 | 未发布 | 全工作区同步、目录/业务/技术审查与brief | 持续运行；按ISSUE-005推进基线与契约决定 |
| [ISSUE-005](ISSUE-005.md) | decision | P0 | in-progress | 两册范围已确认；T02/T03已由项目经理确认，见[验证](../docs/testing/2026-10-12-error-idempotency.md)与[QA签署](../docs/testing/2026-10-12-be-m0-t02-t03-signoff.md) | 本轮提交在codex/repository-foundation；PR #3未合入 | 未发布 | T02与T03已done；T04～T07仍待做。业务库决定为MySQL 8但未接入 | 保持 in-progress，不关闭。向量库仍未决定 |
| [ISSUE-006](ISSUE-006.md) | change | P1 | closed | [后台、记录、HTTP与页面验收](../docs/testing/2026-10-10-backend-demo.md) | PR #3 待合入 | 未发布 | 后端开发准备与本地demo | 本地验收完成；继续生产身份、持久数据库与完整业务规则 |
| [ISSUE-007](ISSUE-007.md) | change | P0 | in-progress | T07范围及T09～15限定任务本地验收；[成员记录](../docs/testing/2026-10-10-project-assignments.md) | PR #3 待合入 | 未发布 | 保留ICG布局与流程，逐页接通后台 | T001与ISSUE-009为 in-review，T002请求层为 in-review，T008离线CI为 done、ISSUE-012 已 closed，T124 因依赖未满足为 blocked（ISSUE-022），其余255卡planned；完整资料、片段/段落、规则、生成闭环及正式Word继续 |
| [ISSUE-008](ISSUE-008.md) | bug | P0 | closed | 后台229、前端58及实际资料/模板页面通过；[验证](../docs/testing/2026-10-11-library-basis.md) | PR #3 待合入 | 未发布 | 资料库旧表单刷新版本后覆盖新内容 | T16限定保护本地done；完整资料/模板继续ISSUE-007 |
| [ISSUE-009](ISSUE-009.md) | change | P0 | in-review | T001布局修复与 T002 请求层均已提交；[请求层](../docs/testing/2026-10-12-request-layer.md) | PR #3 待合入 | 未发布 | 共同页面底座与完整资料库前置 | T001 与 T002 等待项目经理 QA 签收后才能 done |
| [ISSUE-010](ISSUE-010.md) | decision | P0 | blocked | 业务库已决定为 MySQL 8；其余项未决定；[待决记录](../docs/delivery/AI-01.md) | 未创建 PR，未合入 | 未发布 | 向量库、对话模型、嵌入、重排和内网验证仍待用户决定 | 2026-10-12 user decision, relayed by PM；pgvector 不再作为同库选项；Issue 不关闭 |
| [ISSUE-011](ISSUE-011.md) | change | P1 | closed | [契约与后台回归](../docs/testing/2026-10-12-openai-compatible-model.md) | 未创建 PR，未合入 | 未发布 | OpenAI 兼容对话适配器，默认仍为演示替身 | 项目经理于 10-12 12:10 在 QA 签署后确认。未合入、未发布。真实端点仍随 ISSUE-010 |
| [ISSUE-012](ISSUE-012.md) | workflow | P1 | closed | 三作业通过；[验证](../docs/testing/2026-10-12-offline-ci.md)；QA签署见 [记录](../docs/testing/2026-10-12-qa-signoff.md) | PR #3 待合入 | 未发布 | 离线检查纳入 GitHub Actions | 项目经理于 10-12 12:10 在 QA 签署后确认。未合入，未发布。`buildTheme` 未实现 |
| [ISSUE-013](ISSUE-013.md) | change | P1 | in-review | 会话实时HTTP15/15、后台262、前端72复跑通过；T008/AI-02签署[记录](../docs/testing/2026-10-12-qa-signoff.md)；[复跑](../docs/testing/2026-10-12-qa-rerun.md)；T001签署不通过[记录](../docs/testing/2026-10-12-e2e-t001-signoff.md) | PR #3 待合入 | 未发布 | 会话真实HTTP复核入库与QA复跑记录 | REV-M0-T02本地done；CI显式运行会话脚本，固定Node 24 |
| [ISSUE-014](ISSUE-014.md) | version | P1 | in-review | 引入前后构建体积已记录；[记录](../docs/testing/2026-10-12-prolayout-routes.md) | PR #3 待合入 | 未发布 | 批准引入 @ant-design/pro-layout，记录打包体积 | 等待项目经理 QA 签收；不得另加依赖 |
| [ISSUE-015](ISSUE-015.md) | change | P1 | in-progress | 计划评审通过；smoke_t06 12/12、Word渲染留证；[记录](../docs/testing/2026-10-12-t06-smoke-word-render.md) | PR #3 待合入 | 未发布 | APP-M1-T06端到端验收计划与缺口执行 | 后端处理W1～W4；继续缺口2、4～7 |
| [ISSUE-016](ISSUE-016.md) | change | P1 | in-review | [契约与后台回归](../docs/testing/2026-10-12-evidence-candidates.md) | 未创建 PR，未合入 | 未发布 | 检索口与三条证据候选，仅内存实现 | 开发者已提交复核；不标 closed。不连接 MySQL，向量库仍随 ISSUE-010 |
| [ISSUE-017](ISSUE-017.md) | decision | P1 | in-review | [草案核对](../docs/testing/2026-10-12-intranet-deploy-plan.md) | 未创建 PR，未合入 | 未发布 | 内网部署草案；MySQL 8，并补 RAGFlow 内网放置与连通 | 等待项目经理标 done。不改 ISSUE-010 正文。重排仍未选定 |
| [ISSUE-018](ISSUE-018.md) | decision | P1 | in-progress | [方案](../docs/architecture/mysql-8-persistence-plan.md)；[连接交付](../docs/delivery/BE-M0-T10.md) | 未创建 PR，未合入 | 未发布 | MySQL 8 持久化。连接和空迁移已提交复查，回执会话租约和聚合表未做 | 保持 in-progress。T11～T13 仍 planned。不标 closed |
| [ISSUE-019](ISSUE-019.md) | version | P1 | in-review | E2E 11项按预期（7通过、4已知缺陷）；[记录](../docs/testing/2026-10-12-e2e-t001-signoff.md) | PR #3 待合入 | 未发布 | Playwright浏览器端到端检查（仅测试依赖） | 项目经理确认；DevOps接入CI |
| [ISSUE-020](ISSUE-020.md) | change | P1 | in-review | 首屏主块 315.94 kB，低于 1334.42 kB；[记录](../docs/testing/2026-10-12-route-chunks.md) | PR #3 待合入 | 未发布 | 路由级懒加载，记录全部分包体积 | 等待项目经理 QA 签收；未改后台 |
| [ISSUE-021](ISSUE-021.md) | change | P2 | blocked | 未执行；E2E-D5 见[签署记录](../docs/testing/2026-10-12-e2e-t001-signoff.md) | 未创建 PR，未合入 | 未发布 | 旧 /api 统一错误体与幂等；`/api` 前缀大小写不敏感。任务 planned | 排在 ISSUE-018 之后。本轮不实施 |
| [ISSUE-022](ISSUE-022.md) | change | P1 | in-review | 复核意见已写入草案，运行时未实现；[记录](../docs/testing/2026-10-12-t124-dependencies.md) | 未创建 PR，未合入 | 未发布 | 大纲契约为 draft, pending backend review。T124 仍 blocked | 等再次复核草案，并等 T078 与 T114。不标 closed |
| [ISSUE-023](ISSUE-023.md) | version | P1 | in-review | [连接与迁移](../docs/testing/2026-10-12-mysql-connection.md) | 未创建 PR，未合入 | 未发布 | 批准引入 SQLAlchemy 2.0、PyMySQL 1.1、cryptography、Alembic 1.14 | 等待项目经理 QA 签收。不标 closed |
| [ISSUE-025](ISSUE-025.md) | workflow | P1 | in-review | [MySQL CI 核对](../docs/testing/2026-10-12-backend-mysql-ci.md) | 未创建 PR，未合入 | 未发布 | 托管 backend-mysql 作业；运行时密码；不建业务表 | 等待项目经理标 done。ISSUE-024 不建档。ISSUE-018 仍 in-progress |
| [ISSUE-026](ISSUE-026.md) | change | P1 | in-review | 三份基线与看板同为 362 项；[核对](../docs/testing/2026-10-12-issue-026-counts.md) | 本轮提交在codex/repository-foundation；PR #3未合入 | 未发布 | PRD、ROADMAP、PROJECT_BRIEF 的任务计数对齐看板 | 等待项目经理签收。不标 closed。不改请求层重试 |
<!-- issue-board:end -->

ISSUE-001 编号沿用合作分支。其原记录在 xqr 内标为 closed，仅表示该分支当时的文档同步验收；本地整合保持 blocked，不据此采纳或发布技术决策。ISSUE-002 的 closed 仅表示本地验收完成。ISSUE-005 保持 in-progress：T02 与 T03 已由项目经理于 10-12 12:28 在 QA 签署后确认，T04～T07 未完成，不关闭。ISSUE-009、ISSUE-014、ISSUE-016、ISSUE-017、ISSUE-019、ISSUE-020、ISSUE-022、ISSUE-023、ISSUE-025 与 ISSUE-026 均为 in-review：QA 可以签署，done 由项目经理设置。ISSUE-018 为 in-progress，因为连接卡之后仍有 planned 卡片。ISSUE-021 为 blocked，其任务 BE-M0-T09 为 planned，并包含 E2E-D5。ISSUE-022 只复核大纲契约草案，T124 任务仍 blocked。开发者不把任务标 done，也不把 Issue 标 closed。ISSUE-011 与 ISSUE-012 均已由项目经理于 10-12 12:10 在 QA 签署后确认并 closed。

ISSUE-010 至 ISSUE-023 均已占用。ISSUE-024 留给后台，本轮不建档。ISSUE-025 是托管 MySQL CI 作业且为 in-review。ISSUE-026 是计数对齐且为 in-review。ISSUE-010 的业务库已决定为 MySQL 8，向量库和模型仍待决，整体仍 blocked。ISSUE-011 已 closed：项目经理于 10-12 12:10 在 QA 签署后确认。ISSUE-012 用于离线 CI 且已 closed，ISSUE-013 用于 QA 复跑以及 T008/AI-02 的签署记录且当前为 in-review，ISSUE-014 是 `@ant-design/pro-layout` 依赖且为 in-review，ISSUE-015 用于 T06 验收计划与贯通冒烟，ISSUE-016 用于内存检索口且为 in-review，ISSUE-017 为内网部署草案且为 in-review，ISSUE-018 用于 MySQL 8 持久化且为 in-progress，ISSUE-019 用于浏览器端到端检查且为 in-review，ISSUE-020 用于路由分包且为 in-review，ISSUE-021 用于旧接口错误体、幂等和 `/api` 前缀大小写且为 blocked，ISSUE-022 为 in-review，只复核大纲契约草案；T124 任务仍 blocked。ISSUE-023 登记已批准的四个数据库依赖且为 in-review。登记新号前先搜索 `issues/` 目录。只更新此表不能代替详情、任务或验收记录。
