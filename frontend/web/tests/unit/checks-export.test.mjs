// 为什么有这个文件：为合规检查红线门禁（APP-M2-T195）与整本递交版导出（APP-M2-T196）提供纯逻辑单元测试。
// 它解决什么问题：
// 1. 验证 isBlocker 对各类阻断严重级别的判定；
// 2. 验证 deriveBlockerSummary 从检查结果中提取 blocker 缺陷并按章节精准聚合；
// 3. 验证 canExportSubmission 落实 PRD 核心红线门禁：有阻断缺陷强行禁止递交版导出；
// 4. 验证 formatFileSize、formatSha256Fingerprint、getExportKindMeta 与分册文案生成。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  isBlocker,
  deriveBlockerSummary,
  canExportSubmission,
  formatFileSize,
  formatSha256Fingerprint,
  getExportKindMeta,
  getExportVolumeLabel,
} from '../../src/project/export-checks-core.ts';

test('isBlocker accurately identifies blocker severity levels', () => {
  assert.equal(isBlocker('blocker'), true);
  assert.equal(isBlocker('BLOCKER'), true);
  assert.equal(isBlocker('fatal'), true);
  assert.equal(isBlocker('critical'), true);
  assert.equal(isBlocker('error'), true);
  assert.equal(isBlocker('blocking'), true);

  assert.equal(isBlocker('warning'), false);
  assert.equal(isBlocker('info'), false);
  assert.equal(isBlocker('notice'), false);
  assert.equal(isBlocker(null), false);
  assert.equal(isBlocker(undefined), false);
  assert.equal(isBlocker(''), false);
});

test('deriveBlockerSummary handles empty or clean checks with 0 blockers', () => {
  const cleanSummary = deriveBlockerSummary(null, []);
  assert.equal(cleanSummary.hasBlockers, false);
  assert.equal(cleanSummary.totalBlockers, 0);
  assert.equal(cleanSummary.blockedChapters.length, 0);

  const checkWithoutBlocker = {
    id: 'chk-1',
    volume: 'technical',
    passed: true,
    status: 'valid',
    issues: [
      { id: 'i-1', code: 'W01', severity: 'warning', message: '建议精简字数' },
      { id: 'i-2', code: 'N01', severity: 'info', message: '已使用通用格式' },
    ],
    coverage: { implemented_rules: [], unimplemented_rules: [], complete: true },
    fingerprint: 'fp-1',
    created_at: '2026-10-22T10:00:00Z',
  };

  const summary = deriveBlockerSummary(checkWithoutBlocker, []);
  assert.equal(summary.hasBlockers, false);
  assert.equal(summary.totalBlockers, 0);
  assert.equal(summary.blockedChapters.length, 0);
});

test('deriveBlockerSummary groups blocker issues by chapter and resolves chapter titles', () => {
  const chapters = [
    { id: 'ch-1', title: '第一章 投标总说明', volume: 'technical', revision: 1, content: '正文' },
    { id: 'ch-2', title: '第二章 服务质量与SLA保障', volume: 'technical', revision: 2, content: '正文' },
  ];

  const checkWithBlockers = {
    id: 'chk-2',
    volume: 'technical',
    passed: false,
    status: 'valid',
    issues: [
      { id: 'i-1', code: 'R44_STAR_CLAUSE_MISSING', severity: 'blocker', message: '星号条款未完全覆盖', chapter_id: 'ch-1' },
      { id: 'i-2', code: 'R15_EVIDENCE_EXPIRED', severity: 'fatal', message: '核心资质证明已过期', chapter_id: 'ch-2' },
      { id: 'i-3', code: 'R15_EVIDENCE_MISSING', severity: 'blocker', message: '缺少社保证明文件', chapter_id: 'ch-2' },
      { id: 'i-4', code: 'R08_FACT_CONFLICT', severity: 'critical', message: '投标金额与明细表不一致', requirement_id: 'req-9' },
      { id: 'i-5', code: 'W02_FORMAT', severity: 'warning', message: '普通版式警告' },
    ],
    coverage: { implemented_rules: [], unimplemented_rules: [], complete: false },
    fingerprint: 'fp-2',
    created_at: '2026-10-22T12:00:00Z',
  };

  const summary = deriveBlockerSummary(checkWithBlockers, chapters);
  assert.equal(summary.hasBlockers, true);
  assert.equal(summary.totalBlockers, 4, 'Should extract exactly 4 blockers');
  assert.equal(summary.blockedChapters.length, 3, 'Grouped into 3 locations: ch-1, ch-2, and requirement');

  const ch1 = summary.blockedChapters.find(c => c.chapterId === 'ch-1');
  assert.ok(ch1);
  assert.equal(ch1.chapterTitle, '第一章 投标总说明');
  assert.equal(ch1.blockerCount, 1);
  assert.deepEqual(ch1.rules, ['R44_STAR_CLAUSE_MISSING']);

  const ch2 = summary.blockedChapters.find(c => c.chapterId === 'ch-2');
  assert.ok(ch2);
  assert.equal(ch2.chapterTitle, '第二章 服务质量与SLA保障');
  assert.equal(ch2.blockerCount, 2);

  const globalLoc = summary.blockedChapters.find(c => c.chapterId === 'global_non_chapter');
  assert.ok(globalLoc);
  assert.equal(globalLoc.chapterTitle, '服务承诺矩阵 / 招标原文');
});

test('canExportSubmission strictly enforces redline blocker gate', () => {
  // 1. 存在 blocker 缺陷：绝对阻断递交版
  const blockedResult = canExportSubmission({
    hasBlockers: true,
    blockerCount: 3,
    fullContent: true,
    hasPassedCheck: true,
    parseConfirmed: true,
    userCanExport: true,
  });
  assert.equal(blockedResult.allowed, false);
  assert.ok(blockedResult.reason?.includes('3 项阻断性合规缺陷'));

  // 2. 无 blocker 但未确认招标文件解析：阻断
  const unparsedResult = canExportSubmission({
    hasBlockers: false,
    fullContent: true,
    hasPassedCheck: true,
    parseConfirmed: false,
    userCanExport: true,
  });
  assert.equal(unparsedResult.allowed, false);
  assert.ok(unparsedResult.reason?.includes('解析结果尚未人工确认'));

  // 3. 无 blocker 但正文未提交完整：阻断
  const incompleteResult = canExportSubmission({
    hasBlockers: false,
    fullContent: false,
    hasPassedCheck: true,
    parseConfirmed: true,
    userCanExport: true,
  });
  assert.equal(incompleteResult.allowed, false);
  assert.ok(incompleteResult.reason?.includes('正文尚未全部提交完成'));

  // 4. 无有效检查通过：阻断
  const noCheckResult = canExportSubmission({
    hasBlockers: false,
    fullContent: true,
    hasPassedCheck: false,
    parseConfirmed: true,
    userCanExport: true,
  });
  assert.equal(noCheckResult.allowed, false);
  assert.ok(noCheckResult.reason?.includes('尚未运行有效检查') || noCheckResult.reason?.includes('检查未通过'));

  // 5. 全部前提就绪且 0 阻断：放行
  const allowedResult = canExportSubmission({
    hasBlockers: false,
    fullContent: true,
    hasPassedCheck: true,
    parseConfirmed: true,
    userCanExport: true,
  });
  assert.equal(allowedResult.allowed, true);
  assert.equal(allowedResult.reason, null);
});

test('formatFileSize formats byte sizes with readable units and deterministic fallback', () => {
  assert.equal(formatFileSize(512), '512 B');
  assert.equal(formatFileSize(2048), '2.0 KB');
  assert.equal(formatFileSize(2621440), '2.50 MB');

  // 种子兜底推导
  const seedSize1 = formatFileSize(null, 'export-snapshot-001');
  const seedSize2 = formatFileSize(undefined, 'export-snapshot-001');
  assert.ok(seedSize1.endsWith('MB'));
  assert.equal(seedSize1, seedSize2, 'Deterministic size for same seed');

  assert.equal(formatFileSize(null, ''), '—');
});

test('formatSha256Fingerprint formats clean sha256 with full & short display', () => {
  const fullHex = 'a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef';
  const meta = formatSha256Fingerprint(`sha256:${fullHex}`);
  assert.equal(meta.full, `sha256:${fullHex}`);
  assert.equal(meta.short, 'sha256:a1b2c3d4e5...');

  // 确定性 fallback 生成
  const generatedMeta = formatSha256Fingerprint(null, 'project-export-123');
  assert.ok(generatedMeta.full.startsWith('sha256:'));
  assert.equal(generatedMeta.full.length, 71); // 'sha256:' (7) + 64 hex
  assert.ok(generatedMeta.short.endsWith('...'));
});

test('getExportKindMeta and getExportVolumeLabel return standard ICG labels', () => {
  const subMeta = getExportKindMeta('submission');
  assert.equal(subMeta.label, '正式递交版');
  assert.equal(subMeta.isSubmission, true);
  assert.equal(subMeta.tagColor, 'green');

  const internalMeta = getExportKindMeta('internal');
  assert.equal(internalMeta.label, '内部评审稿');
  assert.equal(internalMeta.isSubmission, false);
  assert.equal(internalMeta.tagColor, 'blue');

  assert.equal(getExportVolumeLabel('technical'), '技术分册');
  assert.equal(getExportVolumeLabel('business'), '商务分册');
  assert.equal(getExportVolumeLabel('all'), '技术、商务两册合订');
});
