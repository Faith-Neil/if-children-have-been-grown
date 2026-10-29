// 为什么有这个文件：验证响应矩阵前端判断（APP-M2-T112～T117）。
// 它解决什么问题：星号条款不能选偏离/不适用；挂接只追加不替换；不可引用候选不可选；分流可按建议或现值确认。
import test from 'node:test';
import assert from 'node:assert/strict';
import { appendEvidence, needsReason, responseOptions, routingRows, selectable } from '../../src/project/matrix-core.ts';

test('critical rows cannot be not applicable and deviation is labelled as blocking', () => {
  const disabled = responseOptions(true).filter(o => o.disabled).map(o => o.value);
  assert.deepEqual(disabled, ['not_applicable']);
  assert.match(responseOptions(true).find(o => o.value === 'deviate').label, /阻断/);
  assert.equal(responseOptions(false).some(o => o.disabled), false);
  assert.equal(needsReason('deviate'), true);
  assert.equal(needsReason('comply'), false);
});

test('attach only appends and skips unusable candidates', () => {
  assert.deepEqual(appendEvidence(['a'], ['b', 'a']), ['a', 'b']);
  assert.equal(selectable({ id: 'x', attachable: true, already_attached: false, name: '', score: 1, basis: '' }), true);
  assert.equal(selectable({ id: 'x', attachable: false, name: '', score: 1, basis: '' }), false);
  assert.equal(selectable({ id: 'x', attachable: true, already_attached: true, name: '', score: 1, basis: '' }), false);
});

test('routing rows use suggestion or current volume', () => {
  const items = [{ id: 'r', volume: 'technical', suggested_volume: 'business', is_cross_volume: false }];
  assert.deepEqual(routingRows(items, true), [{ id: 'r', volume: 'business', is_cross_volume: false }]);
  assert.deepEqual(routingRows(items, false), [{ id: 'r', volume: 'technical', is_cross_volume: false }]);
});
