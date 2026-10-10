// 为什么有这个文件：核对服务承诺的真实表单转换和正文插入边界。
// 它解决什么问题：防止空承诺被误填为零、危险数字被接受或选择范围之外的文字丢失。
import test from 'node:test';
import assert from 'node:assert/strict';
import { displaySlaValue, insertSlaToken, insertSlaMeasurement, slaScalar, slaVariablePayload } from '../../frontend/web/src/sla-form.ts';

test('empty values remain missing while a real zero stays zero', () => {
  assert.equal(slaScalar('', 'integer', '响应'), null);
  assert.equal(slaScalar('  ', 'decimal', '响应'), null);
  assert.equal(slaScalar('0', 'integer', '响应'), 0);
  assert.equal(displaySlaValue(0, '分钟'), '0 分钟');
  assert.equal(displaySlaValue(null, '分钟', '未提供'), '未提供');
});
test('integer and decimal promises reject unsafe or ambiguous numbers without coercing text', () => {
  for (const value of ['-1', 'NaN', 'Infinity', '1e3', '30分钟', '9007199254740993', '0.5']) assert.throws(() => slaScalar(value, 'integer', '响应'));
  assert.equal(slaScalar('0.5', 'decimal', '响应'), 0.5);
  assert.equal(slaScalar(' 全天候 ', 'text', '服务时段'), '全天候');
  assert.throws(() => slaVariablePayload({ var_key: 'P1 response', label: '响应', group: 'P1', value_type: 'integer', default_value: null, unit: '分钟', compare_direction: 'lower_better', best_committable_value: null }));
});
test('complete tokens replace only the selected text and reject stale positions', () => {
  assert.deepEqual(insertSlaToken('响应旧值分钟。', 2, 4, '{{sla:P1.response}}'), { content: '响应{{sla:P1.response}}分钟。', cursor: 21 });
  assert.equal(insertSlaToken('正文', 2, 2, '{{sla:P1.response}}').content, '正文{{sla:P1.response}}');
  assert.throws(() => insertSlaToken('正文', 3, 3, '{{sla:P1.response}}'));
  assert.throws(() => insertSlaToken('正文', 0, 0, '{{P1.response}}'));
});

test('measurement insertion keeps matching units and requires selecting a conflicting old unit', () => {
  assert.equal(insertSlaMeasurement('响应30分钟。', 2, 4, '{{sla:P1.response}}', 'minute').content, '响应{{sla:P1.response}}分钟。');
  assert.equal(insertSlaMeasurement('响应30小时。', 2, 6, '{{sla:P1.response}}', 'minute').content, '响应{{sla:P1.response}}分钟。');
  assert.throws(() => insertSlaMeasurement('响应30小时。', 2, 4, '{{sla:P1.response}}', 'minute'));
  assert.equal(displaySlaValue('0.5', 'hour'), '0.5 小时');
});
