为什么有这个文件：记录检索层内存骨架这次实际跑过的检查和没有覆盖的范围。

它解决什么问题：避免把合成数据上的通过结果写成已经接通 MySQL 或向量库。

# 2026-10-12 证据候选验证

日期：2026-10-12。关联 [ISSUE-016](../../issues/ISSUE-016.md) / [AI-03](../tasks/AI-M0.md#ai-03)。业务库决定为 MySQL 8，本验证没有连接它。向量库仍未选定。

## 命令和结果

| 检查 | 命令与结果 |
|---|---|
| 证据候选契约 | `python3 -m pytest tests/backend/test_evidence_candidates.py -q`：7 passed，0.03 秒 |
| 全后台 | `python3 -m pytest tests/backend -q`：300 passed，1 warning，84.33 秒 |
| 记录一致性 | `node scripts/check-project-governance.cjs`：通过。输出为「治理检查通过：148 份 Markdown、344 项任务、16 项 Issue。」检查程序未修改，因此未重跑治理测试 |

全后台 300 项包含原有 `tests/backend/test_reference_boundaries.py`。该文件本轮没有修改。新增 7 项使用合成公司 `company-alpha` 与 `company-beta`。多出的 1 项来自已经在分支上的会话测试，不是本卡新增的依赖或数据库。

既有警告一条：Starlette 提示 `httpx` 与 `TestClient` 的搭配将要弃用。它在本次改动前已经存在，本轮没有为它增加依赖。

## 契约覆盖

- 路径 A 只返回本公司已确认且不是历史类型的资料，并可附着。
- 路径 B 把更接近查询的片段排在前面，并排除其他公司、未确认和其他类型。
- 路径 C 只返回本公司历史投标，`attachable` 为 false，`reference_only` 为 true。
- 搜索缺少公司时拒绝。同一 id 再次 upsert 会覆盖旧文本。
- 知识库关闭时只有路径 A，嵌入函数未被调用。
- 路径 B 失败时保留 A 和 C，原因是 `B failed: RuntimeError`，不含查询里的“机房”。
- 路径 C 的迭代失败时保留 A 和 B。

## 局限

没有连接 MySQL 8，没有调用嵌入模型、重排模型或向量库。服务没有挂到 HTTP，因此没有浏览器或接口验收。治理检查只核对记录是否一致，不证明检索可用。本地通过不是 PR 合入，也不是发布。
