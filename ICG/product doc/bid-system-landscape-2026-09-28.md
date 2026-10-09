# 智能投标 / 标书生成系统：市场与技术调研（私有化部署视角）

- 调研日期：2026-09-28（Asia/Shanghai）
- 调研方式：只用 WebSearch / WebFetch / 公开 GitHub 与 Hugging Face 元数据。没有注册试用，没有联系厂商，也没有填表。
- 用户背景：公司主要投**服务类标**，具体是**数据库维保**和**IT 运维**项目。所以本报告会特别标出各产品对服务类 / IT 运维标书的支持情况。
- **来源标注约定**
  - 【官网】：厂商官网或官方文档自述
  - 【官方新闻】：厂商官网发布的新闻稿
  - 【第三方】：媒体、导航站、博客、评测
  - 【疑似软文】：页面被平台标注为"可能是商业推广软文"，或同一账号连续为单一厂商背书、评分明显夸张的"评测"
  - 【招标原文】：公开招标公告
  - 【推算】：本报告根据已确认的参数量 / 显存数据推算，不是来源原话
- **重要提醒**：国内"AI 标书工具评测"类文章大量是商业推广。比如 cnblogs 页面直接带有"平台提示：本文可能是商业推广软文"；也有 CSDN 文章把某产品标为"TOP1 / 99.9 分"。这类文章中的准确率、客户数、价格都只能当线索，不能当事实。价格尤其混乱，同一产品在不同来源的报价互相矛盾（见各表备注）。

---

## (a) 国内产品对比表

> 表中"功能"一栏只列来源中明确提到的能力。**"未查到"表示本轮公开资料里没有找到，不代表产品没有这项能力。**

| 产品 / 厂商 | 主要功能（来源口径） | 私有化部署 | 大模型（公开信息） | 目标行业 / 标类 | 公开价格 | 服务类 / IT 运维相关 | 来源 |
|---|---|---|---|---|---|---|---|
| **钛投标** / 景网数据服务（武汉） | 招标文件解析（关键条款、资质要求、评分标准）、商务/技术标生成、自动填充资质/业绩/人员、废标风险检查、企业自有库（资质、业绩、人员、产品、历史标书）、企业版协同与权限【官网】 | 支持，但官网只写"企业级数据安全与私有化部署支持（具体以合同为准）"【官网】；第三方称支持断网、信创适配【疑似软文】 | 官网称"基于中央网信办备案大模型"；第三方称是自研"数字方案爵士"垂直大模型【第三方/疑似软文】 | 官网写"政府采购、工程建设、信息化服务、设备采购等 300+ 行业" | 官网有定价页，但为 JS 渲染，未能抓取。第三方说法互相矛盾：IT之家称企业版 9999 元/年起、私有化 10 万元起；CSDN 称尊享版 35000 元/年起；另一文称 9.9 元/份起【均为第三方，存疑】 | 官网列有"信息化服务"场景；未查到运维 SLA / 驻场专项模板 | https://taitoubiao.com/llms.txt ；https://www.ithome.com/0/999/392.htm ；https://blog.csdn.net/lcjwsj/article/details/160847719 ；http://www.jsqmd.com/news/983207/ |
| **巧文书 AI** / 湖南天河国云 | 招标解读（资格、评分、废标条款）、按评分点编写目录、标书编写、标书审查（废标、完整性、重复、格式）、企业知识库（历史标书、资信、产品、图库）、图表生成、标讯查询【官网】 | 支持，官网有"私有化部署"栏目（专职部署负责人、实施支持等）【官网】；第三方称私有化"单项目部署成本约 5 万元"【第三方 36氪】 | 第三方称"自研大模型"【36氪】、"接入 DeepSeek"【导航站】；一篇技术复盘称架构为 RAG + QLoRA 微调 + 多模态解析【第三方】 | 官网写"政府采购、工程建设、设备采购、制造业、信息化项目、企业服务类投标" | 说法互相矛盾：36氪称 SaaS 1888 元/月；AI铺子称 88 元/月、288 元/月、年卡 1888 元；导航站称 299 元/月【均为第三方】 | 官网明确列出"信息化项目、企业服务类投标"；第三方评测称其偏 IT 领域【疑似软文】 | https://qiaowenshu.cn/ ；https://www.36kr.com/p/3440772674622852 ；https://www.aipuzi.cn/ai-tools/qiaowenshu.html ；https://gitcode.csdn.net/6a229f4010ee7a33f2780aa9.html |
| **讯飞 星火投标 / 招采智能体平台 2.0** / 科大讯飞 | 招采全链路智能体平台（招标、投标、开标、评标、定标、监督、履约）；"Harness 可信执行引擎"用规则和公式引擎做强校验，降低幻觉【官方新闻】。"星火投标"是官网"营销重塑"下的独立产品【官网导航】 | 支持：私有化版本可对接 OA/SRM/ERP 并深度定制；与华为联合发布**基于昇腾的智能招采一体机**【官方新闻】 | 星火大模型；官网新闻称已适配星火 X2.5【官方新闻】 | 偏招采全链路，招标方和评标侧占比很重 | 公有云版"按量付费"【官方新闻】。导航站给出的"299 元/月"与该站对巧文书的报价完全相同，**高度存疑** | 导航站称覆盖"服务投标：人员配置、服务流程方案"【第三方，存疑】；官方页面未查到运维专项 | https://www.iflydigital.com/2026/07/13/wechat-0f8c25723b84068f48aa/ ；https://www.ai-zhushou.cn/sites/3037.html |
| **广联达 云清标 AI 编标** | 解析招标基础信息、技术标评分要求、**废标项**、技术标准、**暗标要求**、格式要求，并能点击跳转原文；解析图纸与工程量清单（GBQ/电子标）；目录可"严格按评标办法"生成；施工组织设计图文生成；对接斑马进度生成横道图；按地区暗标规则库导出【第三方操作指南】 | 未查到（网页版 SaaS） | 未在该指南中说明 | **工程类（施工组织设计）** | 按生成字数扣"权益"，具体价格未查到 | 不适配服务类 | https://www.fwxgx.com/articles/249312 |
| **千里马招标网 AI 标书 / 标书评分** | 上传招标文件生成标书；智能荐标；标书评分体检（合规性、技术分、商务分）【官网】 | 未查到 | 官网称"与 Deepseek 等合作开发" | 通用（以标讯数据服务为主） | 未查到 | 标讯侧可按"合同到期"筛选运维、维保类项目【官网】 | https://www.qianlima.com/news/684.html |
| **快标书 AI** | 解析评分标准和写作要点（服务要求、人员设备）、目录与正文生成、超长文档、导出 Word；官网称"微调标书大模型"【官网】 | 未查到 | 官网只写"微调标书大模型" | 服务、货物、工程、政府采购 | 未查到 | **官网明确写了服务类（含信息化服务）：可生成服务方案、实施计划、人员配置、服务保障措施、应急预案**【官网】 | https://www.kuaibiaoshu.com/ |
| **投标官** / 舍予基业 | 逐页解析并**标注页码和条款号**，★实质性要求自动标记；"响应矩阵"把要求、响应、证据、章节放在一张表对照；按册按节成文，引用带 [证据] 标记；**没有依据的地方写【待补】，不编造**；17 条合规规则（如"证书有效期覆盖递交日"、"三处报价一致"、"报价 ≤ 最高限价"）；占位符未清零时禁止导出【官网】 | 未查到 | 未查到 | 通用 | 未查到 | 对"原厂授权/证书匹配"类需求的设计很对口（证据挂接 + 证书有效期校验），但未查到运维专项模板 | https://toubiao.agecms.com/ |
| **智标枪** | 解析项目概况、评分细则、**废标项**；目录大纲；按章节调用企业知识库（资质、方案、历史标书）；评分点覆盖率提示；检查工具【官网】 | 官网列出"SaaS / 公有云 / 专属交付私有化"【官网】 | 未查到 | 通用 | 未查到 | 官网示例含"实施方案、质量说明、交付安排"，未见运维专项 | https://www.bid-gun.com/ |
| **埃文 AI 标书智能编制系统** | 解析、生成、合规预审、实时法规库、行业知识图谱【第三方专栏】 | 称提供 SaaS / 私有化 / 混合 / 边缘四种部署、信创适配【第三方专栏，疑似厂商自发】 | 称用 NLP + 大模型 + RAG，具体模型未查到 | 通用 | 未查到 | 未查到 | https://zhuanlan.zhihu.com/p/2053134517418857674 （本轮 WebFetch 返回 500，只看到搜索摘要） |
| **云境标书 AI** | 解析、生成、知识库、合规扫描、排版【第三方】 | **来源矛盾**：IT之家称支持 SaaS / 半私有化 / 私有化；cnblogs 称"无本地化部署能力" | 一篇 cnblogs 评测称"通用大模型套壳"【疑似软文】 | 医疗、工程、IT、咨询、物流 | IT之家：标准月卡 88 元/月（100 万字）起【第三方】 | 未查到 | https://www.ithome.com/0/999/392.htm ；https://www.cnblogs.com/shuju-biao-shu-guan/p/21810923 |
| **标小信** | 解析、目录、内容防重、支持明标/暗标【第三方】 | IT之家称"仅 SaaS" | 未查到 | 中小企业 | 月卡 68 元起【第三方】 | 未查到 | https://www.ithome.com/0/999/392.htm |
| **智标领航** | 侧重制标流程管理（任务分工、留痕、偏离表、席位），附带 AI 生成【第三方】 | "SaaS 为主"【第三方】 | 未查到 | 成熟制标团队 | 按席位报价（未查到数额） | 未查到 | https://www.ithome.com/0/999/392.htm |
| **快写文书 AI / 小象标书 / AIWork365 易中标 / 文兜智写 / 飞标书 / 慧中标** | 只在疑似软文类评测中出现，官网未核实 | 各评测说法不一 | 未核实 | — | 各评测报价互相矛盾（如易中标、文兜智写都写"3699 元/年起"） | 未查到 | https://www.cnblogs.com/Growth-UME/p/21721241 ；http://www.jsqmd.com/news/983207/ |
| **百度智能云 TextMind 智慧招采**（对照项） | 招标文件智写、招标文件审查、围串标审查、智能辅助评标【官网】 | 未在该页说明 | 文心（据搜索摘要，页面未写明） | **招标方 / 评标侧**，不是投标侧 | 未查到 | 不直接适用 | https://cloud.baidu.com/product/AI_TM/bidding.html |
| **阿里云百炼·全妙**（对照项） | 公文、合同审查、标书生成等智能创作平台【官方社区文】 | 未查到 | 通义（据搜索摘要） | 政企通用写作 | 未查到 | 未查到 | https://developer.aliyun.com/article/1688750 |
| **华为云商店"投标智能体"方案（PDF 未写厂商名）**（架构参考） | 情报与竞对分析、招标文件解析、投标文件生成、合规审查；"三库"（资质、案例、人员）构建 | 支持私有化和 SaaS；提供昇腾、寒武纪、海光、飞腾、龙芯芯片适配以及麒麟/统信系统适配服务 | 架构图列出 **Qwen3-VL、Qwen3-Embedding、Qwen3-Reranker**，以及 Milvus、Elastic、LangChain/LlamaIndex | 文中写"适配服务类招投标流程" | 未查到 | 写了"服务类"，但未见运维细节 | https://mkp-res.hc-cdn.com/marketplace/public/appv2/attachment/CC7/180/A34/0000000000CC7180A34.20260309084332.573fd92c78dc4eb7ba017c39ce691075.pdf |

---

## (b) 海外产品对比表（RFP / Proposal Automation）

| 产品 | 定位与核心功能 | 可借鉴的设计 | On-prem / 部署选项 | 公开价格 | 来源 |
|---|---|---|---|---|---|
| **Responsive（原 RFPIO）** | 全生命周期"SRM"平台：Intake 和 go/no-go、Requirements Analysis（shredding、责任矩阵、追踪矩阵、Document Analyzer）、AI Agents、受治理的内容库（过期与保留策略）、Ask（带来源的问答）、审计日志、Business Unit 隔离、MCP Server【官网】 | **TRACE Score**：从可信度、相关性、准确性、完整性、可解释性五个维度给 AI 答案打分（满分 100），用来分流人工复核量【第三方 VisibleThread】；内容过期治理；按事业部隔离内容 | **无 on-prem**。可选 Dedicated Cloud（单租户）和 AWS GovCloud【官网】 | 三档（Emerging / Growth / Enterprise），价格需询价【Responsive 博客】 | https://www.responsive.io/product-packages/platform ；https://www.responsive.io/blog/best-rfp-software ；https://www.visiblethread.com/blog/rfp-software-aec/ |
| **Loopio** | 以可复用内容库为核心，配 AI "Magic"起草、项目协作；连接 80+ 内容源【第三方】 | 以内容库为中心的问答复用；有 G2 用户反馈 Magic 答案相关性不稳定【Responsive 博客引用 G2】 | 官网安全页写明数据托管在 **AWS**，采用逻辑隔离；**未见 on-prem 选项**【官网】 | 未查到 | https://loopio.com/platform/security/ ；https://www.responsive.io/blog/best-rfp-software |
| **AutoRFP.ai** | 解析 Word/Excel/PDF 并生成答案；Trust Score 并展示来源；自建库（结项后自动归档打标签）；浏览器插件（支持 Ariba 等采购门户）；提供 MCP/OpenAPI【官网 / 第三方】 | **按项目计价、不限用户**；找不到高置信内容时留空并给出候选，不强行编答案 | **仅云**；数据可驻留 EU/US/AU【第三方 VisibleThread】 | Scale **$899/月**（年付，每年 24 个项目）；Accelerate **$1,299/月**（每年 50 个项目）；Enterprise 定制【官方帮助中心】 | https://learn.autorfp.ai/en/articles/12684326-how-to-manage-your-billing-and-understand-your-plan-type ；https://autorfp.ai/ ；https://www.visiblethread.com/blog/rfp-software-aec/ |
| **Inventive AI** | 基于知识库起草首稿，"knowledge hub"对接 Drive / SharePoint / Dropbox，提供评分与建议【第三方 Responsive 博客】 | 知识源实时连接，不依赖静态库 | 未查到（官网本轮抓取超时） | 未查到 | https://www.responsive.io/blog/best-rfp-software |
| **Arphie** | AI-native RFP / DDQ / 安全问卷工具；实时连接 Drive / SharePoint / Confluence 等；每个答案附来源引用和置信度【官网 / 搜索摘要】 | "Trust-first"：答案逐条带出处 | SaaS；SOC 2 Type 2；与 OpenAI、Anthropic 签有零数据保留协议；**未见 on-prem**【官网】 | 未查到 | https://www.arphie.ai/security |
| **AutogenAI** | 长篇 proposal 写作，"custom language engine"学习企业文风，含 Qualify & Extract 和证据溯源【第三方】 | 学习企业文风；每条论断可追溯到证据 | 联邦版称经 Palantir FedStart 获 FedRAMP High【第三方 VisibleThread 转述】；on-prem 未查到 | 未查到 | https://www.visiblethread.com/blog/rfp-software-aec/ |
| **Qvidian（Upland）** | 老牌 proposal 管理：内容库（过期、使用追踪）、审批流、Office 深度集成【第三方】 | 在 Word 内直接写作 | 未查到 | 需询价 | https://www.responsive.io/blog/best-rfp-software |
| **GovDash**（美国政府采购） | 解析整个招标包（含附件和修订）到句子级，生成随修订更新的**合规矩阵**（Sections L/M/C）；从需求映射到大纲；Word/Excel/PPT 插件；自动带出过往业绩（past performance）【官网】 | **合规矩阵 + 修订追踪 + 可溯源** | 未查到 | 未查到 | https://www.govdash.com/proposal |
| **VisibleThread** | 需求抽取用**确定性规则**（shall/will/must），同样的输入总得到同样的输出；AI 只负责起草；支持修订对比、风险条款检测、Word 插件【官网博客】 | **"合规抽取走规则、写作走 AI"的分工**，很适合用来做废标项检查 | **支持 on-prem（含 air-gapped / SCIF）**、Azure GCC High、AWS GovCloud、商业云【官网博客，属厂商自评】 | 未查到 | https://www.visiblethread.com/blog/rfp-software-aec/ |
| **Specgen**（法国） | 分析招标文件包（DCE）、在客户的 Word/Excel 模板中起草、**BidMatching 逐条核对需求覆盖**，引用带出处；也有招标方模块 | "1 个机柜起步"的软硬一体交付；先做 3 个月实测再签约 | **只做 On-Premise / Air-Gapped**，零外呼；使用开源权重模型【官网】 | 机柜一次性价格 + 月订阅，不按用量计费；具体金额未公开【官网】 | https://specgen.ai/why-specgen.php |
| **RFPlex.ai**（欧盟） | 抽取问题、基于 RAG 起草并按置信度评分、合规矩阵（C/PC/NC）、Go/No-Go 评分、知识库健康检查（90 天过期提醒、重复与冲突检测）、低置信暂停人工审核 | 知识库治理（过期、冲突检测）、**置信度阈值人审** | **完全本地**：通过 Ollama 跑自托管 LLM，零外部 API；Beta 期免费【官网】 | Beta 免费；称付费档将提供 Qwen 32B / DeepSeek-R1 等更大模型【官网】 | https://rfplex.ai/ |

---

## (c) GitHub 开源项目表

> Star 数和最近推送日期来自 GitHub API / 搜索（2026-09-28 查询，日期为 UTC）。"二次开发"一栏依据许可证，**不构成法律意见**。

### c1. 标书 / 投标垂直项目

| 项目 | Stars | 最近 push | 许可证 | 要点 | 能否二次开发 |
|---|---|---|---|---|---|
| [FB208/OpenBidKit_Yibiao](https://github.com/FB208/OpenBidKit_Yibiao)（易标） | 3053 | 2026-09-28 | AGPL-3.0 | Electron + React 桌面端；招标文件解析（18 个解析项）、多标段、全文一致性检查、本地知识库、多份标书查重、废标项检查、错别字 / 逻辑检查、插件系统、开放 API；支持 OpenAI 兼容接口及 Ollama / LM Studio 本地模型；文档解析可接 MinerU。注意：部分在线服务依赖 Cloudflare Worker（公告、许可证、统计） | 可以，但 **AGPL**：修改后分发或通过网络提供服务都要开源；内部自用也需评估"网络服务"条款 |
| [guangshu100/BidMaster-Pro](https://github.com/guangshu100/BidMaster-Pro) | 331（0 fork，README 以"star 后加作者微信"引流，热度存疑） | 2026-09-03 | GitHub 识别为 AGPL-3.0，但 README 写 MIT（**许可证冲突，需核实**） | FastAPI + LangGraph + LiteLLM + ChromaDB + PostgreSQL / Redis / MinIO / Celery，提供 Docker 部署；四阶段流程（解读、生成、21 项合规检查、排版）；RBAC 角色（管理员、项目经理、编写员、审核员）；可接自部署 MinerU OCR；可降级到 Ollama/Qwen | 架构参考价值高；使用前必须先澄清许可证 |
| [Get00/BiaoShu-SKILL](https://github.com/Get00/BiaoShu-SKILL) | 164 | 2026-09-24 | Apache-2.0 | Agent Skill 形态，14 步流程；**带 IT/信息化行业指南**，能自动识别行业；提供智能占位符（图片、表格、资质） | 可以（Apache-2.0 较宽松） |
| [xinsuifan-web/Tender-Assistant-V2.5](https://github.com/xinsuifan-web/Tender-Assistant-V2.5) | 101 | 2026-09-01 | 无许可证 | 投标工作流 Agent 原型 | **无许可证，默认保留全部权利，不能直接二开** |
| [zeronezer/bidcraft](https://github.com/zeronezer/bidcraft)（标书匠） | 62 | 2026-09-17 | Apache-2.0 | 基于 LangGraph 的对话式技术标编制，"LLM-Wiki"路线，偏工程类 | 可以 |
| [milkoloa/AIBS](https://github.com/milkoloa/AIBS) | 35 | 2025-06-11 | 无许可证 | 后端 API：解析、生成大纲、生成正文、导出、模板管理 | 无许可证，不能直接二开；可参考接口设计 |
| [Hugin-Z/tender-writer-v3](https://github.com/Hugin-Z/tender-writer-v3)（v1 在 [gitee](https://gitee.com/hugin-z/tender-writer)） | 5 | 2026-06-10 | MIT | 五阶段可审计流程：解析 → **评分矩阵 CSV** → 提纲反推 → 分章撰写 → 合规终审；素材分 own / partner / reference 三级隔离，防止误引用竞品业绩；**不允许一键生成整本标书** | 可以；方法论价值高 |
| [shandianT/bid-dog](https://github.com/shandianT/bid-dog)（中标狗） | 7 | 2026-09-24 | NOASSERTION | 桌面端，覆盖读标、评分与废标检查、素材复用、Word 出件 | 许可证不明，需核实 |
| [weilai00332/Bidagent-studio](https://github.com/weilai00332/Bidagent-studio) | 1 | 2026-09-02 | AGPL-3.0 | 招标解析 + 企业知识匹配 | 同 AGPL 约束 |
| [zhiqianzheng/BidMonitor-AI](https://github.com/zhiqianzheng/BidMonitor-AI) | 199 | 2025-12-19 | 无许可证 | 标讯监控（用 Selenium 采集，LLM 过滤）。注意 README 自称"绕过反爬"，有合规风险 | 无许可证；不建议使用 |
| 1superblack/engineering-bid-document-generator | — | — | — | 搜索结果显示它曾支持服务类（物业 / 政府采购）和 14 维差异化，**但仓库现已 404，无法访问** | 不可用 |

### c2. RAG / 知识库 / 长文档生成基础设施

| 项目 | Stars | 最近 push | 许可证 | 要点 | 二次开发注意 |
|---|---|---|---|---|---|
| [langgenius/dify](https://github.com/langgenius/dify) | 157,375 | 2026-09-28 | 修改版 Apache-2.0 | 工作流、RAG Pipeline、Agent；最低配置 CPU ≥ 2 核、RAM ≥ 4 GiB | **多租户运营和去掉前端 LOGO 需要商业授权**；企业内部单租户使用一般可行 |
| [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | 91,399 | 2026-09-28 | Apache-2.0 | "深度文档理解"（DeepDoc），支持 Word、PPT、Excel、图片、PDF、**影印件、复印件**；最低 CPU ≥ 4 核、RAM ≥ 16 GB、Disk ≥ 50 GB；DeepDoc 可用 GPU 加速 | 宽松 |
| [labring/FastGPT](https://github.com/labring/FastGPT) | 29,760 | 2026-09-28 | FastGPT Open Source License（Apache-2.0 + 附加条款） | 知识库 + Flow 工作流；支持 PDF / Docx / PPTX / XLSX 等 | 不能做同类多租户 SaaS，不能改 LOGO |
| [1Panel-dev/MaxKB](https://github.com/1Panel-dev/MaxKB) | 22,883 | 2026-09-28 | GPL-3.0 | RAG + 工作流 + MCP；支持 DeepSeek / Qwen 等私有模型；提供离线安装文档 | GPL 传染性（分发时需开源） |
| [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | 39,890 | 2026-09-27 | MIT | 轻量图谱 RAG | 宽松 |
| [chatchat-space/Langchain-Chatchat](https://github.com/chatchat-space/Langchain-Chatchat) | 38,667 | 2025-11-10 | Apache-2.0 | 本地知识库问答，近期更新放缓 | 宽松 |
| [netease-youdao/QAnything](https://github.com/netease-youdao/QAnything) | 14,193 | 2026-09-23 | AGPL-3.0 | 文档问答 | AGPL |
| [stanford-oval/storm](https://github.com/stanford-oval/storm) | 31,513 | 2025-09-30 | MIT | "先研究再写长文"，大纲驱动的长文生成范式 | 宽松；可借鉴大纲→分节生成的思路 |
| [THUDM/LongWriter](https://github.com/THUDM/LongWriter) | 1,875 | 2025-06-24 | Apache-2.0 | 万字级长文生成（ICLR 2025） | 宽松 |

### c3. 文档解析 / OCR

| 项目 | Stars | 最近 push | 许可证 | 要点 |
|---|---|---|---|---|
| [opendatalab/MinerU](https://github.com/opendatalab/MinerU) | 80,751 | 2026-09-28 | "MinerU Open Source License"（Apache-2.0 + 附加条款：MAU 超 1 亿或月收入超 2000 万美元需要商业授权；对外提供在线服务须标注使用了 MinerU）。注意：HF 上的 MinerU2.5 VLM 权重标注为 AGPL-3.0 | 支持 PDF（含扫描件）、图片、DOC/DOCX、PPT、XLS、**OFD** 等；擅长 OCR、表格、公式；basic 档 CPU 即可运行，standard/advanced 档需 8GB+ 显存 GPU；NPU 等国产卡需自行安装适配版 torch/vllm |
| [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | 90,309 | 2026-09-16 | Apache-2.0 | PaddleOCR-VL-1.6（0.9B）文档 VLM，支持表格和**印章**识别；PP-StructureV3 输出表格单元格坐标；硬件徽章标注支持 cpu/gpu/xpu/npu；可导出 DOCX |
| [docling-project/docling](https://github.com/docling-project/docling) | 68,092 | 2026-09-28 | MIT | 支持 PDF / DOCX / XLSX 等，解析版面、阅读顺序、表格结构，**支持本地和 air-gapped 运行**，扫描件 OCR |
| [datalab-to/marker](https://github.com/datalab-to/marker) | 40,023 | 2026-09-13 | Apache-2.0（仓库许可证；模型权重条款未核实） | PDF → Markdown/JSON |
| [Unstructured-IO/unstructured](https://github.com/Unstructured-IO/unstructured) | 15,509 | 2026-09-27 | Apache-2.0 | 通用 ETL |
| DeepSeek-OCR-2（[HF](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2)） | — | 2026-02 | Apache-2.0 | 3B OCR VLM；vLLM Recipes 标注 BF16 约 7G |

---

## (d) 私有化技术栈候选与硬件量级

### d1. 可私有化的国产开源大模型（2026-09 现状，以 HF 元数据和官方仓库为准）

> 显存列来自 vLLM Recipes 模型卡片标注的**各精度权重占用**（不含 KV 缓存和并发余量）。实际部署还要按上下文长度和并发量增加显存。

| 档位 | 模型 | 参数（总/激活） | 许可证 | 权重显存（vLLM Recipes） | 硬件量级（证据 / 推算） | 来源 |
|---|---|---|---|---|---|---|
| 轻量 | **Qwen3.6-35B-A3B**（MoE） | 35B / 3B | Apache-2.0 | BF16 84G；FP8 42G；NVFP4 21G | 【推算】FP8 权重约 42G，可放进单张 80GB 卡或 2×48GB 卡，留出 KV 缓存 | https://huggingface.co/Qwen/Qwen3.6-35B-A3B ；https://recipes.vllm.ai/Qwen |
| 轻量 | **Qwen3.8-27B**（Dense，2026-08） | 27.8B | Apache-2.0 | BF16 67G；FP8 38G；INT4 24G | 官方示例：vLLM/SGLang `--tensor-parallel-size 4`，上下文 262K【官方 README】 | https://github.com/QwenLM/Qwen3.5 （README 已更名 Qwen3.8）；https://recipes.vllm.ai/Qwen |
| 轻量 | GLM-4.7-Flash | 约 31B（HF 元数据） | MIT | 未在 Recipes 列表中找到 | 未查到官方硬件说明 | https://huggingface.co/zai-org/GLM-4.7-Flash |
| 中档 | **Qwen3.5-122B-A10B** | 122B / 10B | Apache-2.0 | BF16 293G；FP8 147G；INT4 74G | 【推算】FP8 需 2×96GB 或 4×80GB 量级 | https://huggingface.co/Qwen/Qwen3.5-122B-A10B ；https://recipes.vllm.ai/Qwen |
| 中高档 | **DeepSeek-V4-Flash**（2026-04 预览，0731 正式版） | 284B / 13B，1M 上下文 | MIT | FP8 约 170–200G | vLLM Recipes 写明已验证 **8×RTX PRO 6000（96GB，PCIe）** 单机运行；H200/B200 每个副本用 4 张卡；MI325X 单卡仅在 4K 上下文下验证通过 | https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash ；https://recipes.vllm.ai/deepseek-ai/DeepSeek-V4-Flash |
| 旗舰 | Qwen3.5-397B-A17B | 397B / 17B | Apache-2.0（据 Recipes 列表，HF 未单独核实） | FP8 477G；INT4 239G | 【推算】8×80GB 以上 | https://recipes.vllm.ai/Qwen |
| 旗舰 | GLM-5.2 | 约 743–753B / 39B | MIT | FP8 893G；MXFP4 446G | 第三方部署指南称 FP8 需 8×H200 / H100 起【第三方】 | https://huggingface.co/zai-org/GLM-5.2 ；https://recipes.vllm.ai/zai-org ；https://www.spheron.network/blog/deploy-glm-5-2-gpu-cloud/ |
| 旗舰 | DeepSeek-V4-Pro / V3.2 | 1.6T / 49B；671B / 37B | MIT | V4-Pro FP8 960G；V3.2 FP8 805G | BentoML 称 V3/R1 需要 8×H200（141GB）【第三方】 | https://recipes.vllm.ai/deepseek-ai ；https://www.bentoml.com/blog/the-complete-guide-to-deepseek-models-from-v3-to-r1-and-beyond |
| 超大（不建议企业内部部署） | Qwen3.8-2.4T-A95B | 2.4T / 95B | license: other | FP8 2996G | 多机集群 | https://huggingface.co/Qwen/Qwen3.8-2.4T-A95B |
| 向量 / 重排 | Qwen3-Embedding-8B、Qwen3-Reranker-8B；BAAI/bge-m3 | 约 8B；bge-m3 较小 | Apache-2.0；MIT | — | 【推算】单张 24GB 级显卡即可放下 | https://huggingface.co/Qwen/Qwen3-Embedding-8B ；https://huggingface.co/BAAI/bge-m3 |

**推理框架**：vLLM（92.8k star，Apache-2.0）、SGLang（36.5k，Apache-2.0）、Ollama（181.8k，MIT，适合试验，BentoML 称其"不适合高吞吐企业部署"）。来源：GitHub 元数据；https://www.bentoml.com/blog/the-complete-guide-to-deepseek-models-from-v3-to-r1-and-beyond

**国产算力 / 信创**
- 讯飞与华为发布**基于昇腾的智能招采一体机**【官方新闻】
- 华为云商店投标智能体方案列出昇腾、寒武纪、海光、飞腾、龙芯的芯片适配服务
- PaddleOCR 标注支持 npu；MinerU 在 npu/musa/mlu 等卡上需自装 torch/vllm
- NVIDIA 高端卡在国内能否采购，本轮未调研，需另行确认

### d2. RAG / 知识库框架对比（投标场景）

| 框架 | 优势（来源口径） | 局限与注意 | 许可证要点 |
|---|---|---|---|
| **RAGFlow** | DeepDoc 深度文档理解，支持影印件和复印件，适合解析招标文件和资质扫描件 | 最低 16GB RAM；是"知识库引擎"，不负责长文生成 | Apache-2.0 |
| **Dify** | 可视化工作流和 Agent，适合编排"解析 → 抽取 → 分节生成 → 检查"全流程 | 内置文档解析偏通用 | 多租户运营和去 LOGO 需商业授权 |
| **FastGPT** | 知识库 + Flow 工作流，中文社区活跃 | 同上，有附加条款 | 附加条款 |
| **MaxKB** | 部署简单，支持离线安装，模型无关 | 深度生成能力需要自己编排 | GPL-3.0 |

一种组合思路（【推算】，仅供参考）：**MinerU / PaddleOCR 负责解析 → RAGFlow 或自建向量库负责检索 → Dify 或 LangGraph 负责编排 → 规则引擎负责废标 / 合规检查**。华为云方案 PDF 的架构图就是 Qwen3-VL + Qwen3-Embedding + Qwen3-Reranker + Milvus/Elastic + LangChain/LlamaIndex 的组合，可作为同类参考。

### d3. 文档解析方案要点
- **招标文件（PDF/Word）**：MinerU（支持 OFD，擅长表格和公式，CPU 也能跑）、docling（MIT，air-gapped）、RAGFlow DeepDoc。
- **扫描件、资质证书、原厂授权函、盖章页**：PaddleOCR-VL-1.6 称增强了**印章**识别；PP-StructureV3 可输出表格单元格坐标。
- **表格（评分表、偏离表、人员配置表）**：MinerU、PP-StructureV3、docling 都声明支持表格结构识别。
- 广联达的做法（第三方操作指南）：解析结果可点击跳转回原文位置，方便人工核对。这是很值得借鉴的交互。

---

## (e) 关键发现

1. **市场主流功能已经基本趋同，形成"读标 → 目录 → 写标 → 审查 → 知识库复用"五段式。** 巧文书官网列的五个核心功能、钛投标 llms.txt 写的"读标、解析、生成、检查、复用"、广联达的解析项（评分要求、废标项、暗标、格式）、智标枪的"评分细则 / 废标项"几乎一致。差异主要在四处：行业模板深度、合规检查规则数、证据溯源能力、部署形态。来源：https://qiaowenshu.cn/ ；https://taitoubiao.com/llms.txt ；https://www.fwxgx.com/articles/249312 ；https://www.bid-gun.com/

2. **差异化的方向是"可溯源、不编造"，而不是"写得更快"。** 投标官做了页码/条款号标注、要求 × 证据 × 章节的响应矩阵、【待补】占位、占位符未清零禁止导出、证书有效期校验；海外 VisibleThread 用确定性规则抽取需求、只让 AI 起草；Responsive 用 TRACE Score 分流复核；AutoRFP 在无高置信内容时留空。IT之家的盘点也把"AI 编造业绩、资质"列为最高风险。来源：https://toubiao.agecms.com/ ；https://www.visiblethread.com/blog/rfp-software-aec/ ；https://www.ithome.com/0/999/392.htm

3. **私有化的常见做法是"SaaS + 企业版 + 私有化"三档，私有化按项目单独报价，同时强调信创和昇腾适配。** 钛投标、巧文书、智标枪、讯飞都提供私有化；讯飞和华为推出软硬一体的"招采一体机"；海外 Specgen 走"机柜 + 月订阅"。私有化价格没有官方公开数字。第三方说法有"巧文书单项目约 5 万元"、"钛投标私有化 10 万元起"，均未核实。来源：https://www.iflydigital.com/2026/07/13/wechat-0f8c25723b84068f48aa/ ；https://specgen.ai/why-specgen.php ；https://www.36kr.com/p/3440772674622852 ；https://www.ithome.com/0/999/392.htm

4. **私有化的难点：算力、模型选型、知识库维护、运维升级责任。** 从 vLLM Recipes 数据看，能在单机 8 卡内运行的强模型是 DeepSeek-V4-Flash 这一档（已验证 8×96GB 卡）；Qwen3.6-35B-A3B / Qwen3.8-27B 这一档 FP8 权重约 40GB，门槛低很多。GLM-5.2 / V4-Pro 这类旗舰需要约 900GB 显存级别，不适合一般企业内部部署。第三方私有化评估文列出的关注点包括：是否接入自有 DeepSeek 算力、统信/麒麟适配、并发扩容、知识库清洗、权限审计、升级责任。IT之家也提醒知识库陈旧会直接拉低输出质量。来源：https://recipes.vllm.ai/deepseek-ai/DeepSeek-V4-Flash ；https://recipes.vllm.ai/Qwen ；https://gitcode.csdn.net/6a2bc14a10ee7a33f27bbcc8.html ；https://www.ithome.com/0/999/392.htm

5. **【服务类 / IT 运维 / 数据库维保标书专条】这类标的生成特点与现有产品覆盖情况**
   - **标书特点**（来自招标原文和行业指南）
     - (i) **原厂授权 / 伙伴资质是资格门槛**：例如某数据库维保公告要求"原厂对本项目的投标授权文件"，且投标人和三家原厂分别出具承诺函；国开行 Oracle 维保项目要求非原厂商提供原厂正式授权或代理证明。
     - (ii) **SLA 分级承诺**：例如某公告要求《限时服务承诺函》，一级故障 15 分钟响应、2 小时到场、2 小时恢复，二、三级依次放宽，并要求 7×24 服务。
     - (iii) **人员配置可验证**：驻场人员持原厂认证（如 TDSQL、GBase 认证）、工作年限、简历、社保、劳动合同；指南强调"要写具体人名和证书"，只写人数无法得分。
     - (iv) **巡检报告、服务成果、应急预案、培训计划**是必交内容。
     - (v) 同一份标书往往覆盖**多种数据库**（Oracle / MySQL / TiDB / 达梦 / GoldenDB 等），每种的授权和证书要求都不同。
   - **推论**：这类标书技术方案的比重较轻，"资质 / 证书 / 授权与人员的逐条匹配 + SLA 承诺一致性"比重更大，更适合"结构化资料库 + 规则校验"，而不是纯粹的长文生成。
   - **产品覆盖**
     - 快标书 AI 官网明确列出服务类（含信息化服务），可生成服务方案、人员配置、服务保障措施、应急预案。
     - 巧文书官网列有"信息化项目、企业服务类投标"。
     - 钛投标官网列有"信息化服务"，其自有库包含人员和资质。
     - 投标官的证据挂接和"证书有效期覆盖递交日"规则，最接近原厂授权 / 证书匹配的需求。
     - 开源项目中 BiaoShu-SKILL 带 IT/信息化行业指南。
     - **没有查到任何产品公开提供"数据库维保 / IT 运维"专项模板、SLA 矩阵生成器，或按数据库品牌匹配原厂授权与认证的功能。** 这部分很可能要靠自建"人员-证书-授权"结构化库和规则来补。
   - 来源：https://www.qianlima.com/bid-630971606.html ；https://www.qianlima.com/bid-620107340.html ；https://cg.cdb.com.cn/cmscaigou/9f98ff019e91439fafed687894d3e8ea.html ；https://biaoshuzhizuo.com/knowledge/industry-guides/it-tender-guide/ ；https://www.getbidwin.cn/yun-wei-fang-an-biao-shu-zhi-zuo-ji-gou.html （代写机构经验谈，属第三方）；https://www.kuaibiaoshu.com/ ；https://qiaowenshu.cn/ ；https://toubiao.agecms.com/

6. **"招标方 / 评标侧"和"投标侧"是两条不同赛道，选型时别混淆。** 百度 TextMind 智慧招采做招标文件智写、审查、围串标审查、辅助评标；讯飞招采智能体偏全链路和评标（"Harness"用规则和公式强校验）。投标方需要的是投标文件生成和自查。不过评标侧的"规则 + 公式强校验"思路可以反向用于投标自查。另外，讯飞新闻提到"发改法规〔2026〕195号文"推动"AI + 招投标"，政策原文本轮未核实。来源：https://cloud.baidu.com/product/AI_TM/bidding.html ；https://www.iflydigital.com/2026/07/13/wechat-0f8c25723b84068f48aa/

7. **开源方案可以作为二开起点，但许可证是主要约束。** 最活跃的易标（3053 star）是 **AGPL-3.0**；BidMaster-Pro 的许可证自相矛盾（AGPL / MIT）；多个项目没有许可证。基础设施层中，Dify 和 FastGPT 的附加条款限制多租户和 LOGO，MaxKB 是 GPL，MinerU 有附加条款且 VLM 权重是 AGPL，RAGFlow、docling、PaddleOCR、vLLM 的许可证较宽松。来源：见 (c) 表中各仓库链接；https://raw.githubusercontent.com/langgenius/dify/HEAD/LICENSE

8. **海外产品可借鉴的设计主要有五点：** (1) 内容库治理（过期提醒、重复与冲突检测、按事业部隔离）【Responsive、RFPlex】；(2) 答案置信度评分，低于阈值暂停交人审【Responsive TRACE、RFPlex、AutoRFP】；(3) 合规矩阵随招标文件修订 / 答疑自动更新【GovDash、VisibleThread】；(4) 在 Word 插件内写作【GovDash、VisibleThread、Qvidian】；(5) 按项目计价、不限席位【AutoRFP】。主流海外 SaaS（Loopio、AutoRFP、Arphie、Responsive）**都没有 on-prem 选项**；支持 on-prem / air-gapped 的是 VisibleThread、Specgen、RFPlex 这类面向政府或主权场景的厂商。来源：https://www.responsive.io/product-packages/platform ；https://rfplex.ai/ ；https://www.govdash.com/proposal ；https://learn.autorfp.ai/en/articles/12684326-how-to-manage-your-billing-and-understand-your-plan-type ；https://loopio.com/platform/security/

---

## 附：未查到 / 存疑清单

- **价格**：钛投标、巧文书、云境、易中标等产品的价格只有第三方或疑似软文来源，且互相矛盾。钛投标官网定价页为 JS 渲染，未能抓取。所有厂商的私有化报价都没有官方公开数字。
- **星火投标**：官方产品页未能抓取（iflydigital 首页 504）。导航站给的价格与该站对巧文书的描述逐字相同，判断为不可信。
- **埃文 AI 标书**：知乎原文 WebFetch 返回 500，只看到搜索摘要。
- **云境标书 AI 是否支持私有化**：IT之家与 cnblogs 说法相反。
- **钛投标"军工二级保密资质、国密甲级"等资质**：只见于疑似软文；官网 llms.txt 只写"算法备案、昇腾认证（以官方公示为准）"。
- **快写文书 AI / 小象标书 / 易中标 / 文兜智写 / 飞标书 / 慧中标**：只在评测软文中出现，本轮未核实官网。
- **Inventive AI 官网**：抓取超时，部署方式未查到。
- **GitHub 数据**：1superblack/engineering-bid-document-generator 已 404；BidMaster-Pro 的 star 数（331 star、0 fork）和许可证都存疑。
- **模型与硬件**：Qwen3.5-397B 的许可证只依据 vLLM Recipes 列表，未在 HF 上单独核实；GLM-5.2 的硬件需求只有第三方来源；NVIDIA 高端卡在国内的可采购性未调研。
- **政策**："发改法规〔2026〕195号文"只从讯飞新闻中转引，原文未核实。
- **数据库维保 / IT 运维专项**：没有查到任何产品提供数据库维保 / 运维专项模板或 SLA 矩阵功能。
