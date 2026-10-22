// 为什么有这个文件：把页面地址解析成服务端已经允许的导航入口。
// 它解决什么问题：刷新、深链接和前进后退使用同一套路径，不靠页面内存记住当前位置。
import { applicationPaths, projectTabs } from './session-navigation.ts';

export type HistoryMode = 'push' | 'replace' | 'none';

export type AppRoute =
  | { kind: 'home'; path: '/' }
  | { kind: 'global'; routeId: string; path: string }
  | { kind: 'project'; projectId: string; tab: string; path: string }
  | { kind: 'unknown'; path: string };

const globalRouteByPath = new Map(Object.entries(applicationPaths).map(([routeId, path]) => [path, routeId]));

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

export function parseAppPath(input: string): AppRoute {
  const path = normalizePath(input);
  if (path === '/') return { kind: 'home', path: '/' };
  const routeId = globalRouteByPath.get(path);
  if (routeId) return { kind: 'global', routeId, path };
  const match = /^\/projects\/([^/]+)\/([^/]+)$/.exec(path);
  if (match) {
    const projectId = match[1];
    const tab = match[2];
    if (projectId && projectId !== '.' && projectId !== '..' && projectTabs.includes(tab)) {
      return { kind: 'project', projectId, tab, path: projectPath(projectId, tab) };
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
  if (route.kind === 'home') return { kind: 'global', routeId: homeRouteId, path: globalPath(homeRouteId) };
  return route;
}

export function commitAddress(history: { pathname: string; push(path: string): void; replace(path: string): void }, path: string, mode: HistoryMode): string {
  const next = normalizePath(path);
  if (mode === 'none' || normalizePath(history.pathname) === next) return next;
  if (mode === 'push') history.push(next);
  else history.replace(next);
  return next;
}
