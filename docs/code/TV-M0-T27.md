为什么有这个文件：说明 TV-M0-T27 真机加固与验收驱动修复的代码改动位置与设计理由。

# TV-M0-T27 代码说明

| 项 | 内容 |
|---|---|
| 状态 | in-review |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 交付 | [TV-M0-T27](../delivery/TV-M0-T27.md) |

## 一、五项真机加固（验收前防御性补齐）

### 1. metadata_condition 零命中逐级放宽 — `icg/domain/technical_rag.py`

- `_sanitize_metadata_condition`：把任意输入严格收敛为 RAGFlow 1.0 协议结构 `{logic, conditions:[{name, comparison_operator, value}]}`，非法算子/空值剔除，防止 ABI 漂移静默 422。
- `_model_variants`：型号写法差异生成检索变体（`X800` / `Model-X800` / `X 800` / `X-800` / 去连字符），应对人工录入与事实表写法不一致。
- `_metadata_fallback_ladder`：零命中逐级放宽——精确型号 → 型号变体 `or+is` → 仅 `doc_type` 级 → 不过滤；`history` 直接返回单层（排他是安全底线，永不放宽）。
- `_call_kb_search`：按阶梯顺序重试，命中即停。

### 2. 脱敏白名单 — `icg/domain/kb_preprocess.py`

- 内置厂商/品牌白名单（华为、中兴、浪潮、新华三、OceanBase、达梦、人大金仓等）+ 用户元数据 `deid_allow` / `bidder_name` 自定义放行。
- 白名单只约束 `_SPECIFIC_ORG` 自动探测替换；显式标注字段（采购人/项目名称/项目编号/金额）仍强制占位。
- DOCX 走 XML 级文本替换，不动 `w:p` 样式与标题层级，TitleChunker hierarchy=3 切块不受影响。

### 3. 轻调用参数与并发可配

- `icg/infra/openai_model.py`：`chat_payload` 仅在 `profile.enable_thinking is False` 时发送 `think: False` 与 `chat_template_kwargs`，永不透传 `thinking_budget`。
- `icg/domain/technical_volume.py`：`SECTION_STREAM_CONCURRENCY` 改为读环境变量 `ICG_SECTION_CONCURRENCY`，默认 2（原硬编码 3），防止打满本地 30B 并发导致意图拆解超时降级。

### 4. 核验器白名单与自否定过滤 — `icg/domain/technical_verifier.py`

- `_VERIFY_ORG_ALLOWLIST`：国家级部委/标准制定机构（工信部、财政部、国家卫健委等）引用规范不算外项目实体残留；省市级委办局不在此列（仍可能是旧甲方）。
- `_NEGATED_CONTEXT` / `_SELF_NEGATED`：实体名仅出现在「严禁出现XX/经核查一致/无冲突/符合要求」语境时不进 `verify_warnings`。

### 5. 占位检测与一键冒烟

- `icg/domain/ragflow_config.py`：`get`/`update` 响应附带 `placeholder_dataset_ids`（`dataset-*-01` 模式检测）与 `suggested_dataset_ids`（应用索引中已部署的真实 dataset_id）。
- `frontend/web/src/admin/RagflowConfigModal.tsx`：占位告警 + 建议 ID 一键回填。
- `scripts/real-acceptance-smoke.sh`：一键门控真机冒烟（`ICG_RUN_REAL_RAGFLOW_TESTS=1` / `ICG_RUN_REAL_MODEL_TESTS=1`）。
- antd 废弃告警清理：`bodyStyle`→`styles.body`、`destroyOnClose`→`destroyOnHidden`、`addonAfter`→共享组件 `frontend/web/src/shared/UnitInputNumber.tsx`、静态 `message`→`App.useApp()`（保留项目既有 `AntApp.useApp?.()` 测试兜底约定）。

## 二、真机验收驱动修复（端到端跑通中暴露）

### 1. 解析路径静默吞错 — `icg/domain/tender_orchestrator.py`

`resolve_model_provider` 的 `except Exception` 曾把一切异常吞掉置 `provider=None`：密钥解密失败（SECRET_KEY_UNAVAILABLE）时抽取/目录/生成全部静默降级为规则与模板，工作区毫无提示——违反诚实降级红线。现在：

- `DomainError`（敏感项目模型硬约束等安全语义）直接向上抛，不得吞。
- 其他异常记录 `technical_model_error`（类型+摘要）落盘，经 `workspace_fields`（`technical_outline.py`）透出到工作区，前端可显式告警；健康解析时自动清除。
- 测试：`tests/backend/test_parse_model_resolution_error.py`（配置失败显式落盘/健康清除/安全错误 403 上抛）。

### 2. `contains` 非子串语义对齐 — `technical_query_plan.py` / `technical_rag.py` / `tests/backend/fake_ragflow_v1.py`

真实 RAGFlow 1.0 实测：`contains` 是标量精确匹配（`contains "X800"` 对存储 `Model-X800` 零命中），不是子串；`is`+`or` 逻辑变体组可正确命中。型号过滤全部改 `is` 精确语义，写法差异交给放宽阶梯的变体 OR 覆盖；FakeRagflow `_matches_meta` 对齐真机语义（contains/is 全串精确、列表元素精确包含）。

已知限制：多型号对比表文档的 `model` 元数据为逗号拼接串（`"Model-X800,Model-S200"`），任何单值精确条件都无法命中——精确级落空后由放宽阶梯降到 `doc_type` 级召回，内容侧已按型号分节切片防串参数；单型号文档是精确检索的推荐上传粒度，按型号拆分为独立文档是后续候选优化。

### 3. history 排他改应用侧 — `technical_rag.py::_filter_history_hits`

真机实测 `not is` 负向算子行为不可靠（缺字段文档被误排、命中不一致）。`not_reusable`/`buyer_requirement` 排他是防串标安全底线，改为检索回收后按 `meta_fields` 确定性丢弃，丢弃条数记入 `audit["history_excluded"]`；`technical_query_plan.py` 不再下发负向 metadata 条件。

### 4. 核验器单位感知与评分点分片 — `technical_verifier.py`

- `_METRIC_FIELD_UNITS`：服务期/质保只认日历单位（年/月/周/日），SLA 只认分钟/小时，驻场只认人/名。真机假阳性样本（驻场句旁的 10分钟/2小时、服务期句旁的 7×24小时）不再误报。
- `_sheet_commitments` 同步带字段单位过滤。
- 评分点实质响应核验：长中文连续串（如「每月提交巡检报告」）正文插一字即整串不中造成假阳性，改为 4 字非重叠分片，任一片段命中即视为有响应痕迹——本核验只抓「完全缺席/空喊口号」。

### 5. `chapter_summaries` 工作区透出 — `technical_outline.py::workspace_fields`

章间串行摘要此前只写 `workflow["chapter_summaries"]` 不外露，验收无法观测；现透到工作区响应。


### 6. `chapter_summaries`/`technical_verify` 提交丢失修复 — `icg/domain/generation_orchestrator.py`

真机 R3 发现章间摘要始终为空：`write_volume` 正确写入 `workflow["chapter_summaries"]`，但生成编排器在 worker 线程结束后挑选键构造 `drafted` 快照、`_apply_technical_volume` 再按键白名单应用到 live state——两处白名单都缺 `chapter_summaries` 与 `technical_verify`，导致摘要与核验汇总在提交时被静默丢弃。流式与非流式两处路径已补齐；`technical_rag_audit` 之所以一直可见恰因它在白名单内，该对照是定位根因的关键线索。

### 7. 核验器量词归一与买方简称放行 — `technical_verifier.py`

R3 警示噪声分析后的第二轮降噪：`_UNIT_SYNONYMS` 把 名/位/个 归一为人（"正文取2名 vs 事实表驻场2人"同值不再误报冲突）；`_shares_org_suffix` 把与放行身份共享 ≥4 字后缀的机构引用视为同一买方简称（"大数据局"承接"星河市大数据局"属正常写作），只对真正外项目实体报警。

## 三、运维侧恢复（非代码）

- RAGFlow API key 与三个模型配置密钥因 SECRET 轮换失配无法解密：从 rag_flow MySQL `api_token` 表找回真实 key，经 API 以当前密钥重存（`backend/bid-core/data/local-secret.key` 持久化同一密钥，重启不轮换）。
- 密钥轮换是部署侧高危操作：`technical_model_error` 透出后此类故障不再静默。
