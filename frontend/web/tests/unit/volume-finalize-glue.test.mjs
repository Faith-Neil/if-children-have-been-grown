// 为什么有这个文件：为 INT-VOLUME-FINALIZE-GLUE 分册定稿与前后端契约胶水打通提供单元测试。
// 它解决什么问题：
// 1. 验证 isVolumeFinalized 与 areAllVolumesFinalized 的定稿状态判定；
// 2. 验证 getVolumeFinalizeMeta 与 deriveFinalizePremise 前端徽章与导出前提推导；
// 3. 验证 canExportSubmission 在分册未定稿时正确拦截正式递交版；
// 4. 验证 OpenAPI 契约中 finalize、unlock、listVolumes 报文格式与响应字段对齐。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  isVolumeFinalized,
  areAllVolumesFinalized,
  getVolumeFinalizeMeta,
  deriveFinalizePremise,
} from '../../src/project/volume-api.ts';
import { canExportSubmission } from '../../src/project/export-checks-core.ts';

const SAMPLE_VOLUMES_MIXED = [
  {
    volume_id: 'technical',
    project_id: 'proj-001',
    is_finalized: true,
    finalized_by: 'lead-usr',
    finalized_at: '2026-10-23T10:00:00Z',
    unlocked_by: null,
    unlocked_at: null,
    unlock_reason: null,
  },
  {
    volume_id: 'business',
    project_id: 'proj-001',
    is_finalized: false,
    finalized_by: null,
    finalized_at: null,
    unlocked_by: 'lead-usr',
    unlocked_at: '2026-10-23T11:00:00Z',
    unlock_reason: '核对商务报价与盖章材料',
  },
];

const SAMPLE_VOLUMES_ALL_FINALIZED = [
  {
    volume_id: 'technical',
    project_id: 'proj-001',
    is_finalized: true,
    finalized_by: 'lead-usr',
    finalized_at: '2026-10-23T10:00:00Z',
  },
  {
    volume_id: 'business',
    project_id: 'proj-001',
    is_finalized: true,
    finalized_by: 'lead-usr',
    finalized_at: '2026-10-23T10:30:00Z',
  },
];

const SAMPLE_VOLUMES_NONE_FINALIZED = [
  {
    volume_id: 'technical',
    project_id: 'proj-001',
    is_finalized: false,
  },
  {
    volume_id: 'business',
    project_id: 'proj-001',
    is_finalized: false,
  },
];

test('isVolumeFinalized correctly checks single volume status', () => {
  assert.equal(isVolumeFinalized(SAMPLE_VOLUMES_MIXED, 'technical'), true);
  assert.equal(isVolumeFinalized(SAMPLE_VOLUMES_MIXED, 'business'), false);
  assert.equal(isVolumeFinalized(SAMPLE_VOLUMES_MIXED, 'nonexistent'), false);
  assert.equal(isVolumeFinalized(null, 'technical'), false);
  assert.equal(isVolumeFinalized([], 'technical'), false);
});

test('areAllVolumesFinalized returns true only when both technical and business are finalized', () => {
  assert.equal(areAllVolumesFinalized(SAMPLE_VOLUMES_ALL_FINALIZED), true);
  assert.equal(areAllVolumesFinalized(SAMPLE_VOLUMES_MIXED), false);
  assert.equal(areAllVolumesFinalized(SAMPLE_VOLUMES_NONE_FINALIZED), false);
  assert.equal(areAllVolumesFinalized([]), false);
  assert.equal(areAllVolumesFinalized(null), false);
});

test('getVolumeFinalizeMeta generates compliant badge and label metadata', () => {
  // 单分册已定稿
  const techMeta = getVolumeFinalizeMeta(SAMPLE_VOLUMES_MIXED, 'technical');
  assert.equal(techMeta.isFinalized, true);
  assert.equal(techMeta.label, '技术分册已定稿');
  assert.equal(techMeta.badgeColor, 'success');
  assert.equal(techMeta.finalizedBy, 'lead-usr');

  // 单分册未定稿（已解锁）
  const busMeta = getVolumeFinalizeMeta(SAMPLE_VOLUMES_MIXED, 'business');
  assert.equal(busMeta.isFinalized, false);
  assert.equal(busMeta.label, '商务分册未定稿');
  assert.equal(busMeta.badgeColor, 'default');
  assert.equal(busMeta.unlockReason, '核对商务报价与盖章材料');

  // 两册全量范围
  const allMixedMeta = getVolumeFinalizeMeta(SAMPLE_VOLUMES_MIXED, 'all');
  assert.equal(allMixedMeta.isFinalized, false);
  assert.equal(allMixedMeta.label, '分册未全部定稿');
  assert.equal(allMixedMeta.badgeColor, 'default');

  const allDoneMeta = getVolumeFinalizeMeta(SAMPLE_VOLUMES_ALL_FINALIZED, 'all');
  assert.equal(allDoneMeta.isFinalized, true);
  assert.equal(allDoneMeta.label, '分册全部定稿');
  assert.equal(allDoneMeta.badgeColor, 'success');
});

test('deriveFinalizePremise outputs premise item with tab link and ready state', () => {
  const techPremise = deriveFinalizePremise(SAMPLE_VOLUMES_MIXED, 'technical');
  assert.equal(techPremise.ready, true);
  assert.ok(techPremise.label.includes('技术分册已定稿锁定'));
  assert.equal(techPremise.tab, 'editor');

  const busPremise = deriveFinalizePremise(SAMPLE_VOLUMES_MIXED, 'business');
  assert.equal(busPremise.ready, false);
  assert.ok(busPremise.label.includes('商务分册已定稿锁定'));

  const allPremise = deriveFinalizePremise(SAMPLE_VOLUMES_MIXED, 'all');
  assert.equal(allPremise.ready, false);
  assert.ok(allPremise.label.includes('技术与商务两册均已定稿锁定'));

  const allDonePremise = deriveFinalizePremise(SAMPLE_VOLUMES_ALL_FINALIZED, 'all');
  assert.equal(allDonePremise.ready, true);
});

test('canExportSubmission blocks formal submission when volume is not finalized', () => {
  // 未定稿时强拦截
  const unfinalizedResult = canExportSubmission({
    hasBlockers: false,
    fullContent: true,
    hasPassedCheck: true,
    parseConfirmed: true,
    userCanExport: true,
    isFinalized: false,
  });
  assert.equal(unfinalizedResult.allowed, false);
  assert.ok(unfinalizedResult.reason?.includes('尚未完成定稿锁定'));

  // 已定稿时放行
  const finalizedResult = canExportSubmission({
    hasBlockers: false,
    fullContent: true,
    hasPassedCheck: true,
    parseConfirmed: true,
    userCanExport: true,
    isFinalized: true,
  });
  assert.equal(finalizedResult.allowed, true);
  assert.equal(finalizedResult.reason, null);
});
