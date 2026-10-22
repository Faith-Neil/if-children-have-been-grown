// 为什么有这个文件：确认页面是按路由延迟加载，而不是又被入口静态引入。
// 它解决什么问题：分包一旦被改回静态 import，首屏会重新吃下外壳和项目页。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { loadEditor, loadProjectPages, loadSettings, loadShell, loadSupportPages } from '../src/app/route-loaders.ts';

const appSource = readFileSync(new URL('../src/app/App.tsx', import.meta.url), 'utf8');
const loaderSource = readFileSync(new URL('../src/app/route-loaders.ts', import.meta.url), 'utf8');

test('the signed-in shell and route pages stay behind dynamic imports', () => {
  assert.doesNotMatch(appSource, /from '\.\/AppShell'/);
  assert.doesNotMatch(appSource, /from '\.\/ProjectPages'/);
  assert.doesNotMatch(appSource, /from '\.\/EditorPage'/);
  assert.doesNotMatch(appSource, /from '\.\/SupportPages'/);
  assert.doesNotMatch(appSource, /from '\.\/ProjectSettingsPage'/);
  assert.match(appSource, /from '\.\/lazy-routes'/);
  assert.match(appSource, /<Suspense/);
  for (const specifier of ['../shell/AppShell.tsx', '../editor/EditorPage.tsx', '../project/ProjectSettingsPage.tsx', '../project/ProjectPages.tsx', './SupportPages.tsx']) {
    assert.match(loaderSource, new RegExp(`import\\('${specifier.replaceAll('.', '\\.')}'\\)`));
  }
  for (const load of [loadShell, loadEditor, loadSettings, loadProjectPages, loadSupportPages]) {
    assert.equal(typeof load, 'function');
  }
});
