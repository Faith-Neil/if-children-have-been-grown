为什么有这个文件：记录合成金标集在真实 RAGFlow 上用 ICG“结构化资料”摄入流程（按标题切块 + LLM 生成问法/关键词）的检索评测结果。

它解决什么问题：判断自建摄入流程是否比内置解析更好，决定知识库默认用哪种解析。

# RAG 检索评测（golden-v1，真实 RAGFlow，pipeline）

- 文档 21 篇，查询 32 条；k=3；rerank=无

| 阈值 | 关键词权重 | literal recall@3 | literal MRR | paraphrase recall@3 | paraphrase MRR | 负例误召回 |
|---|---|---|---|---|---|---|
| 0.3 | 0.3 | 0.667 | 0.667 | 0.531 | 0.562 | 0.75 |
| 0.45 | 0.3 | 0.667 | 0.667 | 0.5 | 0.562 | 0.0 |

## 最优组合明细（阈值 0.45，关键词权重 0.3）

| 类别 | 查询 | 期望 | 前 k 命中（相似度） |
|---|---|---|---|
| literal | ISO27001 信息安全管理体系认证 | q-iso27001 | q-iso27001(0.789), q-iso9001(0.764), q-iso20000(0.472) |
| literal | 质量管理体系证书 | q-iso9001 | q-iso9001(0.777), q-iso20000(0.762), q-iso27001(0.758) |
| literal | CMMI5 级 | q-cmmi5 | （无） |
| literal | 等保三级测评报告 | q-dengbao | （无） |
| literal | 高新技术企业 | q-hightech | q-hightech(0.767) |
| literal | 项目经理 PMP 证书 | p-pm | p-pm(0.772) |
| literal | CCIE 网络工程师 | p-network | p-network(0.786), p-security(0.456) |
| literal | 银行数据中心运维业绩 | f-bank | f-bank(0.779), f-gov(0.451) |
| literal | 政务云运维项目 | f-gov | f-gov(0.775) |
| literal | 一级故障响应时间 | s-sla | n-emergency(0.451) |
| literal | 日常巡检方案 | n-inspection | n-inspection(0.497) |
| literal | 数据备份策略 RPO RTO | n-backup | （无） |
| paraphrase | 投标人须具备信息安全方面的体系认证 | q-iso27001 | q-iso27001(0.756) |
| paraphrase | 供应商应具有软件能力成熟度最高等级 | q-cmmi5 | （无） |
| paraphrase | 系统须满足网络安全等级保护第三级要求 | q-dengbao | （无） |
| paraphrase | IT 服务管理流程是否规范，有无相关认证 | q-iso20000, q-itss | q-iso20000(0.471) |
| paraphrase | 拟派项目负责人须具有项目管理资格及金融行业经验 | p-pm | p-pm(0.761) |
| paraphrase | 需要有懂容灾架构设计的技术负责人 | p-architect | （无） |
| paraphrase | 是否配备渗透测试与安全加固人员 | p-security | p-security(0.761) |
| paraphrase | 近三年金融机构机房驻场运维类合同 | f-bank | f-bank(0.469) |
| paraphrase | 医疗行业信息化项目经验 | f-hospital | f-hospital(0.462) |
| paraphrase | 出现严重问题后多久能到现场处理 | n-emergency, s-sla | n-emergency(0.456) |
| paraphrase | 全天候技术支持服务承诺 | s-sla | （无） |
| paraphrase | 现场常驻多少名技术人员 | s-staff | （无） |
| paraphrase | 定期检查机房设备运行状态的做法 | n-inspection | n-inspection(0.48) |
| paraphrase | 数据丢了怎么恢复，多久做一次演练 | n-backup | （无） |
| paraphrase | 交付后如何教会客户使用系统 | n-training | n-training(0.451) |
| paraphrase | 以往投标中的分级运维服务体系 | h-2023 | （无） |
| negative | 公司是否具备建筑工程施工总承包一级资质 | （无） | （无） |
| negative | 食品经营许可证 | （无） | （无） |
| negative | 注册结构工程师人员证书 | （无） | （无） |
| negative | 桥梁隧道施工业绩 | （无） | （无） |

## 结论（2026-10-28）

- 环境：RAGFlow v1.0.0-rc2；嵌入 `text-embedding-3-large@BAAI-BGE-M3@Jiekou.AI`；抽取模型 `zai-org/glm-4.7-flash@BAAI-BGE-M3@Jiekou.AI`；用户已调大并发。
- 21 篇里 14 篇解析完成、**7 篇失败**（LLM 抽取步骤失败）。失败的文档检索不到，这是召回下降的主因：CMMI5、等保、RPO/RTO、SLA 承诺、驻场人数、历史分级运维等查询全部落空。
- 在解析成功的文档上，命中相似度与内置解析相当（约 0.45～0.79），阈值 0.45 时负例误召回为 0。
- 与 [内置解析](rag-eval-golden-v1-builtin.md)（同参数 literal 1.0 / paraphrase 0.969）相比，流程模式目前明显更差（literal 0.667 / paraphrase 0.5）。
- 决定：**默认仍是“流程优先、部署失败退回内置解析”的现状不变，但生产上线前须把抽取模型换成稳定的内网模型并复测**；若复测仍有解析失败，在知识库设置里关闭“使用 ICG 摄入流程”（已支持按公司切换）。流程模式失败的文档在知识库管理页显示为“解析失败”，可单篇重解析。
