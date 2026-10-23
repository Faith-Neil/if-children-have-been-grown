// 为什么有这个文件：落实 FE-WRITING-ARCHIVE 写作档案与风格规范纯业务逻辑（PRD v1.8 §5.6、§5.8.7、R35/R43）。
// 它解决什么问题：
// 1. 公司写作档案多租户强隔离（Alpha vs Beta 独立自称口径、风格倾向、禁用词表与样章库）；
// 2. 语气风格偏好、自称/招标人统称、总结句控制策略配置；
// 3. 禁用词库（夸大词、采购人口吻、行业套话）检索与严重级别判定；
// 4. 国家公文与投标排版规范（标点全角半角、法定计量单位、标题编号格式）；
// 5. 标杆优质样章库（few-shot 结构范本、字数、维度与正文查阅）；
// 6. 草稿正文实时合规扫描纯函数（违规词捕获与自称错用诊断）。

import type {
  CompanyWritingProfile,
  ForbiddenWord,
  ForbiddenWordCategory,
  ForbiddenWordSeverity,
  QualitySample,
  TypographyRule,
  Volume,
} from '../shared/types.ts';

export type {
  CompanyWritingProfile,
  ForbiddenWord,
  ForbiddenWordCategory,
  ForbiddenWordSeverity,
  QualitySample,
  TypographyRule,
  Volume,
};

export interface ForbiddenWordFilterParams {
  search?: string;
  category?: string;
  severity?: string;
}

export interface QualitySampleFilterParams {
  search?: string;
  volume?: string;
  scoring_dimension?: string;
}

export interface ForbiddenWordHit {
  word: string;
  category: ForbiddenWordCategory;
  severity: ForbiddenWordSeverity;
  reason: string;
  suggestion: string;
  startIndex: number;
  endIndex: number;
}

export interface DraftScanResult {
  valid: boolean;
  totalWordCount: number;
  forbiddenHits: ForbiddenWordHit[];
  selfReferenceMismatches: string[];
  summary: {
    blockerCount: number;
    warningCount: number;
    suggestionCount: number;
  };
}

/**
 * 禁用词类别中文标签映射
 */
export const FORBIDDEN_CATEGORY_MAP: Record<string, string> = {
  all: '全部类别',
  exaggeration: '夸大与绝对化词',
  buyer_tone: '采购人口吻误用',
  competitor: '第三方与竞对代称',
  cliche: '空泛行业套话',
};

export function getForbiddenCategoryLabel(cat?: string | null): string {
  if (!cat) return '通用词汇';
  return FORBIDDEN_CATEGORY_MAP[cat] || cat;
}

/**
 * 违规级别元数据与配色
 */
export function getSeverityMeta(severity?: ForbiddenWordSeverity | null): {
  label: string;
  color: string;
  badgeStatus: 'error' | 'warning' | 'processing' | 'default';
} {
  switch (severity) {
    case 'blocker':
      return { label: '强阻断', color: 'red', badgeStatus: 'error' };
    case 'warning':
      return { label: '合规警告', color: 'gold', badgeStatus: 'warning' };
    case 'suggestion':
      return { label: '润色建议', color: 'blue', badgeStatus: 'processing' };
    default:
      return { label: severity || '提示', color: 'default', badgeStatus: 'default' };
  }
}

/**
 * 分册中文名称
 */
export function getVolumeLabel(volume?: Volume | string | null): string {
  if (volume === 'technical') return '技术分册';
  if (volume === 'business') return '商务分册';
  return '通用分册';
}

/**
 * 多维过滤禁用词库
 */
export function filterForbiddenWords(
  words: ForbiddenWord[] | undefined | null,
  params: ForbiddenWordFilterParams = {}
): ForbiddenWord[] {
  if (!Array.isArray(words)) return [];

  return words.filter(item => {
    // 类别筛选
    if (params.category && params.category !== 'all' && item.category !== params.category) {
      return false;
    }

    // 严重级别筛选
    if (params.severity && params.severity !== 'all' && item.severity !== params.severity) {
      return false;
    }

    // 关键字搜索
    if (params.search && params.search.trim()) {
      const kw = params.search.trim().toLowerCase();
      const word = item.word.toLowerCase();
      const reason = item.reason.toLowerCase();
      const suggestion = item.replacement_suggestion.toLowerCase();
      const categoryLabel = getForbiddenCategoryLabel(item.category).toLowerCase();

      const matched =
        word.includes(kw) ||
        reason.includes(kw) ||
        suggestion.includes(kw) ||
        categoryLabel.includes(kw);

      if (!matched) return false;
    }

    return true;
  });
}

/**
 * 多维过滤标杆优质样章
 */
export function filterQualitySamples(
  samples: QualitySample[] | undefined | null,
  params: QualitySampleFilterParams = {}
): QualitySample[] {
  if (!Array.isArray(samples)) return [];

  return samples.filter(item => {
    // 分册筛选
    if (params.volume && params.volume !== 'all' && item.volume !== params.volume) {
      return false;
    }

    // 评分维度筛选
    if (
      params.scoring_dimension &&
      params.scoring_dimension !== 'all' &&
      item.scoring_dimension !== params.scoring_dimension
    ) {
      return false;
    }

    // 关键字搜索
    if (params.search && params.search.trim()) {
      const kw = params.search.trim().toLowerCase();
      const title = item.title.toLowerCase();
      const chapter = item.chapter_name.toLowerCase();
      const dimension = item.scoring_dimension.toLowerCase();
      const tags = item.tags.join(' ').toLowerCase();
      const excerpt = item.excerpt.toLowerCase();

      const matched =
        title.includes(kw) ||
        chapter.includes(kw) ||
        dimension.includes(kw) ||
        tags.includes(kw) ||
        excerpt.includes(kw);

      if (!matched) return false;
    }

    return true;
  });
}

/**
 * 文本草稿合规快速扫描诊断
 * 检查禁用词命中、采购人口吻反常自称
 */
export function scanDraftText(
  text: string | undefined | null,
  profile: CompanyWritingProfile
): DraftScanResult {
  const content = text || '';
  const totalWordCount = content.replace(/\s+/g, '').length;
  const forbiddenHits: ForbiddenWordHit[] = [];
  const selfReferenceMismatches: string[] = [];

  let blockerCount = 0;
  let warningCount = 0;
  let suggestionCount = 0;

  if (content.trim()) {
    // 1. 扫描禁用词
    for (const fw of profile.forbidden_words || []) {
      const escaped = fw.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(escaped, 'gi');
      let match: RegExpExecArray | null;

      while ((match = regex.exec(content)) !== null) {
        forbiddenHits.push({
          word: fw.word,
          category: fw.category,
          severity: fw.severity,
          reason: fw.reason,
          suggestion: fw.replacement_suggestion,
          startIndex: match.index,
          endIndex: match.index + fw.word.length,
        });

        if (fw.severity === 'blocker') blockerCount += 1;
        else if (fw.severity === 'warning') warningCount += 1;
        else suggestionCount += 1;
      }
    }

    // 2. 自称一致性检查（R35：自称须等于写作档案设定，不得错用采购人口吻或异称）
    const buyerTones = ['我行', '我局', '我院', '我司', '我部', '贵公司'];
    for (const bt of buyerTones) {
      if (bt !== profile.self_reference && content.includes(bt)) {
        if (!selfReferenceMismatches.includes(bt)) {
          selfReferenceMismatches.push(bt);
        }
      }
    }
  }

  // 排序命中结果
  forbiddenHits.sort((a, b) => a.startIndex - b.startIndex);

  return {
    valid: blockerCount === 0 && selfReferenceMismatches.length === 0,
    totalWordCount,
    forbiddenHits,
    selfReferenceMismatches,
    summary: {
      blockerCount,
      warningCount,
      suggestionCount,
    },
  };
}

/**
 * 获取指定租户公司的写作档案配置（严格租户隔离）
 */
export function getWritingProfile(companyId?: string | null): CompanyWritingProfile {
  const targetId = companyId && companyId.trim() ? companyId.trim() : 'alpha';
  const found = DEFAULT_COMPANY_WRITING_PROFILES[targetId];

  if (found) {
    return JSON.parse(JSON.stringify(found)) as CompanyWritingProfile;
  }

  // 兜底隔离租户通用档案
  return {
    company_id: targetId,
    company_name: `${targetId.toUpperCase()} 科技实业有限公司`,
    self_reference: '本投标人',
    tenderer_reference: '招标人',
    tone_preference: '客观严谨、文字精炼、契合标书格式规范',
    summary_sentence_strategy: '允许章节末段进行总结，正文段落禁止堆砌总结套话。',
    style_token_budget: 1200,
    typography_rules: DEFAULT_TYPOGRAPHY_RULES,
    forbidden_words: DEFAULT_COMMON_FORBIDDEN_WORDS,
    quality_samples: [],
  };
}

/**
 * 默认排版格式规范清单
 */
export const DEFAULT_TYPOGRAPHY_RULES: TypographyRule[] = [
  {
    id: 'typo-01',
    category: '标点规范',
    rule_name: '中文标点统一使用全角字符',
    standard: '中文正文段落中逗号（，）、句号（。）、顿号（、）、冒号（：）、分号（；）及书名号必须使用全角标点，严禁出现半角逗号“,”或半角句点“.”。',
    bad_case: '系统部署在机房,具备双活冗余.支持随时切换.',
    good_case: '系统部署在机房，具备双活冗余。支持随时切换。',
  },
  {
    id: 'typo-02',
    category: '字符规范',
    rule_name: '英文字母与数字统一使用半角字符',
    standard: '版本号、技术参数、IP 地址与时间数字必须使用半角西文字符，严禁使用全角数字“１２３”或全角字母“ＡＢＣ”。',
    bad_case: '系统支持　１００００　并发，响应时间小于　５０ｍｓ。',
    good_case: '系统支持 10000 并发，响应时间小于 50ms。',
  },
  {
    id: 'typo-03',
    category: '度量规范',
    rule_name: '法定计量单位与间隔标准',
    standard: '严格使用国家法定计量单位（如 km, m, mm, kg, s, h, ms, ℃, %），数值与字母单位之间保留半角空格（百分号除外），严禁使用口语化单位“度”、“里”、“斤”。',
    bad_case: '机房温度25度，网络延迟50毫秒。',
    good_case: '机房温度 25 ℃，网络延迟 50 ms。',
  },
  {
    id: 'typo-04',
    category: '层级规范',
    rule_name: '章节标题序号与国家公文格式对齐',
    standard: '正文章节标题严格采用“一、”、“（一）”、“1.”、“(1)”、“①”的五级层级顺序递进，编号后标点使用规范，严禁跳级混用。',
    bad_case: '第一章 架构 -> 1.1 节点 -> 一、实施',
    good_case: '一、系统架构设计 -> （一）核心节点配置 -> 1. 冗余方案',
  },
  {
    id: 'typo-05',
    category: '句式规范',
    rule_name: '限制连续对比与关联词排比滥用',
    standard: '同一自然段内严禁出现多于 1 次“不是……而是……”否定对比句式；同一技术说明中排比句不超过 3 组，避免明显的机器生成腔调（R43 规则）。',
    bad_case: '不仅提升了效能，而且降低了成本，更是重塑了生态。不是简单的叠加，而是深度的融合。',
    good_case: '方案通过模块化整合优化计算架构，有效缩减通信开销并达成 30% 效能提升。',
  },
  {
    id: 'typo-06',
    category: '变量规范',
    rule_name: '参数注入变量双大括号标注',
    standard: '方案片段中需在生成时动态绑定的工程参数，必须严格使用 {{variable_name}} 进行双大括号封装，变量名限英文字母、数字、下划线及减号。',
    bad_case: '承诺到场时间为 {response_hours} 小时，冗余度达到 99.9%（固定承诺）。',
    good_case: '承诺到场时间为 {{response_hours}} 小时，整体系统可用度达到 {{sla_percent}}%。',
  },
];

/**
 * 默认通用禁用词清单
 */
export const DEFAULT_COMMON_FORBIDDEN_WORDS: ForbiddenWord[] = [
  {
    id: 'fw-01',
    word: '业界第一',
    category: 'exaggeration',
    severity: 'blocker',
    replacement_suggestion: '处于行业领先地位 / 具有突出技术优势',
    reason: '违反《中华人民共和国反不正当竞争法》与广告法绝对化用语，无独立第三方权威机构法定评级佐证。',
  },
  {
    id: 'fw-02',
    word: '绝对保证',
    category: 'exaggeration',
    severity: 'blocker',
    replacement_suggestion: '全力保障 / 提供完备保障措施',
    reason: '构成不可撤销的无限连带绝对法律承诺，未界定不可抗力等免责边界。',
  },
  {
    id: 'fw-03',
    word: '零缺陷',
    category: 'exaggeration',
    severity: 'blocker',
    replacement_suggestion: '高标准交付质量 / 缺陷密度受控于万分之三以下',
    reason: '软件与系统集成工程学上不可实现的绝对指标承诺，极易引发后期实质履约争议。',
  },
  {
    id: 'fw-04',
    word: '独家首创',
    category: 'exaggeration',
    severity: 'warning',
    replacement_suggestion: '自主研发创新成果 / 具有自主知识产权',
    reason: '易引发排他性倾向争议与竞争对手复核质疑。',
  },
  {
    id: 'fw-05',
    word: '我行',
    category: 'buyer_tone',
    severity: 'blocker',
    replacement_suggestion: '本投标人 / 贵行',
    reason: '错用金融采购方口吻自称，主体角色严重混淆（R35 核心审查点）。',
  },
  {
    id: 'fw-06',
    word: '我局',
    category: 'buyer_tone',
    severity: 'blocker',
    replacement_suggestion: '本投标人 / 贵局',
    reason: '错用政务机关采购方口吻自称，违背招投标基本公文规范。',
  },
  {
    id: 'fw-07',
    word: '我院',
    category: 'buyer_tone',
    severity: 'blocker',
    replacement_suggestion: '本投标人 / 贵院',
    reason: '错用科研/医疗采购人自称口吻。',
  },
  {
    id: 'fw-08',
    word: '保姆式',
    category: 'cliche',
    severity: 'suggestion',
    replacement_suggestion: '全周期专属运维保障 / 敏捷管家式技术服务',
    reason: '非规范工程口语化俗语，降低投标文件专业严肃性。',
  },
  {
    id: 'fw-09',
    word: '全方位无死角',
    category: 'cliche',
    severity: 'warning',
    replacement_suggestion: '全流程覆盖 / 涵盖全链路监测指标',
    reason: '典型空泛套话，缺乏度量指标与事实依据（R43 套话密度审查）。',
  },
  {
    id: 'fw-10',
    word: '颠覆性',
    category: 'cliche',
    severity: 'suggestion',
    replacement_suggestion: '突破性优化 / 显著效能提升',
    reason: '缺乏可证实度量数据的空泛形容词。',
  },
];

/**
 * 平台预置租户档案集合（Alpha 与 Beta 双租户隔离）
 */
export const DEFAULT_COMPANY_WRITING_PROFILES: Record<string, CompanyWritingProfile> = {
  alpha: {
    company_id: 'alpha',
    company_name: '阿尔法智能科技有限公司',
    self_reference: '本投标人',
    tenderer_reference: '招标人',
    tone_preference: '客观严谨、技术专业、数据详实、承诺量化',
    summary_sentence_strategy: '允许章节首段引入与末段归纳，中间核心技术阐述段落严禁连篇堆砌“综上所述”、“显而易见”。',
    style_token_budget: 1500,
    typography_rules: DEFAULT_TYPOGRAPHY_RULES,
    forbidden_words: DEFAULT_COMMON_FORBIDDEN_WORDS,
    quality_samples: [
      {
        id: 'sample-alpha-001',
        title: '智慧应急多维感知与异构双活容灾方案',
        volume: 'technical',
        chapter_name: '第三章 总体技术方案与高可用架构设计',
        scoring_dimension: '技术先进性与可行性',
        word_count: 1460,
        tags: ['双活架构', '技术方案', '高可用'],
        excerpt: '本系统基于微服务云原生架构设计，采用跨机房同城双活部署模式。各核心业务单元均以多活容器集群部署，底层数据库配置半同步复制集群与自愈选主套件，确保 RTO ≤ 5 min，RPO ≤ 1 min。',
        full_content: `一、系统总体高可用部署设计
本投标人针对智慧应急业务高并发、全天候不间断监测的严苛要求，在总体架构上全面贯彻“分区自治、跨域多活、快速切换、数据零丢”的设计原则。

（一）计算集群与负载均衡
1. 采用四层与七层硬件负载均衡双机热备架构，前端由两组硬件 F5 负载设备实施 Keepalived 心跳检测与会话漂移，最大处理吞吐量达到 40 Gbps。
2. 业务应用部署于 Kubernetes 容器集群，主备机房节点规模不低于 16 台物理服务器，全站服务基于无状态设计，通过双向流量调度网关达成秒级无感负载均衡。

（二）数据库容灾与存储镜像
1. 核心业务持久层部署 MySQL 8.0 Group Replication（MGR）高可用集群，单集群配置 5 节点跨同城双机房容灾部署。
2. 存储网络采用全光纤 FC-SAN 存储双活网关，实现块级数据毫秒级底层同步镜像，关键配置变更严格记录系统审计追溯日志。`,
        revision: 2,
        updated_at: '2026-10-22T14:30:00Z',
      },
      {
        id: 'sample-alpha-002',
        title: '物联网大数据中台流批一体化实施保障方案',
        volume: 'technical',
        chapter_name: '第四章 数据汇聚与流式计算实施保障',
        scoring_dimension: '项目实施与进度保障',
        word_count: 1680,
        tags: ['数据中台', '流式计算', '实施组织'],
        excerpt: '方案采用成熟的 Apache Flink 与 Kafka 架构实现设备遥测数据的高通量毫秒级解析与入库。结合自研动态分区压缩技术，支撑每秒 50000 笔事件接入，存储压缩比达 4:1。',
        full_content: `一、流批一体数据管道架构
本投标人在数据中台建设中，引入成熟稳定的流批一体化数据计算体系，全面保障全量传感器遥测数据采集的时效性与准确性。

（一）数据高通量接入层
1. 接入集群由 8 台高性能计算节点构成，采用多分区 Kafka 消息队列进行流量削峰与缓冲，设计峰值缓冲能力达 100000 QPS。
2. 数据格式解析引擎基于内存零拷贝反序列化，端到端入库延迟严格控制在 50 ms 范围内。

（二）冷热数据分层归档
1. 7 天内热数据常驻全闪分布式缓存存储，提供近实时高并发报表查询与多维下钻分析。
2. 历史冷数据定期沉降至列式压缩存储集群，标准归档周期为 365 天，满足全生命周期可追溯合规要求。`,
        revision: 1,
        updated_at: '2026-10-21T18:20:00Z',
      },
      {
        id: 'sample-alpha-003',
        title: '7×24小时专属技术维保与快速响应SLA服务承诺',
        volume: 'business',
        chapter_name: '第五章 售后技术支持与维保服务承诺',
        scoring_dimension: '售后服务体系与SLA承诺',
        word_count: 980,
        tags: ['商务服务', 'SLA承诺', '应急抢修'],
        excerpt: '在项目运维质保期内，本投标人承诺设立 7×24 小时专属运维保障团队。一级紧急事件保证 15 分钟内响应，2 小时内技术骨干到达现场排障，确保系统全年可用率达到 99.95%。',
        full_content: `一、维保响应等级与承诺标准
本投标人设立针对本招标项目的专项运维保障专家组，提供全年全天候不间断技术支持服务。

（一）事件分级与响应时效
1. 一级紧急故障（系统主干服务中断或大面积遥测失效）：15 分钟内远程响应并组建专家专班，2 小时内专家到达采购单位指定现场进行应急抢修。
2. 二级重要事件（部分次级功能受阻但不影响核心运转）：30 分钟内远程响应，4 小时内提供明确修复补丁方案。
3. 三级普通事件：1 小时内响应，24 小时内闭环排障。

（二）年度可用率量化保障
本投标人承诺系统年度综合可用率达 99.95% 以上，因我方软硬件设计或维护失误导致服务停运的，按双方商务合同违约条款执行补偿。`,
        revision: 3,
        updated_at: '2026-10-20T11:15:00Z',
      },
    ],
  },
  beta: {
    company_id: 'beta',
    company_name: '贝塔建设工程系统集成有限公司',
    self_reference: '我方',
    tenderer_reference: '业主单位',
    tone_preference: '工法严密、安全优先、质量为本、务实求效',
    summary_sentence_strategy: '分项工程施工组织紧密对标国家现行规范与图集，末段归纳质量自检与隐蔽验收核心控制点。',
    style_token_budget: 1200,
    typography_rules: DEFAULT_TYPOGRAPHY_RULES,
    forbidden_words: [
      {
        id: 'fw-b-01',
        word: '百分之百无渗漏',
        category: 'exaggeration',
        severity: 'blocker',
        replacement_suggestion: '严格满足国家《地下防水工程质量验收规范》一级防水标准',
        reason: '绝对化不当宣传，属于施工工程履约高风险承诺。',
      },
      {
        id: 'fw-b-02',
        word: '绝对工期无延误',
        category: 'exaggeration',
        severity: 'blocker',
        replacement_suggestion: '落实三级网络进度管控体系，确保关键节点按期履约',
        reason: '未考虑恶劣气象、设计变更与不可抗力因素的无限连带责任。',
      },
      ...DEFAULT_COMMON_FORBIDDEN_WORDS.filter(w => w.category === 'buyer_tone'),
    ],
    quality_samples: [
      {
        id: 'sample-beta-001',
        title: '机电综合管线深化设计与三维BIM防碰撞施工方案',
        volume: 'technical',
        chapter_name: '第二章 机电安装综合工法与深化排布',
        scoring_dimension: '施工工法先进性与质量保证',
        word_count: 1320,
        tags: ['机电安装', 'BIM深化', '工法规范'],
        excerpt: '我方在施工全过程深度采用 BIM 三维数字化协同技术，针对强弱电桥架、通风管道与消防喷淋系统开展碰撞检查，将安装标高冲突清零于施工进场前。',
        full_content: `一、机电综合深化技术路线
我方在本项目机电设备安装工程中，全面实行“模型先行、碰撞预警、装配预制、一次成优”的精细化工法。

（一）全专业协同建模
1. 依据业主单位下发的设计施工图纸，采用 Revit 平台建立结构、暖通、给排水、电气专业的高精度三维实体模型（LOD 350）。
2. 重点复核走廊主干管线密集区、设备机房及竖井交汇处净高，确保吊顶完成面高度满足招标文件使用要求。`,
        revision: 1,
        updated_at: '2026-10-21T15:00:00Z',
      },
    ],
  },
};
