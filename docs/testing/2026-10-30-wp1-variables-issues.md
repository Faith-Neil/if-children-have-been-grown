为什么有这个文件：记录 WP-1 变量节点（APP-M2-T164）与问题标注联动（APP-M2-T166）的验证方式与局限。

它解决什么问题：说明跑了哪些测试、在什么环境，以及哪些没有验证。

# WP-1 变量节点与问题联动验证（2026-10-30）

## 环境
- Windows 本机，Python 后端内存仓储（`create_app()`），Node 24，Playwright Chromium headless shell。
- 未连 MySQL；MySQL 套件由 CI 的 mysql 作业运行。
- 未调用真实模型；变量解析不调用模型。

## APP-M2-T164 变量节点
| 验证 | 命令 | 结果 |
|---|---|---|
| 后端变量节点 | `python -m pytest tests/backend/test_variable_nodes.py` | 3 passed |
| 受影响的旧用例 | `python -m pytest tests/backend/test_sla.py tests/backend/test_generation_context.py` 等 7 个文件 | 106 passed |
| 后端全量 | `python -m pytest tests/backend -q` | 改前 9 failed、1075 passed；9 项逐项处理后受影响文件全部通过，全量以 CI 为准 |
| 前端单测 | `pnpm --dir frontend/web test` | 556 passed |
| 类型检查与构建 | `pnpm --dir frontend/web lint`、`build` | 通过 |
| 浏览器 | `playwright test variable-nodes` | 1 passed |

浏览器用例第一次运行时发现：变量类 409 被编辑台当成版本冲突，弹出合并弹窗。已在 `editor-conflict.ts` 排除，重跑通过。

## 本机真实 RAGFlow 的一次误写
本轮用户提供了本机 RAGFlow 地址与 API Key。探测连通性时把这两个变量留在了同一个终端，随后运行的后端全量测试有用例把合成资料同步到了真实服务（数据集 `alpha::icg-library`，4 份 `library__evidence-*.md`）。已当场删除这 4 份文档，数据集内剩 0 份；用户的 `test` 数据集未被写入。

为防再犯，`tests/backend/conftest.py` 在未设置 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 时清掉 `ICG_RAGFLOW_BASE_URL`、`ICG_RAGFLOW_API_KEY`、`ICG_RAGFLOW_API_KEY_ENV`。

连通性结果：`GET /api/v1/datasets` 200，数据集 `test` 2 份文档、521 个切片，嵌入模型 `gemini-embedding-001`（公网模型，生产须换内网嵌入模型）；`POST /api/v1/retrieval` 200，返回 3 条。

## 局限
- 编辑中的文本框内变量仍显示原文，只在框下方变量栏显示取值。
- 三种宽度截图未做（属 T160）。
