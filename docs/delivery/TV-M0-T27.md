为什么有这个文件：记录 TV-M0-T27 真机高危加固五项与端到端真机验收修复的实际完成内容、验收证据与遗留问题。

# TV-M0-T27 交付说明

| 项 | 内容 |
|---|---|
| 状态 | in-review（建议 PM 在 QA/PD 签署后标 done） |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 代码说明 | [TV-M0-T27](../code/TV-M0-T27.md) |

## 一、完成内容

### 1. 验收前五项真机加固（用户点名）

| # | 加固项 | 落地 |
|---|---|---|
| 1 | metadata_condition 零命中逐级放宽 | `technical_rag.py`：协议收敛 `_sanitize_metadata_condition` + 型号变体 `_model_variants` + 放宽阶梯 `_metadata_fallback_ladder`（精确型号→变体OR→doc_type级→不过滤）；history 排他条件永不放宽 |
| 2 | 历史标书脱敏防误伤 | `kb_preprocess.py`：内置厂商品牌白名单 + `deid_allow`/`bidder_name` 用户元数据放行；DOCX XML 级替换不动标题层级 |
| 3 | 轻调用参数与并发可配 | `openai_model.py` 核验确认不透传 thinking_budget；`ICG_SECTION_CONCURRENCY` 环境变量（默认 2，原硬编码 3） |
| 4 | 核验器防假阳性 | `technical_verifier.py`：国家级部委/标准机构白名单 + 自否定语境过滤 |
| 5 | 占位配置清理 | `ragflow_config.py` 占位 dataset_ids 检测 + 建议 ID 回填；前端告警与一键回填；`scripts/real-acceptance-smoke.sh` 一键门控冒烟 |

另完成 antd 废弃告警清理：`bodyStyle`→`styles.body`、`destroyOnClose`→`destroyOnHidden`、`addonAfter`→共享组件 `frontend/web/src/shared/UnitInputNumber.tsx`、静态 message→`App.useApp()`，tsc 零错误。

### 2. 端到端真机验收驱动的修复（R1/R2/R3 三轮）

- **密钥轮换失配恢复**（运维侧）：RAGFlow key 与模型密钥因 SECRET 轮换无法解密全部静默失效；从 rag_flow MySQL 找回真实 key 重存，密钥持久化于 `backend/bid-core/data/local-secret.key`。
- **解析路径静默吞错修复**：`tender_orchestrator.py` 模型解析失败不再吞为 `provider=None`——DomainError 安全语义上抛，其余异常记 `technical_model_error` 显式落盘透出工作区。
- **`contains` 非子串语义对齐**：真实 RAGFlow 1.0 实测 contains 为精确匹配；型号过滤改 `is` 精确 + 变体阶梯；FakeRagflow 对齐真机语义。
- **history 排他改应用侧**：真机 `not is` 负向算子行为不可靠，改检索回收后按 meta_fields 确定性丢弃，丢弃数记 `history_excluded`。
- **核验器单位感知**：服务期/质保只认日历单位、SLA 只认分钟/小时、驻场只认人/名；量词同义归一（2名=2人）；评分点核验改 4 字分片匹配消除插字假阳性；买方机构后缀简称放行（"大数据局"承接"星河市大数据局"）。
- **`chapter_summaries`/`technical_verify` 持久化修复**：根因是 `generation_orchestrator.py` 的 drafted 快照与 `_apply_technical_volume` 白名单缺少这两个键，`write_volume` 算出的章间摘要在提交时被丢弃。流式与非流式两处路径均已补齐。

## 二、真机验收证据（R3，权威轮次）

项目 `project-8aba5dc93b034ce2a928e5ecad7028aa`，真实 RAGFlow + 本地 Qwen 30B（`qwen3:30b-a3b-instruct-2507-q4_K_M`，`is_real: true, is_local: true`）：

| 验收点 | 证据 |
|---|---|
| 招标文件入真实 RAGFlow | `tender_index.backend == "ragflow"`，项目级 `alpha::project-tender-*` 数据集 |
| 真实模型解析 | `outline_source: model`、`extract_pages_read: 1`、`technical_model_error` 为空、锚点 6/6 带 page/chunk_id/quote |
| 事实表冻结 | 保存 200，确认目录后 `fact_frozen: true`，未挂载池 0 |
| 真实生成非模板 | 340 秒 22,348 字（R1 模板回落仅 1,969 字）；模板短语扫描零命中；正文连贯且含 `[标:p1]` 引用标记 |
| 事实一致性 | OceanBase-X800 出现 45 次、30分钟 32 次、12个月 18 次、驻场 42 次——事实表全书注入生效 |
| 四库检索真实命中 | rag_audit：本标 1 命中 + 资料 4 命中（X800运维手册 0.494 / 故障案例集 0.474 / 产品白皮书 0.456，三子库全部真实召回） |
| 脱敏双兜底 | 安康市人民医院/乐山等旧甲方名零泄露；`[某甲方]` 占位符未进入正文 |
| 核验器警示流转 | 11 节带 verify_warnings 进覆盖视图，不静默标合规 |
| 章间摘要持久化（R4 验证） | R4 重生成后 `chapter_summaries` 按一级章 "1"/"2"/"3" 真实落盘，内容为已承诺事项摘要——持久化修复真机生效 |
| 入库脱敏端到端 | 历史标书 docx 上传后 RAGFlow 分块内旧甲方/编号/金额已占位化，华为白名单保留，标题层级存活 |

## 三、测试证据

- `test_tv_m0_t26_verifier_schedule.py` 6 passed（含量词归一与真机假阳性样本回归）
- `test_tv_m0_t25_query_plan_rag.py` 4 passed；`test_parse_model_resolution_error.py` 3 passed
- 放宽阶梯/排他不放宽/脱敏白名单专项测试通过
- 前端 tsc 零错误；此前 Wave 全量回归存量失败已在基线 c9e1702 对照确认为非本次引入


## 六、遗留闭环整改（本轮追加）

### 1. 检索可观测性与 history 召回闭环（P1）
- `technical_rag.py`：每路检索强制记录 `routes[]` 明细（status: ok/empty/filtered_empty/error、raw_hits、post_filter_hits、dropped、top_score、error_detail），并发异常显式进审计，杜绝静默吞错；history 改超额召回 top_k=18，应用侧排他后保留前 6 条，防止过滤后归零。
- `knowledge_base.py`：history 独立相似度阈值 `history_similarity_threshold` / `ICG_KB_HISTORY_SIMILARITY_THRESHOLD`，默认 0.32（写法参考语义相关即可，与资料库事实检索 0.45 区分）。
- 测试：分路明细完整性、并发异常 error 记录、超额召回排他余量 3 项 regression（`test_tv_m0_t25_query_plan_rag.py` 7 passed）。

### 2. 章末摘要事实要点化（P2）
- `_chapter_running_summary` 重写：过滤「本项目旨在/本节阐述/针对本项目/我司将」等过渡套话（确定性规则实现，与 Prompt 禁令等效且无模型延迟），优先含数字承诺/机制名词的紧凑事实行，截到句读，跨节句级去重，≤150 字上限保持。

### 2.5 R5 真机验证发现的两个缺陷（已修复）
- **routes 审计明细未透传**：`retrieve_for_section` 自建审计字典时未携带 `retrieve_dual` 的 `routes`/`history_excluded`，R5 暴露后已补透传。
- **摘要过滤不足**：编号标题行（"1.1 巡检服务"）与"本项目为/面向"套话变体仍混入摘要，已补编号行过滤与套话扩列。
- R5 另证：真实长度历史标书（乐山/甘肃农信，reusability=high）在库情况下，生成正文 22,485 字，串标扫描（乐山/甘肃/农信/人民医院/Oracle）**零命中**——双兜底防串标在真实语料下成立。

### 3. 核验警示人工消警（P3）
- 新增端点 `POST /api/v1/projects/{pid}/technical-tasks/{tid}/verify-warnings/dismiss`：消警不是删除证据，原文留档 `dismissed_warnings`（含操作人/时间审计）。
- `confirm_reasons` 只统计活跃警示，全部消警后「后置核验待复核」红标消除；覆盖行暴露 `verify_warnings`（活跃）与 `dismissed_warnings_count`。
- 前端 `CoverageView.tsx`：「消警」按钮 + Popover 警示明细 + 「已核无误，消除警示」确认操作。


### 4. 消警机制真机证据
- bogus 警示文本 → 422 VALIDATION_ERROR 正确拒绝；真实警示消警 → 200，`dismissed_warnings_count` 落盘，部分消警时红标正确保留（活跃警示仍存在）。
- R6（routes 透传修复后首轮）已启动，用于捕获 history 生成期分路明细终证；若 history 仍 empty，`error_detail`/`raw_hits` 将给出确定原因，不再静默。


### 5. R6 终证与 reranker 根因修复
- R6（305 秒、21,666 字、串标零命中）分路审计显威：history 路并非零命中而是 **error——RAGFlow business error 102 rerank 失败**。观测体系按设计给出确定原因。
- 根因复现确诊：retrieval-test limit=8（page_size 32）正常命中 0.485，limit=20（page_size 80）稳定触发 reranker 错误——history 超额召回放大 page_size 溢出 reranker。
- 修复：`knowledge_base.py` page_size 上限 32；修复后 limit=20 恢复命中（0.485）。章间摘要 R6 内容已为紧凑事实要点（含 RTO/巡检周期/演练目标），套话与编号行消除。


### 6. 真实标书终审（昆明航空 Oracle 维保，504KB 真实 .doc）

- 真实 Qwen 生成 30 节 **56833 字**（920 秒），模板短语零命中，串标扫描零命中，20 节核验警示入覆盖视图。
- history 分路审计：error 102 根除；排他过滤真实执行证据（raw 1 → drop 1，not_reusable 文档被正确丢弃）——防串标在生成期真实生效。
- 诚实遗留：可复用历史文档在生成期 query 下分数未过阈值（对照实验 Oracle 强相关 query 可达 0.778），需后续调优意图拆解 query 或再降 history 阈值；真实 .doc 老格式 OCR 异步未就绪导致本轮 backend=local/rule 目录，跨页评分表保真验证需 .docx 重跑。
- 导出闸口 `SLA_PROJECT_EXPORT_REQUIRED` 正确拦截单章导出，两册主流程门禁按设计生效。

分路明细（节 | status | raw/post/drop | top_score）：
| 数据库每月巡检 | filtered_empty | 1 | 0 | 1 | 0.4557 |
| 承担人为故障损失 | filtered_empty | 1 | 0 | 1 | 0.4725 |
| 有描述无实际内容 | filtered_empty | 1 | 0 | 1 | 0.4532 |
| 昆航DBA服务需求19 | filtered_empty | 1 | 0 | 1 | 0.4557 |
| 件维护、固件升级和关联软件支持 | filtered_empty | 1 | 0 | 1 | 0.4756 |
| 昆航DBA服务需求 | filtered_empty | 1 | 0 | 1 | 0.4584 |

## 四、遗留问题（诚实记录）

1. **历史标书生成期零命中（已闭环：reranker page_size 溢出根因修复，retrieval-test 实证恢复命中；下一轮全量生成将留最终分路证据）**：R3 各节 `history_hits: 0` 且无错误记录。retrieval-test 用生成同款 query 直查可命中（分数 0.485），但该分数仅勉强高于默认相似度阈值 0.45——合成验收标书内容短、语义边际；且生成期 4 路并发检索的错误在 audit 中记录不充分，不排除并发下瞬时失败被静默。建议后续：调低 history 库阈值或在 audit 中强制记录各路异常明细。本轮已确认检索管线、排他过滤、元数据纠正链路本身可用。
2. **章间摘要内容去重不足**：R4 摘要中各节相同的开篇句被重复摘录（"本项目旨在保障..."×3），`_chapter_running_summary` 缺跨节相同行去重；功能可用但噪声待优化。另 `technical_verify` 汇总已持久化但尚未在工作区顶层透出（verify_warnings 走任务级路径可见，不受影响）。
3. **跨节口径互查仍有噪声**："他节出现1个月"类警示源自"每月/1个月内"等语境数字，需语义级判断，规则核验只能降噪无法根除——核验器定位是人工复核信号而非硬门禁，符合设计。
4. 多型号对比表文档元数据为逗号拼接串，单值精确过滤不命中，依赖放宽阶梯降级召回；单型号文档是推荐上传粒度。
5. 治理状态：任务卡/看板 in-review，未标 done——待 QA 独立签署与 PD 产品验收后由 PM 确认。

## 五、三件套影响核对

- PRD：技术卷生成链路的防串标、事实一致性、可追溯要求得到真机证据支撑，无需修改条款。
- ROADMAP/ARCHITECTURE：四物理库 + 前端双库入口架构已在 T24/T25 登记，本卡无新增架构变更。
- OpenAPI 契约：无新增端点（复用既有生成/检索/配置端点），契约无漂移。

## 终审加固轮（P0×4 + P1×3，.docx 终审前置修复）

### P0-1 导出数据源分裂与净化管道（已修）
- **数据丢失根因**：`replace_outline` 重排/重挂目录时用空目录骨架覆盖 `chapter.content`，已生成 5 万字正文被静默销毁（真机导出 6.4KB 空壳的直接原因）。已修为按 task_id/标题保留节体注入新骨架。
- 新增 `export_sanitizer.py` 确定性净化管道：剥模型重复节标题、清 `[标:][片:][证:][medium]` 引用、32 位 hex ID（中文相邻边界已修）、「需要核对」标记、`<br>`/`$$`；孤儿管道行转全角⎮（合法表格保留转 Word 原生）；写时+出口双段净化，编辑台与导出同源。

### P0-2 知识库污染（实证已清零+待确认）
- 真机实证：products/manuals/fault_cases 三库当前 **0 文档**，X800 合成污染已不存在；history 库 5 份全是真实历史标书（乐山/甘肃农信，reusability 已标）。**融科AI文档在 materials 库——是否本司产品待用户确认**。

### P0-3 截断烂尾根治（已修）
- 根因：`SECTION_CALL max_tokens=1200`（≈1600-1850 中文字），21/30 节拦腰截断。
- 修复：按章节权重分档（core 4096/normal 2048/brief 1200，权重来自挂载评分项分值）；闭合校验（半截表格/半句无句读）触发最多 1 次续写收尾，重叠前缀去重拼接，严禁重复已写内容。

### P0-4 偏离表/追溯表链路重构（已修）
- 偏离表响应列改为从本标最终生成正文单向提炼（`_content_response`：首句含数字/SLA/机制事实句，第一人称），切断历史标书口吻旧链路；核心实质性条款严禁负偏离（资料缺口标无偏离+须人工确认）；页码列回填 source.page；条款/响应/说明列严格分列不再互填。
- 生成期外实体名单并集落盘 `foreign_entity_names`，偏离表+追溯表填表时 mask_foreign_names 遮罩防串标。
- 追溯表响应列改用正文实际段落、知识片段来源从 `technical_rag_audit` 回填真实文档名、「（合成）」硬编码人名清理为空。

### P1-5 商务/技术分册网关（已修最小闭环）
- `is_business_clause` 商务硬标记（投标报价/基准价/币种/人民币/投标文件格式/装订/盖章/密封/付款/发票/税率/商务业绩/保证金/报价得分/价格分），三处硬拦截：目录任务生成（标记 clause_volume=business）、技术偏离表、未挂载池（不误阻塞）。
- 评分档位碎片过滤初版因误杀合法简短条款（容灾备份/培训）已撤回，多档位合并留待下一轮。

### P1-6 写作规划卡+故障案例配额（已修）
- `writing_blueprints`：write_volume 启动时为每个叶子节生成规划卡（target_words 按权重、scoring_hooks、must_cover、forbidden_overlap、assigned_tables、assigned_cases），注入单节 Prompt「必须执行」。
- 故障案例双闸门：非应急/故障类节物理不查 fault_cases 库；同一案例 chunk 全书一次性配额（`fault_cases_used` 跨节去重），消灭跨章复读。

### P1-7 事实表三层+反八股（已修）
- Fact Sheet 扩展三层结构化字段：`sla_terms`（故障响应15分钟/一级到场40分钟/修复24小时/二级2小时/DBA 6个月）、`asset_profile`（甲方资产画像）、`scoring_decisions`（评分加分决策），人工确认后注入每节 Prompt，强制覆盖历史模板指标。
- SECTION_SYSTEM 反八股：除第一节外禁止「本项目旨在/面向/聚焦于/本节阐述」开篇；表格必须业务专属列名、禁止千篇一律三列；通用交付物名禁止挖【待补】，仅客观私有事实缺口标 [待人工补充：具体项]；SLA 数字必须与事实表逐字一致。

### 验证证据
- 新增 `tests/backend/test_tv_m0_t28_export_deviation.py` 14 项全绿（净化/截断/偏离表/网关/配额/蓝图）
- 离线自测 26/26 通过；t25+t28 21 passed；OpenAPI 契约已重新导出归零漂移
- test_technical_sources 4 项失败经 HEAD 纯净基线对照证实为**存量失败**（非本轮回归）
- 后端已带全部修复重启（SECRET 稳定配方），等待 .docx 终审闭环轮
