// 为什么有这个文件：把页面地址解析成服务端已经允许的导航入口。
// 它解决什么问题：刷新、深链接和前进后退使用同一套路径，不靠页面内存记住当前位置。
import { applicationPaths, projectTabs } from './session-navigation.ts';

export type HistoryMode = 'push' | 'replace' | 'none';

export type AppRoute =
  | { kind: 'home'; path: '/' }
  | { kind: 'login'; path: '/login' }
  | { kind: 'global'; routeId: string; path: string }
  | { kind: 'project'; projectId: string; tab: string; path: string; chapterId?: string }
  | { kind: 'unknown'; path: string };

const globalRouteByPath = new Map(Object.entries(applicationPaths).map(([routeId, path]) => [path, routeId]));
// 兼容现代 RESTful 路由与规范别名
globalRouteByPath.set('/projects', 'workbench');
globalRouteByPath.set('/writing-archive', 'writing');
globalRouteByPath.set('/admin', 'admin.rules');

export function normalizePath(input: string): string {
  const raw = (input || '/').split('?')[0].split('#')[0] || '/';
  let path = raw;
  try { path = decodeURIComponent(raw); } catch { return '/__invalid__'; }
  if (!path.startsWith('/')) path = `/${path}`;
  if (path.length > 1 && path.endsWith('/')) path = path.slice(0, -1);
  return path;
}

export function globalPath(routeId: string): string {
  const path = applicationPaths[routeId];
  if (!path) throw new Error('未知导航入口。');
  return path;
}

export function projectPath(projectId: string, tab: string): string {
  return `/projects/${encodeURIComponent(projectId)}/${encodeURIComponent(tab)}`;
}

export function editorChapterPath(projectId: string, chapterId: string): string {
  return `/projects/${encodeURIComponent(projectId)}/editor/${encodeURIComponent(chapterId)}`;
}

export function parseAppPath(input: string): AppRoute {
  const path = normalizePath(input);
  if (path === '/') return { kind: 'home', path: '/' };
  if (path === '/login') return { kind: 'login', path: '/login' };
  const routeId = globalRouteByPath.get(path);
  if (routeId) return { kind: 'global', routeId, path };

  // 1. 匹配深度章节编辑器：/projects/:projectId/editor/:chapterId
  const editorMatch = /^\/projects\/([^/]+)\/editor\/([^/]+)$/.exec(path);
  if (editorMatch) {
    const projectId = editorMatch[1];
    const chapterId = editorMatch[2];
    if (projectId && projectId !== '.' && projectId !== '..' && chapterId) {
      return { kind: 'project', projectId, tab: 'editor', chapterId, path };
    }
  }

  // 2. 匹配项目标准 Tab：/projects/:projectId/:tab
  const match = /^\/projects\/([^/]+)\/([^/]+)$/.exec(path);
  if (match) {
    const projectId = match[1];
    const tab = match[2];
    if (projectId && projectId !== '.' && projectId !== '..' && (projectTabs.includes(tab) || tab === 'proposal')) {
      const actualTab = tab === 'proposal' ? 'editor' : tab;
      return { kind: 'project', projectId, tab: actualTab, path: projectPath(projectId, actualTab) };
    }
  }

  // 3. 匹配项目工作区根（缺省定向至 overview）：/projects/:projectId
  const projectOnlyMatch = /^\/projects\/([^/]+)$/.exec(path);
  if (projectOnlyMatch) {
    const projectId = projectOnlyMatch[1];
    if (projectId && projectId !== '.' && projectId !== '..' && projectId !== 'projects') {
      return { kind: 'project', projectId, tab: 'overview', path: projectPath(projectId, 'overview') };
    }
  }

  return { kind: 'unknown', path };
}

export function menuPathFor(route: AppRoute): string {
  if (route.kind === 'global') return route.path;
  return applicationPaths.workbench;
}

export function routeAfterLogin(pathname: string, homeRouteId: string): AppRoute {
  const route = parseAppPath(pathname);
  if (route.kind === 'home' || route.kind === 'login') return { kind: 'global', routeId: homeRouteId, path: globalPath(homeRouteId) };
  return route;
}

export function commitAddress(history: { pathname: string; push(path: string): void; replace(path: string): void }, path: string, mode: HistoryMode): string {
  const next = normalizePath(path);
  if (mode === 'none' || normalizePath(history.pathname) === next) return next;
  if (mode === 'push') history.push(next);
  else history.replace(next);
  return next;
}
