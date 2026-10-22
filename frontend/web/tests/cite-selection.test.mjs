// 为什么有这个文件：静态 AST 结构断言与组件契约测试。
// 它解决什么问题：
// 1. 验证 cite-capsule.ts、CiteCapsule.tsx 与 SelectionBubble.tsx 的导出与结构契约；
// 2. 验证 EditorPage.tsx 挂载 SelectionBubble、RichParagraphWithCites 及 editor-citation-bar；
// 3. 验证相关 data-testid、可访问性标签与选区联动回调的完整性。

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

test('cite-capsule.ts exports required parsing and metadata helpers', () => {
  const { tree } = parseSource('../src/cite-capsule.ts');
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

  assert.ok(exported.has('CITE_REGEX'), 'Must export CITE_REGEX');
  assert.ok(exported.has('parseCitations'), 'Must export parseCitations');
  assert.ok(exported.has('extractCitationIds'), 'Must export extractCitationIds');
  assert.ok(exported.has('resolveCitationMeta'), 'Must export resolveCitationMeta');
  assert.ok(exported.has('formatCiteLabel'), 'Must export formatCiteLabel');
});

test('CiteCapsule.tsx exports CiteCapsule and RichParagraphWithCites with contract testids', () => {
  const { content, tree } = parseSource('../src/CiteCapsule.tsx');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isVariableStatement(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      for (const decl of node.declarationList.declarations) {
        if (ts.isIdentifier(decl.name)) exported.add(decl.name.text);
      }
    }
  });

  assert.ok(exported.has('CiteCapsule'), 'Must export CiteCapsule');
  assert.ok(exported.has('RichParagraphWithCites'), 'Must export RichParagraphWithCites');

  // 契约断言：包含必要的 data-testid 与关键 DOM 属性
  assert.ok(content.includes('data-testid="cite-capsule"'), 'Must declare data-testid="cite-capsule"');
  assert.ok(content.includes('data-cite-id='), 'Must bind data-cite-id');
  assert.ok(content.includes('data-cite-type='), 'Must bind data-cite-type');
  assert.ok(content.includes('data-testid="cite-popover-content"'), 'Must declare cite-popover-content');
  assert.ok(content.includes('data-testid="cite-highlight-btn"'), 'Must declare cite-highlight-btn');
});

test('SelectionBubble.tsx exports SelectionBubble with all action buttons and testids', () => {
  const { content, tree } = parseSource('../src/SelectionBubble.tsx');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isVariableStatement(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      for (const decl of node.declarationList.declarations) {
        if (ts.isIdentifier(decl.name)) exported.add(decl.name.text);
      }
    }
  });

  assert.ok(exported.has('SelectionBubble'), 'Must export SelectionBubble');

  // 契约断言：包含浮动容器与三大快捷操作按钮
  assert.ok(content.includes('data-testid="selection-action-bubble"'), 'Must declare selection-action-bubble');
  assert.ok(content.includes('data-testid="bubble-selected-count"'), 'Must declare bubble-selected-count');
  assert.ok(content.includes('data-testid="bubble-polish-btn"'), 'Must declare bubble-polish-btn');
  assert.ok(content.includes('data-testid="bubble-compliance-btn"'), 'Must declare bubble-compliance-btn');
  assert.ok(content.includes('data-testid="bubble-clear-btn"'), 'Must declare bubble-clear-btn');
});

test('EditorPage.tsx mounts SelectionBubble, RichParagraphWithCites and editor-citation-bar', () => {
  const { content } = parseSource('../src/EditorPage.tsx');

  // 1. 验证关键组件导入
  assert.ok(content.includes("from './CiteCapsule'"), 'Must import CiteCapsule');
  assert.ok(content.includes("from './SelectionBubble'"), 'Must import SelectionBubble');
  assert.ok(content.includes("from './cite-capsule'"), 'Must import cite-capsule');

  // 2. 验证挂载 SelectionBubble
  assert.ok(content.includes('<SelectionBubble'), 'Must render SelectionBubble');

  // 3. 验证在 readonly 和 unheld 视图中挂载 RichParagraphWithCites
  assert.ok(
    content.includes('<RichParagraphWithCites'),
    'Must render RichParagraphWithCites'
  );

  // 4. 验证在可编辑视图中提供引用条
  assert.ok(
    content.includes('data-testid="editor-citation-bar"'),
    'Must provide editor-citation-bar'
  );

  // 5. 验证选区事件监听与联动方法挂接
  assert.ok(content.includes('handleContainerMouseUp'), 'Must bind handleContainerMouseUp');
  assert.ok(content.includes('handleTextareaSelect'), 'Must bind handleTextareaSelect');
  assert.ok(content.includes('handleBubblePolish'), 'Must define handleBubblePolish');
  assert.ok(content.includes('handleBubbleComplianceQa'), 'Must define handleBubbleComplianceQa');
});
