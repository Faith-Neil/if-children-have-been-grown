// 为什么有这个文件：让导航与数据读取先采用后台重新核验的会话。
// 它解决什么问题：登录时的旧角色不能授权菜单，未知或无权入口不会先读取业务数据。
import type { ApplicationSession, ChapterPermissions, ProjectPermissions, Workspace } from '../shared/types';
import { isKnownRole } from '../shared/roles.ts';

export class SessionNavigationError extends Error {
  status = 403;
  code = 'NAVIGATION_FORBIDDEN';
}

export const applicationPaths: Record<string, string> = {
  workbench: '/workbench', library: '/library', knowledge: '/knowledge', writing: '/writing',
  'admin.rules': '/admin/rules', jobs: '/jobs', notifications: '/notifications',
};
export const projectTabs = ['overview', 'tender', 'parse', 'matrix', 'facts', 'editor', 'manual', 'checks', 'export', 'settings'];

function forbidden(message = '你没有该页面的权限，请联系公司管理员。'): never {
  throw new SessionNavigationError(message);
}

export function trustedApplicationSession(value: ApplicationSession): ApplicationSession {
  const roleValid = isKnownRole(value?.user?.role);

  if (!value
    || value.auth_mode !== 'authenticated'
    || value.role_mode !== 'rbac-8roles'
    || !value.user?.id || !value.user.name || !roleValid
    || !value.user.company_id || !Array.isArray(value.user.roles) || !value.user.roles.length || !value.user.primary_role
    || value.scope?.kind !== 'company' || value.scope.active_company_id !== value.user.company_id
    || !Array.isArray(value.scope.allowed_company_ids) || !value.scope.allowed_company_ids.includes(value.user.company_id)
    || !Array.isArray(value.navigation) || !Array.isArray(value.allowedActions) || !value.session) {
    forbidden('当前会话的身份或公司范围无法核验，请重新登录。');
  }
  return value;
}

// 会话请求的采纳也核对发起时的页面/请求序号，较早回包不能覆盖较新的导航。
export async function readTrustedSession(reader: () => Promise<ApplicationSession>, isCurrent: () => boolean) {
  const session = trustedApplicationSession(await reader());
  if (!isCurrent()) throw new Error('读取期间登录会话或页面已变化，旧权限未载入。');
  return session;
}

export function sessionNavigation(session: ApplicationSession | null) {
  return session?.navigation.filter(item => Object.hasOwn(applicationPaths, item.route_id)
    && applicationPaths[item.route_id] === item.path && ['read', 'write'].includes(item.access)) ?? [];
}

export function sessionAllowsRoute(session: ApplicationSession | null, routeId: string): boolean {
  return sessionNavigation(session).some(item => item.route_id === routeId);
}

export function sessionAllowsAction(session: ApplicationSession | null, action: string): boolean {
  return session?.allowedActions.includes(action) === true;
}

export function requireSessionRoute(session: ApplicationSession | null, routeId: string) {
  if (!sessionAllowsRoute(session, routeId)) forbidden();
}

export function requireSessionAction(session: ApplicationSession | null, action: string) {
  if (!sessionAllowsAction(session, action)) forbidden('当前会话没有该操作的权限，请重新核对。');
}

export function sessionHomeRoute(session: ApplicationSession): string {
  const home = sessionNavigation(session).find(item => item.path === session.home_path);
  if (!home) forbidden('当前会话没有可访问的默认首页，请联系公司管理员。');
  return home.route_id;
}

export function sessionAllowsProjectTab(session: ApplicationSession | null, projectId: string, tab: string): boolean {
  return sessionAllowsRoute(session, 'workbench') && projectTabs.includes(tab)
    && session?.project_access?.id === projectId && Array.isArray(session.project_access.route_permissions)
    && session.project_access.route_permissions.includes(`project.${tab}`);
}

export function requireProjectTab(session: ApplicationSession | null, projectId: string, tab: string) {
  if (!sessionAllowsProjectTab(session, projectId, tab)) forbidden('对象已不存在或你没有查看该页面的权限。');
}

// 新会话先收紧已显示的权限；不改正文、草稿、分工或表单依据。
// 会话没有逐条款权限，旧条款先冻结，只有本次 workspace GET 才能恢复它们。
export function workspaceWithSessionPermissions(workspace: Workspace, session: ApplicationSession, freshRequirements = false): Workspace {
  const access = session.scope.active_company_id === workspace.project.company_id
    && sessionAllowsRoute(session, 'workbench') && session.project_access?.id === workspace.project.id ? session.project_access : undefined;
  const projectFlags = ['manage_team', 'manage_project', 'manage_structure', 'prepare_sources', 'manage_sla', 'edit_facts', 'confirm_facts', 'check_all', 'export_internal'] as const;
  const permissions = Object.fromEntries(projectFlags.map(key => [key, workspace.permissions?.[key] === true && access?.permissions?.[key] === true])) as Pick<ProjectPermissions, typeof projectFlags[number]>;
  const chapterFlags = ['edit', 'confirm_plan', 'generate', 'manage_structure', 'assign', 'takeover'] as const;
  return { ...workspace,
    permissions: { ...permissions,
      check_volumes: (workspace.permissions?.check_volumes ?? []).filter(volume => access?.permissions?.check_volumes?.includes(volume)),
      export_volumes: (workspace.permissions?.export_volumes ?? []).filter(volume => access?.permissions?.export_volumes?.includes(volume)),
    },
    chapters: workspace.chapters.map(chapter => {
      const current = access?.chapters.find(item => item.id === chapter.id && item.volume === chapter.volume);
      return { ...chapter, permissions: Object.fromEntries(chapterFlags.map(key => [key, chapter.permissions?.[key] === true && current?.permissions?.[key] === true])) as ChapterPermissions };
    }),
    requirements: workspace.requirements.map(requirement => ({ ...requirement, permissions: access && freshRequirements ? requirement.permissions : { edit: false, response: false, route: false } })),
  };
}

export async function readSessionCollection<T>(session: ApplicationSession, action: 'library.read' | 'sla_templates.read', reader: () => Promise<T>, isCurrent: () => boolean): Promise<T> {
  trustedApplicationSession(session); requireSessionRoute(session, 'library'); requireSessionAction(session, action);
  if (!isCurrent()) throw new Error('当前访问权限已变化，请重新核对。');
  const result = await reader();
  if (!isCurrent()) throw new Error('读取期间访问权限、账号或公司已变化，原填写未替换，请重新核对。');
  return result;
}

export async function readAuthorizedCompanyData<P, L, T, J>(session: ApplicationSession, readers: {
  projects: () => Promise<P>; library: () => Promise<L>; templates: () => Promise<T>; jobs: () => Promise<J>;
}) {
  trustedApplicationSession(session);
  const [projects, library, templates, jobs] = await Promise.all([
    sessionAllowsRoute(session, 'workbench') && sessionAllowsAction(session, 'projects.read') ? readers.projects() : undefined,
    sessionAllowsRoute(session, 'library') && sessionAllowsAction(session, 'library.read') ? readers.library() : undefined,
    sessionAllowsRoute(session, 'library') && sessionAllowsAction(session, 'sla_templates.read') ? readers.templates() : undefined,
    sessionAllowsRoute(session, 'jobs') && sessionAllowsAction(session, 'jobs.read') ? readers.jobs() : undefined,
  ]);
  return { projects, library, templates, jobs };
}

export async function readAuthorizedProject<W>(projectId: string, tab: string, readers: {
  session: (projectId: string) => Promise<ApplicationSession>;
  workspace: (projectId: string, session: ApplicationSession) => Promise<W>;
  isCurrent?: (session: ApplicationSession) => boolean;
}) {
  if (!projectId || !projectTabs.includes(tab)) forbidden('该项目页面不存在或你没有查看权限。');
  const session = trustedApplicationSession(await readers.session(projectId));
  requireProjectTab(session, projectId, tab);
  if (readers.isCurrent && !readers.isCurrent(session)) throw new Error('读取期间页面或权限已变化，旧项目未载入。');
  const workspace = await readers.workspace(projectId, session);
  if (readers.isCurrent && !readers.isCurrent(session)) throw new Error('读取期间页面或权限已变化，旧项目未载入。');
  return { session, workspace };
}
