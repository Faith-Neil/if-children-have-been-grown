// 为什么有这个文件：静态 AST 结构断言与数据权限只读表现契约测试。
// 它解决什么问题：验证 data-permission.ts、useDataPermission.ts、ReadOnlyGate.tsx、EditorPage.tsx 与 MetadataForm.tsx 严格落实 PRD v1.8 §5.11.9 验收约束——“只读成员与集团管理员看到文本而非控件，不是渲染了 input/select 之后再去 disabled，而是在只读模式下直接渲染排版语义纯文本展示”。

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

test('data-permission.ts exports resolveDataPermission, getVolumeDisplayName, getScopeLabel', () => {
  const { tree } = parseSource('../src/shell/data-permission.ts');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('resolveDataPermission'), 'data-permission.ts must export resolveDataPermission');
  assert.ok(exported.has('getVolumeDisplayName'), 'data-permission.ts must export getVolumeDisplayName');
  assert.ok(exported.has('getScopeLabel'), 'data-permission.ts must export getScopeLabel');
});

test('useDataPermission.ts exports useDataPermission hook', () => {
  const { tree } = parseSource('../src/shell/useDataPermission.ts');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('useDataPermission'), 'useDataPermission.ts must export useDataPermission hook');
});

test('ReadOnlyGate.tsx exports ReadOnlyGate, ReadOnlyWrapper, ReadOnlyField, ReadOnlyText', () => {
  const { content, tree } = parseSource('../src/shell/ReadOnlyGate.tsx');
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

  assert.ok(exported.has('ReadOnlyGate'), 'ReadOnlyGate.tsx must export ReadOnlyGate');
  assert.ok(exported.has('ReadOnlyWrapper'), 'ReadOnlyGate.tsx must export ReadOnlyWrapper');
  assert.ok(exported.has('ReadOnlyField'), 'ReadOnlyGate.tsx must export ReadOnlyField');
  assert.ok(exported.has('ReadOnlyText'), 'ReadOnlyGate.tsx must export ReadOnlyText');
});

test('ReadOnlyField renders semantic span and omits inputs when readOnly is true', () => {
  const { content } = parseSource('../src/shell/ReadOnlyGate.tsx');

  // 1. 验证根据 readOnly 状态分支处理
  assert.ok(content.includes('if (readOnly)'), 'ReadOnlyField must check readOnly branch');

  // 2. 验证只读态返回 span 排版文本
  assert.ok(content.includes('className={`icg-readonly-field-text'), 'ReadOnlyField must render span with icg-readonly-field-text');
  assert.ok(content.includes('data-testid={testId || \'readonly-text-field\'}'), 'ReadOnlyField must support testId for assertions');

  // 3. 验证可编辑态渲染控件
  assert.ok(content.includes('renderControl()'), 'ReadOnlyField must render control when writable');
});

test('EditorPage.tsx switches to semantic document text rather than disabled input on readOnly', () => {
  const { content } = parseSource('../src/editor/EditorPage.tsx');

  // 1. 验证引入 useDataPermission 与 ReadonlyBanner
  assert.ok(content.includes("import { ReadonlyBanner } from '../status/StatusViews';"), 'EditorPage must import ReadonlyBanner');
  assert.ok(content.includes("import { useDataPermission } from '../shell/useDataPermission';"), 'EditorPage must import useDataPermission');

  // 2. 验证计算 isReadOnlyView
  assert.ok(content.includes('isReadOnlyView = !canEdit || dataPermission.readOnly;'), 'EditorPage must compute isReadOnlyView');

  // 3. 验证只读态呈现 ReadonlyBanner
  assert.ok(content.includes('<ReadonlyBanner'), 'EditorPage must render ReadonlyBanner on readonly view');

  // 4. 验证只读态直接渲染纯文本排版容器，可编辑态才渲染 Input.TextArea
  assert.ok(content.includes('className="chapter-editor-readonly-view"'), 'EditorPage must render readonly view container');
  assert.ok(content.includes('data-testid="readonly-editor-text"'), 'EditorPage must mark readonly editor text element');
  assert.ok(
    content.includes('{isReadOnlyView ? ('),
    'EditorPage must branch between readonly text view and Input.TextArea control'
  );
});

test('MetadataForm.tsx supports readOnly pure text view and suppresses submit footer', () => {
  const { content } = parseSource('../src/library/MetadataForm.tsx');

  // 1. 验证导入 ReadOnlyField
  assert.ok(content.includes("import { ReadOnlyField } from '../shell/ReadOnlyGate';"), 'MetadataForm must import ReadOnlyField');

  // 2. 验证 MetadataFormProps 支持 readOnly 属性
  assert.ok(content.includes('readOnly?: boolean;'), 'MetadataFormProps must include readOnly prop');

  // 3. 验证在 readOnly 为 true 时渲染 ReadOnlyField 纯文本
  assert.ok(content.includes('<ReadOnlyField'), 'MetadataForm must render ReadOnlyField on readOnly mode');

  // 4. 验证在 readOnly 为 true 时隐藏 FormActionFooter
  assert.ok(
    content.includes('{!readOnly && (showSubmitButton || footerExtra || showResetButton || showCancelButton) && ('),
    'MetadataForm must suppress FormActionFooter when readOnly is true'
  );
});
