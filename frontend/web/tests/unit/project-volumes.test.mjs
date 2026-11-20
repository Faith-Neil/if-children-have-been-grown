// 为什么有这个文件：验证技术方案路径兼容层（API volume_mode）与创建请求写死。
// 它解决什么问题：产品取消分册模式选择后，前端仍按后端字段隐藏商务路径入口。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { projectVolumes, technicalOnly, volumeMode, volumeOptions } from '../../src/project/project-volumes.ts';
import { areAllVolumesFinalized } from '../../src/project/volume-api.ts';
import { teamPayload } from '../../src/project/project-team.ts';

test('product is technical-bid only regardless of legacy volume_mode', () => {
  assert.equal(volumeMode(null), 'technical_only');
  assert.equal(volumeMode({ project: { volume_mode: 'both' } }), 'technical_only');
  assert.deepEqual(projectVolumes({ project: { volume_mode: 'technical_only' } }), ['technical']);
  assert.deepEqual(projectVolumes({ project: { volume_mode: 'both' } }), ['technical']);
  assert.equal(technicalOnly({ team: { volume_mode: 'both' } }), true);
  assert.deepEqual(volumeOptions(null, true), [{ value: 'technical', label: '技术方案' }]);
});

test('finalized means every volume the backend returned is finalized', () => {
  assert.equal(areAllVolumesFinalized([{ volume_id: 'technical', is_finalized: true }]), true);
  assert.equal(areAllVolumesFinalized([{ volume_id: 'technical', is_finalized: true }, { volume_id: 'business', is_finalized: false }]), false);
  assert.equal(areAllVolumesFinalized([]), false);
});

test('team payload for a technical-only project sends one owner row', () => {
  const accounts = [{ id: 'm', role: 'manager' }, { id: 'w', role: 'editor' }];
  const payload = teamPayload({ members: [{ user_id: 'm', project_role: 'lead', volumes: [] }, { user_id: 'w', project_role: 'writer', volumes: ['technical', 'business'] }],
    technical_owner_id: 'm', business_owner_id: 'w', assembly_owner_id: null, reason: '技术方案路径' }, accounts, ['technical']);
  assert.deepEqual(payload.volumes, [{ volume: 'technical', owner_id: 'm' }]);
  assert.deepEqual(payload.members.map(m => m.volumes), [['technical'], ['technical']]);
});

test('create modal has no volume_mode control; App hardcodes technical_only for API', () => {
  const modal = readFileSync(new URL('../../src/project/CreateProjectModal.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(modal, /volume_mode/);
  assert.doesNotMatch(modal, /volume-mode-radio/);
  assert.doesNotMatch(modal, /只写技术标|技术\+商务|分册模式/);
  const pages = readFileSync(new URL('../../src/project/ProjectPages.tsx', import.meta.url), 'utf8');
  assert.match(pages, /导出内部稿/);
  assert.doesNotMatch(pages, /导出前提/);
  assert.doesNotMatch(pages, /VolumeFinalizePanel/);
  assert.doesNotMatch(pages, /只写技术标/);
  assert.match(readFileSync(new URL('../../src/app/App.tsx', import.meta.url), 'utf8'), /volume_mode: 'technical_only'/);
  assert.doesNotMatch(readFileSync(new URL('../../src/app/App.tsx', import.meta.url), 'utf8'), /企业资料库|写作档案/);
});
