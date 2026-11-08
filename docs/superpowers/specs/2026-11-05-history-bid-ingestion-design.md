为什么有这个文件：记下已经确认的历史标书与资料库解析设计，供后续实现按同一口径改代码。

它解决什么问题：避免实现时只记住对话里的补充，而把用户确认的解析方案丢掉；也避免把设计写成已经部署或已经验收。

# 历史标书与资料库解析设计

状态：用户已确认设计，尚未改解析代码，尚未部署到 RAGFlow。确认日期：2026-11-05。关联 [ISSUE-050](../../../issues/ISSUE-050.md)。

主规格是用户确认的「历史标书技术方案智能解析管道」。本文把该方案落成可实现的条目。文末「补充」只记录用户明确改过或方案没写死的地方。两边冲突时，补充覆盖方案。

## 1. 要做成什么

公司知识库保留两类 RAGFlow 数据集，各用一条 ICG 入库管道。管道定义在 `backend/bid-core/icg/infra/ragflow_pipelines.py`，由现有「部署 / 升级」写到当前连接的 RAGFlow。不在 RAGFlow 界面里手改画布。

| 数据集 | 键 | RAGFlow 名称后缀 | 管道键 | 内容 |
|---|---|---|---|---|
| 历史标书 | `history` | `icg-history` | `history_bid` | 历史投标原件。提供过去的技术表述、方案结构和实施方法 |
| 资料库 | `materials` | `icg-materials` | `materials` | 产品说明书、已确认技术参数、企业能力说明、已验收案例、企业技术标准 |

管道键用 `materials`。`icg:authority_material:v1:` 再加 8 位公司标识后长度为 34，超过 RAGFlow 流程标题 32 字符，部署会失败。

历史标书里的承诺不是公司当前能力。资料库才是能力、参数和产品事实的来源。模型分类不能把历史片段升入资料库这一组。

招标文件仍按项目使用现有 `tender` 管道，不出现在知识库配置页。资质证书数据集和「资料与方案片段」数据集不再创建、不再同步、不再出现在知识库页。已经存在于 RAGFlow 的这两类数据集不自动删除，写作检索也不再查询它们。企业资料库里已确认记录的规则匹配保持原样，不读这两个新数据集。

虚拟机是另一套 RAGFlow。同一版代码在那边再部署一次，文件在那边重新上传和解析。本机切块和向量不迁移。

## 2. 解析管道

两条管道的节点顺序相同：Parser → Title Chunker → Extractor → Indexer。不在 Title Chunker 前面或后面再接 Token Chunker。

### 2.1 Parser

`enable_vision_enhancement` 为 false，不为 PDF 填写视觉模型。

本机 RAGFlow v1.0.0-rc2 会把 `doc_type` 为 `table` 的块丢掉，表格里的技术步骤因此进不了切块。历史标书和资料库的 PDF、DOC、DOCX 改为 `flatten_media_to_text` 为 true，并设置 `remove_toc` 为 true。表格文字跟所在小节一起切；一节超过 1100 token 时由标题切块器按句拆开。目录页不入库。

| 格式 | 设置 |
|---|---|
| PDF | DeepDOC，`flatten_media_to_text` 为 true，`preprocess` 为 `main_content`，`remove_toc` 为 true，输出 json |
| DOCX | `flatten_media_to_text` 为 true，`remove_toc` 为 true，输出 json。标题、编号和表格文字留在同一节 |
| DOC | 输出 json，`preprocess` 为 `main_content`，`flatten_media_to_text` 为 true，`remove_toc` 为 true |
| XLS、XLSX、CSV | DeepDOC，输出 html，不把表格压成无行列的纯文本 |
| PPT、PPTX | DeepDOC |

历史标书上传只接受 pdf、doc、docx。资料库上传接受 pdf、doc、docx、xls、xlsx、ppt、pptx。上传权限与现在的历史标书相同：公司管理员可上传。数据集未建立时不能上传，先点建立。

### 2.2 Title Chunker

| 参数 | 值 |
|---|---|
| method | hierarchy |
| hierarchy | 3 |
| chunk_token_cap | 1100 |
| 父级标题下的正文 | 单独成块（`include_heading_content` 为 true） |
| 第一块作为全文上下文 | 关闭（`root_chunk_as_heading` 为 false） |

超长章节在句边界继续拆开，不另接按长度切块的节点。

标题规则先放方案这一组，RAGFlow 仍会挑选最匹配的一组。现有 `BID_HEADING_GROUPS` 作为额外组保留。

| 层级 | 表达式 | 示例 |
|---|---|---|
| H1 | `^第[一二三四五六七八九十百]+章\s*.+` | 第一章 项目概述 |
| H2 | `^第[一二三四五六七八九十百]+节\s*.+` | 第一节 项目背景 |
| H2 | `^[一二三四五六七八九十]+[、．.]\s*.+` | 一、建设目标 |
| H3 | `^\d+(?:\.\d+){1,2}[、．.\s]\s*.+` | 4.1 数据备份 |
| H4 | `^[（(]\d+[）)]\s*.+` | （1）备份策略 |
| H5 | `^[①②③④⑤⑥⑦⑧⑨⑩].+` | ① 全量备份 |

切块边界按第三级。H4、H5 仍写入规则，使更深的编号能被识别。每块保留从章节到本级的标题路径。

### 2.3 关键词

Extractor 的关键词 `top_n` 为 10。提示词仍要求 8～12 个；原文不足 8 个时按实际数量输出，当前文本没有技术词时不输出。每行一个词。不开摘要和标签。问法 `enabled` 为 false 且 `top_n` 为 0，不能只写 0，否则 RAGFlow 保存画布时会按默认条数重新打开问法。温度保持现有的 0.1。

历史标书使用下面的系统提示词：

```text
你是一名企业技术方案知识库的关键词提取专家。

你的任务是从给定的历史投标方案知识片段中提取最具有检索价值的技术关键词。

提取规则：
1. 优先提取具体技术名称、技术架构、技术组件、技术方法和实施措施。
2. 保留具有检索价值的专业术语、产品名称、技术标准及关键参数。
3. 关键词必须直接来源于当前文本，不得根据常识补充原文没有的信息。
4. 避免提取“技术方案”“项目建设”“系统功能”等过于宽泛的词语。
5. 对同义词进行适当合并，避免重复。
6. 优先提取能够帮助后续技术方案生成和企业知识检索的关键词。
7. 输出中文关键词短语，不输出解释性段落。
提取数量：8～12 个。
```

资料库使用同一提示词，并把第 1 条收成：优先提取技术名称、技术参数、标准号和实施措施，不提取投标响应用语。

### 2.4 分类字段

分类必须落在预设取值里。取值写入字段说明和系统提示词。无法判断时用 `other` 或 `unknown`，不新造标签。

两条管道共用：

| 字段 | 取值 |
|---|---|
| section_type | overall_design、technical_architecture、system_function、data_security、network_security、deployment、implementation、training、operation_maintenance、quality_assurance、emergency_plan、project_schedule、project_team、project_case、other |
| technical_domain | 与 section_type 同一套 |
| knowledge_type | technical_solution、technical_method、implementation_experience、service_process、standard_expression、enterprise_capability、project_case_evidence、other |
| reusability | high、medium、low、not_reusable |

历史标书另有：

| 字段 | 取值 |
|---|---|
| document_type | technical_proposal、implementation_plan、service_plan、product_manual、project_case、other |
| content_role | bidder_response、buyer_requirement、enterprise_fact、project_specific_commitment、general_description、irrelevant_content、unknown |
| project_name | 原文项目名称；没有则空 |
| bid_date | 原文日期，格式 YYYY-MM-DD；没有则空 |

上传时人已经填写的递交日期优先于模型抽出的 `bid_date`。采购人、行业、项目类型不再抽取。

资料库没有 `project_name` 和 `bid_date`。它的类型更窄：

| 字段 | 取值 |
|---|---|
| document_type | product_manual、technical_specification、enterprise_capability、project_case、technical_standard、other |
| content_role | enterprise_fact、project_case_evidence、general_description、irrelevant_content、unknown |

历史标书分类提示词：

```text
你是一名企业投标技术知识库分类专家。

请根据输入的历史投标文件知识片段，识别其内容类别，并生成结构化元数据。

分类必须遵循以下规则：

一、document_type：识别文件所属类型。

二、section_type：识别当前知识片段所属的技术方案章节类型。根据内容选择最贴近的分类，不得仅根据标题判断。

三、knowledge_type：判断内容属于技术方案、技术方法、实施经验、服务流程、标准表述、企业能力描述还是项目案例证据。

四、content_role：判断内容的实际来源角色：
- bidder_response：投标方提出的响应方案或技术承诺。
- buyer_requirement：招标方提出的技术要求。
- enterprise_fact：明确描述企业自身技术产品、能力或事实。
- project_specific_commitment：特定历史项目中的个性化承诺。
- general_description：不涉及明确企业事实的通用技术描述。
- irrelevant_content：与技术方案生成无关的内容。
- unknown：无法可靠判断。
五、reusability：判断内容的复用价值：
- high：通用性强、技术逻辑完整，适合其他项目参考。
- medium：具有一定参考价值，需要结合新项目调整。
- low：高度依赖原项目背景。
- not_reusable：与当前企业技术方案生成无关，或不宜复用。
六、technical_domain：与 section_type 使用同一套取值，按内容选择技术领域。
严格要求：
1. 所有分类必须依据当前文本，不得推测原文不存在的企业能力。
2. 历史投标文件中的承诺不能自动等同于企业已经具备的客观能力。
3. 招标要求不能标记为企业技术能力。
4. 无法判断时使用 unknown 或 other，不要强行分类。
5. 只返回符合预设字段和枚举值的结构化结果。
```

资料库分类提示词在上述规则上改为只允许资料库的 `document_type` 与 `content_role`。不使用 `bidder_response`、`buyer_requirement`、`project_specific_commitment`。

分块查看时，这些取值显示中文名称。存储和检索仍用上面的英文键。

### 2.5 Indexer

索引字段为处理后的正文（`fields` 为 `text`）。检索方式为 embedding 与 full_text。文件名向量权重保持 0.1。不用摘要或自动问题代替正文索引。两条数据集共用知识库设置里的嵌入模型、重排模型和抽取用对话模型。相似度阈值和关键词权重仍是公司级一套。

配置页去掉「使用 ICG 摄入流程」开关。这两类数据集只绑定 ICG 管道。部署失败时数据集保持未绑定，页面向管理员显示失败原因，不改绑内置 general 解析器。

一次「部署 / 升级」更新这两条管道并绑定数据集。已有文档不自动重解析。页面保留「全部重新解析」。

## 3. 知识库页面

标签页顺序：历史标书、资料库、数据集配置。资料库页的操作与历史标书相同：建立数据集、上传、刷新、查看分块、全部重新解析、重建。

数据集配置上方是共用的嵌入模型、重排模型、抽取模型、相似度阈值、关键词权重。下方表格只有历史标书和资料库两行。表格下方可以试查，试查范围只能选这两类。

侧栏里的「企业资料库」名称和页面保持不动。

## 4. 检索与写作

命中这两类数据集的结果都是仅供参考，不能挂成正式证据。

| 场景 | 行为 |
|---|---|
| 正文生成、编辑台问答 | 同时检索两类。提示词分成两段，标题固定为「历史技术方案参考：过去项目中的优秀技术表述和实施方法。」和「企业权威资料：产品说明书、技术参数、企业实际能力等事实依据。」 |
| 响应矩阵候选 | 增加一组「资料库（参考）」，不能勾选挂接。原有「资料库规则匹配」仍读企业资料库已确认记录 |
| 技术分册矩阵 | 同一条条款同时检索两类。最相近的一条历史标书作为和本次条款比较偏离的做法，出处注明这是过去的做法。资料库命中另列在同一行。没有历史标书时，不编造带历史出处的响应；资料库片段只留在出处里 |
| 六段正文 | 能看见该行的历史做法和资料库出处，并按下面的写作规则使用 |

历史标书数据集中的片段只进入「历史技术方案参考」，即使 `content_role` 被标成 `enterprise_fact` 也不进入「企业权威资料」。资料库片段只进入「企业权威资料」。

编辑台现在的「知识库候选」按这两个标题分成两组。

写作默认按历史承诺写。以前承诺过的能力，按当时的历史情况写入正文。权威资料没有提到，或与历史承诺不一致时，仍然按历史承诺写，不改成「待补」，也不删掉该能力。

章节正文上方出现一条警告提示的条件是：本次生成放进提示词的历史片段里，至少有一块 `content_role` 为 `bidder_response`、`project_specific_commitment` 或 `enterprise_fact`，并且没有资料库片段与它的 `technical_domain` 相同。`content_role` 为 `general_description`、`unknown` 或其他值时，不因为单纯借鉴写法或步骤而出现提示。

提示文案：「本节有内容来自历史投标承诺，尚未在企业权威资料中核到。历史承诺不代表公司当前一定具备该能力。」并列出触发它的历史文件名。提示在正文外面，可以关掉。关掉后，本章这一次生成的所有查看者都不再看到。重新生成后再次出现。关掉提示不删除正文，提示文字不进入导出的标书。

## 5. 本轮不做

- 待审核、已审核、推荐引用、禁止复用。这些状态以后由管理员维护，不由模型填写。
- 自动重解析，以及把本机 RAGFlow 的切块迁到虚拟机。
- ~~用五份真实标书计算 Recall@5 和 MRR@10。~~ **已做（2026-11-06）**：见 [rag-eval-history-bid-v1.md](../../testing/rag-eval-history-bid-v1.md) 与任务 AI-HISTORY-BID-RAG-EVAL；假服务不算验收。

## 6. 代码完成时要证明的事

用现有假 RAGFlow 和前端测试证明：

1. 两条管道的 DSL 含有本文的解析器、标题切块参数、关键词提示词、分类取值和索引字段，且没有问法、摘要、标签和视觉增强。
2. 部署只确保 `history` 与 `materials`。不再确保 `library` 与 `certificate`，也不删除远端已有数据集。
3. 知识库页只有约定的三个标签。资料库可上传约定格式。
4. 正文提示词把两类片段分到约定的两个标题下。历史片段不会因为分类结果进入权威资料。
5. 满足第 4 节条件时，章节上方出现可关闭的提示；关闭后不进入导出正文；重新生成后提示回来。
6. 技术分册矩阵在有历史命中时仍用最相近的历史片段判断偏离，并把资料库命中记在同一行的另一组出处。

真实 RAGFlow 上的解析质量和检索质量，等用户明确要求部署后再做。代码测试通过不等于生产解析已经验收。

## 补充（2026-11-06 · AI-HISTORY-BID-PARSE-OPT）

本补充覆盖方案正文冲突处。

1. **标题规则**：数字层级允许 `6.3Oracle…`、`1.定期…`（数字后直接接字母/汉字，不强制空白或顿号）。表达式见 `SCHEME_HEADING_GROUP`。
2. **问法关闭**：部署后必须再读远端画布；若 `questions.enabled` 仍为 true 或 `top_n>0`，强制重写 DSL。
3. **真机最小验收**：只认 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 下的四类单测（切块/抽取分类/检索/整管）。金标两份脱敏 docx 见 `tests/backend/fixtures/history-bid-golden/`。假 RAGFlow 绿测不计入解析质量验收。
4. **试查对账**：检索试查前刷新本地索引状态，避免远端已 DONE、本地仍 parsing 导致 zero hits。
