// 为什么有这个文件：落实 APP-M2-T027 (A-02 用户管理、新增与停用前转交安全表单) 与 PRD v1.8 §2.3、§5.10.1、§5.10.2。
// 它解决什么问题：维护用户与 8 大标准 RBAC 角色、公司密码策略即时强校验（只能调严绝不低于平台基线 8 位/3 类）、停用前业务资产强制转交防线（未转交阻断停用，防止项目与章节资产遗失），以及多租户数据强隔离与角色权限感知。

import { SYSTEM_ROLE_LABELS, type SystemRole } from '../shared/roles.ts';

export type UserStatus = 'active' | 'disabled' | 'locked';

export interface ProjectAssetSummary {
  id: string;
  name: string;
  role_in_project: string;
}

export interface ChapterAssetSummary {
  id: string;
  title: string;
  project_name: string;
}

export interface KbItemAssetSummary {
  id: string;
  title: string;
  category: string;
}

export interface UserAssignedAssets {
  active_projects: ProjectAssetSummary[];
  active_chapters: ChapterAssetSummary[];
  kb_items: KbItemAssetSummary[];
}

export interface UserItem {
  id: string;
  username: string;
  name: string;
  role: SystemRole;
  company_id: string;
  status: UserStatus;
  email?: string;
  phone?: string;
  created_at: string;
  last_login_at?: string;
  assigned_assets: UserAssignedAssets;
}

export interface UserHandoverRecord {
  id: string;
  source_user_id: string;
  source_username: string;
  target_user_id: string;
  target_username: string;
  company_id: string;
  transferred_projects_count: number;
  transferred_chapters_count: number;
  transferred_kb_count: number;
  reason: string;
  operator_id: string;
  timestamp: string;
}

export interface CompanyPasswordPolicy {
  password_min_length: number; // 平台基线 >= 8 位
  password_min_char_classes: number; // 平台基线 >= 3 类 (大写、小写、数字、符号)
  max_login_attempts: number; // 平台基线 <= 5 次 (只能调严)
  lockout_minutes: number; // 锁定时间 (分钟)
}

export const PLATFORM_PASSWORD_BASELINE = {
  MIN_LENGTH: 8,
  MIN_CHAR_CLASSES: 3,
  MAX_LOGIN_ATTEMPTS: 5,
  MIN_LOCKOUT_MINUTES: 5,
} as const;

export const DEFAULT_COMPANY_PASSWORD_POLICY: CompanyPasswordPolicy = {
  password_min_length: 8,
  password_min_char_classes: 3,
  max_login_attempts: 5,
  lockout_minutes: 15,
};

export interface PasswordValidationResult {
  valid: boolean;
  charClassCount: number;
  message?: string;
  errors: string[];
}

/**
 * 计算密码所包含的字符类别数（大写、小写、数字、特殊符号）
 */
export function countPasswordCharClasses(password: string): number {
  if (!password) return 0;
  let classes = 0;
  if (/[A-Z]/.test(password)) classes++;
  if (/[a-z]/.test(password)) classes++;
  if (/[0-9]/.test(password)) classes++;
  if (/[^A-Za-z0-9]/.test(password)) classes++;
  return classes;
}

/**
 * 校验密码强度与公司密码策略（支持即时动态策略）
 */
export function validatePasswordStrength(
  password: string,
  policy: Partial<CompanyPasswordPolicy> = DEFAULT_COMPANY_PASSWORD_POLICY
): PasswordValidationResult {
  const minLength = policy.password_min_length ?? PLATFORM_PASSWORD_BASELINE.MIN_LENGTH;
  const minClasses = policy.password_min_char_classes ?? PLATFORM_PASSWORD_BASELINE.MIN_CHAR_CLASSES;
  const errors: string[] = [];

  if (!password) {
    return {
      valid: false,
      charClassCount: 0,
      message: '请输入密码',
      errors: ['密码不能为空'],
    };
  }

  if (password.length < minLength) {
    errors.push(`密码长度至少为 ${minLength} 位（当前 ${password.length} 位）`);
  }

  const charClassCount = countPasswordCharClasses(password);
  if (charClassCount < minClasses) {
    errors.push(`密码至少包含大写字母、小写字母、数字、特殊符号中的 ${minClasses} 类（当前命中 ${charClassCount} 类）`);
  }

  return {
    valid: errors.length === 0,
    charClassCount,
    message: errors[0],
    errors,
  };
}

/**
 * 校验公司密码策略调整：“公司设置只能调严不能调宽”
 */
export function validateCompanyPasswordPolicy(
  policy: Partial<CompanyPasswordPolicy>
): { valid: boolean; issues: string[] } {
  const issues: string[] = [];

  if (typeof policy.password_min_length === 'number') {
    if (policy.password_min_length < PLATFORM_PASSWORD_BASELINE.MIN_LENGTH) {
      issues.push(`密码最小长度（${policy.password_min_length} 位）低于平台基线（${PLATFORM_PASSWORD_BASELINE.MIN_LENGTH} 位），只能调严不能调宽`);
    } else if (policy.password_min_length > 32) {
      issues.push('密码最小长度上限为 32 位');
    }
  }

  if (typeof policy.password_min_char_classes === 'number') {
    if (policy.password_min_char_classes < PLATFORM_PASSWORD_BASELINE.MIN_CHAR_CLASSES) {
      issues.push(`字符种类数（${policy.password_min_char_classes} 类）低于平台基线（${PLATFORM_PASSWORD_BASELINE.MIN_CHAR_CLASSES} 类），只能调严不能调宽`);
    } else if (policy.password_min_char_classes > 4) {
      issues.push('字符种类数最多为 4 类（大写、小写、数字、符号）');
    }
  }

  if (typeof policy.max_login_attempts === 'number') {
    if (policy.max_login_attempts > PLATFORM_PASSWORD_BASELINE.MAX_LOGIN_ATTEMPTS) {
      issues.push(`连续登录失败锁定次数（${policy.max_login_attempts} 次）高于平台基线（${PLATFORM_PASSWORD_BASELINE.MAX_LOGIN_ATTEMPTS} 次），只能调严不能调宽`);
    } else if (policy.max_login_attempts < 1) {
      issues.push('连续登录失败锁定次数至少为 1 次');
    }
  }

  return {
    valid: issues.length === 0,
    issues,
  };
}

/**
 * 统计用户当前持有的未完结资产总数
 */
export function countUserActiveAssets(assets?: UserAssignedAssets | null): number {
  if (!assets) return 0;
  return (
    (assets.active_projects?.length || 0) +
    (assets.active_chapters?.length || 0) +
    (assets.kb_items?.length || 0)
  );
}

/**
 * 判定用户是否持有未完结资产
 */
export function hasActiveAssets(assets?: UserAssignedAssets | null): boolean {
  return countUserActiveAssets(assets) > 0;
}

/**
 * 资产摘要友好文案
 */
export function formatAssetSummary(assets?: UserAssignedAssets | null): string {
  if (!assets) return '0 项资产';
  const parts: string[] = [];
  if (assets.active_projects?.length) {
    parts.push(`${assets.active_projects.length} 个进行中项目`);
  }
  if (assets.active_chapters?.length) {
    parts.push(`${assets.active_chapters.length} 篇在编章节`);
  }
  if (assets.kb_items?.length) {
    parts.push(`${assets.kb_items.length} 项负责资料`);
  }
  return parts.length > 0 ? parts.join(' · ') : '0 项资产（可直接停用）';
}

export interface NewUserFormData {
  username: string;
  name: string;
  role: SystemRole;
  company_id: string;
  password?: string;
  confirm_password?: string;
  email?: string;
  phone?: string;
}

/**
 * 新增用户表单校验
 */
export function validateNewUserForm(
  data: Partial<NewUserFormData>,
  existingUsers: UserItem[],
  policy: CompanyPasswordPolicy = DEFAULT_COMPANY_PASSWORD_POLICY
): { valid: boolean; field?: keyof NewUserFormData; message?: string } {
  const username = data.username?.trim();
  if (!username) {
    return { valid: false, field: 'username', message: '请输入登录账号' };
  }
  if (!/^[a-zA-Z0-9_]{3,32}$/.test(username)) {
    return { valid: false, field: 'username', message: '账号仅限 3~32 位字母、数字或下划线' };
  }
  const duplicated = existingUsers.some(
    u => u.username.toLowerCase() === username.toLowerCase()
  );
  if (duplicated) {
    return { valid: false, field: 'username', message: `账号 "${username}" 已存在，不可重复` };
  }

  const name = data.name?.trim();
  if (!name || name.length < 2) {
    return { valid: false, field: 'name', message: '中文姓名至少需 2 个字符' };
  }

  if (!data.role) {
    return { valid: false, field: 'role', message: '请选择用户所属系统角色' };
  }

  if (!data.company_id?.trim()) {
    return { valid: false, field: 'company_id', message: '所属企业租户不能为空' };
  }

  const password = data.password || '';
  const pwdValidation = validatePasswordStrength(password, policy);
  if (!pwdValidation.valid) {
    return { valid: false, field: 'password', message: pwdValidation.message };
  }

  if (data.confirm_password !== password) {
    return { valid: false, field: 'confirm_password', message: '两次输入的密码不一致' };
  }

  return { valid: true };
}

/**
 * 停用前资产转交校验（交接约束 M1-P10-F2 红线门禁）
 */
export function validateHandoverBeforeDisable(params: {
  sourceUser: UserItem;
  targetUserId: string;
  reason: string;
  availableUsers: UserItem[];
}): { valid: boolean; field?: 'targetUserId' | 'reason'; message?: string } {
  const { sourceUser, targetUserId, reason, availableUsers } = params;

  if (!targetUserId) {
    return { valid: false, field: 'targetUserId', message: '请选择资产接收人' };
  }

  if (targetUserId === sourceUser.id) {
    return { valid: false, field: 'targetUserId', message: '交接接收人不能是待停用用户本人' };
  }

  const targetUser = availableUsers.find(u => u.id === targetUserId);
  if (!targetUser) {
    return { valid: false, field: 'targetUserId', message: '指定的接收人不存在' };
  }

  if (targetUser.status !== 'active') {
    return { valid: false, field: 'targetUserId', message: '接收人当前状态不可用（必须为正常在职用户）' };
  }

  if (targetUser.company_id !== sourceUser.company_id) {
    return { valid: false, field: 'targetUserId', message: '严禁跨企业租户进行业务资产转交' };
  }

  const trimmedReason = reason?.trim() || '';
  if (trimmedReason.length < 5) {
    return { valid: false, field: 'reason', message: '交接理由不得少于 5 个字（用于审计追溯）' };
  }

  return { valid: true };
}

/**
 * 执行资产转交与用户停用
 */
export function executeUserHandoverAndDisable(params: {
  users: UserItem[];
  sourceUserId: string;
  targetUserId: string;
  reason: string;
  operatorId: string;
}): {
  updatedUsers: UserItem[];
  handoverRecord: UserHandoverRecord;
} {
  const { users, sourceUserId, targetUserId, reason, operatorId } = params;
  const source = users.find(u => u.id === sourceUserId);
  const target = users.find(u => u.id === targetUserId);

  if (!source || !target) {
    throw new Error('用户不存在，无法执行资产交接。');
  }

  const transferredProjects = [...(source.assigned_assets.active_projects || [])];
  const transferredChapters = [...(source.assigned_assets.active_chapters || [])];
  const transferredKb = [...(source.assigned_assets.kb_items || [])];

  const handoverRecord: UserHandoverRecord = {
    id: `handover_${Date.now()}`,
    source_user_id: source.id,
    source_username: source.username,
    target_user_id: target.id,
    target_username: target.username,
    company_id: source.company_id,
    transferred_projects_count: transferredProjects.length,
    transferred_chapters_count: transferredChapters.length,
    transferred_kb_count: transferredKb.length,
    reason: reason.trim(),
    operator_id: operatorId,
    timestamp: new Date().toISOString(),
  };

  const updatedUsers = users.map(u => {
    if (u.id === sourceUserId) {
      return {
        ...u,
        status: 'disabled' as UserStatus,
        assigned_assets: {
          active_projects: [],
          active_chapters: [],
          kb_items: [],
        },
      };
    }
    if (u.id === targetUserId) {
      return {
        ...u,
        assigned_assets: {
          active_projects: [...u.assigned_assets.active_projects, ...transferredProjects],
          active_chapters: [...u.assigned_assets.active_chapters, ...transferredChapters],
          kb_items: [...u.assigned_assets.kb_items, ...transferredKb],
        },
      };
    }
    return u;
  });

  return { updatedUsers, handoverRecord };
}

export interface UserManagementPermissionResult {
  canOperate: boolean;
  canConfigurePolicy: boolean;
  isReadOnly: boolean;
  role: SystemRole | string;
  roleLabel: string;
  readOnlyNotice?: string;
}

/**
 * 8 角色权限感知与只读安全判定
 */
export function checkUserManagementPermission(role?: string): UserManagementPermissionResult {
  const normalizedRole = role?.toLowerCase() || '';
  const canOperate = normalizedRole === 'platform_admin' || normalizedRole === 'company_admin';
  const roleLabel = (SYSTEM_ROLE_LABELS as Record<string, string>)[normalizedRole] || normalizedRole || '未知角色';

  return {
    canOperate,
    canConfigurePolicy: canOperate,
    isReadOnly: !canOperate,
    role: normalizedRole,
    roleLabel,
    readOnlyNotice: canOperate
      ? undefined
      : '当前登录角色仅具备用户与角色列表查阅权限。如需新增账号、调整密码策略或停用用户，请联系公司或系统管理员。',
  };
}

/**
 * 用户列表多维检索与租户隔离过滤
 */
export function filterUsersList(
  users: UserItem[],
  filters: {
    keyword?: string;
    role?: string;
    status?: string;
    companyId?: string;
  },
  currentCompanyId?: string,
  isPlatformAdmin = false
): UserItem[] {
  let list = users;

  // 1. 租户强隔离：非平台超管严格只展示本公司用户
  if (!isPlatformAdmin && currentCompanyId) {
    list = list.filter(u => u.company_id === currentCompanyId);
  } else if (filters.companyId && filters.companyId !== 'all') {
    list = list.filter(u => u.company_id === filters.companyId);
  }

  // 2. 角色筛选
  if (filters.role && filters.role !== 'all') {
    list = list.filter(u => u.role === filters.role);
  }

  // 3. 状态筛选
  if (filters.status && filters.status !== 'all') {
    list = list.filter(u => u.status === filters.status);
  }

  // 4. 关键字检索（支持账号、姓名）
  if (filters.keyword?.trim()) {
    const q = filters.keyword.trim().toLowerCase();
    list = list.filter(
      u => u.username.toLowerCase().includes(q) || u.name.toLowerCase().includes(q)
    );
  }

  return list;
}

/**
 * 初始合成演示数据（全方位覆盖 8 大角色、多租户、带资产/无资产及已停用场景）
 */
export const INITIAL_USERS: UserItem[] = [
  {
    id: 'u_zhang',
    username: 'lead_zhang',
    name: '张建国',
    role: 'project_lead',
    company_id: 'alpha',
    status: 'active',
    email: 'zhang.jg@alpha.com',
    phone: '13800001001',
    created_at: '2026-08-10 09:30:00',
    last_login_at: '2026-10-28 08:45:00',
    assigned_assets: {
      active_projects: [
        { id: 'p_water_01', name: '2026年某省智慧水利工程数字化投标', role_in_project: '项目总负责人' },
        { id: 'p_cloud_02', name: '某央企信创协同办公系统改造', role_in_project: '商务资质统筹' },
      ],
      active_chapters: [
        { id: 'ch_arch_01', title: '3.1 总体技术架构与集成方案', project_name: '智慧水利工程' },
      ],
      kb_items: [],
    },
  },
  {
    id: 'u_li',
    username: 'writer_li',
    name: '李明',
    role: 'bid_writer',
    company_id: 'alpha',
    status: 'active',
    email: 'li.ming@alpha.com',
    phone: '13800001002',
    created_at: '2026-08-15 14:00:00',
    last_login_at: '2026-10-27 19:20:00',
    assigned_assets: {
      active_projects: [],
      active_chapters: [
        { id: 'ch_sla_02', title: '4.2 质量保证体系与售后响应SLA', project_name: '智慧水利工程' },
        { id: 'ch_sec_03', title: '5.1 网络安全等保三级整改承诺', project_name: '信创协同办公' },
      ],
      kb_items: [
        { id: 'kb_cert_01', title: '通用甲级水利工程设计资质证书', category: '资质证书' },
      ],
    },
  },
  {
    id: 'u_wang',
    username: 'auditor_wang',
    name: '王雪',
    role: 'auditor',
    company_id: 'alpha',
    status: 'active',
    email: 'wang.xue@alpha.com',
    phone: '13800001003',
    created_at: '2026-09-01 10:15:00',
    last_login_at: '2026-10-26 11:10:00',
    assigned_assets: {
      active_projects: [],
      active_chapters: [],
      kb_items: [],
    },
  },
  {
    id: 'u_admin_alpha',
    username: 'admin_alpha',
    name: '陈总',
    role: 'company_admin',
    company_id: 'alpha',
    status: 'active',
    email: 'chen.admin@alpha.com',
    phone: '13800001004',
    created_at: '2026-07-01 08:00:00',
    last_login_at: '2026-10-28 09:00:00',
    assigned_assets: {
      active_projects: [],
      active_chapters: [],
      kb_items: [],
    },
  },
  {
    id: 'u_zhao_viewer',
    username: 'viewer_zhao',
    name: '赵小明',
    role: 'viewer',
    company_id: 'alpha',
    status: 'active',
    email: 'zhao.xm@alpha.com',
    phone: '13800001005',
    created_at: '2026-09-20 16:30:00',
    last_login_at: '2026-10-25 14:00:00',
    assigned_assets: {
      active_projects: [],
      active_chapters: [],
      kb_items: [],
    },
  },
  {
    id: 'u_sun_data',
    username: 'data_sun',
    name: '孙静',
    role: 'data_admin',
    company_id: 'alpha',
    status: 'active',
    email: 'sun.j@alpha.com',
    phone: '13800001006',
    created_at: '2026-09-05 11:20:00',
    last_login_at: '2026-10-27 15:40:00',
    assigned_assets: {
      active_projects: [],
      active_chapters: [],
      kb_items: [
        { id: 'kb_case_02', title: '某省智慧水利一期优秀案例业绩合同', category: '历史业绩' },
      ],
    },
  },
  {
    id: 'u_disabled_qian',
    username: 'writer_qian',
    name: '钱程（已离职）',
    role: 'bid_writer',
    company_id: 'alpha',
    status: 'disabled',
    email: 'qian.c@alpha.com',
    phone: '13800001007',
    created_at: '2026-06-10 10:00:00',
    last_login_at: '2026-09-30 18:00:00',
    assigned_assets: {
      active_projects: [],
      active_chapters: [],
      kb_items: [],
    },
  },
  {
    id: 'u_beta_lead',
    username: 'lead_beta_zhou',
    name: '周海',
    role: 'project_lead',
    company_id: 'beta',
    status: 'active',
    email: 'zhou.h@beta.com',
    phone: '13900002001',
    created_at: '2026-08-20 09:00:00',
    last_login_at: '2026-10-28 08:30:00',
    assigned_assets: {
      active_projects: [
        { id: 'p_metro_01', name: '智慧城轨综合管控平台一体化招标', role_in_project: '标段牵头人' },
      ],
      active_chapters: [],
      kb_items: [],
    },
  },
  {
    id: 'u_superadmin',
    username: 'admin',
    name: '平台超级管理员',
    role: 'platform_admin',
    company_id: 'system',
    status: 'active',
    email: 'superadmin@icg.internal',
    phone: '18888888888',
    created_at: '2026-01-01 00:00:00',
    last_login_at: '2026-10-28 09:15:00',
    assigned_assets: {
      active_projects: [],
      active_chapters: [],
      kb_items: [],
    },
  },
];
