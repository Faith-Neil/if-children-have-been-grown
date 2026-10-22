// 为什么有这个文件：验证业务小组件（LevelTag、AiTag、DirectTag、Cite、SourceBar）的核心纯函数、色彩规范与对比度。
// 它解决什么问题：
// 1. 严格防范 AI 紫外溢，确保只有 AiTag 使用 AI 紫色阶；
// 2. 验证所有标签文字在白底及对应浅色背景上的对比度均严格符合 WCAG AA 4.5:1 标准；
// 3. 验证各级别标签、AI变体、系统直查标签、引用元信息与段落来源条的数据解析逻辑。

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  BIZ_COLOR_TOKENS,
  contrastRatio,
  isAiColor,
  assertNotAiColor,
  resolveLevelTag,
  resolveAiTag,
  resolveDirectTag,
  resolveCite,
  resolveSourceBar,
  formatFingerprint,
} from '../../src/library/business-tags.ts';

test('WCAG 4.5:1 text contrast compliance for all business tag colors', () => {
  const white = '#FFFFFF';

  // 1. 阻断与废标条款（实心红底白字对比度 >= 4.5:1；浅底红字对比度 >= 4.5:1）
  const blockerSolidRatio = contrastRatio(BIZ_COLOR_TOKENS.blockerSolidText, BIZ_COLOR_TOKENS.blockerSolidBg);
  assert.ok(blockerSolidRatio >= 4.5, `blocker solid contrast ${blockerSolidRatio.toFixed(2)} must be >= 4.5`);

  const blockerSubtleRatio = contrastRatio(BIZ_COLOR_TOKENS.blockerSubtleText, BIZ_COLOR_TOKENS.blockerSubtleBg);
  assert.ok(blockerSubtleRatio >= 4.5, `blocker subtle contrast ${blockerSubtleRatio.toFixed(2)} must be >= 4.5`);

  // 2. 星号与关键要求条款
  const starSubtleRatio = contrastRatio(BIZ_COLOR_TOKENS.starText, BIZ_COLOR_TOKENS.starBg);
  assert.ok(starSubtleRatio >= 4.5, `star subtle contrast ${starSubtleRatio.toFixed(2)} must be >= 4.5`);

  // 3. 警告标签（黄色/深橙色文字）
  const warningRatio = contrastRatio(BIZ_COLOR_TOKENS.warningText, BIZ_COLOR_TOKENS.warningBg);
  assert.ok(warningRatio >= 4.5, `warning contrast ${warningRatio.toFixed(2)} must be >= 4.5`);

  // 4. 加分项 / 评分项（青色）
  const bonusRatio = contrastRatio(BIZ_COLOR_TOKENS.bonusText, BIZ_COLOR_TOKENS.bonusBg);
  assert.ok(bonusRatio >= 4.5, `bonus contrast ${bonusRatio.toFixed(2)} must be >= 4.5`);

  // 5. 资格要求（极客蓝）
  const qualRatio = contrastRatio(BIZ_COLOR_TOKENS.qualificationText, BIZ_COLOR_TOKENS.qualificationBg);
  assert.ok(qualRatio >= 4.5, `qualification contrast ${qualRatio.toFixed(2)} must be >= 4.5`);

  // 6. 一般条款（中性灰）
  const generalRatio = contrastRatio(BIZ_COLOR_TOKENS.generalText, BIZ_COLOR_TOKENS.generalBg);
  assert.ok(generalRatio >= 4.5, `general clause contrast ${generalRatio.toFixed(2)} must be >= 4.5`);

  // 7. AI 紫色标签（白底实心与浅紫底文字）
  const aiSolidRatio = contrastRatio(BIZ_COLOR_TOKENS.aiSolidText, BIZ_COLOR_TOKENS.aiSolidBg);
  assert.ok(aiSolidRatio >= 4.5, `ai solid contrast ${aiSolidRatio.toFixed(2)} must be >= 4.5`);

  const aiSubtleRatio = contrastRatio(BIZ_COLOR_TOKENS.aiSubtleText, BIZ_COLOR_TOKENS.aiSubtleBg);
  assert.ok(aiSubtleRatio >= 4.5, `ai subtle contrast ${aiSubtleRatio.toFixed(2)} must be >= 4.5`);

  // 8. 答案卡 / 直接采用（深蓝系统直查）
  const directRatio = contrastRatio(BIZ_COLOR_TOKENS.directText, BIZ_COLOR_TOKENS.directBg);
  assert.ok(directRatio >= 4.5, `direct tag contrast ${directRatio.toFixed(2)} must be >= 4.5`);

  // 9. 变量事实行内高亮
  const varRatio = contrastRatio(BIZ_COLOR_TOKENS.varText, BIZ_COLOR_TOKENS.varBg);
  assert.ok(varRatio >= 4.5, `var text contrast ${varRatio.toFixed(2)} must be >= 4.5`);

  // 10. 人工编写与方案片段段落色
  const manualRatio = contrastRatio(BIZ_COLOR_TOKENS.srcManualText, BIZ_COLOR_TOKENS.srcManualBg);
  assert.ok(manualRatio >= 4.5, `manual text contrast ${manualRatio.toFixed(2)} must be >= 4.5`);

  const snippetRatio = contrastRatio(BIZ_COLOR_TOKENS.srcSnippetText, BIZ_COLOR_TOKENS.srcSnippetBg);
  assert.ok(snippetRatio >= 4.5, `snippet text contrast ${snippetRatio.toFixed(2)} must be >= 4.5`);
});

test('strict AI purple isolation rule: AI purple only appears on AiTag', () => {
  // 1. isAiColor 正确识别 AI 紫色阶
  assert.equal(isAiColor('#6E4BD8'), true, '#6E4BD8 is primary AI purple');
  assert.equal(isAiColor('#A23CC8'), true, '#A23CC8 is assistant purple');
  assert.equal(isAiColor('#5329B3'), true, '#5329B3 is subtle AI text');
  assert.equal(isAiColor('#F2EEFC'), true, '#F2EEFC is subtle AI bg');

  // 2. 正常业务颜色不被误报为 AI 紫
  assert.equal(isAiColor('#1E4DB7'), false, '#1E4DB7 is primary blue');
  assert.equal(isAiColor('#D9363E'), false, '#D9363E is red');
  assert.equal(isAiColor('#2B9D5C'), false, '#2B9D5C is green');
  assert.equal(isAiColor('#0E8A8A'), false, '#0E8A8A is cyan snippet');
  assert.equal(isAiColor('#4E5969'), false, '#4E5969 is neutral text');

  // 3. assertNotAiColor 防守性检测
  assert.doesNotThrow(() => assertNotAiColor('LevelTag', '#D9363E'));
  assert.doesNotThrow(() => assertNotAiColor('DirectTag', '#1E4DB7'));
  assert.throws(
    () => assertNotAiColor('DirectTag', '#6E4BD8'),
    /ICG 色彩规范违规/
  );
  assert.throws(
    () => assertNotAiColor('LevelTag', '#A23CC8'),
    /ICG 色彩规范违规/
  );
});

test('resolveLevelTag handles clause categories and solid/subtle modes', () => {
  // 1. 阻断项（默认实心红）
  const blockerRes = resolveLevelTag('blocker');
  assert.equal(blockerRes.category, 'blocker');
  assert.equal(blockerRes.label, '阻断');
  assert.equal(blockerRes.isSolid, true);
  assert.equal(blockerRes.bg, BIZ_COLOR_TOKENS.blockerSolidBg);
  assert.equal(blockerRes.color, BIZ_COLOR_TOKENS.blockerSolidText);

  // 2. 废标条款 / 否决项（识别中文和英文 void）
  const voidRes = resolveLevelTag('void');
  assert.equal(voidRes.category, 'blocker');
  assert.equal(voidRes.label, '废标条款');

  const vetoRes = resolveLevelTag('否决项');
  assert.equal(vetoRes.category, 'blocker');
  assert.equal(vetoRes.label, '否决项');

  // 3. 星号与关键要求
  const starRes = resolveLevelTag('star');
  assert.equal(starRes.category, 'star');
  assert.equal(starRes.label, '星号条款');
  assert.equal(starRes.bg, BIZ_COLOR_TOKENS.starBg);
  assert.equal(starRes.color, BIZ_COLOR_TOKENS.starText);

  const criticalRes = resolveLevelTag('关键要求');
  assert.equal(criticalRes.category, 'star');
  assert.equal(criticalRes.label, '关键要求');

  // 4. 加分项与评分项
  const bonusRes = resolveLevelTag('加分项');
  assert.equal(bonusRes.category, 'bonus');
  assert.equal(bonusRes.label, '加分项');
  assert.equal(bonusRes.color, BIZ_COLOR_TOKENS.bonusText);

  const scoringRes = resolveLevelTag('scoring');
  assert.equal(scoringRes.category, 'bonus');
  assert.equal(scoringRes.label, '评分项');

  // 5. 资格要求
  const qualRes = resolveLevelTag('qualification');
  assert.equal(qualRes.category, 'qualification');
  assert.equal(qualRes.label, '资格要求');
  assert.equal(qualRes.color, BIZ_COLOR_TOKENS.qualificationText);

  // 6. 一般条款
  const genRes = resolveLevelTag('general');
  assert.equal(genRes.category, 'general');
  assert.equal(genRes.label, '一般条款');
  assert.equal(genRes.color, BIZ_COLOR_TOKENS.generalText);

  // 7. 自定义覆盖 label
  const customRes = resolveLevelTag('star', { customLabel: '★ 核心响应指标' });
  assert.equal(customRes.label, '★ 核心响应指标');
});

test('resolveAiTag properly sets AI purple palette and variant labels', () => {
  // suggestion
  const sugRes = resolveAiTag('suggestion');
  assert.equal(sugRes.label, 'AI 建议');
  assert.equal(sugRes.isSolid, false);
  assert.equal(sugRes.bg, BIZ_COLOR_TOKENS.aiSubtleBg);
  assert.equal(sugRes.color, BIZ_COLOR_TOKENS.aiSubtleText);

  // candidate
  const candRes = resolveAiTag('candidate');
  assert.equal(candRes.label, '整章候选');

  // generated
  const genRes = resolveAiTag('generated', { isSolid: true });
  assert.equal(genRes.label, 'AI 生成');
  assert.equal(genRes.isSolid, true);
  assert.equal(genRes.bg, BIZ_COLOR_TOKENS.aiSolidBg);
  assert.equal(genRes.color, BIZ_COLOR_TOKENS.aiSolidText);

  // demo / model / assistant
  assert.equal(resolveAiTag('demo').label, '演示建议');
  assert.equal(resolveAiTag('model').label, '模型建议');
  assert.equal(resolveAiTag('assistant').label, '助手建议');
});

test('resolveDirectTag uses system direct blue and rejects AI purple', () => {
  const directRes = resolveDirectTag('direct');
  assert.equal(directRes.label, '系统直查 · 未经模型');
  assert.equal(directRes.bg, BIZ_COLOR_TOKENS.directBg);
  assert.equal(directRes.color, BIZ_COLOR_TOKENS.directText);
  assert.equal(isAiColor(directRes.color), false);

  const adoptRes = resolveDirectTag('adopt');
  assert.equal(adoptRes.label, '直接采用');

  const respRes = resolveDirectTag('response');
  assert.equal(respRes.label, '直接响应');
});

test('resolveCite handles evidence, snippet, tender, fact, and none types', () => {
  // 1. 证据资料引用
  const evCite = resolveCite('evidence', undefined, { title: '东海银行维保合同', version: 2 });
  assert.equal(evCite.type, 'evidence');
  assert.equal(evCite.marker, '[证·v2]');
  assert.equal(evCite.isSuperscript, true);
  assert.equal(evCite.metadata.title, '东海银行维保合同');

  // 2. 方案片段引用
  const snCite = resolveCite('snippet', undefined, { title: '应急演练方案', version: 1 });
  assert.equal(snCite.type, 'snippet');
  assert.equal(snCite.marker, '[片·v1]');
  assert.equal(snCite.isSuperscript, true);

  // 3. 招标原文页码引用
  const tdCite = resolveCite('tender', undefined, { page: 47, quote: '7*24小时技术服务要求' });
  assert.equal(tdCite.type, 'tender');
  assert.equal(tdCite.marker, 'P.47');
  assert.equal(tdCite.isSuperscript, true);

  // 4. 项目事实变量高亮（不上标，黄底带下划线）
  const factCite = resolveCite('fact', undefined, { title: '项目服务期 (36个月)' });
  assert.equal(factCite.type, 'fact');
  assert.equal(factCite.marker, '项目服务期 (36个月)');
  assert.equal(factCite.isSuperscript, false);
  assert.equal(factCite.hasUnderline, true);
  assert.equal(factCite.bg, BIZ_COLOR_TOKENS.varBg);

  // 5. 无来源标签
  const noneCite = resolveCite('none');
  assert.equal(noneCite.type, 'none');
  assert.equal(noneCite.marker, '无知识库来源');
  assert.equal(noneCite.isSuperscript, false);
});

test('resolveSourceBar and formatFingerprint handle provenance metadata and stale status', () => {
  // 1. formatFingerprint
  assert.equal(formatFingerprint(null), '无依据指纹');
  assert.equal(formatFingerprint(''), '无依据指纹');
  assert.equal(formatFingerprint('abc12345'), 'fp:abc12345');
  assert.equal(formatFingerprint('7a8b9c0d1e2f3g4h5i6j7k8l'), 'fp:7a8b9c0d...');

  // 2. 正常已确认证据来源条
  const confirmedRes = resolveSourceBar({
    kind: 'evidence',
    sourceName: '数据库维保方案',
    version: 3,
    fingerprint: '9f8e7d6c5b4a',
    status: 'confirmed',
  });
  assert.equal(confirmedRes.kind, 'evidence');
  assert.equal(confirmedRes.kindLabel, '资料证据');
  assert.equal(confirmedRes.sourceName, '数据库维保方案');
  assert.equal(confirmedRes.versionLabel, 'v3');
  assert.equal(confirmedRes.isStale, false);
  assert.equal(confirmedRes.statusLabel, '已确认');
  assert.equal(confirmedRes.formattedFingerprint, 'fp:9f8e7d6c...');

  // 3. 来源已变化（stale）条目
  const staleRes = resolveSourceBar({
    kind: 'snippet',
    sourceName: '旧架构说明',
    version: 1,
    status: 'stale',
  });
  assert.equal(staleRes.isStale, true);
  assert.equal(staleRes.statusLabel, '来源已变化待核对');

  // 4. 7 种段落来源类型全覆盖
  const kinds = ['evidence', 'snippet', 'tender', 'model', 'assistant', 'manual', 'system'];
  for (const k of kinds) {
    const res = resolveSourceBar({ kind: k });
    assert.ok(res.kindLabel, `Kind label should be populated for ${k}`);
    assert.ok(res.color, `Kind color should be populated for ${k}`);
  }
});
