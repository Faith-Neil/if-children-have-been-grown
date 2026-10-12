为什么有这个文件：说明前端各部分怎样配合、怎样读取和保存数据。

它解决什么问题：避免模块连接后出现数据不一致或互相覆盖。

# 智能投标系统前端架构说明

<!-- governance-baseline:start -->
| 项目 | 当前值 |
|---|---|
| 治理版本 | g1.1 |
| 更新日期 | 2026-10-11 |
| 关联 Issue | ISSUE-007 |
<!-- governance-baseline:end -->

写作输入由共享组装器从账号公司、当前项目与已确认本章方案构造；仅输入本章矩阵、合格证据、选中可选事实及全部必备事实。候选保存实际输入快照及指纹，快照/候选自身不进入指纹；变量先校验，来源或方案改变需重新确认。source_scope为新增实施字段，不表示逐段溯源已完成。

T14/T15已本地验收：项目成员、分册负责人和本节编写人在同一事务存储中管理，公司操作角色与资源范围共同校验；页面使用后台权限，每次后台操作仍重新判定。逐章方案分别记确认人与依赖摘要，生成只核对本章，项目确认状态由全部章节汇总；检查/输出有本册或全部范围，并绑定项目输入。交接保留正文历史和每人私有草稿，解除旧编辑权；旧接口、原件、任务与下载都遵守项目范围。模型每次调用前后及保存结果前再次核对，撤权不能留下部分候选。

团队、基本信息、逐章方案分别保留页面已读依据。冲突刷新仅更新后台状态，旧填写仍保留并暂停写入；使用者明确查看新旧内容后才载入最新依据。单章操作只更新该行，批量大纲还核对章节清单和顺序。新增可信会话后实际49路径57操作见[契约](architecture/icg-reference-contract.md)；既有成员验证见[成员验收](testing/2026-10-10-project-assignments.md)。后续259卡按同一业务核心扩展，不提前建立无实现微服务。

ISSUE-009 / APP-M2-T001增加[可信会话与导航契约](architecture/application-session-contract.md)：当前账号和资源权限从后台现有会话读取，公司/角色不可由客户端提升。实际页面先会话再读获准数据；新权限立即收紧缓存项目/章节操作，条款权限须新workspace读回；会话序号和同授权对象阻止迟到读取。原8角色矩阵与当前3演示身份兼容模式分列；manager未映射company_admin且无公司管理入口，旧资料细权限仍待迁移。布局、浏览器路由和全页离开保护继续本卡，阶段验证见[记录](testing/2026-10-11-application-session.md)。

ISSUE-008 / T16已本地验收，把相同原则用于现有文字资料及公司SLA模板表单：原公司版本、公司和完整记录内容构成已读依据，后台刷新只更新当前状态；保存传原版本，核对载入时真实重读最新状态。两个集合各自保存对应GET版本，不能混用并行读取的版本；完整集合供核验，搜索只过滤显示。完整ACL、确认审核和附件治理尚未因此实现。

当前实施：`frontend/web`正式页面按ICG示例重建，通过同源接口连接`backend/bid-core`；主链路在同一公司隔离与事务存储下扩展文件、条款、矩阵、事实、证据、计划、任务、检查和两册输出。旧后台验收页作为开发工具。数据库、模型、解析器独立替换；实际字段见[接口约定](architecture/icg-reference-contract.md)。正式产品与旧demo分别验收，生产数据库和部署不因本地页面贯通自动完成。

2026-10-12：ISSUE-011 在既有模型口后增加可显式启用的 OpenAI 兼容对话适配器。项目经理于 10-12 12:10 在 QA 签署后确认，AI-02 为 done，ISSUE-011 为 closed。未打开配置时默认仍是演示替身；调用失败继续返回 502，不改写成演示成功。ISSUE-010 已 closed（user decision, relayed by PM）：业务库为 MySQL 8；对话模型由配置页提供，设计见 [配置驱动的对话模型](architecture/model-config-provider.md)；嵌入与向量库用 RAGFlow 自带能力，设计见 [RAGFlow 检索适配器](architecture/ragflow-retrieval-adapter.md)；生产生成只在内网。两份设计都未实现。内存实现继续用于测试。该适配器不是内网模型已接通。ISSUE-016 的检索口仍只在内存中运行，状态为 in-review。它不进入 `create_app`，不连接 MySQL，也不连接 RAGFlow。重排产品未选定。

2026-10-12（ISSUE-005）：`/api/v1` 错误体和 24 小时幂等回执已提交复查。本轮不引入驱动、迁移或表结构，测试仍用内存仓库。状态表不在本文重复。

## 工程治理结构（ISSUE-003）

服务承诺新增结构化公司模板与项目取值，通过同一Repository保存；事实直接读取项目承诺，取值不在事实表复制。单位比较、风险批准、检查与变量替换在后台执行。模板业务版本与记录版本分开，模板/来源/承诺变化使引用需复核并进入统一输入摘要，阻止旧检查/候选/下载继续用。接口与字段见[服务承诺约定](architecture/icg-reference-contract.md)。

本轮共同保护：工作区、生成候选与旧建议使用统一输入摘要，引用资料改变后旧候选/检查/导出失效；敏感项目两个模型入口共用本地路由门禁。失败解析可能保存任务并增加版本，页面按错误详情刷新。旧草稿或历史正文核对后只保存新个人草稿，提交才更新正式正文。实际新增接口与两代错误字段见[主流程约定](architecture/icg-reference-contract.md)，当前同步任务不假称202排队/SSE恢复已实现。

| 路径 | 职责 |
|---|---|
| [docs/TASK_BOARD.md](TASK_BOARD.md) / [docs/tasks/](tasks/) | 里程碑总览与任务卡，记录依赖、范围、验收 |
| [issues/](../issues/) | 需求、版本、Bug及决策的来源和闭环状态 |
| [docs/governance/WORKFLOW.md](governance/WORKFLOW.md) | Issue → 任务 → 实现 → 验收 → 交付 → 文档同步流程 |
| [docs/templates/](templates/) | 任务、交付、代码解释模板 |
| [docs/delivery/](delivery/) / [docs/code/](code/) | 每任务验收、进度和实际代码解释 |
| [docs/PROJECT_STATUS.md](PROJECT_STATUS.md) | 基于任务事实的项目进度 |
| [docs/DOCUMENT_INDEX.md](DOCUMENT_INDEX.md) | 文档版本、状态、日期和来源登记 |
| [scripts/check-project-governance.cjs](../scripts/check-project-governance.cjs) | 结构一致性检查，无第三方依赖 |

检查程序读取实际维护文档，校验共享治理块、本地链接、已完成任务交付字段、Issue验收证据与索引登记。它不创建业务接口或假设后端存在，不能代替功能验收和架构评审。真实业务代码与模拟原型继续按原架构边界区分。

本次变化的代码解释见 [FE-M0-T02](code/FE-M0-T02.md)，规则依据见 [工作流](governance/WORKFLOW.md)。

全工作区根包含活动项目和 `ICG/` 历史来源；客户合同根、凭据和运行数据不进入远端。`tools/workspace-sync/` 提供自动WIP提交/推送及clean状态的远端快进获取；双方分叉保全，由维护者处理。凭据和运行状态放工作区外。该工程工具不提供生产应用的业务数据同步。

图片目录与渐进代码边界见 [目录方案](architecture/repository-layout.md)；前后端契约及风险见 [技术审查](reviews/2026-10-09-technical-readiness.md)。目录名不等于独立服务已建立，数据库、编辑器和编排选型仍待评审。

## 1. 架构目标

前端架构需要满足：

- 长文编辑稳定
- AI 任务可追踪
- 多角色权限清晰
- 页面间状态一致
- 编辑与检查闭环可追溯
- 私有化部署环境可运行
- 后续可扩展更多行业模板与标书类型

## 2. 前端模块拆分

建议按业务域拆分：

```text
app-shell
dashboard
project
tender-document
response-matrix
project-fact
chapter
editor
assistant
checking
knowledge-base
writing-profile
export
admin
```

其中 `editor` 与 `assistant` 独立模块化。

原因：

- 正文编辑
- 段落定位
- 引用来源
- 问题定位
- AI 选区
- Diff
- 自动保存
- 编辑锁
- 版本管理

这些能力复杂且高频，不宜散落在普通页面组件内。

## 3. 路由结构

建议：

```text
/dashboard

/projects
/projects/:projectId

/projects/:projectId/documents
/projects/:projectId/matrix
/projects/:projectId/facts
/projects/:projectId/chapters
/projects/:projectId/chapters/:chapterId/plan
/projects/:projectId/chapters/:chapterId/progress
/projects/:projectId/editor/:chapterId
/projects/:projectId/check
/projects/:projectId/export
/projects/:projectId/settings

/kb
/kb/company
/kb/people
/kb/qualifications
/kb/cases
/kb/snippets
/kb/history

/writing
/writing/profile
/writing/templates
/writing/samples
/writing/terms
/writing/task-cards

/admin
/admin/users
/admin/roles
/admin/company-settings
/admin/models
/admin/audit
```

## 4. 页面 Shell

### 4.1 全局 Shell

组成：

- 左侧一级导航
- 顶部全局搜索
- 项目快速切换
- 消息 / 待办
- 用户菜单

### 4.2 项目 Shell

进入项目后顶部保留：

- 项目名称
- 项目状态
- 投标截止时间
- 项目负责人

二级导航：

- 概览
- 招标文件
- 响应矩阵
- 项目事实
- 章节编写
- 检查
- 导出

## 5. 状态管理

状态应分三层：

### 5.1 服务端业务状态

例如：

- 章节状态
- 分册状态
- 项目状态
- 检查任务状态
- 导出任务状态

服务端为唯一事实源。

### 5.2 页面会话状态

例如：

- 当前选中章节
- 当前筛选
- Drawer 是否打开
- 当前版本对比选择

可保存在前端 store。

### 5.3 编辑器临时状态

例如：

- 未提交草稿
- 当前选区
- 光标位置
- 本地 Undo / Redo 栈

编辑器状态要与后端草稿自动保存解耦。

## 6. 编辑器架构

建议编辑器拆成：

```text
EditorShell
├─ ChapterHeader
├─ DocumentEditor
├─ ParagraphMetaLayer
├─ SourceDrawer
├─ IssueDrawer
├─ AssistantPanel
├─ DiffModal
├─ SaveIndicator
└─ EditLockBanner
```

### 6.1 段落级元数据

正文和段落元数据不要混成纯 HTML。

建议逻辑结构：

```text
paragraph_id
content
source_refs
edit_mode
version_id
issue_refs
lock_state
```

这样才能稳定支持：

- 来源追踪
- 段落问题
- 增量复查
- AI 局部修改
- 版本对比

## 7. AI 助手交互架构

### 7.1 问答模式

输入：

- 当前项目
- 当前章节
- 对话历史
- 可选知识库上下文

输出：

- 文本回答
- 来源引用

不写正文。

### 7.2 修改模式

输入：

- 选区原文
- 前后文
- 用户指令
- 招标条款
- 项目事实
- 知识库检索结果
- 写作档案
- 对话历史

输出：

- 3～5 个修改建议
- 每个建议的来源
- 每个建议的修改类型

用户确认后才写入正文。

## 8. 任务状态模型

长任务统一：

```text
queued
running
succeeded
failed
```

适用于：

- 文件解析
- 章节生成
- 合规检查
- 全文检查
- Word 导出

前端要允许用户离开页面后继续任务，重新进入时从服务端恢复状态。

## 9. 编辑锁

采用章节级独占编辑锁。

前端状态：

```text
editable
readonly_locked_by_other
lock_expired
taking_over
```

需要：

- 心跳
- 超时
- 强制接管
- 接管原因
- 锁失效后的草稿保护

## 10. 自动保存

建议：

- 编辑后延迟自动保存
- 页面离开前强制刷新草稿
- 保存失败有明确状态
- 网络恢复后可重试
- 不使用频繁 Toast

自动保存的是“草稿”，正式提交才创建章节版本。

## 11. 版本机制

每次正式写入创建新版本。

来源：

- chapter_generate
- manual_edit
- assistant_edit
- rollback

回退不覆盖历史版本，而是生成新版本。

## 12. 权限

前端权限分两层：

### 12.1 路由权限

控制用户能否进入：

- 系统管理
- 企业资料库
- 模型配置等

### 12.2 操作权限

即使能进入页面，也要控制：

- 编辑
- 定稿
- 解锁
- 强制接管
- 导出
- 查看敏感资料

前端只负责展示与交互控制，最终权限必须由服务端再次验证。

## 13. 搜索架构

全局搜索至少支持：

- 项目
- 章节
- 招标条款
- 评分项
- 人员
- 项目案例
- 资质
- 方案片段

结果按类型分组展示。

## 14. 错误处理

统一优先级：

```text
系统错误
  ↓
权限限制
  ↓
编辑锁
  ↓
业务阻断
  ↓
普通警告
  ↓
正常状态
```

错误展示建议分：

- 页面级 Error State
- 区域级 Error State
- Inline Error
- Toast

避免所有问题都使用 Toast。

## 15. 组件体系

### 通用组件

- Table
- Tree
- Tabs
- Drawer
- Modal
- Tooltip
- Timeline
- EmptyState
- ErrorState
- LoadingState

### 业务组件

- ProjectRiskCard
- ChapterTree
- GenerationTimeline
- AIEditor
- SourceCard
- IssuePanel
- VersionCompare
- CitationTrace
- EditLockBanner
- SaveIndicator
- ResponseCoverage
- FactConflictCard

## 16. 响应式策略

一期以桌面 Web 为主。

建议：

- ≥ 1440px：完整三栏编辑台
- 1200～1439px：左侧章节树可折叠
- < 1200px：右侧助手改成 Drawer
- 移动端：只支持查看、审批、待办，不支持完整长文编辑

## 17. 性能重点

优先关注：

- 大章节长文渲染
- 大型响应矩阵
- 章节树
- Diff
- 大量检查问题
- 长对话历史

建议：

- 表格虚拟滚动
- 长文分块渲染
- Drawer 延迟加载
- Diff 按需计算
- 对话历史分页
- 来源详情按需加载

## 18. 审计与可追溯

所有关键交互应携带：

- operator_id
- project_id
- chapter_id
- version_id
- operation_type
- timestamp

包括：

- 章节编辑
- AI 建议采纳
- 回退
- 强制接管
- 分册解锁
- 导出
- 查看敏感资料

## 19. 建议目录结构

```text
src/
├─ app/
├─ components/
├─ features/
│  ├─ dashboard/
│  ├─ project/
│  ├─ tender-document/
│  ├─ response-matrix/
│  ├─ project-fact/
│  ├─ chapter/
│  ├─ editor/
│  ├─ assistant/
│  ├─ checking/
│  ├─ knowledge-base/
│  ├─ writing-profile/
│  ├─ export/
│  └─ admin/
├─ hooks/
├─ services/
├─ stores/
├─ types/
└─ utils/
```

## 20. 架构原则总结

1. 业务状态以服务端为准。
2. 编辑器独立模块化。
3. AI 不静默修改正文。
4. 草稿与正式版本分离。
5. 长任务可离开页面继续。
6. 所有重要修改可追溯。
7. 错误、权限、锁、业务状态按优先级展示。

写作收尾增加原子来源校验：Draft/Version请求携带input_fingerprint，草稿响应保存原基准；来源项目写事务同时核对来源摘要、租约和章revision。页面候选采纳/草稿恢复保留原基准，明确人工复核后才绑定新值。通用事实解析识别完整数字+已知单位，错误/重复后缀在模型结果、检查和输出共同阻断。

## 最新分支复核修复（2026-10-12）

ISSUE-032 / REV-M0-T20只修已承诺约束的实际缺陷：失败与成功响应同样核对来源身份，令牌只留私有映射；离开判断以真正显示的页为准；冻结的密钥故障503不自动重试。同进程片段修改与回执使用同一串行事务，失败回滚独立记录/审计；数据库读取不裁剪有效回执，旧清理按原时间/指纹比较后删除。没有新接口或服务，冻结大纲/任务和模型/数据库范围不变。真实MySQL仍需对应环境验证；[复核记录](reviews/2026-10-12-foundation-review.md)。
