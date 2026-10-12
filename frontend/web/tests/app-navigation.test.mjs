// 为什么有这个文件：验证浏览器地址和未保存离开的纯规则。
// 它解决什么问题：深链接、前进后退和取消离开不能只靠页面内存，取消时地址必须留在原页。
import test from 'node:test';
import assert from 'node:assert/strict';
import { commitAddress, menuPathFor, parseAppPath, projectPath, routeAfterLogin } from '../src/app-route.ts';
import { applyBeforeUnload, decideNavigation, holdAddressForPrompt, leaveCopy } from '../src/leave-guard.ts';

test('global paths, project tabs and unknown addresses parse without reading business data', () => {
  assert.deepEqual(parseAppPath('/library'), { kind: 'global', routeId: 'library', path: '/library' });
  assert.deepEqual(parseAppPath('/admin/rules/'), { kind: 'global', routeId: 'admin.rules', path: '/admin/rules' });
  assert.deepEqual(parseAppPath('/'), { kind: 'home', path: '/' });
  assert.deepEqual(parseAppPath('/projects/alpha-project/editor'), { kind: 'project', projectId: 'alpha-project', tab: 'editor', path: '/projects/alpha-project/editor' });
  assert.equal(parseAppPath('/projects/alpha-project/editor').path, projectPath('alpha-project', 'editor'));
  assert.equal(parseAppPath('/projects/alpha-project/not-a-tab').kind, 'unknown');
  assert.equal(parseAppPath('/projects/../editor').kind, 'unknown');
  assert.equal(parseAppPath('/%E4%B8%8D%E5%AD%98%E5%9C%A8').kind, 'unknown');
  assert.equal(menuPathFor(parseAppPath('/projects/alpha-project/matrix')), '/workbench');
  assert.equal(menuPathFor(parseAppPath('/jobs')), '/jobs');
});

test('login returns to the requested address and only the root falls back to the session home', () => {
  assert.deepEqual(routeAfterLogin('/library', 'workbench'), { kind: 'global', routeId: 'library', path: '/library' });
  assert.deepEqual(routeAfterLogin('/', 'workbench'), { kind: 'global', routeId: 'workbench', path: '/workbench' });
  assert.equal(routeAfterLogin('/projects/p-1/settings', 'workbench').kind, 'project');
  assert.equal(routeAfterLogin('/missing', 'workbench').kind, 'unknown');
});

test('history push and replace keep an already canonical address in place', () => {
  const history = { pathname: '/library/', stack: ['/library/'], push(path) { this.stack.push(path); this.pathname = path; }, replace(path) { this.stack[this.stack.length - 1] = path; this.pathname = path; } };
  assert.equal(commitAddress(history, '/library', 'push'), '/library');
  assert.deepEqual(history.stack, ['/library/']);
  assert.equal(commitAddress(history, '/jobs', 'push'), '/jobs');
  assert.equal(history.pathname, '/jobs');
  assert.equal(commitAddress(history, '/workbench', 'replace'), '/workbench');
  assert.equal(history.stack.at(-1), '/workbench');
  assert.deepEqual(history.stack, ['/library/', '/workbench']);
  const frozen = { pathname: '/workbench', stack: ['/workbench'], push(path) { this.stack.push(path); this.pathname = path; }, replace(path) { this.stack[this.stack.length - 1] = path; this.pathname = path; } };
  assert.equal(commitAddress(frozen, '/jobs', 'none'), '/jobs');
  assert.equal(frozen.pathname, '/workbench');
  assert.deepEqual(frozen.stack, ['/workbench']);
});

test('unsaved navigation stays until confirmed, and refresh or close is blocked only while dirty', () => {
  const current = '/projects/alpha-project/editor';
  const next = '/library';
  assert.deepEqual(decideNavigation({ dirty: true, currentPath: current, nextPath: next, confirmed: false }), { path: current, proceed: false });
  assert.deepEqual(decideNavigation({ dirty: true, currentPath: current, nextPath: `${next}/`, confirmed: true }), { path: next, proceed: true });
  assert.equal(decideNavigation({ dirty: false, currentPath: current, nextPath: next, confirmed: false }).proceed, true);
  assert.equal(decideNavigation({ dirty: true, currentPath: current, nextPath: `${current}/`, confirmed: false }).proceed, true);
  const clean = { preventDefault() { this.blocked = true; }, returnValue: '', blocked: false };
  const dirty = { preventDefault() { this.blocked = true; }, returnValue: '', blocked: false };
  assert.equal(applyBeforeUnload(false, clean), false);
  assert.equal(clean.blocked, false);
  assert.equal(applyBeforeUnload(true, dirty), true);
  assert.equal(dirty.blocked, true);
  assert.equal(dirty.returnValue, leaveCopy.content);
});

test('cancelling browser back restores the address of the page that still holds the text', () => {
  const history = { pathname: '/library', pushed: [], push(path) { this.pushed.push(path); this.pathname = path; } };
  const incoming = holdAddressForPrompt(history, '/projects/alpha-project/editor');
  assert.equal(incoming, '/library');
  assert.deepEqual(history.pushed, ['/projects/alpha-project/editor']);
  assert.equal(history.pathname, '/projects/alpha-project/editor');
  const stayed = decideNavigation({ dirty: true, currentPath: history.pathname, nextPath: incoming, confirmed: false });
  assert.equal(stayed.proceed, false);
  assert.equal(stayed.path, '/projects/alpha-project/editor');
});
