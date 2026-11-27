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


## TV-M0-T17 · 三张清单 + 清单拟目录挂要点 + 正文废标约束

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 依赖 | [TV-M0-T16](TV-M0.md#tv-m0-t16) |
| 完成时交付 | docs/delivery/TV-M0-T17.md |
| 代码解释 | docs/code/TV-M0-T17.md |

范围：模型抽取输出三张清单；`tender_digest` 编号 T/S/R；一次模型调用拟 1～4 级目录并挂要点，漏挂补入「其他服务承诺」，失败回落规则目录；正文提示加评分标准与全部废标清单；检索词加挂载要点；两库都检索。

验收：`tests/backend/test_technical_digest.py` 通过；技术相关后端用例无新增失败。


## TV-M0-T18 · 覆盖视图即矩阵：检索摘要、人工确认、单节重试

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 依赖 | [TV-M0-T17](TV-M0.md#tv-m0-t17) |
| 完成时交付 | docs/delivery/TV-M0-T18.md |
| 代码解释 | docs/code/TV-M0-T18.md |

范围：覆盖行带清单编号、评分项与分值、本节检索摘要（两库命中、前 3 条来源、状态与原因）、人工确认原因、失败原因；新增 `POST /api/v1/projects/{project_id}/technical-tasks/{task_id}/confirm`；失败节在覆盖视图单节重试（复用流式接口 `section`）；展示废标清单。

验收：`tests/backend/test_technical_coverage_view.py`、`frontend/web/tests/unit/coverage-live.test.mjs` 通过；项目只读成员确认与重试均 403；OpenAPI `--check` 一致。

<a id="tv-m0-t19"></a>

## TV-M0-T19 · 写作助手按节问答与按节修改

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 依赖 | [TV-M0-T18](TV-M0.md#tv-m0-t18) |
| 完成时交付 | docs/delivery/TV-M0-T19.md |
| 代码解释 | docs/code/TV-M0-T19.md |

范围：技术分册写作助手去掉固定文案，按所选小节工作。问答走现有流式接口，带本节挂载要点、评分标准、废标清单与三库检索；新增 `POST /api/v1/projects/{project_id}/technical-sections/rewrite` 按节生成修改候选（不写入），候选带废标约束预检与来源；写入沿用差异预览、编辑锁与版本校验。快捷指令五条；覆盖视图「目标章节」跳到编辑台并预填小节与修改要求。

验收：`tests/backend/test_technical_assistant.py`、`frontend/web/tests/unit/technical-assistant.test.mjs` 通过；项目只读成员按节修改 403；未接真实模型 502；OpenAPI `--check` 一致。

<a id="tv-m0-t20"></a>

## TV-M0-T20 · 三角色权限收口与项目只读写拒绝核查

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 依赖 | [TV-M0-T19](TV-M0.md#tv-m0-t19) |
| 完成时交付 | docs/delivery/TV-M0-T20.md |
| 代码解释 | docs/code/TV-M0-T20.md |

范围：登录角色只认平台管理员、公司管理员、普通用户；旧角色名（`data_admin`、`group_admin`、`manager`、`viewer`、`auditor` 等）只在归一化入口兼容，业务授权不再按旧原值判断。只读只看项目角色 `readonly`（旧数据 `viewer` 同义），`ensure_not_readonly()` 按项目成员判断。演示账号改为三角色命名。逐个调用 `/api/v1` 项目写接口核查项目只读成员都被后端拒绝。

验收：`tests/backend/test_readonly_member_writes.py` 通过（项目只读成员调用全部项目写接口均 403，解除段落锁 403）；受影响的知识库、SLA、通知、字典、会话、模型配置、问答测试按新角色语义通过；前端 lint 通过、全量失败集合不新增；OpenAPI `--check` 一致。

<a id="tv-m0-t21"></a>

## TV-M0-T21 · 修改候选数字预检与问答按小节分会话

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-053](../../issues/ISSUE-053.md) |
| 依赖 | [TV-M0-T19](TV-M0.md#tv-m0-t19) |
| 完成时交付 | docs/delivery/TV-M0-T21.md |
| 代码解释 | docs/code/TV-M0-T21.md |

范围：按节修改候选在写入前查数字：本节需求的偏离类型与数字口径沿用写入后的同一条规则；候选里带单位的承诺数字须在本节原文、本章其他正文、需求与评分、挂载要点、已确认事实或检索片段里出现过，否则标「需核对」，人工勾选已核对后才能写入。自由提问在技术服务方案里按小节分会话：会话记小节键与标题，续问只能在同一小节，会话列表按小节过滤；回答仍只可复制。

验收：`tests/backend/test_technical_assistant.py` 通过（数字预检、候选带数字结果、按小节分会话与跨小节续问 403）；`frontend/web/tests/unit/technical-assistant.test.mjs` 通过；前端 lint 通过；OpenAPI `--check` 一致。

<a id="tv-m0-t22"></a>

## TV-M0-T22 · 招标文件解析表格保真与跨页续表切分优化

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 依赖 | [TV-M0-T17](TV-M0.md#tv-m0-t17) |
| 完成时交付 | `docs/delivery/TV-M0-T22.md` |
| 代码解释 | `docs/code/TV-M0-T22.md` |

范围：DeepDOC HTML 表格与本地 DOCX 表格还原为标准 Markdown 表格，识别跨页续表自动补齐表头行；已启用内网 RAGFlow 时技术标 PDF 可优先走 DeepDOC 版面识别；`technical_model_extract` 改为携带 `[第 P 页]` 页锚、不硬切表格行的重叠窗口扫描，强制保留精确页码、原文 `quote` 与本标 `chunk_id` 锚点。

验收：跨页评分表切分与表头承接单测通过；精确页码与 `chunk_id` 溯源回填单测通过；既有解析回归无新增失败。

<a id="tv-m0-t23"></a>

## TV-M0-T23 · 目录编辑“未挂载池”防丢机制与全局项目事实表

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 依赖 | [TV-M0-T22](TV-M0.md#tv-m0-t22) |
| 完成时交付 | `docs/delivery/TV-M0-T23.md` |
| 代码解释 | `docs/code/TV-M0-T23.md` |

范围：`replace_outline` 同步维护 `response_tasks` 与 `unassigned_requirements`（未挂载池），删除章节或非叶化不静默丢失评分点，支持重挂与一键归入兜底节；`confirm_directory` 对未挂载池非空且未显式放行返回 `409 UNASSIGNED_REQUIREMENTS`；新增 `Global Fact Sheet`（项目名、甲方名、服务期、质保期、SLA、驻场人数、项目经理、核心产品型号列表、技术路线）在目录确认阶段核对冻结；前端补齐未挂载池、确认强提醒弹窗与全局事实表编辑抽屉。

验收：后端目录防丢与事实表接口单测通过；前端单元与 lint 通过；OpenAPI `--check` 一致。

<a id="tv-m0-t24"></a>

## TV-M0-T24 · RAGFlow 底层物理 4 库管道、入库脱敏与参数表带表头拆行

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 依赖 | [TV-M0-T23](TV-M0.md#tv-m0-t23) |
| 完成时交付 | `docs/delivery/TV-M0-T24.md` |
| 代码解释 | `docs/code/TV-M0-T24.md` |

范围：前端保持「历史标书 / 资料库」双主入口，资料库内分「运维手册 / 故障案例 / 产品参数」三子库，底层管理 `${company_id}::icg-history / icg-manuals / icg-fault-cases / icg-products` 四套专属画布 DSL 与 Metadata（保留旧 `icg-material` 只读兜底）；历史标书入库前做去实体化脱敏；多型号参数表与 Excel/CSV 台账入库前做带表头拆行 Markdown 化并注入行级型号元数据。

验收：四套画布 DSL、入库脱敏与参数表拆行单测通过；前端 `kb-admin` 单测与 lint 通过；OpenAPI `--check` 一致。

<a id="tv-m0-t25"></a>

## TV-M0-T25 · 检索意图拆解、四库并发配额召回与 Metadata 强过滤

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 依赖 | [TV-M0-T24](TV-M0.md#tv-m0-t24) |
| 完成时交付 | `docs/delivery/TV-M0-T25.md` |
| 代码解释 | `docs/code/TV-M0-T25.md` |

范围：打通 `knowledge_base.py:search` 的 `metadata_condition` 与多切片保留；新增 `technical_query_plan` 基于节路径、挂载评分点与目标型号拆解差异化检索子 Query（模型失败回落规则）；并发执行本标补充召回 + 四子库按配额召回（本标 ~20%、资料三子库 ~55%、历史标书 ~25%），覆盖视图展示子库命中明细。

验收：意图拆解、`metadata_condition` 过滤与配额截断单测通过；前端覆盖视图检索文案测试通过。

<a id="tv-m0-t26"></a>

## TV-M0-T26 · 五段多源隔离 Prompt、废标分级、章间串行摘要与后置核验器

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 依赖 | [TV-M0-T25](TV-M0.md#tv-m0-t25) |
| 完成时交付 | `docs/delivery/TV-M0-T26.md` |
| 代码解释 | `docs/code/TV-M0-T26.md` |

范围：移除单节全量废标灌入改为 `L0 + 关联 L1`；落地五段式多源隔离 Prompt（全局项目事实 JSON / 路径+相邻防重+前文摘要 / 本节原文+满分评分细则+关联红线 / 资料库事实源 / 历史标书写法参考）；`write_volume` 按一级章串行推进并生成 `running_summary`、章内保持并发流式输出；新增 `technical_verifier` 执行防串标全实体扫描、全局事实表冲突比对与高分评分节实质响应复核，写入覆盖视图确认原因。

验收：隔离 Prompt、章间摘要调度与防串标/合规核验器单测通过；本机真机 Qwen + RAGFlow 冒烟通过。

<a id="tv-m0-t27"></a>

## TV-M0-T27 · 真机高危加固五项与端到端真机验收修复

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 关联 Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 依赖 | [TV-M0-T26](TV-M0.md#tv-m0-t26) |
| 完成时交付 | `docs/delivery/TV-M0-T27.md` |
| 代码解释 | `docs/code/TV-M0-T27.md` |

范围：真机五项加固——metadata_condition 零命中逐级放宽阶梯（型号变体 OR → doc_type 级 → 不过滤，history 排他永不放宽）；历史标书脱敏白名单（内置厂商品牌词 + bidder_name/deid_allow，不误伤我方实体，DOCX 标题层级保持）；轻调用不透传思考参数核验 + `ICG_SECTION_CONCURRENCY` 章内并发可配（默认 2）；核验器国家部委/标准机构白名单与自否定语境过滤；ragflow 配置占位 dataset_ids 检测与建议回填 + 一键真机冒烟脚本。端到端真机验收（真实 RAGFlow + 本地 Qwen 30B）驱动修复——模型/RAGFlow 密钥 SECRET 轮换失配恢复、解析路径模型解析失败静默吞错改为 `technical_model_error` 显式落盘 + 安全 DomainError 上抛、`contains` 非子串语义对齐（型号过滤改 `is` 精确匹配 + 变体阶梯）、history 排他改应用侧确定性执行（真机 `not is` 行为不可靠）、核验器单位感知数字抓取与评分点分片匹配消除假阳性、`chapter_summaries` 工作区透出、antd 废弃告警清理。

验收：五项加固专项测试通过；真机端到端（建项 → ragflow 索引 → 模型抽取/目录 → 事实表冻结 → 流式生成 → 核验）走通，覆盖视图四库命中细分、脱敏双兜底、事实一致性可见。
<a id="tv-m0-t28"></a>

## TV-M0-T28 · 导出净化、偏离表兜底、防截断续写与最终真机闭环

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 关联 Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 依赖 | [TV-M0-T27](TV-M0.md#tv-m0-t27) |
| 完成时交付 | `docs/delivery/TV-M0-T28.md` |
| 代码解释 | `docs/code/TV-M0-T28.md` |

范围：终审收口五项定向修复——统一 `【待补】` 提示词与确定性后处理边界（常规交付物直接命名，真实私有事实缺口用 `[待人工补充：具体项]`）；扩充商务/资格/格式条款网关，拦截联合体、转包分包、投标文件份数、报名材料、资格条件、投标有效期、保证金等非技术卷内容；偏离表样表识别兼容「偏离说明表」并在无样表时使用标准 5 列兜底模板稳定导出 `技术偏离表.docx`；修复本地 Qwen `finish_reason` 透出与 comma/顿号/未闭合标点结尾的自动续写；补齐检索审计 query、陈旧 document_id 自愈提示与非测试环境缺 `ICG_DATABASE_URL` 启动硬失败。最终用昆明航空 Oracle 维保 `.docx` 项目执行全量生成与主流程导出闭环。

验收：`tests/backend/test_tv_m0_t28_export_deviation.py` 与受影响后端测试通过；本项目目录为真实模型树且商务条款零泄漏；`history` 路生成期 `status=ok`、`post_filter_hits>0` 且 `query` 非空；正文、偏离表、追溯表串标扫描零命中；`technical.docx` 零截断、零脏标记/Markdown 源码残留、`【待补】` 回归合理低位；`技术偏离表.docx` 与 `response-trace-technical.xlsx` 完整产出且第一人称、核心项零负偏离。开发者最高标 in-review，不标 done。


<a id="tv-m0-t29"></a>

## TV-M0-T29 · 偏离表精准响应、程序条款拦截与导出审计精修

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 关联 Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 依赖 | [TV-M0-T28](TV-M0.md#tv-m0-t28) |
| 完成时交付 | `docs/delivery/TV-M0-T29.md` |
| 代码解释 | `docs/code/TV-M0-T29.md` |

范围：根据 PM 对 `.audit/final-round-v2/` 三件套的拆包复核，精修五项业务质量与导出细节：偏离表按条款精准提炼响应并清洗断句碎片；继续拦截打印、涂改、送达、开标出席、成交公示、电子/纸质一致等招标人义务与程序格式条款；增强 Global Fact Sheet 对分模块服务周期、异构资产明细、评分加分决策与当前年份基准的表达和注入；清除 Markdown 引用前缀、内部 T/S 编号、空括号与缺宾语搭配，处理非首节“本项目…”八股开篇；追溯表精准回填章节与分节知识来源，并把子库为空错误拆到分路审计字段。

验收：聚焦单测通过；昆明航空 Oracle 维保项目局部重跑并重新导出后，偏离表按标准化条款去重且无“我司一、”病句、页码列串台、硬截断残句、评分公式/付款协定/表名噪点，程序格式条款不进入技术正文/偏离表，正文无 `> `、内部 T/S 编号、空括号与跨节 SLA/人数/年限冲突，追溯表章节精确到真实叶子节且知识来源按节命中填充，顶层 `rag.error` 不再因子库为空误报。导出层不得硬编码单项目业务事实；一致性由 Global Fact Sheet 与 Verifier 动态检出。开发者最高标 in-review，不标 done。

## TV-M0-T30 · 偏离表兜底池按章批量语义提炼

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 关联 Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 依赖 | [TV-M0-T29](TV-M0.md#tv-m0-t29) |
| 完成时交付 | `docs/delivery/TV-M0-T30.md` |
| 代码解释 | `docs/code/TV-M0-T30.md` |

范围：保持规则提取器为主干，仅将未命中精确句、落入通用兜底模板的偏离表条款收入兜底池；按所属章节分组，每章 1 次本地 Qwen 批量 JSON 调用；Prompt 传入本章正文、Global Fact Sheet 与兜底条款列表，按条输出 50～110 字第一人称正式投标响应；对模型结果执行外实体、历史做法、负偏离与完整句边界校验，失败单条回落确定性兜底。

验收：聚焦单测覆盖技术/服务类与违约/赔偿/保密类提炼、校验失败回落与零串标；昆明航空 Oracle 维保项目不重新生成正文，仅重导偏离表，通用兜底行显著下降或清零，导出耗时增加控制在 20 秒以内。开发者最高标 in-review，不标 done。

<a id="tv-m0-t31"></a>

## TV-M0-T31 · 招标条款残句清洗、技术/非技术分流与假负偏离加固

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-060](../../issues/ISSUE-060.md) |
| 依赖 | — |
| 来源 | 用户 2026-11-28 重庆中烟真标 P0 质量反馈 |
| 完成时交付 | `docs/delivery/TV-M0-T31.md` |
| 代码解释 | `docs/code/TV-M0-T31.md` |

范围：改造招标解析后处理、入库与偏离判定链路。对长度过短、悬空标点/冒号/未闭合括号结尾、无实质要求动作或纯标题序号的碎片，优先回溯原文所在完整句补全；仍无法构成有效独立要求的残句直接丢弃，不进入技术要求列表。增加技术 vs 非技术范围分流（规则 + 轻量模型兜底），将资格审查、保证金/限价/付款、投标文件装订/签署/密封/修改格式等纯商务与形式条款标记为 `non_technical`，归入“非技术/资格格式条款（已过滤）”区供查阅；这些条款不参与技术目录挂载、不进入技术偏离表、不得触发技术方案负偏离。复核第 1/9 章误标负偏离根因，确保仅真实技术能力缺口才标负偏离。

可验证验收：

- [x] 重庆中烟残句样本能补全或丢弃，丢弃/补全原因可审计，残句不进入技术要求列表。
- [x] 商务、资格、付款、限价、装订、签署、密封、修改格式样本稳定分流为 `non_technical`。
- [x] `non_technical` 不参与技术目录挂载、不进入技术偏离表、不触发技术负偏离。
- [x] 仅真实技术能力缺口标负偏离；无法回答残句或格式条款不得误判负偏离。
- [x] 自动化单元测试覆盖残句补全/丢弃、分流与假负偏离防护。

<a id="tv-m0-t32"></a>

## TV-M0-T32 · 强制模型两阶段目录规划、失败上浮与全量均衡挂载

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-060](../../issues/ISSUE-060.md) |
| 依赖 | [TV-M0-T31](TV-M0.md#tv-m0-t31) |
| 来源 | 用户 2026-11-28 重庆中烟真标 P0 质量反馈 |
| 完成时交付 | `docs/delivery/TV-M0-T32.md` |
| 代码解释 | `docs/code/TV-M0-T32.md` |

范围：改造 `technical_outline.py`、`technical_digest_outline.py` 及相关编排。真实模型环境下技术目录必须由大模型生成，允许内部 JSON 修复和最多 2 次自动重试；修复 `technical_digest_outline.py:213-216` 目录失败/超时记录识别不到真实适配器超时的问题。重试后模型仍不可用或输出仍不合法时必须明确向上报错并在前端提供「重新生成目录」按钮，严禁偷偷塞入通用 11 章规则目录。实行两阶段规划：阶段一基于清洗后的有效技术要求与评分表（按分值权重）生成贴合本项目业务语境的章节目录骨架；阶段二将全部有效技术要求与评分点按语义全量均衡挂载到最匹配章节，彻底移除“每章最多 9 条、其余全塞最后一个兜底章”的硬编码截断，确保高分评分点落在核心技术章节。

可验证验收：

- [x] 真实模型路径不再静默退回规则模板；失败时错误原因、重试次数与审计状态明确上浮。
- [x] 前端在目录生成失败时可见错误并能点击「重新生成目录」恢复，不丢已有确认数据。
- [x] 适配器超时能被 `technical_digest_outline.py` 正确识别并记录，有失败注入测试。
- [x] 每章 9 条硬上限移除；全部有效条款/评分点被挂载或可解释地保留在未挂载池，严禁几十条倾倒「其他服务承诺」。
- [x] 自动化单元测试覆盖模型失败不静默降级、JSON 修复/最多 2 次重试、超时记录与全量均衡挂载。

<a id="tv-m0-t33"></a>

## TV-M0-T33 · 重庆中烟真实 MySQL 验证、前后对比实证与回归留档

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4 小时 |
| 关联 Issue | [ISSUE-060](../../issues/ISSUE-060.md) |
| 依赖 | [TV-M0-T31](TV-M0.md#tv-m0-t31)、[TV-M0-T32](TV-M0.md#tv-m0-t32) |
| 来源 | 用户 2026-11-28 验收与交付标准 |
| 完成时交付 | `docs/delivery/TV-M0-T33.md` |
| 代码解释 | `docs/code/TV-M0-T33.md`（如本卡无代码变化，写明原因） |

范围：使用本地真实 MySQL（端口 3407）与重庆中烟项目（`project-741441c54d364cfb8c16c24e3e8d1937` 或其招标文件）实跑一轮清洗与目录规划验证。输出清洗前 161 条 vs 清洗后有效技术要求数、被过滤残句/非技术条款样本、真实模型生成的目录结构与各章挂载数量分布；证明无规则兜底、无「其他服务承诺」倾倒几十条、核心评分项归位、无假负偏离。跑通后端聚焦回归、`python backend/bid-core/export_openapi.py --check`、前端 `pnpm --dir frontend/web exec tsc -b --noEmit`、`pnpm --dir frontend/web build` 与 `node scripts/check-project-governance.cjs`，并在 `docs/testing/` 登记验证方式、证据与局限。`.audit/` 真实客户材料严禁入库。

可验证验收：

- [x] 真实 MySQL 3407 定向验证完成，PR 描述包含前后对比实证。
- [x] 清洗后有效技术要求数、残句/非技术过滤样本、目录结构与各章挂载分布可复查。
- [x] 核心高分评分项落在核心技术章节，无规则兜底与「其他服务承诺」倾倒。
- [x] 后端聚焦回归、OpenAPI、前端类型检查/构建、治理检查按真实结果记录。
- [x] `docs/testing/` 留档验证方式与局限；Mock 与真机证据严格区分。
