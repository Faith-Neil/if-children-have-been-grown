// 为什么有这个文件：验证资料表单实际采用的保存和核对载入保护。
// 它解决什么问题：防止旧表单借新版本覆盖资料，或核对窗口中的过时内容替换未保存文字。
import test from 'node:test';
import assert from 'node:assert/strict';
import { captureLibraryReview, confirmLibraryReview, libraryItemBasis, libraryMutationVersion, libraryReviewProblem, libraryWriteVersion, loadReviewedLibrary } from '../src/library/library-review.ts';

const originalItem = { id: 'evidence-one', company_id: 'alpha', revision: 3, name: '合成资料', type: 'qualification', content: '原始资料正文', valid_until: '2027-12-31', status: 'confirmed', reason: '已核对', usable_as_evidence: true };
const original = () => ({ company_id: 'alpha', revision: 7, items: [{ ...originalItem }] });

test('refreshing the company revision cannot bless an old material form', () => {
  const current = original();
  const basis = captureLibraryReview(current, originalItem.id);
  const changed = { ...current, revision: 8, items: [{ ...originalItem, revision: 4, content: '他人新正文' }] };
  assert.match(libraryReviewProblem(basis, changed), /后台这条资料已更新/);
  assert.throws(() => libraryWriteVersion(basis, changed), /后台这条资料已更新/);
  assert.equal(basis.item.content, '原始资料正文');
  assert.deepEqual(libraryWriteVersion(basis, current), { company_id: 'alpha', revision: 7 });
});

test('all reviewed record fields and its version participate in the read basis', () => {
  for (const change of [{ name: '新名称' }, { type: 'performance' }, { content: '新正文' }, { valid_until: null }, { status: 'pending' }, { reason: '新说明' }, { revision: 4 }, { usable_as_evidence: false }, { company_id: 'beta' }]) {
    assert.notEqual(libraryItemBasis({ ...originalItem, ...change }), libraryItemBasis(originalItem));
  }
  assert.equal(libraryItemBasis({ ...originalItem, irrelevant_display_field: 'extra' }), libraryItemBasis(originalItem));
});

test('an unrelated company change requires explicit review and can then preserve the local form', () => {
  const current = original();
  const basis = captureLibraryReview(current, originalItem.id);
  const newer = { ...current, revision: 8, items: [...current.items, { ...originalItem, id: 'other', content: '无关新资料' }] };
  assert.match(libraryReviewProblem(basis, newer), /公司资料库版本已更新/);
  assert.throws(() => libraryWriteVersion(basis, newer));
  const proposal = captureLibraryReview(newer, originalItem.id);
  const accepted = confirmLibraryReview(basis, proposal, newer);
  assert.equal(accepted.replace_form, false);
  assert.deepEqual(libraryWriteVersion(accepted.basis, newer), { company_id: 'alpha', revision: 8 });
});

test('changed target data is loaded only after explicit review and another change rejects the load', () => {
  const current = original();
  const basis = captureLibraryReview(current, originalItem.id);
  const newer = { ...current, revision: 8, items: [{ ...originalItem, revision: 4, content: '他人新正文' }] };
  const proposal = captureLibraryReview(newer, originalItem.id);
  const accepted = confirmLibraryReview(basis, proposal, newer);
  assert.equal(accepted.replace_form, true);
  assert.equal(accepted.basis.item.content, '他人新正文');
  assert.throws(() => confirmLibraryReview(basis, proposal, { ...newer, revision: 9 }), /核对期间/);
  assert.throws(() => confirmLibraryReview(basis, proposal, { ...newer, items: [{ ...newer.items[0], content: '核对期间又变' }] }), /核对期间/);
});

test('missing, cross-company or different target records cannot be saved or loaded', () => {
  const current = original();
  const basis = captureLibraryReview(current, originalItem.id);
  assert.throws(() => libraryWriteVersion(basis, { ...current, items: [] }), /不可见/);
  assert.throws(() => captureLibraryReview({ ...current, items: [] }, originalItem.id), /不在当前可见列表/);
  assert.throws(() => libraryWriteVersion(basis, { ...current, company_id: 'beta' }), /公司已变化/);
  assert.throws(() => captureLibraryReview({ ...current, items: [{ ...originalItem, company_id: 'beta' }] }, originalItem.id), /不属于当前公司/);
  assert.throws(() => confirmLibraryReview(basis, captureLibraryReview(current, null), current), /原公司或原资料/);
  assert.throws(() => confirmLibraryReview(basis, { ...basis, company_id: 'beta' }, current), /原公司或原资料/);
});

test('new records also pin the original company revision without discarding their local input', () => {
  const current = original();
  const basis = captureLibraryReview(current, null);
  assert.deepEqual(libraryWriteVersion(basis, current), { company_id: 'alpha', revision: 7 });
  const newer = { ...current, revision: 8 };
  assert.throws(() => libraryWriteVersion(basis, newer), /公司资料库版本已更新/);
  const accepted = confirmLibraryReview(basis, captureLibraryReview(newer, null), newer);
  assert.equal(accepted.replace_form, false);
  assert.equal(accepted.basis.item, null);
});

test('invalid or missing reviewed versions never turn into a default latest write', () => {
  for (const revision of [0, -1, NaN, Infinity, 1.5, Number.MAX_SAFE_INTEGER + 1]) assert.throws(() => captureLibraryReview({ ...original(), revision }, originalItem.id), /有效/);
  assert.throws(() => captureLibraryReview({ ...original(), company_id: '' }, originalItem.id), /有效/);
  assert.throws(() => libraryWriteVersion(null, original()), /尚未读取/);
});

test('mutation version validation checks explicit versions and permits only the caller-selected default', () => {
  const current = { company_id: 'alpha', revision: 8 };
  assert.equal(libraryMutationVersion(undefined, current), 8);
  assert.equal(libraryMutationVersion({ company_id: 'alpha', revision: 8 }, current), 8);
  assert.throws(() => libraryMutationVersion({ company_id: 'alpha', revision: 7 }, current), /又有变化/);
  assert.throws(() => libraryMutationVersion({ company_id: 'beta', revision: 8 }, current), /原公司/);
  assert.throws(() => libraryMutationVersion({ company_id: 'alpha', revision: NaN }, current), /已核对/);
});

test('confirmation waits for a fresh asynchronous read and rejects an unobserved second server update', async () => {
  const basis = captureLibraryReview(original(), originalItem.id);
  const v2 = { ...original(), revision: 8, items: [{ ...originalItem, revision: 4, content: '服务器第二版' }] };
  const proposal = captureLibraryReview(v2, originalItem.id);
  let server = v2;
  let releaseRead;
  let reads = 0;
  let localForm = '我尚未保存的填写';
  const loading = loadReviewedLibrary(basis, proposal, async () => {
    reads++;
    await new Promise(resolve => { releaseRead = resolve; });
    return server;
  }).then(accepted => { localForm = accepted.basis.item.content; });
  assert.equal(reads, 1);
  assert.equal(localForm, '我尚未保存的填写');
  server = { ...v2, revision: 9, items: [{ ...v2.items[0], revision: 5, content: '服务器第三版，页面缓存未更新' }] };
  releaseRead();
  await assert.rejects(loading, /核对期间资料库又有变化/);
  assert.equal(localForm, '我尚未保存的填写');
});

test('a fresh successful asynchronous read permits an explicitly reviewed target load', async () => {
  const basis = captureLibraryReview(original(), originalItem.id);
  const server = { ...original(), revision: 8, items: [{ ...originalItem, revision: 4, content: '已明确核对的服务器新版' }] };
  const proposal = captureLibraryReview(server, originalItem.id);
  let reads = 0;
  const accepted = await loadReviewedLibrary(basis, proposal, async () => { reads++; return server; });
  assert.equal(reads, 1);
  assert.equal(accepted.replace_form, true);
  assert.equal(accepted.basis.item.content, '已明确核对的服务器新版');
});

test('failed or cross-company asynchronous reads do not apply the reviewed proposal', async () => {
  const basis = captureLibraryReview(original(), originalItem.id);
  const proposal = captureLibraryReview(original(), originalItem.id);
  let localForm = '读取失败也保留的填写';
  await assert.rejects(loadReviewedLibrary(basis, proposal, async () => { throw new Error('实际读取失败'); }).then(accepted => { localForm = accepted.basis.item.content; }), /实际读取失败/);
  await assert.rejects(loadReviewedLibrary(basis, proposal, async () => ({ ...original(), company_id: 'beta' })).then(accepted => { localForm = accepted.basis.item.content; }), /核对期间/);
  assert.equal(localForm, '读取失败也保留的填写');
});

test('fresh review of an unrelated company version change retains the original pending form', async () => {
  const basis = captureLibraryReview(original(), originalItem.id);
  const server = { ...original(), revision: 8 };
  const proposal = captureLibraryReview(server, originalItem.id);
  let localForm = '这条资料未改，我的修改继续保留';
  const accepted = await loadReviewedLibrary(basis, proposal, async () => server);
  if (accepted.replace_form) localForm = accepted.basis.item.content;
  assert.equal(accepted.replace_form, false);
  assert.equal(localForm, '这条资料未改，我的修改继续保留');
  assert.deepEqual(libraryWriteVersion(accepted.basis, server), { company_id: 'alpha', revision: 8 });
});
