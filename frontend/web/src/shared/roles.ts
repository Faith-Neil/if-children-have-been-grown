// 为什么有这个文件：基于 PRD v1.8 §2.2 与数据字典 v1.9 §4.16 单源收口八角色定义。
// 它解决什么问题：统一前后端角色码表、别名归一化、只读与编写资质集合，杜绝各模块分散硬编码角色字符串。

/**
 * 登录角色只有三个。项目负责人是项目成员身份，不是登录角色。
 */
export type SystemRole = 'platform_admin' | 'company_admin' | 'member';

export const SYSTEM_ROLES: Record<string, SystemRole> = {
  PLATFORM_ADMIN: 'platform_admin',
  COMPANY_ADMIN: 'company_admin',
  MEMBER: 'member',
} as const;

export const SYSTEM_ROLE_LABELS: Record<SystemRole, string> = {
  platform_admin: '平台管理员',
  company_admin: '公司管理员',
  member: '普通用户',
};

/**
 * 旧登录角色收成普通用户。与后端 project_access.ROLE_NORMALIZATION_MAP 一致。
 */
export const ROLE_NORMALIZATION_MAP: Record<string, SystemRole> = {
  platform_admin: 'platform_admin',
  company_admin: 'company_admin',
  member: 'member',
  group_admin: 'member',
  data_admin: 'member',
  project_lead: 'member',
  lead: 'member',
  manager: 'member',
  bid_writer: 'member',
  writer: 'member',
  editor: 'member',
  auditor: 'member',
  reviewer: 'member',
  viewer: 'member',
  readonly: 'member',
};

/** 平台管理员不能写投标项目。 */
export const READONLY_SYSTEM_ROLES = new Set<SystemRole>(['platform_admin']);

/** 普通用户和公司管理员可以新建项目。 */
export const PROJECT_CREATOR_ROLES = new Set<SystemRole>(['member', 'company_admin']);

export const PROJECT_WRITER_ROLES = new Set<SystemRole>(['member', 'company_admin']);

export const LEAD_COMPANY_ROLES = new Set<SystemRole>(['member', 'company_admin']);

/** 平台管理员不进入投标业务页。 */
export const PLATFORM_ADMIN_FORBIDDEN_ROUTES = new Set<string>([
  'workbench',
  'library',
  'knowledge',
  'writing',
]);

/** 普通用户和公司管理员可以新建项目。平台管理员不可以。 */
export function canCreateProject(roleOrRoles?: string | string[] | null): boolean {
  return PROJECT_CREATOR_ROLES.has(normalizeSystemRole(roleOrRoles));
}

/**
 * 将任意角色字符串或角色数组归一化为三个登录角色之一。
 */
export function normalizeSystemRole(roleOrRoles?: string | string[] | null): SystemRole {
  if (!roleOrRoles) return 'member';
  const rawRole = Array.isArray(roleOrRoles) ? roleOrRoles[0] : roleOrRoles;
  if (!rawRole || typeof rawRole !== 'string') return 'member';
  const clean = rawRole.trim().toLowerCase();
  return ROLE_NORMALIZATION_MAP[clean] ?? 'member';
}

/**
 * 获取标准角色的中文友好名称
 */
export function getSystemRoleLabel(roleOrRoles?: string | string[] | null): string {
  const norm = normalizeSystemRole(roleOrRoles);
  return SYSTEM_ROLE_LABELS[norm] ?? '普通用户';
}

/**
 * 判断是否为只读角色
 */
export function isReadonlyRole(roleOrRoles?: string | string[] | null): boolean {
  return READONLY_SYSTEM_ROLES.has(normalizeSystemRole(roleOrRoles));
}

/**
 * 判断角色是否在已知角色或别名表中
 */
export function isKnownRole(role?: string | null): boolean {
  if (!role || typeof role !== 'string') return false;
  return Object.hasOwn(ROLE_NORMALIZATION_MAP, role.trim().toLowerCase());
}

