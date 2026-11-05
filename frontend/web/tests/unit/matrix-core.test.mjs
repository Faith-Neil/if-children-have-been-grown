// 为什么有这个文件：验证响应矩阵前端判断（APP-M2-T112～T117）。
// 它解决什么问题：星号条款不能选偏离/不适用；挂接只追加不替换；不可引用候选不可选；分流可按建议或现值确认。
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  appendEvidence, candidateMeta, candidateSelectable, coverageSummary, groupCandidates, kbStatusText, needsReason, responseOptions, routingRows, selectable,
} from '../../src/project/matrix-core.ts';

test('critical rows cannot be not applicable and deviation is labelled as blocking', () => {
  const disabled = responseOptions(true).filter(o => o.disabled).map(o => o.value);
  assert.deepEqual(disabled, ['not_applicable']);
  assert.match(responseOptions(true).find(o => o.value === 'deviate').label, /阻断/);
  assert.equal(responseOptions(false).some(o => o.disabled), false);
  assert.equal(needsReason('deviate'), true);
  assert.equal(needsReason('comply'), false);
  assert.equal(needsReason('exceed', true), true);
  assert.equal(needsReason('exceed'), false);
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

test('candidates are grouped into the fixed routes, empty routes kept', () => {
  const groups = groupCandidates([cand(), cand({ route: 'history', id: 'h1', attachable: false }), cand({ id: 'e2' })]);
  assert.deepEqual(groups.map(g => g.title), ['资料库规则匹配', '知识库片段', '资料库（参考）', '历史标书仅参考']);
  assert.deepEqual(groups.map(g => g.items.length), [2, 0, 0, 1]);
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

test('coverage summary counts mapped gaps deviate and response coverage without acting as a gate', () => {
  const requirements = [
    { id: 'a', text: '健康检查', technical_clause: true, response: '每月巡检', response_type: 'comply' },
    { id: 'b', text: '故障处理', technical_clause: true, response: '30分钟', response_type: 'exceed' },
    { id: 'c', text: '培训', technical_clause: true, response: '', response_origin: 'no_evidence' },
    { id: 'd', text: '商务', technical_clause: false, response: 'x' },
  ];
  const summary = coverageSummary(requirements, {
    headings: [{ requirement_id: 'a' }, { requirement_id: 'b' }],
    missing: ['c'],
  });
  assert.equal(summary.total, 3);
  assert.equal(summary.mapped, 2);
  assert.equal(summary.gaps, 1);
  assert.equal(summary.withResponse, 2);
  assert.equal(summary.deviate, 1);
  assert.equal(summary.noEvidence, 1);
  assert.equal(summary.coveragePercent, 67);
});
