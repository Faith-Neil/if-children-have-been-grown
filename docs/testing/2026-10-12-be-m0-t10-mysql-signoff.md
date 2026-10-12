为什么有这个文件：记录QA对ISSUE-018首张卡（MySQL连接与空Alembic基线，BE-M0-T08/T10，依赖登记ISSUE-023）的独立复跑与签署结论。

它解决什么问题：项目经理标done前有真实MySQL 8上的可核对证据，而不是只看开发者自报。

# BE-M0-T08 / BE-M0-T10 QA签署复核（真实MySQL 8.4）

ISSUE-013 / REV-M0-T09；关联[ISSUE-018](../../issues/ISSUE-018.md)、[ISSUE-023](../../issues/ISSUE-023.md)。执行人成长测试QA；复核提交 `7d97369`。环境：Linux、Python 3.13、Node v24.9.0、pnpm 11.25.0。只读复核，未改两张卡的代码或状态；done由项目经理设置。

## 结论

- BE-M0-T10（连接配置与迁移骨架）：**通过**。
- BE-M0-T08（持久化方案）：文档齐全，**通过**（只核对方案与交付文档，本卡不含代码）。
- ISSUE-023（依赖登记）：**有条件通过**，见Q1。
- 无阻断缺陷。

## MySQL 准备方式

QA机无docker。下载官方 `mysql-8.4.6-linux-glibc2.28-x86_64-minimal` 压缩包，apt 安装 `libaio1t64` 并在临时库目录里软链为 `libaio.so.1`；`--initialize-insecure` 后只监听 127.0.0.1:33061，`--mysqlx=OFF`。建库 `icg`（utf8mb4 / utf8mb4_0900_ai_ci），专用账号 `icg`@127.0.0.1，密码由 `secrets.token_urlsafe` 随机生成，只经环境变量传入，未写入仓库或日志。

## 复跑（无数据库环境变量）

| 项目 | 结果 |
|---|---|
| 后台 pytest | 320 passed，2 skipped（两条 mysql 用例跳过），与自报一致 |
| `session_live_http.py` | 15/15 |
| `qa_error_idempotency_live_http.py` | 47/47 |
| `smoke_t06.py` | 12/12 |
| 前端构建 | 通过（首屏 index 316.53 kB） |
| 前端 `.mjs` | 78/78 |
| `.cjs` | 35/35 |
| 治理检查 | 通过 |
| Actions run 38205644760（headSha 7d97369） | completed / success：frontend、backend、governance、e2e 全部 success |

## 真实 MySQL 8.4.6

- `alembic upgrade head` → `0001_baseline (head)`；`downgrade base` → 无版本；再 `upgrade head` → `0001_baseline (head)`。往返通过。
- `ICG_REQUIRE_MYSQL=1 ICG_DATABASE_URL=mysql+pymysql://…?charset=utf8mb4 pytest tests/backend -m mysql`：**2 passed**。
- 经应用的 engine 查询：`@@character_set_connection=utf8mb4`、`@@collation_connection=utf8mb4_0900_ai_ci`，client/results 也为 utf8mb4；库默认 utf8mb4 / utf8mb4_0900_ai_ci；`SHOW TABLES` 只有 `alembic_version`。
- 不设 URL 运行 alembic：`RuntimeError: ICG_DATABASE_URL is required…`，退出非0。

## 门禁：要求 MySQL 时失败而非跳过

| 场景（均 `ICG_REQUIRE_MYSQL=1 pytest tests/backend -m mysql`） | 结果 | 退出码 |
|---|---|---|
| 不设 URL | 2 failed（门禁消息），无 skip | 1 |
| 端口不可达 127.0.0.1:1 | 15 个收集错误 | 2 |
| 错误密码 | 15 个收集错误 | 2 |
| 不可路由地址 10.255.255.1 | 15 个收集错误，耗时约50秒 | 2 |

均不是跳过、退出码非0，满足验收。但URL已设而连不上时，测试模块在导入期调用 `create_app()` 就因连库失败而报收集错误，门禁的可读原因没有出现（见Q2）。

## 密码不泄露

- 带正确URL启动 uvicorn（debug 日志）：`/health` = `{"status":"ok","mode":"local-demo","repository":"mysql","model":"mock","persistent":false,"single_process":true}`。
- 带错误密码启动 uvicorn：启动失败退出1，报 `(1045, "Access denied for user 'icg'@'localhost' (using password: YES)")`。
- 在两次 uvicorn 日志、`/health` 正文、`/api/v1` 错误正文、alembic 错误输出、pytest 门禁输出、mysqld 日志中搜索真实密码和错误密码：**0 次命中**。
- `repr(engine)` 与 `str(engine.url)` 均为 `mysql+pymysql://icg:***@…`，密码已遮蔽。

## 依赖

- `requirements.txt`：`alembic~=1.14.1`、`PyMySQL~=1.1.3`、`cryptography~=50.0.2`、`sqlalchemy~=2.0.54`，按批准的次版本兼容发行锁定；传递依赖 Mako 1.4.3、greenlet 3.5.6、cffi 2.1.1、pycparser 3.11 精确锁定，与安装结果一致。
- 其他依赖文件（前端 package.json / lock）未改。ISSUE-023 类型为 version，已在 issues/index 登记。
- 测试只新增（conftest 钩子、`test_mysql_connection.py`、`test_mysql_gate.py`），没有删除或放宽既有用例。

## 文档与状态

`docs/delivery|code/BE-M0-T08.md`、`docs/delivery|code/BE-M0-T10.md` 均存在；BE-M0-T08、BE-M0-T10、ISSUE-023 为 in-review。PRD、ROADMAP、ARCHITECTURE、WORKFLOW 未改；PROJECT_BRIEF 改动已登记在 ISSUE-018 与 ISSUE-023 同步表。

## 缺陷与缺口

| 编号 | 现象 | 位置 | 严重程度 | 建议负责人 |
|---|---|---|---|---|
| Q1 | Mako 的安装依赖 MarkupSafe（本机 3.0.4）没有锁进 `requirements.txt`，与“传递依赖已精确锁定”的说法不符，重建环境时版本会漂移 | `backend/bid-core/requirements.txt`、ISSUE-023 | 轻微 | 成长后端开发 |
| Q2 | 已设 URL 但连不上时，pytest 报模块收集错误而不是门禁的 failed，原因被堆栈淹没；不可路由地址时每个模块各等3秒，总计约50秒 | `icg_demo/database.py`、测试模块导入期 `create_app()` | 轻微（退出码仍非0，满足验收） | 成长后端开发 |
| Q3 | ISSUE-018 同步表“依赖与CI”一行仍写“均未加入”，已被本次提交改变，未更新 | `docs/governance/ISSUE-018-sync.md` | 轻微（文档） | 成长后端开发 |

未验证：业务数据入库（本卡仍委托内存仓库，`persistent:false`）、多进程、TLS 连接。
