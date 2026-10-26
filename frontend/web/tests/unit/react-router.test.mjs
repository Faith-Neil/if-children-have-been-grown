// 为什么有这个文件：验证 D5-FE React-Router 现代化路由体系与可信守卫落地。
// 它解决什么问题：验证结构化路由配置、深链接解析、RBAC 八角色守卫（AuthGuard）拦截与脏状态离开保护。

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  APP_ROUTES,
  buildProjectPath,
  buildEditorChapterPath,
  buildGlobalPath,
  getRouteTitle,
} from '../../src/app/routes-core.ts';
import {
  parseAppPath,
  normalizePath,
  routeAfterLogin,
} from '../../src/app/app-route.ts';
import {
  checkRoutePermission,
  SYSTEM_ROLES,
  normalizeSystemRole,
} from '../../src/shell/route-guard.ts';
import { decideNavigation, leaveCopy } from '../../src/app/leave-guard.ts';

// 构造模拟标准 RBAC 会话
function createSession(role, overrides = {}) {
  const norm = normalizeSystemRole(role);
  return {
    auth_mode: 'synthetic-demo',
    role_mode: 'legacy-demo-compat',
    user: {
      id: `user-${norm}`,
      name: `测试用户（${norm}）`,
      company_id: 'company-alpha',
      role: norm === 'project_lead' ? 'manager' : norm === 'bid_writer' ? 'editor' : 'viewer',
      roles: [norm],
      primary_role: norm,
    },
    scope: {
      kind: 'company',
      active_company_id: 'company-alpha',
      allowed_company_ids: ['company-alpha'],
    },
    navigation: [
      { route_id: 'workbench', path: '/workbench', access: 'read' },
      { route_id: 'library', path: '/library', access: 'read' },
      { route_id: 'knowledge', path: '/knowledge', access: 'read' },
      { route_id: 'writing', path: '/writing', access: 'read' },
      { route_id: 'admin.rules', path: '/admin/rules', access: 'read' },
      { route_id: 'jobs', path: '/jobs', access: 'read' },
    ],
    allowedActions: ['projects.read', 'library.read'],
    home_path: norm === 'platform_admin' ? '/admin/rules' : '/workbench',
    session: { expires_at: null, renew_supported: false },
    ...overrides,
  };
}

// ----------------------------------------------------
// 1. APP_ROUTES 结构化常量与路径构造函数测试
// ----------------------------------------------------

test('APP_ROUTES defines all official paths according to Decision B2', () => {
  assert.equal(APP_ROUTES.LOGIN, '/login');
  assert.equal(APP_ROUTES.PROJECTS, '/projects');
  assert.equal(APP_ROUTES.WORKBENCH, '/workbench');
  assert.equal(APP_ROUTES.PROJECT_DETAIL, '/projects/:projectId');
  assert.equal(APP_ROUTES.PROJECT_TAB, '/projects/:projectId/:tab');
  assert.equal(APP_ROUTES.PROJECT_EDITOR_CHAPTER, '/projects/:projectId/editor/:chapterId');
  assert.equal(APP_ROUTES.LIBRARY, '/library');
  assert.equal(APP_ROUTES.KNOWLEDGE, '/knowledge');
  assert.equal(APP_ROUTES.WRITING_ARCHIVE, '/writing-archive');
  assert.equal(APP_ROUTES.WRITING, '/writing');
  assert.equal(APP_ROUTES.ADMIN, '/admin');
  assert.equal(APP_ROUTES.ADMIN_RULES, '/admin/rules');
  assert.equal(APP_ROUTES.JOBS, '/jobs');
});

test('buildProjectPath correctly formats project and tab routes with URI encoding', () => {
  assert.equal(buildProjectPath('proj-001'), '/projects/proj-001/overview');
  assert.equal(buildProjectPath('proj-001', 'tender'), '/projects/proj-001/tender');
  assert.equal(buildProjectPath('proj-001', 'matrix'), '/projects/proj-001/matrix');
  assert.equal(buildProjectPath('proj-001', 'editor'), '/projects/proj-001/editor');
  assert.equal(buildProjectPath('proj-001', 'checks'), '/projects/proj-001/checks');
  assert.equal(buildProjectPath('proj-001', 'export'), '/projects/proj-001/export');
  assert.equal(buildProjectPath('特殊 项目#1', 'checks'), '/projects/%E7%89%B9%E6%AE%8A%20%E9%A1%B9%E7%9B%AE%231/checks');
});

test('buildEditorChapterPath formats deep link into chapter editor', () => {
  const path = buildEditorChapterPath('proj-001', 'chap-302');
  assert.equal(path, '/projects/proj-001/editor/chap-302');
});

test('buildGlobalPath maps navigation domain IDs to canonical paths', () => {
  assert.equal(buildGlobalPath('workbench'), '/projects');
  assert.equal(buildGlobalPath('projects'), '/projects');
  assert.equal(buildGlobalPath('library'), '/library');
  assert.equal(buildGlobalPath('knowledge'), '/knowledge');
  assert.equal(buildGlobalPath('writing'), '/writing-archive');
  assert.equal(buildGlobalPath('writing-archive'), '/writing-archive');
  assert.equal(buildGlobalPath('admin'), '/admin');
  assert.equal(buildGlobalPath('admin.rules'), '/admin');
  assert.equal(buildGlobalPath('jobs'), '/jobs');
});

test('getRouteTitle derives informative Chinese titles for all route kinds', () => {
  assert.equal(getRouteTitle('/projects'), '投标项目工作台');
  assert.equal(getRouteTitle('/workbench'), '投标项目工作台');
  assert.equal(getRouteTitle('/login'), '系统登录');
  assert.equal(getRouteTitle('/library'), '企业资料库');
  assert.equal(getRouteTitle('/knowledge'), '知识库方案片段');
  assert.equal(getRouteTitle('/writing-archive'), '写作档案与风格规范');
  assert.equal(getRouteTitle('/admin'), '企业合规与审计中心');
  assert.equal(getRouteTitle('/jobs'), '后台异步任务中心');
  assert.equal(getRouteTitle('/projects/proj-001/overview'), '项目概览');
  assert.equal(getRouteTitle('/projects/proj-001/tender'), '招标文件');
  assert.equal(getRouteTitle('/projects/proj-001/parse'), '解析结果');
  assert.equal(getRouteTitle('/projects/proj-001/matrix'), '响应矩阵');
  assert.equal(getRouteTitle('/projects/proj-001/editor'), '方案编辑台');
  assert.equal(getRouteTitle('/projects/proj-001/editor/chap-1'), '方案编辑台');
  assert.equal(getRouteTitle('/projects/proj-001/checks'), '合规检查中心');
  assert.equal(getRouteTitle('/projects/proj-001/export'), '整本导出');
  assert.equal(getRouteTitle('/some-invalid-path'), '未知页面');
});

// ----------------------------------------------------
// 2. parseAppPath 与现代化路径别名解析测试
// ----------------------------------------------------

test('parseAppPath accurately parses modern and legacy route paths', () => {
  // 1. 登录页
  assert.deepEqual(parseAppPath('/login'), { kind: 'login', path: '/login' });

  // 2. 现代路径别名映射
  assert.deepEqual(parseAppPath('/projects'), { kind: 'global', routeId: 'workbench', path: '/projects' });
  assert.deepEqual(parseAppPath('/workbench'), { kind: 'global', routeId: 'workbench', path: '/workbench' });
  assert.deepEqual(parseAppPath('/writing-archive'), { kind: 'global', routeId: 'writing', path: '/writing-archive' });
  assert.deepEqual(parseAppPath('/writing'), { kind: 'global', routeId: 'writing', path: '/writing' });
  assert.deepEqual(parseAppPath('/admin'), { kind: 'global', routeId: 'admin.rules', path: '/admin' });
  assert.deepEqual(parseAppPath('/admin/rules'), { kind: 'global', routeId: 'admin.rules', path: '/admin/rules' });

  // 3. 项目缺省 Tab 映射为 overview
  assert.deepEqual(parseAppPath('/projects/proj-101'), {
    kind: 'project',
    projectId: 'proj-101',
    tab: 'overview',
    path: '/projects/proj-101/overview',
  });

  // 4. 标准项目各 Tab
  assert.deepEqual(parseAppPath('/projects/proj-101/tender'), {
    kind: 'project',
    projectId: 'proj-101',
    tab: 'tender',
    path: '/projects/proj-101/tender',
  });
  assert.deepEqual(parseAppPath('/projects/proj-101/matrix'), {
    kind: 'project',
    projectId: 'proj-101',
    tab: 'matrix',
    path: '/projects/proj-101/matrix',
  });

  // 5. 生成方案 proposal 别名映射为 editor
  assert.deepEqual(parseAppPath('/projects/proj-101/proposal'), {
    kind: 'project',
    projectId: 'proj-101',
    tab: 'editor',
    path: '/projects/proj-101/editor',
  });

  // 6. 深度章节编辑器：/projects/:projectId/editor/:chapterId
  assert.deepEqual(parseAppPath('/projects/proj-101/editor/chap-tech-01'), {
    kind: 'project',
    projectId: 'proj-101',
    tab: 'editor',
    chapterId: 'chap-tech-01',
    path: '/projects/proj-101/editor/chap-tech-01',
  });

  // 7. 未知路径
  assert.deepEqual(parseAppPath('/unknown-bad-url'), {
    kind: 'unknown',
    path: '/unknown-bad-url',
  });
});

test('routeAfterLogin redirects from login or root to user home path, preserves deep link', () => {
  // 从登录页或根目录登录，定向至工作台
  const fromRoot = routeAfterLogin('/', 'workbench');
  assert.equal(fromRoot.kind, 'global');
  assert.equal(fromRoot.path, '/workbench');

  const fromLogin = routeAfterLogin('/login', 'workbench');
  assert.equal(fromLogin.kind, 'global');
  assert.equal(fromLogin.path, '/workbench');

  // 从深层链接登录，保留原目标
  const fromDeep = routeAfterLogin('/projects/p-101/editor/chap-2', 'workbench');
  assert.equal(fromDeep.kind, 'project');
  assert.equal(fromDeep.projectId, 'p-101');
  assert.equal(fromDeep.tab, 'editor');
  assert.equal(fromDeep.chapterId, 'chap-2');
});

// ----------------------------------------------------
// 3. 路由守卫（AuthGuard & RoutePermission）权限矩阵测试
// ----------------------------------------------------

test('AuthGuard blocks platform_admin from business data routes', () => {
  const adminSession = createSession('platform_admin', {
    home_path: '/admin/rules',
  });

  // 访问工作台应被阻断
  const checkWorkbench = checkRoutePermission({
    session: adminSession,
    targetPath: '/projects',
  });
  assert.equal(checkWorkbench.allowed, false);
  assert.equal(checkWorkbench.code, 'ROLE_FORBIDDEN');

  // 访问企业资料库应被阻断
  const checkLibrary = checkRoutePermission({
    session: adminSession,
    targetPath: '/library',
  });
  assert.equal(checkLibrary.allowed, false);
  assert.equal(checkLibrary.code, 'ROLE_FORBIDDEN');

  // 访问项目工作区应被阻断
  const checkProject = checkRoutePermission({
    session: adminSession,
    targetPath: '/projects/proj-001/overview',
  });
  assert.equal(checkProject.allowed, false);
  assert.equal(checkProject.code, 'ROLE_FORBIDDEN');
});

test('AuthGuard allows project_lead and bid_writer to access legitimate routes', () => {
  const leadSession = createSession('project_lead');
  const writerSession = createSession('bid_writer');

  // 项目负责人访问 /projects
  const leadWb = checkRoutePermission({
    session: leadSession,
    targetPath: '/projects',
  });
  assert.equal(leadWb.allowed, true);

  // 投标编写人访问 /writing-archive
  const writerArch = checkRoutePermission({
    session: writerSession,
    targetPath: '/writing-archive',
  });
  assert.equal(writerArch.allowed, true);

  // 投标编写人访问 /library
  const writerLib = checkRoutePermission({
    session: writerSession,
    targetPath: '/library',
  });
  assert.equal(writerLib.allowed, true);
});

test('AuthGuard rejects cross-company project access', () => {
  const sessionAlpha = createSession('project_lead'); // company-alpha
  const foreignWorkspace = {
    project: {
      id: 'proj-beta-999',
      name: 'Beta公司涉密标书',
      company_id: 'company-beta', // 跨租户
    },
    chapters: [],
    requirements: [],
    facts: [],
    checks: [],
  };

  const crossCheck = checkRoutePermission({
    session: sessionAlpha,
    targetPath: '/projects/proj-beta-999/overview',
    workspace: foreignWorkspace,
  });

  assert.equal(crossCheck.allowed, false);
  assert.equal(crossCheck.code, 'SCOPE_FORBIDDEN');
  assert.match(crossCheck.reason, /跨公司访问受限/);
});

// ----------------------------------------------------
// 4. DirtyGuard 脏状态未保存离开拦截测试
// ----------------------------------------------------

test('DirtyGuard intercepts navigation when editor is dirty until confirmed', () => {
  const currentPath = '/projects/proj-001/editor';
  const targetPath = '/library';

  // 1. 编辑器干净时直接放行
  const cleanDecision = decideNavigation({
    dirty: false,
    currentPath,
    nextPath: targetPath,
    confirmed: false,
  });
  assert.equal(cleanDecision.proceed, true);

  // 2. 编辑器有脏数据未确认时拦截
  const dirtyDecision = decideNavigation({
    dirty: true,
    currentPath,
    nextPath: targetPath,
    confirmed: false,
  });
  assert.equal(dirtyDecision.proceed, false);

  // 3. 用户在弹窗确认放弃修改后放行
  const confirmedDecision = decideNavigation({
    dirty: true,
    currentPath,
    nextPath: targetPath,
    confirmed: true,
  });
  assert.equal(confirmedDecision.proceed, true);

  // 4. 确认文案符合产品要求
  assert.match(leaveCopy.title, /未保存的修改/);
  assert.match(leaveCopy.okText, /离开页面/);
  assert.match(leaveCopy.cancelText, /继续编辑/);
});
