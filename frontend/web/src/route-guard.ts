// 为什么有这个文件：落实 PRD v1.8 §2.2 / §2.3 的八角色权限矩阵与细粒度项目分工路由守卫。
// 它解决什么问题：在页面加载与路由跳转前置拦截越权访问，彻底杜绝静默发送受保护数据请求，并提供语义化 403 与快捷切换引导。

import type { ApplicationSession, Chapter, ProjectRole, Volume, Workspace } from './types.ts';
import { parseAppPath, type AppRoute } from './app-route.ts';
import { projectTabs, sessionAllowsAction, sessionAllowsProjectTab, sessionAllowsRoute } from './session-navigation.ts';

/**
 * PRD v1.8 §2.2 定义的 8 类标准系统角色
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
 * 角色映射别名表，双向向后兼容历史 manager / editor / readonly / reviewer 等
 */
const ROLE_NORMALIZATION_MAP: Record<string, SystemRole> = {
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
 * 判断是否有权新建项目
 */
export function canCreateProject(roleOrRoles?: string | string[] | null): boolean {
  return PROJECT_CREATOR_ROLES.has(normalizeSystemRole(roleOrRoles));
}

/**
 * 细粒度章节编辑鉴权参数
 */
export interface ChapterEditGuardParams {
  role?: string | string[] | null;
  userId: string;
  chapter: Pick<Chapter, 'id' | 'volume' | 'assignee_id'>;
  workspace: Pick<Workspace, 'permissions' | 'team'>;
}

export interface ChapterEditGuardResult {
  allowed: boolean;
  reason?: string;
  reasonType?: 'readonly' | 'not_member' | 'not_assigned' | 'wrong_volume';
}

/**
 * 细粒度章节编辑鉴权（项目负责人 vs 分册负责人 vs 编写人分配）
 */
export function checkChapterEditPermission(params: ChapterEditGuardParams): ChapterEditGuardResult {
  const { role, userId, chapter, workspace } = params;
  const norm = normalizeSystemRole(role);
  const roleLabel = SYSTEM_ROLE_LABELS[norm];

  if (READONLY_SYSTEM_ROLES.has(norm)) {
    return {
      allowed: false,
      reason: `抱歉，您当前的角色（${roleLabel}）处于只读状态，无权编辑章节正文。`,
      reasonType: 'readonly',
    };
  }

  const member = workspace.team?.members.find(m => m.user_id === userId);
  if (!member) {
    return {
      allowed: false,
      reason: '抱歉，您不是当前项目的成员，无权编辑本章节。',
      reasonType: 'not_member',
    };
  }

  if (member.project_role === 'readonly') {
    return {
      allowed: false,
      reason: '抱歉，您在当前项目中为只读成员，无权编辑章节正文。',
      reasonType: 'readonly',
    };
  }

  // 1. 项目负责人：可以编辑全部分册全部章节
  if (member.project_role === 'lead') {
    return { allowed: true };
  }

  // 2. 分册负责人：可以编辑本分册内所有章节
  const isVolumeOwner = workspace.team?.volumes.some(
    v => v.volume === chapter.volume && v.owner_id === userId
  );
  if (isVolumeOwner && member.volumes.includes(chapter.volume)) {
    return { allowed: true };
  }

  // 3. 编写人：被分配到该章节，且参与该分册
  if (chapter.assignee_id === userId && member.volumes.includes(chapter.volume)) {
    return { allowed: true };
  }

  if (chapter.assignee_id === userId && !member.volumes.includes(chapter.volume)) {
    const volName = chapter.volume === 'technical' ? '技术分册' : '商务分册';
    return {
      allowed: false,
      reason: `抱歉，您未分配参与${volName}，无权编辑本分册章节。`,
      reasonType: 'wrong_volume',
    };
  }

  return {
    allowed: false,
    reason: `抱歉，您当前未被分配负责章节【${chapter.id}】，仅被分配编写人或分册负责人可编辑。`,
    reasonType: 'not_assigned',
  };
}

/**
 * 路由守卫检查入参
 */
export interface RoutePermissionCheckParams {
  session: ApplicationSession | null;
  targetPath: string;
  workspace?: Workspace | null;
  action?: 'read' | 'write' | 'create_project' | 'edit_chapter' | string;
  chapterId?: string;
}

/**
 * 路由守卫判定结果
 */
export interface RoutePermissionResult {
  allowed: boolean;
  code?: 'UNAUTHENTICATED' | 'ROLE_FORBIDDEN' | 'SCOPE_FORBIDDEN' | 'PROJECT_FORBIDDEN' | 'TAB_FORBIDDEN' | 'CHAPTER_FORBIDDEN' | 'READONLY_FORBIDDEN' | 'ROUTE_NOT_FOUND';
  reason?: string;
  role?: SystemRole;
  roleLabel?: string;
  contextInfo?: {
    projectName?: string;
    roleName?: string;
    path?: string;
    retainedMessage?: string;
  };
  suggestedAction?: 'login' | 'switch_role' | 'back_workbench' | 'contact_admin';
}

/**
 * 构造清晰语义化的 403 拦截原因
 */
export function formatForbiddenReason(params: {
  role?: string | string[] | null;
  path: string;
  action?: string;
  serverMessage?: string;
  tab?: string;
}): string {
  const norm = normalizeSystemRole(params.role);
  const roleLabel = SYSTEM_ROLE_LABELS[norm] ?? '当前身份';

  if (params.serverMessage) {
    return `抱歉，您当前的角色（${roleLabel}）无权访问：${params.serverMessage}`;
  }

  if (norm === 'platform_admin') {
    return `抱歉，您当前的角色（${roleLabel}）仅限管理平台级服务、模型与审计，不可访问公司业务数据与投标项目。`;
  }

  if (norm === 'group_admin') {
    if (params.action && params.action !== 'read') {
      return `抱歉，您当前的角色（${roleLabel}）仅具备全站跨公司只读权限，不能执行写操作或创建项目。`;
    }
  }

  if (norm === 'viewer' || norm === 'auditor') {
    if (params.action && params.action !== 'read') {
      return `抱歉，您当前的角色（${roleLabel}）处于只读状态，无权修改业务数据。`;
    }
  }

  if (norm === 'data_admin') {
    if (params.action === 'create_project' || params.action === 'projects.create') {
      return `抱歉，您当前的角色（${roleLabel}）专职负责公司资料库与模板维护，无权新建投标项目。`;
    }
  }

  if (norm === 'bid_writer') {
    if (params.action === 'create_project' || params.action === 'projects.create') {
      return `抱歉，您当前的角色（${roleLabel}）无权新建投标项目，请联系项目负责人或公司管理员办理。`;
    }
    if (params.tab === 'settings' || params.path.endsWith('/settings')) {
      return `抱歉，您当前的角色（${roleLabel}）无权修改项目设置与团队分工，仅项目负责人可操作。`;
    }
  }

  return `抱歉，您当前的角色（${roleLabel}）无权访问此页面（${params.path}），请联系公司管理员。`;
}

/**
 * 核心路由守卫准入检查函数
 * 纯逻辑函数，绝不发起任何 fetch / request API 调用
 */
export function checkRoutePermission(params: RoutePermissionCheckParams): RoutePermissionResult {
  const { session, targetPath, workspace, action, chapterId } = params;

  // 1. 未登录状态拦截
  if (!session || !session.user) {
    return {
      allowed: false,
      code: 'UNAUTHENTICATED',
      reason: '请先登录系统再访问受保护页面。',
      suggestedAction: 'login',
    };
  }

  const role = session.user.primary_role || session.user.role || session.user.roles;
  const normRole = normalizeSystemRole(role);
  const roleLabel = SYSTEM_ROLE_LABELS[normRole];

  const route = parseAppPath(targetPath);

  // 2. 未知路由拦截
  if (route.kind === 'unknown') {
    return {
      allowed: false,
      code: 'ROUTE_NOT_FOUND',
      role: normRole,
      roleLabel,
      reason: `未找到与 ${targetPath} 对应的页面。`,
      contextInfo: { path: targetPath, roleName: roleLabel },
      suggestedAction: 'back_workbench',
    };
  }

  // 3. 根目录自动放行
  if (route.kind === 'home') {
    return { allowed: true, role: normRole, roleLabel };
  }

  // 4. 全局页面守卫 (/workbench, /library, /jobs, /knowledge, /writing, /admin/rules)
  if (route.kind === 'global') {
    // 4.1 平台管理员隔离：不得访问业务数据页面
    if (normRole === 'platform_admin' && PLATFORM_ADMIN_FORBIDDEN_ROUTES.has(route.routeId)) {
      const reason = formatForbiddenReason({ role: normRole, path: targetPath, action });
      return {
        allowed: false,
        code: 'ROLE_FORBIDDEN',
        role: normRole,
        roleLabel,
        reason,
        contextInfo: { path: targetPath, roleName: roleLabel },
        suggestedAction: 'switch_role',
      };
    }

    // 4.2 会话导航声明准入校验
    if (!sessionAllowsRoute(session, route.routeId)) {
      const reason = formatForbiddenReason({ role: normRole, path: targetPath, action });
      return {
        allowed: false,
        code: 'ROLE_FORBIDDEN',
        role: normRole,
        roleLabel,
        reason,
        contextInfo: { path: targetPath, roleName: roleLabel },
        suggestedAction: 'switch_role',
      };
    }

    // 4.3 写动作前置阻断 (如新建项目、资料写入)
    if (action === 'create_project' || action === 'projects.create') {
      if (isReadonlyRole(normRole)) {
        return {
          allowed: false,
          code: 'READONLY_FORBIDDEN',
          role: normRole,
          roleLabel,
          reason: `抱歉，您当前的角色（${roleLabel}）仅具备只读权限，不能新建投标项目。`,
          contextInfo: { path: targetPath, roleName: roleLabel },
          suggestedAction: 'switch_role',
        };
      }
      if (!canCreateProject(normRole)) {
        return {
          allowed: false,
          code: 'ROLE_FORBIDDEN',
          role: normRole,
          roleLabel,
          reason: `抱歉，您当前的角色（${roleLabel}）无权新建投标项目，仅项目负责人和公司管理员可新建项目。`,
          contextInfo: { path: targetPath, roleName: roleLabel },
          suggestedAction: 'contact_admin',
        };
      }
    }

    return { allowed: true, role: normRole, roleLabel };
  }

  // 5. 项目工作区路由守卫 (/projects/:projectId/:tab)
  if (route.kind === 'project') {
    // 5.1 平台管理员阻断：完全禁止访问项目业务数据
    if (normRole === 'platform_admin') {
      return {
        allowed: false,
        code: 'ROLE_FORBIDDEN',
        role: normRole,
        roleLabel,
        reason: '抱歉，平台管理员不可访问项目业务内容与标书详情。',
        contextInfo: { path: targetPath, roleName: roleLabel },
        suggestedAction: 'switch_role',
      };
    }

    // 5.2 跨公司数据隔离核验 (若工作区已加载)
    if (workspace && workspace.project && workspace.project.company_id !== session.scope.active_company_id) {
      return {
        allowed: false,
        code: 'SCOPE_FORBIDDEN',
        role: normRole,
        roleLabel,
        reason: '跨公司访问受限：您无法访问其他公司的投标项目。',
        contextInfo: { projectName: workspace.project.name, path: targetPath, roleName: roleLabel },
        suggestedAction: 'back_workbench',
      };
    }

    // 5.3 项目成员与具体 Tab 细粒度校验
    if (session.project_access) {
      // 检查是否具备当前项目的访问权限
      if (session.project_access.id !== route.projectId) {
        return {
          allowed: false,
          code: 'PROJECT_FORBIDDEN',
          role: normRole,
          roleLabel,
          reason: '抱歉，您未加入该投标项目，无权查看本项目内容。',
          contextInfo: { path: targetPath, roleName: roleLabel },
          suggestedAction: 'back_workbench',
        };
      }

      // 检查当前 Tab 是否在服务端授权的 route_permissions 中
      if (!sessionAllowsProjectTab(session, route.projectId, route.tab)) {
        const reason = formatForbiddenReason({ role: normRole, path: targetPath, tab: route.tab });
        return {
          allowed: false,
          code: 'TAB_FORBIDDEN',
          role: normRole,
          roleLabel,
          reason,
          contextInfo: {
            projectName: workspace?.project?.name,
            path: targetPath,
            roleName: roleLabel,
          },
          suggestedAction: 'back_workbench',
        };
      }
    }

    // 5.4 编辑台章节级细粒度分工校验
    if (route.tab === 'editor' && chapterId && workspace) {
      const chapter = workspace.chapters.find(c => c.id === chapterId);
      if (chapter && action === 'edit_chapter') {
        const chapterCheck = checkChapterEditPermission({
          role: normRole,
          userId: session.user.id,
          chapter,
          workspace,
        });
        if (!chapterCheck.allowed) {
          return {
            allowed: false,
            code: 'CHAPTER_FORBIDDEN',
            role: normRole,
            roleLabel,
            reason: chapterCheck.reason,
            contextInfo: {
              projectName: workspace.project.name,
              path: targetPath,
              roleName: roleLabel,
              retainedMessage: `章节【${chapter.id}】处于只读查看状态，写入口已关闭。`,
            },
            suggestedAction: 'back_workbench',
          };
        }
      }
    }

    return {
      allowed: true,
      role: normRole,
      roleLabel,
      contextInfo: {
        projectName: workspace?.project?.name,
        roleName: roleLabel,
        path: targetPath,
      },
    };
  }

  return { allowed: true, role: normRole, roleLabel };
}
