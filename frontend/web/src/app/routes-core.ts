// 为什么有这个文件：提取纯路由模型、路径构造与标题推导纯逻辑。
// 它解决什么问题：支持 Node.js 权威单元测试零 JSX 依赖直接加载运行，践行逻辑与视图分离规范。

import { normalizePath, parseAppPath } from './app-route.ts';

/**
 * 结构化路由路径定义（对齐用户审计与官方拍板 B2）
 */
export const APP_ROUTES = {
  ROOT: '/',
  LOGIN: '/login',
  PROJECTS: '/projects',
  WORKBENCH: '/workbench', // 兼容历史别名
  PROJECT_DETAIL: '/projects/:projectId',
  PROJECT_TAB: '/projects/:projectId/:tab',
  PROJECT_EDITOR_CHAPTER: '/projects/:projectId/editor/:chapterId',
  LIBRARY: '/library',
  KNOWLEDGE: '/knowledge',
  WRITING_ARCHIVE: '/writing-archive',
  WRITING: '/writing', // 兼容历史别名
  ADMIN: '/admin',
  ADMIN_RULES: '/admin/rules', // 兼容历史别名
  JOBS: '/jobs',
  NOTIFICATIONS: '/notifications',
} as const;

export type AppRouteKey = keyof typeof APP_ROUTES;

/**
 * 构造项目标准工作区路径
 */
export function buildProjectPath(projectId: string, tab = 'overview'): string {
  return `/projects/${encodeURIComponent(projectId)}/${encodeURIComponent(tab)}`;
}

/**
 * 构造编辑器章节深链接路径
 */
export function buildEditorChapterPath(projectId: string, chapterId: string): string {
  return `/projects/${encodeURIComponent(projectId)}/editor/${encodeURIComponent(chapterId)}`;
}

/**
 * 将业务领域 ID 映射到规范化全局路由路径
 */
export function buildGlobalPath(routeId: string): string {
  switch (routeId) {
    case 'workbench':
    case 'projects':
      return APP_ROUTES.PROJECTS;
    case 'library':
      return APP_ROUTES.LIBRARY;
    case 'knowledge':
      return APP_ROUTES.KNOWLEDGE;
    case 'writing':
    case 'writing-archive':
      return APP_ROUTES.WRITING_ARCHIVE;
    case 'admin':
    case 'admin.rules':
      return APP_ROUTES.ADMIN;
    case 'jobs':
      return APP_ROUTES.JOBS;
    case 'notifications':
      return APP_ROUTES.NOTIFICATIONS;
    default:
      return APP_ROUTES.PROJECTS;
  }
}

/**
 * 获取路径对应的中文可读标题（用于顶栏与面包屑）
 */
export function getRouteTitle(pathname: string): string {
  const norm = normalizePath(pathname);
  if (norm === '/' || norm === APP_ROUTES.PROJECTS || norm === APP_ROUTES.WORKBENCH) return '投标项目工作台';
  if (norm === APP_ROUTES.LOGIN) return '系统登录';
  if (norm === APP_ROUTES.LIBRARY) return '企业资料库';
  if (norm === APP_ROUTES.KNOWLEDGE) return '知识库方案片段';
  if (norm === APP_ROUTES.WRITING_ARCHIVE || norm === APP_ROUTES.WRITING) return '写作档案与风格规范';
  if (norm === APP_ROUTES.ADMIN || norm === APP_ROUTES.ADMIN_RULES) return '企业合规与审计中心';
  if (norm === APP_ROUTES.JOBS) return '后台异步任务中心';
  if (norm === APP_ROUTES.NOTIFICATIONS) return '站内提醒';
  if (norm.startsWith('/projects/')) {
    const route = parseAppPath(norm);
    if (route.kind === 'project') {
      const tabTitles: Record<string, string> = {
        overview: '项目概览',
        tender: '招标文件',
        parse: '解析结果',
        matrix: '响应矩阵',
        facts: '项目事实表',
        proposal: '生成方案',
        editor: '方案编辑台',
        manual: '人工处理队列',
        checks: '合规检查中心',
        export: '整本导出',
        settings: '项目设置',
      };
      return tabTitles[route.tab] ?? '项目工作区';
    }
  }
  return '未知页面';
}
