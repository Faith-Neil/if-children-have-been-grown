// 为什么有这个文件：执行 App 和编辑台的真实闭包，验证迟到错误与失败切页后的离开保护。
// 它解决什么问题：纯导航规则不能证明旧 401 不退出新账号，也不能证明失败重试和历史取消仍保留文字。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import * as api from '../src/shared/api.ts';
import * as sessions from '../src/app/session-navigation.ts';
import * as routes from '../src/app/app-route.ts';
import * as leaves from '../src/app/leave-guard.ts';
import * as reviews from '../src/library/library-review.ts';
import * as team from '../src/project/project-team.ts';
import * as guards from '../src/shell/route-guard.ts';
import * as conflicts from '../src/editor/editor-conflict.ts';

function sourceFunctions(filename, component) {
  const source = readFileSync(new URL(`../src/${filename}`, import.meta.url), 'utf8');
  const tree = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const root = tree.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === component);
  assert.ok(root?.body, `${component} is the actual component`);
  return { tree, root, functions: new Map(root.body.statements.filter(ts.isFunctionDeclaration).map(node => [node.name.text, node.getText(tree)])) };
}
const app = sourceFunctions('app/App.tsx', 'App');
const editor = sourceFunctions('editor/EditorPage.tsx', 'EditorPage');
const historyEffect = app.root.body.statements.find(node => ts.isExpressionStatement(node)
  && ts.isCallExpression(node.expression) && node.expression.expression.getText(app.tree) === 'useEffect'
  && node.expression.arguments[0].getText(app.tree).includes("window.addEventListener('popstate'"));
assert.ok(historyEffect, 'the actual App history effect is exercised');

const permissions = { manage_team: false, manage_project: false, manage_structure: false, prepare_sources: false, manage_sla: false, edit_facts: false, confirm_facts: false, check_all: false, export_internal: false, check_volumes: [], export_volumes: [] };
const account = { id: 'alpha-editor', name: '合成编写人', company_id: 'alpha', role: 'editor', roles: ['bid_writer'], primary_role: 'bid_writer' };
const session = () => ({
  auth_mode: 'authenticated', role_mode: 'rbac-8roles', user: account,
  scope: { kind: 'company', active_company_id: 'alpha', allowed_company_ids: ['alpha'] },
  navigation: [{ route_id: 'workbench', path: '/workbench', access: 'read' }, { route_id: 'library', path: '/library', access: 'write' }],
  allowedActions: ['projects.read', 'library.read', 'sla_templates.read'], home_path: '/workbench', session: { expires_at: null, renew_supported: false },
  project_access: { id: 'p-one', revision: 1, route_permissions: ['project.editor', 'project.matrix'], permissions, chapters: [] },
});
const workspace = () => ({ project: { id: 'p-one', company_id: 'alpha', name: '合成项目' }, revision: 1, permissions, chapters: [], requirements: [], facts: [], checks: [] });
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { resolve, promise }; };
const settle = () => new Promise(resolve => setImmediate(resolve));
const response = (status, data) => new Response(JSON.stringify(data), { status });
function runSource(context, source) {
  vm.runInContext(ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None } }).outputText, context);
}

function contextFor(names) {
  const initialPath = '/projects/p-one/editor';
  const context = { ...api, ...sessions, ...routes, ...leaves, ...reviews, ...team, ...guards, ...conflicts, Error, TypeError,
    user: account, token: 'token-A', epoch: { current: 1 }, sessionRequest: { current: 0 }, activeToken: { current: 'token-A' },
    currentSession: { current: { company_id: 'alpha', account_id: account.id } }, currentAuthorization: { current: session() },
    currentLibrary: { current: {} }, currentTemplates: { current: {} }, projectId: { current: 'p-one' },
    workspace: workspace(), tab: 'editor', nav: 'workbench', armedLeave: { current: false }, dirtyRef: { current: true }, editorDirty: true,
    addressRef: { current: initialPath }, displayedPathRef: { current: initialPath }, indexRef: { current: 0 },
    ignorePop: { current: false }, pendingLeave: { current: null }, prompting: { current: false },
    confirmations: [], errors: [], modal: {}, message: {}, loading: false, missing: null, denied: null, deniedDetails: null, refreshes: 0,
  };
  context.modal.confirm = options => { context.confirmations.push(options); };
  context.message.error = value => { context.errors.push(value); };
  for (const key of ['LibrarySnapshot', 'TemplatesSnapshot', 'Projects', 'Jobs', 'ApplicationSession', 'Token', 'User', 'Workspace', 'EditorDirty', 'CreateOpen', 'TaskDrawer', 'AccessLost', 'Denied', 'DeniedDetails', 'Loading', 'Missing', 'Nav', 'Tab', 'Busy', 'Notice', 'SourceAdvice', 'Lease', 'Versions', 'VersionsOpen']) {
    context[`set${key}`] = value => {
      const name = key[0].toLowerCase() + key.slice(1);
      context[name] = typeof value === 'function' ? value(context[name]) : value;
    };
  }
  const listeners = new Map();
  const history = { entries: [{ path: initialPath, state: { app: true, idx: 0 } }], position: 0,
    get state() { return this.entries[this.position].state; },
    pushState(state, _unused, path) { this.entries.splice(this.position + 1); this.entries.push({ path, state }); this.position++; },
    replaceState(state, _unused, path) { this.entries[this.position] = { path, state }; },
    go(step) { const next = this.position + step; if (next < 0 || next >= this.entries.length) return; this.position = next; queueMicrotask(() => listeners.get('popstate')?.()); },
  };
  context.window = { history, location: { get pathname() { return history.entries[history.position].path; } },
    addEventListener(name, callback) { listeners.set(name, callback); }, removeEventListener(name) { listeners.delete(name); },
  };
  context.refreshGlobal = async () => { context.refreshes++; };
  vm.createContext(context);
  runSource(context, names.map(name => { assert.ok(app.functions.has(name), `actual App function ${name}`); return app.functions.get(name); }).join('\n'));
  context.followRef = { current: context.followPath };
  context.attachHistory = () => runSource(context, `(${historyEffect.expression.arguments[0].getText(app.tree)})();`);
  return context;
}
const errorFunctions = ['clearCompanyData', 'logout', 'report', 'loadSession', 'readLibrary'];
const navigationFunctions = ['report', 'reportDirty', 'arrived', 'writeAddress', 'askLeave', 'requestPath', 'followPath', 'loadTab'];
function replaceLogin(context) {
  context.logout(); context.epoch.current++;
  context.activeToken.current = 'token-B'; context.token = 'token-B';
  context.user = { id: 'beta-viewer', name: '合成新账号', company_id: 'beta', role: 'viewer' };
  context.currentSession.current = { account_id: context.user.id, company_id: context.user.company_id };
  context.currentAuthorization.current = { ...session(), user: context.user };
  context.librarySnapshot = { company_id: 'beta', revision: 4, items: [{ id: 'new-company-data' }] };
}

test('a late company GET 401 cannot report or log out the subsequently logged-in account', async t => {
  const context = contextFor(errorFunctions); const started = deferred(); const held = deferred();
  t.mock.method(globalThis, 'fetch', async (path, init) => {
    assert.equal(init.headers.Authorization, 'Bearer token-A');
    if (path === '/api/v1/session') return response(200, session());
    assert.equal(path, '/api/v1/library'); started.resolve(); return held.promise;
  });
  const pending = context.readLibrary().catch(context.report); await started.promise;
  replaceLogin(context); held.resolve(response(401, { code: 'SESSION_REQUIRED', message: '旧会话失效' })); await pending;
  assert.equal(context.activeToken.current, 'token-B'); assert.deepEqual(context.errors, []);
  assert.equal(context.librarySnapshot.items[0].id, 'new-company-data');
});

test('the actual Editor history callback cannot use its late 401 to clear a new login', async t => {
  const context = contextFor(['clearCompanyData', 'logout', 'report']);
  context.chapterId = 'c-one'; context.currentLease = { current: null }; context.reload = async () => {}; context.VARIABLE_ERROR_CODES = new Set(['FACT_VARIABLE_INVALID']);
  runSource(context, ['localError', 'run', 'viewVersions'].map(name => editor.functions.get(name)).join('\n'));
  const started = deferred(); const held = deferred();
  t.mock.method(globalThis, 'fetch', async (path, init) => { assert.equal(path, '/api/chapters/c-one/versions'); assert.equal(init.headers.Authorization, 'Bearer token-A'); started.resolve(); return held.promise; });
  const pending = context.viewVersions(); await started.promise;
  replaceLogin(context); held.resolve(response(401, { error: { code: 'SESSION_REQUIRED', message: '旧版本请求失效' }, request_id: 'old-history' })); await pending;
  assert.equal(context.activeToken.current, 'token-B'); assert.deepEqual(context.errors, []);
});

test('a current session 401 still reports once and clears identity and company caches', async t => {
  const context = contextFor(errorFunctions);
  t.mock.method(globalThis, 'fetch', async () => response(401, { code: 'SESSION_REQUIRED', message: '当前会话失效', traceId: 'current-session' }));
  await context.loadSession().catch(context.report);
  assert.equal(context.activeToken.current, null); assert.equal(context.user, null); assert.equal(context.currentAuthorization.current, null);
  assert.equal(context.librarySnapshot.company_id, ''); assert.equal(context.librarySnapshot.revision, 0); assert.equal(context.librarySnapshot.items.length, 0);
  assert.deepEqual(context.errors, ['当前会话失效（追踪号 current-session）']);
});

test('a current request and an unassociated manual validation error remain visible', async t => {
  const context = contextFor(['clearCompanyData', 'logout', 'report']);
  t.mock.method(globalThis, 'fetch', async () => response(422, { code: 'FIELD_INVALID', message: '当前字段无效', traceId: 'field-check' }));
  await api.request('/api/v1/library', 'token-A').catch(context.report);
  context.report(new Error('人工核对仍未完成'));
  assert.deepEqual(context.errors, ['当前字段无效（追踪号 field-check）', '人工核对仍未完成']); assert.equal(context.activeToken.current, 'token-A');
});

for (const status of [500, 403]) test(`a failed ${status} page load retains dirty editor state and retry requires another confirmation`, async () => {
  const context = contextFor(navigationFunctions); let failure = true;
  context.loadSession = async () => { const approved = session(); context.currentAuthorization.current = approved; return approved; };
  context.request = async () => { if (failure) throw new api.ApiError(status, 'WORKSPACE_FAILED', '合成工作区读取失败'); return workspace(); };
  context.logout = () => {};
  const target = '/projects/p-one/matrix';
  context.requestPath(target); assert.equal(context.confirmations.length, 1); context.confirmations[0].onOk(); await settle();
  assert.equal(context.tab, 'editor'); assert.equal(context.dirtyRef.current, true); assert.equal(context.armedLeave.current, false);
  assert.equal(context.window.location.pathname, target);
  failure = false; context.requestPath(target); await settle();
  assert.equal(context.confirmations.length, 2); assert.equal(context.tab, 'editor'); assert.equal(context.dirtyRef.current, true);
  context.confirmations[1].onCancel?.(); assert.equal(context.tab, 'editor');
  context.requestPath(target); context.confirmations[2].onOk(); await settle();
  assert.equal(context.tab, 'matrix'); assert.equal(context.dirtyRef.current, false);
  assert.equal(context.window.history.entries.length, 2); assert.equal(context.indexRef.current, 1);
});

test('after a failed push, back to the retained editor and canceled forward preserve the history stack', async () => {
  const context = contextFor(navigationFunctions); let failure = true;
  context.loadSession = async () => { const approved = session(); context.currentAuthorization.current = approved; return approved; };
  context.request = async () => { if (failure) throw new api.ApiError(500, 'WORKSPACE_FAILED', '合成读取失败'); return workspace(); };
  context.logout = () => {}; context.attachHistory();
  context.requestPath('/projects/p-one/matrix'); context.confirmations[0].onOk(); await settle();
  failure = false; context.window.history.go(-1); await settle();
  assert.equal(context.window.location.pathname, '/projects/p-one/editor'); assert.equal(context.confirmations.length, 1);
  assert.equal(context.indexRef.current, 0); assert.equal(context.tab, 'editor'); assert.equal(context.dirtyRef.current, true);
  context.window.history.go(1); await settle(); assert.equal(context.confirmations.length, 2);
  assert.equal(context.window.history.position, 0); context.confirmations[1].onCancel();
  assert.equal(context.window.history.entries.length, 2); assert.equal(context.tab, 'editor'); assert.equal(context.dirtyRef.current, true);
  context.window.history.go(1); await settle(); assert.equal(context.confirmations.length, 3);
  context.confirmations[2].onOk(); await settle();
  assert.equal(context.window.history.position, 1); assert.equal(context.indexRef.current, 1);
  assert.equal(context.tab, 'matrix'); assert.equal(context.dirtyRef.current, false); assert.equal(context.window.history.entries.length, 2);
});

test('a confirmed forward that fails keeps the displayed editor and its next retry remains guarded', async () => {
  const context = contextFor(navigationFunctions); let failure = true;
  context.loadSession = async () => { const approved = session(); context.currentAuthorization.current = approved; return approved; };
  context.request = async () => { if (failure) throw new api.ApiError(500, 'WORKSPACE_FAILED', '合成前进读取失败'); return workspace(); };
  context.logout = () => {}; context.attachHistory();
  context.requestPath('/projects/p-one/matrix'); context.confirmations[0].onOk(); await settle();
  failure = false; context.window.history.go(-1); await settle();
  failure = true; context.window.history.go(1); await settle(); context.confirmations[1].onOk(); await settle();
  assert.equal(context.window.history.position, 1); assert.equal(context.indexRef.current, 1);
  assert.equal(context.tab, 'editor'); assert.equal(context.dirtyRef.current, true); assert.equal(context.displayedPathRef.current, '/projects/p-one/editor');
  context.requestPath('/projects/p-one/matrix'); assert.equal(context.confirmations.length, 3); context.confirmations[2].onCancel?.();
  assert.equal(context.tab, 'editor'); assert.equal(context.dirtyRef.current, true); assert.equal(context.window.history.entries.length, 2);
  failure = false; context.window.history.go(-1); await settle();
  assert.equal(context.window.history.position, 0); assert.equal(context.indexRef.current, 0); assert.equal(context.confirmations.length, 3);
  context.window.history.go(1); await settle(); context.confirmations[3].onOk(); await settle();
  assert.equal(context.tab, 'matrix'); assert.equal(context.dirtyRef.current, false); assert.equal(context.window.history.entries.length, 2);
});

test('an old mutation 403 cannot reload or freeze the new account project', async t => {
  const context = contextFor(['clearCompanyData', 'logout', 'report', 'mutate']); const started = deferred(); const held = deferred(); let reloads = 0;
  context.reload = async () => { reloads++; };
  t.mock.method(globalThis, 'fetch', async () => { started.resolve(); return held.promise; });
  const pending = context.mutate('/api/v1/projects/p-one', 'PATCH', { name: '合成更新' }).catch(error => error); await started.promise;
  replaceLogin(context); held.resolve(response(403, { code: 'PROJECT_FORBIDDEN', message: '原项目无权' })); await pending;
  assert.equal(reloads, 0); assert.deepEqual(context.errors, []); assert.equal(context.activeToken.current, 'token-B');
});
