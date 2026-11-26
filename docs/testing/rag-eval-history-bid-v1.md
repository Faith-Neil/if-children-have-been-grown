# 历史标书 RAG 检索评测（golden-history-bid-v1，真实 RAGFlow，history_bid）

- 文档 5 篇，查询 37 条；Recall@5 / MRR@10；rerank=无
- 摄入映射 5 篇；远端失败标记 0 篇
- 本报告为真实 RAGFlow 跑盘结果。

| 阈值 | 关键词权重 | literal recall@5 | literal MRR@10 | paraphrase recall@5 | paraphrase MRR@10 | 负例误召回 |
|---|---|---|---|---|---|---|
| 0.3 | 0.3 | 1.0 | 0.932 | 1.0 | 0.883 | 1.0 |
| 0.3 | 0.5 | 1.0 | 0.932 | 1.0 | 0.883 | 1.0 |
| 0.45 | 0.3 | 1.0 | 0.932 | 1.0 | 0.883 | 0.8 |
| 0.45 | 0.5 | 0.909 | 0.886 | 0.4 | 0.35 | 0.0 |

## 结论（2026-11-06）

- 环境：本机 RAGFlow v1.0.0-rc2；五份脱敏历史标书经 `history_bid` 管道全部解析成功（0 失败）；耗时约 22 分钟。
- 语料仅 5 篇时，过阈后若命中则 Recall@5 易接近 1.0；更有区分度的是 **MRR@10** 与 **负例误召回**。
- 脚本按「literal+paraphrase 召回 − 负例误召回」选出的最优为 **阈值 0.45 / 关键词权重 0.5**（负例误召回 0，但 paraphrase recall@5 仅 0.4）。
- **写作检索更看重召回时**：优先看 **0.45 / 0.3**（literal/paraphrase recall@5 均为 1.0，MRR@10 约 0.93/0.88；负例误召回 0.8，五篇语料下负例仍易捞到相似运维文档）。
- **本轮不自动改写公司默认阈值**（现网默认仍为 0.45/0.3）；是否收紧关键词权重到 0.5 另开产品决定。
- 若干同义查询在 0.45/0.5 下落空（如 MOS、融科小e、部分信创改写），字面查询整体稳定。

## 最优组合明细（阈值 0.45，关键词权重 0.5；按脚本打分）

| 类别 | 查询 | 期望 | 前 k 命中（相似度） |
|---|---|---|---|
| literal | 季度深度巡检 HIS LIS PACS | leshan | leshan(0.849), lutianhua(0.833), guiyang2025(0.83), gansu(0.824), guiyang2024(0.818) |
| literal | Oracle OEM优化工具安装配置 | leshan | lutianhua(0.855), leshan(0.853), guiyang2025(0.835) |
| literal | 每季度对HIS、LIS、PACS数据库作一次现场巡检 | leshan | leshan(0.853) |
| paraphrase | 医院 Oracle 数据库按季度到场巡检怎么做 | leshan | （无） |
| paraphrase | OEM 原生优化分析工具如何给招标人安装 | leshan | lutianhua(0.855), leshan(0.854) |
| literal | 7×24小时故障响应 15分钟电话联系 | leshan | leshan(0.848) |
| literal | Real Application Clusters RAC | gansu | gansu(0.853), guiyang2025(0.831), lutianhua(0.826) |
| literal | Active Data Guard ADG | gansu | gansu(0.844), lutianhua(0.833), guiyang2025(0.828) |
| literal | MY ORACLE SUPPORT | gansu | （无） |
| literal | Database Enterprise Edition DBEE | gansu | gansu(0.845), lutianhua(0.822), guiyang2025(0.813) |
| paraphrase | Oracle RAC 与 ADG 如何满足单位采购 | gansu | gansu(0.839), guiyang2025(0.836), lutianhua(0.832) |
| paraphrase | 官方电子支持平台 MOS 接入服务 | gansu | （无） |
| literal | 泸天化集团数据库运维保障 | lutianhua | lutianhua(0.861) |
| literal | RMAN备份 0级备份 归档日志 | lutianhua | lutianhua(0.851), guiyang2025(0.835) |
| literal | MySQL数据库SQL审核工具Yearning | lutianhua | lutianhua(0.836), guiyang2025(0.831) |
| literal | 融科小e监控软件 日常自动巡检 | lutianhua | （无） |
| literal | 工作日每天对数据库作0级备份 | lutianhua | lutianhua(0.853) |
| paraphrase | 泸天化项目如何做 RMAN 备份与恢复演练 | lutianhua | （无） |
| paraphrase | 用 Yearning 做 MySQL SQL 审核 | lutianhua | lutianhua(0.836), guiyang2025(0.831) |
| literal | 2025年贵阳银行基础软件平台维保 | guiyang2025 | guiyang2025(0.859) |
| literal | P52011520250008VU | guiyang2025 | guiyang2025(0.821) |
| literal | ORACLE原厂全球解决方案中心 SSC 高级服务包 | guiyang2025 | guiyang2025(0.844), gansu(0.833), lutianhua(0.829), leshan(0.828) |
| literal | 服务期限 2025年11月16日—2026年11月15日 | guiyang2025 | guiyang2025(0.845) |
| paraphrase | 贵阳银行基础平台软件一年维保服务期如何约定 | guiyang2025 | guiyang2025(0.852) |
| paraphrase | ORACLE SSC 高级服务包投标报价条目 | guiyang2025 | （无） |
| literal | 贵阳银行2024年信创基础软件采购 | guiyang2024 | guiyang2024(0.857) |
| literal | YGCQ-QC-2024-10-521-公 | guiyang2024 | guiyang2024(0.82) |
| literal | 国产数据库品牌技术认证证书 达梦 人大金仓 | guiyang2024 | guiyang2024(0.832), lutianhua(0.828) |
| literal | 信创中间件品牌技术认证证书 | guiyang2024 | guiyang2024(0.832) |
| literal | 信创操作系统品牌技术认证 | guiyang2024 | guiyang2024(0.833) |
| paraphrase | 投标人需提供几种国产数据库认证 | guiyang2024 | （无） |
| paraphrase | 信创基础软件采购评分中的中间件认证要求 | guiyang2024 | （无） |
| negative | 建筑工程施工总承包一级资质 | （无） | （无） |
| negative | 食品经营许可证 | （无） | （无） |
| negative | 注册结构工程师人员证书 | （无） | （无） |
| negative | 桥梁隧道施工业绩 | （无） | （无） |
| negative | 医疗器械经营许可证 | （无） | （无） |
