为什么有这个文件：记录合成金标集在真实 RAGFlow（内置解析、text-embedding-3-large）上的检索评测结果。

它解决什么问题：用数据确定默认相似度阈值与关键词权重。

# RAG 检索评测（golden-v1，真实 RAGFlow，builtin）

- 文档 21 篇，查询 32 条；k=3；rerank=无

| 阈值 | 关键词权重 | literal recall@3 | literal MRR | paraphrase recall@3 | paraphrase MRR | 负例误召回 |
|---|---|---|---|---|---|---|
| 0.1 | 0.3 | 1.0 | 1.0 | 0.969 | 1.0 | 0.75 |
| 0.1 | 0.5 | 1.0 | 1.0 | 0.969 | 1.0 | 0.75 |
| 0.1 | 0.7 | 1.0 | 1.0 | 0.969 | 1.0 | 0.75 |
| 0.2 | 0.3 | 1.0 | 1.0 | 0.969 | 1.0 | 0.75 |
| 0.2 | 0.5 | 1.0 | 1.0 | 0.969 | 1.0 | 0.75 |
| 0.2 | 0.7 | 0.833 | 0.833 | 0.406 | 0.438 | 0.25 |
| 0.3 | 0.3 | 1.0 | 1.0 | 0.969 | 1.0 | 0.75 |
| 0.3 | 0.5 | 1.0 | 1.0 | 0.969 | 1.0 | 0.75 |
| 0.3 | 0.7 | 0.25 | 0.25 | 0.0 | 0.0 | 0.25 |

## 最优组合明细（阈值 0.1，关键词权重 0.3）

| 类别 | 查询 | 期望 | 前 k 命中（相似度） |
|---|---|---|---|
| literal | ISO27001 信息安全管理体系认证 | q-iso27001 | q-iso27001(0.489), q-iso20000(0.472), q-iso9001(0.464) |
| literal | 质量管理体系证书 | q-iso9001 | q-iso9001(0.477), q-iso20000(0.462), q-iso27001(0.459) |
| literal | CMMI5 级 | q-cmmi5 | q-cmmi5(0.781) |
| literal | 等保三级测评报告 | q-dengbao | q-dengbao(0.461), h-2023(0.42), n-inspection(0.415) |
| literal | 高新技术企业 | q-hightech | q-hightech(0.766), q-itss(0.42), q-iso20000(0.409) |
| literal | 项目经理 PMP 证书 | p-pm | p-pm(0.472), q-iso20000(0.433), p-architect(0.431) |
| literal | CCIE 网络工程师 | p-network | p-network(0.784), p-security(0.455), p-architect(0.434) |
| literal | 银行数据中心运维业绩 | f-bank | f-bank(0.48), f-gov(0.451), h-2023(0.445) |
| literal | 政务云运维项目 | f-gov | f-gov(0.475), f-bank(0.436), q-dengbao(0.433) |
| literal | 一级故障响应时间 | s-sla | s-sla(0.466), n-emergency(0.451), p-network(0.402) |
| literal | 日常巡检方案 | n-inspection | n-inspection(0.497), n-training(0.442), f-bank(0.414) |
| literal | 数据备份策略 RPO RTO | n-backup | n-backup(0.492), n-inspection(0.435), f-bank(0.404) |
| paraphrase | 投标人须具备信息安全方面的体系认证 | q-iso27001 | q-iso27001(0.456), q-dengbao(0.449), p-security(0.445) |
| paraphrase | 供应商应具有软件能力成熟度最高等级 | q-cmmi5 | q-cmmi5(0.454), q-dengbao(0.442), q-itss(0.441) |
| paraphrase | 系统须满足网络安全等级保护第三级要求 | q-dengbao | q-dengbao(0.469), p-security(0.433), q-itss(0.431) |
| paraphrase | IT 服务管理流程是否规范，有无相关认证 | q-iso20000, q-itss | q-iso20000(0.471), q-iso27001(0.447), q-itss(0.441) |
| paraphrase | 拟派项目负责人须具有项目管理资格及金融行业经验 | p-pm | p-pm(0.461), p-architect(0.437), p-security(0.423) |
| paraphrase | 需要有懂容灾架构设计的技术负责人 | p-architect | p-architect(0.469), p-network(0.428), p-security(0.427) |
| paraphrase | 是否配备渗透测试与安全加固人员 | p-security | p-security(0.461), s-staff(0.431), p-network(0.423) |
| paraphrase | 近三年金融机构机房驻场运维类合同 | f-bank | f-bank(0.469), h-2023(0.452), f-gov(0.444) |
| paraphrase | 医疗行业信息化项目经验 | f-hospital | f-hospital(0.462), f-gov(0.431), q-iso20000(0.424) |
| paraphrase | 出现严重问题后多久能到现场处理 | n-emergency, s-sla | n-emergency(0.456), n-training(0.4), q-iso20000(0.39) |
| paraphrase | 全天候技术支持服务承诺 | s-sla | s-sla(0.477), s-staff(0.448), h-2023(0.443) |
| paraphrase | 现场常驻多少名技术人员 | s-staff | s-staff(0.471), p-architect(0.438), p-security(0.432) |
| paraphrase | 定期检查机房设备运行状态的做法 | n-inspection | n-inspection(0.48), f-bank(0.418), p-network(0.403) |
| paraphrase | 数据丢了怎么恢复，多久做一次演练 | n-backup | n-backup(0.456), s-sla(0.408), f-bank(0.391) |
| paraphrase | 交付后如何教会客户使用系统 | n-training | n-training(0.451), f-hospital(0.409), s-staff(0.405) |
| paraphrase | 以往投标中的分级运维服务体系 | h-2023 | h-2023(0.459), f-gov(0.428), q-dengbao(0.428) |
| negative | 公司是否具备建筑工程施工总承包一级资质 | （无） | q-itss(0.433), p-pm(0.428), p-network(0.417) |
| negative | 食品经营许可证 | （无） | （无） |
| negative | 注册结构工程师人员证书 | （无） | p-architect(0.443), p-security(0.442), p-network(0.435) |
| negative | 桥梁隧道施工业绩 | （无） | f-bank(0.724), f-hospital(0.719), f-gov(0.717) |

## 第二轮：高阈值扫描（同一金标集，2026-10-28）

| 阈值 | 关键词权重 | literal recall@3 | paraphrase recall@3 | paraphrase MRR | 负例误召回 |
|---|---|---|---|---|---|
| 0.35 | 0.1 | 1.0 | 0.938 | 1.0 | 0.75 |
| 0.35 | 0.3 | 1.0 | 0.969 | 1.0 | 0.75 |
| **0.45** | 0.1 | 1.0 | 0.938 | 1.0 | **0.0** |
| **0.45** | **0.3** | **1.0** | **0.938** | **1.0** | **0.0** |
| 0.55 | 0.1 | 0.917 | 0.469 | 0.5 | 0.0 |
| 0.55 | 0.3 | 0.25 | 0.0 | 0.0 | 0.0 |

结论：默认值定为阈值 0.45、关键词权重 0.3（`ICG_KB_SIMILARITY_THRESHOLD` / `ICG_KB_KEYWORDS_WEIGHT`）。原默认 0.2 / 0.7 时同义改写召回只有 0.41。关键词权重越高，阈值越不能高（关键词相似度量纲小），两者需一起调。数值依赖嵌入模型（本轮为 Jiekou text-embedding-3-large）；生产换内网模型后须重跑本评测。

ICG“结构化资料”流程评测：解析已在真实 RAGFlow 跑通（问法、关键词生成正常），但每块一次 LLM 调用加单解析进程，21 篇短文档约 15 分钟仍未全部完成，且有模型超时失败；对比数字待解析并发调大后补测。
