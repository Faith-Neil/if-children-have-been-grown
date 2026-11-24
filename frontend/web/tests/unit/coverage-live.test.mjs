// 为什么有这个文件：覆盖视图在技术卷生成过程中按 task.patched 实时更新行状态。
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  coverageLabel,
  coverageStats,
  mergeTaskPatch,
  parseTaskPatched,
  patchRows,
} from '../../src/project/coverage-live.ts';

function row(extra = {}) {
  return {
    requirement_id: 'r1', task_id: 't1', text: '健康检查', risk_level: 'medium', is_rejection_criterion: false,
    response_status: 'not_started', generation_status: 'pending', response_type: null, ...extra,
  };
}

test('labels follow generation status and deviation type', () => {
  assert.equal(coverageLabel(row()), '未响应');
  assert.equal(coverageLabel(row({ generation_status: 'generating' })), '生成中');
  assert.equal(coverageLabel(row({ generation_status: 'generated', response_type: 'comply' })), '已响应(无偏离)');
  assert.equal(coverageLabel(row({ generation_status: 'generated', response_type: 'exceed' })), '已响应(正偏离)');
  assert.equal(coverageLabel(row({ generation_status: 'generated', response_type: 'deviate' })), '已响应(负偏离)');
  assert.equal(coverageLabel(row({ generation_status: 'generated' })), '已响应');
  assert.equal(coverageLabel(row({ generation_status: 'failed', response_status: 'gap' })), '生成失败');
  assert.equal(coverageLabel(row({ response_status: 'confirmed' })), '已响应');
});

test('parses task.patched and rejects other shapes', () => {
  assert.deepEqual(
    parseTaskPatched({ event: 'task.patched', task_id: 't1', generation_status: 'generating', response_types: { r1: 'exceed', r2: 3 } }),
    { task_id: 't1', generation_status: 'generating', response_types: { r1: 'exceed' } },
  );
  assert.equal(parseTaskPatched({ event: 'section.done', section_id: 't1', text: 'x' }), null);
  assert.equal(parseTaskPatched({ event: 'task.patched', generation_status: 'generated' }), null);
  assert.equal(parseTaskPatched({ event: 'task.patched', task_id: 't1', generation_status: 'done?' }), null);
});

test('merging the same patch twice changes nothing', () => {
  const event = { task_id: 't1', generation_status: 'generated', response_status: 'generated' };
  const once = mergeTaskPatch({}, event);
  const twice = mergeTaskPatch(once, event);
  assert.equal(twice, once);
  assert.deepEqual(once, { t1: { generation_status: 'generated', response_status: 'generated' } });
});

test('a replayed generating patch does not undo a finished section', () => {
  let patches = mergeTaskPatch({}, { task_id: 't1', generation_status: 'generating', response_types: { r1: 'exceed' } });
  patches = mergeTaskPatch(patches, { task_id: 't1', generation_status: 'generated', response_status: 'needs_confirm' });
  const replayed = mergeTaskPatch(patches, { task_id: 't1', generation_status: 'generating', response_types: { r1: 'exceed' } });
  assert.equal(replayed, patches);
  const [only] = patchRows([row()], replayed);
  assert.equal(coverageLabel(only), '已响应(正偏离)');
  assert.equal(only.response_status, 'needs_confirm');
});

test('patches touch only rows of their task and keep the rest by reference', () => {
  const rows = [row(), row({ requirement_id: 'r2', task_id: 't2' })];
  const patched = patchRows(rows, mergeTaskPatch({}, { task_id: 't2', generation_status: 'failed', response_status: 'gap' }));
  assert.equal(patched[0], rows[0]);
  assert.equal(coverageLabel(patched[1]), '生成失败');
  assert.equal(patchRows(rows, {}), rows);
});

test('stats count responded, generating and failed rows', () => {
  const rows = [
    row({ generation_status: 'generated', response_type: 'comply' }),
    row({ generation_status: 'generating' }),
    row({ generation_status: 'failed' }),
    row({ is_rejection_criterion: true }),
  ];
  assert.deepEqual(coverageStats(rows), { total: 4, rejection: 1, responded: 1, generating: 1, failed: 1, confirm: 0 });
});

test('task patches carry RAG summary and failure reason onto rows', async () => {
  const { ragLabel } = await import('../../src/project/coverage-live.ts');
  const rag = { status: 'hit', query: '健康检查', history_hits: 2, material_hits: 1 };
  const patch = parseTaskPatched({ event: 'task.patched', task_id: 't1', generation_status: 'generated', rag, failure_reason: '' });
  assert.deepEqual(patch.rag, rag);
  assert.equal(parseTaskPatched({ event: 'task.patched', task_id: 't1', generation_status: 'failed', rag: { status: 'x' } }).rag, undefined);
  const [patched] = patchRows([row()], mergeTaskPatch({}, patch));
  assert.equal(patched.rag, rag);
  assert.equal(patched.retryable, true);
  assert.equal(ragLabel(rag), '历史 2 · 资料 1');
  assert.equal(ragLabel({ status: 'failed', query: '', history_hits: 0, material_hits: 0, error: 'ReadTimeout' }), '检索失败（ReadTimeout）');
  assert.equal(ragLabel(null), '未检索');
  assert.equal(coverageStats([row({ confirm_reasons: ['知识库无依据'] })]).confirm, 1);
});
