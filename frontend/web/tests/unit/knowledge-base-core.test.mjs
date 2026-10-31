// 为什么有这个文件：核对知识库同步状态的汇总、待处理排序与片段状态值归一。
// 它解决什么问题：防止界面把后端的 failed 状态显示成“未知”，或把失败条目埋在列表后面。

import test from 'node:test';
import assert from 'node:assert/strict';
import { attentionItems, kbStatusMeta, normalizeSnippetSyncStatus, summarizeKnowledgeBase } from '../../src/library/knowledge-base-core.ts';
import { getSnippetSyncStatusMeta } from '../../src/library/snippet-library-core.ts';

const item = (key, status, name) => ({ key, status, name, source_type: 'library', source_id: key, item_type: 'qualification',
  revision: 1, message: '', chunk_count: 0, updated_at: null, document_id: '' });

test('summary counts and coverage', () => {
  const summary = summarizeKnowledgeBase({ enabled: true, dataset_id: 'd', last_sync_at: null, last_error: '',
    counts: { synced: 3, failed: 1 }, items: [] });
  assert.deepEqual(summary, { total: 4, synced: 3, parsing: 0, pending: 0, failed: 1, coverage: 75 });
  assert.equal(summarizeKnowledgeBase(null).coverage, 0);
});

test('attention items put failures first and skip synced', () => {
  const rows = attentionItems({ enabled: true, dataset_id: 'd', last_sync_at: null, last_error: '', counts: {},
    items: [item('a', 'parsing', '甲'), item('b', 'synced', '乙'), item('c', 'failed', '丙'), item('d', 'unsynced', '丁')] });
  assert.deepEqual(rows.map(r => r.key), ['c', 'd', 'a']);
});

test('backend failed status is recognised everywhere', () => {
  assert.equal(normalizeSnippetSyncStatus('sync_failed'), 'failed');
  assert.equal(normalizeSnippetSyncStatus('failed'), 'failed');
  assert.equal(getSnippetSyncStatusMeta('failed').label, '同步失败');
  assert.equal(kbStatusMeta('parsing').label, '解析中');
});
