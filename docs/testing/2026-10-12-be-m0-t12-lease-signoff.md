为什么有这个文件：记录QA对BE-M0-T12编辑租约入库（09ada43，ISSUE-018）的签署。

它解决什么问题：证明在真实 MySQL 上，跨进程和重启后，续期、过期接管、释放都成立。

# BE-M0-T12 编辑租约入库 QA签署（REV-M0-T19）

- 被验提交：`09ada43`；复核基线：`ae91024`；MySQL 8.4 本地，`ICG_REQUIRE_MYSQL=1`；数据：仅合成数据。
- 结论：**通过**。按项目经理的要求，`chapter_lease` 是演示期过渡表，只验行为，不按字典逐字段核对。

## 证据

- `pytest -m mysql`：选中 8 个，8 个通过（新增的 `test_mysql_leases.py` 两条测试带 `pytestmark = pytest.mark.mysql`）。不连数据库：351 个通过，8 个跳过，内存路径不受影响。
- QA 探针 `qa-tools/lease_live.py`：每一步都开一个新的 Python 进程，等于每一步都重启一次：
  - alpha-editor 取得租约，返回 200，库里记一行，过期时间约 120 秒后；
  - alpha-manager 在租约有效时来取，返回 409 `TAKEOVER_REASON_REQUIRED`；
  - 编写人在新进程里续期，返回 200，占用人不变，`expires_at` 推后；
  - 在新进程里释放，返回 200 `released`，库里那一行删掉；
  - alpha-manager 释放后取得，返回 200；
  - 手动把 `expires_at` 改到 2000 年（模拟过期）后，alpha-editor 接管，返回 200；
  - 被接管的一方再续期，返回 423 `LOCK_LOST`。
- CI：09ada43 的 run 38216199622、2439616 的 run 38217405067、ae91024 的 run 38217677190，五个 job 全部 success，backend-mysql 都是 `tests=8 skipped=0`。

## 观察项

- O-1（P3）：持久化方案第 5 节"字典 v1.9 字段对照表"已经有了，但还缺"偏差已获 PM 有条件批准，待 ISSUE-032 对齐"这句备注，等后端下一个提交补上（不阻塞）。
- O-2（P3）：MySQL 测试没覆盖释放，释放这一项只由 QA 探针验证过。
