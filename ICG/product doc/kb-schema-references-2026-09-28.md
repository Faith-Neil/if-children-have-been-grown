# 企业投标资料库：可复用/可借鉴设计方案调研

- 调研日期：2026-09-28（UTC+8）
- 适用背景：私有化部署智能投标系统；主投数据库维保、IT 运维服务类标；要求通用（后续扩展工程/货物类）、好维护
- 草案实体：公司主体、资质证书、人员、人员证书、厂商产品（字典）、原厂授权、业绩合同、SLA 模板、方案片段、附件文件
- 方法：只读公开资料。GitHub 仓库通过 GitHub API / raw.githubusercontent.com 读取源码；标准类读取政府网站原文或政府网站转载的 PDF；商业产品读取官网、帮助中心。没有注册、没有联系任何人。
- 来源标注：**【官方原文】**＝发布机关/厂商自己的网站或原始文件；**【官方转载】**＝其他政府网站转载的原文附件；**【第三方】**＝媒体、导航站、论坛、搜索摘要等转述；**【源码】**＝仓库里的实际代码/SQL/schema 文件。
- 下文中的字段名都照源码或原文抄录，没有自己补造的字段。标“建议”的内容是本报告的设计建议，不是任何来源的定义。

---

## 0. 一句话结论

1. **没有哪个现成方案能同时做到：许可证宽松、设计成熟、覆盖全部 10 个实体。** 开源 AI 标书项目的资料库大多还是“文件夹＋向量库”，结构化的资质/人员/业绩表很少。结构化做得最完整的两个，一个是 AGPL（OpenBidKit_Yibiao），一个仓库里没有许可证（RudyJunyu/Bid_Agent），都只能参考思路。
2. **字段命名最硬的依据是两份国家发改委系文件**：《电子招标投标系统技术规范 第1部分：交易平台技术规范》（2013，《电子招标投标办法》附件）和《公共资源交易平台系统数据规范（V2.0）》（发改办法规〔2018〕1156号）。它们对“投标人/法人基本信息、资质、执业人员、执业资格、投标人业绩、合同、附件集”都给出了**中文名、英文名、类型、长度、代码表**。
3. **“原厂授权”“SLA 模板”“厂商产品字典”在所有开源项目和国家标准里都没有找到字段级定义**，需要自己设计。ITSS（GB/T 28827.1-2022、T/CESA 1299—2023）只规定了“服务级别管理”的过程要求，没有字段。
4. **治理机制（审核状态、负责人、复审周期、新鲜度、过期拦截、来源追溯）**可以借鉴 Loopio/Responsive 的官方帮助文档，以及 Hugin-Z/tender-writer-v3（MIT）的 `review_status` + `company_type` 隔离规则。

---

## 1. 开源项目的实际数据模型

### 1.0 仓库元数据与许可证一览

| 仓库 | 实际 LICENSE 文件 | 备注 | Stars / 最近推送（UTC+8） | 资料库形态 |
|---|---|---|---|---|
| FB208/OpenBidKit_Yibiao | AGPL-3.0 | README 要求保留 NOTICE 归属 | 3053 / 2026-09-28 14:14 | **结构化表（SQLite，Electron 客户端）** + 知识库条目 |
| guangshu100/BidMaster-Pro | AGPL-3.0 | **README 徽章和正文写的是 MIT，与 LICENSE 文件不一致** | 331 / 2026-09-03 17:44 | 只有向量知识库，**没有资质/人员/业绩表** |
| Hugin-Z/tender-writer-v3 | MIT | Claude Skill，数据用 Markdown frontmatter + CSV | 5 / 2026-06-10 16:07 | **按类别分的 schema.md（字段规范）** |
| Get00/BiaoShu-SKILL | Apache-2.0 | **README 写 MIT，与 LICENSE 文件不一致** | 164 / 2026-09-24 09:39 | 没有数据模型（只有 `--company-profile` 的 JSON 入参，结构未定义） |
| zeronezer/bidcraft | Apache-2.0 | NOTICE/ATTRIBUTION 要求显著注明来源 | 62 / 2026-09-17 15:18 | MySQL 表；面向工程施组，**没有资质/人员/业绩表** |
| shandianT/bid-dog | **专有许可证（非开源）** | LICENSE 明文写明“本软件不是开源软件”，禁止复制和制作衍生作品 | 7 / 2026-09-24 14:32 | 文件夹素材库 + “待确认事实”（公司/资质/业绩/人员） |

来源：GitHub API `https://api.github.com/repos/<owner>/<repo>`（stars、推送时间、许可证识别结果），以及各仓库 `main` 分支的 LICENSE/README 原文：
- https://github.com/FB208/OpenBidKit_Yibiao/blob/main/LICENSE ，README 许可证一节：https://github.com/FB208/OpenBidKit_Yibiao/blob/main/README.md
- https://github.com/guangshu100/BidMaster-Pro/blob/main/LICENSE ，README：https://github.com/guangshu100/BidMaster-Pro/blob/main/README.md
- https://github.com/Hugin-Z/tender-writer-v3/blob/main/LICENSE
- https://github.com/Get00/BiaoShu-SKILL/blob/main/LICENSE ，README：https://github.com/Get00/BiaoShu-SKILL/blob/main/README.md
- https://github.com/zeronezer/bidcraft/blob/main/LICENSE ，https://github.com/zeronezer/bidcraft/blob/main/NOTICE ，https://github.com/zeronezer/bidcraft/blob/main/ATTRIBUTION.md
- https://github.com/shandianT/bid-dog/blob/main/LICENSE ，https://github.com/shandianT/bid-dog/blob/main/NOTICE

### 1.1 FB208/OpenBidKit_Yibiao（AGPL-3.0）【源码】

**资质库（credential library）**。字段来自 `client/src/features/credential-library/types.ts`，表名和列名来自 `client/electron/services/credentialLibraryService.cjs`：
- https://github.com/FB208/OpenBidKit_Yibiao/blob/main/client/src/features/credential-library/types.ts
- https://github.com/FB208/OpenBidKit_Yibiao/blob/main/client/electron/services/credentialLibraryService.cjs

| 表 | 字段（列名） |
|---|---|
| `credential_library_profile`（单行，PROFILE_ID='1'，**只支持一个公司主体**） | company_name, unified_social_credit_code, phone, email, legal_representative, registered_capital, operating_period_start, operating_period_end, address, business_scope, industry, company_type, insured_employee_count, company_intro, tax_certificate_date, tax_certificate_note, audit_report_date, audit_report_note, social_security_certificate_date, social_security_certificate_note, bank_account_name, bank_account_number, bank_name, bank_routing_number, watermark_enabled, watermark_content, createdAt/updatedAt |
| `credential_library_certificates` | certificate_id, name, number, validity_mode（'' / 'range' / 'long-term'）, valid_from, valid_to |
| `credential_library_employees` | employee_id, name, id_number, position, professional_title, gender, phone, id_validity_mode, id_valid_from, id_valid_to, education, school, major, introduction |
| `credential_library_projects`（业绩） | project_id, project_name, project_number, customer_name, project_type（'' / 'service' / 'goods' / 'construction'）, project_manager, contract_amount, start_date, end_date, project_status, introduction |
| `credential_library_other_materials` | material_id, name, note |
| `credential_library_images`（**多态附件**） | imageId, ownerType（profile/certificate/employee/project/other）, ownerId, fieldKey, originalName, relativePath, assetUrl, customName, sortOrder |

附件槽位 `fieldKey`（这是该项目最值得借鉴的地方）：
- 公司：officeEnvironment, businessLicense, legalRepresentativeIdEmblem/Portrait, legalRepresentativeAuthorization, authorizedRepresentativeIdEmblem/Portrait, basicDepositAccountInfo, creditChinaReport, governmentProcurementRecord, enterpriseCreditReport, dishonestEnforcementQuery, taxCertificate, auditReport, socialSecurityCertificate, bankAccountLicense
- 证书：certificateImages
- 人员：employeeSocialSecurity, employeeIdEmblem, employeeIdPortrait, laborContract, educationCertificate, driverLicense, skillCertificate
- 业绩：projectContract, bidWinningNotice, projectAcceptanceCertificate, paymentInvoice

**知识库**（`client/src/features/knowledge-base/types.ts`）：KnowledgeFolder(id, name, sort_order)、KnowledgeDocument(id, folder_id, file_name, status 共 11 个解析状态, progress, item_count …)、KnowledgeItem(id, title, resume, content, source_block_ids, source_file)。
- https://github.com/FB208/OpenBidKit_Yibiao/blob/main/client/src/features/knowledge-base/types.ts

评价：字段贴近政府采购实务（信用中国截图、失信被执行人查询、基本存款账户、社保/纳税/审计的日期＋说明）。**不足**：只有一个公司主体；证书没有发证机构、等级、类别；人员证书没有独立成表（只有 skillCertificate 图片槽位）；没有原厂授权、厂商产品、SLA；没有审核状态。

### 1.2 guangshu100/BidMaster-Pro（LICENSE 为 AGPL-3.0）【源码】

- `db/init_pg.sql` 的表：users, rbac_roles, rbac_permissions, rbac_user_roles, rbac_role_permissions, projects, documents, analyses, outlines, chapters, check_reports, skill_configs, agent_configs, notifications, **knowledge_bases**(id, name, doc_count, embedding_model, collection_name, created_at), monitoring_tasks, crawl_results。
  https://github.com/guangshu100/BidMaster-Pro/blob/main/db/init_pg.sql
- ORM 与 SQL 一致：https://github.com/guangshu100/BidMaster-Pro/blob/main/services/models.py
- 知识库上传后切块写入 ChromaDB，chunk metadata 只有 `{"source", "kb_id"}`：https://github.com/guangshu100/BidMaster-Pro/blob/main/services/routers/knowledge.py
- 资质核查是 LLM 提示词，5 项检查：有效期覆盖投标截止日、名称一致、企业名称一致、三证合一、清晰度。可以作为“资质校验规则”的参考：https://github.com/guangshu100/BidMaster-Pro/blob/main/services/check/skills/qualification_check_skill.py
- 结论：**没有结构化资料库**，对本需求价值低。另外搜索到 `sirchinj/BidMaster-Pro`（https://github.com/sirchinj/BidMaster-Pro ）描述相同，两者关系未核实。

### 1.3 Hugin-Z/tender-writer-v3（MIT）【源码】

资料以“类别/公司 id”两级目录存放，每类配一份 `*schema.md` 字段规范（YAML frontmatter）：
- 总说明：https://github.com/Hugin-Z/tender-writer-v3/blob/main/assets/README.md
- 公司注册表：https://github.com/Hugin-Z/tender-writer-v3/blob/main/companies.yaml

| 类别 | 字段（frontmatter 原文） | 来源 |
|---|---|---|
| 通用头（所有类别） | company_id, company_type（own / partner；reference 严禁进入 assets）, review_status（pending / approved）, source_file, ingest_date | 各 schema.md |
| 公司资质 | 资质名称, 资质等级, 证书号（脱敏：前4位+****+后4位）, 颁证机构, 颁证日期, 有效期至, 适用范围, 是否年审, 下次年审日期 | https://github.com/Hugin-Z/tender-writer-v3/blob/main/assets/公司资质/资质schema.md |
| 团队简历 | 姓名（脱敏）, 性别, 出生年份, 学历, 毕业院校, 专业, 工作年限, 当前岗位, 职称, 关键证书[], 证书有效期{证书名: 日期}, 适配项目类型[] | https://github.com/Hugin-Z/tender-writer-v3/blob/main/assets/团队简历/简历schema.md |
| 类似业绩 | 项目名称, 甲方单位, 甲方类型（政府机关/事业单位/国有企业/央企/其他）, 合同金额（万元）, 项目周期, 开始日期, 结束日期, 行业分类, 项目规模, 关键技术[], 验收结果（已验收/在建/待验收）, 项目地点 | https://github.com/Hugin-Z/tender-writer-v3/blob/main/assets/类似业绩/业绩schema.md |
| 标准话术 | 话术名称, 适用维度, 适用场景[], 字数, 来源项目, 中标证据, 核心句式；正文包括“话术正文 / 改写建议 / 注意事项” | https://github.com/Hugin-Z/tender-writer-v3/blob/main/assets/标准话术/话术schema.md |
| 通用图表 | 图表标题, 图表类型, 适用维度[], 适用项目类型[], 原图路径, 原图格式, 原图分辨率, 适配能力[] | https://github.com/Hugin-Z/tender-writer-v3/blob/main/assets/通用图表/图表schema.md |
| 历史标书案例（knowledge_base） | 项目类型, 项目名称, 甲方单位, 预算, 结果（中标/未中标/废标）, 评分, 排名, 中标金额, 关键成功因素[], 失败原因[], 评委关注点[] | https://github.com/Hugin-Z/tender-writer-v3/blob/main/references/knowledge_base/历史标书案例/案例schema.md |
| 公司（companies.yaml） | id, name, type（own/partner/reference）, status, aliases, legal_representative, address, phone, email, fax, postal_code, business_license_no, registered_capital, company_type, established_date, business_period, legal_representative_gender, legal_representative_title | companies.yaml |

值得借鉴的治理规则（原文要点）：
- 只有 `review_status=approved` 的素材允许被标书引用。
- `partner` 素材可以引用，但必须注明来源；`reference`（竞品/标杆）素材严禁进入可引用库。
- 缺失字段填 `TODO:待人工确认`，严禁编造。
- 摄入时用 sha256 去重（`.ingest_history.json`），原始文件带时间戳前缀归档到 `_raw/`。
- 资产类型映射表：https://github.com/Hugin-Z/tender-writer-v3/blob/main/references/asset_type_mapping.yaml

### 1.4 Get00/BiaoShu-SKILL（LICENSE 为 Apache-2.0）【源码】

- 没有数据库和实体模型。`bid_writer_pipeline.py` 只接收一个 `company_profile` 文件路径，结构没有定义：https://github.com/Get00/BiaoShu-SKILL/blob/main/BiaoShu-writer-pro/scripts/bid_writer_pipeline.py
- 可参考的是按行业划分的章节配置 `industry_configs.json`，例如 `it_information` 的“售后服务”包含：服务体系、响应时间、培训计划、备品备件。可以作为 SLA/方案片段的分类参考：https://github.com/Get00/BiaoShu-SKILL/blob/main/BiaoShu-writer-pro/references/industry_configs.json

### 1.5 zeronezer/bidcraft（Apache-2.0）【源码】

`scripts/init_db.sql`（MySQL 8）：https://github.com/zeronezer/bidcraft/blob/main/scripts/init_db.sql
- 知识库相关：`knowledge_doc`(file_name, file_path, doc_category sod/method, project_tags JSON, status, parsed_path, **file_md5**)、`knowledge_page`(doc_id, chapter_type, title, tags, content JSON, **source_location**, status draft/confirmed)、`method_index`(name, summary, applies_to)、`experience_item`(exp_type, chapter_type, tags, content, source JSON, status pending/confirmed)
- 事实表：`global_fact`(project_id, lot_id, category, fact_key, fact_value, unit, source_file, source_location, **confidence**, status pending/confirmed/expired, **edited**（人工改过，重新抽取时不覆盖）, version)
- 文件：`project_file`(category, status, parsed_path, file_md5)、`file_section_index`
- 结论：面向工程施工组织设计，**没有资质/人员/业绩/授权**。可借鉴的是方案片段的“章节类型 + 适用范围 + 来源位置 + draft/confirmed”，以及事实表的“置信度 + 人工编辑锁 + 版本”。

### 1.6 shandianT/bid-dog（专有许可证，**不可复用**）【源码，仅了解】

- 素材库是本地文件夹。入库时从历史标书抽取“待确认事实”，勾选确认后才写入 `公司介绍.md` / `资质与案例.md`。展示字段：资质(name, level, issuer, valid_until)、业绩(project, client, amount, date, role)、人员(name, title, certs)。
  https://github.com/shandianT/bid-dog/blob/main/app-next/src/views/FactsPanel.jsx ，https://github.com/shandianT/bid-dog/blob/main/app-next/src/views/AssetsSheet.jsx
- 思路可以参考：先抽取、再人工确认、确认后才能引用；业绩带 `role`（我方角色）。代码和设计文件不能复制（LICENSE 禁止衍生作品）。

### 1.7 其他搜到的开源项目

| 项目 | 许可证 | 资料库结构（已读文件） | 来源 |
|---|---|---|---|
| **RudyJunyu/Bid_Agent** | **仓库根目录没有 LICENSE 文件**（按惯例视为保留全部权利） | `DATABASE_SCHEMA_DESIGN.md` 是**本次找到的最完整的投标资料库设计文档**。企业知识库层：`companies`(company_name, short_name, credit_code, legal_representative, registered_capital, business_scope, address, contact_person, contact_phone, company_profile, status)；`company_qualifications`(company_id, qualification_type 枚举：营业执照/体系认证/行业资质/**授权**/许可证/其他, qualification_name, certificate_no, issuer, issue_date, expire_date, valid_status 有效/临期/过期/待核对, file_path, applicable_scope, notes)；`company_personnel`(name, role, title, certificates JSON, education, years_experience, project_experience, file_path, availability_status 可用/占用/停用/待确认)；`financial_records`(record_type, fiscal_year, revenue, net_profit, total_assets, tax_status, social_security_status…)；`performance_records`(project_name, client_name, industry_domain, contract_amount, contract_date, acceptance_date, project_scope, proof_files JSON, reusable_points, tags)；`historical_cases`；`historical_bid_files`；`solution_materials`(material_type 枚举, title, content, applicable_domain, applicable_project_type 服务/货物/工程, quality_level, source_case_id, source_bid_file_id, tags, confirmed_status) | https://github.com/RudyJunyu/Bid_Agent/blob/main/DATABASE_SCHEMA_DESIGN.md |
| **HunterLzap/rag-tender** | MIT | `qualifications`(file_id, name, number, issue_date, expiry_date, issuing_authority, scope, level, holder, category enterprise/personnel/performance/financial, status valid/expiring/expired **由 expiry_date 计算**, raw_text)；`knowledge_files`(filename, file_path, file_type, category, status, extracted_text, extracted_at)；`PerformanceProject`(project_name, client_name, contract_no, contract_amount, sign_date, completion_date, project_scope, year, file_ids, remark) | https://github.com/HunterLzap/rag-tender/blob/HEAD/backend/app/models/knowledge.py ，https://github.com/HunterLzap/rag-tender/blob/HEAD/backend/app/models/performance.py ，LICENSE：https://github.com/HunterLzap/rag-tender/blob/HEAD/LICENSE |
| **ry-vue-flowable-xg**（若依 flowable-plus 二开，工程 OA） | MIT（LICENSE 版权行是 RuoYi-Flowable-Plus；Gitee 页面自述 MIT，并说明“仅推荐用于学习”） | `sys_oa_bid`(bid_title, bid_number, bid_type, budget, package_info, expiration_time, agency, document_info JSON 保证金, is_win…)；`sys_oa_contract`(contract_num, contract_name, first_name/person/phone 甲方, second_name/person/phone 乙方, contract_price, sign_time, validity, contract_type, contract_status, accessory)。**没有资质/人员证书表** | https://gitee.com/weity/ry-vue-flowable-xg ，GitHub 镜像 SQL：https://github.com/huangxing2010/ry-vue-flowable-xg/blob/master/script/sql/mysql/ry-vue-flowable-xg.sql |
| Gitee kai-yuan/ruoyi-vue3-ts-springboot-certificate-management（若依证书管理） | 未核实 | README 只说“证书的增删改查、导入、导出”，**没有读到 SQL，字段未知** | https://gitee.com/kai-yuan/ruoyi-vue3-ts-springboot-certificate-management |
| **Odoo 19 hr_skills**（开源 ERP 的人员证书模块） | LGPL-3.0 | `hr.skill.type.is_certification`（把一个技能类型标记为“证书类”）；员工技能 mixin 有 `valid_from`(Validity Start)、`valid_to`(Validity Stop)，并据此判断过期；`hr.resume.line` 有 date_start, date_end, line_type_id, certificate_file, certificate_filename, external_url | https://github.com/odoo/odoo/blob/19.0/addons/hr_skills/models/hr_skill_type.py ，https://github.com/odoo/odoo/blob/19.0/addons/hr_skills/models/hr_individual_skill_mixin.py ，https://github.com/odoo/odoo/blob/19.0/addons/hr_skills/models/hr_resume_line.py ，LICENSE：https://github.com/odoo/odoo/blob/19.0/LICENSE |
| JeecgBoot 上的投标管理项目 | — | **未查到**公开的、带资质/人员证书表的项目 | — |

---

## 2. 商业产品公开的资料库分类与治理

> 以下厂商都**没有公开字段级 schema**，只能整理分类和机制。

| 产品 | 资料库分类（原文） | 公开的字段 / 治理机制 | 来源与性质 |
|---|---|---|---|
| **钛投标** | 企业自有库：资质、业绩、人员、**产品、工器具、备品备件**、历史投标文件；FAQ 另列“企业基本信息与资质证书；财务信息与财务报表；项目业绩与历史投标文件；人员信息与技术团队资料；产品资料、工器具与备品备件信息” | 企业版有“专属企业知识库 / 图库 / 标书版式风格”，写明支持私有化部署。第三方介绍提到“多子公司知识库隔离”“按行业、项目类型标签检索” | 【官方原文】https://taitoubiao.com/llms.txt ，https://taitoubiao.com/faq/what-resources-reusable.html ；【第三方】https://www.aitop100.cn/tools/taitoubiao |
| **巧文书** | 官网写“企业知识库用于沉淀历史标书、企业资信、产品资料和专属图库”。资信库分为：基本信息、项目人员、企业证书、项目业绩、财务信息、行业标准 | 营业执照 OCR；证书自动抓取“证书编号/发证单位/有效期”，**过期前 7 天预警，标书禁用过期资料**；人员有在职/已离职/停用状态，无效人员自动屏蔽；业绩填写“项目金额/甲方单位/起止时间/验收结果”并打标签；财务上传近 3 年审计报告/社保/纳税证明 | 【官方原文】https://qiaowenshu.cn/ （只有概述）；【第三方，厂商在 V2EX 发的更新帖】https://www.v2ex.com/t/1124504 ；【第三方】https://sanwenge.com/post/1263.html |
| **智标枪** | 平台行业知识库 + 企业自有知识库（企业资质、产品方案、技术材料、历史标书、项目案例） | 访问控制、数据加密、审计留痕；支持 SaaS/公有云/私有化部署。**没有公开字段** | 【官方原文】https://www.bid-gun.com/ |
| **投标官**（舍予基业） | 企业资料库、响应矩阵、**全局事实表** | 每条招标要求挂接资料库证据（要求 × 响应 × 证据 × 章节）；“业绩、人员、证书编号，只能引用资料库里真实存在的条目，每处引用都带 [证据] 标记”，没有依据的写【待补】；**占位符未清零或★项未响应时锁定导出**；规则示例“R3 证书有效期覆盖递交日” | 【官方原文】https://toubiao.agecms.com/ |
| 喜鹊标书AI（补充） | 知识库、产品库（产品名称、型号、参数）、图片库、资信库（企业基本信息、人员、财务、合同、资质荣誉） | 提醒“应明确每份资料的适用项目、有效时间和对应版本” | 【第三方，媒体稿】http://enet.com.cn/article/2026/0901/A202609011276990.html ，http://enet.com.cn/article/2026/0903/A202609031277041.html |
| 标书魔方（中控，补充） | 投标素材沉淀库：企业资质、业绩、技术方案、检测报告、人员证书；匹配时填充“业绩、人员、**设备**、技术方案” | 关键词检索、分类归档、权限管控 | 【第三方】https://www.aitop100.cn/tools/biaoshu-supcon |
| **Loopio** | 三级分类：**Stack**（最高层，**按 Stack 控制访问权限**）→ **Category** → **Subcategory**（可选）；**Tag**（跨结构的元过滤器，例如按产品或按地区区分答案变体） | Entry（Q&A 对）字段/机制：Question、**Alternate Question**（同义问法）、Answer（可含附件）、**Alert**（使用前提示，≤250 字符）、Comments（内部备注）、Language、**Library Merge Variable**（随时间变化的值，例如客户数）、**Linked Entries**（中英版本或长短版本互链）、**Entry History**、**Freshness Score**（复审后为 100%，随时间下降）、**Review Cycles**（可设在 Category、Subcategory 或单条 Entry 上）、Reviews from Projects（项目结束后回流入库）；官方建议避免重复条目 | 【官方原文】Loopio Dictionary https://support.loopio.com/hc/en-us/articles/4417065553171-Loopio-Dictionary （WebFetch 被 Cloudflare 拦截，改用 curl 读取 Zendesk 公开 API：https://support.loopio.com/api/v2/help_center/en-us/articles/4417065553171.json ，更新时间 2026-09-17 05:06 UTC+8） |
| **Responsive（原 RFPIO）** | Content Library（Q&A 对、文档、Section Templates、**Catalogs**＝产品/服务目录模板）；**Collection**（切分内容库并限制可见范围）；**Tag**；**Custom Fields** | **Owner**（负责维护，可被分配复审）；**Moderator**（开启后，现有 Q&A 的修改须经审核才发布）；**Review cycle**（只能给已有 Owner 的条目设；复审方式有 Any/All/Sequential；按周期定期复审，也可临时发起；最多 4 个跟进日期；“Review Cycle”和“Next Review Date”默认必填）；**Alert text**；**Merge Tag**（动态占位） | 【官方原文】https://help.responsive.io/en-US/responsive/article/cbwhsNYn-glossary-of-responsive-terms ，https://help.responsive.io/en-US/responsive/article/16Yt23ND-setting-up-scheduled-review-cycles |

---

## 3. 国家/行业标准与规范

### 3.1 《电子招标投标系统技术规范 第1部分：交易平台技术规范》（2013）——《电子招标投标办法》附件，与办法同等效力

- 【官方原文】办法第三条、第六十五条（“技术规范作为本办法的附件，与本办法具有同等效力”）和附件正文：https://www.gov.cn/zhengce/2021-11/30/content_5713227.htm （gov.cn 网页版的附录 A 数据项**表格没有显示出来**）
- 【官方文本转载 PDF，第三方交易平台托管】附录 A 数据项表格读自：https://www.wtjy360.com/trade/upload/website/downloadArea/2018-11-05/20181105205309217.pdf

与资料库直接相关的条款：
- **6.4 投标人信息库 a)**：投标人代码、投标人名称、负责人、国别/地区、资质序列、资质等级、资信等级、奖惩记录、营业执照号码、CA 证书编号、组织机构代码、税务登记号、开户银行、基本账户账号、注册资本、注册资本币种、信息申报和变更责任人、联系电话、联系地址、邮政编码、电子邮箱。
- **6.4 e)** 投标人专业职业资格人员：姓名、性别、身份证件类型、身份证件号码、出生年月、所在行政区域代码、最高学历、联系电话、通讯地址、邮政编码、所在单位、职务、技术职称、职业资格序列、职业资格等级、职业证书编号、从业经历、从业年限、项目业绩、奖惩记录。
- **附录 A.2**（每个字段都有数据类型和格式）：
  - A.2.1 招投标主体基本信息表：主体代码（C9，组织机构代码）、主体名称、负责人、国别/地区（GB/T 2659）、单位性质（GB/T 12402）、行政区域代码（GB/T 2260 市级）、行业代码（GB/T 4754 门类+大类）、营业执照号码、CA 证书编号、税务登记号、资信等级、开户银行、基本账户账号、注册资本 N..20,2、注册资本币种（GB/T 12406）、注册资本单位、信息申报责任人、联系电话、联系地址、邮政编码、电子邮箱、主体类型、交易平台验证人员、交易平台验证时间
  - A.2.2 主体经营资质信息表：主体代码、资质序列行业和专业类别（C6）、资质等级（C2）、资质证书编号、信息申报责任人
  - A.2.4 职业人员基本信息：职业人员代码（身份证号 C18）、姓名、性别（GB/T 2261.1）、出生年月、所在行政区域代码、最高学历、联系电话、通讯地址、邮政编码、所在单位代码、所在单位名称、是否在职、职务、技术职称、从业经历、从业年限
  - A.2.5 人员职业资格信息：职业人员代码、职业资格序列、职业资格等级、资格证书编号（原文“资格资格证书编号”，疑为笔误）、注册登记证书编号
  - A.2.6 人员业绩信息：职业人员代码、标段（包）编号/名称、招标人代码/名称、合同金额、结算金额、金额币种代码、金额单位、合同签署时间、合同完成时间
  - A.2.7 投标人业绩：投标人代码、中标项目的标段（包）编号、中标项目和标段（包）名称、招标人代码/名称、中标金额、合同金额、合同结算金额、合同期限（天）、实际履行期限（天）、金额币种代码、金额单位、合同签署时间
  - A.2.8 奖惩记录：奖惩对象代码、奖惩对象类型、奖惩时间、奖惩内容、奖惩类型
- **附录 B**：B.3.6 标段（包）分类代码第一级为 **A-工程、B-货物、C-服务**、D-产权、E-土地（**可以直接用作“工程/货物/服务”的通用分类**）；B.3.7 附件关联标识号用 GUID；B.3.15 资质序列、行业和专业类别为 6 位层次码；B.3.16 资质等级代码。
- **第 6 章导语**：信息资源库原则上只收经过验证的信息；另建的“辅助信息资源库”收集非可靠信息的，“应当注明信息采集来源和相关责任人员”。**这可以作为资料库“来源 + 责任人”字段的规范依据。**
- 局限：业绩表注明“业绩仅限于在电子招投标交易平台上成交的项目”；主体代码还是 9 位组织机构代码（三证合一以前的口径），V2.0 已改用 18 位统一社会信用代码。

### 3.2 《公共资源交易平台系统数据规范（V2.0）》（发改办法规〔2018〕1156号，2018 年 9 月）

- 【官方原文】通知：https://www.ndrc.gov.cn/xxgk/zcfb/tz/201810/t20181008_962289.html ，https://www.gov.cn/zhengce/zhengceku/2018-12/31/content_5435038.htm
- 【官方转载 PDF，湖南省发改委】正文读自：http://fgw.hunan.gov.cn/xxgk_70899/tzgg/201810/9766404/files/e9ae80b76cdf41efb712d6a2a058bbca.pdf
- 截至 2026-09-28 **没有查到国家层面的 V3.0**；2024 年只看到地方标准（例如 DB35/T 2167-2024、DB41/T 2685-2024），未细读。

**第 14 章“主体信息数据集”**（字段照原文，英文名是规范自带的）：
- **14.1.1 法人基本信息（表 89）**：法人名称 LEGAL_NAME、法人类别 BIDDER_CODE_TYPE、法人代码 LEGAL_CODE（C18，GB 32100-2015）、法人角色 LEGAL_ROLE、营业执照号码 LICENSE_NO、营业执照失效日期 LICENSE_END_DATE、国税/地税税务登记证号及失效日期（TAX_CERT_NO / TAX_CERT_END_DATE / LOCAL_TAX_CERT_NO / LOCAL_TAX_CERT_END_DATE）、法定代表人姓名 LEGAL_REPRESENT、法人机构类别 LEGAL_TYPE、法人机构行业代码 LEGAL_INDUSTRY（GB/T 4754-2011）、国别/地区 COUNTRY_REGION、行政区域代码 REGION_CODE、注册资本 REG_CAPITAL（N..20,6）、注册资本币种 REG_CAP_CURRENCY、注册资本单位 REG_UNIT、联系人 LEGAL_CONTACT、联系人电话 LEGAL_CONTACT_PHONE、数据时间戳 DATA_TIMESTAMP 等
- **14.1.4 投标人扩展信息（表 92）**：主体代码 LEGAL_CODE、资质等级 QUAL_LEVEL（C2）、资质名称 QUAL_NAME、资质序列行业和专业类别 QUAL_TYPE（C6）、资质证书编号 QUAL_CERT_NO、资质证书失效日期 QUAL_CERT_END_DATE、自定义数据项 CUSTOM_DEFINITION_DATAITEM（C..5000）
- **14.1.7 供应商扩展信息（表 95）**：字段与投标人扩展信息相同（政府采购口径，资质等级/名称为非必填）
- **14.2.5 执业人员基本信息（表 103）**：身份证件号码 ID_CARD、身份证件类型 ID_CARD_TYPE、姓名 PERSON_NAME、行政区域代码 REGION_CODE、联系电话 PERSON_PHONE、所在单位代码 UNIT_CODE、所在单位名称 UNIT_NAME、**从业开始时间 WORK_START_DATE**
- **14.2.6 执业人员资格信息（表 104）**：执业资格名称 QUAL_NAME、执业资格类型 QUAL_TYPE、执业人员证件号 ID_CARD、执业人员身份证件类型 ID_CARD_TYPE、执业资格证书编号 CERT_NO、**执业资格注册有效期止 CERT_END_DATE**
- **14.3 附件集**：附件集结构（ATTACHMENT_SET_CODE, ATTACHMENT_COUNT, ATTACHMENT_NAME, ATTACHMENT_TYPE, ATTACHMENT_FILE_NAME, URL）；附件采集项（营业执照副本扫描件 LICENSE_CERT_DOC、组织机构代码证扫描件 ORGAN_CERT_DOC、税务登记证扫描件 TAX_CERT_DOC、资质证书副本扫描件 QUAL_CART_DOC、执业人员身份证件扫描件 ID_CARD_DOC、执业资格证书扫描件 PROFESSIONAL_CART_DOC）
- **14.4 代码集**：法人机构类别（1 企业 / 2 机关法人 / 3 事业单位 / 4 社会组织 / 9 其他）；主体角色类型（01 招标人 … 03 投标人 … 06 供应商 …）；**资质等级（01 特级、02 一级、03 二级、04 三级、05 四级、06 甲级、07 乙级、08 丙级、09 丁级、10 暂定级、11 初级、12 中级、13 高级）**；资质序列、行业和专业类别（6 位层次码，详见《企业资质序列行业和专业类别编码标准》，**本次未取得该标准原文**）；资质类型（表 111，执业资格代码，例如 010201 一级注册建造师、010801 注册造价工程师……**以工程类执业资格为主，没有 IT 类证书**）；**主体类别（1 自然人 / 2 法人 / 3 联合体 / 4 部队 / 5 港澳企业 / 6 境外企业 / 7 二级单位（非法人）/ 9 其他）**
- **7.5 工程建设合同（表 23）**：合同名称 CONTRACT_NAME、招标人名称/代码、中标人名称/代码、合同金额 CONTRACT_PRICE、金额币种代码 PRICE_CURRENCY、金额单位 PRICE_UNIT、合同主要内容 CONTRACT_CONTENT、合同期限 LIMITE_TIME（年）、质量要求 QUALITY_REQUIRE、递交时间 SUBMIT_TIME、合同签署时间 CONTRACT_SIGN_TIME
- **8.1.5 政府采购合同（表 49）**：采购项目编号/名称、子包编号、合同名称、采购人名称/代码、中标（成交）供应商名称 SUPPLIER_NAME / 代码 SUPPLIER_CODE、**价款形式代码 PRICE_FORM_CODE**、合同金额 CONTRACT_AMOUNT、币种 CURRENCY_CODE、金额单位 PRICE_UNIT、**中标优惠率或其它类型价格 WIN_BID_RATE**、合同期限 CONTRACT_TERM（年）、合同签署时间 SIGNING_TIME

### 3.3 行政许可“双公示”信用信息归集公示标准（许可证类资质的字段参考）

- 【官方转载，应急管理部网站“信用服务-制度文件”栏目，2018-07 附件】https://www.mem.gov.cn/fw/cxfw/xycx/zdwj/201807/W020180803400814056242.pdf ，字段说明：https://www.mem.gov.cn/fw/cxfw/xycx/zdwj/201807/W020180803400814064687.pdf
- 行政许可信息字段：XK_XDR_MC 行政相对人名称、XK_XDR_SHXYM 统一社会信用代码、XK_FRDB 法定代表人、XK_XKWS 行政许可决定文书名称、XK_WSH 文书号、XK_XKLB 许可类别、**XK_XKZS 许可证书名称、XK_XKBH 许可编号**、XK_NR 许可内容、XK_JDRQ 许可决定日期、**XK_YXQZ 有效期自、XK_YXQZI 有效期至、XK_XKJG 许可机关、XK_XKJGDM 许可机关统一社会信用代码、XK_ZT 当前状态**、XK_LYDW/XK_LYDWDM 数据来源单位及代码
- 存疑：搜索摘要称“2026 年 2 月 24 日起已启用新报送标准”，**没有找到原文，未核实**。

### 3.4 《中华人民共和国市场主体登记管理条例》（公司主体登记事项的法定口径）

- 【官方原文】https://www.gov.cn/gongbao/content/2021/content_5636139.htm
- 第八条 一般登记事项：名称；主体类型；经营范围；住所或者主要经营场所；注册资本或者出资额；法定代表人、执行事务合伙人或者负责人姓名。第九条 备案事项包括：章程、**经营期限**、认缴出资额、董事监事高管、受益所有人等。

### 3.5 政府采购投标人资格证明材料

- 【官方原文】《政府采购法》第二十二条（2002 年公布，2014 年修正；此处读的是 2002 年公报版）：https://www.gov.cn/gongbao/content/2002/content_61590.htm
- 【官方原文】《政府采购法实施条例》第十七条：营业执照等证明文件（自然人提供身份证明）；财务状况报告，依法缴纳税收和社会保障资金的相关材料；具备履行合同所必需的设备和专业技术能力的证明材料；参加政府采购活动前 3 年内在经营活动中没有重大违法记录的书面声明；其他法定条件的证明材料。https://www.gov.cn/gongbao/content/2015/content_2827183.htm
- 【官方转载，地方解读】部分地区实行资格条件承诺制：https://czj.cq.gov.cn/zwgk_268/zfxxgkml/zcjd/bmjd/202205/t20220510_10700404_wap.html
- 用法：这些是**材料清单**，不是字段标准，适合作为“公司主体下的证明材料类型字典”（财务报告、纳税证明、社保证明、无重大违法记录声明等）的依据。

### 3.6 ITSS（运维服务能力）

- 【官方原文，ITSS 工作组】GB/T 28827.1-2022《信息技术服务 运行维护 第1部分：通用要求》，2023-05-01 实施，能力模型由人员、过程、技术、资源（PPTR）四要素组成：https://www.itss.cn/web/itss/a/1aecf3347910497dae25e83e2cc8ff88
- 【官方原文，ITSS 工作组托管 PDF】T/CESA 1299—2023《信息技术服务 运行维护服务能力成熟度模型》（代替 ITSS.1—2015）：人员要素包括人员能力规划、岗位结构、人员储备、人员培训、绩效管理、能力评价；过程要素 6.4.1“服务级别管理”要求“识别和定义运维服务清单；建立服务级别管理过程；签订并执行服务级别协议”，并要求“建立与 GB/T29264 相匹配的服务目录”。https://www.itss.cn/file/202411/28/20241128144802171.pdf
- 结论：**ITSS 没有定义人员、证书、SLA 的数据字段**，只有过程和管理要求。评估中对持证人员数量等要求，**没有在官方原文中查到**。GB/T 28827.1-2022 全文是付费标准，没有读到。

### 3.7 分类代码（通用性与扩展工程/货物）

- 【官方原文】《政府采购品目分类目录》（财库〔2022〕31号）：https://www.gov.cn/zhengce/zhengceku/2022-09/23/content_5711343.htm ；目录 PDF：http://gks.mof.gov.cn/guizhangzhidu/202209/P020220921609826606921.pdf 。其中 **C16070000 运行维护服务**，下分 C16070100 基础环境运维、**C16070200 硬件运维**、**C16070300 软件运维**（包括基础软件运维，原文“基础软件（包括操作系统、数据库管理系统…）”）、C16070400 安全运维、C16079900 其他运行维护服务；货物以 A 开头，工程以 B 开头。
- 【官方原文，标准信息平台】GB/T 29264-2012《信息技术服务 分类与代码》，现行：https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=1D8487A30DD439F2D882C282B79F53C5 （**全文未读，具体代码未核实**）
- 电子招投标技术规范 B.3.6 标段（包）分类代码：A 工程 / B 货物 / C 服务（见 3.1）。

### 3.8 查了但没有查到的

- 信用中国“信用报告”或国家企业信用信息公示系统的**对外字段标准**：未查到（只有 3.3 的双公示标准）。
- 住建“四库一平台”的数据标准：本次没有检索（与 IT 运维主业关系弱；扩展工程类时建议补查）。
- 《企业资质序列行业和专业类别编码标准》原文：未取得。

---

## 4. 与草案实体的对照表

图例：●＝有结构化字段定义；○＝只有分类/思路；—＝没有。

| 草案实体 | Yibiao | Bid_Agent | tender-writer | rag-tender | 其他开源 | 商业产品 | 标准 |
|---|---|---|---|---|---|---|---|
| 公司主体 | ●（单主体） | ● | ●（companies.yaml，含 own/partner/reference） | — | — | ○（全部都有） | ●（A.2.1；14.1.1；登记条例第八、九条） |
| 资质证书 | ● | ● | ● | ● | — | ○（巧文书：编号/发证单位/有效期+预警） | ●（A.2.2；14.1.4/14.1.7；双公示 XK_*） |
| 人员 | ● | ● | ● | — | Odoo（resume） | ○（巧文书在职状态） | ●（6.4 e、A.2.4；14.2.5） |
| 人员证书 | ○（只有图片槽位） | ○（JSON 列） | ○（列表+字典） | ○（category=personnel） | ●（Odoo is_certification + valid_from/to） | ○ | ●（A.2.5；14.2.6） |
| 厂商产品（字典） | — | — | — | — | — | ○（钛投标产品/工器具/备品备件；喜鹊产品库；Responsive Catalogs） | ○（品目目录 A 类货物编码，不是产品字典） |
| 原厂授权 | —（只能放 other） | ○（qualification_type 有“授权”枚举） | — | — | — | — | — |
| 业绩合同 | ● | ● | ● | ● | ●（ry-xg 合同表） | ○（巧文书业绩字段；bid-dog role） | ●（A.2.6、A.2.7；7.5；8.1.5） |
| SLA 模板 | — | ○（material_type 有“售后服务”） | — | — | ○（BiaoShu 售后服务小节） | — | ○（ITSS 服务级别管理的过程要求） |
| 方案片段 | ○（KnowledgeItem） | ●（solution_materials） | ●（标准话术/通用图表） | — | ●（bidcraft knowledge_page/method_index） | ●（Loopio/Responsive 条目治理） | — |
| 附件文件 | ●（多态 images + fieldKey 槽位） | ●（source_documents） | ○（_raw + sha256） | ●（knowledge_files） | ●（bidcraft file_md5） | — | ●（14.3 附件集 + 附件采集项；B.3.7 GUID） |

### 4.1 各实体的字段差异与值得补充的字段

下面“来源字段”都照原文抄录；“建议补充”是本报告的设计建议，已注明依据。

**① 公司主体**
- 来源字段并集：统一社会信用代码（LEGAL_CODE / unified_social_credit_code / credit_code）、名称、简称、法定代表人、注册资本（数值＋币种＋单位，V2.0）、经营期限起止（Yibiao operating_period_*；登记条例第九条“经营期限”）、住所、经营范围、行业代码（GB/T 4754）、行政区域代码（GB/T 2260）、国别/地区、法人机构类别、联系人/电话/邮箱、开户银行＋基本账户账号（6.4 a；Yibiao bank_*）、参保人数（Yibiao）、公司简介。
- 建议补充：
  - **主体类别**（依据 V2.0 14.4.7：法人 / 联合体 / 二级单位（非法人）…），用来支持分公司、联合体投标。
  - **主体关系类型** own/partner（依据 tender-writer company_type），用于联合体或分包方的材料要标注来源。
  - **状态** 有效/停用（依据 Bid_Agent）。
  - **信息申报责任人**（依据 A.2.1）。
  - 纳税/社保/审计证明的“开具日期＋说明”，建议从主体表拆到附件或证明材料表（Yibiao 把它们平铺在 profile 里，不利于按年度管理）。
  - 默认水印内容（Yibiao watermark_*）。

**② 资质证书**
- 来源字段并集：名称、证书编号、等级、类型/序列、发证机构、发证日期、有效期起止、长期有效模式（Yibiao validity_mode=long-term）、适用范围/认证范围原文、持证主体、状态（rag-tender 的 valid/expiring/expired 由有效期计算）、备注、是否年审、下次年审日期（tender-writer）。
- 建议补充：
  - **资质类型字典**：营业执照 / 体系认证 / 行业资质 / 授权 / 许可证 / 其他（依据 Bid_Agent 枚举）；IT 运维类要自己扩充 ISO 27001/20000、ITSS、CMMI 等，**标准代码表里没有这些**。
  - **资质等级代码**，直接采用 V2.0 表 110 的 01–13 码。
  - **许可机关统一社会信用代码、当前状态**（双公示 XK_XKJGDM、XK_ZT）。
  - **监督审核/年审日期**（tender-writer）。
  - **审核状态** pending/approved 与复审负责人（tender-writer；Responsive Owner）。

**③ 人员**
- 来源字段并集：姓名、证件类型＋证件号码（ID_CARD_TYPE/ID_CARD）、证件有效期（Yibiao）、性别、出生年月（A.2.4；tender-writer 出于脱敏只存年份）、最高学历、毕业院校、专业、职务/岗位、技术职称（14.2.5 GB/T 8561 在专家表中引用）、所在单位代码/名称、是否在职（A.2.4；巧文书 在职/已离职/停用）、从业开始时间 WORK_START_DATE（14.2.5）、从业年限、从业经历、项目业绩、奖惩记录、适配项目类型（tender-writer）、可用状态 可用/占用/停用（Bid_Agent）。
- 建议补充：
  - **从业开始日期**替代手填年限（依据 V2.0），年限按日期计算。
  - **社保缴纳单位/期间**、**劳动合同期限**（依据 Yibiao 附件槽位 employeeSocialSecurity、laborContract，并结合实施条例第十七条的社保要求）。
  - **占用状态**（同一项目经理在多个在投标段中的冲突；依据 Bid_Agent availability_status）。
  - 敏感字段脱敏/加密策略（依据 tender-writer 脱敏规则）。

**④ 人员证书**
- 来源字段并集：执业资格名称 QUAL_NAME、资格类型 QUAL_TYPE（代码）、职业资格序列、职业资格等级、资格证书编号 CERT_NO、**注册登记证书编号**（A.2.5）、注册有效期止 CERT_END_DATE（14.2.6）、有效期起止（Odoo valid_from/valid_to）、证书附件。
- 建议补充：
  - **把“资格证书号”和“注册证书号”分开存**（依据 A.2.5 两个独立字段）。
  - **注册单位**：须与投标主体一致。依据是 A.2.4 的“所在单位代码”，属于推论。
  - 发证机构、级别、继续教育/复审日期（建议）。
  - 证书类型字典可以借鉴 Odoo 的“技能类型 + is_certification”两层结构，厂商认证（如数据库厂商认证）和国家职业资格共用一张表。

**⑤ 厂商产品（字典）**
- 来源：开源项目和标准都没有字段定义。商业产品只给出分类：钛投标“产品资料、工器具与备品备件”，喜鹊“产品名称、型号和参数”，Responsive“Catalogs”。
- 建议字段（无来源定义）：厂商、产品线、产品名称、版本/型号、产品类别（可挂政府采购品目编码，依据 3.7）、生命周期状态。**维保标通常要求原厂授权或原厂服务，这个字典应作为“原厂授权”和“业绩合同服务对象”的外键。**

**⑥ 原厂授权**
- 来源：只有 Bid_Agent 在 qualification_type 枚举里列了“授权”、在 README 的资质管理里提到“授权文件和有效期”（https://github.com/RudyJunyu/Bid_Agent ）；**没有字段级定义**。
- 建议字段（无来源定义）：授权厂商（→厂商字典）、被授权主体（→公司主体）、授权产品/产品线（多对多）、授权类型（年度代理/服务授权/项目专项授权等）、适用项目名称/编号（项目专项授权）、授权书编号、有效期起止、授权地域、是否需要原件、附件。有效期计算和过期拦截沿用资质证书的机制。

**⑦ 业绩合同**
- 来源字段并集：项目名称、合同名称、合同编号、客户（招标人/采购人）名称＋代码、客户类型（tender-writer 甲方类型）、项目类型 service/goods/construction（Yibiao）、行业领域、中标金额、合同金额、**结算金额**（A.2.6/A.2.7）、币种、金额单位、**价款形式/中标优惠率**（8.1.5）、合同签署时间、开始/结束日期、合同期限、**实际履行期限**（A.2.7）、验收日期/验收结果、质量要求（7.5）、合同主要内容、项目经理、项目地点、关键技术、证明材料（合同、中标通知书、验收证书、发票：Yibiao 槽位；proof_files）、可复用亮点、标签。
- 建议补充：
  - **我方角色**（总包/分包/联合体成员；依据 bid-dog `role` 与 V2.0 主体类别“联合体”）。
  - **项目分类码**（政府采购品目 C1607xxxx；工程/货物用 A/B/C 大类，依据 3.1 B.3.6 与 3.7），这是日后扩展工程/货物的关键。
  - **服务对象产品**（→厂商产品字典，例如某数据库版本）。
  - 标段（包）编号（A.2.7）。

**⑧ SLA 模板**
- 来源：没有字段标准。ITSS 只要求“识别和定义运维服务清单、签订并执行服务级别协议、服务报告”（T/CESA 1299—2023 6.4.1）；BiaoShu 在 IT 行业售后小节列了“服务体系、响应时间、培训计划、备品备件”。
- 建议字段（无来源定义）：适用服务类别（C160702/C160703…）、服务时段、按故障等级的响应/到场/恢复时限、巡检频次、报告周期、备品备件承诺、适用厂商产品；**用变量占位**（借鉴 Loopio Library Merge Variable / Responsive Merge Tag）来承载具体数值。

**⑨ 方案片段**
- 来源字段并集：标题、正文、摘要（Yibiao resume）、类型/章节类型（Bid_Agent material_type、bidcraft chapter_type）、适用领域、适用项目类型（服务/货物/工程）、适用维度/评分项、适用场景、质量等级、来源案例/来源标书/来源位置（source_location、source_block_ids）、中标证据、改写建议、注意事项、标签、状态（draft/confirmed、pending/approved）。
- 建议补充（依据 Loopio/Responsive 官方文档）：
  - **负责人 owner**、**复审周期与下次复审日期**、**新鲜度**（Freshness Score）
  - **使用提示 Alert**、**同义问法 Alternate Question**（用于检索）、**变体互链 Linked Entries**（长短版本）
  - **修改审核 Moderation**、**版本历史 Entry History**
  - **按库/集合控制权限**（Stack/Collection）

**⑩ 附件文件**
- 来源字段并集：原文件名、存储路径、文件类型、大小、**哈希**（bidcraft file_md5；Bid_Agent file_hash；tender-writer sha256）、解析状态、解析产物路径、OCR/抽取文本（rag-tender extracted_text）、页数、**归属对象 + 用途槽位**（Yibiao ownerType/ownerId/fieldKey）、自定义名称、排序、附件集标识（V2.0 ATTACHMENT_SET_CODE）、附件关联标识号 GUID（B.3.7）。
- 建议补充：
  - **附件用途字典**：直接用 V2.0 14.3.2 附件采集项（LICENSE_CERT_DOC、QUAL_CART_DOC、ID_CARD_DOC、PROFESSIONAL_CART_DOC…）作为基础码，再合并 Yibiao 的 fieldKey 扩展。
  - 水印版本（Yibiao watermark）。
  - 上传人/上传时间、来源（依据技术规范第 6 章“注明信息采集来源和相关责任人员”）。

### 4.2 所有实体共用的治理字段（建议）

| 机制 | 依据 |
|---|---|
| `review_status`：pending → approved；未审核不得引用 | tender-writer README；Bid_Agent confirmed_status；bidcraft draft/confirmed；bid-dog 确认后才入库 |
| 有效期状态自动计算（有效/临期/过期），临期预警，过期禁止引用 | rag-tender status；Bid_Agent valid_status；巧文书“过期前 7 天预警、标书禁用过期资料”（第三方）；投标官“证书有效期覆盖递交日”规则（官方） |
| 来源追溯：来源文件、页码/章节、采集人、置信度、人工编辑锁 | bidcraft global_fact；技术规范第 6 章 |
| Owner + 复审周期 + 下次复审日期 + 新鲜度 | Loopio Dictionary；Responsive 帮助文档 |
| 主体隔离：own/partner/reference | tender-writer companies.yaml |
| 引用证据标记 + 缺失写【待补】+ 导出闸门 | 投标官官网 |

---

## 5. 明确结论

### 5.1 可以直接复用（许可证允许，且设计相对成熟）

| 可复用对象 | 许可证 | 复用方式 | 说明 |
|---|---|---|---|
| **国家标准/规范的字段与代码表**（3.1、3.2、3.3、3.7） | 政府规范性文件，不涉及软件许可 | **直接作为字段命名和代码表依据** | 最推荐。见 5.3 |
| Hugin-Z/tender-writer-v3 的 schema.md 字段清单和治理规则 | MIT | 可以直接拿来做字段清单和审核规则（保留 MIT 声明） | 它是 Markdown 规范，不是数据库 schema，要自己转成表 |
| HunterLzap/rag-tender 的 `Qualification` / `PerformanceProject` 模型 | MIT | 可以直接参考或拷贝 | 字段少，成熟度一般；资质表设计（发证机构、范围、等级、持证主体、计算状态）可以直接用 |
| zeronezer/bidcraft 的 `global_fact`、`knowledge_page`、文件 md5 去重模式 | Apache-2.0（须保留 NOTICE 并显著注明来源） | 可以复用模式 | 领域是工程施组，不含资质/人员 |
| Odoo hr_skills 的“技能类型 + is_certification + valid_from/valid_to” | LGPL-3.0 | 作为人员证书建模模式参考；**直接拷贝代码需遵守 LGPL** | 通用 ERP，设计成熟 |

### 5.2 只能参考思路（许可证限制、缺失，或成熟度不足）

| 对象 | 原因 |
|---|---|
| **FB208/OpenBidKit_Yibiao**（资质库 6 张表 + fieldKey 附件槽位） | **AGPL-3.0**：直接使用它的代码或 schema 文件，分发或以网络服务提供时须开源（是否触发由法务判断）。**字段设计是本次开源里最贴近政府采购实务的**，建议作为字段核对清单，自行重新建模 |
| **RudyJunyu/Bid_Agent** `DATABASE_SCHEMA_DESIGN.md` | **仓库没有 LICENSE**，默认保留全部权利；但它是最完整的“企业知识库层”设计文档，适合做对照 |
| guangshu100/BidMaster-Pro | AGPL-3.0，且没有结构化资料库；只能参考资质校验的 5 项规则 |
| Get00/BiaoShu-SKILL | 没有数据模型；只能参考行业章节配置 |
| ry-vue-flowable-xg | MIT 但成熟度低（作者自述“仅推荐用于学习”），合同表可以参考“甲乙方＋负责人” |
| shandianT/bid-dog | **专有许可证，禁止衍生**；只能了解“先抽取、再确认、后引用”的思路 |
| 钛投标 / 巧文书 / 智标枪 / 投标官 / 喜鹊 / 标书魔方 | 没有公开 schema；分类（尤其“产品、工器具、备品备件”“行业标准”）和治理（过期预警、证据标记、导出闸门）可以参考 |
| Loopio / Responsive | SaaS 帮助文档；**方案片段库的治理设计最成熟**（分层权限、Owner、复审周期、审核发布、新鲜度、变量、别名），建议照搬机制，不涉及代码 |

### 5.3 可作为字段命名依据的标准

| 实体 | 首选依据 | 可直接采用的英文名/代码 |
|---|---|---|
| 公司主体 | V2.0 14.1.1（兼容电子招投标技术规范 A.2.1） | LEGAL_NAME, LEGAL_CODE（GB 32100-2015，18 位）, LEGAL_REPRESENT, LEGAL_TYPE（表 108）, LEGAL_INDUSTRY（GB/T 4754）, REGION_CODE（GB/T 2260）, REG_CAPITAL/REG_CAP_CURRENCY/REG_UNIT, LICENSE_NO, LICENSE_END_DATE；主体类别用表 112 |
| 资质证书 | V2.0 14.1.4/14.1.7 + 双公示行政许可字段 | QUAL_NAME, QUAL_LEVEL（表 110）, QUAL_TYPE, QUAL_CERT_NO, QUAL_CERT_END_DATE；XK_YXQZ/XK_YXQZI/XK_XKJG/XK_ZT 可作为起始日期、发证机关、状态的命名参考 |
| 人员 | V2.0 14.2.5 + 技术规范 A.2.4 | ID_CARD_TYPE, ID_CARD, PERSON_NAME, UNIT_CODE, UNIT_NAME, WORK_START_DATE；性别 GB/T 2261.1；学历 GB/T 4658（技术规范引用） |
| 人员证书 | V2.0 14.2.6 + 技术规范 A.2.5 | QUAL_NAME, QUAL_TYPE, CERT_NO, CERT_END_DATE；另加“注册登记证书编号”（A.2.5） |
| 业绩合同 | 技术规范 A.2.7 + V2.0 7.5/8.1.5 | CONTRACT_NAME, CONTRACT_PRICE/CONTRACT_AMOUNT, PRICE_CURRENCY（GB/T 12406）, PRICE_UNIT, PRICE_FORM_CODE, WIN_BID_RATE, CONTRACT_SIGN_TIME, LIMITE_TIME/CONTRACT_TERM；结算金额、实际履行期限（A.2.7，没有英文名） |
| 附件文件 | V2.0 14.3 + 技术规范 B.3.7 | ATTACHMENT_SET_CODE, ATTACHMENT_NAME, ATTACHMENT_TYPE, ATTACHMENT_FILE_NAME, URL；附件用途码 LICENSE_CERT_DOC / QUAL_CART_DOC / ID_CARD_DOC / PROFESSIONAL_CART_DOC；关联标识 GUID |
| 项目/服务分类（跨实体标签） | 政府采购品目分类目录（2022）+ 技术规范 B.3.6 | C16070000 运行维护服务及其子类；A/B/C 大类（原文：技术规范中 A 工程、B 货物、C 服务；品目目录中 A 货物、B 工程、C 服务，**两套字母含义不同，不能混用**） |
| 证明材料类型 | 政府采购法实施条例第十七条 | 财务状况报告、纳税证明、社保证明、无重大违法记录声明等（材料名，不是字段） |
| 厂商产品 / 原厂授权 / SLA 模板 / 方案片段 | **没有可用的国家字段标准** | 自行设计；SLA 的过程要求可以引用 ITSS T/CESA 1299—2023 6.4.1 |

使用注意：
1. 这些标准是给交易平台做数据交换用的，英文名是全大写缩写。建议**库内列名自定、另建映射表对应标准英文名**，不要直接拿来做列名。
2. 资质序列码、执业资格类型码以建设工程为主，**IT 运维常用的资质和个人证书需要自建扩展码段**（V2.0 允许“自定义数据项 CUSTOM_DEFINITION_DATAITEM”，也可以用 99 其他）。
3. 2013 版技术规范的主体代码是 9 位组织机构代码，已过时，应以 V2.0 的 18 位统一社会信用代码为准。

---

## 6. 查不到或存疑的地方

1. **商业产品字段**：钛投标、巧文书、智标枪、投标官都没有公开字段级 schema；巧文书的资信库细节只来自厂商 V2EX 帖和第三方文章，官网只有概述。
2. **Loopio 帮助中心**：WebFetch 被 Cloudflare 拦截，改用 curl 读 Zendesk 公开 API 的同一篇文章。其余文章（Entry Owner、Library Review）只看到搜索摘要，没有读全文。
3. **Responsive** “Assigning owners and review cycles” 页面只返回了标题，内容没有读到；复审机制来自另一篇“Setting up scheduled review cycles”的全文。
4. **许可证不一致**：BidMaster-Pro（LICENSE 是 AGPL-3.0，README 写 MIT）、BiaoShu-SKILL（LICENSE 是 Apache-2.0，README 写 MIT）。本报告以 LICENSE 文件为准，**实际使用前请法务确认**。
5. **RudyJunyu/Bid_Agent 没有 LICENSE 文件**（依据：仓库 git tree 列表），不能复用。
6. **ITSS 评估中的人员持证数量或资质要求**：没有在官方原文中查到；GB/T 28827.1-2022、GB/T 29264-2012 全文是付费标准，没有读到。
7. **双公示“2026-02-24 新报送标准”**：只出现在搜索摘要里，没有找到原文，未采用。
8. **《企业资质序列行业和专业类别编码标准》**（V2.0 引用）原文没有取得，6 位资质码的具体码表未核实。
9. **公共资源交易平台数据规范 V3.0**：没有查到国家层面的新版；2024 年的地方标准（DB35/T 2167-2024、DB41/T 2685-2024）没有细读。
10. **若依证书管理项目（Gitee kai-yuan）**：没有读到 SQL，字段未知；**JeecgBoot 投标管理项目**：未查到。
11. 电子招投标技术规范附录 A 的表格读自第三方交易平台托管的 PDF（gov.cn 网页版没有显示表格），和 gov.cn 正文对照了条款编号，一致，但没有逐字比对表格内容。V2.0 正文读自湖南省发改委转载的 PDF。
12. `sirchinj/BidMaster-Pro` 与 `guangshu100/BidMaster-Pro` 描述相同，二者关系未核实。

---

## 附：本次实际读取的源码/原文文件（便于复核）

- Yibiao：`client/src/features/credential-library/types.ts`、`client/electron/services/credentialLibraryService.cjs`、`client/src/features/knowledge-base/types.ts`
- BidMaster-Pro：`db/init_pg.sql`、`services/models.py`、`services/routers/knowledge.py`、`services/check/skills/qualification_check_skill.py`
- tender-writer-v3：`assets/README.md`、`assets/*/…schema.md`（5 份）、`references/knowledge_base/历史标书案例/案例schema.md`、`companies.yaml`、`references/asset_type_mapping.yaml`、CSV 表头
- BiaoShu-SKILL：`SKILL.md`、`references/industry_configs.json`、`scripts/bid_writer_pipeline.py`
- bidcraft：`scripts/init_db.sql`、NOTICE、ATTRIBUTION.md
- bid-dog：LICENSE、NOTICE、`app-next/src/views/AssetsSheet.jsx`、`FactsPanel.jsx`、`docs/中标狗产品介绍.md`
- Bid_Agent：`DATABASE_SCHEMA_DESIGN.md`；rag-tender：`backend/app/models/knowledge.py`、`performance.py`、LICENSE
- ry-vue-flowable-xg：`script/sql/mysql/ry-vue-flowable-xg.sql`、LICENSE；Odoo 19：`addons/hr_skills/models/*.py`、LICENSE
- 标准：技术规范第 1 部分 PDF（附录 A.2）、V2.0 PDF（第 7.5、8.1.5、14 章）、双公示标准 PDF、T/CESA 1299—2023 PDF、政府采购品目分类目录 PDF
