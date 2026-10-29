// 为什么有这个文件：验证“只写技术标”项目在前端只出现技术分册（用户 2026-10-29 要求，不一定要合标）。
// 它解决什么问题：定稿判断、团队提交、筛选项与导出页原先都写死技术+商务两册。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { projectVolumes, technicalOnly, volumeMode, volumeOptions } from '../../src/project/project-volumes.ts';
import { areAllVolumesFinalized } from '../../src/project/volume-api.ts';
import { teamPayload } from '../../src/project/project-team.ts';

test('volume mode comes from the project, falling back to the team, default both', () => {
  assert.equal(volumeMode(null), 'both');
  assert.deepEqual(projectVolumes({ project: { volume_mode: 'technical_only' } }), ['technical']);
  assert.equal(technicalOnly({ team: { volume_mode: 'technical_only' } }), true);
  assert.deepEqual(volumeOptions({ project: { volume_mode: 'technical_only' } }, true), [{ value: 'technical', label: '技术分册' }]);
  assert.equal(volumeOptions({}, true).length, 3);
});

test('finalized means every volume the backend returned is finalized', () => {
  assert.equal(areAllVolumesFinalized([{ volume_id: 'technical', is_finalized: true }]), true);
  assert.equal(areAllVolumesFinalized([{ volume_id: 'technical', is_finalized: true }, { volume_id: 'business', is_finalized: false }]), false);
  assert.equal(areAllVolumesFinalized([]), false);
});

test('team payload for a technical-only project sends one owner row', () => {
  const accounts = [{ id: 'm', role: 'manager' }, { id: 'w', role: 'editor' }];
  const payload = teamPayload({ members: [{ user_id: 'm', project_role: 'lead', volumes: [] }, { user_id: 'w', project_role: 'writer', volumes: ['technical', 'business'] }],
    technical_owner_id: 'm', business_owner_id: 'w', assembly_owner_id: null, reason: '只写技术标' }, accounts, ['technical']);
  assert.deepEqual(payload.volumes, [{ volume: 'technical', owner_id: 'm' }]);
  assert.deepEqual(payload.members.map(m => m.volumes), [['technical'], ['technical']]);
});

test('create modal offers the technical-only choice and export page explains no merge', () => {
  assert.match(readFileSync(new URL('../../src/project/CreateProjectModal.tsx', import.meta.url), 'utf8'), /volume_mode/);
  assert.match(readFileSync(new URL('../../src/project/ProjectPages.tsx', import.meta.url), 'utf8'), /本项目只写技术标，不需要合标/);
  assert.match(readFileSync(new URL('../../src/app/App.tsx', import.meta.url), 'utf8'), /volume_mode: values\.volume_mode === 'technical_only'/);
});
