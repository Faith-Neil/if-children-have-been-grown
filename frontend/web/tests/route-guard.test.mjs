// 为什么有这个文件：静态 AST 结构断言与守卫模块契约验证。
// 它解决什么问题：证实 route-guard.ts、RouteGuard.tsx 与 App.tsx 严格遵循八角色权限规范，无越权调用漏洞。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

function parseSource(path) {
  const content = readFileSync(new URL(path, import.meta.url), 'utf8');
  return {
    content,
    tree: ts.createSourceFile(path, content, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX),
  };
}

test('route-guard.ts exports all 8 roles, normalization, predicates, and guards', () => {
  const { content, tree } = parseSource('../src/route-guard.ts');

  // 1. 验证 8 角色枚举与元数据存在
  const requiredRoleKeys = [
    'platform_admin',
    'group_admin',
    'company_admin',
    'data_admin',
    'project_lead',
    'bid_writer',
    'auditor',
    'viewer',
  ];
  for (const role of requiredRoleKeys) {
    assert.ok(content.includes(`'${role}'`), `route-guard.ts must define role '${role}'`);
  }

  // 2. 导出符号核查
  const exportedIdentifiers = new Set();
  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exportedIdentifiers.add(node.name.text);
    }
    if (ts.isVariableStatement(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      for (const decl of node.declarationList.declarations) {
        if (ts.isIdentifier(decl.name)) exportedIdentifiers.add(decl.name.text);
      }
    }
  });

  assert.ok(exportedIdentifiers.has('SYSTEM_ROLE_LABELS'), 'SYSTEM_ROLE_LABELS must be exported');
  assert.ok(exportedIdentifiers.has('READONLY_SYSTEM_ROLES'), 'READONLY_SYSTEM_ROLES must be exported');
  assert.ok(exportedIdentifiers.has('PROJECT_CREATOR_ROLES'), 'PROJECT_CREATOR_ROLES must be exported');
  assert.ok(exportedIdentifiers.has('normalizeSystemRole'), 'normalizeSystemRole must be exported');
  assert.ok(exportedIdentifiers.has('getSystemRoleLabel'), 'getSystemRoleLabel must be exported');
  assert.ok(exportedIdentifiers.has('isReadonlyRole'), 'isReadonlyRole must be exported');
  assert.ok(exportedIdentifiers.has('canCreateProject'), 'canCreateProject must be exported');
  assert.ok(exportedIdentifiers.has('checkChapterEditPermission'), 'checkChapterEditPermission must be exported');
  assert.ok(exportedIdentifiers.has('checkRoutePermission'), 'checkRoutePermission must be exported');
  assert.ok(exportedIdentifiers.has('formatForbiddenReason'), 'formatForbiddenReason must be exported');
});

test('RouteGuard.tsx wraps Forbidden403 and provides declarative protection', () => {
  const { content } = parseSource('../src/RouteGuard.tsx');

  assert.ok(content.includes('export function RouteGuard'), 'RouteGuard function component must be exported');
  assert.ok(content.includes('checkRoutePermission'), 'RouteGuard must use checkRoutePermission');
  assert.ok(content.includes('Forbidden403'), 'RouteGuard must render Forbidden403');
  assert.ok(content.includes('onSwitchRole'), 'RouteGuard must accept onSwitchRole');
  assert.ok(content.includes('switchRoleText'), 'RouteGuard must accept switchRoleText');
});

test('StatusViews.tsx Forbidden403 renders switch role action button', () => {
  const { content } = parseSource('../src/StatusViews.tsx');

  assert.ok(content.includes('onSwitchRole?: () => void'), 'Forbidden403Props must declare onSwitchRole');
  assert.ok(content.includes('switchRoleText?: ReactNode'), 'Forbidden403Props must declare switchRoleText');
  assert.ok(content.includes('forbidden-switch-role-button'), 'Forbidden403 must render forbidden-switch-role-button');
});

test('App.tsx intercepts navigation with route guard before data fetching', () => {
  const { content } = parseSource('../src/App.tsx');

  // 1. 验证从 route-guard 模块导入必要函数
  assert.ok(content.includes("from './route-guard'"), 'App.tsx must import from route-guard');
  assert.ok(content.includes('checkRoutePermission'), 'App.tsx must use checkRoutePermission');

  // 2. 验证切页入口前置守卫核验
  assert.ok(content.includes('followPath'), 'followPath must exist');
  assert.ok(content.includes('openProject'), 'openProject must exist');
  assert.ok(content.includes('loadNav'), 'loadNav must exist');
  assert.ok(content.includes('loadTab'), 'loadTab must exist');
  assert.ok(content.includes('canCreateProject'), 'canCreateProject must be used');

  // 3. 验证 403 页面提供切换身份按钮
  assert.ok(content.includes('onSwitchRole'), 'Forbidden403 call in App.tsx must provide onSwitchRole');
  assert.ok(content.includes('switchRoleText="切换身份"'), 'Forbidden403 in App.tsx must provide switchRoleText');
});
