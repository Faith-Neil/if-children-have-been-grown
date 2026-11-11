// 为什么有这个文件：锁定覆盖视图检索审计短句格式。
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  auditSearchLine,
  auditTopKinds,
  tenderIndexLine,
  writerModelLine,
} from '../../src/project/coverage-audit.ts';

test('auditSearchLine prefers hit counts and keeps skip reason', () => {
  assert.equal(
    auditSearchLine({
      tender_searched: true,
      tender_hits: 2,
      history_searched: true,
      history_hits: 1,
      material_searched: false,
      skip_reason: 'materials empty',
    }),
    '本标 2 · 历史 1 · materials empty',
  );
  assert.equal(auditSearchLine({}), '未检索');
});

test('auditTopKinds dedupes dataset kinds from top hits', () => {
  assert.equal(
    auditTopKinds({
      top: [
        { name: 'a', dataset_kind: 'tender' },
        { name: 'b', dataset_kind: 'history' },
        { name: 'c', dataset_kind: 'tender' },
      ],
    }),
    'tender / history',
  );
});

test('tenderIndexLine and writerModelLine stay compact', () => {
  assert.equal(
    tenderIndexLine({ dataset_name: 'workflow.pages', chunk_count: 3, backend: 'local' }),
    'workflow.pages · 3 片',
  );
  assert.equal(writerModelLine({ name: 'qwen', is_real: true, is_local: true }), 'qwen（本地真实）');
  assert.equal(writerModelLine({ name: 'mock', is_real: false }), 'mock（替身）');
});
