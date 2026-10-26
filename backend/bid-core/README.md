为什么有这个文件：说明怎样运行ICG产品页面与后台，以及页面操作实际由哪些接口处理。

它解决什么问题：避免把内存保存、模拟建议和基础 Word 文件误当成完整生产系统。

# ICG本地产品与业务后台

当前开发关联 ISSUE-007 / APP-M1，目标是实现完整ICG示例。历史 ISSUE-006 / BE-M0-T01 只记录最小后台的交付。这里的Python/FastAPI后台负责同一产品的业务处理，`frontend/web`是供人操作的页面；后台还把构建好的页面提供给浏览器。所有预置公司、账号、项目与正文均为合成数据。

数据库与模型按本轮要求保留替换接口，默认使用内存仓库与模型替身。招标文件的本地文字提取已经实际实现，复杂解析、扫描件文字识别、真实模型和生产部署尚未完成。

资料及公司模板旧表单保护已在同源页面接通；后台仍按原公司版本校验，前端不能把刷新当作用户已核对。ISSUE-008 / T16新增19项真实HTTP回归，当时全后台229项通过，见[验收](../../docs/testing/2026-10-11-library-basis.md)。这是限定缺陷修复，完整资料审核、附件、知识片段和正式Word仍待实现。

会话与权限契约已落地真实 `GET /api/v1/session`：重新读取后台当前会话账号，返回导航/动作、公司和可选项目/章节权限，不带正文/草稿。页面先核验会话再请求业务数据。系统现行支持 8 大标准 RBAC 角色体系（`platform_admin`、`group_admin`、`company_admin`、`data_admin`、`project_lead`、`bid_writer`、`auditor`、`viewer`），并对历史三角色（`manager`、`editor`、`viewer`）保留显式兼容映射（`role_mode: legacy-demo-compat`），支持通过 `VITE_DEMO=0` 关闭演示模式。

## 安装和启动

在仓库根目录运行（Windows PowerShell）：

本轮验证环境为Windows和Python 3.12.10；首次安装需要本机已有Python。其他Python版本需另行验证依赖组合。

推荐统一入口：`& .\backend\bid-core\Start-Demo.ps1 -Install`。它会创建Python环境、安装后台依赖、安装前端依赖并构建页面，再启动；后续启动省略`-Install`。首次安装还需要Node.js和pnpm，本轮页面验证使用Node.js 24与pnpm 11.25.0。也可使用下面的分步方法。

```powershell
python -m venv .venv
& .venv\Scripts\python.exe -m pip install -r backend/bid-core/requirements.txt
pnpm --dir frontend/web install --frozen-lockfile
pnpm --dir frontend/web build
& .venv\Scripts\python.exe -m uvicorn icg_demo.main:app --app-dir backend/bid-core --host 127.0.0.1 --port 8710 --workers 1
```

浏览器打开 [ICG产品入口](http://127.0.0.1:8710/)。`/`读取`frontend/web/dist/index.html`，`/assets`提供构建资源；未构建页面会返回`UI_NOT_READY`，需先构建。旧验证页为`/demo`，它的资源仍在`icg_demo/static/`，通过`/static`提供。

默认只监听本机，必须使用单进程。安装依赖需要可用的软件源或预备好的安装包；默认适配器在安装后运行时不调用外部模型或网页资源。不要把 `.venv`、`node_modules`、上传文件、运行日志或真实客户数据提交入库。前端单独开发时使用`pnpm --dir frontend/web dev`，5173端口将`/api`请求转发到8710后台，详见[前端说明](../../frontend/web/README.md)。

查看 `/health` 可确认 `repository: memory`、`model: mock`。`/openapi.json` 提供实际接口说明；默认 Swagger 和 ReDoc 页面关闭，以免离线运行依赖外部网页脚本。

进程入口会读取模型开关，但默认不访问外部模型。只有同时把 `ICG_MODEL_PROVIDER` 设为 `openai-compatible`，并提供 `ICG_MODEL_BASE_URL`、`ICG_MODEL_NAME` 和 `ICG_MODEL_IS_LOCAL`（`true` 或 `false`），才会使用 OpenAI 兼容适配器。可选变量：`ICG_MODEL_API_KEY_ENV`（默认 `ICG_MODEL_API_KEY`，这里写的是密钥所在变量的名字）、`ICG_MODEL_TIMEOUT_SECONDS`（默认 60）、`ICG_MODEL_MAX_TOKENS`（默认 1024）、`ICG_MODEL_RETRIES`（默认 1）。密钥、内网地址和客户正文都不要写入仓库。配置缺失时进程拒绝启动，不会改用演示文本假装调用成功。测试里的 `create_app()` 不读取这些变量。真实端点仍待 ISSUE-010，当前验收没有连接内网。业务库已决定为 MySQL 8，但本进程不连接它，运行数据仍在内存中。检索口同样只在内存中，见下文。

## 当前产品主流程

1. 用合成项目经理账号新建项目，填写招标编号和投标截止时间，到项目设置登记成员、两册负责人及合标人。账号同时需要公司角色和项目分工；同公司未加入项目也不可见。页面按北京时间输入和显示，接口时间按UTC保存。
2. 上传合成招标文件并解析，核对原文、条款、事实与冲突。解析结果必须由人确认；未处理的冲突、待确认条目或未解析文件会阻止确认。
3. 在响应矩阵填写逐项响应，选择本公司已确认资料作为证据，再映射到对应分册章节。响应矩阵就是“每项要求在哪里回答、用什么证明”的对照表。
4. 分配技术/商务本节编写人，逐节保存事实、要点和目标字数，再由本节编写人或对应负责人确认。本节已确认就可以单独生成，另一节未确认不拖住它。模型替身只返回候选，不改变已提交正文；看差异确认后，保存和提交仍需取得编辑权。
5. 编辑、保存草稿并提交章节版本，查看版本和操作记录。检查与输出只读取已提交正文。
6. 项目负责人运行全项目流程检查并生成两册；分册负责人可以仅检查/生成本册。合标人下载已生成文件，不因此取得检查、生成或全部章节编辑权。输出只取已提交正文，个人草稿不入Word。

这条主流程已完成一轮真实页面操作，两个Word的文件包和各册正文已核对。页面渲染尝试尚未成功：本机缺少LibreOffice转换程序，Word导出也失败。因此Word版式仍未验收，不能宣称正式模板、目录、附件和定稿已交付。完整目标见[ICG覆盖清单](../../docs/testing/icg-coverage.md)，主流程的成功不代表其余页面已完成。

## 文件解析的实际范围

当前单文件上限5MB。支持UTF-8文本（`.txt`、`.md`）、有效DOCX文件包和含可提取文字的PDF。文本按换页符定位；DOCX只按明确分页符定位，没有经过Word排版，不能把它当最终印刷页码。PDF按实际页面提取文字。

扫描PDF、含无文字页面的PDF返回`OCR_REQUIRED`。OCR就是把图片里的文字识别出来，当前尚未接入；不能把只读到了部分页面说成完整解析。加密PDF、非法文件包、非法控制字符和超出限制的文件也会明确拒绝。原件与文字预览均需登录并核对所属公司。

提取后的分类和条款识别是确定性的基础规则，依然需要人工确认，不等于完整的复杂文档理解、漏抽复核或附件关系识别。

## 旧后台验证页的历史流程

`/demo`保留首个后台交付的简单操作页，用于验证单章节失败边界，不是完整产品入口：

1. 选择甲公司编写人登录，打开合成项目的技术或商务章节。
2. 取得编辑权；保存草稿后刷新，本人草稿单独显示，上方先展示已提交正文。核对后可恢复草稿；基础版本落后时必须先明确处理冲突，不能直接覆盖别人修改。草稿不改变正式正文或版本。
3. 提交正式版本后，查看正文、版本列表和审计记录。
4. 请求模拟建议：后台只返回文本，没有直接修改正文。查看建议文本并确认采用后，页面仍通过正式提交接口写入。
5. 检查已提交版本；空正文或含“待补”的文字（包括 `【待补】`、`[待补]`）会阻止输出。这是演示用的简单文字检查，不判断上下文含义。
6. 检查通过后创建输出并下载真正的 `.docx`。文件明确标注“本地演示内部稿，不可正式递交”。
7. 换成只读账号验证写入被拒；换乙公司账号验证甲公司资源不可访问；经理填写理由接管后，原编写人的旧编辑权不能再保存。

旧验证页上述编辑使用种子项目分工；单章检查/输出现在也要求项目或对应分册负责人，编写账号不能借旧入口绕过产品权限。

## 多人协作本次验证

T14/T15已实际验证项目成员、可空参与分册、技术/商务负责人、本节编写人和合标下载。人员交接保留正文与历史、每人原草稿，旧编辑权失效；团队/基本信息/写作方案旧表单需要明确核对新内容，不能拿刷新后的版本号覆盖他人修改。

当前完整后台210项、前端36项回归通过。实际本机多账号验证入口：`& .\.venv\Scripts\python.exe backend\bid-core\smoke_members.py --base-url http://127.0.0.1:8710`，只创建完全合成的新项目；输出文件可用`--output-dir`指定工作区外目录。页面与下载文件的独立证据见[成员验收](../../docs/testing/2026-10-10-project-assignments.md)。模型/数据库仍按要求预留，完整规则和正式版式继续。

## 实际接口与页面协同

业务请求使用`Authorization: Bearer <access_token>`，即演示登录返回的本次登录凭证；页面、健康检查和账号/登录入口无需登录。前端登录凭证只存在当前页面内存，不写长期浏览器存储。

两组接口共用一个仓库和一套公司权限。项目级`revision`是数据版本号：页面修改`/api/v1`数据时带`If-Match`，意思是“只在数据仍是我读取的这个版本时保存”；带`Idempotency-Key`，意思是“重复发送同一次操作时不要再执行一次”。公司资料库有独立版本号。

| 产品接口 | 作用 |
|---|---|
| `GET /api/v1/projects/{id}/workspace` | 读取项目、文件、条款、事实、章节、检查和输出摘要，返回版本号与ETag |
| `PATCH /api/v1/projects/{id}` | 更新项目基本信息 |
| `POST /api/v1/projects/{id}/files`；`GET .../files/{file_id}`、`.../preview` | 保存真实上传字节、下载原件和读取文字预览；上传通过JSON中的Base64字段传递 |
| `POST /api/v1/projects/{id}/parse`、`/parse/confirm` | 执行本地解析和人工确认门禁 |
| `PATCH /api/v1/projects/{id}/requirements/{rid}`、`/facts/{fid}`、`/conflicts/{cid}` | 核对条款、填响应/证据/章节映射、处理事实和冲突 |
| `POST /api/v1/projects/{id}/plan`、`/generate` | 保存两册大纲与顺序、创建待人核对的章节候选 |
| `GET/POST /api/v1/projects/{id}/checks` | 查看和执行项目级流程检查 |
| `POST /api/v1/projects/{id}/exports`；`GET .../exports/{eid}/{volume}` | 创建技术/商务内部稿并带权限下载 |
| `GET /api/v1/jobs` | 查看本公司项目的同步任务记录；没有取消和断点恢复 |
| `GET/POST /api/v1/library`；`PATCH /api/v1/library/{id}` | 本公司基础文本资料及确认状态、有效期维护 |

系统以 `/api/v1` 为主接口路径。核心主流程与会话接口：

| 产品主接口（主路径） | 作用 |
|---|---|
| `GET /api/v1/session` | 依据 Bearer Token 重新核验会话，返回 8 角色权限集与可用导航 |
| `GET /api/v1/projects` | 读取当前有权访问的项目列表 |
| `GET /api/v1/projects/{id}/workspace` | 读取项目、文件、条款、事实、章节、检查和输出摘要，返回版本号与ETag |
| `PATCH /api/v1/projects/{id}` | 更新项目基本信息 |
| `POST /api/v1/projects/{id}/files`；`GET .../files/{file_id}`、`.../preview` | 保存真实上传字节、下载原件和读取文字预览 |
| `POST /api/v1/projects/{id}/parse`、`/parse/confirm` | 执行本地解析和人工确认门禁 |
| `PATCH /api/v1/projects/{id}/requirements/{rid}`、`/facts/{fid}`、`/conflicts/{cid}` | 核对条款、填响应/证据/章节映射、处理事实和冲突 |
| `POST /api/v1/projects/{id}/plan`、`/generate` | 保存两册大纲与顺序、创建待人核对的章节候选 |
| `GET/POST /api/v1/projects/{id}/checks` | 查看和执行项目级流程检查 |
| `POST /api/v1/projects/{id}/exports`；`GET .../exports/{eid}/{volume}` | 创建技术/商务内部稿并带权限下载 |
| `GET /api/v1/jobs` | 查看本公司项目的同步任务记录 |
| `GET/POST /api/v1/library`；`PATCH /api/v1/library/{id}` | 本公司基础文本资料及确认状态维护 |

章节编辑与旧演示兼容接口（已标为 Deprecated 或受控兼容）：

| 接口路径 | 兼容说明 |
|---|---|
| `GET /api/demo/accounts`、`POST /api/demo/login` | **[Deprecated]** 仅供演示兼容；兼容截止至 2026-11-15（RFC 8594 `Sunset: Sun, 15 Nov 2026 00:00:00 GMT`）；响应头返回 `Deprecation: true` 与 `Sunset` 头；生产配置（`ICG_REQUIRE_MYSQL=1`）下阻断演示账号 |
| `GET /api/projects/{id}/chapters`、`GET /api/chapters/{id}` | 查看本公司章节、当前正式正文、有效锁摘要和本人草稿 |
| `POST /api/chapters/{id}/lock`、`/lock/renew`、`/lock/release` | 取得、续期和释放编辑权，默认有效期 120 秒 |
| `PUT /api/chapters/{id}/draft` | 带编辑凭据、正式版本号及递增序号保存草稿 |
| `POST /api/chapters/{id}/versions` | 原子提交正文、新版本、审计和重复请求结果 |
| `GET /api/chapters/{id}/versions`、`/audit` | 查看该章节实际版本与操作记录 |
| `POST /api/chapters/{id}/suggestions` | 返回修改建议及其基础版本，不自动保存正文 |
| `POST /api/chapters/{id}/checks`、`/exports` | 对已提交正文做基础检查，并创建输出记录 |
| `GET /api/exports/{id}/file` | 携带登录凭据下载文件 |

在演示兼容模式（`role_mode: legacy-demo-compat`）下，系统将历史演示身份映射为标准角色（`manager → project_lead`，`editor → bid_writer`，`viewer → viewer`）；在标准 RBAC 模式（`role_mode: rbac-8roles`）下，系统支持 PRD v1.8 定义的全部 8 大标准角色及权限集。公司经理不自动得到公司管理员权限。公司一致还须加入项目，写入和两册内部稿按项目/分册/章节分工决定，不能仅凭公司角色；只读成员没有v1项目导出权限。允许接管的负责人仍须填写理由，普通编写人不能接管。编辑权同时绑定账号与本次登录会话，别人的凭据也不能冒用。后台每次写入重新核对权限和编辑权，不能只靠页面按钮是否可点；旧单章输出接口继续仅供历史验证页使用。

未登录为401，只读账号写入为403，跨公司或不存在的资源为404，旧版本、乱序草稿、重复请求内容冲突为409，编辑权占用或失效为423，字段不符合要求为422。`/api/v1`缺少版本号或重复请求标记为428；体积限制为413。每个业务code只对应一个HTTP状态。`MODEL_UNAVAILABLE`为502：`/api/v1`候选生成返回`{code, message, details, traceId}`，旧`/api`章节建议仍返回`{error: {code, message}, request_id}`。两者响应头都含服务端生成的`X-Request-ID`。

重复请求标记的范围是scope、账号和键。项目写入的scope是项目编号，公司资料和服务承诺模板是`library:{公司编号}`。同标记、同内容返回第一次成功结果；同标记、不同内容被拒。失败不留下可重放记录。记录保留24小时，内存最多2048条。旧章节提交仍在正文发送该标记；如果请求头也带了标记，两者必须相同。重试仍须持有有效编辑权。客户端只对允许重试的网络错误、网关502及瞬时503复用同一标记；502 MODEL_UNAVAILABLE和503 SECRET_KEY_UNAVAILABLE不自动重试；409、422、423、428不自动重试。202与SSE仍未实现。

## 草稿、检查与输出的分界

检查和 Word 只取已提交正文，绑定它的版本号、内容摘要和当时的项目输入摘要。保存草稿不改变已提交版本的检查，也不会把草稿写进输出；创建输出返回 `excludes_drafts: true`，并带上 `check_id`、`revision`、`content_hash`、`input_fingerprint`。不返回 `stale` 布尔字段。正文或项目输入变化后，旧检查不能再导出，旧文件下载返回 `EXPORT_STALE`。操作页面对尚未提交的修改另行提醒。

项目检查记录输入指纹，即把这次项目资料和已提交正文作一份可比对的摘要。项目、上传文件、条款、事实、冲突、计划、章节正文及公司资料变动后，旧检查和旧导出自动失效；当前对公司资料采用保守做法，同公司任一资料变动都会影响项目检查。草稿和模型候选不进入导出正文，也不因自身变化改变正式内容的检查结果。

当前检查实现10项流程条件，例如人工确认、有效章节映射、响应/证据存在、已确认资料、登记有效期与截止日关系、两册正文和旧输入失效；它们不是完整44项参考规则的实现。登记有效期为空时，目前不会因缺日期阻断，完整资料治理仍待补齐。检查返回`coverage.complete: false`，剩余5组能力继续实施。

项目级内部稿含对应分册的已提交章节，按确认顺序输出，并对部分长号码作基础遮盖。未完成结构化敏感变量、全部业务规则、正式模板、目录与附件。请求递交版时，编写人被权限拒绝，经理也会被`RULES_INCOMPLETE`拒绝。既有单章检查和下载只用于旧验证页，不可替代项目级两册检查。

## 可替换位置与测试入口

`icg_demo.ports.Repository` 提供 `read()` 和 `transaction(operation)`；`MemoryRepository` 用可重入锁和隔离副本执行事务，操作、返回值拷贝或提交失败都不会保留部分修改。替换为数据库时必须提供等效的原子提交和失败回滚，不能只换掉一个字典。

`icg_demo.ports.ModelProvider`提供同步`suggest(instruction, content) -> str`，只返回文本，不直接读写仓库。章节建议传入当前有权章节的正文；产品候选生成则由业务层组织本章节已确认条款、响应和所选证据文本后传入。默认`DemoModelProvider`固定返回模拟建议，`provider: demo`、`is_real_model: false`。敏感项目已有基础路由限制，但真实模型的超时、完整字段权限、敏感路由和审计仍需继续实现。

`icg_demo.ports.ParserProvider.parse(filename, content)`接收原件字节并返回原文页块、分页依据和提示，不写仓库。默认`LocalTextParser`执行上文的本地文字提取；换解析器时保留公司权限、人工确认和页码来源规则。

`icg_demo.ports` 另有 `EmbeddingProvider.embed`、`RerankProvider.rerank` 和 `VectorStore.upsert/search`。搜索必须同时给出公司、状态和类型。`icg_demo.retrieval.EvidenceCandidateService` 用这三个内存实现产出资料规则、片段检索和仅供参考的历史投标。`create_app` 不构造该服务，页面请求不会调用它。它不连接 MySQL，也不使用向量库。

`icg_demo.main.create_app(repository=None, model_provider=None, clock=None, parser_provider=None)`可注入三个接口和可控时钟。时钟返回Unix秒数或带时区的`datetime`。服务实例在`app.state.service`，产品流程服务在`app.state.workflow`，两者共用同一仓库。不同应用实例默认各有独立内存，不共享状态。

| 模块路径 | 分层定位 | 职责描述 |
|---|---|---|
| `icg_demo/main.py` | 适配器与装配入口 | FastAPI 应用组装、生命周期、全局中间件、统一错误体及生产演示账号门禁 |
| `icg_demo/database.py` | 兼容门面 (Façade) | 76 行转接壳，向后兼容代理至 `icg.infra.mysql_gate` 与 `icg.infra.repositories.*` |
| `icg_demo/workflow.py` | 兼容门面 (Façade) | 29 行转接壳，向后兼容代理至 `icg.domain` 四大服务（workflow_orchestrator, export_service, generation_service, outline_service） |
| `icg_demo/adapters.py` | 适配器门面与替身 | 包含 `DemoModelProvider` 演示替身实现；re-export `MemoryRepository` 与 Word 生成工具 |
| `icg_demo/schemas.py` | 契约模型层 | 请求/响应 Pydantic 模型，定义 AuthMode / RoleMode / 统一错误体契约 |
| `icg/infra/memory_repository.py` | 基础设施实现 | 内存事务仓储 `MemoryRepository` 与演示状态初始化 `seed_state` |
| `icg/infra/mysql_gate.py` | 基础设施门禁 | MySQL 引擎连接、`ICG_REQUIRE_MYSQL=1` 生产门禁与重试回执处理 |
| `icg/infra/repositories/` | 持久化仓储模块 | `chapters.py`、`checks_exports.py`、`projects.py`、`library.py`、`sla.py`、`jobs.py`、`model_config.py`、`mysql_repository.py`、`common.py` |
| `icg/domain/workflow_orchestrator.py` | 领域编排服务 | 投标项目整体工作流状态机编排与用例协调 |
| `icg/domain/export_service.py` | 领域导出服务 | 标书 Word 导出格式装配、导出阻断检查错误（`CheckBlockerError`）与快照指纹 |
| `icg/domain/generation_service.py` | 领域生成服务 | 章节 AI 建议生成与候选装配 |
| `icg/domain/outline_service.py` | 领域大纲服务 | 项目章节大纲推断与结构服务 |
| `icg/api/`、`icg/app/` | 架构骨架占位 | 仅含 `__init__.py` 说明；当前路由与装配仍在 `icg_demo/main.py`（待后续 ISSUE-038 迁移填充） |
| `icg_demo/parsing.py` | 提取服务 | 提取原件文本与分页位置 |
| `icg_demo/retrieval.py` | 检索服务 | 嵌入、重排与三条证据候选服务 |

在仓库根目录运行实际后端测试：

```powershell
& .venv\Scripts\python.exe -m pytest tests/backend -q
node --test tests/backend/demo-page.test.cjs
node --test tests/frontend/project-form.test.mjs
```

本轮已记录52项后台测试和3项前端日期/空值测试通过，旧验证页有7项事件回归记录；最终核对以实际测试记录为准。后台主流程测试覆盖两册正文隔离、原文位置、确认门禁、跨公司/只读权限、版本与重复请求保护、输入变化使旧输出失效、非法文件和扫描PDF拒绝。运行测试不会证明整套页面、完整规则或Word版式已经完成。

重启会丢失全部登录、项目、锁、草稿、版本和输出记录。当前仍没有密码验证、持久数据库、真实模型、异步恢复、生产备份、多实例协调或完整合规检查。产品高级编辑、知识库、写作配置和其他示例页面继续按任务交付；历史验收与本轮局限分别记录。

## 数值服务承诺协作

页面企业资料库维护公司模板，响应矩阵切到服务承诺，登记原文要求与项目取值。后台按单位和优劣方向计算七类结果，负责人说明风险并到事实表逐项确认，编辑台插入变量，最后检查并下载两册或内部承诺函。不同页面引用同一个值，不分别保存三份承诺。

接口位于`/api/v1/sla/templates`和`/api/v1/projects/{id}/sla/*`，写入使用公司或项目当前版本；第一次确认模板也需要本次依据。模板/来源/取值变化会使事实需复核，旧检查/下载失效；旧单章出口不能绕过项目门禁。实际119项后台与HTTP/页面证据见[验收](../../docs/testing/2026-10-10-sla.md)，完整服务时段、故障等级、语义规则与正式Word版式仍未交付。

## 本章写作输入与来源阶段

reference-writing-1新增本章事实选择/要点/字数、负责人确认、共用生成/整章建议输入及当次快照、通用事实变量检查与两册解析。独立旧demo仍保持原模式；真实端口验收运行`python backend/bid-core/smoke_writing.py --base-url http://127.0.0.1:8710`，它只创建合成本机项目，最后故意改变来源以验证失效。当前完整测试及页面证据见[写作验收](../../docs/testing/2026-10-10-writing-input.md)。完整片段、人员分配、逐段来源、全文语义、选区助手和Word正式版式继续后续任务。

最新分支复核ISSUE-034修复了片段同进程重复操作、数据库读取2048条容量边界及旧快照误删新回执；片段仍内存，数据库仍局部持久化，实机MySQL须另验。见[复核记录](../../docs/reviews/2026-10-12-foundation-review.md)。
