为什么有这个文件：留下挂证据规则的后台测试方式。

它解决什么问题：避免只说已经拒绝过期和缺协议，却没有未设库时的通过数量。

# 2026-10-12 挂证据核对

关联 [ISSUE-033](../../issues/ISSUE-033.md)、[BE-M0-T18](../delivery/BE-M0-T18.md)。状态 in-review。只用合成数据。

## 未设置数据库

工作目录为仓库根。

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend -q
```

结果：359 passed，13 skipped。其中 12 条跳过是未设置连接串时的 mysql 标记测试，另外 1 条是未设 `ICG_RUN_REAL_MODEL_TESTS` 时的真实模型测试。新增 `tests/backend/test_evidence_mount.py` 四条：旧字段名 `restricted` 为 422 `VALIDATION_ERROR`；过期与非长期返回 409 `EVIDENCE_EXPIRED`，长期有效可以挂接；仅供参考与缺协议都是 409 `EVIDENCE_NOT_USABLE` 且说明不同；无权受限资料为 403 `FORBIDDEN`，授权用户以及公司管理员、资料管理员可以挂接。资料列表和条款 PATCH 的 `x-issue-033.x-implemented` 为 true。冻结模型 `EvidenceMountFields` 仍是 `x-implemented: false`。

原有过期检查仍在。直接挂接已经过期的资料改为 409。先挂上仍有效的资料，再把有效期改到截止日之前，项目检查仍出现 `EVIDENCE_EXPIRED`。

错误码名单没有增减。运行中的 OpenAPI 与 `spec/openapi/demo-v1.json` 在去掉尚未实现的冻结草案后一致。没有重跑 `export_openapi.py`。

## 治理

```text
node scripts/check-project-governance.cjs
```

结果：`治理检查通过：305 份 Markdown、386 项任务、35 项 Issue。` ISSUE-033 为 in-review。BE-M0-T18 为 in-review。ISSUE-035 为 new。BE-M0-T19 为 planned。ISSUE-036 保持上游 in-review。T11 仍 in-review。
