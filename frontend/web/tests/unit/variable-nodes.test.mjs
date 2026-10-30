// 为什么有这个文件：验证编辑台变量节点的切分与显示（APP-M2-T164）。
// 它解决什么问题：变量按后台给的位置切出，前后文字不丢；文字改过、位置对不上时不显示；失效变量的显示文字与数据源入口。
import test from 'node:test';
import assert from 'node:assert/strict';
import { lineSegments, lineStarts, mayHaveVariables, nodesMatch, sourceLabel, variableText } from '../../src/editor/variable-nodes.ts';

const content = '服务期 {{fact:f-term}}。\n驻场 {{fact:f-pending}} 人';
const node = (token, start, extra = {}) => ({
  token, kind: 'fact', ref: token.slice(7, -2), label: '服务期限', start, end: start + token.length,
  line: 0, display: '12个月', masked: false, status: 'valid', code: null, message: '', source: 'facts', ...extra,
});
const term = node('{{fact:f-term}}', 4);
const pending = node('{{fact:f-pending}}', content.indexOf('{{fact:f-pending}}'), { line: 1, label: '驻场人数', status: 'invalid', display: '', message: '未确认' });

test('lines are split into text and variable pieces at the backend positions', () => {
  const starts = lineStarts(content);
  assert.deepEqual(starts, [0, content.indexOf('\n') + 1]);
  const [first, second] = content.split('\n');
  const a = lineSegments(first, starts[0], [term, pending]);
  assert.deepEqual(a.map(p => p.type), ['text', 'variable', 'text']);
  assert.equal(a[0].text, '服务期 ');
  assert.equal(a[2].text, '。');
  const b = lineSegments(second, starts[1], [term, pending]);
  assert.deepEqual(b.map(p => (p.type === 'text' ? p.text : p.node.ref)), ['驻场 ', 'f-pending', ' 人']);
});

test('nodes are shown only while the text still matches', () => {
  assert.equal(nodesMatch([term, pending], content), true);
  assert.equal(nodesMatch([term, pending], 'X' + content), false);
  assert.equal(nodesMatch([], 'anything'), true);
});

test('chip text and data-source entry', () => {
  assert.equal(variableText(term), '12个月');
  assert.equal(variableText(pending), '驻场人数 · 已失效');
  assert.equal(variableText({ ...pending, status: 'unknown' }), '驻场人数 · 不存在');
  assert.equal(sourceLabel('facts'), '去项目事实表');
  assert.equal(sourceLabel('matrix'), '去服务承诺矩阵');
  assert.equal(mayHaveVariables('无变量'), false);
  assert.equal(mayHaveVariables('{{ sla : x'), true);
});
