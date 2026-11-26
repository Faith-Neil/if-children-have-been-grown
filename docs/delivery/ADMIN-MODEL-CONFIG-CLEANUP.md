# ADMIN-MODEL-CONFIG-CLEANUP 交付说明

## 实际修改
- 模型配置弹窗移除 temperature、timeout、max_tokens 假开关，保留连接、模型名、密钥、本地/涉密属性、连通性测试与绑定。
- 平台 system 任务模型路由可作为公司运行时兜底，项目绑定仍执行敏感项目本地模型门禁。

## 验证
- `pytest tests/backend/test_admin_rbac_security_cleanup.py -q`：8 passed，覆盖平台接口 403、跨租户用户/审计隔离、弱密码、登录锁定、会话过期、解析/技术卷任务 demo_job 进度与取消/重试语义。
- `pytest tests/backend/test_parse_jobs.py tests/backend/test_generation_session.py -q`：23 passed，用时 38.29s；此前组合卡死根因是测试替身的模型目录提示词契约过期及后台线程等待，已修正并稳定收尾。
- 聚焦回归 `test_admin_rbac_security_cleanup.py + test_generation_session.py + test_parse_jobs.py + mysql_gate + technical_rag + technical_digest + TV-M0-T28/T29/T30`：109 passed，用时 80.76s。
- `pnpm --dir frontend/web exec tsc -b --noEmit`：通过。
- `ICG_ALLOW_MEMORY=1 python backend/bid-core/export_openapi.py --check`：通过。

## 状态
- 任务进入 in-review；按治理纪律仍建议 QA/PD 复核后由 PM 标 done，不合并 PR。
