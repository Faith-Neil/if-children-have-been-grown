// 为什么有这个文件：落实 APP-M2-T026 (A-01 公司与租户管理页) 与 PRD v1.8 §5.10.1、§5.10.2、§6.9、§7.1 合规规范。
// 它解决什么问题：维护公司多租户基本信息、强脱敏规则生效标识、涉密强制本地模型、密码安全策略（只能调严绝不低于平台基线）、编辑锁与自动保存心跳三元校验，并提供集团管理员/公司管理员精细化权限感知与停用二次确认保护。

import { normalizeSystemRole, SYSTEM_ROLE_LABELS, type SystemRole } from './route-guard.ts';

export interface CompanyTenantInfo {
  id: string;
  name: string;
  credit_code: string; // 18位统一社会信用代码
  group_id: string;
  group_name: string;
  legal_person: string;
  status: 'active' | 'disabled';
  created_at: string;
  user_count: number;
  project_count: number;
  storage_space_id: string;
  rag_collection_id: string;
  settings: CompanyComplianceSettings;
}

export interface CompanyComplianceSettings {
  // 1. 脱敏合规规则 (PRD §6.9)
  mask_strict_mode_enabled: boolean; // 强规则生效标识（不可关闭）
  mask_id_card_mode: 'standard' | 'strict'; // 标准 6+4 或 严格 3+4
  mask_phone_mode: 'standard'; // 前3后4
  mask_bank_card_mode: 'standard'; // 仅后4位
  // 2. 本地模型强制开关 (PRD §6.4, §7.1)
  force_local_model: boolean; // 涉密与敏感项目强制仅用本地模型与本地MinerU
  // 3. 密码安全策略 (PRD §5.10.2, §5.12.1)
  password_min_length: number; // 密码最少位数（默认8，只能调高8~32，严禁低于平台基线8）
  password_min_char_classes: number; // 至少字符类数（默认3，范围3~4，严禁低于3）
  // 4. 编辑锁与自动保存安全约束 (PRD §5.11.9, §7.3 第13条)
  editor_autosave_seconds: number; // 自动保存间隔（秒，默认10，范围5~60）
  edit_lock_heartbeat_seconds: number; // 心跳间隔（秒，默认60，范围15~120）
  edit_lock_timeout_minutes: number; // 编辑锁超时（分钟，默认30，范围10~120）
}

export interface ComplianceValidationIssue {
  field: keyof CompanyComplianceSettings | 'mask_rules' | 'general';
  code: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface CompanyAdminPermissionResult {
  canEdit: boolean;
  canDisable: boolean;
  canViewAudit: boolean;
  canToggleStatus: boolean;
  role: SystemRole;
  roleLabel: string;
  readOnlyNotice?: string;
}

/**
 * 平台默认基线常量（PRD §5.10.2 / §5.11.9）
 */
export const PLATFORM_BASELINE = {
  PASSWORD_MIN_LENGTH: 8,
  PASSWORD_MIN_CHAR_CLASSES: 3,
  LOCK_MIN_TIMEOUT_MINUTES: 5,
} as const;

/**
 * 公司合规参数校验核心算法（合规红线门禁）
 *
 * 验收规则：
 * 1. 密码最少位数不能低于平台默认值 8 位；
 * 2. 密码字符类数不能低于平台默认值 3 类；
 * 3. 自动保存间隔必须 <= 心跳间隔；
 * 4. 心跳间隔的 10 倍必须 <= 锁超时时间（换算为秒）；
 * 5. 锁超时时间必须大于释放前提示的 5 分钟；
 * 6. 严禁关闭高敏脱敏保护（mask_strict_mode_enabled 必须为 true）。
 */
export function validateCompanyComplianceSettings(
  settings: Partial<CompanyComplianceSettings>
): {
  valid: boolean;
  issues: ComplianceValidationIssue[];
} {
  const issues: ComplianceValidationIssue[] = [];

  // 1. 密码策略校验 (PRD §5.10.2)
  if (
    typeof settings.password_min_length === 'number' &&
    settings.password_min_length < PLATFORM_BASELINE.PASSWORD_MIN_LENGTH
  ) {
    issues.push({
      field: 'password_min_length',
      code: 'PASSWORD_MIN_LENGTH_TOO_LOW',
      message: `密码最少位数（当前 ${settings.password_min_length} 位）不能低于平台安全基线 ${PLATFORM_BASELINE.PASSWORD_MIN_LENGTH} 位。`,
      severity: 'error',
    });
  }

  if (
    typeof settings.password_min_char_classes === 'number' &&
    settings.password_min_char_classes < PLATFORM_BASELINE.PASSWORD_MIN_CHAR_CLASSES
  ) {
    issues.push({
      field: 'password_min_char_classes',
      code: 'PASSWORD_MIN_CLASSES_TOO_LOW',
      message: `密码至少包含的字符类别数（当前 ${settings.password_min_char_classes} 类）不能低于平台默认 ${PLATFORM_BASELINE.PASSWORD_MIN_CHAR_CLASSES} 类。`,
      severity: 'error',
    });
  }

  // 2. 编辑锁、心跳与自动保存三元校验 (PRD §5.11.9)
  const autosave = settings.editor_autosave_seconds ?? 10;
  const heartbeat = settings.edit_lock_heartbeat_seconds ?? 60;
  const timeoutMin = settings.edit_lock_timeout_minutes ?? 30;
  const timeoutSec = timeoutMin * 60;

  if (autosave > heartbeat) {
    issues.push({
      field: 'editor_autosave_seconds',
      code: 'AUTOSAVE_EXCEEDS_HEARTBEAT',
      message: `自动保存间隔（${autosave} 秒）不能大于心跳间隔（${heartbeat} 秒），以确保锁释放前最近编辑草稿已落库。`,
      severity: 'error',
    });
  }

  if (heartbeat * 10 > timeoutSec) {
    issues.push({
      field: 'edit_lock_heartbeat_seconds',
      code: 'HEARTBEAT_EXCEEDS_TIMEOUT_RATIO',
      message: `心跳间隔的 10 倍（${heartbeat * 10} 秒）不能大于锁超时时间（${timeoutSec} 秒），以避免瞬时弱网误释放编辑锁。`,
      severity: 'error',
    });
  }

  if (timeoutMin <= PLATFORM_BASELINE.LOCK_MIN_TIMEOUT_MINUTES) {
    issues.push({
      field: 'edit_lock_timeout_minutes',
      code: 'TIMEOUT_TOO_SHORT',
      message: `编辑锁超时时间必须大于释放前强提醒的 ${PLATFORM_BASELINE.LOCK_MIN_TIMEOUT_MINUTES} 分钟。`,
      severity: 'error',
    });
  }

  // 3. 高敏脱敏强合规底线 (PRD §6.9: 不提供关闭掩码开关)
  if (settings.mask_strict_mode_enabled === false) {
    issues.push({
      field: 'mask_strict_mode_enabled',
      code: 'CANNOT_DISABLE_MASKING',
      message: '系统合规底线要求：高敏个人信息脱敏强合规规则不可关闭，必须保持启用状态。',
      severity: 'error',
    });
  }

  return {
    valid: issues.filter(i => i.severity === 'error').length === 0,
    issues,
  };
}

/**
 * 权限感知判定：区分集团管理员、公司管理员、平台管理员与只读人员
 *
 * 权限矩阵规则：
 * 1. platform_admin (平台管理员): 可管理全部公司、开通与停用（停用需二次确认）；
 * 2. company_admin (公司管理员): 仅可管理与编辑本公司的基本信息与安全合规参数；不能停用自身公司；
 * 3. group_admin (集团管理员): 跨公司查看各租户基本信息与合规概览，但严禁修改配置或停用公司（非公司管理员隐藏管理按钮）；
 * 4. viewer / 其他角色: 纯只读展示，彻底隐藏所有编辑与敏感管理按钮。
 */
export function canManageCompanySettings(params: {
  role?: string | string[] | null;
  targetCompanyId: string;
  userCompanyId?: string | null;
}): CompanyAdminPermissionResult {
  const normRole = normalizeSystemRole(params.role);
  const roleLabel = SYSTEM_ROLE_LABELS[normRole];
  const isSameCompany = Boolean(
    params.userCompanyId && params.userCompanyId === params.targetCompanyId
  );

  // 1. 平台管理员：全局最高权限
  if (normRole === 'platform_admin') {
    return {
      canEdit: true,
      canDisable: true,
      canViewAudit: true,
      canToggleStatus: true,
      role: normRole,
      roleLabel,
    };
  }

  // 2. 公司管理员：管理本公司
  if (normRole === 'company_admin') {
    if (isSameCompany) {
      return {
        canEdit: true,
        canDisable: false, // 公司管理员不能自我注销/停用所在公司，需平台管理员执行
        canViewAudit: true,
        canToggleStatus: false,
        role: normRole,
        roleLabel,
      };
    }
    return {
      canEdit: false,
      canDisable: false,
      canViewAudit: false,
      canToggleStatus: false,
      role: normRole,
      roleLabel,
      readOnlyNotice: '您是其他公司的管理员，无法跨公司编辑本租户配置。',
    };
  }

  // 3. 集团管理员：跨公司只读监管，严禁编辑与停用
  if (normRole === 'group_admin') {
    return {
      canEdit: false,
      canDisable: false,
      canViewAudit: true,
      canToggleStatus: false,
      role: normRole,
      roleLabel,
      readOnlyNotice: '当前以【集团管理员】视角浏览各公司租户合规配置。您具备全局监管审阅权限，但不可直接修改具体公司的参数。',
    };
  }

  // 4. 其他只读或业务角色（viewer, bid_writer, auditor 等）
  return {
    canEdit: false,
    canDisable: false,
    canViewAudit: false,
    canToggleStatus: false,
    role: normRole,
    roleLabel,
    readOnlyNotice: `当前角色（${roleLabel}）无权修改企业租户安全配置，所有参数仅供只读参考。`,
  };
}

/**
 * 停用公司二次确认输入核验（PRD §5.10.1 约束：停用二次确认）
 */
export function validateDisableConfirmation(
  inputCompanyName: string,
  expectedCompanyName: string
): boolean {
  if (!inputCompanyName || !expectedCompanyName) return false;
  return inputCompanyName.trim() === expectedCompanyName.trim();
}

/**
 * 默认演示公司数据（华东数智与远山信息）
 */
export const DEFAULT_COMPANIES: CompanyTenantInfo[] = [
  {
    id: 'alpha',
    name: '华东数智科技有限公司',
    credit_code: '91310000MA1FL7XX99',
    group_id: 'grp-east-01',
    group_name: '东风信息技术集团',
    legal_person: '林振华',
    status: 'active',
    created_at: '2026-01-15 09:00:00',
    user_count: 28,
    project_count: 12,
    storage_space_id: 'space-alpha-store-01',
    rag_collection_id: 'rag-col-alpha-kb',
    settings: {
      mask_strict_mode_enabled: true,
      mask_id_card_mode: 'standard',
      mask_phone_mode: 'standard',
      mask_bank_card_mode: 'standard',
      force_local_model: true,
      password_min_length: 8,
      password_min_char_classes: 3,
      editor_autosave_seconds: 10,
      edit_lock_heartbeat_seconds: 60,
      edit_lock_timeout_minutes: 30,
    },
  },
  {
    id: 'beta',
    name: '远山信息技术有限公司',
    credit_code: '91330100MA2BL8YY88',
    group_id: 'grp-east-01',
    group_name: '东风信息技术集团',
    legal_person: '赵远山',
    status: 'active',
    created_at: '2026-03-20 14:30:00',
    user_count: 16,
    project_count: 7,
    storage_space_id: 'space-beta-store-01',
    rag_collection_id: 'rag-col-beta-kb',
    settings: {
      mask_strict_mode_enabled: true,
      mask_id_card_mode: 'strict',
      mask_phone_mode: 'standard',
      mask_bank_card_mode: 'standard',
      force_local_model: true,
      password_min_length: 10,
      password_min_char_classes: 3,
      editor_autosave_seconds: 15,
      edit_lock_heartbeat_seconds: 60,
      edit_lock_timeout_minutes: 45,
    },
  },
];
