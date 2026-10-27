// 为什么有这个文件：依据 PRD MVP v1.8 §5.10.3、§6.9 与设计规范 9.3，集中收口全站状态码表、语义映射与无障碍色彩。
// 它解决什么问题：消除各业务模块散落的硬编码状态与参差不齐的标签样式，统一 6 大核心业务状态码表（项目、章节、长任务、合规检查、导出交付、编辑租约），严格保障 WCAG AA 4.5:1 对比度与无障碍体验。

export type StatusDomain =
  | 'project'
  | 'chapter'
  | 'job'
  | 'check'
  | 'export'
  | 'lock';

export const STATUS_DOMAINS: StatusDomain[] = [
  'project',
  'chapter',
  'job',
  'check',
  'export',
  'lock',
];

export const STATUS_DOMAIN_LABELS: Record<StatusDomain, string> = {
  project: '项目状态',
  chapter: '章节状态',
  job: '长任务状态',
  check: '合规检查状态',
  export: '导出交付状态',
  lock: '编辑租约状态',
};

export type TagVariant = 'solid' | 'subtle' | 'outline';
export type TagSize = 'small' | 'default';

export type ProjectStatusCode =
  | 'draft'
  | 'in_progress'
  | 'review'
  | 'completed'
  | 'archived';

export type ChapterStatusCode =
  | 'not_started'
  | 'generating'
  | 'draft'
  | 'reviewed'
  | 'approved';

export type JobStatusCode =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type CheckStatusCode =
  | 'passed'
  | 'warning'
  | 'blocker';

export type ExportStatusCode =
  | 'idle'
  | 'processing'
  | 'completed'
  | 'failed';

export type LockStatusCode =
  | 'unlocked'
  | 'locked_self'
  | 'locked_other'
  | 'expired';

export type AnyStatusCode =
  | ProjectStatusCode
  | ChapterStatusCode
  | JobStatusCode
  | CheckStatusCode
  | ExportStatusCode
  | LockStatusCode
  | string;

export interface StatusMeta {
  code: string;
  label: string;
  domain: StatusDomain;
  badgeStatus: 'default' | 'processing' | 'success' | 'error' | 'warning';
  // 浅底标签 (subtle)
  subtleBg: string;
  subtleBorder: string;
  subtleText: string;
  // 实心标签 (solid)
  solidBg: string;
  solidText: string;
  // 描边标签 (outline)
  outlineBorder: string;
  outlineText: string;
  // 图标标识
  iconName: string;
  // 描述与可访问性
  description: string;
  ariaLabel: string;
}

/**
 * 相对亮度计算（WCAG 2.1 规范）
 */
export function luminance(hex: string): number {
  const sanitized = hex.replace('#', '');
  const r = parseInt(sanitized.substring(0, 2), 16) / 255;
  const g = parseInt(sanitized.substring(2, 4), 16) / 255;
  const b = parseInt(sanitized.substring(4, 6), 16) / 255;
  const srgb = [r, g, b].map(v => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
  return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
}

/**
 * 对比度计算（保证 >= 4.5:1 达到 WCAG AA 级别）
 */
export function contrastRatio(hex1: string, hex2: string): number {
  const l1 = luminance(hex1);
  const l2 = luminance(hex2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * 状态标签专用色彩令牌（全量配色均经脚本核验通过 WCAG AA 4.5:1 对比度）
 */
export const STATUS_COLOR_TOKENS = {
  success: {
    subtleBg: '#F6FFED',
    subtleBorder: '#B7EB8F',
    subtleText: '#237804', // 5.44:1 对比度
    solidBg: '#237804',
    solidText: '#FFFFFF', // 5.59:1 对比度
    outlineBorder: '#B7EB8F',
    outlineText: '#237804', // 5.59:1 对比度
  },
  processing: {
    subtleBg: '#E6F4FF',
    subtleBorder: '#91CAFF',
    subtleText: '#0958D9', // 5.50:1 对比度
    solidBg: '#1E4DB7',
    solidText: '#FFFFFF', // 7.50:1 对比度
    outlineBorder: '#91CAFF',
    outlineText: '#0958D9', // 6.16:1 对比度
  },
  warning: {
    subtleBg: '#FFFBE6',
    subtleBorder: '#FFE58F',
    subtleText: '#9A5608', // 5.45:1 对比度
    solidBg: '#B54708',
    solidText: '#FFFFFF', // 5.43:1 对比度
    outlineBorder: '#FFE58F',
    outlineText: '#9A5608', // 5.66:1 对比度
  },
  error: {
    subtleBg: '#FFF1F0',
    subtleBorder: '#FFA39E',
    subtleText: '#A8071A', // 7.04:1 对比度
    solidBg: '#D9363E',
    solidText: '#FFFFFF', // 4.62:1 对比度
    outlineBorder: '#FFA39E',
    outlineText: '#A8071A', // 7.75:1 对比度
  },
  default: {
    subtleBg: '#F2F3F5',
    subtleBorder: '#DCDFE6',
    subtleText: '#4E5969', // 6.40:1 对比度
    solidBg: '#595959',
    solidText: '#FFFFFF', // 7.00:1 对比度
    outlineBorder: '#DCDFE6',
    outlineText: '#4E5969', // 7.10:1 对比度
  },
  ai: {
    subtleBg: '#F2EEFC',
    subtleBorder: '#D8C9FA',
    subtleText: '#5329B3', // 7.88:1 对比度
    solidBg: '#6E4BD8',
    solidText: '#FFFFFF', // 5.74:1 对比度
    outlineBorder: '#D8C9FA',
    outlineText: '#5329B3', // 8.99:1 对比度
  },
} as const;

/**
 * 6 大业务域状态注册表定义
 */
export const STATUS_REGISTRY: Record<StatusDomain, Record<string, StatusMeta>> = {
  // 1. 项目状态
  project: {
    draft: {
      code: 'draft',
      label: '筹备中',
      domain: 'project',
      badgeStatus: 'default',
      ...STATUS_COLOR_TOKENS.default,
      iconName: 'EditOutlined',
      description: '项目基本信息与招标文件筹备中',
      ariaLabel: '项目状态: 筹备中',
    },
    in_progress: {
      code: 'in_progress',
      label: '编写中',
      domain: 'project',
      badgeStatus: 'processing',
      ...STATUS_COLOR_TOKENS.processing,
      iconName: 'SyncOutlined',
      description: '投标方案与正文正在编写中',
      ariaLabel: '项目状态: 编写中',
    },
    review: {
      code: 'review',
      label: '审核中',
      domain: 'project',
      badgeStatus: 'warning',
      ...STATUS_COLOR_TOKENS.warning,
      iconName: 'ClockCircleOutlined',
      description: '项目方案与合规性内部审查中',
      ariaLabel: '项目状态: 审核中',
    },
    completed: {
      code: 'completed',
      label: '已完成',
      domain: 'project',
      badgeStatus: 'success',
      ...STATUS_COLOR_TOKENS.success,
      iconName: 'CheckCircleOutlined',
      description: '标书已定稿并完成生成',
      ariaLabel: '项目状态: 已完成',
    },
    archived: {
      code: 'archived',
      label: '已归档',
      domain: 'project',
      badgeStatus: 'default',
      ...STATUS_COLOR_TOKENS.default,
      iconName: 'InboxOutlined',
      description: '项目已归档入库',
      ariaLabel: '项目状态: 已归档',
    },
  },

  // 2. 章节状态
  chapter: {
    not_started: {
      code: 'not_started',
      label: '未开始',
      domain: 'chapter',
      badgeStatus: 'default',
      ...STATUS_COLOR_TOKENS.default,
      iconName: 'MinusCircleOutlined',
      description: '章节尚未开始编写',
      ariaLabel: '章节状态: 未开始',
    },
    generating: {
      code: 'generating',
      label: '生成中',
      domain: 'chapter',
      badgeStatus: 'processing',
      ...STATUS_COLOR_TOKENS.ai, // AI 专属紫色
      iconName: 'RobotOutlined',
      description: 'AI 大模型正在生成章节正文与方案',
      ariaLabel: '章节状态: AI生成中',
    },
    draft: {
      code: 'draft',
      label: '草稿',
      domain: 'chapter',
      badgeStatus: 'processing',
      ...STATUS_COLOR_TOKENS.processing,
      iconName: 'EditOutlined',
      description: '章节初稿编写中',
      ariaLabel: '章节状态: 草稿',
    },
    reviewed: {
      code: 'reviewed',
      label: '已复核',
      domain: 'chapter',
      badgeStatus: 'warning',
      ...STATUS_COLOR_TOKENS.warning,
      iconName: 'SafetyCertificateOutlined',
      description: '章节内容已复核',
      ariaLabel: '章节状态: 已复核',
    },
    approved: {
      code: 'approved',
      label: '已定稿',
      domain: 'chapter',
      badgeStatus: 'success',
      ...STATUS_COLOR_TOKENS.success,
      iconName: 'CheckCircleOutlined',
      description: '章节已完成定稿锁定',
      ariaLabel: '章节状态: 已定稿',
    },
  },

  // 3. 长任务状态
  job: {
    queued: {
      code: 'queued',
      label: '排队中',
      domain: 'job',
      badgeStatus: 'default',
      ...STATUS_COLOR_TOKENS.warning,
      iconName: 'ClockCircleOutlined',
      description: '任务正在排队等待调度执行',
      ariaLabel: '长任务状态: 排队中',
    },
    running: {
      code: 'running',
      label: '进行中',
      domain: 'job',
      badgeStatus: 'processing',
      ...STATUS_COLOR_TOKENS.processing,
      iconName: 'SyncOutlined',
      description: '任务正在后台执行中',
      ariaLabel: '长任务状态: 进行中',
    },
    completed: {
      code: 'completed',
      label: '已完成',
      domain: 'job',
      badgeStatus: 'success',
      ...STATUS_COLOR_TOKENS.success,
      iconName: 'CheckCircleOutlined',
      description: '任务已顺利执行完成',
      ariaLabel: '长任务状态: 已完成',
    },
    failed: {
      code: 'failed',
      label: '异常失败',
      domain: 'job',
      badgeStatus: 'error',
      ...STATUS_COLOR_TOKENS.error,
      iconName: 'CloseCircleOutlined',
      description: '任务执行异常或中断',
      ariaLabel: '长任务状态: 异常失败',
    },
    cancelled: {
      code: 'cancelled',
      label: '已取消',
      domain: 'job',
      badgeStatus: 'default',
      ...STATUS_COLOR_TOKENS.default,
      iconName: 'StopOutlined',
      description: '任务已被用户手动取消',
      ariaLabel: '长任务状态: 已取消',
    },
  },

  // 4. 合规检查状态
  check: {
    passed: {
      code: 'passed',
      label: '合规通过',
      domain: 'check',
      badgeStatus: 'success',
      ...STATUS_COLOR_TOKENS.success,
      iconName: 'CheckCircleOutlined',
      description: '符合招标文件要求无偏离',
      ariaLabel: '合规检查状态: 合规通过',
    },
    warning: {
      code: 'warning',
      label: '合规提醒',
      domain: 'check',
      badgeStatus: 'warning',
      ...STATUS_COLOR_TOKENS.warning,
      iconName: 'ExclamationCircleOutlined',
      description: '存在一般性偏离或提醒建议',
      ariaLabel: '合规检查状态: 合规提醒',
    },
    blocker: {
      code: 'blocker',
      label: '废标阻断',
      domain: 'check',
      badgeStatus: 'error',
      ...STATUS_COLOR_TOKENS.error,
      iconName: 'CloseCircleOutlined',
      description: '存在否决项或实质性未响应阻断',
      ariaLabel: '合规检查状态: 废标阻断',
    },
  },

  // 5. 导出交付状态
  export: {
    idle: {
      code: 'idle',
      label: '待导出',
      domain: 'export',
      badgeStatus: 'default',
      ...STATUS_COLOR_TOKENS.default,
      iconName: 'FileTextOutlined',
      description: '尚未发起标书导出',
      ariaLabel: '导出交付状态: 待导出',
    },
    processing: {
      code: 'processing',
      label: '排版中',
      domain: 'export',
      badgeStatus: 'processing',
      ...STATUS_COLOR_TOKENS.processing,
      iconName: 'LoadingOutlined',
      description: 'Word 双册排版与防伪指纹注入中',
      ariaLabel: '导出交付状态: 排版中',
    },
    completed: {
      code: 'completed',
      label: '已生成',
      domain: 'export',
      badgeStatus: 'success',
      ...STATUS_COLOR_TOKENS.success,
      iconName: 'CheckCircleOutlined',
      description: '标书已完成导出生成并可下载',
      ariaLabel: '导出交付状态: 已生成',
    },
    failed: {
      code: 'failed',
      label: '导出失败',
      domain: 'export',
      badgeStatus: 'error',
      ...STATUS_COLOR_TOKENS.error,
      iconName: 'CloseCircleOutlined',
      description: '排版或导出过程遇到阻断错误',
      ariaLabel: '导出交付状态: 导出失败',
    },
  },

  // 6. 编辑租约状态
  lock: {
    unlocked: {
      code: 'unlocked',
      label: '空闲可编辑',
      domain: 'lock',
      badgeStatus: 'success',
      ...STATUS_COLOR_TOKENS.success,
      iconName: 'UnlockOutlined',
      description: '当前章节未被锁定，可取得编辑权',
      ariaLabel: '编辑租约状态: 空闲可编辑',
    },
    locked_self: {
      code: 'locked_self',
      label: '本人编辑中',
      domain: 'lock',
      badgeStatus: 'processing',
      ...STATUS_COLOR_TOKENS.processing,
      iconName: 'LockOutlined',
      description: '本人正持有独占编辑租约',
      ariaLabel: '编辑租约状态: 本人编辑中',
    },
    locked_other: {
      code: 'locked_other',
      label: '他人占用',
      domain: 'lock',
      badgeStatus: 'warning',
      ...STATUS_COLOR_TOKENS.warning,
      iconName: 'LockOutlined',
      description: '章节正由其他协作成员编辑',
      ariaLabel: '编辑租约状态: 他人占用',
    },
    expired: {
      code: 'expired',
      label: '租约过期',
      domain: 'lock',
      badgeStatus: 'error',
      ...STATUS_COLOR_TOKENS.error,
      iconName: 'FieldTimeOutlined',
      description: '编辑租约已超时过期',
      ariaLabel: '编辑租约状态: 租约过期',
    },
  },
};

/**
 * 历史系统兼容别名映射表
 */
const STATUS_ALIASES: Record<StatusDomain, Record<string, string>> = {
  project: {
    drafting: 'in_progress',
    parsing: 'in_progress',
    checking: 'review',
    pending_confirm: 'review',
    exportable: 'completed',
    exported: 'completed',
    submitted: 'completed',
    opened: 'completed',
    closed: 'archived',
    cancelled: 'archived',
    planning: 'draft',
    done: 'completed',
  },
  chapter: {
    init: 'not_started',
    empty: 'not_started',
    pending: 'not_started',
    generating_ai: 'generating',
    in_review: 'reviewed',
    confirmed: 'reviewed',
    finalized: 'approved',
    locked: 'reviewed',
    stale: 'not_started',
    failed: 'not_started',
  },
  job: {
    pending: 'queued',
    succeeded: 'completed',
    canceled: 'cancelled',
    abort: 'cancelled',
    err: 'failed',
    processing: 'running',
    timeout: 'failed',
  },
  check: {
    hint: 'warning',
    caution: 'warning',
    disqualification: 'blocker',
    fail: 'blocker',
    failed: 'blocker',
    ok: 'passed',
    pass: 'passed',
    pending: 'warning',
    running: 'warning',
    incomplete: 'warning',
    has_blocker: 'blocker',
    warning_only: 'warning',
  },
  export: {
    waiting: 'idle',
    ready: 'idle',
    queued: 'idle',
    exporting: 'processing',
    generating: 'processing',
    building: 'processing',
    done: 'completed',
    success: 'completed',
    error: 'failed',
    expired: 'failed',
  },
  lock: {
    free: 'unlocked',
    idle: 'unlocked',
    self: 'locked_self',
    held: 'locked_self',
    locked: 'locked_other',
    other: 'locked_other',
    busy: 'locked_other',
    timeout: 'expired',
    taken_over: 'expired',
  },
};

/**
 * 生成未知状态的安全默认回退对象（保证系统永不崩溃）
 */
function createFallbackStatus(domain: StatusDomain, code?: string | null): StatusMeta {
  const safeCode = (code || 'unknown').trim();
  const domainLabel = STATUS_DOMAIN_LABELS[domain] || '业务状态';
  return {
    code: safeCode,
    label: safeCode ? safeCode : '未知状态',
    domain,
    badgeStatus: 'default',
    ...STATUS_COLOR_TOKENS.default,
    iconName: 'QuestionCircleOutlined',
    description: `${domainLabel}未知状态 (${safeCode})`,
    ariaLabel: `${domainLabel}: 未知状态 ${safeCode}`,
  };
}

/**
 * 统一状态解析器
 * @param domain 业务域
 * @param code 状态代码（支持别名与大小写容错）
 */
export function resolveStatus(domain: StatusDomain, code?: string | null): StatusMeta {
  if (!code || typeof code !== 'string') {
    return createFallbackStatus(domain, code);
  }

  const normalized = code.trim().toLowerCase();
  const domainRegistry = STATUS_REGISTRY[domain];
  if (!domainRegistry) {
    return createFallbackStatus(domain, code);
  }

  // 1. 直接命中规范码
  if (domainRegistry[normalized]) {
    return domainRegistry[normalized];
  }

  // 2. 命中别名映射
  const aliases = STATUS_ALIASES[domain];
  if (aliases && aliases[normalized] && domainRegistry[aliases[normalized]]) {
    return domainRegistry[aliases[normalized]];
  }

  // 3. 回退为安全未知状态
  return createFallbackStatus(domain, code);
}

// 便捷领域解析器
export const resolveProjectStatus = (code?: string | null) => resolveStatus('project', code);
export const resolveChapterStatus = (code?: string | null) => resolveStatus('chapter', code);
export const resolveJobStatus = (code?: string | null) => resolveStatus('job', code);
export const resolveCheckStatus = (code?: string | null) => resolveStatus('check', code);
export const resolveExportStatus = (code?: string | null) => resolveStatus('export', code);
export const resolveLockStatus = (code?: string | null) => resolveStatus('lock', code);

/**
 * 获取某个领域下所有标准状态列表
 */
export function getAllStatusesForDomain(domain: StatusDomain): StatusMeta[] {
  const domainRegistry = STATUS_REGISTRY[domain];
  if (!domainRegistry) return [];
  return Object.values(domainRegistry);
}

/**
 * 判断长任务或流程是否已进入终态
 */
export function isStatusTerminal(domain: StatusDomain, code?: string | null): boolean {
  const meta = resolveStatus(domain, code);
  if (domain === 'job') {
    return ['completed', 'failed', 'cancelled'].includes(meta.code);
  }
  if (domain === 'export') {
    return ['completed', 'failed'].includes(meta.code);
  }
  if (domain === 'project') {
    return ['completed', 'archived'].includes(meta.code);
  }
  if (domain === 'chapter') {
    return ['approved'].includes(meta.code);
  }
  return false;
}
