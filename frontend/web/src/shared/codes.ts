// 为什么有这个文件：依据数据字典 v1.9 §4.16 与 PRD v1.8 集中收口状态码、章节分册类型与错误码。
// 它解决什么问题：杜绝前端散落魔法字符串（Magic Strings），使项目状态、需求分类、作业状态、分册枚举与错误码单源驱动。

/**
 * 项目状态代码表 (project_status, 字典 4.16 节)
 */
export const PROJECT_STATUSES = {
  DRAFT: 'draft',
  PARSING: 'parsing',
  PENDING_CONFIRM: 'pending_confirm',
  DRAFTING: 'drafting',
  CHECKING: 'checking',
  EXPORTABLE: 'exportable',
  EXPORTED: 'exported',
  SUBMITTED: 'submitted',
  OPENED: 'opened',
  CLOSED: 'closed',
  CANCELLED: 'cancelled',
} as const;

export type ProjectStatusCode = typeof PROJECT_STATUSES[keyof typeof PROJECT_STATUSES];

export const PROJECT_STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  parsing: '解析中',
  pending_confirm: '待确认',
  drafting: '编制中',
  checking: '检查中',
  exportable: '可导出',
  exported: '已导出',
  submitted: '已递交',
  opened: '已开标',
  closed: '已结束',
  cancelled: '已取消',
};

/**
 * 分册类型代码表 (bid_volume_type, 字典 4.13 节)
 */
export const VOLUME_TYPES = {
  TECHNICAL: 'technical',
  BUSINESS: 'business',
} as const;

export type VolumeType = typeof VOLUME_TYPES[keyof typeof VOLUME_TYPES];

export const VOLUME_LABELS: Record<string, string> = {
  technical: '技术标',
  business: '商务标',
};

/**
 * 招标文件解析状态 (tender_parse_status, 字典 4.16 节)
 */
export const TENDER_PARSE_STATUSES = {
  PENDING: 'pending',
  UPLOADING: 'uploading',
  PARSING: 'parsing',
  EXTRACTING: 'extracting',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;

/**
 * 抽取类别代码表 (requirement_category, 字典 4.16 节)
 */
export const REQUIREMENT_CATEGORIES = {
  BASIC_INFO: 'basic_info',
  QUALIFICATION: 'qualification',
  SCORING: 'scoring',
  VOID_CLAUSE: 'void_clause',
  STAR_CLAUSE: 'star_clause',
  TECH_SERVICE: 'tech_service',
  SLA: 'sla',
  FORMAT: 'format',
  TIMELINE: 'timeline',
  DEPOSIT: 'deposit',
} as const;

export const REQUIREMENT_CATEGORY_LABELS: Record<string, string> = {
  basic_info: '项目基本信息',
  qualification: '资格要求',
  scoring: '评分办法与评分项',
  void_clause: '废标与无效标条款',
  star_clause: '星号实质性条款',
  tech_service: '技术服务要求',
  sla: 'SLA 要求',
  format: '投标文件格式要求',
  timeline: '时间节点',
  deposit: '保证金',
};

/**
 * 抽取条目状态 (requirement_status, 字典 4.16 节)
 */
export const REQUIREMENT_STATUSES = {
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  MANUALLY_EDITED: 'manually_edited',
  DELETED: 'deleted',
} as const;

export const REQUIREMENT_STATUS_LABELS: Record<string, string> = {
  pending: '待确认',
  confirmed: '已确认',
  manually_edited: '已人工修改',
  deleted: '已删除',
};

/**
 * 事实状态 (fact_status)
 */
export const FACT_STATUSES = {
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  REJECTED: 'rejected',
  NEEDS_REVIEW: 'needs_review',
} as const;

export const FACT_STATUS_LABELS: Record<string, string> = {
  pending: '待确认',
  confirmed: '已确认',
  rejected: '已拒绝',
  needs_review: '待复核',
};

/**
 * 冲突状态 (conflict_status, 字典 4.16 节)
 */
export const CONFLICT_STATUSES = {
  PENDING: 'pending',
  CHOSEN: 'chosen',
  NOT_CONFLICT: 'not_conflict',
  RESOLVED_BY_ADDENDUM: 'resolved_by_addendum',
} as const;

/**
 * 后台任务状态 (job_status, 字典 4.16 节)
 */
export const JOB_STATUSES = {
  QUEUED: 'queued',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
} as const;

export const JOB_STATUS_LABELS: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  completed: '已完成',
  failed: '执行失败',
  cancelled: '已取消',
};

/**
 * 规则严重性级别 (rule_level, 字典 4.16 节)
 */
export const RULE_LEVELS = {
  BLOCKER: 'blocker',
  WARNING: 'warning',
  HINT: 'hint',
} as const;

export const RULE_LEVEL_LABELS: Record<string, string> = {
  blocker: '阻断项',
  warning: '警告项',
  hint: '提示项',
};

/**
 * 统一后端错误码常量（与 backend frozen_error_codes.py 保持单源对齐）
 */
export const ERROR_CODES = {
  UNAUTHENTICATED: 'UNAUTHENTICATED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  CONFLICT: 'CONFLICT',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  SESSION_ROLE_UNSUPPORTED: 'SESSION_ROLE_UNSUPPORTED',
  SESSION_SCOPE_UNSUPPORTED: 'SESSION_SCOPE_UNSUPPORTED',
  VOLUME_OWNER_REQUIRED: 'VOLUME_OWNER_REQUIRED',
  TWO_VOLUMES_REQUIRED: 'TWO_VOLUMES_REQUIRED',
  MODEL_UNAVAILABLE: 'MODEL_UNAVAILABLE',
  SECRET_KEY_UNAVAILABLE: 'SECRET_KEY_UNAVAILABLE',
  SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL: 'SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL',
  IDEMPOTENCY_CONFLICT: 'IDEMPOTENCY_CONFLICT',
  IDEMPOTENCY_KEY_REQUIRED: 'IDEMPOTENCY_KEY_REQUIRED',
  EVIDENCE_EXPIRED: 'EVIDENCE_EXPIRED',
  EVIDENCE_NOT_USABLE: 'EVIDENCE_NOT_USABLE',
} as const;
