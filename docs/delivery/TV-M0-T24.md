为什么有这个文件：记录 RAGFlow 底层物理 4 库管道、入库脱敏与参数表带表头拆行交付。

# TV-M0-T24 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 代码 | [TV-M0-T24](../code/TV-M0-T24.md) |

## 实际变更

- 前端保持「历史标书 / 资料库」双主入口；资料库页签内分「运维手册 / 故障案例 / 产品参数」三子库切换，底层对应 `${company_id}::icg-manuals / icg-fault-cases / icg-products` 三个独立 Dataset，加 `icg-history` 共四套专属画布 DSL；旧 `icg-material` 保留只读兜底兼容。
- 各管道绑定差异化切片参数与 Metadata 字段（`model` / `product_model` / `fault_category` / `section_type` / `technical_domain` / `content_role` / `reusability` / `document_type` 等）。
- 新增 `kb_preprocess.py`：历史标书入库前去实体化（旧甲方、项目名、编号、金额等替换为 `[某甲方]`/`[某项目]` 占位符，原元数据留档）；多型号参数表与 Excel/CSV 台账带表头拆行 Markdown 化，行级注入型号/故障分类元数据。
- KB 管理接口按类型路由上传，支持子库选择与型号元数据录入、重解析与四库部署状态展示；权限沿用公司管理员/授权角色。
- `fake_ragflow_v1.py` 支持 `metadata_condition` 过滤，覆盖测试边界。

## 验收证据

- `tests/backend/test_tv_m0_t24_four_datasets_preprocess.py`：16 passed。
- `frontend/web/tests/unit/kb-admin-core.test.mjs`：5 passed；前端 tsc 无错误。

## 局限

- 脱敏为规则+词典混合，罕见实体写法可能漏网（生成期仍有遮罩兜底）。
- 只用 FakeRagflow 验证；真实 RAGFlow 部署矩阵待内网复验。

## 同步

PRD、ROADMAP、ARCHITECTURE：无改动，按 [ISSUE-054](../../issues/ISSUE-054.md) 的 Wave 3 设计执行。
