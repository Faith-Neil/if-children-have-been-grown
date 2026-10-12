为什么有这个文件：记录QA对ISSUE-016检索层内存骨架（AI-03）的独立复核。

它解决什么问题：确认检索口只做内存实现、不连库不加依赖，三条候选路径隔离公司并在失败时回退。

# ISSUE-016 检索层内存骨架 QA 签署

日期 2026-10-12（UTC+8）。签署卡 REV-M0-T16，归入 ISSUE-013。分支 `codex/repository-foundation`，被验提交 `3b629b1`，核对到 `9a079b0`。Python 为 QA 虚拟环境，数据全部合成。

## 结论

**通过。** AC-01～AC-05 满足。ISSUE-016 与 AI-03 保持 in-review，done 由项目经理设置。另记 1 项 P3 观察，不挡签署。

## 逐条核对

| 编号 | 结果 | 证据 |
|---|---|---|
| AC-01 | 通过 | `ports.py` 定义 EmbeddingProvider、RerankProvider、VectorStore 三个协议；`VectorStore.search` 必须给出 company_id、status、type（缺一抛 RetrievalError）；`retrieval.py` 各有内存实现 |
| AC-02 | 通过 | `3b629b1` 未改 `requirements.txt`（之后的改动来自 MySQL 卡 `7d97369`、`b465316`，不属本卡）；`retrieval.py` 只导入 math、zlib、dataclasses 与本地 ports；无模块引用它挂入 `create_app` |
| AC-03 | 通过 | 契约测试 7 项覆盖关闭、B 失败、C 失败。QA 补探针：向量库返回他公司记录 → B 被丢弃并记 `B failed: RetrievalError`，A、C 保留；嵌入超时 → 记 `B failed: TimeoutError`，A、C 保留 |
| AC-04 | 通过 | 以 company-beta 视角只得到 lib-b、chunk-b、hist-b；路径 C 的 `attachable` 为 false、`reference_only` 为 true；空白 company_id 被拒 |
| AC-05 | 通过 | `pytest tests/backend` 349 passed、6 skipped（均为 `mysql` 标记，本机无 MySQL，CI backend-mysql 作业另跑），含 `test_reference_boundaries.py`；本卡不新增错误码 |

## 观察项

- O-1（P3，成长AI与RAG集成）：路径 C 不按查询词过滤，查询“完全无关”时仍返回本公司全部历史投标（hist-a）。因不可附着、仅供参考，不影响隔离；建议接 RAGFlow 时补相关性过滤或在 AI-03 代码解释中写明。
