// 为什么有这个文件：验证导出页的合标核对清单（APP-M2-T200）取最近一次递交版批次，并如实标出未运行/须人工的结论。
// 它解决什么问题：原先是写死的 5 条提示；现在必须来自后台随递交批次生成的 9 类清单，过期批次仍可下载并注明。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { checklistFilename, checklistRowTone, latestSubmissionWithChecklist, responseTracePath } from '../../src/project/export-checks-core.ts';

test('latest submission batch with a checklist is chosen; internal drafts are ignored', () => {
  const exports = [
    { id: 'a', kind: 'submission', created_at: '2026-10-01T00:00:00Z', merge_checklist: { sections: [] } },
    { id: 'b', kind: 'internal', created_at: '2026-10-03T00:00:00Z' },
    { id: 'c', kind: 'submission', created_at: '2026-10-02T00:00:00Z', merge_checklist: { sections: [] } },
  ];
  assert.equal(latestSubmissionWithChecklist(exports).id, 'c');
  assert.equal(latestSubmissionWithChecklist([{ id: 'b', kind: 'internal', created_at: 'x' }]), null);
});

test('row tones flag not-run and manual items for human review', () => {
  assert.equal(checklistRowTone('not_run'), 'orange');
  assert.equal(checklistRowTone('manual'), 'orange');
  assert.equal(checklistRowTone('failed'), 'red');
  assert.equal(checklistRowTone('passed'), 'green');
  assert.equal(checklistRowTone(undefined), 'default');
  assert.equal(checklistFilename('e1'), 'merge-checklist-e1.xlsx');
});

test('export page no longer hard-codes the checklist and offers the Excel download', () => {
  const page = readFileSync(new URL('../../src/project/ProjectPages.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(page, /资格材料是否按本项目要求归册/);
  assert.match(page, /<MergeChecklistCard \/>/);
  assert.match(page, /export-checklist-btn/);
  assert.match(page, /已过期：分册已解锁或正文已改动/);
});

test('response trace path keeps the selected volume', () => {
  assert.equal(responseTracePath('p 1', 'technical'), '/api/v1/projects/p%201/response-trace.xlsx?volume=technical');
  assert.equal(responseTracePath('p', ''), '/api/v1/projects/p/response-trace.xlsx?volume=all');
  const page = readFileSync(new URL('../../src/project/ProjectPages.tsx', import.meta.url), 'utf8');
  assert.match(page, /response-trace-btn/);
});
