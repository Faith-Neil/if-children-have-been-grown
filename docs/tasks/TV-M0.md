为什么有这个文件：把已确认的技术分册路径拆成可以单独验收的任务。

它解决什么问题：避免一次改完目录、矩阵、正文和偏离表，中间没有可核对的步骤。

# TV-M0：技术分册 MVP

日期：2026-11-03；修订：2026-11-05 下午最短路径。关联 [ISSUE-047](../../issues/ISSUE-047.md)、[技术分册 MVP](../decisions/2026-11-03-technical-volume-mvp.md)、[最短主路径](../decisions/2026-11-05-technical-volume-shortest-path.md)。

已有两册项目不迁移。这些卡都不标 done，完成实现后最多到 in-review。T05～T07 的「单章六段 / 矩阵确认」口径以 2026-11-05 决定为准作废，由工单 1～7 修订验收，不另开两册主路径。

集成分支是 `feat/iss-047-technical-volume-mvp`。产品提交只在这条分支。不合并进 main。PR #8 草稿禁止合并。

<a id="tv-m0-t00"></a>

## TV-M0-T00 · RAGFlow 招标解析打通（工单 0）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | 公司 RAGFlow 已连接；知识库已配内网嵌入 |
| PRD / 架构出处 | [最短主路径](../decisions/2026-11-05-technical-volume-shortest-path.md) 工单 0；B5/B6 不出外网 |
| 完成时交付 | docs/delivery/TV-M0-T00.md |
| 代码解释 | docs/code/TV-M0-T00.md |

范围：上传招标文件后 RAGFlow/DeepDOC 解析必须可成功；失败可见（含外网嵌入提示）、可重试、禁止静默假成功。招标临时数据集强制使用公司配置的内网嵌入；嵌入不一致删除重建。验证双库名可配置检索不在本卡（工单 4）。

可验证验收：

- [x] 关演示 + 真 MySQL：真实 `.doc` 样例解析成功并进入可抽取状态（本轮 16 页 / 61 条款）。
- [x] 外网嵌入失败文案可识别；假服务单测覆盖重建与提示。
- [ ] 产品进程已加载新代码后的二次回归（需重启 `Start-Product.ps1`）。

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

<a id="tv-m0-t08"></a>

## TV-M0-T08 · 管道去闸门（工单 1）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 3 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T00](TV-M0.md#tv-m0-t00) |
| PRD / 架构出处 | [最短主路径](../decisions/2026-11-05-technical-volume-shortest-path.md) 工单 1 |
| 完成时交付 | docs/delivery/TV-M0-T08.md |
| 代码解释 | docs/code/TV-M0-T08.md |

范围：技术分册上传完成后自动解析→抽取→拟目录→内部矩阵填充；去掉用户「抽取技术条款」主路径闸门与「确认解析结果并进入矩阵」主闸门。抽出为空停说明页；解析失败可见可重试。目录确认与矩阵后台化不在本卡（工单 2/3）。

可验证验收：

- [x] 技术分册解析成功后 `parse_confirmed=true`；抽出为空则为 `false` 且无目录。
- [x] 前端上传后按条件自动启动解析；成功有目录则进编辑台；「重新解析」为次要入口。
- [x] 解析结果页不再以「进入矩阵」为主按钮。
- [ ] QA/PD 签署后由人类 PM 标 done。

<a id="tv-m0-t09"></a>

## TV-M0-T09 · 动态目录唯一确认（工单 2）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T08](TV-M0.md#tv-m0-t08) |
| PRD / 架构出处 | [最短主路径](../decisions/2026-11-05-technical-volume-shortest-path.md) 工单 2；§6 动态 1～4 级 |
| 完成时交付 | docs/delivery/TV-M0-T09.md |
| 代码解释 | docs/code/TV-M0-T09.md |

范围：目录按规范编号树 + 评分主观分叶子动态拟 1～4 级；**【删】教程六块/单章硬编码与六段正文硬模板**。编辑台「确认目录」为生成唯一强制闸门；矩阵确认不挡生成。覆盖视图/双库/写作助手不在本卡。

可验证验收：

- [x] `arrange` 产出「技术规范响应 / 评分主观分响应」动态结构，不再出现写死的「服务方式→…→质保」空块。
- [x] 目录级别 API/UI 支持 1～4；确认后按钮为「开始生成」；无 historyBlocked 矩阵闸门。
- [x] `assert_ready` 只要求目录已确认；`writable` 不要求矩阵 status=confirmed。
- [ ] QA/PD 签署后由人类 PM 标 done。

<a id="tv-m0-t10"></a>

## TV-M0-T10 · 矩阵后台化 + 覆盖视图（工单 3）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 3 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T09](TV-M0.md#tv-m0-t09) |
| PRD / 架构出处 | [最短主路径](../decisions/2026-11-05-technical-volume-shortest-path.md) 工单 3 |
| 完成时交付 | docs/delivery/TV-M0-T10.md |
| 代码解释 | docs/code/TV-M0-T10.md |

范围：矩阵 API 保留；技术分册前端改为「覆盖视图」（映射/偏离/缺口），去掉「确认历史做法」主路径；页签改称覆盖视图；分析页不再叠解析确认。事后可改偏离说明。双库写作与一键全文不在本卡。

可验证验收：

- [x] `coverageSummary` 单测覆盖映射/缺口/偏离统计。
- [x] 技术分册页签「覆盖视图」；无整表确认按钮；提示不挡生成。
- [ ] QA/PD 签署后由人类 PM 标 done。

<a id="tv-m0-t11"></a>

## TV-M0-T11 · 双库 RAG + 审计（工单 4）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T10](TV-M0.md#tv-m0-t10) |
| PRD / 架构出处 | [最短主路径](../decisions/2026-11-05-technical-volume-shortest-path.md) 工单 4；§9 双库 |
| 完成时交付 | docs/delivery/TV-M0-T11.md |
| 代码解释 | docs/code/TV-M0-T11.md |

范围：现网名 `公司名::icg-history` + `公司名::icg-material`（单数，可配置）；节生成强制双库检索与审计；缺库编辑台显性提示。质量八条/写作助手不在本卡。

可验证验收：

- [x] 默认后缀 `icg-material`；可配置；旧 `icg-materials` 仅作查找别名。
- [x] 生成路径写入 `technical_rag_audit`；缺库 `technical_kb.missing` 提示。
- [ ] QA/PD 签署后由人类 PM 标 done。

<a id="tv-m0-t12"></a>

## TV-M0-T12 · 一键全文 + 质量八条（工单 5）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T11](TV-M0.md#tv-m0-t11) |
| PRD / 架构出处 | [最短主路径](../decisions/2026-11-05-technical-volume-shortest-path.md) 工单 5；§10.6 质量八条 |
| 完成时交付 | docs/delivery/TV-M0-T12.md |
| 代码解释 | docs/code/TV-M0-T12.md |

范围：按确认目录顺序一键全文；生成后八条规则抽检；未达标标「需核对」可见警告；允许导出、不恢复矩阵闸门。编辑台 Figma / 写作助手不在本卡。

可验证验收：

- [x] `evaluate_quality` 覆盖薄弱得分点、商务灌水等；节末可标「需要核对」。
- [x] 工作区 / 编辑台 / 导出页暴露 `technical_quality.warning`。
- [ ] QA/PD 签署后由人类 PM 标 done。

<a id="tv-m0-t13"></a>

## TV-M0-T13 · 编辑台 UI 精简（工单 6）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T12](TV-M0.md#tv-m0-t12) |
| PRD / 架构出处 | [最短主路径](../decisions/2026-11-05-technical-volume-shortest-path.md) 工单 6；§11 编辑台 UI |
| 完成时交付 | docs/delivery/TV-M0-T13.md |
| 代码解释 | docs/code/TV-M0-T13.md |

范围：三栏保留；主路径确认目录/开始生成/导出；工具栏白名单；目录搜索与节状态；去事实条与重锁挡板。写作助手双模式见 T14。

可验证验收：

- [x] 技术分册主路径条与白名单工具栏；事实条/生成候选不在主条。
- [x] 目录搜索与节状态 Tag。
- [ ] QA/PD 签署后由人类 PM 标 done。

<a id="tv-m0-t14"></a>

## TV-M0-T14 · 写作助手双模式（工单 7）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 3 小时 |
| 关联 Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 依赖 | [TV-M0-T13](TV-M0.md#tv-m0-t13) |
| PRD / 架构出处 | [最短主路径](../decisions/2026-11-05-technical-volume-shortest-path.md) 工单 7；§11.4 |
| 完成时交付 | docs/delivery/TV-M0-T14.md |
| 代码解释 | docs/code/TV-M0-T14.md |

范围：初稿后启用；问答写作不改文档；标书修改经预览写入；情境芯片。

可验证验收：

- [x] 双模式切换与芯片；无初稿/生成中禁用提示。
- [x] 问答不直接写正文；标书修改走候选预览。
- [ ] QA/PD 签署后由人类 PM 标 done。

<a id="tv-m0-t15"></a>

## TV-M0-T15 · Requirement/ResponseTask 两层 + 实质生成（ISSUE-051）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-051](../../issues/ISSUE-051.md) |
| 依赖 | [TV-M0-T12](TV-M0.md#tv-m0-t12) |
| 完成时交付 | docs/delivery/TV-M0-T15.md |
| 代码解释 | docs/code/TV-M0-T15.md |

范围：主题目录短标题；ResponseTask 多对多；计划校验；生成按任务+要求+RAG；缺依据标待确认。

<a id="tv-m0-t16"></a>

## TV-M0-T16 · 覆盖视图五列 + 去事实冲突 + 壳层紧凑

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-051](../../issues/ISSUE-051.md) |
| 依赖 | [TV-M0-T15](TV-M0.md#tv-m0-t15) |
| 完成时交付 | docs/delivery/TV-M0-T16.md |
| 代码解释 | docs/code/TV-M0-T16.md |

范围：技术分册分析页仅覆盖视图五列；去掉项目事实/取值冲突主路径；顶栏侧栏紧凑。
