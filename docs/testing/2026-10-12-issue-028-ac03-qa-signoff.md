为什么有这个文件：记录QA对ISSUE-028 AC-03（不改OpenAPI、不加依赖、create_app默认演示替身）的独立签署。

它解决什么问题：确认AI本轮夹具交付未改契约与依赖清单，默认仍走演示替身，并写明不标done。

# ISSUE-028 AC-03 OpenAPI/依赖/演示替身 QA签署（REV-M0-T30）

- 被验提交：`9e3fcdd`（假服务夹具）；AI 证据：`be3ce98`（`docs/testing/2026-10-12-issue-028-ac03-evidence.md`）；复核 tip：`be3ce98`；关联 ISSUE-028 / AI-01；数据：仅合成数据。
- 对照范围：夹具提交 `9e3fcdd`（相对其父）。**不含** tip 上 `af51151`（ISSUE-033 / BE-M0-T18）对 OpenAPI 的改动。
- 结论：**通过**。**ISSUE-028 / AI-01 / 本卡均不标 done / closed**。路径规范化与真模型仍 hold；AC-04 仍等 ISSUE-024。

## 验收对照

| 检查 | 结果 | 证据 |
|---|---|---|
| AC-03-1 本轮未改 OpenAPI | 通过 | `git show --name-only 9e3fcdd` 无 `spec/openapi/`；`git diff --stat 9e3fcdd^ 9e3fcdd -- spec/openapi/demo-v1.json` 为空。`9e3fcdd..be3ce98` 仅 `af51151` 改 OpenAPI（ISSUE-033），不计入本 AC |
| AC-03-2 未新增未批依赖 | 通过 | `requirements.txt` blob 在 `9e3fcdd^` / `9e3fcdd` / `be3ce98` 均为 `b8f91f5e896919a009f2c316079d41e77ed8c252`；夹具提交无清单改动 |
| AC-03-3 create_app 默认演示替身 | 通过 | `use_configured_model=False` 默认；未打开时 `DemoModelProvider`（`name=demo`，`is_real_model=False`）。`openai_model.py` blob 在 `9e3fcdd` 与 tip 均为 `9c7d93df31ce4cf47fcf0b9312825dcaa7eb2abb`。夹具套件 **34 passed / 1 skipped**（真模型旗） |
| 治理 | 通过 | 签署前基线（仅已入库）：306 Markdown、386 任务、35 Issue；签署提交后加本卡再跑 |

## 独立复跑命令

```text
git show --name-only --format= 9e3fcdd
git diff --stat 9e3fcdd^ 9e3fcdd -- spec/openapi/demo-v1.json backend/bid-core/requirements.txt backend/bid-core/icg_demo/openai_model.py
git diff --stat 9e3fcdd be3ce98 -- backend/bid-core/requirements.txt backend/bid-core/icg_demo/openai_model.py
git log --oneline 9e3fcdd^..be3ce98 -- spec/openapi/demo-v1.json backend/bid-core/requirements.txt
/workspace/qa-venv/bin/python -m pytest tests/backend/test_openai_compatible_model.py -q -rs
# → 34 passed, 1 skipped
node scripts/check-project-governance.cjs
```

## 观察项

- O-1：tip OpenAPI 差异只来自 `af51151`（ISSUE-033），不算进 AC-03。
- O-2：AC-04 / 配置运行时 / 真模型仍未接通。
- O-3：ISSUE-028 / AI-01 / REV-M0-T30 保持 in-review，**不标 done**。
