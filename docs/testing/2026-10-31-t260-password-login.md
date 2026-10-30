为什么有这个文件：记录 APP-M2-T260 口令登录补齐的验证方式、结果与局限。

它解决什么问题：说明哪些在本机跑过、哪些只在 CI 跑过，以及 CI 第一次失败的原因和处理。

# APP-M2-T260 口令登录验证（2026-10-31）

## 环境
- 开发沙箱：无外网，装不了 FastAPI、SQLAlchemy 与前端依赖。只能运行不依赖 antd/react 的前端单测（Node 22，借用全局 typescript）、治理检查和 Python 语法编译。
- 后端全量、MySQL、类型检查与构建、浏览器用例均在 GitHub Actions `offline-check` 上运行（托管 Ubuntu，Python 3.13.5，Node 24.9.0，MySQL 8.4 容器，Playwright Chromium）。
- 不调用模型与 RAGFlow。

## 契约导出
本机不能运行 `export_openapi.py`。backend 作业新增一步：把代码导出的契约写到运行器临时目录并上传为 `openapi-regenerated` 产物，不改仓库文件。开发机下载后替换 `spec/openapi/demo-v1.json`，再由同一作业的 `--check` 核对。本卡新增 6 个路径（auth/logout、auth/password、auth/password-policy、branding、companies、companies/{id}/status）和 8 个模式，修改 auth/login 的响应与错误声明。

## 结果
| 验证 | 命令 / 位置 | 结果 |
|---|---|---|
| 本机前端单测 | `node --test tests/*.test.mjs tests/**/*.test.mjs` | 改前 524 通过 5 失败；改后相同；5 项失败均为本机缺 antd/react，与本卡无关 |
| 本机新单测 | `password-change.test.mjs`、`application-session.test.mjs` | 6、15 通过 |
| 本机治理 | `node scripts/check-project-governance.cjs`、`node --test tests/governance/*.test.cjs` | 通过、12 通过 |
| CI 第一次（`92b63ef`） | offline-check | frontend、governance、backend-mysql 通过；backend 31 项失败；e2e 2 项失败 |
| CI 第二次（`294648d`） | offline-check | backend、backend-mysql、frontend、governance、e2e 五个作业全部通过（含 `test_password_login.py` 8 项、`password-login.spec.ts` 2 项） |

## 第一次 CI 失败的原因与处理
- **登录写审计破坏章节审计**：新增的登录、登录失败事件写进 `state.audit`，没有 `chapter_id`，章节审计接口 `event["chapter_id"]` 报 KeyError（`test_demo.py` 16 项、`test_version_rollback.py` 1 项）；`test_project_assignments.py` 8 项在失败写入前后比较整个 `state.audit`，中间的登录事件让比较不相等。处理：账号与公司安全事件改存 `security_audit`；章节审计接口改用 `.get`。
- **OpenAPI 未重新导出**（4 项）：按上节方式更新。
- **旧用例断言旧提示文字**（1 项）：改为逐项措辞。
- **e2e 用例 1**：改密页的“退出登录”按钮被 `getByRole('button', { name: '退出' })` 按包含匹配到，改为精确匹配。
- **e2e 用例 2**：平台超级管理员在浏览器里登录后会话被前端判为无法核验，退回登录页。这是已有缺陷：前端只接受公司范围会话，`admin` 的会话是 system 范围。已修复并补单测。

## 局限
- 本机未运行任何后端测试和浏览器用例，以 CI 为准。
- 未在 Windows 与内网 MySQL 上复测；未在生产模式（`ICG_ENV=production`）下手工走一遍 `admin` 首次登录改密。
- 品牌接口只验证了默认值；品牌页（T033/T034）未做。
