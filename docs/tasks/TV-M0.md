为什么有这个文件：把已确认的技术分册路径拆成可以单独验收的任务。

它解决什么问题：避免一次改完目录、矩阵、正文和偏离表，中间没有可核对的步骤。

# TV-M0：技术分册 MVP

日期：2026-11-03。关联 [ISSUE-047](../../issues/ISSUE-047.md)、[技术分册 MVP](../decisions/2026-11-03-technical-volume-mvp.md)。

已有两册项目不迁移。这些卡都不标 done，完成实现后最多到 in-review。

集成分支是 `feat/iss-047-technical-volume-mvp`，从 `origin/main` 的 `36b7e41` 加上决定记录 `0b9d1d5` 拉出。产品提交只在这条分支。不合并进 main。PR #7 只曾承载决定记录，不接收这些卡的产品代码。

<a id="tv-m0-t01"></a>

## TV-M0-T01 · 隐藏资料库与写作档案，新建项目固定技术分册

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 2 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | 决定已确认。不依赖后续抽取和生成 |
| PRD / 架构出处 | [技术分册 MVP](../decisions/2026-11-03-technical-volume-mvp.md) 范围、项目文件 |
| 完成时交付 | docs/delivery/TV-M0-T01.md |
| 代码解释 | docs/code/TV-M0-T01.md |

范围：侧栏不再出现企业资料库、写作档案。页面源码和路由保留。新建项目不再选择两册，创建请求固定 `technical_only`。已有 `both` 项目仍按原分册打开。

候选文件：`frontend/web/src/app/App.tsx`、`frontend/web/src/project/CreateProjectModal.tsx`。

当前条件：创建接口仍接受 `both`，本卡不改旧项目数据，也不在接口层禁止两册，避免打乱既有测试和旧项目。

可验证验收：

- [ ] 侧栏有工作台、知识库、管理规则，没有企业资料库、写作档案。
- [ ] 新建项目弹窗没有编写范围选项，创建请求的 `volume_mode` 为 `technical_only`。
- [ ] 已有两册项目的分册判断仍按项目上的 `volume_mode`。

<a id="tv-m0-t02"></a>

## TV-M0-T02 · 知识库只上传历史标书

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T01](TV-M0.md#tv-m0-t01) |
| PRD / 架构出处 | 决定「历史标书」 |
| 完成时交付 | docs/delivery/TV-M0-T02.md |
| 代码解释 | docs/code/TV-M0-T02.md |

范围：知识库页用于上传 doc、docx、pdf 到本公司一份 RAGFlow 数据集，新文件追加。数据集未配置时不能上传。公司管理员配置数据集，项目经理不能改配置。证书、方案片段不作为本页主路径。

<a id="tv-m0-t03"></a>

## TV-M0-T03 · 招标文件与辅助文件

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T01](TV-M0.md#tv-m0-t01) |
| PRD / 架构出处 | 决定「项目文件」 |
| 完成时交付 | docs/delivery/TV-M0-T03.md |
| 代码解释 | docs/code/TV-M0-T03.md |

范围：一个新项目必须有一份招标文件，技术规范书和其他辅助文件可选。格式为 pdf、doc、docx。文件变动后取消目录确认和矩阵确认，已有正文保留并标成需要重新生成。同一批文件不能再次抽取。不做补遗差异对照。

<a id="tv-m0-t04"></a>

## TV-M0-T04 · 按教程抽取技术条款

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T03](TV-M0.md#tv-m0-t03) |
| PRD / 架构出处 | 决定「抽取」；[目录教程](../reference/writing/01-服务方案目录制作教程.md) |
| 完成时交付 | docs/delivery/TV-M0-T04.md |
| 代码解释 | docs/code/TV-M0-T04.md |

范围：点「抽取技术条款」后，主观分按顿号、逗号、分号拆条，规格书按条款树逐条抽取。定义、封面、目录、客观分、资质、报价不抽。同一件事只留一行。一条都没抽到时停在说明页。

<a id="tv-m0-t05"></a>

## TV-M0-T05 · 单章服务方案目录

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T04](TV-M0.md#tv-m0-t04) |
| PRD / 架构出处 | 决定「目录」 |
| 完成时交付 | docs/delivery/TV-M0-T05.md |
| 代码解释 | docs/code/TV-M0-T05.md |

范围：编辑台只有一章「服务方案」或招标规定的同义标题。二级、三级是章内标题。评分要点和需要响应的规格书条款都有标题才能确认。创建时的「技术方案」不作目录。

<a id="tv-m0-t06"></a>

## TV-M0-T06 · 矩阵响应来自历史做法

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T04](TV-M0.md#tv-m0-t04)、[TV-M0-T02](TV-M0.md#tv-m0-t02) |
| PRD / 架构出处 | 决定「矩阵」；[响应教程](../reference/writing/02-技术标响应教程.md) |
| 完成时交付 | docs/delivery/TV-M0-T06.md |
| 代码解释 | docs/code/TV-M0-T06.md |

范围：历史做法由本地模型对照本次招标条款判断正偏离、负偏离或无偏离。只有无偏离可以整表确认。没有命中时逐条确认。检索失败和判断失败不进正文。

<a id="tv-m0-t07"></a>

## TV-M0-T07 · 按节生成正文并导出技术偏离表

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T05](TV-M0.md#tv-m0-t05)、[TV-M0-T06](TV-M0.md#tv-m0-t06) |
| PRD / 架构出处 | 决定「正文」「技术偏离表」「导出」 |
| 完成时交付 | docs/delivery/TV-M0-T07.md |
| 代码解释 | docs/code/TV-M0-T07.md |

范围：点「生成技术分册」后按六段写入同一章，先写服务内容。重新生成只影响一节。导出技术分册内部稿，并按招标样表填技术偏离表。没有样表时不自造。待补和需要核对不阻止内部稿导出。
