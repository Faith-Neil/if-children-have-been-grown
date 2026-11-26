为什么有这个文件：记录 TV-M0-T28 导出净化、偏离表兜底、防截断续写与最终真机闭环的实际完成内容、验收证据与遗留问题。

# TV-M0-T28 交付说明

| 项 | 内容 |
|---|---|
| 状态 | done（PM 已依据 `.audit/final-round-v2/` 拆包复核签收） |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 代码说明 | [TV-M0-T28](../code/TV-M0-T28.md) |


<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | TV-M0-T28 |
| 代码解释 | [代码说明](../code/TV-M0-T28.md) |
| 验收 | `.audit/final-round-v2/` 三件套拆包复核通过；history 12/12 命中、串标/脏标记/负偏离为零，PM 已签收。 |
| 项目进度 | done（PM 已拆包复核签收）；ISSUE-054 技术卷质量升级继续推进。 |
<!-- task-delivery:end -->

## 一、完成内容（实施中记录）

1. 统一技术卷 Prompt 与后处理边界：常规交付物/报告/标准协议名由模型直接命名；真实私有事实缺口使用 `[待人工补充：具体项]`；`scrub()` 不再把未在招标来源出现的书名号名称暴力挖成 `【待补】`，外项目实体遮罩为语义完整的“相关机构”。
2. 扩充商务/资格/格式条款网关：联合体、转包分包、投标文件份数、报名材料、资格条件、投标有效期、保证金等进入拦截词表，并在三张清单 digest 输入侧统一过滤。
3. 偏离表：样表识别兼容「偏离说明表」，修复表头自身含“偏离说明表”导致漏抽；无样表时稳定使用标准 5 列模板导出独立《技术偏离表.docx》；条款长表头防列错位，响应列继续单向提炼自本标最终正文。
4. 截断续写：本地 Qwen 非流式与流式直连探针均确认 `finish_reason=length` 正确透出；章节权重 profile 已修正为真实传入模型调用，捕获 `finish_reason` 并在未闭合逗号/顿号/截断结尾或 length 时自动续写；续写失败时删除未闭合短尾，不交付半句。
5. 导出审计件净化：技术追溯表剔除 rejected/商务格式条款；历史标书知识来源统一脱敏为“历史标书参考（已脱敏）”；导出 Word 前剥离 `**` 强调源码但保留文字。
6. 审计与防复发：分路审计 `routes[].query` 记录实际完整查询词，fallback 后改写为实际生效 query；陈旧 `document_id` 在检索归零后校验并标记重同步提示，带 5 分钟缓存避免每节重复探测；非测试环境缺 `ICG_DATABASE_URL` 启动直接报错，禁止静默回落内存仓储。

## 二、当前验证证据

- `tests/backend/test_tv_m0_t28_export_deviation.py`：22 passed。
- `tests/backend/test_technical_rag.py` 与 T28 合计：39 passed。
- `tests/backend/test_technical_digest.py` + T28 + technical_rag + mysql_gate 合计：55 passed。
- 昆明航空 `.docx` 本地解析复核：LocalTextParser 得到 16 个按显式分页符划分的逻辑页，不是 Word 渲染的 64 个物理页；`extract_pages_read=5` 是模型成功读完的抽取块数，不是只读 5 页。样表漏抽根因是表头行本身包含“偏离说明表”被误判为下一张样表标题；修复后 `find_samples` 能抽出《十、项目详细需求偏离说明表》及 5 列表头。
- 直连本地 Qwen 探针：`max_tokens=5` 非流式与流式响应均返回 `finish_reason: length`。
- 本项目存量目录曾含商务条款章节，已通过正式 API 将 11 条商务/资格/格式条款从技术卷拒绝；随后用新增隐藏运维端点 `POST /technical-outline/rebuild-model` 在本项目重跑真实本地模型目录编排，返回 `ok=true / outline_source=model / tree_model_failed=false / headings=12`，12 个目录标题商务命中为 0。

## 三、最终真机闭环实证

目标项目 `project-78884aacf9e546fdaa6871ae06510662`，最终生成 revision 28，导出 revision 29；报告与三件套保存于 `.audit/final-round-v2/`。

1. 目录：`outline_source=model`、`tree_model_failed=false`、12 个目录标题，商务/资格/格式命中 0；生成 12/12 节，`failed=[]`，用时 620.6 秒。
2. 模型：`qwen3:30b-a3b-instruct-2507-q4_K_M`，`is_real=true`、`is_local=true`。
3. history 路：12/12 条审计 `status=ok`、`post_filter_hits=5`、`raw_hits=5`、`query` 非空。
4. 串标扫描：`technical.docx`、`技术偏离表.docx`、`response-trace-technical.xlsx` 对甘肃/农信/安康/星河/华为/浪潮/中兴/历史做法全部 0 命中。
5. 正文：`technical.docx` 35061 字符，`【待补】=0`、脏标记/Markdown 源码 0、逗号截断 false；`[待人工补充]` 10 处，均属需人工核对的企业/项目私有事实缺口，不再是通用交付物名称。
6. 偏离表：识别并沿用招标附件《十、项目详细需求偏离说明表》5 列表头；96 条技术条款行，`无偏离=96`、`负偏离=0`、外来厂商/历史做法 0。
7. 追溯表：96 行技术条款，商务/资格/格式命中 0，外来历史文件名 0；历史知识来源以“历史标书参考（已脱敏）”呈现。
8. 文件字节：`technical.docx` 58584、`技术偏离表.docx` 11185、`response-trace-technical.xlsx` 16516。

建议 QA 与 PD 复核上述实证后，由 PM 决定是否标 done；开发者不自行标 done。

## 四、测试与局限

- `test_tv_m0_t28_export_deviation.py`：24 passed。
- mysql_gate / technical_digest / technical_rag / T28 聚合复测：mysql gate 已转绿；`test_technical_sources.py` 仍有 4 个旧规则分组期望失败，失败点在旧测试要求“健康检查+故障处理”必须合并为“运维保障与巡检”等规则目录细节，不影响本轮真实模型树闭环，需后续单独校正旧测试或规则分组。
- `node scripts/check-project-governance.cjs` 预检查通过：832 份 Markdown、492 项任务、54 项 Issue。
