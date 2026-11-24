import test from 'node:test';
import assert from 'node:assert/strict';
import { coverageInstruction, numberIssues, sectionRewritePath, sectionsOf, sessionsForSection, storePrefill, takePrefill, TECH_CHIPS } from '../../src/editor/technical-assistant.ts';

function memory() {
  const data = new Map();
  return { getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key) };
}

test('sectionsOf keys sections by task so same-title sections stay separate', () => {
  const outline = { title: 't', chapter_id: 'c', headings: [
    { level: 1, number: '1', title: '服务内容' },
    { level: 2, number: '1.1', title: '健康检查', task_id: 'k1' },
    { level: 2, number: '1.2', title: '应急响应', requirement_id: 'r1' },
    { level: 2, number: '1.3', title: '健康检查', task_id: 'k2' },
  ] };
  assert.deepEqual(sectionsOf(outline), [
    { key: 'k1', label: '1.1 健康检查' }, { key: 'r1', label: '1.2 应急响应' }, { key: 'k2', label: '1.3 健康检查' },
  ]);
  assert.deepEqual(sectionsOf(null), []);
});

test('prefill is read once per project', () => {
  const store = memory();
  storePrefill('p1', { section: '健康检查', instruction: '补齐' }, store);
  assert.deepEqual(takePrefill('p2', store), null);
  assert.deepEqual(takePrefill('p1', store), { section: '健康检查', instruction: '补齐' });
  assert.equal(takePrefill('p1', store), null);
  store.setItem('icg.assistant.prefill.p3', '{bad');
  assert.equal(takePrefill('p3', store), null);
});

test('coverage instruction and quick commands', () => {
  assert.match(coverageInstruction({ text: '季度健康检查', generation_status: 'generated' }), /季度健康检查/);
  assert.match(coverageInstruction({ text: 'x', generation_status: 'failed' }), /生成失败/);
  assert.ok(TECH_CHIPS.some(item => item.label === '补齐未覆盖要点'));
  assert.equal(sectionRewritePath('a b'), '/api/v1/projects/a%20b/technical-sections/rewrite');
});

test('question sessions are listed per section', () => {
  const sessions = [{ id: 'a', section_key: 'TASK-1' }, { id: 'b', section_key: 'TASK-2' }, { id: 'c', section_key: null }, { id: 'd' }];
  assert.deepEqual(sessionsForSection(sessions, 'TASK-1').map(s => s.id), ['a']);
  assert.deepEqual(sessionsForSection(sessions, '').map(s => s.id), ['c', 'd']);
  assert.deepEqual(sessionsForSection(sessions, undefined).map(s => s.id), ['c', 'd']);
});

test('number issues list mismatched requirements and unsupported numbers', () => {
  assert.deepEqual(numberIssues(undefined), []);
  const lines = numberIssues({ status: 'needs_confirm', mismatched_requirements: ['T-01'], unsupported: ['30分钟'] });
  assert.equal(lines.length, 2);
  assert.match(lines[0], /T-01/);
  assert.match(lines[1], /30分钟/);
});
