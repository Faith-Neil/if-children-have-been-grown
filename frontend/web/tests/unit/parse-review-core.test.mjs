// 为什么有这个文件：验证解析结果分类树、确认前提提示与批量确认候选（PRD v1.8 §5.2.2；APP-M2-T104）。
// 它解决什么问题：筛选按后台分类；评分项分组只列其要点；星号等三类没有批量候选；提示列出还差几条。
import test from 'node:test';
import assert from 'node:assert/strict';
import { batchCandidates, gateSummary, nodeRows, nodeTitle, unmetGates } from '../../src/project/parse-review-core.ts';

const review = {
  categories: [
    { no: 3, key: 'scoring', label: '评分办法与评分项', requirements: 2, facts: 0, total: 2, pending: 2, batch_allowed: true,
      groups: [{ name: '技术方案（20分）', score: 20, ids: ['s1', 's2'], pending: 2 }] },
    { no: 5, key: 'star', label: '星号实质性条款', requirements: 1, facts: 0, total: 1, pending: 1, batch_allowed: false },
    { no: 6, key: 'technical', label: '技术服务要求', requirements: 2, facts: 0, total: 2, pending: 1, batch_allowed: true },
  ],
  requirement_categories: { s1: 'scoring', s2: 'scoring', st: 'star', t1: 'technical', t2: 'technical' },
  fact_categories: {},
  gates: [
    { code: 'CONFLICTS_PENDING', label: '事实冲突待选定', count: 1, blocking: true, ok: false },
    { code: 'STAR_PENDING', label: '星号条款待逐条确认', count: 1, blocking: true, ok: false },
    { code: 'REFERENCES_UNRESOLVED', label: '引用未解析', count: 2, blocking: false, ok: false },
  ],
  can_confirm: false, parse_confirmed: false,
};
const rows = [
  { id: 's1', status: 'pending' }, { id: 's2', status: 'pending', reference_status: 'unresolved' },
  { id: 'st', status: 'pending' }, { id: 't1', status: 'pending' }, { id: 't2', status: 'confirmed' },
];

test('rows follow the selected category or scoring item', () => {
  assert.equal(nodeRows(rows, review, { kind: 'all' }).length, 5);
  assert.deepEqual(nodeRows(rows, review, { kind: 'category', key: 'technical' }).map(r => r.id), ['t1', 't2']);
  assert.deepEqual(nodeRows(rows, review, { kind: 'group', key: 'scoring', name: '技术方案（20分）' }).map(r => r.id), ['s1', 's2']);
  assert.equal(nodeTitle(review, { kind: 'group', key: 'scoring', name: '技术方案（20分）' }), '评分办法与评分项 › 技术方案（20分）');
  assert.equal(nodeTitle(review, { kind: 'category', key: 'star' }), '5 星号实质性条款');
});

test('batch candidates exclude individual-only categories, confirmed rows and unresolved references', () => {
  assert.deepEqual(batchCandidates(rows, review, { kind: 'category', key: 'star' }), []);
  assert.deepEqual(batchCandidates(rows, review, { kind: 'category', key: 'technical' }).map(r => r.id), ['t1']);
  assert.deepEqual(batchCandidates(rows, review, { kind: 'category', key: 'scoring' }).map(r => r.id), ['s1']);
  assert.deepEqual(batchCandidates(rows, review, { kind: 'all' }), []);
});

test('gate summary lists what is still missing; non-blocking references only warn', () => {
  assert.deepEqual(unmetGates(review).map(g => g.code), ['CONFLICTS_PENDING', 'STAR_PENDING']);
  assert.equal(gateSummary(review), '还差 2 项：事实冲突待选定 1、星号条款待逐条确认 1');
  const ready = { ...review, gates: review.gates.map(g => (g.blocking ? { ...g, count: 0, ok: true } : g)), can_confirm: true };
  assert.match(gateSummary(ready), /另有 2 条引用未解析/);
  assert.equal(gateSummary(null), '');
});

test('unreadable rows need re-entry, low confidence follows the company threshold, quality nodes filter rows', async () => {
  const { needsReentry, lowConfidence, confidenceLabel, threshold } = await import('../../src/project/parse-review-core.ts');
  const rows = [
    { id: 'a', status: 'pending', confidence: 0.4, unreadable: true },
    { id: 'b', status: 'pending', confidence: 0.4, unreadable: true, manually_edited: true },
    { id: 'c', status: 'pending', confidence: 0.85 },
    { id: 'd', status: 'rejected', confidence: 0.1, unreadable: true },
    { id: 'e', status: 'pending' },
  ];
  assert.deepEqual(rows.filter(needsReentry).map(r => r.id), ['a']);
  assert.equal(threshold(null), 0.8);
  assert.equal(threshold({ ...review, confidence_threshold: 0.9 }), 0.9);
  assert.deepEqual(nodeRows(rows, { ...review, confidence_threshold: 0.9 }, { kind: 'quality', which: 'low' }).map(r => r.id), ['a', 'b', 'c']);
  assert.deepEqual(nodeRows(rows, review, { kind: 'quality', which: 'unreadable' }).map(r => r.id), ['a']);
  assert.equal(lowConfidence(rows[2], 0.8), false);
  assert.equal(confidenceLabel(rows[2]), '置信度 0.85');
  assert.equal(confidenceLabel(rows[4]), '');
  assert.equal(nodeTitle(review, { kind: 'quality', which: 'unreadable' }), '原文不可读（对照原页补录）');
  const pendingTech = { categories: [{ no: 6, key: 'technical', label: '技术', requirements: 2, facts: 0, total: 2, pending: 2, batch_allowed: true }],
    requirement_categories: { a: 'technical', c: 'technical' }, fact_categories: {}, gates: [], can_confirm: false, parse_confirmed: false };
  assert.deepEqual(batchCandidates(rows, pendingTech, { kind: 'category', key: 'technical' }).map(r => r.id), ['c']);
});
