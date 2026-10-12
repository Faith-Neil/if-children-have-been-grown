// 为什么有这个文件：核对挂证据抽屉怎样分组、拦截和记录变动。
// 它解决什么问题：避免未确认、过期、缺协议、受限或历史标书被勾成证据。
import test from 'node:test';
import assert from 'node:assert/strict';
import { applyRefreshedAttachment, attachedEvidenceLabel, attachmentDiff, attachmentStale, evidenceDecision, groupEvidence, toggleSelection } from '../src/evidence-drawer.ts';

const deadline = '2026-12-31T17:00:00+08:00';

function item(overrides) {
  return {
    id: 'e-1', name: '合成资质', type: 'qualification', content: '合成正文', valid_until: '2027-01-01',
    status: 'confirmed', usable_as_evidence: true, reason: '', revision: 3, ...overrides,
  };
}

test('confirmed structured and snippet records can be attached, with version and source visible in the decision', () => {
  const certificate = item({ id: 'cert', name: '合成证书', revision: 4 });
  const snippet = item({ id: 'snip', name: '合成片段', type: 'snippet', match_score: 0.2, revision: 2 });
  assert.equal(evidenceDecision(certificate, deadline).selectable, true);
  assert.equal(evidenceDecision(certificate, deadline).reason, '');
  assert.equal(certificate.revision, 4);
  const groups = groupEvidence([
    snippet,
    item({ id: 'closer', name: '更相关片段', type: 'snippet', match_score: 0.9 }),
    certificate,
  ], deadline);
  assert.deepEqual(groups.snippets.map(row => row.item.id), ['closer', 'snip']);
  assert.deepEqual(groups.structured.map(row => row.item.id), ['cert']);
  assert.equal(groups.citableEmpty, false);
});

test('unconfirmed, expired, missing agreement, restricted and history cannot be attached', () => {
  const cases = [
    item({ id: 'pending', status: 'pending', usable_as_evidence: false }),
    item({ id: 'expired', valid_until: '2020-01-01' }),
    item({ id: 'partner', source_tier: 'partner', agreement_present: false }),
    item({ id: 'restricted', restricted: true }),
    item({ id: 'history', type: 'history', status: 'confirmed', usable_as_evidence: false }),
  ];
  const reasons = Object.fromEntries(cases.map(value => [value.id, evidenceDecision(value, deadline).reason]));
  assert.deepEqual(reasons, {
    pending: '未确认',
    expired: '过期',
    partner: '缺协议',
    restricted: '受限无权',
    history: '历史标书只能参考，不能挂为证据',
  });
  for (const value of cases) assert.equal(evidenceDecision(value, deadline).selectable, false);
  const groups = groupEvidence(cases, deadline);
  assert.equal(groups.history.length, 1);
  assert.equal(groups.history[0].decision.selectable, false);
  assert.equal(groups.citableEmpty, true);
});

test('a partner record with an agreement stays selectable, and history has no selection toggle', () => {
  const partner = item({ id: 'partner-ok', source_tier: 'partner', agreement_present: true });
  assert.equal(evidenceDecision(partner, deadline).selectable, true);
  const history = item({ id: 'hist', type: 'history' });
  assert.deepEqual(toggleSelection(['kept'], history.id, true, evidenceDecision(history, deadline).selectable), ['kept']);
  assert.deepEqual(toggleSelection([], partner.id, true, true), [partner.id]);
  assert.deepEqual(toggleSelection([partner.id], partner.id, false, true), []);
  assert.deepEqual(toggleSelection([partner.id], 'other', true, false), [partner.id]);
});

test('an expired attachment is labeled 证据失效, and refresh copies the reloaded row', () => {
  const expired = item({ id: 'expired', valid_until: '2020-01-01' });
  const current = item({ id: 'current' });
  assert.equal(evidenceDecision(expired, deadline).reason, '过期');
  assert.equal(attachedEvidenceLabel(expired, deadline), '证据失效');
  assert.equal(attachedEvidenceLabel(current, deadline), '当前合格');
  assert.equal(attachedEvidenceLabel(item({ status: 'pending', usable_as_evidence: false }), deadline), '未确认');
  assert.equal(attachedEvidenceLabel(undefined, deadline), '资料已不可见');
  const fresh = applyRefreshedAttachment({ evidence_ids: ['expired', 'current'] }, 9);
  assert.deepEqual(fresh.ids, ['expired', 'current']);
  assert.deepEqual(fresh.opened, { revision: 9, ids: ['expired', 'current'] });
  fresh.ids.push('local');
  assert.deepEqual(fresh.opened.ids, ['expired', 'current']);
});

test('removal is listed against the opened selection, and a newer row blocks save', () => {
  assert.deepEqual(attachmentDiff(['a', 'b'], ['b', 'c']), { added: ['c'], removed: ['a'] });
  assert.equal(attachmentStale(4, ['a'], 4, ['a']), false);
  assert.equal(attachmentStale(4, ['a'], 5, ['a']), true);
  assert.equal(attachmentStale(4, ['a'], 4, ['a', 'b']), true);
});
