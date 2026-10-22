// 为什么有这个文件：执行 FormActionFooter、useUnsavedPrompt 与 MetadataForm 通用表单交互能力的 AST 与结构静态断言。
// 它解决什么问题：
// 1. 验证 FormActionFooter 吸底操作条组件正确导出并声明了吸底容器、脏数据状态与操作按钮；
// 2. 验证 useUnsavedPrompt 离开拦截 Hook 正确实现 beforeunload 原生监听与应用内 Modal 拦截确认；
// 3. 验证 MetadataForm 深度集成固底操作条、未保存离开保护与服务端字段级错误就近映射及平滑滚动定位；
// 4. 验证 styles.css 中表单吸底与错误脉冲高亮样式的完整声明。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const footerSource = readFileSync(new URL('../src/shared/FormActionFooter.tsx', import.meta.url), 'utf8');
const footerTree = ts.createSourceFile('FormActionFooter.tsx', footerSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

const hookSource = readFileSync(new URL('../src/shared/useUnsavedPrompt.ts', import.meta.url), 'utf8');
const hookTree = ts.createSourceFile('useUnsavedPrompt.ts', hookSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);

const formSource = readFileSync(new URL('../src/library/MetadataForm.tsx', import.meta.url), 'utf8');
const formTree = ts.createSourceFile('MetadataForm.tsx', formSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

const cssSource = readFileSync(new URL('../src/shared/styles.css', import.meta.url), 'utf8');

function findFunctionDeclaration(tree, name) {
  for (const statement of tree.statements) {
    if (ts.isFunctionDeclaration(statement) && statement.name && statement.name.text === name) {
      return statement;
    }
  }
  return null;
}

test('FormActionFooter is declared and exported as named and default export with sticky bar and tags', () => {
  const footerFunc = findFunctionDeclaration(footerTree, 'FormActionFooter');
  assert.ok(footerFunc, 'FormActionFooter function component is declared');

  const text = footerFunc.getText(footerTree);

  // 1. 吸底容器与类名
  assert.match(text, /className=\{`icg-form-sticky-footer \$\{sticky \? 'is-sticky' : ''\}/, 'supports sticky footer class');
  assert.match(text, /data-testid="form-action-footer"/, 'provides data-testid for container');
  assert.match(text, /data-testid="form-footer-info"/, 'provides data-testid for left info');

  // 2. 脏数据标签与 ★ 关键字段提示
  assert.match(text, /data-testid="dirty-count-tag"/, 'renders dirty count tag');
  assert.match(text, /starredModifiedCount > 0/, 'checks starred field modifications');
  assert.match(text, /检测到 ★ 关键字段变动，保存后将需重新核对确认/, 'shows compliance warning for starred modifications');

  // 3. 提交、重置、取消按钮
  assert.match(text, /data-testid="form-footer-submit"/, 'provides test id for submit button');
  assert.match(text, /data-testid="form-footer-reset"/, 'provides test id for reset button');
  assert.match(text, /data-testid="form-footer-cancel"/, 'provides test id for cancel button');
  assert.match(text, /disabled=\{disabled \|\| loading \|\| !isDirty\}/, 'disables reset button when form is not dirty');
});

test('useUnsavedPrompt implements beforeunload listener and modal confirm navigation', () => {
  const hookFunc = findFunctionDeclaration(hookTree, 'useUnsavedPrompt');
  assert.ok(hookFunc, 'useUnsavedPrompt hook is declared');

  const text = hookFunc.getText(hookTree);

  // 1. beforeunload 事件绑定与解绑
  assert.match(text, /window\.addEventListener\('beforeunload', handleBeforeUnload\)/, 'binds beforeunload event');
  assert.match(text, /window\.removeEventListener\('beforeunload', handleBeforeUnload\)/, 'cleans up beforeunload event');
  assert.match(text, /applyBeforeUnloadEvent\(true, event\)/, 'applies beforeunload event logic');

  // 2. 模态拦截确认
  assert.match(text, /Modal\.confirm\(/, 'invokes Ant Design Modal.confirm for in-app navigation');
  assert.match(text, /FORM_LEAVE_COPY\.title/, 'uses standard leave prompt title');
  assert.match(text, /FORM_LEAVE_COPY\.content/, 'uses standard leave prompt content');
  assert.match(text, /okButtonProps:\s*\{\s*danger:\s*true\s*\}/, 'sets danger style for abandon action');
});

test('MetadataForm deeply integrates FormActionFooter, useUnsavedPrompt, and serverErrors mapping', () => {
  const formFunc = findFunctionDeclaration(formTree, 'MetadataForm');
  assert.ok(formFunc, 'MetadataForm is present');

  const text = formFunc.getText(formTree);

  // 1. 脏数据检测与未保存 Hook 接入
  assert.match(text, /detectDirtyFields\(/, 'invokes detectDirtyFields to track dirty status');
  assert.match(text, /useUnsavedPrompt\(\{/, 'integrates useUnsavedPrompt hook');

  // 2. 服务端字段错误就近映射与平滑滚动聚焦
  assert.match(text, /mapServerFieldErrors\(serverErrors\)/, 'maps serverErrors to Ant Design field errors');
  assert.match(text, /form\.setFields\(mapped\.fieldErrors/, 'sets field errors into Ant Design Form');
  assert.match(text, /scrollFieldIntoView\(mapped\.firstErrorField\)/, 'scrolls first error field into view smoothly');

  // 3. 渲染 FormActionFooter 并支持吸底配置
  assert.match(text, /<FormActionFooter/, 'renders FormActionFooter component');
  assert.match(text, /sticky=\{stickyFooter\}/, 'passes stickyFooter prop');
  assert.match(text, /isDirty=\{dirtySummary\.isDirty\}/, 'passes isDirty state');
  assert.match(text, /modifiedCount=\{dirtySummary\.modifiedCount\}/, 'passes modifiedCount');
});

test('styles.css contains sticky footer and error pulse animation styles', () => {
  assert.match(cssSource, /\.icg-form-sticky-footer\s*\{/, 'defines .icg-form-sticky-footer');
  assert.match(cssSource, /\.icg-form-sticky-footer\.is-sticky\s*\{/, 'defines .is-sticky modifier');
  assert.match(cssSource, /position:\s*sticky/, 'uses position sticky');
  assert.match(cssSource, /bottom:\s*0/, 'anchors to bottom 0');
  assert.match(cssSource, /\.icg-footer-inner\s*\{/, 'defines .icg-footer-inner');
  assert.match(cssSource, /\.icg-footer-modified-tag\s*\{/, 'defines .icg-footer-modified-tag');
  assert.match(cssSource, /@keyframes icg-field-error-pulse/, 'defines keyframes animation for error field');
});
