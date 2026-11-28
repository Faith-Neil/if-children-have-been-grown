// 为什么有这个文件：核对覆盖视图已过滤条款查阅区的只读行解析与原因标签。
import assert from 'node:assert/strict';
import test from 'node:test';
import { filteredClauseLabel, filteredClauseRows } from '../../src/project/filtered-clauses.ts';

test('keeps only valid non-technical and fragment rows', () => {
  const rows = filteredClauseRows([
    { requirement_id: 'r1', text: '投标报价不得高于最高限价', requirement_scope: 'non_technical', non_tech_category: 'pricing' },
    { requirement_id: 'r2', text: '| 采用数据库', requirement_scope: 'fragment_filtered', fragment_reason: 'leading_broken_punct+table_noise' },
    { requirement_id: 'r3', text: '技术服务要求', requirement_scope: 'technical' },
    'bad',
  ]);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].requirement_id, 'r1');
  assert.equal(rows[1].requirement_id, 'r2');
});

test('labels categories and fragment reasons in business language', () => {
  assert.equal(filteredClauseLabel({ requirement_scope: 'non_technical', non_tech_category: 'format' }), '投标文件格式');
  assert.equal(filteredClauseLabel({ requirement_scope: 'fragment_filtered', fragment_reason: 'leading_broken_punct+table_noise' }), '残句：开头残缺、表格噪声');
  assert.equal(filteredClauseLabel({ requirement_scope: 'fragment_filtered', fragment_reason: '' }), '残句');
});
