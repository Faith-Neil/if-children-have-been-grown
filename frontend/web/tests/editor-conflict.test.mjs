// 为什么有这个文件：为 APP-M2-T162 编辑台段落保存、实时字数统计与 OCC 409 冲突合并提供组件契约与 AST 级结构校验。
// 它解决什么问题：
// 1. 验证 EditorPage 组件源码中存在字数统计（editor-word-count / word-count-progress / word-count-status-tag）完整标记与展示逻辑；
// 2. 验证脏状态标签（dirty-status-tag）与保存草稿按钮高亮状态（save-draft-btn / toolbar-save-draft-btn）；
// 3. 验证只读态与未持锁纯文本视图（readonly-editor-view / unheld-editor-view / unheld-acquire-btn）的三态守卫；
// 4. 验证 OCC 409 冲突弹窗（conflict-resolution-modal / conflict-overwrite-btn / conflict-discard-btn / conflict-cancel-btn）契约。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

function getEditorSource() {
  const source = readFileSync(new URL('../src/EditorPage.tsx', import.meta.url), 'utf8');
  const tree = ts.createSourceFile('EditorPage.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  return { source, tree };
}

test('EditorPage AST: 正文编辑区三态权限守卫（只读态、未持锁态、持锁编辑态）', () => {
  const { source } = getEditorSource();

  // 1. 只读态守卫：isReadOnlyView 触发 readonly-editor-view
  assert.ok(source.includes('data-testid="readonly-editor-view"'), '必须包含 readonly-editor-view 测试标识');
  assert.ok(source.includes('data-testid="readonly-editor-text"'), '必须包含 readonly-editor-text 测试标识');

  // 2. 未持锁态守卫：!held 触发 unheld-editor-view，优雅纯文本且附带取得编辑权引导
  assert.ok(source.includes('data-testid="unheld-editor-view"'), '必须包含 unheld-editor-view 测试标识');
  assert.ok(source.includes('data-testid="unheld-editor-text"'), '必须包含 unheld-editor-text 测试标识');
  assert.ok(source.includes('data-testid="unheld-acquire-btn"'), '必须包含 unheld-acquire-btn 取得编辑权按钮');

  // 3. 结构三态分支验证：isReadOnlyView ? ... : !held ? ... : ...
  assert.ok(
    source.includes('isReadOnlyView ?') && source.includes(': !held ?'),
    '必须严格按 isReadOnlyView -> !held -> Input.TextArea 三态进行分支控制'
  );
});

test('EditorPage AST: 实时字数统计与目标符合诊断指标', () => {
  const { source } = getEditorSource();

  // 1. 字符数与目标诊断容器
  assert.ok(source.includes('data-testid="editor-word-count"'), 'Footer 必须包含 editor-word-count 容器');
  assert.ok(source.includes('data-testid="word-count-text"'), '必须包含 word-count-text 文本指标');

  // 2. 进度条与状态 Tag
  assert.ok(source.includes('data-testid="word-count-progress"'), '必须包含 word-count-progress 进度条');
  assert.ok(source.includes('data-testid="word-count-status-tag"'), '必须包含 word-count-status-tag 状态 Tag');

  // 3. 目标字数字段引用验证
  assert.ok(
    source.includes('calculateWordCount('),
    '必须调用 calculateWordCount 计算指标'
  );
  assert.ok(
    source.includes('target_length'),
    '必须从 writing_input 中获取 target_length 作为目标字数'
  );
});

test('EditorPage AST: 脏状态检测与保存草稿按钮高亮', () => {
  const { source } = getEditorSource();

  // 1. 顶部工具栏脏状态 Tag
  assert.ok(source.includes('data-testid="dirty-status-tag"'), '顶部工具栏必须包含 dirty-status-tag');
  assert.ok(source.includes('未保存修改'), '脏状态标签文案必须包含“未保存修改”');

  // 2. 工具栏与底部保存草稿按钮
  assert.ok(source.includes('data-testid="toolbar-save-draft-btn"'), '工具栏必须包含 toolbar-save-draft-btn');
  assert.ok(source.includes('data-testid="save-draft-btn"'), '底部操作区必须包含 save-draft-btn');

  // 3. 按钮高亮条件判断：仅当 dirty 且 held 时为 primary
  assert.ok(
    source.includes("type={dirty && held ? 'primary' : 'default'}"),
    '保存草稿按钮必须在 dirty && held 时呈现 primary 高亮'
  );
});

test('EditorPage AST: OCC 409 版本冲突检测与合并弹窗', () => {
  const { source } = getEditorSource();

  // 1. 冲突弹窗主体
  assert.ok(source.includes('data-testid="conflict-resolution-modal"'), '必须包含 conflict-resolution-modal 冲突合并弹窗');

  // 2. 左右两侧对比区域
  assert.ok(source.includes('data-testid="conflict-local-content"'), '必须包含 conflict-local-content 本地内容区');
  assert.ok(source.includes('data-testid="conflict-remote-content"'), '必须包含 conflict-remote-content 远程正文区');

  // 3. 合并决策按钮
  assert.ok(source.includes('data-testid="conflict-overwrite-btn"'), '必须包含 conflict-overwrite-btn 保留本地覆盖保存按钮');
  assert.ok(source.includes('data-testid="conflict-discard-btn"'), '必须包含 conflict-discard-btn 放弃本地采用远程最新按钮');
  assert.ok(source.includes('data-testid="conflict-cancel-btn"'), '必须包含 conflict-cancel-btn 稍后处理按钮');

  // 4. OCC 乐观锁冲突拦截逻辑
  assert.ok(source.includes('isRevisionConflict'), '必须接入 isRevisionConflict 拦截 409');
  assert.ok(source.includes('handleRevisionConflict'), '必须实现 handleRevisionConflict 拉取最新远程章节');
  assert.ok(source.includes('applyConflictResolution'), '必须实现 applyConflictResolution 执行合并');
});
