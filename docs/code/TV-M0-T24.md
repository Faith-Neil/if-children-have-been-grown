为什么有这个文件：解释 TV-M0-T24 四物理库管道、入库脱敏与参数表拆行的代码。

# TV-M0-T24 代码说明

| 文件 | 说明 |
|---|---|
| [ragflow_pipelines.py](../../backend/bid-core/icg/infra/ragflow_pipelines.py) | `icg-history / icg-manuals / icg-fault-cases / icg-products` 四套画布 DSL 与差异化切片参数、Metadata 字段矩阵 |
| [kb_preprocess.py](../../backend/bid-core/icg/domain/kb_preprocess.py) | 历史标书去实体化（旧甲方/项目名/编号/金额→占位符，原元数据留档）；参数表与台账带表头拆行 Markdown 化并提取行级 `model`/`fault_category` |
| [knowledge_base.py](../../backend/bid-core/icg/domain/knowledge_base.py) | `MATERIAL_SUBKINDS` 常量与别名、四库索引登记、`search()` 透传 `metadata_condition`/`max_chunks_per_doc`、命中携带 `meta_fields` |
| [kb_admin.py](../../backend/bid-core/icg/domain/kb_admin.py) / [api/kb_admin.py](../../backend/bid-core/icg/api/kb_admin.py) | 四类数据集部署/上传路由、子库元数据录入、重解析与状态展示 |
| [fake_ragflow_v1.py](../../tests/backend/fake_ragflow_v1.py) | 检索端 `metadata_condition` 条件求值（is/not is/contains/in 等），覆盖四库测试边界 |
| [kb-admin-core.ts](../../frontend/web/src/library/kb-admin-core.ts) / [KnowledgeBaseAdminPage.tsx](../../frontend/web/src/library/KnowledgeBaseAdminPage.tsx) | 资料库页签三子库切换、型号元数据录入、四库部署状态 |
| [test_tv_m0_t24_four_datasets_preprocess.py](../../tests/backend/test_tv_m0_t24_four_datasets_preprocess.py) | 四库部署、脱敏、拆行与元数据断言（16 passed） |
