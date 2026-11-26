为什么有这个文件：说明 TV-M0-T28 导出净化、偏离表兜底、防截断续写与最终真机闭环的代码改动位置与设计理由。

# TV-M0-T28 代码说明

| 项 | 内容 |
|---|---|
| 状态 | in-progress |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 交付 | [TV-M0-T28](../delivery/TV-M0-T28.md) |

## 一、Prompt 与实体遮罩

- `icg/domain/technical_volume.py::SECTION_SYSTEM`：本标事实不得用占位符代替；通用交付物直接规范命名；仅真实私有事实缺口写 `[待人工补充：具体项]`。
- `icg/domain/technical_volume.py::scrub`：删除“书名号不在招标来源就替换成【待补】”的暴力后处理，避免制造缺宾语病句；只做“其他项目→同类项目”的完整语义替换。
- `icg/domain/writing_knowledge_prompt.py`：历史知识提示改成省略或概括为“相关机构/同类项目”，`FOREIGN_NAME_PLACEHOLDER` 从 `【待补】` 改为 `相关机构`。

## 二、商务网关

- `icg/domain/technical_constraint_context.py`：扩充 `_BUSINESS_MARKERS`，覆盖联合体、转包分包、投标文件份数、报名材料、资格条件、投标有效期、保证金、正副本等。
- `icg/domain/technical_digest.py::_rows`：三张清单输入侧统一调用 `row_is_non_tech` 过滤，拦截结果写入 `business_intercepted_requirements`，防止商务/格式条款进入目录与正文任务。
- `icg/domain/technical_digest_outline.py`：目录模型 Prompt 明确商务/资格/格式条款不得成章。

## 三、偏离表样表与兜底

- `icg/domain/technical_volume.py::find_samples`：识别「偏离说明表/偏差说明表」；含竖线的表头优先按表头处理，即使其中出现“偏离说明表”也不再误判为下一张样表标题；中文编号附件标题视为附件样表。
- `table_rows`：按 `requirement_ids` 全量发射行，矩阵检索失败不再导致条款漏行；序号使用表格自然序号。
- `_cell`：章节/页码列优先；长条款表头先按条款列填充，防止被其中“偏离”二字带偏；响应列仍由 `_content_response` 从本标最终正文提炼。
- `export_parts`：无论是否抽到样表都产出独立《技术偏离表.docx》；无样表使用 `FALLBACK_DEVIATION_SAMPLE` 标准 5 列模板。

## 四、截断续写

- `icg/infra/openai_model.py`：非流式与流式均捕获 `finish_reason`，并写入模型审计响应记录。
- `technical_volume.py::_complete_section`：修复章节权重 profile 被硬编码为 `SECTION_CALL` 的问题，core/brief 档位真正生效。
- `produce_section`：`finish_reason=length` 或 `_unclosed_tail` 触发续写；续写为空/失败时用 `_trim_unfinished_sentence` 删除末尾未闭合短行或退到最近句读，避免「所有承诺，」式半句进入导出。

## 五、模型目录重触发与导出审计件净化

- `tender_orchestrator.py::rebuild_technical_outline_model` + `/technical-outline/rebuild-model`：在既有项目上用当前三张清单重跑真实本地模型目录编排；不清空正文、不重抽条款，明确返回 `outline_source/model` 或失败原因，并有技术卷写入权限校验。
- `export_sanitizer.py::normalize_markdown_noise`：导出 Word 前剥离 `**` 强调源码但保留文字，避免 Markdown 标记裸露。
- `response_trace.py`：技术追溯表剔除 rejected/商务格式条款；响应句先做 Markdown 噪声净化；历史标书知识来源统一显示为“历史标书参考（已脱敏）”，防止其他业主文件名进入本标审计件。

## 六、审计、陈旧索引与数据库门禁

- `icg/domain/technical_rag.py`：`routes[].query` 记录实际完整查询词；意图拆解 query 回落后改写为实际生效 query。
- `icg/domain/knowledge_base.py::_mark_stale_document_ids`：检索归零后核对 RAGFlow 数据集中仍存在的 document_id；陈旧索引标 failed 并提示重新同步，缓存 5 分钟避免每节重复探测。
- `icg/infra/mysql_gate.py`：仅 pytest 或显式 `ICG_ALLOW_MEMORY=1` 允许内存仓储；普通启动缺 `ICG_DATABASE_URL` 直接 RuntimeError。

## 七、验证脚本

- `scripts/final_round_v2.py`：驱动既有昆明航空项目技术卷流式全量生成、主流程导出、下载 `technical.docx` / `技术偏离表.docx` / `response-trace-technical.xlsx`，并输出 history 分路、商务目录、串标、占位符、脏标记与截断扫描报告。
