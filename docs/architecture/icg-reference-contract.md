为什么有这个文件：让示例页面和后台使用同一套数据与操作约定。

它解决什么问题：避免前端继续使用假反馈，后台另做一套互不相通的流程。

# ICG 示例主链路接口约定

日期：2026-10-10。关联 ISSUE-007。实施目标是 ICG 原始设计和交接清单，先贯通主链路，再补齐其他页面。模型与数据库保持可替换；原始资料不改。

## 当前实施边界

正式页面放在 `frontend/web`，保留深色窄侧栏、白色顶栏、项目摘要、分册状态条、项目页签、解析三栏、矩阵表格、编辑三栏与检查问题列表。新页面最终由同一后台地址提供；原后台验证页仅作为开发验收入口。

新业务接口使用 `/api/v1`。演示账号登录与章节租约等现有接口先复用 `/api`；正式接口迁移单独验证，不以旧字段假冒交接契约已完全满足。登录凭证只留当前页面，所有新接口核对公司与权限。

## 主链路首批约定

下表字段是本次实现的共同入口；实际 OpenAPI 从最终代码生成，代码变动同步本表。

| 请求 | 主要输入 | 主要返回及规则 |
|---|---|---|
| GET `/api/v1/projects/{id}/workspace` | 登录凭证 | `project`, `stage`, `files`, `requirements`, `facts`, `chapters`, `checks`, `exports`, `jobs`, `parse_confirmed`；全部来自同一后台状态 |
| GET `/api/v1/projects/{id}/files/{file_id}/preview` | 登录凭证 | 实际原文分块、定位页码方式及限制；未成功解析返回409 |
| DELETE `/api/v1/projects/{id}/files/{file_id}` | 非空 `reason` | `deleted_file_id`；仅无来源引用的未解析/失败上传可移除，已解析或仍有来源返回409；须重新确认解析与大纲 |
| PATCH `/api/v1/projects/{id}` | `name`, `tender_number`, `deadline`, `sensitive` | 项目信息与版本；版本更新带 If-Match |
| POST `/api/v1/projects/{id}/files` | `filename`, `content_base64` | 文件 id、解析任务与状态；UTF-8文本、DOCX优先真实解析，PDF能力按适配器情况明确标示 |
| GET `/api/v1/projects/{id}/files/{file_id}` | 登录凭证 | 真实上传原件，限制当前公司 |
| POST `/api/v1/projects/{id}/parse` | 无或明确文件范围 | `job`, `requirements`, `facts`, `conflicts`；保留原文、页码及人工确认状态 |
| PATCH `/api/v1/projects/{id}/requirements/{requirement_id}` | `text`, `category`, `volume`, `chapter_id`, `status`, `response`, `reason`, `evidence_ids` | 更新后的要求；不允许伪造章节、证据或覆盖他人版本 |
| POST `/api/v1/projects/{id}/parse/confirm` | 无 | 必须先处理冲突和未确认条款；确认不代表自动生成承诺 |
| PATCH `/api/v1/projects/{id}/facts/{fact_id}` | `value`, `status`, `reason` | 事实人工核对；改变冲突的已选值会重新打开冲突 |
| PATCH `/api/v1/projects/{id}/conflicts/{conflict_id}` | `selected_fact_id`, `reason` | 从实际候选中明确选择，其他值被排除；不得伪造ID |
| POST `/api/v1/projects/{id}/plan` | `chapters`: `title`, `volume` 列表 | 已确认大纲与章节；不得在有草稿或锁时静默覆盖正文 |
| POST `/api/v1/projects/{id}/generate` | 无或选定章节 | 生成任务及章节候选；模型演示实现明确标识，不自动提交正式正文 |
| GET `/api/v1/projects/{id}/checks` | 无 | 检查批次及问题列表，标示已实现规则与未实现规则 |
| POST `/api/v1/projects/{id}/checks` | `volume`: `technical`/`business`/`all` | 检查绑定当前条款、证据和已提交正文指纹；不读取未提交草稿 |
| POST `/api/v1/projects/{id}/exports` | `check_id`, `kind`: `internal`/`submission` | 导出记录与两个独立 Word 地址；提交版仅经理，有效检查与完整分册前提需后台校验 |
| GET `/api/v1/projects/{id}/exports/{export_id}/{volume}` | 登录凭证 | 技术或商务Word实际文件；检查失效或公司不符时拒绝 |
| GET `/api/v1/jobs` | 登录凭证 | 当前公司任务，明确同步/可恢复能力边界 |
| GET/POST `/api/v1/library` | 公司合成证据、类型、名称、正文、有效期 | 企业资料和可引用状态，证据变动使旧检查过期 |
| PATCH `/api/v1/library/{id}` | 名称、类型、正文、有效期、状态、核对理由 | 实质变化默认回待确认；同次重新确认需非空理由；使用公司资料版本 |

章节编辑先复用已验证租约、草稿、版本、建议接口。编辑器先保留来源、正文与建议确认三区布局，再补结构化段落、选区与引用写入；不把纯文本编辑标为完整编辑器交付。

GET工作区/资料响应包含版本和ETag。v1写入带 `If-Match`（核对的版本）和 `Idempotency-Key`（防重复操作的标记）：缺版本428，旧版本409，同标记同载荷重放原结果，改载荷409。解析/生成失败也可能保存失败任务并增加版本，错误 `details.revision` 明示时页面刷新最新状态，保留填写内容。

v1错误为 `{code,message,details,traceId}`，旧接口仍用 `{error:{code,message},request_id}`，页面理解两种格式。当前任务同步完成，未实现交接要求的202排队、SSE持续通知和重启恢复；不得假称它们已联调。

工作区、生成候选和旧章节建议均返回 `input_fingerprint`，即参与本次生成的资料摘要。条款、事实、证据或已提交正文改变后，旧候选失效；页面采纳前重新读取工作区核对，不只看章节版本。未声明运行位置的模型也不能处理敏感项目；两条生成入口使用同一门禁。截止时刻以UTC保存、北京时间显示；证据有效期按北京时间截止日核对，含时分的原文事实比较同一时刻。

旧草稿和历史正文先并排核对，取得编辑权后重新核对后台版本及草稿顺序，再保存为当前版本的个人草稿。只有提交本节才产生新的正式正文；结构化差异合并和正式回滚事件尚未完成。

## 服务承诺矩阵本次接口（reference-sla-1）

对应PRD 5.3.2、5.7.8与字典3.2.13～15、3.10.1.5。服务承诺（SLA）是响应、到场、恢复等承诺指标。公司模板与项目取值分开保存；改项目承诺不能改公司能力。模板实质更新后重新确认，引用它的项目须重新核对，不能靠旧快照继续通过。

| 接口 | 输入与输出 |
|---|---|
| GET `/api/v1/sla/templates` | 当前公司 `revision`、`items`；版本使用公司资料版本，与资料库写入共用 |
| POST `/api/v1/sla/templates` | 负责人新增模板：`name`、`edition`、`service_hours`、`body_text`、`status`、`reason`、`variables`；返回 `revision`、`item` |
| PATCH `/api/v1/sla/templates/{id}` | 负责人修改；实质变化回待确认，同次重新确认须说明理由；返回 `revision`、`item` |
| POST `/api/v1/projects/{id}/sla/template` | `template_id`、`reason`；选用已确认的本公司模板；同模板刷新保留项目承诺/招标绑定并重新核对，更换不同模板前明确提示重置项目值，返回项目 `revision` 与 `sla` |
| PATCH `/api/v1/projects/{id}/sla/values/{var_key}` | `project_value`、`project_unit`、`requirement_id`、`tender_required_value`、`tender_unit`、`reason`；人工核对原条款后登记数值或未量化要求，不能伪造来源或改公司能力 |
| POST `/api/v1/projects/{id}/sla/apply-tender` | 无；逐项按招标值取值，遇到超出公司能力时取公司能力极限并显示不满足；不自动批准风险或确认事实 |
| POST `/api/v1/projects/{id}/sla/values/{var_key}/review` | 负责人填写非空 `reason`；确认当前数值的能力风险/需人工判断，确认绑当前全部输入，修改后失效；不满足招标的条目不能批准为满足 |
| POST `/api/v1/projects/{id}/sla/commitment` | 无；返回 `revision`、`commitment`（`id`、`filename`、`download_url`、`created_at`、`fingerprint`、`status`）；失败/未核对项禁止生成 |
| GET `/api/v1/projects/{id}/sla/commitment/{export_id}` | 当前数据仍一致才下载实际Word表格；不是正式递交文件 |

模板变量：`var_key`（本模板唯一）、`label`、`group`、`value_type`（integer/decimal/text）、`default_value`、`unit`、`compare_direction`（lower_better/higher_better/exact）、`best_committable_value`（可空）。模板另含可编辑的业务版本 `version_no`（如1.0），并返回 `id`、`company_id`、`revision`、`status`；业务版本与用于防覆盖的整数记录版本分开。不预设或伪造真实公司能力。完整故障等级定义及服务类别治理仍另验收。

工作区新增 `sla`：未选用时为null；已选用包含 `template_id`、`template_name`、`template_revision`、`template_stale`、`rows`。每行包含上述变量字段、项目取值/单位、招标要求值/单位、`requirement_id`、`source`（可空）、`source_stale`、`judgment`、`judgment_label`、`message`、`exceeds_capability`、`review`（确认人/时间/理由，或null）、`fact_status`（pending/confirmed/needs_review）、`variable_token`（`{{sla:P1.response}}`）。判定由后台即时计算，不由页面伪造。

判定码为 `satisfied`、`not_satisfied`、`exceeds_capability`、`missing`、`manual`、`not_required`、`unquantified`。最后两种保留PRD明确的边界，不冒充满足。分钟/小时/自然日可换算；工作日和自然日、月和自然日不能强换算；相同频次单位可比较，其余按字典与可证明的换算判定。纯文本按exact核对。输入必须为有限、非负且符合类型的值。

SLA事实以 `sla:<var_key>` 为稳定ID，工作区事实表只引用当前项目值：`source_type=sla`、`sla_var_key`、`unit`、`required`，来源可空，值不可在事实页另改。有招标来源的事实必须负责人逐条确认；数值、来源、模板发生实质变化后为需复核，阻止新写作方案与导出。SLA来源条款不能通过改类别躲过未绑定指标检查。

检查新增能力/取值/引用检查（只声明R09/R10的已实现子集）：不满足、未填写、过期模板/来源和未核对事实阻断；未批准的能力风险/人工判断须处理后才可导出。正文中的变量由当前已确认值替换，未知/未确认变量阻断；可明确匹配指标名称的手写数值不一致时定位到章节，不能声称覆盖所有自然语言写法。项目输入摘要纳入SLA项目值、审阅和当前模板。两册导出与承诺函都用同一变量解析，并保留内部稿标记。

所有写入保持现有If-Match、Idempotency-Key、公司隔离和事务回滚；按设计P-07服务承诺值和模板维护均限负责人，其他成员只读。SLA必备事实逐条确认也限负责人。审计记录变更理由、旧/新取值与批准依据。模型、数据库仍通过原接口替换。

## 后续必须补齐

完整分册定稿、正文来源和变量节点、事实/SLA冲突、所有一期检查规则、文件解析覆盖、资料治理、任务恢复、答案卡与引用、完整角色管理、搜索/提醒、规则/模型/服务/品牌配置，以及设计规定的登录和安全状态。

缺少的示例源包由截图和文档重建；设计差异单独登记，不趁实现主流程改写产品。产品完成以每页真实操作和业务验收为准，不能按文件数、测试数或旧任务完成比率推断。

首次或主动重新确认模板必须填写本次非空reason，页面打开修改时清空旧理由供本次填写。`sla.commitments`可读取当前有效/过期的承诺函记录；模板/来源/数值与已提交正文变动使下载失效。正文变量统一换算为模板单位，后缀冲突或不可证明的单位转换拒绝输出；无后缀自动附模板单位。矩阵未绑定招标要求的额外承诺需负责人核对（R30子集）；承诺函每行都须事实已确认。该阶段手动变量链路的历史限制已由下述reference-writing-1补上选定事实与必备服务事实输入；完整事实类别与语义规则仍未完成。


## 本章写作输入（reference-writing-1）

对应PRD §5.7.2/5.7.8/5.11。当前44路径50操作；软件应用版本仍reference-1，交付阶段版本独立。

POST plan的每章新增`fact_ids`（选中的本项目可选事实，默认空）、`writing_points`（最多5000字，默认空）、`target_length`（1～100000整数或null）。必备事实自动加入，不能通过不选择绕过。当前manager批量确认整份，保存`confirmed_by/confirmed_by_name/confirmed_at`；未实现原文完整章节/分册负责人分配。

工作区新增`writing_plan`（确认信息与chapters配置），各chapter新增`writing_input`；`plan_confirmed`按来源摘要即时计算，不继续沿用已变更的来源。条款映射、响应、证据和事实/方案变化需重新确认；提交正文只使候选/检查/输出失效，不让来源相同的方案自动失效。

GET `/api/v1/projects/{project_id}/chapters/{chapter_id}/writing-input`只读返回`source_scope=whole_chapter`、`input_snapshot`、`ready`、`issues`。这是当前准备输入，尚未发送模型；不ready仍可查看具体阻断，但不能生成。

生成候选及旧整章建议返回当次`source_scope/input_snapshot`。快照包含project标识/名称、chapter标识/分册/正文版本、plan配置与确认、requirements原文/响应/来源、evidence名称/记录版本/有效期/内容/关联要求、facts取值/单位/必备/变量/来源、omitted_inputs理由、official_content和生成时间；实际发送时另保存`model_input/model_instruction`。没有检索知识库或片段，不能冒称检索快照或逐段来源。SLA读项目当前值，不读模板默认值。

候选新增`status=valid/stale`，旧候选保留历史快照供人核对，但不可采纳。快照自身不参与项目输入指纹。普通事实使用`{{fact:事实ID}}`，SLA使用原专用token；输出先检查未知、未确认、未纳入本章、错误单位及丢失原变量。源值修改返回FACT_SOURCE_CHANGE_REQUIRED与data_source_value理由；页面给事实表/矩阵入口。后台、来源当前性及输出仍必须核对，不能只依赖页面按钮。

只实现明确可验证的变量和来源子项；完整R27/R44、敏感事实治理、勾选片段、字数动态预算、逐段矩阵绑定、拒绝事件完整审计和选区助手继续后续任务。两册内部稿用同一解析器，正式递交门禁不改变。

写入来源保护（reference-writing-1收尾）：有requirements/facts/sla的工作流章节，PUT draft与POST versions请求必须包含当前input_fingerprint；服务器在同一事务校验来源摘要、编辑凭据及正文revision。缺失返回409 INPUT_FINGERPRINT_REQUIRED，过期返回409 INPUT_FINGERPRINT_STALE。Draft返回保存时的input_fingerprint，源改后不自动升级；真正重复提交可返回已完成结果，不重复写入。独立无来源旧demo仍可省略。事实取值已包含明确数字单位时，正文不能追加不同或重复单位，否则检查阻断；未知普通文本不推测单位。
