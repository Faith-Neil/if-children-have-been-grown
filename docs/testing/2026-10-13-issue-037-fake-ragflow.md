为什么有这个文件：记录 ISSUE-037 / AI-04 假 RAGFlow 实际跑过的检查，以及真实地址为什么没有跑。

它解决什么问题：避免把本机假端点的通过写成已经连通公司知识库。

# 2026-10-13 ISSUE-037 假 RAGFlow

日期：2026-10-13。关联 [ISSUE-037](../../issues/ISSUE-037.md) / [AI-04](../tasks/AI-M0.md#ai-04)。ISSUE-029 仍 closed。ISSUE-037 为 in-progress。AI-04 为 in-review。AI-05 与 AI-06 为 planned。

## 怎么打开真实地址

默认不跑。需要同时满足：

```text
ICG_RUN_REAL_RAGFLOW_TESTS=1
ICG_RAGFLOW_BASE_URL=<绝对 http(s) 基址>
python3 -m pytest tests/backend/test_fake_ragflow.py::test_real_ragflow_health_when_opted_in -q
```

未设置 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 时，该测试跳过，原因是 `real RAGFlow endpoint tests require ICG_RUN_REAL_RAGFLOW_TESTS=1`。这次只打 `GET /api/v1/system/healthz`。发布文档写明该路径不需要 Authorization。真实检索还要注入 dataset id，本卡不跑，也不创建数据集。

## 命令和结果

| 检查 | 命令与结果 |
|---|---|
| 假服务 | `python3 -m pytest tests/backend/test_fake_ragflow.py -q -rs`：9 passed，1 skipped。跳过的是 `test_real_ragflow_health_when_opted_in`，原因见上 |
| 记录一致性 | `node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：340 份 Markdown、397 项任务、37 项 Issue。」检查程序未修改。计数含已并入的 REV-M0-T36 |

假服务绑定 `127.0.0.1` 的临时端口。成功用例核对 `Authorization: Bearer synthetic-ragflow-key`，以及记录下的 `base_url` 等于夹具地址。带 `/gateway` 前缀时，记录的 `base_url` 保留该前缀。空 chunks 仍是 `code` 0。业务错误是 `code` 102。HTTP 错误是状态 500。超时模式在释放前不返回。没有访问外网。

## 局限

没有调用公司内网，没有验证真实数据集、`rerank_id` 或并发。零命中记为跳过、客户端和 `retrieval.py` 接线都还没有。不加依赖。不改 OpenAPI。治理检查只核对记录是否一致。本地通过不是合入，也不是发布。
