// 为什么有这个文件：同一项目里切换页签不应重新拉取整份工作区。
// 它解决什么问题：页签点击会把章节正文和覆盖行再读一遍，并闪出整页加载。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import * as api from '../../src/shared/api.ts';
import * as sessions from '../../src/app/session-navigation.ts';
import * as routes from '../../src/app/app-route.ts';
import * as leaves from '../../src/app/leave-guard.ts';
import * as team from '../../src/project/project-team.ts';
import * as guards from '../../src/shell/route-guard.ts';

function appFunctions(names) {
  const source = readFileSync(new URL('../../src/app/App.tsx', import.meta.url), 'utf8');
  const tree = ts.createSourceFile('App.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const root = tree.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === 'App');
  assert.ok(root?.body, 'App is the actual component');
  const functions = new Map(root.body.statements.filter(ts.isFunctionDeclaration).map(node => [node.name.text, node.getText(tree)]));
  return names.map(name => {
    assert.ok(functions.has(name), `actual App function ${name}`);
    return functions.get(name);
  }).join('\n');
}

const permissions = {
  manage_team: false, manage_project: false, manage_structure: false, prepare_sources: false, manage_sla: false,
  edit_facts: false, confirm_facts: false, check_all: false, export_internal: false, check_volumes: [], export_volumes: [],
};

function sessionFor(projectId) {
  return {
    auth_mode: 'authenticated', role_mode: 'rbac-3roles',
    user: { id: 'alpha-editor', name: '合成编写人', company_id: 'alpha', role: 'editor', roles: ['bid_writer'], primary_role: 'bid_writer' },
    scope: { kind: 'company', active_company_id: 'alpha', allowed_company_ids: ['alpha'] },
    navigation: [{ route_id: 'workbench', path: '/workbench', access: 'read' }],
    allowedActions: ['projects.read'], home_path: '/workbench', session: { expires_at: null, renew_supported: false },
    project_access: {
      id: projectId, revision: 1,
      route_permissions: ['project.overview', 'project.tender', 'project.analyze', 'project.editor', 'project.export', 'project.settings'],
      permissions, chapters: [],
    },
  };
}

function workspaceFor(projectId) {
  return { project: { id: projectId, company_id: 'alpha', name: '合成项目' }, revision: 4, permissions, chapters: [{ id: 'c1', content: '正文' }], coverage_rows: [{ requirement_id: 'r1' }], requirements: [], facts: [], checks: [] };
}

function harness() {
  const reads = [];
  const loadingWrites = [];
  const initialPath = '/projects/p-one/editor';
  const loaded = workspaceFor('p-one');
  const context = {
    ...api, ...sessions, ...routes, ...leaves, ...team, ...guards, Error,
    reads, loadingWrites, loaded,
    user: sessionFor('p-one').user, token: 'token-A', epoch: { current: 1 }, sessionRequest: { current: 0 },
    activeToken: { current: 'token-A' }, currentSession: { current: { company_id: 'alpha', account_id: 'alpha-editor' } },
    currentAuthorization: { current: sessionFor('p-one') }, projectId: { current: 'p-one' },
    workspace: loaded, tab: 'editor', nav: 'workbench', collapsed: false,
    armedLeave: { current: false }, dirtyRef: { current: false }, editorDirty: false,
    addressRef: { current: initialPath }, displayedPathRef: { current: initialPath }, indexRef: { current: 0 },
    ignorePop: { current: false }, pendingLeave: { current: null }, prompting: { current: false },
    loading: false, missing: null, denied: null, deniedDetails: null, accessLost: false, companyDetailId: null,
    modal: { confirm() {} }, message: { error() {}, success() {}, warning() {} },
  };
  for (const key of ['Workspace', 'Loading', 'Missing', 'AccessLost', 'Nav', 'Tab', 'Denied', 'DeniedDetails', 'EditorDirty', 'CompanyDetailId', 'Collapsed']) {
    context[`set${key}`] = value => {
      const name = key[0].toLowerCase() + key.slice(1);
      context[name] = typeof value === 'function' ? value(context[name]) : value;
    };
  }
  context.setLoading = value => {
    const next = typeof value === 'function' ? value(context.loading) : value;
    loadingWrites.push(next);
    context.loading = next;
  };
  context.loadSession = async (_token, selected) => {
    const approved = sessionFor(selected || context.projectId.current || 'p-one');
    context.currentAuthorization.current = approved;
    return approved;
  };
  context.request = async path => {
    reads.push(String(path));
    const id = /\/projects\/([^/]+)/.exec(String(path))?.[1];
    return workspaceFor(id ? decodeURIComponent(id) : 'p-one');
  };
  context.refreshGlobal = async () => {};
  context.logout = () => {};
  context.sessionStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
  const history = {
    entries: [{ path: initialPath, state: { app: true, idx: 0 } }], position: 0,
    get state() { return this.entries[this.position].state; },
    pushState(state, _title, path) { this.entries.splice(this.position + 1); this.entries.push({ path, state }); this.position += 1; },
    replaceState(state, _title, path) { this.entries[this.position] = { path, state }; },
  };
  context.window = { history, location: { get pathname() { return history.entries[history.position].path; } } };
  vm.createContext(context);
  const source = appFunctions(['report', 'arrived', 'writeAddress', 'askLeave', 'requestPath', 'followPath', 'loadTab', 'openProject', 'reload']);
  vm.runInContext(ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None } }).outputText, context);
  return context;
}

const settle = () => new Promise(resolve => setImmediate(resolve));
const workspaceReads = reads => reads.filter(path => path.includes('/workspace'));

test('a tab click in the loaded project updates the address and does not read the workspace', async () => {
  const context = harness();
  context.requestPath('/projects/p-one/analyze');
  await settle();
  assert.deepEqual(workspaceReads(context.reads), []);
  assert.deepEqual(context.loadingWrites, []);
  assert.equal(context.loading, false);
  assert.equal(context.tab, 'analyze');
  assert.equal(context.window.location.pathname, '/projects/p-one/analyze');
  assert.equal(context.workspace, context.loaded);
});

test('opening a different project still reads that project workspace', async () => {
  const context = harness();
  context.currentAuthorization.current = sessionFor('p-two');
  context.requestPath('/projects/p-two/tender');
  await settle();
  assert.deepEqual(workspaceReads(context.reads), ['/api/v1/projects/p-two/workspace']);
  assert.equal(context.loadingWrites.includes(true), true);
  assert.equal(context.workspace.project.id, 'p-two');
  assert.equal(context.tab, 'tender');
});

test('reload still reads the workspace for the open project', async () => {
  const context = harness();
  await context.reload();
  assert.deepEqual(workspaceReads(context.reads), ['/api/v1/projects/p-one/workspace']);
});
