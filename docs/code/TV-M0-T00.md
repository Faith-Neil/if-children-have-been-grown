为什么有这个文件：说明工单 0 招标 RAGFlow 解析修复的入口与约束。

它解决什么问题：接手者知道为何必须重建 tender 数据集，而不是只改 embedding 字段。

# TV-M0-T00 代码说明

## 入口

- `icg/domain/tender_remote.py`：`RemoteTenderParser.ensure_dataset` / `resolve_embedding` / `explain_parse_failure`
- `icg/domain/tender_orchestrator.py`：解析失败时 `pop("remote_parse")`
- 调用链：`ParseJobRunner` → `TenderOrchestrator.parse` → `RemoteTenderParser.submit` → RAGFlow upload + `trigger_parse` + poll

## 关键约束

1. 嵌入模型取自公司 `kb_settings.embedding_model`；必须非外网（禁止 Jiekou / 公网 Gemini 等作招标临时库默认）。
2. 现有 `{company}::icg-tender` 的 `embedding_model` 与配置不一致时 **delete_datasets + create_dataset**，禁止 PUT 改嵌入（Infinity 列维度会错）。
3. 解析失败必须带可读 `warnings`；禁止把失败当 `parsed`。
4. `trust_env=False` 仍由 RAGFlow 客户端保证；业务正文不得因嵌入出网。

## 测试

`tests/backend/test_tender_remote_parse.py`：假 RAGFlow 覆盖成功、挂起续取、失败提示、嵌入不一致重建。
