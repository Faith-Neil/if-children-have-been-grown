# BE-PROJECT-LIST-PAGING 交付说明


| 项目 | 内容 |
|---|---|
| Task ID | BE-PROJECT-LIST-PAGING |
| 状态建议 | in-review；建议 PM 复核后标 done |
| 关联 Issue | [ISSUE-055](../../issues/ISSUE-055.md) |
| 代码说明 | [../code/BE-PROJECT-LIST-PAGING.md](../code/BE-PROJECT-LIST-PAGING.md) |

## 实际完成

last_accessed_at、列表分页排序筛选、前端适配已实施。真实 MySQL 复测中位数：session 1047.8 → 47.2 ms，projects 1091.7 → 30.6 ms，company settings 1074.8 → 29.4 ms，workspace 1214.1 → 294.2 ms。workspace JSON 从约 1.19MB 降至 896KB，并启用 4KB 以上响应 gzip；规则内嵌重复 issues 不再随工作台重复传输，完整问题仍保留在 `check.issues`。

## 验收证据

- `test_technical_tender_ground.py` 与 `test_kb_admin.py`：34 passed。
- 索引迁移 `0015_project_hotpath_indexes` 已在真实 MySQL 执行，`alembic_version=0015_project_hotpath_indexes`；`demo_project` 四个二级索引、`demo_chapter(project_id)`、`demo_chapter_version(chapter_id)`、`demo_state_entry(scope,updated_at)` 已核实。
- `.doc` 上传测试证明转换件以 PDF 名称、PDF 内容、 `converted_from=doc` 推入 Fake RAGFlow；未连接生产 RAGFlow，未留脏文档。
- 招标检索测试证明 A/B 文档只按当前 `document_id` 召回；缺 `document_id` 时不访问远端 dataset。
- 前端 `pnpm exec tsc -b --noEmit` 通过。

## 限制与风险

测试知识库为进程内 Fake RAGFlow；真实 RAGFlow 联通性仍受既有门控控制。workspace 仍包含完整检查问题清单，超大规模项目可继续做检查明细分页；本轮未改变业务语义。PRD/ROADMAP 不改变产品范围；ARCHITECTURE 受影响点为 MySQL 作用域读取、索引、LibreOffice 与三机部署。
