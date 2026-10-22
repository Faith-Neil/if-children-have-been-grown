// 为什么有这个文件：静态 AST 结构断言与权限指令契约测试。
// 它解决什么问题：验证 can.ts、useCan.ts、Can.tsx 与 App.tsx 严格遵循指令式权限架构，确保无权限元素从 DOM 中彻底隐藏。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

function parseSource(relativePath) {
  const fileUrl = new URL(relativePath, import.meta.url);
  const content = readFileSync(fileUrl, 'utf8');
  const tree = ts.createSourceFile(
    relativePath,
    content,
    ts.ScriptTarget.Latest,
    true,
    relativePath.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );
  return { content, tree };
}

test('can-directive.ts exports can, normalizeAction and types', () => {
  const { tree } = parseSource('../src/can-directive.ts');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('can'), 'can-directive.ts must export can function');
  assert.ok(exported.has('normalizeAction'), 'can-directive.ts must export normalizeAction function');
});

test('useCan.ts exports useCan and useCanMap hooks', () => {
  const { tree } = parseSource('../src/useCan.ts');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('useCan'), 'useCan.ts must export useCan hook');
  assert.ok(exported.has('useCanMap'), 'useCan.ts must export useCanMap hook');
});

test('Can.tsx exports Can, CanProvider, CanContext and re-exports hooks', () => {
  const { content, tree } = parseSource('../src/Can.tsx');
  const exportedVars = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isVariableStatement(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      for (const decl of node.declarationList.declarations) {
        if (ts.isIdentifier(decl.name)) exportedVars.add(decl.name.text);
      }
    }
  });

  assert.ok(exportedVars.has('Can'), 'Can.tsx must export Can component');
  assert.ok(exportedVars.has('CanProvider'), 'Can.tsx must export CanProvider component');
  assert.ok(content.includes('export { CanContext }'), 'Can.tsx must re-export CanContext');
  assert.ok(content.includes('export { useCan'), 'Can.tsx must re-export useCan');
  assert.ok(content.includes('export { can'), 'Can.tsx must re-export can function');
});

test('Can.tsx guarantees complete DOM omission on unauthorized by default', () => {
  const { content } = parseSource('../src/Can.tsx');

  // 1. 验证默认 fallback 为 null
  assert.ok(content.includes('fallback = null'), 'Can.tsx must default fallback to null');

  // 2. 验证支持 passThrough 与 tooltipOnDisabled 降级模式
  assert.ok(content.includes('passThrough'), 'Can.tsx must support passThrough prop');
  assert.ok(content.includes('tooltipOnDisabled'), 'Can.tsx must support tooltipOnDisabled prop');

  // 3. 验证默认返回 fallback（即 null，零 DOM 节点残留）
  assert.ok(content.includes('return <>{fallback}</>'), 'Can.tsx must return fallback on unauthorized');
});

test('App.tsx integrates CanProvider and protects create project button with Can directive', () => {
  const { content } = parseSource('../src/App.tsx');

  // 1. 验证导入 Can 与 CanProvider
  assert.ok(content.includes("import { Can, CanProvider } from './Can';"), 'App.tsx must import Can and CanProvider');

  // 2. 验证 AppShell 外部包裹 CanProvider
  assert.ok(content.includes('<CanProvider value='), 'App.tsx must provide CanProvider context');

  // 3. 验证“新建项目”按钮被 <Can perform="project:create"> 保护
  assert.ok(
    content.includes('<Can perform="project:create"><Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}'),
    'App.tsx must protect create project button with <Can perform="project:create">'
  );
});
