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

## 后续必须补齐

完整分册定稿、正文来源和变量节点、事实/SLA冲突、所有一期检查规则、文件解析覆盖、资料治理、任务恢复、答案卡与引用、完整角色管理、搜索/提醒、规则/模型/服务/品牌配置，以及设计规定的登录和安全状态。

缺少的示例源包由截图和文档重建；设计差异单独登记，不趁实现主流程改写产品。产品完成以每页真实操作和业务验收为准，不能按文件数、测试数或旧任务完成比率推断。
