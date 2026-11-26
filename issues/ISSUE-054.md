为什么有这个文件：登记技术服务方案全链路质量升级与 RAGFlow 四库协同优化的需求变更。

它解决什么问题：跨页评分表切分易丢表头、人工编辑目录删节会静默丢评分点、知识库未分形态切片且检索未启用 Metadata 过滤、每节灌入全量废标稀释注意力、分段生成缺全局事实表与章间摘要导致前后口径不一或串标。

# ISSUE-054：技术卷全链路质量升级与 RAGFlow 四库协同

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-054 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | closed（本地验收） |
| 登记日期 | 2026-11-25 |
| 最后更新日期 | 2026-11-26 |
| revision | tech-volume-quality-v3 |
| 关联 Task | [TV-M0-T22](../docs/tasks/TV-M0.md#tv-m0-t22)、[TV-M0-T23](../docs/tasks/TV-M0.md#tv-m0-t23)、[TV-M0-T24](../docs/tasks/TV-M0.md#tv-m0-t24)、[TV-M0-T25](../docs/tasks/TV-M0.md#tv-m0-t25)、[TV-M0-T26](../docs/tasks/TV-M0.md#tv-m0-t26)、[TV-M0-T27](../docs/tasks/TV-M0.md#tv-m0-t27)、[TV-M0-T28](../docs/tasks/TV-M0.md#tv-m0-t28)、[TV-M0-T29](../docs/tasks/TV-M0.md#tv-m0-t29)、[TV-M0-T30](../docs/tasks/TV-M0.md#tv-m0-t30) |
| 关联 PR | 目标分支 `feat/iss-047-technical-volume-mvp`，不合 main |
| 本地验收 | 通过；2026-11-26，T28/T29/T30 聚焦回归与昆明航空真机三件套导出复核 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | `docs/delivery/TV-M0-T22.md`～`docs/delivery/TV-M0-T30.md` |

## 用户拍板与目标架构

1. **招标解析表格保真与溯源锚点（TV-M0-T22）**：DeepDOC 与本地 DOCX 表格还原为标准 Markdown 表，跨页续表自动补齐表头；重叠滑动窗口禁止在表格中间裸切，逐页带 `[第 P 页]` 锚点并回填精确页码、原文 `quote` 与本标 `chunk_id`。
2. **目录未挂载池防丢与全局项目事实表（TV-M0-T23）**：删除或调整目录章节时，孤儿评分点与技术要求自动退回 `unassigned_requirements`（未挂载池），支持重挂或一键归入兜底节；确认目录时前后端双重强提醒/拦截；同步核对并冻结 `Global Fact Sheet` JSON 单一事实源。
3. **前端双库 + RAGFlow 底层物理 4 库与入库预处理（TV-M0-T24）**：前端保持「历史标书 / 资料库」双主入口，资料库内分「文档/运维手册 · 故障案例 · 产品手册/参数」三子库，底层映射到 `${company_id}::icg-history / icg-manuals / icg-fault-cases / icg-products` 四个独立 Dataset 与专属画布 DSL（兼容旧 `icg-material` 兜底）；历史标书入库前做去实体化脱敏，多型号参数表与故障台账入库前做带表头拆行预处理。
4. **检索意图拆解与四库带过滤配额召回（TV-M0-T25）**：打通 `knowledge_base.py:search` 的 `metadata_condition`；单节检索前用轻量本地 Qwen（失败回落规则）拆解差异化子 Query，并发召回本标补充（~20%）+ 资料三子库（~55%，锁定适用型号）+ 历史标书（~25%，过滤不可复用块）。
5. **五段隔离 Prompt、废标分级、章间串行摘要与后置核验器（TV-M0-T26）**：砍掉每节全量废标灌入改为 `L0 + 本节关联 L1`；采用五段多源隔离 Prompt；按一级章串行推进并更新 `running_summary`、章内并发流式输出；落盘后执行防串标全实体扫描、全局事实表口径核验与高分评分节实质响应复核。

## 基线影响核对

| 文档 | 影响与处理 |
|---|---|
| PRD / ROADMAP / ARCHITECTURE | 无结构破坏：产品范围沿用 [仅技术标决策](../docs/decisions/2026-11-08-tech-bid-only-product.md)，本次升级技术卷内部解析、四库管道与生成核验引擎 |
| TASK_BOARD / 任务卡 | 新增 `TV-M0-T22`～`TV-M0-T26` |
| DOCUMENT_INDEX / PROJECT_STATUS | 随各卡交付同步登记 |

## 2026-11-26 终审精修进展

- TV-M0-T28 已由 PM 对 `.audit/final-round-v2/` 三件套拆包复核并签收 done。
- TV-M0-T29 已推进至 in-review：最终局部复核产物位于 `.audit/final-round-v2-t29-hardfix/`；已移除导出层单项目硬编码并改为 Global Fact Sheet + Verifier 动态校验，局部重跑第 1/4/9 节后正文 SLA/人数/年份冲突清零；偏离表 49/49 唯一条款、0 负偏离、0 页码列串台、0 硬截断残句、0 评分公式/付款协定/表名噪点。ISSUE-054 同步关闭，PR 未合入、未发布。
- TV-M0-T29 已由 PM 签收 done；TV-M0-T30 已登记并进入 in-progress，目标是消除偏离表通用兜底模板且控制导出耗时增幅。
- TV-M0-T30 已由 PM 签收 done；签收前复核证据：`.audit/final-round-t30/` 真机复导显示偏离表 49/49 唯一条款、通用兜底清零、0 负偏离、0 外项目/历史标书串标；兜底池 3 条按 2 章并发调用内网 Qwen 全部通过门禁，新鲜导出 13.548 秒、缓存复导 3.898 秒。待 QA/PD 独立复核后由 PM 决定是否标 done；Issue 整体保持 in-progress。

