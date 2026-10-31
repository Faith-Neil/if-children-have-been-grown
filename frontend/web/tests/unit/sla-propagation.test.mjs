// 为什么有这个文件：验证服务承诺“需复核”传播面板的文案、提醒级别和接线（APP-M2-T122 / T119）。
// 它解决什么问题：面板只呈现后台判定，不自行下结论；没有待处理时不得写成“全部通过”，页面接到矩阵页。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { propagationHeadline, propagationSeverity, reasonColor } from '../../src/admin/sla-propagation.ts';

const summary = (over = {}) => ({ total: 3, by_judgment: {}, needs_review: 0, unconfirmed: 0, risk_unreviewed: 0, invalid: 0, stale_commitments: 0, affected_chapters: 0, ...over });

test('headline lists only the counts the backend reports', () => {
  assert.equal(propagationHeadline(null), '正在读取服务承诺复核状态');
  assert.equal(propagationHeadline({ selected: false, summary: summary() }), '尚未选用服务模板');
  assert.equal(propagationHeadline({ selected: true, summary: summary() }), '没有待处理的复核项');
  assert.equal(
    propagationHeadline({ selected: true, summary: summary({ needs_review: 2, stale_commitments: 1, affected_chapters: 3 }) }),
    '2 项需重新核对，1 份承诺函已过期，涉及 3 个章节',
  );
});

test('severity is warning for review, invalid or stale commitments and success only when nothing is pending', () => {
  assert.equal(propagationSeverity(null), 'info');
  assert.equal(propagationSeverity({ selected: false, summary: summary() }), 'info');
  assert.equal(propagationSeverity({ selected: true, summary: summary({ needs_review: 1 }) }), 'warning');
  assert.equal(propagationSeverity({ selected: true, summary: summary({ invalid: 1 }) }), 'warning');
  assert.equal(propagationSeverity({ selected: true, summary: summary({ stale_commitments: 1 }) }), 'warning');
  assert.equal(propagationSeverity({ selected: true, summary: summary({ unconfirmed: 1 }) }), 'info');
  assert.equal(propagationSeverity({ selected: true, summary: summary() }), 'success');
});

test('reason colors distinguish invalid from review reasons', () => {
  assert.equal(reasonColor('VALUE_INVALID'), 'red');
  assert.equal(reasonColor('NEEDS_REVIEW'), 'orange');
});

test('matrix page renders the panel and it reads the propagation endpoint', () => {
  const page = readFileSync(new URL('../../src/admin/SlaPages.tsx', import.meta.url), 'utf8');
  assert.ok(page.includes('<SlaPropagationPanel />'));
  const core = readFileSync(new URL('../../src/admin/sla-propagation.ts', import.meta.url), 'utf8');
  assert.ok(core.includes('/sla/propagation'));
});
