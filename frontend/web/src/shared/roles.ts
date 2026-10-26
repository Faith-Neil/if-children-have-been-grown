// 为什么有这个文件：基于 PRD v1.8 §2.2 与数据字典 v1.9 §4.16 单源收口八角色定义。
// 它解决什么问题：统一前后端角色码表、别名归一化、只读与编写资质集合，杜绝各模块分散硬编码角色字符串。

/**
 * PRD v1.8 §2.2 与字典 v1.9 sys_role_code 定义的 8 类标准系统角色
 */
export type SystemRole =
  | 'platform_admin'
  | 'group_admin'
  | 'company_admin'
  | 'data_admin'
  | 'project_lead'
  | 'bid_writer'
  | 'auditor'
  | 'viewer';

export const SYSTEM_ROLES: Record<string, SystemRole> = {
  PLATFORM_ADMIN: 'platform_admin',
  GROUP_ADMIN: 'group_admin',
  COMPANY_ADMIN: 'company_admin',
  DATA_ADMIN: 'data_admin',
  PROJECT_LEAD: 'project_lead',
  BID_WRITER: 'bid_writer',
  AUDITOR: 'auditor',
  VIEWER: 'viewer',
} as const;

export const SYSTEM_ROLE_LABELS: Record<SystemRole, string> = {
  platform_admin: '平台管理员',
  group_admin: '集团管理员',
  company_admin: '公司管理员',
  data_admin: '资料管理员',
  project_lead: '项目负责人',
  bid_writer: '投标编写人',
  auditor: '审核人',
  viewer: '只读成员',
};

/**
 * 历史演示角色与别名映射（与后端 project_access.py: ROLE_NORMALIZATION_MAP 完全一致）
 */
export const ROLE_NORMALIZATION_MAP: Record<string, SystemRole> = {
  platform_admin: 'platform_admin',
  group_admin: 'group_admin',
  company_admin: 'company_admin',
  data_admin: 'data_admin',
  project_lead: 'project_lead',
  lead: 'project_lead',
  manager: 'project_lead',
  bid_writer: 'bid_writer',
  writer: 'bid_writer',
  editor: 'bid_writer',
  auditor: 'auditor',
  reviewer: 'auditor',
  viewer: 'viewer',
  readonly: 'viewer',
};

/**
 * 只读角色集合：阻断一切写操作与创建动作
 */
export const READONLY_SYSTEM_ROLES = new Set<SystemRole>([
  'group_admin',
  'viewer',
  'auditor',
  'platform_admin',
]);

/**
 * 具备新建项目资质的角色
 */
export const PROJECT_CREATOR_ROLES = new Set<SystemRole>([
  'project_lead',
  'company_admin',
]);

/**
 * 具备项目编写资质的角色
 */
export const PROJECT_WRITER_ROLES = new Set<SystemRole>([
  'bid_writer',
  'project_lead',
  'company_admin',
  'data_admin',
]);

/**
 * 具备项目负责人资质的角色
 */
export const LEAD_COMPANY_ROLES = new Set<SystemRole>([
  'project_lead',
  'company_admin',
]);

/**
 * 平台管理员禁止访问的业务路由
 */
export const PLATFORM_ADMIN_FORBIDDEN_ROUTES = new Set<string>([
  'workbench',
  'library',
  'knowledge',
  'writing',
]);

/**
 * 将任意角色字符串或角色数组归一化为标准八角色代码
 */
export function normalizeSystemRole(roleOrRoles?: string | string[] | null): SystemRole {
  if (!roleOrRoles) return 'viewer';
  const rawRole = Array.isArray(roleOrRoles) ? roleOrRoles[0] : roleOrRoles;
  if (!rawRole || typeof rawRole !== 'string') return 'viewer';
  const clean = rawRole.trim().toLowerCase();
  return ROLE_NORMALIZATION_MAP[clean] ?? 'viewer';
}

/**
 * 获取标准角色的中文友好名称
 */
export function getSystemRoleLabel(roleOrRoles?: string | string[] | null): string {
  const norm = normalizeSystemRole(roleOrRoles);
  return SYSTEM_ROLE_LABELS[norm] ?? '只读成员';
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

/**
 * 判断是否开启演示模式。
 * 默认策略（未设置 VITE_DEMO）为 false，生产与关演示路径走真实账号与 RBAC 8 角色会话；
 * 仅在显式配置 VITE_DEMO=1 或 VITE_DEMO=true 时开启本地演示快捷入口。
 */
export function isDemoMode(): boolean {
  const metaEnv = (import.meta as unknown as { env?: Record<string, string | undefined> })?.env;
  if (metaEnv) {
    if (metaEnv.VITE_DEMO === '1' || metaEnv.VITE_DEMO === 'true') {
      return true;
    }
  }
  return false;
}
