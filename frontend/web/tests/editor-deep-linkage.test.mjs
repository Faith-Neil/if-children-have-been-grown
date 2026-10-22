// 为什么有这个文件：静态 AST 结构断言与编辑台深度联动（APP-M2-T168）、响应式断点（APP-M2-T160）契约测试。
// 它解决什么问题：
// 1. 验证 EditorPage.tsx 完整集成 OutlineTreeView、mapChaptersToOutlineNodes、ChapterTypeBadge 与 useBreakpoint；
// 2. 验证编辑台大纲目录折叠、助手折叠、抽屉触发及正文区域保障契约；
// 3. 验证保留 data-testid="readonly-editor-view" 等分册权限只读兼容测试桩；
// 4. 验证核心按钮与抽屉的 data-testid 声明完整无误。

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

test('1. EditorPage.tsx 静态引入大纲树组件与响应式 Hook', () => {
  const { content } = parseSource('../src/editor/EditorPage.tsx');

  assert.ok(content.includes("from '../project/OutlineTreeView'"), 'must import OutlineTreeView');
  assert.ok(content.includes("from '../project/ChapterTypeBadge'"), 'must import ChapterTypeBadge');
  assert.ok(content.includes("from '../project/outline-tree'"), 'must import outline-tree helpers');
  assert.ok(content.includes("from '../shell/responsive'"), 'must import useBreakpoint');
  assert.ok(content.includes('mapChaptersToOutlineNodes'), 'must import mapChaptersToOutlineNodes');
  assert.ok(content.includes('useDataPermission'), 'must import useDataPermission');
});

test('2. EditorPage.tsx 声明响应式折叠状态与派生大纲节点', () => {
  const { content } = parseSource('../src/editor/EditorPage.tsx');

  assert.ok(content.includes('const breakpoint = useBreakpoint()'), 'must call useBreakpoint');
  assert.ok(content.includes('directoryCollapsed'), 'must declare directoryCollapsed state');
  assert.ok(content.includes('assistantCollapsed'), 'must declare assistantCollapsed state');
  assert.ok(content.includes('outlineDrawerOpen'), 'must declare outlineDrawerOpen state');
  assert.ok(content.includes('outlineNodes'), 'must derive outlineNodes from mapChaptersToOutlineNodes');
});

test('3. EditorPage.tsx 渲染布局容器与测试属性契约', () => {
  const { content } = parseSource('../src/editor/EditorPage.tsx');

  // 布局类名与 testid
  assert.ok(content.includes('data-testid="editor-page-layout"'), 'must include editor-page-layout testid');
  assert.ok(content.includes('data-testid="editor-center-section"'), 'must include editor-center-section testid');
  assert.ok(content.includes('data-testid="editor-directory-collapsed-strip"'), 'must include collapsed strip testid');

  // 折叠与展开交互按钮契约
  assert.ok(content.includes('data-testid="collapse-outline-btn"'), 'must include collapse-outline-btn testid');
  assert.ok(content.includes('data-testid="expand-outline-btn"'), 'must include expand-outline-btn testid');
  assert.ok(content.includes('data-testid="open-outline-drawer-btn"'), 'must include open-outline-drawer-btn testid');
  assert.ok(content.includes('data-testid="toggle-assistant-btn"'), 'must include toggle-assistant-btn testid');
  assert.ok(content.includes('data-testid="toolbar-outline-drawer-btn"'), 'must include toolbar-outline-drawer-btn testid');
});

test('4. EditorPage.tsx 抽屉与只读态向后兼容契约', () => {
  const { content } = parseSource('../src/editor/EditorPage.tsx');

  // 大纲树抽屉
  assert.ok(content.includes('data-testid="editor-outline-drawer"'), 'must include editor-outline-drawer testid');

  // 严格保留已有的只读视图 testid
  assert.ok(content.includes('data-testid="readonly-editor-view"'), 'must retain readonly-editor-view testid');
  assert.ok(content.includes('data-testid="readonly-editor-text"'), 'must retain readonly-editor-text testid');
  assert.ok(content.includes('ReadonlyBanner'), 'must render ReadonlyBanner on readonly view');
});
