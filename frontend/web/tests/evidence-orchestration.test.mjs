// 为什么有这个文件：执行矩阵与应用的真实闭包，核对证据抽屉撤权和补录导航。
// 它解决什么问题：旧行对象不能继续授权保存，补录也不能生成绕过离开守卫的历史项。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import * as evidence from '../src/library/evidence-drawer.ts';
import * as api from '../src/shared/api.ts';
import * as routes from '../src/app/app-route.ts';
import * as leaves from '../src/app/leave-guard.ts';
import * as sessions from '../src/app/session-navigation.ts';
import * as team from '../src/project/project-team.ts';

function component(filename, name) {
  const source = readFileSync(new URL(`../src/${filename}`, import.meta.url), 'utf8');
  const tree = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const node = tree.statements.find(value => ts.isFunctionDeclaration(value) && value.name?.text === name);
  assert.ok(node?.body);
  return { tree, node, functions: new Map(node.body.statements.filter(ts.isFunctionDeclaration).map(value => [value.name.text, value.getText(tree)])) };
}
const matrix = component('project/ProjectPages.tsx', 'MatrixPage');
const app = component('app/App.tsx', 'App');
let drawer;
function findDrawer(node) { if (ts.isJsxSelfClosingElement(node) && node.tagName.getText(matrix.tree) === 'EvidenceDrawer') drawer = node; ts.forEachChild(node, findDrawer); }
findDrawer(matrix.node); assert.ok(drawer);
const drawerExpression = name => drawer.attributes.properties.find(node => node.name?.getText(matrix.tree) === name).initializer.expression.getText(matrix.tree);
const evaluate = (context, source) => vm.runInContext(ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None } }).outputText, context);
const settle = () => new Promise(resolve => setImmediate(resolve));
const row = { id: 'row-one', evidence_ids: [], permissions: { response: true, route: true } };
const workspace = () => ({ revision: 7, project: { id: 'p-one', company_id: 'alpha' }, requirements: [row], chapters: [], facts: [], checks: [] });

function matrixContext() {
  const calls = [];
  const context = { ...evidence, workspace: workspace(), evidenceItem: null, evidenceIds: [], openedEvidence: null, evidenceStale: false,
    mutate: async (...args) => { calls.push(args); }, calls,
  };
  for (const key of ['EvidenceItem', 'EvidenceIds', 'OpenedEvidence', 'EvidenceStale']) context[`set${key}`] = value => { context[key[0].toLowerCase() + key.slice(1)] = value; };
  vm.createContext(context); evaluate(context, [...matrix.functions.values()].join('\n')); context.openEvidence(row);
  return context;
}

test('same-version row revocation disables the actual drawer prop and prevents the actual save callback', async () => {
  const context = matrixContext(); context.evidenceIds = ['e-one'];
  context.workspace = { ...context.workspace, requirements: [{ ...row, permissions: { response: false, route: false } }] };
  assert.equal(context.evidenceItem.permissions.response, true); // 打开时的对象确实还持有旧许可。
  assert.equal(evaluate(context, drawerExpression('canWrite')), false);
  await context.saveEvidence(); assert.equal(context.calls.length, 0);
  assert.equal(context.evidenceItem.id, 'row-one'); assert.deepEqual(context.evidenceIds, ['e-one']);
});

test('a removed current row cannot leave the actual drawer writable or issue a write', async () => {
  const context = matrixContext(); context.workspace = { ...context.workspace, requirements: [] };
  assert.equal(evaluate(context, drawerExpression('canWrite')), false);
  await context.saveEvidence(); assert.equal(context.calls.length, 0);
});

test('a current permitted row saves its selection, while a newer version preserves pending input and blocks save', async () => {
  const permitted = matrixContext(); permitted.evidenceIds = ['e-one'];
  assert.equal(evaluate(permitted, drawerExpression('canWrite')), true);
  await permitted.saveEvidence(); assert.equal(permitted.calls.length, 1); assert.equal(permitted.calls[0][2].evidence_ids[0], 'e-one'); assert.equal(permitted.evidenceItem, null);
  const changed = matrixContext(); changed.evidenceIds = ['e-local']; changed.workspace = { ...changed.workspace, revision: 8 };
  await changed.saveEvidence(); assert.equal(changed.calls.length, 0); assert.equal(changed.evidenceStale, true); assert.deepEqual(changed.evidenceIds, ['e-local']);
});

test('the actual supplement callback uses application history, then dirty editor back/cancel keeps indexed forward history', async () => {
  const initial = '/projects/p-one/matrix'; const listeners = new Map(); const confirmations = [];
  const approved = { auth_mode: 'authenticated', role_mode: 'rbac-8roles', user: { id: 'alpha-editor', name: '合成账号', company_id: 'alpha', role: 'editor', roles: ['bid_writer'], primary_role: 'bid_writer' }, scope: { kind: 'company', active_company_id: 'alpha', allowed_company_ids: ['alpha'] }, navigation: [{ route_id: 'workbench', path: '/workbench', access: 'read' }, { route_id: 'library', path: '/library', access: 'write' }], allowedActions: ['library.read'], home_path: '/workbench', session: {}, project_access: { id: 'p-one', revision: 7, route_permissions: ['project.editor'], permissions: {}, chapters: [] } };
  const context = { ...api, ...routes, ...leaves, ...sessions, ...team, Error, PopStateEvent: class {},
    workspace: workspace(), projectId: { current: 'p-one' }, activeToken: { current: 'token-A' }, currentAuthorization: { current: approved }, epoch: { current: 1 },
    addressRef: { current: initial }, displayedPathRef: { current: initial }, indexRef: { current: 0 }, dirtyRef: { current: false }, armedLeave: { current: false },
    ignorePop: { current: false }, pendingLeave: { current: null }, prompting: { current: false }, modal: { confirm: value => confirmations.push(value) }, message: { error() {} }, confirmations,
    loadSession: async () => { context.currentAuthorization.current = approved; return approved; }, request: async () => workspace(), refreshGlobal: async () => {},
  };
  for (const key of ['Workspace', 'Loading', 'Missing', 'AccessLost', 'Nav', 'Tab', 'Denied', 'EditorDirty']) context[`set${key}`] = value => { const name = key[0].toLowerCase() + key.slice(1); context[name] = typeof value === 'function' ? value(context[name]) : value; };
  const history = { entries: [{ path: initial, state: { app: true, idx: 0 } }], position: 0,
    get state() { return this.entries[this.position].state; },
    pushState(state, _title, path) { this.entries.splice(this.position + 1); this.entries.push({ state, path }); this.position++; },
    replaceState(state, _title, path) { this.entries[this.position] = { state, path }; },
    go(step) { const next = this.position + step; if (next < 0 || next >= this.entries.length) return; this.position = next; queueMicrotask(() => listeners.get('popstate')?.()); },
  };
  context.window = { history, location: { get pathname() { return history.entries[history.position].path; } }, addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: name => listeners.delete(name), dispatchEvent: () => listeners.get('popstate')?.() };
  vm.createContext(context);
  evaluate(context, ['navigate', 'requestPath', 'followPath', 'loadNav', 'loadTab', 'openProject', 'showMissing', 'writeAddress', 'arrived', 'reportDirty', 'askLeave', 'report'].map(name => app.functions.get(name)).join('\n'));
  context.followRef = { current: context.followPath };
  const effect = app.node.body.statements.find(node => ts.isExpressionStatement(node) && ts.isCallExpression(node.expression) && node.expression.expression.getText(app.tree) === 'useEffect' && node.expression.arguments[0].getText(app.tree).includes("window.addEventListener('popstate'"));
  evaluate(context, `(${effect.expression.arguments[0].getText(app.tree)})();`);
  evaluate(context, `(${drawerExpression('onSupplement')})();`); await settle();
  assert.equal(context.window.location.pathname, '/library'); assert.equal(leaves.readHistoryIndex(history.state), 1); assert.equal(context.indexRef.current, 1);
  context.requestPath('/projects/p-one/editor'); await settle(); context.reportDirty(true);
  history.go(-1); await settle(); assert.equal(confirmations.length, 1);
  assert.equal(context.window.location.pathname, '/projects/p-one/editor'); assert.equal(context.dirtyRef.current, true);
  confirmations[0].onCancel(); assert.equal(history.entries.length, 3); assert.equal(history.position, 2); assert.equal(context.indexRef.current, 2);
  history.go(-1); await settle(); assert.equal(confirmations.length, 2); confirmations[1].onOk(); await settle();
  assert.equal(context.window.location.pathname, '/library'); assert.equal(history.position, 1); assert.equal(context.indexRef.current, 1); assert.equal(history.entries.length, 3);
});
