为什么有这个文件：说明怎样运行首个真实后端演示，以及它能验证哪些业务边界。

它解决什么问题：避免把内存保存、模拟建议和基础 Word 文件误当成完整生产系统。

# 本地后端演示

关联 ISSUE-006 / BE-M0-T01。Python/FastAPI 在本轮用于本地演示，正式数据库、模型、解析和部署选型仍需评审。所有预置公司、账号、项目与正文均为合成数据。

## 安装和启动

在仓库根目录运行（Windows PowerShell）：

本轮验证环境为Windows和Python 3.12.10；首次安装需要本机已有Python。其他Python版本需另行验证依赖组合。

推荐统一入口：`& .\backend\bid-core\Start-Demo.ps1 -Install`。它会创建环境、安装依赖并启动；后续启动省略`-Install`。也可使用下面的分步方法。

```powershell
python -m venv .venv
& .venv\Scripts\python.exe -m pip install -r backend/bid-core/requirements.txt
& .venv\Scripts\python.exe -m uvicorn icg_demo.main:app --app-dir backend/bid-core --host 127.0.0.1 --port 8710 --workers 1
```

浏览器打开 `http://127.0.0.1:8710/`。页面文件放在 `icg_demo/static/`，由本进程提供，浏览器资源入口为 `/static`。默认只监听本机，必须使用单进程。安装依赖需要可用的软件源或预备好的安装包；安装后运行不调用外部模型或网页资源。不要把已创建的 `.venv`、上传文件、运行日志或真实客户数据提交入库。

查看 `/health` 可确认 `repository: memory`、`model: mock`。`/openapi.json` 提供实际接口说明；默认 Swagger 和 ReDoc 页面关闭，以免离线运行依赖外部网页脚本。

## 一条可实际操作的流程

1. 选择甲公司编写人登录，打开合成项目的技术或商务章节。
2. 取得编辑权；保存草稿后刷新，本人草稿单独显示，上方先展示已提交正文。核对后可恢复草稿；基础版本落后时必须先明确处理冲突，不能直接覆盖别人修改。草稿不改变正式正文或版本。
3. 提交正式版本后，查看正文、版本列表和审计记录。
4. 请求模拟建议：后台只返回文本，没有直接修改正文。查看建议文本并确认采用后，页面仍通过正式提交接口写入。
5. 检查已提交版本；空正文或含“待补”的文字（包括 `【待补】`、`[待补]`）会阻止输出。这是演示用的简单文字检查，不判断上下文含义。
6. 检查通过后创建输出并下载真正的 `.docx`。文件明确标注“本地演示内部稿，不可正式递交”。
7. 换成只读账号验证写入被拒；换乙公司账号验证甲公司资源不可访问；经理填写理由接管后，原编写人的旧编辑权不能再保存。

## 实际接口和权限

公开接口只有合成账号列表、演示登录、健康检查和本地页面。其他 `/api` 请求必须带 `Authorization: Bearer <access_token>`。

| 路径 | 作用 |
|---|---|
| `GET /api/demo/accounts`、`POST /api/demo/login` | 选择预置账号，不是真实身份认证 |
| `GET /api/projects`、`POST /api/projects` | 查看本公司项目；新建项目自动建立技术、商务章节 |
| `GET /api/projects/{id}/chapters`、`GET /api/chapters/{id}` | 查看本公司章节、当前正式正文、有效锁摘要和本人草稿 |
| `POST /api/chapters/{id}/lock`、`/lock/renew`、`/lock/release` | 取得、续期和释放编辑权，默认有效期 120 秒 |
| `PUT /api/chapters/{id}/draft` | 带编辑凭据、正式版本号及递增序号保存草稿，拒绝乱序覆盖 |
| `POST /api/chapters/{id}/versions` | 原子提交正文、新版本、审计和重复请求结果 |
| `GET /api/chapters/{id}/versions`、`/audit` | 查看该章节实际版本与操作记录 |
| `POST /api/chapters/{id}/suggestions` | 返回模拟修改建议及其基础版本，不自动保存正文 |
| `POST /api/chapters/{id}/checks`、`/exports` | 对已提交正文做基础检查，并按有效检查创建输出记录 |
| `GET /api/exports/{id}/file` | 携带登录凭据下载文件，重新核对公司权限和正文版本 |

`editor` 和 `manager` 可以写入及创建演示内部稿；`viewer` 只读，可查看同公司正文、版本、审计与已有有效演示输出。经理接管他人会话必须填写理由，普通编写人不能接管。编辑权同时绑定账号与本次登录会话，别人的租约凭据也不能冒用。

无认证为 401，只读账号写入为 403，跨公司或不存在的资源为 404，旧版本、乱序草稿、重复请求内容冲突为 409，编辑权占用或失效为 423。字段验证失败为 422。错误统一为 `{error: {code, message}, request_id}`；响应头含 `X-Request-ID`，可用于定位请求。

重复请求标记在“账号 + 章节”内生效：同标记、同载荷返回原结果，不重复创建版本或审计；同标记、不同载荷被拒。重试仍须持有有效编辑权，已失去的编辑权不能绕过保护。

## 草稿、检查与输出的分界

检查和 Word 只取已提交正文，绑定它的版本号和内容摘要。保存草稿不改变已提交版本的检查，也不会把草稿写进输出；创建输出返回 `excludes_drafts: true`。操作页面对尚未提交的修改另行提醒。

提交新版本后，旧检查不能用于新输出，旧文件下载也会被拒。输出仅包含单个章节的简单段落，不包含完整分册排版、真实附件、敏感字段处理、完整规则或正式递交权限。ZIP/XML 校验与能生成文件不等同于 Word/WPS 版式验收。

## 可替换位置与测试入口

`icg_demo.ports.Repository` 提供 `read()` 和 `transaction(operation)`；`MemoryRepository` 用可重入锁和隔离副本执行事务，操作、返回值拷贝或提交失败都不会保留部分修改。替换为数据库时必须提供等效的原子提交和失败回滚，不能只换掉一个字典。

`icg_demo.ports.ModelProvider` 提供同步 `suggest(instruction, content) -> str`。只接收当前有权章节的正文，不直接访问或写入资料库。默认 `DemoModelProvider` 固定返回模拟建议，`provider: demo`、`is_real_model: false`。真正模型的超时、权限、敏感路由和审计需要另行实现。

`icg_demo.main.create_app(repository=None, model_provider=None, clock=None)` 可注入两个接口和可控时钟。时钟为可调用对象，返回 Unix 秒数或带时区的 `datetime`；服务实例存放在 `app.state.service`。不同应用实例默认各有独立内存，不共享状态。

在仓库根目录运行实际后端测试：

```powershell
& .venv\Scripts\python.exe -m pytest tests/backend -q
node --test tests/backend/demo-page.test.cjs
```

重启会丢失全部登录、项目、锁、草稿、版本和输出记录。本演示没有密码验证、持久数据库、真实模型、解析服务、生产备份、多实例协调或完整合规检查；它验证的是本地 HTTP 链路及几个必要失败边界。
