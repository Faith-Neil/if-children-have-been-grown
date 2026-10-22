// 为什么有这个文件：验证模板指标与版本保护，以及两类公司资料读取版本不会串用。
// 它解决什么问题：旧服务模板不能覆盖新承诺，切公司和读取失败不能把旧数据标成新公司的资料。
import test from 'node:test';
import assert from 'node:assert/strict';
import { companyCollectionMutationVersion, companyReadSessionMatches, readCompanyCollections, visibleCompanyCollection } from '../src/library/library-review.ts';
import { captureTemplateReview, copyTemplate, loadReviewedTemplate, templateItemBasis, templateReviewProblem, templateWriteVersion } from '../src/library/template-review.ts';

const variable = { var_key: 'P1.response', label: '响应', group: 'response', value_type: 'integer', default_value: 30, unit: 'minute', compare_direction: 'lower_better', best_committable_value: 20 };
const template = { id: 'tpl-one', company_id: 'alpha', revision: 3, name: '合成服务模板', version_no: '1.0', edition: 'standard', service_hours: 'h5x8', body_text: '响应{{P1.response}}分钟。', status: 'confirmed', reason: '逐项核对', variables: [variable] };
const original = () => ({ company_id: 'alpha', revision: 7, items: [copyTemplate(template)] });

test('an old 30-minute form cannot borrow a refreshed version to overwrite a 90-minute template', () => {
  const old = original();
  const basis = captureTemplateReview(old, template.id);
  const newer = { ...old, revision: 8, items: [{ ...copyTemplate(template), revision: 4, variables: [{ ...variable, default_value: 90 }] }] };
  assert.match(templateReviewProblem(basis, newer), /后台这份服务模板或指标已更新/);
  assert.throws(() => templateWriteVersion(basis, newer), /后台这份/);
  assert.equal(basis.template.variables[0].default_value, 30);
  assert.deepEqual(templateWriteVersion(basis, old), { company_id: 'alpha', revision: 7 });
});

test('every template field, record revision and complete ordered variable array participates in the basis', () => {
  for (const change of [{ name: '新版' }, { version_no: '2.0' }, { revision: 4 }, { edition: 'finance' }, { service_hours: 'h7x24' }, { body_text: '新正文' }, { status: 'pending' }, { reason: '新核对' }, { company_id: 'beta' }]) assert.notEqual(templateItemBasis({ ...template, ...change }), templateItemBasis(template));
  for (const change of [{ var_key: 'P2.response' }, { label: '响应新版' }, { group: 'other' }, { value_type: 'decimal' }, { default_value: 90 }, { unit: 'hour' }, { compare_direction: 'higher_better' }, { best_committable_value: null }]) assert.notEqual(templateItemBasis({ ...template, variables: [{ ...variable, ...change }] }), templateItemBasis(template));
  const second = { ...variable, var_key: 'P2.response' };
  assert.notEqual(templateItemBasis({ ...template, variables: [variable, second] }), templateItemBasis({ ...template, variables: [second, variable] }));
});

test('form copies and captured template variables never mutate the saved read basis', () => {
  const state = original();
  const basis = captureTemplateReview(state, template.id);
  const local = copyTemplate(basis.template);
  local.variables[0].default_value = 900;
  local.variables.push({ ...variable, var_key: 'P3.response' });
  assert.equal(basis.template.variables[0].default_value, 30);
  assert.equal(state.items[0].variables.length, 1);
  assert.equal(templateReviewProblem(basis, state), null);
});

test('fresh confirmation reads reject an unseen second template update before replacing local fields', async () => {
  const basis = captureTemplateReview(original(), template.id);
  const newer = { ...original(), revision: 8, items: [{ ...copyTemplate(template), revision: 4, variables: [{ ...variable, default_value: 90 }] }] };
  const proposal = captureTemplateReview(newer, template.id);
  let server = newer;
  let release;
  let reads = 0;
  let local = '我未保存的服务承诺';
  const pending = loadReviewedTemplate(basis, proposal, async () => { reads++; await new Promise(resolve => { release = resolve; }); return server; }).then(result => { local = result.basis.template.body_text; });
  assert.equal(reads, 1);
  server = { ...newer, revision: 9, items: [{ ...newer.items[0], revision: 5, variables: [{ ...variable, default_value: 120 }] }] };
  release();
  await assert.rejects(pending, /核对期间模板库又有变化/);
  assert.equal(local, '我未保存的服务承诺');
});

test('explicitly reviewed fresh target data loads, while unrelated version updates retain pending inputs', async () => {
  const basis = captureTemplateReview(original(), template.id);
  const unchanged = { ...original(), revision: 8 };
  assert.throws(() => templateWriteVersion(basis, unchanged), /模板读取版本已更新/);
  const retained = await loadReviewedTemplate(basis, captureTemplateReview(unchanged, template.id), async () => unchanged);
  assert.equal(retained.replace_form, false);
  const changed = { ...unchanged, items: [{ ...copyTemplate(template), revision: 4, variables: [{ ...variable, default_value: 90 }] }] };
  const loaded = await loadReviewedTemplate(basis, captureTemplateReview(changed, template.id), async () => changed);
  assert.equal(loaded.replace_form, true);
  assert.equal(loaded.basis.template.variables[0].default_value, 90);
});

test('missing templates, different company and failed fresh reads preserve original input', async () => {
  const basis = captureTemplateReview(original(), template.id);
  assert.throws(() => templateWriteVersion(basis, { ...original(), items: [] }), /不可见/);
  assert.throws(() => captureTemplateReview({ ...original(), company_id: 'beta' }, template.id), /不属于当前公司/);
  assert.throws(() => templateWriteVersion(basis, { ...original(), company_id: 'beta' }), /公司已变化/);
  await assert.rejects(loadReviewedTemplate(basis, basis, async () => { throw new Error('真实读取失败'); }), /真实读取失败/);
  await assert.rejects(loadReviewedTemplate(basis, basis, async () => ({ ...original(), company_id: 'beta' })), /核对期间/);
});

test('new template forms also pin the actual template GET revision and require explicit review', async () => {
  const basis = captureTemplateReview(original(), null);
  const newer = { ...original(), revision: 8 };
  assert.throws(() => templateWriteVersion(basis, newer), /模板读取版本已更新/);
  const accepted = await loadReviewedTemplate(basis, captureTemplateReview(newer, null), async () => newer);
  assert.equal(accepted.replace_form, false);
  assert.deepEqual(templateWriteVersion(accepted.basis, newer), { company_id: 'alpha', revision: 8 });
});

test('parallel GET results keep their own item/revision pairs across an intervening company write', async () => {
  const pairs = await readCompanyCollections('alpha', async () => ({ revision: 8, items: [{ id: 'proof', content: '版本8普通资料' }] }), async () => ({ revision: 9, items: [{ ...copyTemplate(template), revision: 4 }] }));
  assert.equal(pairs.library.company_id, 'alpha');
  assert.equal(pairs.library.revision, 8);
  assert.equal(pairs.library.items[0].content, '版本8普通资料');
  assert.equal(pairs.templates.revision, 9);
  assert.equal(pairs.templates.items[0].revision, 4);
  const library = { company_id: 'alpha', revision: pairs.library.revision };
  const templates = { company_id: 'alpha', revision: pairs.templates.revision };
  assert.equal(companyCollectionMutationVersion('/api/v1/library/proof', library, library, templates), 8);
  assert.equal(companyCollectionMutationVersion('/api/v1/sla/templates/tpl-one', templates, library, templates), 9);
  assert.throws(() => companyCollectionMutationVersion('/api/v1/sla/templates/tpl-one', library, library, templates), /又有变化/);
  assert.throws(() => companyCollectionMutationVersion('/api/v1/library/proof', templates, library, templates), /又有变化/);
  assert.throws(() => companyCollectionMutationVersion('/api/v1/sla/templates', undefined, library, templates), /模板必须携带/);
});

test('old-company snapshots are hidden and not assigned a usable new-company revision when login refresh fails', async () => {
  const old = { ...original(), company_id: 'alpha' };
  const visible = visibleCompanyCollection(old, 'beta');
  assert.deepEqual(visible, { company_id: '', revision: 0, items: [] });
  assert.throws(() => captureTemplateReview({ ...visible, company_id: 'beta' }, null), /有效/);
  await assert.rejects(readCompanyCollections('beta', async () => ({ revision: 1, items: [] }), async () => { throw new Error('切公司读取失败'); }), /切公司读取失败/);
  assert.equal(visibleCompanyCollection(old, 'beta').items.length, 0);
  assert.equal(visibleCompanyCollection(old, 'alpha'), old);
});

test('late replies cannot populate a logged out session, different company or different account in the same company', () => {
  const start = { company_id: 'alpha', account_id: 'alpha-manager', epoch: 4 };
  assert.equal(companyReadSessionMatches(start, { ...start }), true);
  for (const change of [{ epoch: 5 }, { company_id: 'beta' }, { account_id: 'alpha-editor' }, { company_id: '', account_id: '' }]) assert.equal(companyReadSessionMatches(start, { ...start, ...change }), false);
});
