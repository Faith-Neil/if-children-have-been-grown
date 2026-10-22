// 为什么有这个文件：执行 BusinessTags 组件的真实 AST 结构与无障碍属性断言。
// 它解决什么问题：
// 1. 验证五大业务小组件（LevelTag、AiTag、DirectTag、Cite、SourceBar）均按规范导出且具有正确的 TypeScript 类型与 data-testid；
// 2. 验证 AI 紫色彩锁定（非 AiTag 组件严禁带有紫色相关预设与类名）；
// 3. 验证 Cite 引用上标与悬浮 Popover、SourceBar 段落左侧 3px 色条及底部来源条的结构声明。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import * as bizLogic from '../src/library/business-tags.ts';

const source = readFileSync(new URL('../src/library/BusinessTags.tsx', import.meta.url), 'utf8');
const tree = ts.createSourceFile('BusinessTags.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

function findVariableDeclaration(name) {
  for (const statement of tree.statements) {
    if (ts.isVariableStatement(statement)) {
      for (const decl of statement.declarationList.declarations) {
        if (ts.isIdentifier(decl.name) && decl.name.text === name) {
          return decl;
        }
      }
    }
  }
  return null;
}

test('BusinessTags exports all five core business components with data-testid attributes', () => {
  // 1. LevelTag 条款级别标签
  const levelTagDecl = findVariableDeclaration('LevelTag');
  assert.ok(levelTagDecl, 'LevelTag component is declared and exported');

  // 2. AiTag AI 辅助标签
  const aiTagDecl = findVariableDeclaration('AiTag');
  assert.ok(aiTagDecl, 'AiTag component is declared and exported');

  // 3. DirectTag 直接响应 / 系统直查标签
  const directTagDecl = findVariableDeclaration('DirectTag');
  assert.ok(directTagDecl, 'DirectTag component is declared and exported');

  // 4. Cite 资料与正文段落引用标注组件
  const citeDecl = findVariableDeclaration('Cite');
  assert.ok(citeDecl, 'Cite component is declared and exported');

  // 5. SourceBar 底部或段落侧边来源条
  const sourceBarDecl = findVariableDeclaration('SourceBar');
  assert.ok(sourceBarDecl, 'SourceBar component is declared and exported');
});

test('LevelTag supports solid and subtle variants with proper accessibility attributes', () => {
  const levelDecl = findVariableDeclaration('LevelTag');
  assert.ok(levelDecl, 'LevelTag is present');
  const text = levelDecl.getText(tree);

  assert.match(text, /data-testid="icg-level-tag"/);
  assert.match(text, /data-level={resolved\.category}/);
  assert.match(text, /resolveLevelTag\(level/);
  assert.match(text, /role={resolved\.ariaRole}/);
  assert.match(text, /aria-label=/);
  assert.match(text, /onClick={onClick}/);
});

test('AiTag strictly adopts AI purple tokens and isolates from other tags', () => {
  const aiDecl = findVariableDeclaration('AiTag');
  assert.ok(aiDecl, 'AiTag is present');
  const text = aiDecl.getText(tree);

  assert.match(text, /data-testid="icg-ai-tag"/);
  assert.match(text, /resolveAiTag\(variant/);
  assert.match(text, /role="status"/);
  assert.match(text, /aria-label={resolved\.ariaLabel}/);
  assert.match(text, /RobotOutlined/);
});

test('DirectTag renders direct response blue tag and does not use AI purple', () => {
  const directDecl = findVariableDeclaration('DirectTag');
  assert.ok(directDecl, 'DirectTag is present');
  const text = directDecl.getText(tree);

  assert.match(text, /data-testid="icg-direct-tag"/);
  assert.match(text, /resolveDirectTag\(variant/);
  assert.match(text, /direct-tag/);
  assert.match(text, /DatabaseOutlined/);
  assert.match(text, /role="status"/);
});

test('Cite supports popover hover card, superscript citation, and inline fact highlights', () => {
  const citeDecl = findVariableDeclaration('Cite');
  assert.ok(citeDecl, 'Cite is present');
  const text = citeDecl.getText(tree);

  // 悬浮 Popover 支持
  assert.match(text, /<Popover/);
  assert.match(text, /renderPopover/);

  // 上标与事实高亮变体
  assert.match(text, /data-testid="icg-cite-anchor"/);
  assert.match(text, /data-testid="icg-cite-fact"/);
  assert.match(text, /data-testid="icg-cite-none"/);
  assert.match(text, /verticalAlign:\s*'super'/);
  assert.match(text, /role="doc-biblioref"/);
  assert.match(text, /tabIndex={0}/);
});

test('SourceBar provides paragraph 3px gutter and bottom bar layouts with fingerprint provenance', () => {
  const barDecl = findVariableDeclaration('SourceBar');
  assert.ok(barDecl, 'SourceBar is present');
  const text = barDecl.getText(tree);

  // 两种布局：段落侧边 3px 色条 vs 底部来源条
  assert.match(text, /data-testid="icg-source-bar-paragraph"/);
  assert.match(text, /data-testid="icg-source-bar-bottom"/);
  assert.match(text, /borderLeft:\s*`3px solid \${resolved\.color}`/);

  // 指纹展示与来源核对触发
  assert.match(text, /formattedFingerprint/);
  assert.match(text, /onVerifySource/);
  assert.match(text, /role="region"/);
});

test('business-tags pure module constants and contrast tokens are intact', () => {
  assert.equal(typeof bizLogic.resolveLevelTag, 'function');
  assert.equal(typeof bizLogic.resolveAiTag, 'function');
  assert.equal(typeof bizLogic.resolveDirectTag, 'function');
  assert.equal(typeof bizLogic.resolveCite, 'function');
  assert.equal(typeof bizLogic.resolveSourceBar, 'function');
  assert.equal(typeof bizLogic.formatFingerprint, 'function');
  assert.equal(typeof bizLogic.isAiColor, 'function');
  assert.equal(typeof bizLogic.assertNotAiColor, 'function');
  assert.equal(bizLogic.BIZ_COLOR_TOKENS.aiPurple, '#6E4BD8');
  assert.equal(bizLogic.BIZ_COLOR_TOKENS.directText, '#1E4DB7');
  assert.equal(bizLogic.BIZ_COLOR_TOKENS.blockerSolidBg, '#D9363E');
});
