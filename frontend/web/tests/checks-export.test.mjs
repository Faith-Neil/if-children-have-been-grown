// 为什么有这个文件：静态 AST 结构断言与合规检查红线门禁（APP-M2-T195）及整本递交版导出（APP-M2-T196）契约测试。
// 它解决什么问题：
// 1. 验证 export-checks-core.ts 的导出与契约签名；
// 2. 验证 ChecksPage 中阻断横幅 blocker-alert-banner 与受阻章节列表 blocker-chapters-list 的挂载；
// 3. 验证 ExportPage 中导出前提、阻断告警 export-blocker-warning、生成按钮 export-generate-btn、导出历史表格与 SHA256 指纹展示契约。

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

test('export-checks-core.ts exports all required blocker and export helpers', () => {
  const { tree } = parseSource('../src/project/export-checks-core.ts');
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

  assert.ok(exported.has('isBlocker'), 'Must export isBlocker');
  assert.ok(exported.has('deriveBlockerSummary'), 'Must export deriveBlockerSummary');
  assert.ok(exported.has('canExportSubmission'), 'Must export canExportSubmission');
  assert.ok(exported.has('formatFileSize'), 'Must export formatFileSize');
  assert.ok(exported.has('formatSha256Fingerprint'), 'Must export formatSha256Fingerprint');
  assert.ok(exported.has('getExportKindMeta'), 'Must export getExportKindMeta');
  assert.ok(exported.has('getExportVolumeLabel'), 'Must export getExportVolumeLabel');
});

test('ProjectPages.tsx ChecksPage integrates blocker alert banner and chapters list', () => {
  const { content } = parseSource('../src/project/ProjectPages.tsx');

  // 1. 验证导入 export-checks-core
  assert.ok(content.includes("from './export-checks-core'"), 'ProjectPages must import export-checks-core');

  // 2. 验证 ChecksPage 阻断横幅与受阻章节列表声明
  assert.ok(content.includes('data-testid="blocker-alert-banner"'), 'ChecksPage must declare blocker-alert-banner');
  assert.ok(content.includes('data-testid="blocker-chapters-list"'), 'ChecksPage must declare blocker-chapters-list');
  assert.ok(content.includes('deriveBlockerSummary(check, workspace.chapters)'), 'ChecksPage must call deriveBlockerSummary');
});

test('ProjectPages.tsx ExportPage integrates blocker redline gate, options, and history table', () => {
  const { content } = parseSource('../src/project/ProjectPages.tsx');

  // 1. 验证导出前提中包含合规红线门禁检查
  assert.ok(
    content.includes('合规红线门禁：无阻断性缺陷（Blocker 清零）'),
    'ExportPage premises must check zero blockers'
  );

  // 2. 验证分册范围与类型单选
  assert.ok(content.includes('data-testid="export-volume-radio"'), 'ExportPage must declare export-volume-radio');
  assert.ok(content.includes('data-testid="export-kind-radio"'), 'ExportPage must declare export-kind-radio');

  // 3. 验证阻断警告横幅与递交版禁用按钮
  assert.ok(content.includes('data-testid="export-blocker-warning"'), 'ExportPage must declare export-blocker-warning');
  assert.ok(content.includes('data-testid="export-generate-btn"'), 'ExportPage must declare export-generate-btn');
  assert.ok(content.includes('canExportSubmission({'), 'ExportPage must call canExportSubmission');

  // 4. 验证导出历史表格与元数据列
  assert.ok(content.includes('data-testid="export-history-table"'), 'ExportPage must declare export-history-table');
  assert.ok(content.includes('data-testid="export-history-id"'), 'ExportPage must declare export-history-id');
  assert.ok(content.includes('data-testid="export-fingerprint"'), 'ExportPage must declare export-fingerprint');
  assert.ok(content.includes('data-testid="export-download-btn"'), 'ExportPage must declare export-download-btn');
});
