// 为什么有这个文件：验证页面实际采用的可信会话、导航和数据读取守卫。
// 它解决什么问题：旧登录角色、未知入口和项目撤权不能导致先读取资料或正文。
import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, request } from '../src/shared/api.ts';
import { SessionNavigationError, readAuthorizedCompanyData, readAuthorizedProject, readSessionCollection, readTrustedSession, requireProjectTab, requireSessionAction, requireSessionRoute, sessionAllowsRoute, sessionHomeRoute, sessionNavigation, trustedApplicationSession, workspaceWithSessionPermissions } from '../src/app/session-navigation.ts';
import { chapterCan, projectCan } from '../src/project/project-team.ts';
import { companyReadSessionMatches } from '../src/library/library-review.ts';

const session = (change = {}) => ({
  auth_mode: 'authenticated', role_mode: 'rbac-8roles',
  user: { id: 'alpha-manager', name: '合成经理', company_id: 'alpha', role: 'manager', roles: ['project_lead'], primary_role: 'project_lead' },
  scope: { kind: 'company', active_company_id: 'alpha', allowed_company_ids: ['alpha'] },
  navigation: [{ route_id: 'workbench', path: '/workbench', access: 'write' }, { route_id: 'library', path: '/library', access: 'write' }, { route_id: 'jobs', path: '/jobs', access: 'read' }],
  allowedActions: ['projects.read', 'library.read', 'sla_templates.read', 'jobs.read', 'projects.create'],
  home_path: '/workbench', session: { expires_at: null, renew_supported: false }, ...change,
});
const denied = error => error instanceof SessionNavigationError && error.status === 403;
const projectPermissions = (value = true) => ({ manage_team: value, manage_project: value, manage_structure: value, prepare_sources: value, manage_sla: value, edit_facts: value, confirm_facts: value, check_all: value, export_internal: value, check_volumes: value ? ['technical', 'business'] : [], export_volumes: value ? ['technical', 'business'] : [] });
const chapterPermissions = (value = true) => ({ edit: value, confirm_plan: value, generate: value, manage_structure: value, assign: value, takeover: value });
const workspace = () => ({
  project: { id: 'p-one', company_id: 'alpha', name: '合成项目' }, revision: 9,
  permissions: projectPermissions(),
  chapters: [{ id: 'c-one', volume: 'technical', content: '已提交正文', draft: { content: '个人草稿', sequence: 3 }, permissions: chapterPermissions() }],
  requirements: [{ id: 'r-one', response: '原响应', permissions: { edit: true, route: true, response: true } }],
});
const scopedSession = (permissions = projectPermissions(), chapters = [{ id: 'c-one', volume: 'technical', permissions: chapterPermissions() }]) => session({
  project_access: { id: 'p-one', revision: 9, route_permissions: ['project.editor', 'project.settings'], permissions, chapters },
});
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };

test('the legacy manager role never grants a menu or action missing from getSession', () => {
  const current = session({ navigation: [{ route_id: 'workbench', path: '/workbench', access: 'read' }], allowedActions: ['projects.read'] });
  assert.equal(current.user.role, 'manager');
  assert.equal(sessionAllowsRoute(current, 'admin.rules'), false);
  assert.equal(sessionAllowsRoute(current, 'library'), false);
  assert.throws(() => requireSessionRoute(current, 'admin.rules'), denied);
  assert.throws(() => requireSessionAction(current, 'projects.create'), denied);
  assert.equal(sessionHomeRoute(current), 'workbench');
});

test('unknown routes, mismatched paths and unsupported access never become usable entries', () => {
  const current = session({ navigation: [
    { route_id: 'library', path: '/admin/rules', access: 'write' },
    { route_id: 'admin.rules', path: '/admin/rules', access: 'none' },
    { route_id: 'unknown', path: '/unknown', access: 'write' },
  ] });
  assert.deepEqual(sessionNavigation(current), []);
  for (const route of ['library', 'admin.rules', 'unknown', 'statistics']) assert.throws(() => requireSessionRoute(current, route), denied);
  assert.throws(() => sessionHomeRoute(current), denied);
});

test('unsupported identity modes and contradictory company scopes fail before any company read', async () => {
  let reads = 0;
  const readers = Object.fromEntries(['projects', 'library', 'templates', 'jobs'].map(key => [key, async () => { reads++; return []; }]));
  for (const current of [session({ auth_mode: 'oidc' }), session({ scope: { kind: 'company', active_company_id: 'beta', allowed_company_ids: ['beta'] } }), session({ user: { ...session().user, role: 'superuser' } })]) {
    assert.throws(() => trustedApplicationSession(current), denied);
    await assert.rejects(readAuthorizedCompanyData(current, readers), denied);
  }
  assert.equal(reads, 0);
});

test('company readers require both the matching route and the individual server action', async () => {
  const calls = [];
  const readers = Object.fromEntries(['projects', 'library', 'templates', 'jobs'].map(key => [key, async () => { calls.push(key); return key; }]));
  const hidden = session({ navigation: [] });
  assert.deepEqual(await readAuthorizedCompanyData(hidden, readers), { projects: undefined, library: undefined, templates: undefined, jobs: undefined });
  assert.deepEqual(calls, []);
  const current = session({ allowedActions: ['library.read', 'jobs.read'] });
  assert.deepEqual(await readAuthorizedCompanyData(current, readers), { projects: undefined, library: 'library', templates: undefined, jobs: 'jobs' });
  assert.deepEqual(calls, ['library', 'jobs']);
});

test('each collection keeps the items and revision returned by its own successful read', async () => {
  const result = await readAuthorizedCompanyData(session(), {
    projects: async () => ({ projects: [] }), jobs: async () => ({ jobs: [] }),
    library: async () => ({ revision: 7, items: [{ id: 'material-at-7' }] }),
    templates: async () => ({ revision: 8, items: [{ id: 'template-at-8' }] }),
  });
  assert.deepEqual(result.library, { revision: 7, items: [{ id: 'material-at-7' }] });
  assert.deepEqual(result.templates, { revision: 8, items: [{ id: 'template-at-8' }] });
});

test('project workspace is requested only after an actual scoped session permits the target page', async context => {
  const calls = [];
  context.mock.method(globalThis, 'fetch', async path => {
    calls.push(path);
    if (path === '/api/v1/session?project_id=p-one') return new Response(JSON.stringify(session({ project_access: { id: 'p-one', revision: 4, route_permissions: ['project.editor'], permissions: {}, chapters: [] } })));
    if (path === '/api/v1/projects/p-one/workspace') return new Response(JSON.stringify({ revision: 4, private_content: '仅获准才读取' }));
    throw new Error('unexpected read');
  });
  const result = await readAuthorizedProject('p-one', 'editor', {
    session: id => request(`/api/v1/session?project_id=${id}`, 'synthetic-session'),
    workspace: id => request(`/api/v1/projects/${id}/workspace`, 'synthetic-session'),
  });
  assert.equal(result.workspace.private_content, '仅获准才读取');
  assert.deepEqual(calls, ['/api/v1/session?project_id=p-one', '/api/v1/projects/p-one/workspace']);
});

test('revoked page, missing or mismatched project access and an unknown tab do not read workspace', async () => {
  let reads = 0;
  for (const project_access of [undefined, { id: 'another-project', route_permissions: ['project.editor'] }, { id: 'p-one', route_permissions: ['project.overview'] }]) {
    const current = session({ project_access });
    assert.throws(() => requireProjectTab(current, 'p-one', 'editor'), denied);
    await assert.rejects(readAuthorizedProject('p-one', 'editor', { session: async () => current, workspace: async () => { reads++; return {}; } }), denied);
  }
  let sessionReads = 0;
  await assert.rejects(readAuthorizedProject('p-one', 'unknown', { session: async () => { sessionReads++; return session(); }, workspace: async () => { reads++; return {}; } }), denied);
  assert.equal(reads, 0); assert.equal(sessionReads, 0);
});

test('a real 401 or hidden-project 404 stops before the workspace request', async context => {
  let reads = 0;
  for (const status of [401, 404]) {
    context.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ code: 'ACCESS_DENIED', message: '对象已不存在或你没有查看权限。', traceId: 'session-test' }), { status }));
    await assert.rejects(readAuthorizedProject('p-one', 'overview', { session: id => request(`/api/v1/session?project_id=${id}`, 'synthetic-session'), workspace: async () => { reads++; return {}; } }), error => error instanceof ApiError && error.status === status);
  }
  assert.equal(reads, 0);
});

test('fresh scoped permissions remove the same account manager write grants after downgrade, preserving text and draft', () => {
  const original = workspace();
  const current = scopedSession(projectPermissions(false), [{ id: 'c-one', volume: 'technical', permissions: chapterPermissions(false) }]);
  current.user = { ...current.user, role: 'viewer', roles: ['readonly'], primary_role: 'readonly' };
  assert.equal(current.user.id, session().user.id);
  const updated = workspaceWithSessionPermissions(original, current);
  assert.equal(projectCan(updated, 'manage_project'), false);
  assert.equal(projectCan(updated, 'manage_team'), false);
  assert.equal(chapterCan(updated.chapters[0], 'edit'), false);
  assert.equal(chapterCan(updated.chapters[0], 'generate'), false);
  assert.deepEqual(updated.permissions.export_volumes, []);
  assert.deepEqual(updated.requirements[0].permissions, { edit: false, response: false, route: false });
  assert.equal(updated.chapters[0].content, original.chapters[0].content);
  assert.equal(updated.chapters[0].draft, original.chapters[0].draft);
  assert.equal(updated.requirements[0].response, '原响应');
  assert.equal(chapterCan(original.chapters[0], 'edit'), true);
});

test('chapter handoff closes old edit controls even when the same account and legacy role remain', () => {
  const original = workspace();
  const current = scopedSession(projectPermissions(), [{ id: 'c-one', volume: 'technical', permissions: chapterPermissions(false) }]);
  const updated = workspaceWithSessionPermissions(original, current);
  assert.equal(current.user.role, 'manager');
  assert.equal(projectCan(updated, 'manage_project'), true);
  assert.equal(chapterCan(updated.chapters[0], 'edit'), false);
  assert.equal(chapterCan(updated.chapters[0], 'assign'), false);
  assert.equal(updated.chapters[0].draft, original.chapters[0].draft);
  assert.equal(updated.requirements[0].permissions.response, false);
  const actualRead = { ...original, requirements: [{ ...original.requirements[0], permissions: { edit: true, route: true, response: false } }] };
  assert.deepEqual(workspaceWithSessionPermissions(actualRead, current, true).requirements[0].permissions, actualRead.requirements[0].permissions);
  assert.equal(chapterCan(workspaceWithSessionPermissions(original, scopedSession(projectPermissions(), []), true).chapters[0], 'edit'), false);
  assert.equal(chapterCan(workspaceWithSessionPermissions(original, session()).chapters[0], 'edit'), false);
});

test('library and template responses arriving after a 403 cannot repopulate cleared caches even with unchanged account and epoch', async () => {
  for (const action of ['library.read', 'sla_templates.read']) {
    const approved = session(); const read = deferred();
    let authorization = approved;
    const same = { epoch: 5, company_id: 'alpha', account_id: approved.user.id };
    let cache = { items: [], revision: 0 }; let accepted = 0;
    const pending = readSessionCollection(approved, action, () => read.promise,
      () => authorization === approved && companyReadSessionMatches(same, same)).then(value => { cache = value; accepted++; });
    authorization = null; cache = { items: [], revision: 0 };
    read.resolve({ items: [{ id: 'late-private-content' }], revision: 9 });
    await assert.rejects(pending, /访问权限、账号或公司已变化/);
    assert.equal(accepted, 0); assert.deepEqual(cache, { items: [], revision: 0 });
  }
});

test('a later authorization prevents old collection results while a current result keeps its own revision pair', async () => {
  const approved = session(); let current = approved; const read = deferred();
  const pending = readSessionCollection(approved, 'library.read', () => read.promise, () => current === approved);
  current = session(); read.resolve({ items: [{ id: 'old' }], revision: 6 });
  await assert.rejects(pending, /访问权限、账号或公司已变化/);
  const actual = { items: [{ id: 'current-at-11' }], revision: 11 };
  assert.equal(await readSessionCollection(current, 'library.read', async () => actual, () => true), actual);
});

test('two fast tab requests adopt only the latest session, with no old workspace request or tab update', async () => {
  const first = deferred(); const second = deferred(); let generation = 1; let approved = null; let activeTab = 'overview'; let reads = 0;
  const navigate = async (tab, requestGeneration, reader) => {
    const result = await readAuthorizedProject('p-one', tab, {
      session: async () => { const value = await readTrustedSession(reader, () => requestGeneration === generation); approved = value; return value; },
      workspace: async () => { reads++; return workspace(); },
      isCurrent: value => requestGeneration === generation && approved === value,
    });
    activeTab = tab; return result;
  };
  const oldRequest = navigate('editor', 1, () => first.promise);
  generation = 2; const latestRequest = navigate('settings', 2, () => second.promise);
  const newest = scopedSession(projectPermissions(false)); second.resolve(newest); await latestRequest;
  first.resolve(scopedSession()); await assert.rejects(oldRequest, /旧权限未载入/);
  assert.equal(activeTab, 'settings'); assert.equal(approved, newest); assert.equal(reads, 1);
});

test('workspace arriving after a newer authorization cannot restore previous chapter permissions', async () => {
  const approved = scopedSession(); let current = approved; const read = deferred(); const started = deferred();
  const pending = readAuthorizedProject('p-one', 'editor', { session: async () => approved, workspace: () => { started.resolve(); return read.promise; }, isCurrent: value => current === value });
  await started.promise; current = scopedSession(projectPermissions(false), []); read.resolve(workspace());
  await assert.rejects(pending, /页面或权限已变化/);
});
