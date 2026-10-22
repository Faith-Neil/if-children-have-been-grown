// 为什么有这个文件：执行 MetadataForm 组件的 AST 结构与设计规范（§9.2 规则 2、§5.2.2 与 PRD §5.12）静态断言。
// 它解决什么问题：
// 1. 验证 MetadataForm 组件正确声明并以具名与默认导出形式导出；
// 2. 验证 ★ 关键字段修改提示（Alert 醒目横幅与 .icg-form-item-starred-modified 项级黄色高亮）；
// 3. 验证系统键两行标签排版（.icg-form-two-line-label、.icg-label-primary、.icg-label-secondary、★ 前缀）；
// 4. 验证不支持/未启用字段置灰禁用与 Tooltip 明确悬浮原因解释（.icg-field-disabled-hint、LockOutlined）；
// 5. 验证多数据类型控件分流（Input.TextArea、InputNumber 带单位、Input type="date/datetime-local"、Switch、Select、Input）；
// 6. 验证 1/2/3 栏栅格响应式布局及外部 initialValues 变更双向同步。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/MetadataForm.tsx', import.meta.url), 'utf8');
const tree = ts.createSourceFile('MetadataForm.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

function findFunctionDeclaration(name) {
  for (const statement of tree.statements) {
    if (ts.isFunctionDeclaration(statement) && statement.name && statement.name.text === name) {
      return statement;
    }
  }
  return null;
}

test('MetadataForm is declared and exported as named and default export', () => {
  const formFunc = findFunctionDeclaration('MetadataForm');
  assert.ok(formFunc, 'MetadataForm function component is declared');

  // 检查是否具备 export default 语句
  const hasDefaultExport = tree.statements.some(
    stmt => ts.isExportAssignment(stmt) && stmt.expression.getText(tree) === 'MetadataForm'
  );
  assert.ok(hasDefaultExport, 'MetadataForm is exported as default');
});

test('MetadataForm implements two-line label structure with primary title and monospace system key', () => {
  const formFunc = findFunctionDeclaration('MetadataForm');
  assert.ok(formFunc, 'MetadataForm is present');
  const text = formFunc.getText(tree);

  // 1. 双行标签容器与 CSS 类名
  assert.match(text, /className="icg-form-two-line-label"/, 'renders two-line label container');
  assert.match(text, /data-testid=\{`form-label-\$\{field\.field_key\}`\}/, 'provides test id for labels');

  // 2. 上部中文主标题与 ★ 关键字段前缀
  assert.match(text, /className="icg-label-primary"/, 'renders primary label container');
  assert.match(text, /field\.is_starred &&/, 'checks is_starred flag for critical fields');
  assert.match(text, /className="icg-starred-indicator"/, 'renders starred indicator span');
  assert.match(text, /★/, 'includes star symbol for critical fields');

  // 3. 下部等宽英文/系统键（系统键与主标题不同时才展示，避免冗余）
  assert.match(text, /field\.system_key && field\.system_key !== field\.label/, 'renders system_key conditionally');
  assert.match(text, /className="icg-label-secondary"/, 'renders secondary system key container');
});

test('MetadataForm implements ★ critical field modification warning banner and modified item highlight', () => {
  const formFunc = findFunctionDeclaration('MetadataForm');
  assert.ok(formFunc, 'MetadataForm is present');
  const text = formFunc.getText(tree);

  // 1. 调用纯函数比对 initialValues 与实时值
  assert.match(text, /getModifiedStarredFields/, 'invokes getModifiedStarredFields to diff values');
  assert.match(text, /modifiedStarredFields\.length > 0/, 'computes isStarredModified boolean');

  // 2. 醒目警告横幅（Alert）及文案调用
  assert.match(text, /showStarredBanner && isStarredModified/, 'controls banner visibility based on prop and diff state');
  assert.match(text, /<Alert/, 'renders Ant Design Alert banner');
  assert.match(text, /className="icg-starred-warning-banner page-notice"/, 'uses compliance alert class names');
  assert.match(text, /type="warning"/, 'uses warning alert type');
  assert.match(text, /formatStarredWarning\(modifiedStarredFields\)/, 'uses formatStarredWarning for compliant warning text');
  assert.match(text, /data-testid="starred-modification-alert"/, 'provides test id for starred alert');

  // 3. 项级黄色边框高亮
  assert.match(text, /isModified \? 'icg-form-item-starred-modified' : ''/, 'applies modified highlight class to Form.Item');

  // 4. 底部保存区辅助黄色警示提示与回调通知
  assert.match(text, /onStarredModifiedChange/, 'notifies external consumers of starred modification state');
  assert.match(text, /检测到 ★ 关键字段变动，保存后将需重新核对确认/, 'shows extra hint near submit button');
});

test('MetadataForm handles unsupported, system readonly, and permission disabled fields with Tooltip explanations', () => {
  const formFunc = findFunctionDeclaration('MetadataForm');
  assert.ok(formFunc, 'MetadataForm is present');
  const text = formFunc.getText(tree);

  // 1. 禁用状态判定（resolveFieldDisabledState）
  assert.match(text, /resolveFieldDisabledState\(field, userCanEdit\)/, 'resolves field disabled state and reason');

  // 2. 悬浮 Tooltip 解释禁用原因
  assert.match(text, /disabledState\.disabled && disabledState\.reason/, 'checks if disabled with explanatory reason');
  assert.match(text, /<Tooltip title=\{disabledState\.reason\}/, 'wraps control with Tooltip explaining why disabled');
  assert.match(text, /className="icg-disabled-control-wrapper"/, 'wraps disabled control in tooltip-friendly wrapper');

  // 3. Form.Item extra 辅助锁图标提示
  assert.match(text, /className="icg-field-disabled-hint"/, 'renders disabled hint below input');
  assert.match(text, /<LockOutlined/, 'renders lock icon for disabled explanation');

  // 4. 置灰禁用时免去必填校验规则
  assert.match(text, /field\.required && !disabledState\.disabled/, 'does not enforce required validation on disabled fields');
});

test('MetadataForm dispatches appropriate control components based on field data type and render type', () => {
  const formFunc = findFunctionDeclaration('MetadataForm');
  assert.ok(formFunc, 'MetadataForm is present');
  const text = formFunc.getText(tree);

  // 1. 多行文本与对象：Input.TextArea
  assert.match(text, /<Input\.TextArea/, 'renders Input.TextArea for textarea or object');
  assert.match(text, /rows=\{3\}/, 'specifies default 3 rows');

  // 2. 数值型：InputNumber 带单位后缀
  assert.match(text, /<InputNumber/, 'renders InputNumber for numeric fields');
  assert.match(text, /addonAfter=\{field\.unit\}/, 'passes unit as addonAfter');

  // 3. 日期与日期时间：Input type="date" / type="datetime-local"（避免 dayjs 绑定异常）
  assert.match(text, /type="date"/, 'renders native date input for date fields');
  assert.match(text, /type="datetime-local"/, 'renders native datetime-local input for datetime fields');

  // 4. 布尔开关：Switch
  assert.match(text, /<Switch/, 'renders Switch for boolean fields');
  assert.match(text, /valuePropName=\{/, 'handles checked valuePropName for Switch');

  // 5. 枚举下拉：Select
  assert.match(text, /<Select/, 'renders Select for select / options fields');
  assert.match(text, /options=\{field\.options\}/, 'passes options to Select');

  // 6. 默认单行文本：Input
  assert.match(text, /<Input\s+placeholder=\{field\.placeholder\}/, 'renders standard Input as default fallback');
});

test('MetadataForm supports grid column layout and responsive spans', () => {
  const formFunc = findFunctionDeclaration('MetadataForm');
  assert.ok(formFunc, 'MetadataForm is present');
  const text = formFunc.getText(tree);

  // 1. 栅格布局 Row/Col
  assert.match(text, /<Row gutter=\{16\}>/, 'uses standard Ant Design Row with 16px gutter');
  assert.match(text, /<Col span=\{fieldSpan\}/, 'assigns fieldSpan to Col');

  // 2. 列跨度计算逻辑（1 栏 24、3 栏 8、默认 2 栏 12）
  assert.match(text, /columns === 1 \? 24 : columns === 3 \? 8 : 12/, 'computes defaultColSpan accurately');
  assert.match(text, /field\.span \|\| \(field\.render_type === 'textarea' \? 24 : defaultColSpan\)/, 'textarea spans full row by default');
});
