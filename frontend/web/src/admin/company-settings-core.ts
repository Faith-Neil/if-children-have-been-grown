// 为什么有这个文件：提取企业设置与扩展字段配置的核心逻辑、平台基线上下限与 9.11 联动校验规则。
// 它解决什么问题：
// 1. 落实 PRD v1.8 §5.10.3、§6.9 与交接约束 M1-P09-F3；
// 2. 贯彻“越界提示平台上下限，公司设置只能调严不能调宽”安全基线；
// 3. 校验编辑锁心跳三元联动约束（自动保存 <= 心跳，心跳*10 <= 锁超时）；
// 4. 精细化识别 8 大标准 RBAC 角色权限与只读态。

import { normalizeSystemRole, SYSTEM_ROLE_LABELS, type SystemRole } from '../shell/route-guard.ts';

export interface CustomFieldMetadata {
  id: string;
  field_key: string;
  field_name: string;
  field_type: 'text' | 'number' | 'select' | 'date';
  required: boolean;
  scope: 'project' | 'chapter' | 'tender';
  options?: string[];
  description?: string;
}

export interface CompanySettingsData {
  company_id: string;
  company_name: string;

  // 1. 账号安全策略（PRD §5.10.2 / Q28 定案：只能调严不可调宽）
  password_min_length: number; // 平台默认 8，范围 8~32
  password_min_char_classes: number; // 平台默认 3，范围 3~4
  password_expire_days: number; // 密码有效期（天），范围 30~365
  session_timeout_minutes: number; // 会话超时（分钟），范围 30~480（与后台一致）
  max_login_attempts: number; // 连续登录失败锁定次数，范围 1~5（只能调严）

  // 2. 编辑锁定与协同（规范 9.11 核心三元规则）
  editor_autosave_seconds: number; // 默认 10，范围 5~60
  edit_lock_heartbeat_seconds: number; // 默认 60，范围 15~120
  edit_lock_timeout_minutes: number; // 默认 30，范围 6~60（与后台一致）

  // 3. 导出交付与合规红线 (PRD §6.9)
  export_watermark_enabled: boolean;
  export_watermark_text: string;
  export_redline_blocking: boolean; // 废标阻断硬门禁（强制 true，不可关闭）
  force_local_model: boolean; // 涉密项目强制使用本地模型

  // 4. 大纲规划与 AI 上下文预算
  outline_max_depth: number; // 默认 4（卷-章-节-小节），范围 2~5
  outline_target_words_default: number; // 默认 3000，范围 500~20000
  ai_token_budget_per_chapter: number; // 默认 16384，范围 4096~65536

  // 5. 扩展字段元数据
  custom_fields: CustomFieldMetadata[];

  // 6. 对话助手、解析与查重（后台 CompanySettingsModel 同名字段，PRD §5.11.9、§5.2.2、§5.8.3）
  assistant_enabled: boolean;
  assistant_suggestion_count: number; // 3~5
  assistant_kb_default: boolean;
  assistant_allow_kb_off: boolean;
  parse_confidence_threshold: number; // 0.5~0.99
  dup_min_chars: number;
  dup_history_months: number;
}

export interface SettingBoundMeta {
  min: number;
  max: number;
  default: number;
  tightenDirection: 'higher' | 'lower'; // 'higher' 表示值越大越严（如密码长度），'lower' 表示值越小越严（如自动保存）
  unit: string;
  label: string;
  description: string;
}

/**
 * 平台基线与上下限定义表（PRD §5.10.2、§5.11.9 与规范 9.2）
 */
export const PLATFORM_SETTING_BOUNDS: Record<string, SettingBoundMeta> = {
  password_min_length: {
    min: 8,
    max: 32,
    default: 8,
    tightenDirection: 'higher',
    unit: '位',
    label: '密码最少位数',
    description: '平台基线 8 位，公司只能调严（>=8）',
  },
  password_min_char_classes: {
    min: 3,
    max: 4,
    default: 3,
    tightenDirection: 'higher',
    unit: '类',
    label: '密码最少字符类别',
    description: '平台基线 3 类，公司只能调严（>=3）',
  },
  password_expire_days: {
    min: 30,
    max: 365,
    default: 90,
    tightenDirection: 'lower',
    unit: '天',
    label: '密码有效期限',
    description: '公司安全密码最长轮换周期',
  },
  session_timeout_minutes: {
    min: 30,
    max: 480,
    default: 120,
    tightenDirection: 'lower',
    unit: '分钟',
    label: '会话闲置超时',
    description: '无操作自动登出超时保护',
  },
  editor_autosave_seconds: {
    min: 5,
    max: 60,
    default: 10,
    tightenDirection: 'lower',
    unit: '秒',
    label: '自动保存间隔',
    description: '编辑器内容自动静默落盘间隔',
  },
  edit_lock_heartbeat_seconds: {
    min: 15,
    max: 120,
    default: 60,
    tightenDirection: 'lower',
    unit: '秒',
    label: '编辑锁心跳间隔',
    description: '排他编辑租约续约心跳周期',
  },
  edit_lock_timeout_minutes: {
    min: 6,
    max: 60,
    default: 30,
    tightenDirection: 'lower',
    unit: '分钟',
    label: '编辑锁租约时长',
    description: '编辑锁闲置最大超时时长',
  },
  max_login_attempts: {
    min: 1,
    max: 5,
    default: 5,
    tightenDirection: 'lower',
    unit: '次',
    label: '连续登录失败锁定次数',
    description: '平台上限 5 次，公司只能调严',
  },
  assistant_suggestion_count: {
    min: 3,
    max: 5,
    default: 3,
    tightenDirection: 'higher',
    unit: '条',
    label: '修改样例条数',
    description: '对话助手每次给出的写法数',
  },
  parse_confidence_threshold: {
    min: 0.5,
    max: 0.99,
    default: 0.8,
    tightenDirection: 'higher',
    unit: '',
    label: '解析置信度阈值',
    description: '低于此值的条目在解析页高亮',
  },
  dup_min_chars: {
    min: 5,
    max: 50,
    default: 8,
    tightenDirection: 'lower',
    unit: '字',
    label: '查重连续相同字数',
    description: '本公司查重判定为重复的连续字数',
  },
  dup_history_months: {
    min: 1,
    max: 120,
    default: 24,
    tightenDirection: 'higher',
    unit: '月',
    label: '查重历史年限',
    description: '与多少个月内的历史标书比对',
  },
  outline_max_depth: {
    min: 2,
    max: 5,
    default: 4,
    tightenDirection: 'higher',
    unit: '级',
    label: '大纲层级上限',
    description: '标书大纲树最大规划深度',
  },
  outline_target_words_default: {
    min: 500,
    max: 20000,
    default: 3000,
    tightenDirection: 'higher',
    unit: '字',
    label: '单节基准字数',
    description: '章节生成默认参考目标篇幅',
  },
  ai_token_budget_per_chapter: {
    min: 4096,
    max: 65536,
    default: 16384,
    tightenDirection: 'higher',
    unit: 'Token',
    label: 'AI 上下文预算',
    description: '单章写作方案检索与生成上限',
  },
};

export interface SettingsValidationIssue {
  field: string;
  code: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface CompanySettingsPermissionResult {
  canEdit: boolean;
  canSave: boolean;
  canAddCustomField: boolean;
  isReadOnly: boolean;
  role: SystemRole;
  roleLabel: string;
  readOnlyNotice?: string;
}

/**
 * 校验 8 大角色对公司设置与扩展字段的控制权限
 */
export function checkCompanySettingsPermission(rawRole?: string): CompanySettingsPermissionResult {
  const role = normalizeSystemRole(rawRole);
  const roleLabel = SYSTEM_ROLE_LABELS[role] || '只读成员';

  // 仅平台管理员与公司管理员拥有配置修改权限
  const isPrivileged = role === 'platform_admin' || role === 'company_admin';

  if (isPrivileged) {
    return {
      canEdit: true,
      canSave: true,
      canAddCustomField: true,
      isReadOnly: false,
      role,
      roleLabel,
    };
  }

  return {
    canEdit: false,
    canSave: false,
    canAddCustomField: false,
    isReadOnly: true,
    role,
    roleLabel,
    readOnlyNotice: `您当前身份为「${roleLabel}」，仅具备公司设置查阅权限。如需调整请联系公司管理员或平台运维。`,
  };
}

/**
 * 核心合规校验算法：
 * 1. 平台基线红线：密码策略只能调严（>= 平台下限，如 8 位、3 类字符）；
 * 2. 规范 9.11 编辑协同三元约束：
 *    - 规则 ①: 自动保存间隔 <= 心跳间隔；
 *    - 规则 ②: 心跳间隔 * 10 <= 锁超时秒数；
 *    - 规则 ③: 锁超时时间 >= 5 分钟；
 * 3. 废标红线导出门禁强制开启，不可关闭；
 * 4. 各数值字段越界检查（上下限判定）。
 */
export function validateCompanySettings(settings: Partial<CompanySettingsData>): {
  valid: boolean;
  issues: SettingsValidationIssue[];
} {
  const issues: SettingsValidationIssue[] = [];

  // 1. 密码安全策略只能调严（PRD §5.10.2 / Q28 定案）
  if (typeof settings.password_min_length === 'number') {
    const bound = PLATFORM_SETTING_BOUNDS.password_min_length;
    if (settings.password_min_length < bound.min) {
      issues.push({
        field: 'password_min_length',
        code: 'PASSWORD_MIN_LENGTH_TOO_LOW',
        message: `密码最少位数（当前 ${settings.password_min_length} 位）不能低于平台安全基线 ${bound.min} 位（公司策略只能调严不能调宽）。`,
        severity: 'error',
      });
    } else if (settings.password_min_length > bound.max) {
      issues.push({
        field: 'password_min_length',
        code: 'PASSWORD_MIN_LENGTH_OUT_OF_BOUNDS',
        message: `密码最少位数不能超过上限 ${bound.max} 位。`,
        severity: 'error',
      });
    }
  }

  if (typeof settings.password_min_char_classes === 'number') {
    const bound = PLATFORM_SETTING_BOUNDS.password_min_char_classes;
    if (settings.password_min_char_classes < bound.min) {
      issues.push({
        field: 'password_min_char_classes',
        code: 'PASSWORD_CHAR_CLASSES_TOO_LOW',
        message: `密码字符类别数（当前 ${settings.password_min_char_classes} 类）不能低于平台安全基线 ${bound.min} 类（公司策略只能调严不能调宽）。`,
        severity: 'error',
      });
    } else if (settings.password_min_char_classes > bound.max) {
      issues.push({
        field: 'password_min_char_classes',
        code: 'PASSWORD_CHAR_CLASSES_OUT_OF_BOUNDS',
        message: `密码字符类别数不能超过上限 ${bound.max} 类。`,
        severity: 'error',
      });
    }
  }

  // 2. 编辑锁定与协同（规范 9.11 核心三元约束）
  const autosave = settings.editor_autosave_seconds;
  const heartbeat = settings.edit_lock_heartbeat_seconds;
  const lockTimeoutMin = settings.edit_lock_timeout_minutes;

  if (typeof autosave === 'number' && typeof heartbeat === 'number') {
    if (autosave > heartbeat) {
      issues.push({
        field: 'editor_autosave_seconds',
        code: 'AUTOSAVE_GREATER_THAN_HEARTBEAT',
        message: `自动保存间隔（${autosave} 秒）必须小于或等于心跳间隔（${heartbeat} 秒），否则编辑内容可能在心跳续约前丢失。`,
        severity: 'error',
      });
    }
  }

  if (typeof heartbeat === 'number' && typeof lockTimeoutMin === 'number') {
    const lockTimeoutSec = lockTimeoutMin * 60;
    if (heartbeat * 10 > lockTimeoutSec) {
      issues.push({
        field: 'edit_lock_timeout_minutes',
        code: 'HEARTBEAT_RATIO_EXCEEDS_TIMEOUT',
        message: `心跳间隔的 10 倍（${heartbeat * 10} 秒）必须小于或等于锁超时时间（${lockTimeoutSec} 秒），以预留足够的网络波动重试容错窗口。`,
        severity: 'error',
      });
    }
  }

  if (typeof lockTimeoutMin === 'number') {
    if (lockTimeoutMin < 5) {
      issues.push({
        field: 'edit_lock_timeout_minutes',
        code: 'LOCK_TIMEOUT_TOO_SHORT',
        message: `锁超时时间（当前 ${lockTimeoutMin} 分钟）不能低于 5 分钟，否则无法在租约释放前向编辑人员发出有效预警提示。`,
        severity: 'error',
      });
    }
  }

  // 3. 导出合规与红线门禁 (PRD §6.9)
  if (settings.export_redline_blocking === false) {
    issues.push({
      field: 'export_redline_blocking',
      code: 'REDLINE_BLOCKING_CANNOT_BE_DISABLED',
      message: '废标红线导出门禁属于系统核心强制合规规范，不可关闭（只能调严）。',
      severity: 'error',
    });
  }

  // 4. 其他数值字段越界检查
  for (const [key, bound] of Object.entries(PLATFORM_SETTING_BOUNDS)) {
    if (key === 'password_min_length' || key === 'password_min_char_classes') continue;
    const val = (settings as Record<string, unknown>)[key];
    if (typeof val === 'number') {
      if (val < bound.min || val > bound.max) {
        issues.push({
          field: key,
          code: `${key.toUpperCase()}_OUT_OF_RANGE`,
          message: `${bound.label}当前值 ${val} 超出平台允许范围（${bound.min} ~ ${bound.max} ${bound.unit}）。`,
          severity: 'error',
        });
      }
    }
  }

  return {
    valid: issues.every(i => i.severity !== 'error'),
    issues,
  };
}

/**
 * 默认扩展字段初始配置
 */
export const DEFAULT_CUSTOM_FIELDS: CustomFieldMetadata[] = [
  {
    id: 'cf-01',
    field_key: 'custom_sla_grade',
    field_name: 'SLA 服务保障等级',
    field_type: 'select',
    required: true,
    scope: 'project',
    options: ['7x24 极速响应', '5x8 标准响应', '专人驻场支持'],
    description: '客户要求的 SLA 服务可用性级别',
  },
  {
    id: 'cf-02',
    field_key: 'custom_tender_budget_code',
    field_name: '投标预算科目编码',
    field_type: 'text',
    required: false,
    scope: 'tender',
    description: '财务核算与立项报备编号',
  },
  {
    id: 'cf-03',
    field_key: 'custom_lead_reviewer',
    field_name: '终审复核总工',
    field_type: 'text',
    required: false,
    scope: 'chapter',
    description: '指定关键技术章节签字确认专家',
  },
];

/**
 * 构造初始公司设置数据集
 */
export function buildInitialCompanySettings(companyId = 'alpha', companyName = '华东数智科技有限公司'): CompanySettingsData {
  return {
    company_id: companyId,
    company_name: companyName,
    password_min_length: 8,
    password_min_char_classes: 3,
    password_expire_days: 90,
    session_timeout_minutes: 120,
    max_login_attempts: 5,
    editor_autosave_seconds: 10,
    edit_lock_heartbeat_seconds: 60,
    edit_lock_timeout_minutes: 30,
    export_watermark_enabled: true,
    export_watermark_text: '机密投标材料 · 仅供内部流转',
    export_redline_blocking: true,
    force_local_model: true,
    outline_max_depth: 4,
    outline_target_words_default: 3000,
    ai_token_budget_per_chapter: 16384,
    custom_fields: [...DEFAULT_CUSTOM_FIELDS],
    assistant_enabled: true,
    assistant_suggestion_count: 3,
    assistant_kb_default: true,
    assistant_allow_kb_off: true,
    parse_confidence_threshold: 0.8,
    dup_min_chars: 8,
    dup_history_months: 24,
  };
}
