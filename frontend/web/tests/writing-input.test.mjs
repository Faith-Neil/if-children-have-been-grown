// 为什么有这个文件：验证编辑台实际使用的方案转换、失效保护和事实变量插入。
// 它解决什么问题：输入变化不能采用旧候选，方案不能丢失本章选择，未确认事实不能变成正文承诺。
import test from 'node:test';
import assert from 'node:assert/strict';
import { candidateProblem, insertFactToken, writingPlanPayload, writingPlanRows } from '../src/writing-input.ts';

test('writing plans preserve per-chapter selections and use the saved plan instead of empty live defaults', () => {
  const workspace = {
    chapters: [
      { id: 'chapter-a', title: '技术', volume: 'technical', writing_input: { fact_ids: ['fallback'], writing_points: '旧要点', target_length: 20 } },
      { id: 'chapter-b', title: '商务', volume: 'business' },
    ],
    writing_plan: { chapters: [{ id: 'chapter-a', fact_ids: ['optional-one', 'no-longer-confirmed'], writing_points: '引用实施地点', target_length: 900 }] },
  };
  const rows = writingPlanRows(workspace);
  assert.deepEqual(rows[0].fact_ids, ['optional-one', 'no-longer-confirmed']);
  assert.equal(rows[0].writing_points, '引用实施地点');
  assert.equal(rows[0].target_length, 900);
  assert.deepEqual(rows[1].fact_ids, []);
  rows[0].fact_ids.push('local-only');
  assert.deepEqual(workspace.writing_plan.chapters[0].fact_ids, ['optional-one', 'no-longer-confirmed']);
});

test('plan payload keeps explicit fact selections, empty targets, and rejects ambiguous lengths', () => {
  const row = { id: 'chapter-a', title: ' 技术服务 ', volume: 'technical', fact_ids: ['fact-a', 'fact-a', 'fact-b'], writing_points: ' 分步骤回应 ', target_length: null };
  assert.deepEqual(writingPlanPayload([row])[0], { ...row, title: '技术服务', fact_ids: ['fact-a', 'fact-b'], writing_points: '分步骤回应' });
  for (const target_length of [0, -1, 1.5, 100001, NaN, Infinity, '500']) assert.throws(() => writingPlanPayload([{ ...row, target_length }]));
  assert.equal(writingPlanPayload([{ ...row, target_length: 100000 }])[0].target_length, 100000);
});

test('candidate acceptance requires both current input and official chapter revision', () => {
  const candidate = { input_fingerprint: 'input-current', base_revision: 3, status: 'valid' };
  assert.equal(candidateProblem(candidate, 'input-current', 3), null);
  assert.match(candidateProblem(candidate, 'input-changed', 3), /已过期/);
  assert.match(candidateProblem({ ...candidate, status: 'stale' }, 'input-current', 3), /已过期/);
  assert.match(candidateProblem({ ...candidate, input_fingerprint: '' }, 'input-current', 3), /已过期/);
  assert.match(candidateProblem(candidate, 'input-current', 4), /版本/);
  assert.match(candidateProblem(candidate, 'input-current', undefined), /版本/);
});

test('confirmed fact insertion preserves surrounding text and refuses stale or service-specific inputs', () => {
  const fact = { id: 'fact-opaque-id', status: 'confirmed', value: '12个月', source_type: 'tender' };
  assert.deepEqual(insertFactToken('服务期为旧值。', 4, 6, fact), { content: '服务期为{{fact:fact-opaque-id}}。', cursor: 27 });
  assert.equal(insertFactToken('正文', 2, 2, fact).content, '正文{{fact:fact-opaque-id}}');
  for (const status of ['pending', 'needs_review', 'rejected']) assert.throws(() => insertFactToken('正文', 0, 0, { ...fact, status }));
  assert.throws(() => insertFactToken('正文', 0, 0, { ...fact, source_type: 'sla' }));
  assert.throws(() => insertFactToken('正文', 0, 0, { ...fact, value: '' }));
  assert.throws(() => insertFactToken('正文', 3, 3, fact));
  assert.throws(() => insertFactToken('正文', 0, 0, { ...fact, id: 'bad }} id' }));
});
