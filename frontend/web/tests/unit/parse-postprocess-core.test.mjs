// 为什么有这个文件：验证冲突处理、合并/拆分、文件版本链的页面规则（APP-M2-T101/T102/T107/T109/T110）。
// 它解决什么问题：理由必填、补遗处理不阻断、多位置切换等规则不依赖浏览器即可回归。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { blockingCount, buildDecision, decisionPath, durationLabel, hasAddendumDiff, mergedLabel, nextSourceIndex,
  replacementOptions, retryBody, roleChangeAllowed, sourceLabel, visibleRequirements } from '../../src/project/parse-postprocess-core.ts';

test('处理冲突必须写理由，确认“已按补遗处理”除外', () => {
  assert.equal(buildDecision('not_conflict', '  ').error, '请写明处理理由');
  assert.equal(buildDecision('choose', '以正式文件为准').error, '请先选定一方的取值');
  assert.deepEqual(buildDecision('choose', ' 以正式文件为准 ', { factId: 'f1' }).body,
    { action: 'choose', reason: '以正式文件为准', selected_fact_id: 'f1' });
  assert.deepEqual(buildDecision('not_conflict', '口径不同').body, { action: 'not_conflict', reason: '口径不同' });
  assert.equal(buildDecision('confirm', '').error, undefined);
  assert.equal(buildDecision('assign_target', '对应第三条').error, '请先选择被替代的原条款');
  assert.equal(buildDecision('assign_target', '对应第三条', { requirementId: 'r1' }).body.requirement_id, 'r1');
  assert.equal(decisionPath('p1', 'c 1'), '/api/v1/projects/p1/parse/conflicts/c%201/decision');
});

test('已按补遗处理和历史记录不阻断确认', () => {
  const rows = [
    { status: 'pending', current: true, blocking: true },
    { status: 'by_addendum', current: true, blocking: false },
    { status: 'pending', current: false, blocking: true },
    { status: 'not_conflict', current: true, blocking: false },
  ];
  assert.equal(blockingCount(rows), 1);
});

test('已合并 N 条与拆分后的显示', () => {
  assert.equal(mergedLabel({ merge_status: 'primary', merged_ids: ['a', 'b'] }), '已合并 2 条');
  assert.equal(mergedLabel({ merge_status: 'independent', merged_ids: [] }), '');
  assert.equal(mergedLabel({ merge_status: 'primary', merged_ids: [] }), '');
  const rows = [{ id: 1, merge_status: 'primary' }, { id: 2, merge_status: 'merged' }, { id: 3 }];
  assert.deepEqual(visibleRequirements(rows).map(r => r.id), [1, 3]);
});

test('多位置切换循环取来源', () => {
  assert.equal(nextSourceIndex(0, 3), 1);
  assert.equal(nextSourceIndex(2, 3), 0);
  assert.equal(nextSourceIndex(0, 0), 0);
  assert.equal(sourceLabel({ filename: 'a.docx', page: 4 }, 1, 3), '2/3 · a.docx 第 4 页');
  assert.equal(sourceLabel({ page: 0 }, 0, 1), '1/1 · 页码未知');
});

test('文件版本链：可替代的新版、类型切换限制与差异入口', () => {
  const old = { id: 'a', file_role: 'tender', uploaded_at: '2026-01-01', status: 'parsed' };
  const next = { id: 'b', file_role: 'tender', uploaded_at: '2026-02-01', status: 'uploaded' };
  const other = { id: 'c', file_role: 'addendum', uploaded_at: '2026-03-01', status: 'parsed' };
  assert.deepEqual(replacementOptions(old, [old, next, other]).map(f => f.id), ['b']);
  assert.deepEqual(replacementOptions({ ...old, superseded_by: 'b' }, [old, next]), []);
  assert.equal(roleChangeAllowed(old, 'addendum'), false);
  assert.equal(roleChangeAllowed(old, 'contract'), true);
  assert.equal(roleChangeAllowed(next, 'addendum'), true);
  assert.equal(roleChangeAllowed(other, 'clarification'), true);
  assert.equal(hasAddendumDiff(other), true);
  assert.equal(hasAddendumDiff(old), false);
});

test('解析耗时和换服务重试的请求体', () => {
  assert.equal(durationLabel(null), '—');
  assert.equal(durationLabel(350), '350 毫秒');
  assert.equal(durationLabel(2400), '2.4 秒');
  assert.deepEqual(retryBody('ragflow', 'f1'), { file_ids: ['f1'], service: 'ragflow' });
});
