// 为什么有这个文件：验证编辑台实际使用的方案转换、失效保护和事实变量插入。
// 它解决什么问题：输入变化不能采用旧候选，方案不能丢失本章选择，未确认事实不能变成正文承诺。
import test from 'node:test';
import assert from 'node:assert/strict';
import { advancePlanReviewRow, candidateProblem, capturePlanReviewBasis, chapterPlanChanged, chapterPlanPayload, chapterStructureChanged, insertFactToken, planReviewRowProblem, planReviewScopeProblem, writingPlanPayload, writingPlanRows } from '../src/writing-input.ts';

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

test('individual confirmation cannot treat unsaved writing inputs or structure and assignment as saved', () => {
  const row = { id: 'c', title: '技术方案', volume: 'technical', assignee_id: 'tech', fact_ids: ['fact'], writing_points: '分步回应', target_length: 800 };
  const input = { fact_ids: ['fact'], writing_points: '分步回应', target_length: 800 };
  assert.deepEqual(chapterPlanPayload(row), input);
  assert.equal(chapterPlanChanged(row, input), false);
  assert.equal(chapterPlanChanged({ ...row, writing_points: '新要点' }, input), true);
  assert.equal(chapterPlanChanged({ ...row, fact_ids: [] }, input), true);
  assert.equal(chapterPlanChanged({ ...row, target_length: 900 }, input), true);
  const chapter = { title: '技术方案', volume: 'technical', assignee_id: 'tech' };
  assert.equal(chapterStructureChanged(row, chapter), false);
  assert.equal(chapterStructureChanged({ ...row, title: '修改名称' }, chapter), true);
  assert.equal(chapterStructureChanged({ ...row, volume: 'business' }, chapter), true);
  assert.equal(chapterStructureChanged({ ...row, assignee_id: null }, chapter), true);
  assert.equal(chapterStructureChanged({ ...row, assignee_id: undefined }, { ...chapter, assignee_id: null }), false);
  assert.equal(writingPlanPayload([{ ...row, assignee_id: null }])[0].assignee_id, null);
  assert.equal(writingPlanPayload([{ ...row }])[0].assignee_id, 'tech');
});

function collaborationPlan() {
  return {
    revision: 10, input_fingerprint: 'global-original', project: { id: 'p', name: '合成项目', company_id: 'alpha' },
    team: { members: [{ user_id: 'tech', project_role: 'writer', company_role: 'editor', volumes: ['technical'] }, { user_id: 'biz', project_role: 'writer', company_role: 'editor', volumes: ['business'] }], volumes: [{ volume: 'technical', owner_id: 'tech' }, { volume: 'business', owner_id: 'biz' }] },
    chapters: [
      { id: 'tech-a', title: '技术A', volume: 'technical', assignee_id: 'tech', content: '', writing_input: { fact_ids: ['fact-tech'], writing_points: '技术A要点', target_length: 700, confirmed_at: null, is_current: false } },
      { id: 'tech-b', title: '技术B', volume: 'technical', assignee_id: 'tech', content: '', writing_input: { fact_ids: [], writing_points: '技术B要点', target_length: 300, confirmed_at: null, is_current: false } },
      { id: 'biz-a', title: '商务A', volume: 'business', assignee_id: 'biz', content: '', writing_input: { fact_ids: ['fact-biz'], writing_points: '商务要点', target_length: 400, confirmed_at: null, is_current: false } },
    ],
    facts: [{ id: 'fact-tech', key: '技术地点', value: '合成技术地点', status: 'confirmed', required: false }, { id: 'fact-biz', key: '商务地点', value: '合成商务地点', status: 'confirmed', required: false }],
    requirements: [{ id: 'req-tech', chapter_id: 'tech-a', text: '每月巡检', evidence_ids: ['proof-tech'], response: '按月巡检', permissions: { response: true }, source: { file_id: 'file-tech', quote: '每月巡检', page: 1 } }],
    files: [{ id: 'file-tech', filename: '合成.txt', sha256: 'original-file', status: 'parsed', page_count: 1, pagination: 'text', warnings: [] }],
    conflicts: [], sla: null,
  };
}

test('a reloaded project revision does not authorize an old row, and saving a different row cannot upgrade its basis', () => {
  const original = collaborationPlan();
  const opened = capturePlanReviewBasis(original, 'technical');
  const updated = structuredClone(original);
  updated.revision = 11; updated.input_fingerprint = 'global-new';
  updated.chapters[0].writing_input.target_length = 900;
  assert.match(planReviewRowProblem(opened, 'tech-a', updated), /后台本节/);
  assert.equal(planReviewRowProblem(opened, 'tech-b', updated), null);
  const saved = { ...updated.chapters[1], writing_input: { ...updated.chapters[1].writing_input, target_length: 600 } };
  const nextBasis = advancePlanReviewRow(opened, updated, saved);
  const afterSave = structuredClone(updated); afterSave.revision = 12; afterSave.chapters[1] = saved;
  assert.equal(planReviewRowProblem(nextBasis, 'tech-b', afterSave), null);
  assert.match(planReviewRowProblem(nextBasis, 'tech-a', afterSave), /后台本节/);
  assert.match(planReviewScopeProblem(nextBasis, afterSave), /后台本节/);
  assert.equal(opened.rows['tech-a'], nextBasis.rows['tech-a']);
  assert.equal(original.chapters[0].writing_input.target_length, 700);
});

test('row review detects source, evidence, owner, assignee and confirmation changes without treating unrelated revisions as review', () => {
  const original = collaborationPlan();
  const resources = { library: [{ id: 'proof-tech', content: '原证据', revision: 1 }] };
  const basis = capturePlanReviewBasis(original, 'all', undefined, resources);
  for (const change of [
    state => { state.chapters[0].title = '新的技术标题'; },
    state => { state.chapters[0].assignee_id = null; },
    state => { state.chapters[0].writing_input.fact_ids = []; },
    state => { state.chapters[0].writing_input.confirmed_at = '2026-10-11T01:00:00Z'; },
    state => { state.facts[0].value = '新的技术地点'; },
    state => { state.requirements[0].response = '每周巡检'; },
    state => { state.files[0].sha256 = 'replaced-file'; },
    state => { state.team.volumes[0].owner_id = null; },
  ]) {
    const changed = structuredClone(original); change(changed);
    assert.match(planReviewRowProblem(basis, 'tech-a', changed, resources), /后台本节/);
  }
  assert.match(planReviewRowProblem(basis, 'tech-a', original, { library: [{ id: 'proof-tech', content: '新证据', revision: 2 }] }), /后台本节/);
  const unrelated = structuredClone(original); unrelated.revision = 99; unrelated.input_fingerprint = 'global-changed'; unrelated.chapters[2].writing_input.target_length = 1200; unrelated.facts[1].value = '新的商务地点';
  assert.equal(planReviewRowProblem(basis, 'tech-a', unrelated, resources), null);
});

test('batch review checks the original scope membership and order including removed rows rather than only retained form rows', () => {
  const original = collaborationPlan();
  const basis = capturePlanReviewBasis(original, 'technical');
  assert.equal(planReviewScopeProblem(basis, original), null);
  for (const change of [
    state => { state.chapters.splice(1, 0, { ...state.chapters[1], id: 'tech-new' }); },
    state => { state.chapters.splice(0, 1); },
    state => { [state.chapters[0], state.chapters[1]] = [state.chapters[1], state.chapters[0]]; },
    state => { state.chapters[0].volume = 'business'; },
  ]) {
    const changed = structuredClone(original); change(changed);
    assert.match(planReviewScopeProblem(basis, changed), /章节顺序或章节清单/);
  }
  const locallyRemovedButRemotelyChanged = structuredClone(original);
  locallyRemovedButRemotelyChanged.chapters[1].writing_input.writing_points = '他人刚保存的技术B要点';
  assert.match(planReviewScopeProblem(basis, locallyRemovedButRemotelyChanged), /后台本节/);
  const unrelatedNew = structuredClone(original); unrelatedNew.chapters.push({ ...unrelatedNew.chapters[2], id: 'biz-new' });
  assert.equal(planReviewScopeProblem(basis, unrelatedNew), null);
});

test('successful individual confirmation and assignment advance only the returned row and do not erase pending form input', () => {
  const original = collaborationPlan();
  const basis = capturePlanReviewBasis(original, 'all');
  const localRows = writingPlanRows(original); localRows[1].writing_points = '本人尚未保存的技术B输入';
  const saved = { ...original.chapters[0], assignee_id: null, writing_input: { ...original.chapters[0].writing_input, confirmed_at: '2026-10-11T01:00:00Z', is_current: true } };
  const nextBasis = advancePlanReviewRow(basis, original, saved);
  const current = structuredClone(original); current.chapters[0] = saved;
  assert.equal(planReviewRowProblem(nextBasis, 'tech-a', current), null);
  assert.equal(nextBasis.rows['tech-b'], basis.rows['tech-b']);
  assert.equal(localRows[1].writing_points, '本人尚未保存的技术B输入');
  assert.throws(() => advancePlanReviewRow(basis, original, { ...saved, id: 'foreign-chapter' }), /不属于本次/);
  const explicitlyReviewed = capturePlanReviewBasis(current, 'all');
  assert.equal(planReviewScopeProblem(explicitlyReviewed, current), null);
});
