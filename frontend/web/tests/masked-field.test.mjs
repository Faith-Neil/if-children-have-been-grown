// 为什么有这个文件：静态 AST 结构断言与 MaskedField / RevealFieldModal 组件契约测试。
// 它解决什么问题：验证敏感字段掩码模块、查看弹窗强校验、审计留痕告警以及完整高敏值零 storage / URL 泄露的硬编码架构约束。

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

test('sensitive-mask.ts exports maskSensitiveValue, validateRevealReason and rules', () => {
  const { tree } = parseSource('../src/admin/sensitive-mask.ts');
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

  assert.ok(exported.has('maskSensitiveValue'), 'must export maskSensitiveValue');
  assert.ok(exported.has('maskIdCard'), 'must export maskIdCard');
  assert.ok(exported.has('maskPhone'), 'must export maskPhone');
  assert.ok(exported.has('maskBankCard'), 'must export maskBankCard');
  assert.ok(exported.has('validateRevealReason'), 'must export validateRevealReason');
  assert.ok(exported.has('assertNoSensitiveLeak'), 'must export assertNoSensitiveLeak');
  assert.ok(exported.has('DEFAULT_MASK_RULES'), 'must export DEFAULT_MASK_RULES');
});

test('RevealFieldModal.tsx enforces mandatory reason, audit notice and zero storage persistence', () => {
  const { content, tree } = parseSource('../src/admin/RevealFieldModal.tsx');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('RevealFieldModal'), 'must export RevealFieldModal');

  // 1. 验证引入 validateRevealReason 校验器
  assert.ok(content.includes('validateRevealReason'), 'must import and invoke validateRevealReason');

  // 2. 验证审计告警条与测试标识
  assert.ok(content.includes('data-testid="reveal-security-alert"'), 'must include security audit alert');
  assert.ok(content.includes('系统将如实记录安全审计日志'), 'must display audit trail explanation');

  // 3. 验证查看原因输入框与确认按钮
  assert.ok(content.includes('data-testid="reveal-reason-input"'), 'must include reason textarea with test id');
  assert.ok(content.includes('data-testid="reveal-confirm-button"'), 'must include confirm button with test id');

  // 4. 验证明文展示容器、一键复制与遮蔽切换
  assert.ok(content.includes('data-testid="revealed-plaintext-value"'), 'must display plaintext in dedicated container');
  assert.ok(content.includes('data-testid="reveal-copy-button"'), 'must include copy button');
  assert.ok(content.includes('data-testid="reveal-remask-button"'), 'must include remask button');

  // 5. 零 Storage / URL 泄露硬约束：绝对不能调用 localStorage / sessionStorage 存储明文
  assert.ok(!content.includes('localStorage.setItem'), 'must never write revealed plaintext to localStorage');
  assert.ok(!content.includes('sessionStorage.setItem'), 'must never write revealed plaintext to sessionStorage');
});

test('MaskedField.tsx integrates permission checks and reveal modal', () => {
  const { content, tree } = parseSource('../src/admin/MaskedField.tsx');
  const exported = new Set();

  ts.forEachChild(tree, node => {
    if (ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      if (node.name) exported.add(node.name.text);
    }
  });

  assert.ok(exported.has('MaskedField'), 'must export MaskedField');

  // 1. 验证引入 useCan 并核验 id_card:view
  assert.ok(content.includes("useCan(canViewAction)"), 'must call useCan to check permission');
  assert.ok(content.includes("'id_card:view'"), 'must check id_card:view action');

  // 2. 验证掩码文本呈现与测试标识
  assert.ok(content.includes('data-testid="masked-value-text"'), 'must render masked text with test id');

  // 3. 验证授权与未授权分支
  assert.ok(content.includes('data-testid="reveal-action-button"'), 'must render reveal button on permission allowed');
  assert.ok(content.includes("unauthorizedMode === 'disabled'"), 'must support disabled mode with tooltip');
  assert.ok(content.includes('data-testid="reveal-action-disabled"'), 'must render disabled button when configured');

  // 4. 验证集成 RevealFieldModal
  assert.ok(content.includes('<RevealFieldModal'), 'must mount RevealFieldModal');
});
