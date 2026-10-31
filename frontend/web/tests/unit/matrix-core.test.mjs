// 为什么有这个文件：验证响应矩阵前端判断（APP-M2-T112～T117）。
// 它解决什么问题：星号条款不能选偏离/不适用；挂接只追加不替换；不可引用候选不可选；分流可按建议或现值确认。
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  appendEvidence, candidateMeta, candidateSelectable, groupCandidates, kbStatusText, needsReason, responseOptions, routingRows, selectable,
} from '../../src/project/matrix-core.ts';

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

const cand = (over = {}) => ({ route: 'structured', route_label: '资料库规则匹配', id: 'e1', name: '资质', version: 2, source: '资料库',
  cite_reason: '字面重合', attachable: true, already_attached: false, ...over });

test('candidates are grouped into the three fixed routes, empty routes kept', () => {
  const groups = groupCandidates([cand(), cand({ route: 'history', id: 'h1', attachable: false }), cand({ id: 'e2' })]);
  assert.deepEqual(groups.map(g => g.title), ['资料库规则匹配', '知识库片段', '历史标书仅参考']);
  assert.deepEqual(groups.map(g => g.items.length), [2, 0, 1]);
});

test('only usable structured candidates are selectable; history and snippets never are', () => {
  assert.equal(candidateSelectable(cand(), true), true);
  assert.equal(candidateSelectable(cand(), false), false);
  assert.equal(candidateSelectable(cand({ already_attached: true }), true), false);
  assert.equal(candidateSelectable(cand({ attachable: false }), true), false);
  assert.equal(candidateSelectable(cand({ route: 'history', attachable: true }), true), false);
  assert.equal(candidateSelectable(cand({ route: 'snippet', attachable: true }), true), false);
});

test('meta line shows version, source and validity; kb status text explains degradation', () => {
  assert.equal(candidateMeta(cand({ valid_until: '2027-01-01' })), 'v2 · 资料库 · 有效至 2027-01-01');
  assert.equal(candidateMeta(cand({ version: null, source: '历史标书' })), '历史标书');
  assert.match(kbStatusText('unavailable'), /知识库暂不可用/);
  assert.match(kbStatusText('disabled'), /未启用/);
  assert.equal(kbStatusText('available'), null);
});
