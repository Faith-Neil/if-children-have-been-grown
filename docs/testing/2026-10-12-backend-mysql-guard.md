为什么有这个文件：记录 QA 签署 `b20b844` 之后，守卫和密码环境变量改了什么。

它解决什么问题：避免把“任一跳过即失败”只写在工作流里，却没有一份可核对的负例。

# BE-M0-T14 守卫与密码范围

日期 2026-10-12。ISSUE-025 / BE-M0-T14。依据 QA 签署 `b20b844` 的 M2、M3。分支 `codex/repository-foundation`。

## 改动

- 守卫条件从“跳过数等于测试数”改为 `skipped > 0`。文件缺失、`tests == 0`、失败或错误仍然失败。
- `ICG_MYSQL_PASSWORD` 不再写入 `$GITHUB_ENV`。启动步骤只读密码文件。后续步骤只收到已经掩码的 `ICG_DATABASE_URL` 和 `ICG_REQUIRE_MYSQL=1`。工作流不引用 `secrets`。
- BE-M0-T11 增加验收：真实业务表进入仓库后，作业必须先 `downgrade base` 再 `upgrade head`。当前空基线不加这一步。

## 本地负例

用与工作流相同的 junit 判断，对合成 XML 运行。没有启动 MySQL。

| 输入 | 退出码 |
|---|---|
| 文件缺失 | 1 |
| tests=0 skipped=0 | 1 |
| tests=2 skipped=2 | 1 |
| tests=2 skipped=1 | 1 |
| tests=2 failures=1 | 1 |
| tests=2 errors=1 | 1 |
| tests=2 skipped=0 failures=0 errors=0 | 0 |

七项都与预期一致。守卫仍写在工作流步骤里，不是独立脚本，所以没有新增测试文件。

提交前 `node scripts/check-project-governance.cjs` 输出为：治理检查通过：228 份 Markdown、366 项任务、28 项 Issue。检查程序未改，未跑 `tests/governance`。

## 未执行

- 没有在本机启动 `mysql:8.4`。托管作业的通过次数要等这次推送的 Actions。
- 没有把 downgrade 再 upgrade 加进当前作业。
- 没有把密码或连接串写入仓库。
