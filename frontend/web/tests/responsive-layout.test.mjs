// 为什么有这个文件：执行 responsive.ts、BreadcrumbNav.tsx、AppShell.tsx、App.tsx 与 styles.css 的 AST 结构静态断言。
// 它解决什么问题：
// 1. 验证 responsive.ts 完整导出三大断点常量（1280/1440/1680）、useBreakpoint Hook、侧栏持久化与面包屑推导函数；
// 2. 验证 BreadcrumbNav 组件声明了无障碍导航容器（aria-label="面包屑导航"）与末级纯文本页签（aria-current="page"）；
// 3. 验证 AppShell 响应式集成 useBreakpoint 并声明 breakpoint-* 样式类与 data-breakpoint 属性；
// 4. 验证 App.tsx 状态流无缝串联侧栏 localStorage 记忆、进入项目自动收起策略与动态面包屑渲染；
// 5. 验证 styles.css 包含 1040px 紧凑桌面内容区约束与面包屑样式声明。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const responsiveSource = readFileSync(new URL('../src/shell/responsive.ts', import.meta.url), 'utf8');
const responsiveTree = ts.createSourceFile('responsive.ts', responsiveSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);

const breadcrumbSource = readFileSync(new URL('../src/shell/BreadcrumbNav.tsx', import.meta.url), 'utf8');
const breadcrumbTree = ts.createSourceFile('BreadcrumbNav.tsx', breadcrumbSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

const shellSource = readFileSync(new URL('../src/shell/AppShell.tsx', import.meta.url), 'utf8');
const shellTree = ts.createSourceFile('AppShell.tsx', shellSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

const appSource = readFileSync(new URL('../src/app/App.tsx', import.meta.url), 'utf8');
const appTree = ts.createSourceFile('App.tsx', appSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

const cssSource = readFileSync(new URL('../src/shared/styles.css', import.meta.url), 'utf8');

function findExportedIdentifiers(tree) {
  const exports = new Set();
  for (const statement of tree.statements) {
    if (ts.isVariableStatement(statement)) {
      const isExported = statement.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword);
      if (isExported) {
        for (const decl of statement.declarationList.declarations) {
          if (ts.isIdentifier(decl.name)) exports.add(decl.name.text);
        }
      }
    } else if (ts.isFunctionDeclaration(statement)) {
      const isExported = statement.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword);
      if (isExported && statement.name) exports.add(statement.name.text);
    }
  }
  return exports;
}

test('responsive.ts exports standard breakpoint tokens, hooks, storage functions, and breadcrumb derivation', () => {
  const exports = findExportedIdentifiers(responsiveTree);

  // 1. 三大断点
  assert.ok(exports.has('BREAKPOINT_COMPACT'), 'exports BREAKPOINT_COMPACT');
  assert.ok(exports.has('BREAKPOINT_STANDARD'), 'exports BREAKPOINT_STANDARD');
  assert.ok(exports.has('BREAKPOINT_WIDE'), 'exports BREAKPOINT_WIDE');
  assert.ok(exports.has('getBreakpointInfo'), 'exports getBreakpointInfo');
  assert.ok(exports.has('useBreakpoint'), 'exports useBreakpoint');

  // 2. 侧栏持久化记忆
  assert.ok(exports.has('SIDEBAR_COLLAPSED_STORAGE_KEY'), 'exports SIDEBAR_COLLAPSED_STORAGE_KEY');
  assert.ok(exports.has('readStoredSidebarCollapsed'), 'exports readStoredSidebarCollapsed');
  assert.ok(exports.has('writeStoredSidebarCollapsed'), 'exports writeStoredSidebarCollapsed');
  assert.ok(exports.has('resolveInitialSidebarCollapsed'), 'exports resolveInitialSidebarCollapsed');
  assert.ok(exports.has('onEnterProjectCollapse'), 'exports onEnterProjectCollapse');

  // 3. 动态面包屑
  assert.ok(exports.has('formatProjectShortName'), 'exports formatProjectShortName');
  assert.ok(exports.has('deriveBreadcrumbs'), 'exports deriveBreadcrumbs');
  assert.ok(exports.has('PROJECT_TAB_LABELS'), 'exports PROJECT_TAB_LABELS');
  assert.ok(exports.has('GLOBAL_ROUTE_LABELS'), 'exports GLOBAL_ROUTE_LABELS');
});

test('BreadcrumbNav component renders semantic navigation container and leaf elements', () => {
  const exports = findExportedIdentifiers(breadcrumbTree);
  assert.ok(exports.has('BreadcrumbNav'), 'exports BreadcrumbNav');

  // 检查无障碍属性与测试属性
  assert.match(breadcrumbSource, /aria-label="面包屑导航"/, 'declares aria-label on nav container');
  assert.match(breadcrumbSource, /data-testid="topbar-breadcrumb-nav"/, 'declares testid on nav container');
  assert.match(breadcrumbSource, /className="breadcrumb-leaf"/, 'renders leaf element with breadcrumb-leaf class');
  assert.match(breadcrumbSource, /aria-current="page"/, 'declares aria-current page on current leaf');
});

test('AppShell integrates responsive breakpoint tier and supports breadcrumbs prop', () => {
  assert.match(shellSource, /import\s*\{[^}]*useBreakpoint[^}]*\}\s*from\s*'\.\/responsive(?:\.ts)?'/, 'imports useBreakpoint');
  assert.match(shellSource, /const\s+breakpoint\s*=\s*useBreakpoint\(\)/, 'calls useBreakpoint');
  assert.match(shellSource, /`breakpoint-\$\{breakpoint\.tier\}`/, 'applies breakpoint tier class');
  assert.match(shellSource, /data-breakpoint=\{breakpoint\.tier\}/, 'sets data-breakpoint attribute');
  assert.match(shellSource, /breadcrumbs\?: BreadcrumbItemData\[\]/, 'accepts breadcrumbs array prop');
  assert.match(shellSource, /<BreadcrumbNav\s+items=\{breadcrumbs\}/, 'renders BreadcrumbNav with items');
});

test('App.tsx initializes and persists sidebar collapsed state and supplies dynamic breadcrumbs', () => {
  // 1. 侧栏存储与初始化
  assert.match(appSource, /readStoredSidebarCollapsed/, 'reads stored sidebar collapsed state');
  assert.match(appSource, /resolveInitialSidebarCollapsed/, 'computes initial collapsed state with resolveInitialSidebarCollapsed');
  assert.match(appSource, /writeStoredSidebarCollapsed/, 'writes user toggle to persistent storage');
  assert.match(appSource, /handleCollapseChange/, 'implements collapse toggle handler');

  // 2. 进入项目自动收起
  assert.match(appSource, /onEnterProjectCollapse/, 'invokes onEnterProjectCollapse on project navigation');

  // 3. 动态面包屑推导
  assert.match(appSource, /deriveBreadcrumbs/, 'calls deriveBreadcrumbs with context');
  assert.match(appSource, /breadcrumbs=\{breadcrumbs\}/, 'passes breadcrumbs to AppShell');
});

test('styles.css defines compact desktop 1040px width rules and breadcrumb styles', () => {
  assert.match(cssSource, /\.topbar-breadcrumb-nav/, 'styles breadcrumb nav');
  assert.match(cssSource, /\.breadcrumb-leaf/, 'styles breadcrumb leaf');
  assert.match(cssSource, /\.breakpoint-compact\s+\.workspace-content/, 'defines compact desktop content width');
  assert.match(cssSource, /max-width:\s*1040px/, 'enforces 1040px budget to prevent horizontal scrolling');
});
