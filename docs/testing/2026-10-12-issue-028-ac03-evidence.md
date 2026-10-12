为什么有这个文件：给 QA 一份可复跑的证据，用来勾选 ISSUE-028 AC-03。

它解决什么问题：避免把别的提交改过的 OpenAPI 算进假服务这一轮，或把 AC-03 写成已经勾选。

# 2026-10-12 ISSUE-028 AC-03 证据

日期：2026-10-12。关联 [ISSUE-028](../../issues/ISSUE-028.md) / [AI-01](../tasks/AI-M0.md#ai-01)。AC-02 已由 [REV-M0-T29](../delivery/REV-M0-T29.md) 签署，记录在 [AC-02 签署](2026-10-12-issue-028-ac02-qa-signoff.md)。本文件只准备 AC-03（不改 OpenAPI 文件，不新增依赖）。**待 QA 勾选。** ISSUE-028 与 AI-01 仍为 in-review，不标 done，不标 closed。

ISSUE-024 与 AC-04 仍等待。路径规范化 hold，不改 `backend/bid-core/icg_demo/openai_model.py`。真模型冒烟另计，默认仍须 `ICG_RUN_REAL_MODEL_TESTS=1`。

## 对照范围

| 提交 | 说明 |
|---|---|
| `9e3fcdd8f60ec4e751336c55154cbf9b9bae1e35` | 假服务提交。AC-03 看这一笔 |
| `20f2b9254957fae578ef4d126e9c1e3d21c778e1` | 写本证据时的分支尖端。用来确认依赖和适配器之后也没被夹具改动 |
| `af51151c734da9947ecf6fbea4b61565e20f420c` | 尖端相对夹具提交的 OpenAPI 差异只来自这一笔（ISSUE-033 / BE-M0-T18）。不属于 AC-03 |

`9e3fcdd` 的 `git show --name-only` 只有文档、`pytest.ini`、`tests/backend/conftest.py`、`tests/backend/fake_openai_chat.py` 和 `tests/backend/test_openai_compatible_model.py`。没有 `spec/openapi/demo-v1.json`，没有 `backend/bid-core/requirements.txt`，没有 `openai_model.py`。

## QA 检查步骤

在仓库根执行。空 diff 表示该路径没有变化。

```text
git show --name-only --format= 9e3fcdd8f60ec4e751336c55154cbf9b9bae1e35
git diff --stat 9e3fcdd8f60ec4e751336c55154cbf9b9bae1e35^ 9e3fcdd8f60ec4e751336c55154cbf9b9bae1e35 -- spec/openapi/demo-v1.json backend/bid-core/requirements.txt backend/bid-core/icg_demo/openai_model.py
git diff --stat 9e3fcdd8f60ec4e751336c55154cbf9b9bae1e35 20f2b9254957fae578ef4d126e9c1e3d21c778e1 -- backend/bid-core/requirements.txt backend/bid-core/icg_demo/openai_model.py
git log --oneline 9e3fcdd8f60ec4e751336c55154cbf9b9bae1e35^..20f2b9254957fae578ef4d126e9c1e3d21c778e1 -- spec/openapi/demo-v1.json backend/bid-core/requirements.txt
python3 -m pytest tests/backend/test_openai_compatible_model.py -q -rs
node scripts/check-project-governance.cjs
```

## 本次核对结果

| 检查 | 结果 |
|---|---|
| `9e3fcdd` 相对其父提交 | `spec/openapi/demo-v1.json`、`backend/bid-core/requirements.txt`、`openai_model.py` 的 diff 为空 |
| 依赖 blob | `backend/bid-core/requirements.txt` 在 `9e3fcdd^`、`9e3fcdd` 与尖端 `20f2b92` 都是 `b8f91f5e896919a009f2c316079d41e77ed8c252` |
| 适配器 blob | `openai_model.py` 在 `9e3fcdd` 与尖端都是 `9c7d93df31ce4cf47fcf0b9312825dcaa7eb2abb`。本轮不改运行代码 |
| 尖端 OpenAPI | `9e3fcdd..20f2b92` 只有 `af51151` 改了 `spec/openapi/demo-v1.json`（202 行增、8 行删）。那是挂证据，不是假服务 |
| 夹具测试 | `python3 -m pytest tests/backend/test_openai_compatible_model.py -q -rs`：34 passed，1 skipped，1 warning。跳过原因是 `real model endpoint tests require ICG_RUN_REAL_MODEL_TESTS=1` |
| 治理 | `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：306 份 Markdown、386 项任务、35 项 Issue。」检查程序未修改 |

AC-02 的全后台 355 passed / 13 skipped 与 CI run 38231417634 记在 REV-M0-T29，本文件不重签 AC-02。
