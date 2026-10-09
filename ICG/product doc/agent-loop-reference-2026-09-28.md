# Agent 闭环（方案设计→生成→Review→修正）参考调研：WorkBuddy 路线与可借鉴做法

- 调研日期：2026-09-28（下文所有来源的查阅日期都是 2026-09-28，不再逐条重复）
- 对应 PRD：/workspace/deliverables/prd-mvp-v1.md（MVP v1）
- 相关调研：同目录下 bid-system-landscape-2026-09-28.md（市场格局）、kb-schema-references-2026-09-28.md（知识库结构）
- 写作约定：“厂商称”“社区文章称”表示没有经过第三方验证；“未查到”就是没查到，没有推测补全。

---

## 0. 一页结论

**推荐：保留 PRD 现在“主流程写死”的做法，不引入自主 Agent 循环。在“分节生成”和“合规检查”之间补一个固定编排的“章节评审→定位修正”小闭环。评审以机器可验证的外部检查为主，LLM 评审为辅，结论只作提示；修正只改被指出的段落，最多自动 1 轮，之后交给人。**

依据有三条：

1. **WorkBuddy 是腾讯的通用职场 Agent 桌面工作台**，不是标书产品。它的标书能力来自第三方 Skill，本质上是 SKILL.md 形式的提示词、脚本和资料包。做得好的标书 Skill，比如百炼、Hugin-Z/tender-writer、tiettuo/claude-bid-gen、HUAN2022A/bid-skills，**实际跑的也是固定阶段的流水线，加人工确认门，再加脚本硬校验**，并不是让 Agent 自由发挥。它们值得借鉴的是阶段划分和校验规则，这些我们用固定流程也能实现，不需要 Agent 框架。
2. **学术证据比较一致：没有外部反馈时，“模型自己评、自己改”不可靠**（Huang et al. ICLR 2024；Kamoi et al. TACL 综述）。有工具、规则、检索这类外部反馈时才有效（CRITIC）。迭代收益主要在前 1–2 轮（Self-Refine）。LLM 当评审存在自我偏好和顺序偏差（Panickssery 2024；Zheng 2023）。所以评审的主力应该是 PRD 已有的规则引擎，外加新增的覆盖度对账、事实一致性检查，LLM 只做补充。
3. **Qwen3-30B-A3B-Instruct-2507 适合做“单步、结构化”的任务，不适合多轮自主调用工具。** 官方模型卡上 IFEval 84.7、WritingBench 85.5、RULER 16k 96.9 都不错，但多轮工具 Agent 基准 TAU2 Airline 只有 38.0、Telecom 只有 12.3。多轮对话场景下，各模型平均掉点 39%（Laban 2025）。输入越长越不稳定（Chroma Context Rot，测试含 Qwen3 系列）。

**建议借鉴的 9 条**：骨架对账、大纲确认门、项目事实表＋章节摘要、章节评审（规则为主）、定位式修正（≤1 轮自动）、召回确认、教训库转成检查清单、评审模型异构化、把“Skill”落成可版本化的任务卡，详见第 4 节。**不要照搬**：自主 Agent 循环、自动长期记忆、把文件传到第三方云端的 Skill、一键全自动加“AI 去痕”、同模型打分决定放行、购买 WorkBuddy 私有化版（300 席起售，价格未公开）。

---

## 1. WorkBuddy 是什么

| 维度 | 事实 | 来源 |
|---|---|---|
| 厂商、定位 | 腾讯出品，官方称“全场景职场 AI 智能体桌面工作台”。能自主规划、拆解任务，读写用户授权的本地文件；有专家中心、SkillHub、项目空间、自动任务。官方称自动任务在云端运行，关掉客户端也能继续 | https://cloud.tencent.com.cn/product/workbuddy ；https://www.workbuddy.cn/docs/workbuddy/Overview |
| 规模宣传 | 官网写“100+ 领域专家、7 万+ Skills”，属于厂商口径，未经核实 | 同上 |
| 形态 | 桌面客户端，另有 IDE 形态和 CLI 形态的文档 | https://www.workbuddy.cn/docs/ide/Features/Skills ；https://www.workbuddy.cn/docs/cli/skills |
| Skill 机制 | 一个 Skill 是一个目录：SKILL.md（YAML frontmatter 包括 name、description、allowed-tools、disable-model-invocation、user-invocable、context: fork、model、hooks 等）加上 scripts/references/assets。按需渐进加载：平时只看 description，命中后才读全文和附件。可以导入本地技能包、搜索、创建、启停。官方提醒非官方 Skill 可能有提示词注入、后门等风险 | https://www.workbuddy.cn/docs/ide/Features/Skills ；https://open.workbuddy.cn/en/docs/skill ；https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market |
| 企业 Skill | 企业后台上传 zip（SKILL.md＋manifest.yaml），可以按成员、部门、角色下发 | https://www.workbuddy.cn/docs/enterprise/adminguide/Skill%E7%AE%A1%E7%90%86 |
| 工具调用 | 内置本地文件读写、命令执行等能力；社区文章称支持 MCP，并“兼容 OpenClaw 生态”（**非正式文档，存疑**） | https://cloud.tencent.com/developer/techpedia/2610/20530 |
| 记忆 | 官方文档：每晚从当天会话中提取事实、偏好、人物关系、跟进事项，注入系统提示词；可以检索会话历史；可以查看、编辑、删除、关闭；可以从其他 AI 导入。官方自己提示记忆“可能存在概括偏差或时效性问题”。社区文章还描述了三层结构（云端画像、~/.workbuddy/MEMORY.md、工作区 .workbuddy/memory/ 加每日日志），**非官方** | https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Memory ；https://www.woshipm.com/ai/6441979.html ；https://www.cnblogs.com/xiaobaiysf/p/21866387 |
| 多轮 Loop | 产品层面是“规划→调用工具→观察→继续”的 Agent 循环。上下文默认 200K，非 Max 模式下自动压缩上下文 | https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Model |
| 模型 | 快速、均衡、极致三档；内置 Hy4 preview、Hy3、GLM-5.3/5.2、MiniMax-M3、Kimi-K3、DeepSeek-V4 等；支持自定义模型，包括通过 Ollama 接本地 OpenAI 兼容接口，API Key 只存在本地 models.json | 同上 |
| 个人版定价 | 体验版免费（500 积分/月）；标准版 99 元/月、高级版 199 元/月、旗舰版 999 元/月（连续包月 7 折；连续包年 672/1344/6720 元/年）；加量包 50 元/1000 积分；2026-07-01 起启用新方案 | https://www.workbuddy.cn/docs/workbuddy/Pricing |
| 企业版定价与部署 | 旗舰版（SaaS）198 元/人/月或 2376 元/人/年，1 席起；专享版（专有 VPC）316 元/人/月或 3792 元/人/年，100 席起；**企业私有化版：300 席起，自备算力和模型服务，企业内网部署、数据不出域，价格需咨询售前，未公开**。企业版有企业 Skill、企业模型配置、安全审计、OpenAPI；使用自定义模型不消耗 Credits | https://cloud.tencent.com.cn/product/workbuddy-enterprise ；https://cloud.tencent.cn/document/product/1831/134333 （该页直接抓取被反爬拦截，内容来自搜索摘要）；https://cloud.tencent.com/document/product/1831/134332 |
| 用户数 | **未查到官方数字** | — |

**对我们的含义**
- 能私有化，但门槛是 300 席起，且要自备模型，价格未公开。对单一投标团队明显不合适。
- WorkBuddy 的“开箱即用”靠的是强云端模型（200K 上下文）加通用 Agent 循环。换成本地 30B/16k 后，它的优势大部分不存在了，本地模型的工具调用稳定性见第 3.3 节。
- 它的记忆是**用户级、跨会话自动提取**的，没有“公司”和“项目”这两个隔离维度，和 PRD 第 8 章“以公司为最高隔离单位”冲突（详见第 4.2 节）。

---

## 2. 公开案例、教程与 Skill 的流程拆解

### 2.1 总览

| 案例 | 类型 | 流程 | 评审/修正怎么做 | 值得学 | 不宜照搬 |
|---|---|---|---|---|---|
| 百炼智能《如何用 WorkBuddy 生成 1000 页超长标书》（2026-07-13，厂商文章）https://www.bailian-ai.com/news/2451.html ；SkillHub：https://skillhub.cloud.tencent.com/skills/org-32m5yxyy/biaoshu-bailian-official （v3.1.2） | WorkBuddy Skill，底层调用百炼云端 API | ①先画“模块地图”：按评分标准、采购需求、交付范围拆成 20–40 页的模块，列出每个模块的评分点、依据、素材、依赖；②三层知识库（企业事实、能力模块、项目经验，标注有效期和负责人）；③每个模块带“评分点·原文·素材·规则”四样东西生成，先出目录和响应关系，再展开正文；④拿不准的内容留待填项 | 用**术语表＋项目事实表**保持一致；每个模块写完生成简短摘要，供后续模块参考；设两道门：模块审核，再加整套合规审查和查重 | 模块地图（等同于我们的响应矩阵→大纲）；事实表；章节摘要接力；两道门 | Skill 要 API Key，文件会上传到百炼（GitHub 镜像 chichihaixiaojian666/biaoshu-bailian 写明“招标/投标文件会上传到百炼®标书”）；“1000 页”是厂商自述 |
| Hugin-Z/tender-writer（GitHub，SKILL.md 已完整阅读） | 通用 Agent Skill | 五个阶段：解析→评分矩阵 CSV→提纲→逐章撰写→合规终审。每个阶段都产出中间文件，**用户明确确认后才进下一阶段**；tender_brief 作为唯一事实来源 | 提纲末尾做“覆盖度自检”；每章写明覆盖了哪几行评分项；终审报告有未覆盖项就必须回到阶段 4；素材 review_status=approved 才能引用；reference 类素材禁止进正文；合作伙伴素材必须标来源；过期或临期资质标红 | 阶段确认门；唯一事实源；覆盖度自检＋回退 | 依赖 Agent 自觉遵守，没有系统强制 |
| tiettuo/claude-bid-gen（GitHub） | Claude 类 Agent 工程 | 机器先抽出评分办法、必含大纲、废标条款三份 JSON 骨架，LLM 只负责翻译和填细节 | “八条铁律”闭环校验：分值总和、字数±15%、必含大纲覆盖、来源页码过度集中、正文与骨架对账等，**退出码 2 就硬阻断**；另有机器审校、相似度检查（防围标）、memory/feedback 教训库。这些规则来自 3 个真实项目的失败（例如漏抄必含大纲、14 条废标条款全标成同一页码） | **骨架先由机器抽取，事后对账**；把失败教训沉淀成规则 | 个人项目，效果没有第三方验证 |
| HUAN2022A/bid-skills（GitHub，2★） | 7 个 Skill | 评分点对照表是“中枢契约”；大纲是唯一的人工确认点，召回的历史材料再确认一次；**召回历史真实标书、以改写为主，从零生成只作兜底** | bid-check 用脚本判断覆盖率、关键词、[待补]、章节是否齐全，并扫描“串味”（旧项目残留）；模型只判断“响应是否实质”；--fix 只改元数据和编号，不碰语义；废标、待补、覆盖缺口“**永远只报不修**” | 脚本判定为主、模型判断为辅；“只报不修”的边界；召回改写优先 | 星数很低，效果没有验证 |
| maike-china/rejection-check（GitHub） | 废标风险 Skill | 三轮检查：先确定范围→逐项核查→合并定稿 | 另查错别字和前后不一致（人员、工期、金额） | 跨章一致性检查项 | — |
| Get00/BiaoShu-SKILL（GitHub，164★） | 全自动 Skill | 14 步全自动流水线：行业检测、评分提取、大纲、生成、字数检查、“AI 去痕”、占位符等，会自动生成新的行业指南 | **没有评审环节** | 字数、占位符检查 | 全自动加“AI 去痕”：合规风险高，也违背 PRD 的证据约束 |
| Dify / Coze 教程（CSDN、博客园等） | 低代码工作流 | 搜索摘要显示的共同模式：上传招标文件→文档解析节点→抽取关键条款→按章节调用 LLM（接知识库）→审查节点对照评分标准→导出 Word/PDF | 多为单次“审查节点”，不做迭代 | 流程和我们的设计一致 | **本次没有深入核实**：主要文章 https://blog.csdn.net/sheepForTest/article/details/159501386 被 WAF 拦截；https://www.cnblogs.com/jzssuanfa/p/19702624 、https://blog.csdn.net/m0_53539063/article/details/147637685 只看了搜索摘要 |
| 腾讯云开发者文章《用 WorkBuddy 创建标书 SKILL》 https://cloud.tencent.com/developer/article/2656994 | 教程 | **被反爬拦截，没读到正文** | — | — | — |
| Manus 做标书的公开案例 | — | **未查到可靠的公开案例** | — | — | — |

GitHub 用“标书 skill”检索共 36 个仓库（2026-09-28，通过 GitHub 搜索）。其他如 yanhaoluo0/technical-proposal-expert-writing-skill（78★）、aidevsource/Bid-Analysis-Skill 没有展开分析。

### 2.2 共性规律

1. **做得好的 Skill 其实都是“固定流水线＋确认门＋脚本校验”**。Agent 在里面只是执行器，流程由 SKILL.md 规定。这恰好说明 PRD 选择“业务层写死主流程”方向是对的，而且写死之后系统能强制执行这些规则，比“提示词里要求 Agent 遵守”更可靠。
2. **评审的主力是可机器判定的检查**：覆盖度、分值、字数、占位符、串味、骨架对账、有效期。LLM 只负责“响应是否实质”这类语义判断。
3. **修正有边界**：废标、待补、覆盖缺口这类问题只报告不自动修；自动修复限于格式和编号，或者针对具体问题做局部改写。
4. **长标书靠“事实表＋摘要接力”保持一致，而不是靠长上下文**。这个做法正适合 16k。
5. **评审没有公开的量化效果数据**：所有案例都没有给出返工率、得分提升之类的对照数据，只有自述。

---

## 3. “生成-评审-修正”循环：业界做法、局限与小模型证据

### 3.1 业界做法

| 模式 | 要点 | 适用条件 | 来源 |
|---|---|---|---|
| Workflow 优先于 Agent | 先用最简单的方案，很多场景单次调用加检索就够；Agent 成本高、错误会累积；定义明确的任务适合用 workflow。“先写大纲、检查大纲是否满足标准、再写正文”被列为 prompt chaining 的例子 | 任务步骤可以预先定义 | Anthropic《Building effective agents》https://www.anthropic.com/engineering/building-effective-agents |
| Evaluator-optimizer | 一个模型生成，另一个评价并反馈，循环进行 | “评价标准清晰，且迭代能带来可衡量的提升” | 同上 |
| Self-Refine | 同一模型生成→反馈→改写 | 7 个任务平均提升约 20%，最多迭代 4 轮，**收益主要在前 1–2 轮** | https://arxiv.org/abs/2303.17651 |
| CRITIC | 借助工具（搜索、代码执行等）验证后再修改 | 摘要强调“外部反馈对持续自我改进至关重要” | https://arxiv.org/abs/2305.11738 |
| 先规划再写（长文） | STORM：先调研、生成大纲，再写（专家评价在组织性上提升 25%，覆盖面提升 10%）；LongWriter/AgentWrite：把超长输出拆成子任务 | 长文生成 | https://arxiv.org/abs/2402.14207 ；https://arxiv.org/abs/2408.07055 |
| 上下文工程 | 相关信息“是否在上下文里”不够，“怎么呈现”更重要；长输入会让表现下降且不均匀 | 所有长文任务 | https://www.trychroma.com/research/context-rot |

### 3.2 局限（这是本次最重要的证据）

1. **没有外部反馈时，自我纠错会让表现变差**：Huang et al.（ICLR 2024）发现模型把对的改成错的，比把错的改对还多；多智能体辩论不如同等调用次数的 self-consistency；不少“提升”其实来自反馈 prompt 里的信息比初始 prompt 更全。https://arxiv.org/abs/2310.01798
2. **综述结论**：通用任务中，没有可靠证据表明只靠 prompt 的自我纠错有效；有可靠外部反馈（工具、检索、规则）时有效；可分解、易验证的任务例外；瓶颈在“生成反馈”这一步。Kamoi et al.（TACL）https://arxiv.org/abs/2406.01297
3. **反馈质量是瓶颈**：Self-Refine 的失败案例里，33% 是反馈定位错了，61% 是反馈给的修改建议不对；Math 任务上 94% 的反馈都是“看起来没问题”。代码自我修复算上成本后收益有限，改用更强模型提供反馈后提升明显（Olausson et al.）。https://arxiv.org/abs/2303.17651 ；https://arxiv.org/abs/2306.09896
4. **LLM 当评审有偏差**：位置偏差、冗长偏差、自我增强偏差（Zheng et al. MT-Bench）；自我偏好和自我识别能力线性相关，调换选项顺序后改判的比例 GPT-4 为 25%、GPT-3.5 为 58%、Llama2 为 89%（Panickssery et al.）；自我偏好的实质是偏爱困惑度低、“看着眼熟”的文本（Wataoka et al.）。https://arxiv.org/abs/2306.05685 ；https://arxiv.org/abs/2404.13076 ；https://arxiv.org/abs/2410.21819
5. **多轮对话会让模型“迷路”**：在 6 类生成任务上，多轮对话比单轮平均下降 39%，主要原因是不稳定性大增：模型早早做出假设并过度依赖。https://arxiv.org/abs/2505.06120
6. **长输入会“腐烂”**：18 个模型（包括 Qwen3-235B/32B/8B）都随输入变长而下降；干扰项（和正确信息相似但不对的内容）的负面影响随长度放大；LongMemEval 上，“只给相关内容（约 300 token）”明显优于“给全部内容（约 113k token）”。https://www.trychroma.com/research/context-rot

**对投标场景的含义**：标书评审里，真正“标准清晰、可以验证”的部分，比如覆盖度、★条款、分值、SLA 数值、人名证书、有效期、串味、格式，应该交给规则。语义层面的“写得好不好、响应是否实质”只适合当提示，不能决定放行。迭代轮数要少。

### 3.3 小参数本地模型做工具调用、评审是否稳定

| 证据 | 数值 | 来源 |
|---|---|---|
| Qwen3-30B-A3B-Instruct-2507 函数调用 | BFCL-v3 65.1 | https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507 |
| 多轮工具 Agent | TAU1-Retail 59.1、TAU1-Airline 40.0；TAU2-Retail 57.0、Airline 38.0、**Telecom 12.3** | 同上 |
| 指令遵循与写作 | IFEval 84.7；WritingBench 85.5；Creative Writing v3 86.0 | 同上 |
| 长上下文 | RULER 16k 96.9、32k 97.2、128k 89.1 | 同上 |
| 官方建议 | temperature=0.7、TopP=0.8、TopK=20，可以用 presence_penalty 抑制重复；工具调用推荐用 Qwen-Agent 处理模板和解析；只有非思考模式 | 同上 |
| 小模型自我修正 | Self-Refine 中 Vicuna-13B 连反馈格式都生成不稳，refine 也做不好 | https://arxiv.org/abs/2303.17651 |

**判断**：这个模型在“一次调用完成一件事，并按格式输出”（写一节、按清单评一节、抽取字段）上可用。让它自主决定“下一步调哪个工具、调几轮”，成功率只有四成左右甚至更低（TAU 系列），而且每多一轮都会叠加多轮对话和长上下文的不稳定。结论是：**编排由系统负责，模型只完成单步任务**。16k 的 RULER 分数很高，说明“少量相关材料”的场景没问题，但这不代表评审时可以把整本标书塞进去。

注意：TAU/BFCL 是通用基准，不是标书任务，不能直接换算成标书场景的成功率。建议在试运行时用 3–5 份历史标书做一次本地评审的准确率抽测（见第 5 节）。

---

## 4. 结论：借鉴什么、不照搬什么

### 4.0 推荐的闭环形态（放在 PRD 4.2 主流程里）

```
解析确认 → 响应矩阵 → [新] 骨架对账 → 大纲 → [新] 大纲确认门 → 召回确认
→ 分节生成（带项目事实表＋前序章节摘要）
→ [新] 章节评审：L1 机器检查（必跑，可复现）→ L2 LLM 按评分项逐条评（只出提示）
→ [新] 定位修正：只改被点名的段落，自动最多 1 轮，重跑 L1，没有改善就交人工
→ 人工编辑 → 合规检查（R01–R25，阻断就退回）→ 导出
```

这仍然是写死的 workflow，每一步的输入、输出、模型、提示词版本都会记录下来，可以复现。

### 4.1 推荐借鉴清单（按优先级排序）

| # | 借鉴点（出处） | 放进 PRD 哪个模块 | 怎么落地 | 30B/16k 适配 | 风险 |
|---|---|---|---|---|---|
| 1 | **骨架先由机器抽取，事后对账**（claude-bid-gen、tender-writer 覆盖度自检、百炼模块地图） | 5.2 解析、5.3 响应矩阵、5.7.1 规则 1 大纲生成；5.8 建议新增一条规则（暂编 R26“评分项覆盖度”） | 评分项、★条款、废标条款、必含目录（招标文件规定的章节）抽成结构化骨架（即矩阵行）；大纲节点必须覆盖全部评分项行和规定章节，缺了就标红；章节生成时要求模型输出“本章覆盖了哪些 matrix_item_id”，系统和 bid_outline_node.matrix_item_ids 对账；外加分值总和、目标字数±N% 校验。评分项未覆盖→警告，规定章节缺失→阻断（R24 已有部分覆盖）| 全部是规则计算，不占模型上下文；抽取已经走本地模型，并由人逐项确认 | 抽取错了，对账也会跟着错。靠 4.2 的“负责人逐项确认”兜底 |
| 2 | **阶段确认门**（tender-writer 每阶段确认，bid-skills 大纲是唯一的人工确认点） | 4.2 主流程、4.3 项目状态、5.7.1 | 在现有“抽取确认”之后增加“大纲已确认”状态：大纲没确认就不能批量生成章节；确认人和时间写进审计日志 | 减少“整本生成后再推翻”的浪费，本地算力更珍贵 | 多一步操作。可以允许负责人一键确认 |
| 3 | **项目事实表＋章节摘要接力**（百炼术语表＋项目事实表＋模块摘要；tender_brief 作为唯一事实源） | 5.7 分节生成（新增数据对象）；衔接 5.3.2 SLA 矩阵、全局变量、5.6 写作档案的术语表；扩展 5.8 R10 | 新建 project_fact（项目名称、招标人、服务期、服务地点、项目经理、设备数量、SLA 值等，全部以变量引用）；每章生成后由模型产出不超过 300 字的摘要，加上“本章使用的事实”清单，存入 chapter_version.summary；后续章节只拿前序章节的摘要，不拿全文。R10“SLA 全文一致”扩展为“项目事实全文一致”：正文中出现的日期、数量、人名和事实表比对，不一致就报 | 这是 16k 下保持跨章一致的关键：摘要和事实表加起来控制在约 1–2k token；符合 Chroma“只给相关内容”的结论 | 摘要本身可能有偏差。摘要只作衔接参考，不作证据；事实以事实表和资料库为准 |
| 4 | **章节评审以外部可验证检查为主（L1），LLM 按评分项评审为辅（L2）**（bid-skills“脚本判定、模型只判实质”；Kamoi、CRITIC 的证据） | 5.7 新增“章节评审”小节；结果复用 5.8.4 compliance_issue（新增 source=章节评审，LLM 结论 level 固定为“提示”）；6.4 任务表新增“章节评审”任务 | L1（必跑，结果可复现）：本章覆盖度、【待补】数、无证据事实（5.7 规则 3 已有）、事实表一致性、串味和旧项目名（复用 R25 的逻辑，改成按章实时跑）、禁用词、字数。L2（可选）：每次输入“一节正文＋本章矩阵行原文＋评分细则＋检查清单”，输出 JSON 问题列表 {matrix_item_id, paragraph_key, 问题类型, 原文引用, 修改建议}；**系统校验“原文引用”确实出现在正文里，对不上的问题直接丢弃**，防止评审模型编造问题 | 每次只评一节，正文超过约 8k token 就按三级标题分片；强制结构化 JSON 输出（推理框架是否支持受约束解码需研发核实）；评审用较低 temperature（这是经验做法，官方推荐值 0.7 针对通用对话，需要试运行验证）| LLM 评审有自我偏好、顺序偏差，可能漏报或误报。所以只出提示，不阻断，符合 5.8.2 规则 1 |
| 5 | **定位式修正，自动最多 1 轮**（Self-Refine 收益集中在前 1–2 轮；Huang“改对为错”；bid-skills“只报不修”） | 5.7.1 规则 6 局部改写；5.7.2 generation_task.task_type 新增“评审修正” | 编写人勾选问题后点“按问题修正”（也可以由负责人配置为自动执行 1 轮）：只把被点名的段落、问题描述、相关证据发给模型；锁定段落不动；改完重跑 L1，满足“问题数减少、没有新增 L1 问题、证据标记完整”才采纳，否则丢弃修改稿并转人工。**【待补】、★条款、废标、覆盖缺口永远只报不修** | 单段改写的输入很小，16k 足够；不做多轮对话，每轮都是新的单步调用 | 语义类改写可能把对的改错。所以保留版本对比，需要人确认采纳 |
| 6 | **召回历史真实稿、改写优先，并设召回确认**（bid-skills） | 5.5 方案片段库、5.7.1 右侧“可用证据”面板 | 生成前展示本章召回的已发布片段（本公司、已确认），编写人勾选后才喂给模型；有高匹配片段时，提示词改为“基于片段改写”而不是从零写 | 片段比自由生成更稳，也能少占输出长度 | 容易串味、异常一致。R25、R18 已覆盖；写作档案需要有差异化要求 |
| 7 | **失败教训沉淀为检查清单，不做自动长期记忆**（claude-bid-gen 教训库；WorkBuddy 记忆的反面教训） | 5.6 写作档案（新增“审查清单”组成部分）；5.10 管理后台 | 复盘时，由负责人把丢分项、废标原因、专家意见写成检查项（例如“运维方案必须写备件响应时间”），公司管理员审核后发布，带版本；L2 评审按章节类型取用对应清单 | 清单按章节类型筛选，每次只取 5–15 条，避免撑爆上下文 | 清单越积越多、互相矛盾。需要有负责人和停用机制 |
| 8 | **评审尽量换一个模型**（Panickssery 自我偏好；Olausson“更强模型给反馈收益更大”） | 6.4 任务与模型对应表；6.5 路由 | “章节评审”任务单独配置模型：非敏感项目可以用云端异构模型做 L2；敏感项目只能用本地模型，这时用不同的评审提示词，随机打乱清单顺序，并以 L1 规则为主。遵守 6.5“永远不会从本地降到云端” | 本地同模型评审的价值有限，要预期它主要起“按清单逐项提醒”的作用 | 云端评审会把正文发出去，受 6.4 敏感规则约束，需要审计（6.7）|
| 9 | **把“Skill”落成可版本化的任务卡**（WorkBuddy SKILL.md 的渐进加载思想） | 5.6 写作档案的 prompt_template；6.4；5.7.2 generation_task 记录模板版本 | 每类任务（大纲、章节写作、摘要、评审、修正）配一张“任务卡”：用途、输入字段、输出 JSON schema、检查清单、1–2 个示例，按公司和章节类型取用，带版本号，写入 generation_task。**只借鉴“按需加载、打包管理”这个思想，不引入会自主调用工具的 Agent 运行时** | 按需加载本身就是在节省上下文，和 16k 预算（6.2.2）相符 | 模板多了之后难维护。先做少量公司级模板 |

### 4.2 不照搬清单

| 不照搬 | 理由 |
|---|---|
| 自主 Agent 多轮 Loop（让模型决定下一步做什么、调哪个工具） | ①黑盒，不可复现，违背 5.8.2 规则 1“结果可复现”；②本地模型多轮工具成功率只有约 12–59%（TAU 系列），多轮对话平均下降 39%；③错误会累积，成本和耗时难预估（Anthropic）；④审计和权限（第 7、8 章）难以按步骤落地 |
| WorkBuddy 式的自动长期记忆（每晚自动提炼、注入提示词） | ①按用户累积，没有公司、项目隔离维度，容易跨项目串味、跨公司泄漏，和第 8 章冲突；②官方自己提示有“概括偏差、时效性问题”；③自动写入的记忆没有人审核，会变成无证据的“事实”，绕过 5.7 规则 2、3 的证据约束。替代做法：项目事实表（项目级），加上人工审核的检查清单（公司级） |
| 使用把文件传到第三方云端的标书 Skill（例如百炼 Skill） | 招标、投标文件出域，和私有化定位以及 6.4“抽取、匹配只走本地”冲突 |
| 一键全自动生成加“AI 去痕”（Get00/BiaoShu-SKILL） | 没有评审环节；“去痕”对证据约束和合规都没有帮助，还会掩盖 AI 生成标记（5.7.1 要求显示），并带来串通投标、异常一致的解释风险（8.2） |
| 同一个模型打分、分数够了自动放行，或者循环到“满意”为止 | 自我偏好、顺序偏差、会改对为错；PRD 规定模型结论只能是“提示” |
| 采购 WorkBuddy 私有化版作为底座 | 300 席起售，价格未公开，要自备模型；通用工作台不具备 PRD 要求的响应矩阵、证据挂载、公司隔离、合规阻断，这些都要重新做 |
| 依赖 200K 长上下文“一次看全书” | 本地模型实测 16k 效果最好；Context Rot 表明长输入不稳定；应该用摘要接力和分片评审 |

### 4.3 对 PRD 的最小改动建议（便于排期）

1. 4.2 主流程图：在“分节生成”和“人工编辑”之间插入“章节评审→定位修正（可选自动 1 轮）”；在“大纲”之后加“大纲确认”。
2. 5.7：新增 5.7.x“章节评审与修正”（L1、L2 定义，1 轮上限，只报不修的清单，引用校验）；数据对象新增 project_fact，chapter_version 增加 summary 和 facts_used 字段，generation_task.task_type 增加“摘要、评审、评审修正”，并记录 prompt_template_version。
3. 5.8：新增 R26“评分项覆盖度”（警告）；R10 扩展为“项目事实一致”；compliance_issue 增加 source 字段（规则/章节评审/LLM 辅助）。
4. 5.6：写作档案增加“审查清单”，带版本，公司管理员审核后发布。
5. 6.4：任务表新增“章节摘要”（只走本地）、“章节评审”（敏感项目走本地，非敏感项目可以走云端异构模型）。
6. 1.3 成功指标（可选）：增加“评审提示采纳率”“自动修正采纳率”，用来在试运行中判断 L2 和自动修正值不值得保留。

---

## 5. 查不到、存疑或需要验证的点

1. **WorkBuddy 私有化版价格**：官方写“咨询售前”，未公开。
2. **WorkBuddy 用户数**：没有查到官方数字。“7 万+ Skills”是厂商口径。
3. **三层记忆结构、“兼容 OpenClaw”、“三次相似指令自动提示生成 Skill”**：出自社区文章或腾讯云百科类页面，不是正式产品文档，存疑。
4. **没读到正文的来源**：腾讯云开发者文章 2656994（反爬）；腾讯云企业版价格文档 134333（反爬，只看了搜索摘要）；Dify 标书教程 CSDN 159501386（WAF）。
5. **Coze、Dify、Manus 做标书的案例**：只看了搜索摘要，没有逐篇核实；Manus 没找到可靠的公开案例。
6. **GitHub Skill 的效果**：大多是个人项目，星数低（2–164★），没有第三方效果验证；百炼“1000 页”是厂商自述。
7. **所有案例都没有公开“评审环节带来多少提升”的量化数据。**
8. **本地模型评审的准确率没有直接证据**：TAU、BFCL、IFEval 是通用基准。建议试运行时拿 3–5 份已中标或已评分的历史标书，人工标注问题后，测 L2 评审的召回率和误报率，再决定 L2 默认开还是关，以及是否允许自动修正。
9. 评审的 temperature、受约束 JSON 解码是否可用（取决于推理框架），需要研发核实。

---

## 6. 来源列表（查阅日期均为 2026-09-28）

**WorkBuddy 官方与相关**
- https://cloud.tencent.com.cn/product/workbuddy
- https://www.workbuddy.cn/docs/workbuddy/Overview
- https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market
- https://www.workbuddy.cn/docs/ide/Features/Skills
- https://www.workbuddy.cn/docs/cli/skills
- https://open.workbuddy.cn/en/docs/skill
- https://www.workbuddy.cn/docs/enterprise/adminguide/Skill%E7%AE%A1%E7%90%86
- https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Memory
- https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Model
- https://www.workbuddy.cn/docs/workbuddy/Pricing
- https://cloud.tencent.com.cn/product/workbuddy-enterprise
- https://cloud.tencent.cn/document/product/1831/134333 （反爬，内容来自搜索摘要）
- https://cloud.tencent.com/document/product/1831/134332
- https://cloud.tencent.com/developer/techpedia/2610/20530 （社区/百科，非正式文档）
- https://www.woshipm.com/ai/6441979.html （社区）
- https://www.cnblogs.com/xiaobaiysf/p/21866387 （社区）

**案例与 Skill**
- https://www.bailian-ai.com/news/2451.html
- https://skillhub.cloud.tencent.com/skills/org-32m5yxyy/biaoshu-bailian-official
- https://github.com/chichihaixiaojian666/biaoshu-bailian
- https://github.com/Hugin-Z/tender-writer
- https://github.com/tiettuo/claude-bid-gen
- https://github.com/HUAN2022A/bid-skills
- https://github.com/maike-china/rejection-check
- https://github.com/Get00/BiaoShu-SKILL
- https://github.com/yanhaoluo0/technical-proposal-expert-writing-skill
- https://github.com/aidevsource/Bid-Analysis-Skill
- https://cloud.tencent.com/developer/article/2656994 （反爬，未读）
- https://blog.csdn.net/sheepForTest/article/details/159501386 （WAF，未读）
- https://www.cnblogs.com/jzssuanfa/p/19702624 （只看了摘要）
- https://blog.csdn.net/m0_53539063/article/details/147637685 （只看了摘要）

**方法论与文献**
- Anthropic, Building effective agents：https://www.anthropic.com/engineering/building-effective-agents
- Madaan et al., Self-Refine：https://arxiv.org/abs/2303.17651
- Huang et al., Large Language Models Cannot Self-Correct Reasoning Yet：https://arxiv.org/abs/2310.01798
- Kamoi et al., When Can LLMs Actually Correct Their Own Mistakes?（TACL 综述）：https://arxiv.org/abs/2406.01297
- Gou et al., CRITIC：https://arxiv.org/abs/2305.11738
- Olausson et al., Is Self-Repair a Silver Bullet for Code Generation?：https://arxiv.org/abs/2306.09896
- Zheng et al., Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena：https://arxiv.org/abs/2306.05685
- Panickssery et al., LLM Evaluators Recognize and Favor Their Own Generations：https://arxiv.org/abs/2404.13076
- Wataoka et al., Self-Preference Bias in LLM-as-a-Judge：https://arxiv.org/abs/2410.21819
- Laban et al., LLMs Get Lost In Multi-Turn Conversation：https://arxiv.org/abs/2505.06120
- Hong et al.（Chroma）, Context Rot：https://www.trychroma.com/research/context-rot
- Shao et al., STORM：https://arxiv.org/abs/2402.14207
- Bai et al., LongWriter：https://arxiv.org/abs/2408.07055
- Qwen3-30B-A3B-Instruct-2507 模型卡：https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507
