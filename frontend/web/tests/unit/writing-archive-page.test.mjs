// 为什么有这个文件：覆盖 FE-WRITING-ARCHIVE 写作档案与风格规范最小页专属业务逻辑与租户隔离单测。
// 它解决什么问题：
// 1. 【安全隔离红线】严格验证当前登录租户 company_id 强隔离（Alpha 与 Beta 独立自称、禁用词与样章）；
// 2. 验证语气偏好、自称口径（R35）与排版规范完整性；
// 3. 验证禁用词库（夸大词、采购人口吻、行业套话）多维筛选与严重度元数据；
// 4. 验证标杆样章库多维筛选与分册过滤；
// 5. 验证草稿正文快速合规扫描诊断算法（违规词检出与反常自称捕获）。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  FORBIDDEN_CATEGORY_MAP,
  getForbiddenCategoryLabel,
  getSeverityMeta,
  getVolumeLabel,
  getWritingProfile,
  filterForbiddenWords,
  filterQualitySamples,
  scanDraftText,
  DEFAULT_TYPOGRAPHY_RULES,
  DEFAULT_COMMON_FORBIDDEN_WORDS,
} from '../../src/library/writing-archive-core.ts';

/* ========================================================================= */
/* 1. 词典映射与严重度元信息测试                                              */
/* ========================================================================= */

test('FORBIDDEN_CATEGORY_MAP & getForbiddenCategoryLabel: 类别标签与友好回退', () => {
  assert.equal(getForbiddenCategoryLabel('exaggeration'), '夸大与绝对化词');
  assert.equal(getForbiddenCategoryLabel('buyer_tone'), '采购人口吻误用');
  assert.equal(getForbiddenCategoryLabel('competitor'), '第三方与竞对代称');
  assert.equal(getForbiddenCategoryLabel('cliche'), '空泛行业套话');

  // 未知或空类型回退
  assert.equal(getForbiddenCategoryLabel('other_cat'), 'other_cat');
  assert.equal(getForbiddenCategoryLabel(null), '通用词汇');
  assert.equal(getForbiddenCategoryLabel(undefined), '通用词汇');
});

test('getSeverityMeta: 违规严重度级别映射', () => {
  const blocker = getSeverityMeta('blocker');
  assert.equal(blocker.label, '强阻断');
  assert.equal(blocker.color, 'red');
  assert.equal(blocker.badgeStatus, 'error');

  const warning = getSeverityMeta('warning');
  assert.equal(warning.label, '合规警告');
  assert.equal(warning.color, 'gold');
  assert.equal(warning.badgeStatus, 'warning');

  const suggestion = getSeverityMeta('suggestion');
  assert.equal(suggestion.label, '润色建议');
  assert.equal(suggestion.color, 'blue');
  assert.equal(suggestion.badgeStatus, 'processing');

  const fallback = getSeverityMeta('custom');
  assert.equal(fallback.label, 'custom');
  assert.equal(fallback.badgeStatus, 'default');
});

test('getVolumeLabel: 分册友好名称映射', () => {
  assert.equal(getVolumeLabel('technical'), '技术分册');
  assert.equal(getVolumeLabel('business'), '商务分册');
  assert.equal(getVolumeLabel(null), '通用分册');
});

/* ========================================================================= */
/* 2. 【核心安全红线】租户公司强隔离 (Tenant Isolation)                       */
/* ========================================================================= */

test('getWritingProfile: 租户公司强隔离验证 (Alpha 与 Beta 独立配置)', () => {
  const profileAlpha = getWritingProfile('alpha');
  const profileBeta = getWritingProfile('beta');

  // 1. 公司标识与自称严格隔离
  assert.equal(profileAlpha.company_id, 'alpha');
  assert.equal(profileAlpha.self_reference, '本投标人');
  assert.equal(profileAlpha.tenderer_reference, '招标人');

  assert.equal(profileBeta.company_id, 'beta');
  assert.equal(profileBeta.self_reference, '我方');
  assert.equal(profileBeta.tenderer_reference, '业主单位');

  // 2. 样章库独立且绝对无交叉
  assert.ok(profileAlpha.quality_samples.length > 0);
  assert.ok(profileAlpha.quality_samples.every(s => s.id.includes('alpha')));

  assert.ok(profileBeta.quality_samples.length > 0);
  assert.ok(profileBeta.quality_samples.every(s => s.id.includes('beta')));

  assert.equal(
    profileAlpha.quality_samples.some(s => s.id.includes('beta')),
    false,
    'Alpha 绝不包含 Beta 样章'
  );
  assert.equal(
    profileBeta.quality_samples.some(s => s.id.includes('alpha')),
    false,
    'Beta 绝不包含 Alpha 样章'
  );

  // 3. 未知租户返回隔离的干净档案
  const profileGamma = getWritingProfile('gamma');
  assert.equal(profileGamma.company_id, 'gamma');
  assert.equal(profileGamma.quality_samples.length, 0);
});

/* ========================================================================= */
/* 3. 禁用词库筛选算法 (filterForbiddenWords)                                 */
/* ========================================================================= */

test('filterForbiddenWords: 类别、严重度与多维搜索过滤', () => {
  const words = DEFAULT_COMMON_FORBIDDEN_WORDS;

  // 1. 按类别筛选
  const buyerToneWords = filterForbiddenWords(words, { category: 'buyer_tone' });
  assert.ok(buyerToneWords.length > 0);
  assert.ok(buyerToneWords.every(w => w.category === 'buyer_tone'));

  // 2. 按严重级别筛选
  const blockerWords = filterForbiddenWords(words, { severity: 'blocker' });
  assert.ok(blockerWords.length > 0);
  assert.ok(blockerWords.every(w => w.severity === 'blocker'));

  // 3. 关键字搜索（词、理由、建议、类别）
  const search1 = filterForbiddenWords(words, { search: '第一' });
  assert.equal(search1.length, 1);
  assert.equal(search1[0].word, '业界第一');

  const search2 = filterForbiddenWords(words, { search: '反不正当竞争法' });
  assert.ok(search2.length >= 1);

  const search3 = filterForbiddenWords(words, { search: 'non_existent_key_xyz' });
  assert.equal(search3.length, 0);
});

/* ========================================================================= */
/* 4. 标杆样章库筛选算法 (filterQualitySamples)                               */
/* ========================================================================= */

test('filterQualitySamples: 分册、评分维度与关键字检索', () => {
  const profile = getWritingProfile('alpha');
  const samples = profile.quality_samples;

  // 1. 分册筛选
  const technicalSamples = filterQualitySamples(samples, { volume: 'technical' });
  assert.ok(technicalSamples.length > 0);
  assert.ok(technicalSamples.every(s => s.volume === 'technical'));

  const businessSamples = filterQualitySamples(samples, { volume: 'business' });
  assert.ok(businessSamples.length > 0);
  assert.ok(businessSamples.every(s => s.volume === 'business'));

  // 2. 关键字检索（跨标题、章节、标签、摘要）
  const kwSearch1 = filterQualitySamples(samples, { search: '双活' });
  assert.ok(kwSearch1.length >= 1);
  assert.equal(kwSearch1[0].id, 'sample-alpha-001');

  const kwSearch2 = filterQualitySamples(samples, { search: 'SLA' });
  assert.ok(kwSearch2.length >= 1);
  assert.equal(kwSearch2[0].id, 'sample-alpha-003');

  const kwSearch3 = filterQualitySamples(samples, { search: 'non_existent_sample_999' });
  assert.equal(kwSearch3.length, 0);
});

/* ========================================================================= */
/* 5. 草稿正文实时合规扫描诊断算法 (scanDraftText)                             */
/* ========================================================================= */

test('scanDraftText: 准确定位禁用词与自称口径错用', () => {
  const profile = getWritingProfile('alpha'); // self_reference = '本投标人'

  // 1. 包含禁用词与采购人口吻错用
  const riskyText = '我行在过去项目中获得了业界第一的荣誉，我司承诺绝对保证系统零缺陷运行。';
  const resultRisky = scanDraftText(riskyText, profile);

  assert.equal(resultRisky.valid, false);
  assert.ok(resultRisky.forbiddenHits.length >= 3);
  // 命中“业界第一”、“绝对保证”、“零缺陷”
  const hitWords = resultRisky.forbiddenHits.map(h => h.word);
  assert.ok(hitWords.includes('业界第一'));
  assert.ok(hitWords.includes('绝对保证'));
  assert.ok(hitWords.includes('零缺陷'));

  // 检出采购人口吻错用（“我行”、“我司”与“本投标人”不一致）
  assert.ok(resultRisky.selfReferenceMismatches.includes('我行'));
  assert.ok(resultRisky.selfReferenceMismatches.includes('我司'));
  assert.ok(resultRisky.summary.blockerCount > 0);

  // 2. 规范合规正文
  const cleanText = '本投标人针对智慧应急业务要求，采用跨机房同城双活部署模式，具备高可用容灾能力。';
  const resultClean = scanDraftText(cleanText, profile);

  assert.equal(resultClean.valid, true);
  assert.equal(resultClean.forbiddenHits.length, 0);
  assert.equal(resultClean.selfReferenceMismatches.length, 0);
  assert.equal(resultClean.summary.blockerCount, 0);
  assert.ok(resultClean.totalWordCount > 0);

  // 3. 空输入防御
  const emptyRes = scanDraftText('', profile);
  assert.equal(emptyRes.valid, true);
  assert.equal(emptyRes.totalWordCount, 0);
});

/* ========================================================================= */
/* 6. 排版规范清单完整性测试                                                 */
/* ========================================================================= */

test('DEFAULT_TYPOGRAPHY_RULES: 包含国家公文与标书排版核心规范', () => {
  assert.ok(DEFAULT_TYPOGRAPHY_RULES.length >= 5);
  const categories = DEFAULT_TYPOGRAPHY_RULES.map(r => r.category);
  assert.ok(categories.includes('标点规范'));
  assert.ok(categories.includes('字符规范'));
  assert.ok(categories.includes('度量规范'));
  assert.ok(categories.includes('层级规范'));

  // 每条规范包含明确的错误与推荐示例
  for (const rule of DEFAULT_TYPOGRAPHY_RULES) {
    assert.ok(rule.rule_name.length > 0);
    assert.ok(rule.standard.length > 0);
    assert.ok(rule.bad_case !== undefined);
    assert.ok(rule.good_case !== undefined);
  }
});
