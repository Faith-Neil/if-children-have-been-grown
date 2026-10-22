// 为什么有这个文件：静态 AST 结构断言与大纲树组件群（OutlineTreeView / ChapterTypeBadge / ValueAddedReasonModal）契约测试。
// 它解决什么问题：验证大纲组件、章节类型徽标、增值理由弹窗、分册数据权限只读协同以及星号/废标条款绝对禁止标“不适用”的合规门禁契约。

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

test('1. outline-tree.ts 导出核心类型、门禁判定与排序算法', () => {
  const { tree } = parseSource('../src/outline-tree.ts');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
    if (ts.isVariableStatement(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      for (const decl of node.declarationList.declarations) {
        if (ts.isIdentifier(decl.name)) exported.add(decl.name.text);
      }
    }
  });

  assert.ok(exported.has('canMarkNotApplicable'), 'must export canMarkNotApplicable');
  assert.ok(exported.has('validateChapterTypeChange'), 'must export validateChapterTypeChange');
  assert.ok(exported.has('reorderNodes'), 'must export reorderNodes');
  assert.ok(exported.has('normalizeChapterNumbers'), 'must export normalizeChapterNumbers');
  assert.ok(exported.has('validateValueAddedReason'), 'must export validateValueAddedReason');
  assert.ok(exported.has('getChapterTypeMeta'), 'must export getChapterTypeMeta');
  assert.ok(exported.has('CHAPTER_TYPES_CONFIG'), 'must export CHAPTER_TYPES_CONFIG');
  assert.ok(exported.has('VALUE_ADDED_PRESETS'), 'must export VALUE_ADDED_PRESETS');
});

test('2. ChapterTypeBadge.tsx 导出徽标组件并支持 5 类章节类型', () => {
  const { content, tree } = parseSource('../src/ChapterTypeBadge.tsx');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('ChapterTypeBadge'), 'must export ChapterTypeBadge');
  assert.ok(content.includes('data-testid="chapter-type-badge"'), 'must include test id');
  assert.ok(content.includes('is-system-generated'), 'must support is-system-generated class');
});

test('3. ValueAddedReasonModal.tsx 具备字数限制、预置模板与只读拦截', () => {
  const { content, tree } = parseSource('../src/ValueAddedReasonModal.tsx');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('ValueAddedReasonModal'), 'must export ValueAddedReasonModal');
  assert.ok(content.includes('data-testid="value-added-modal"'), 'must include modal test id');
  assert.ok(content.includes('data-testid="value-added-textarea"'), 'must include textarea test id');
  assert.ok(content.includes('data-testid="value-added-save-btn"'), 'must include save button test id');
  assert.ok(content.includes('maxLength={500}'), 'must enforce 500 max length');
  assert.ok(content.includes('VALUE_ADDED_PRESETS'), 'must import and render presets');
});

test('4. OutlineTreeView.tsx 落实星号/废标门禁拦截、权限协同与排序跳转', () => {
  const { content, tree } = parseSource('../src/OutlineTreeView.tsx');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('OutlineTreeView'), 'must export OutlineTreeView');

  // 1. 核心门禁：星号/废标条款禁止标“不适用”
  assert.ok(content.includes('canMarkNotApplicable'), 'must check canMarkNotApplicable');
  assert.ok(content.includes('isNotApplicableDisabled'), 'must compute isNotApplicableDisabled');
  assert.ok(content.includes('disabled: isNotApplicableDisabled'), 'must disable not_applicable in options');

  // 2. 数据权限协同：非主管分册只读
  assert.ok(content.includes('useDataPermission'), 'must invoke useDataPermission');
  assert.ok(content.includes('data-testid="readonly-notice-banner"'), 'must display readonly notice banner');

  // 3. 排序与编辑台跳转测试属性
  assert.ok(content.includes('data-testid="outline-tree-view"'), 'must include outline-tree-view root id');
  assert.ok(content.includes('data-testid="outline-node-item"'), 'must include outline-node-item id');
  assert.ok(content.includes('data-testid="chapter-type-select"'), 'must include chapter-type-select id');
  assert.ok(content.includes('data-testid="reorder-up-btn"'), 'must include reorder-up-btn id');
  assert.ok(content.includes('data-testid="reorder-down-btn"'), 'must include reorder-down-btn id');
  assert.ok(content.includes('data-testid="edit-reason-btn"'), 'must include edit-reason-btn id');
  assert.ok(content.includes('data-testid="navigate-editor-btn"'), 'must include navigate-editor-btn id');
});
