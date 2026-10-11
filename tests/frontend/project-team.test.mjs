// 为什么有这个文件：验证页面实际使用的项目分工、权限和撤权保护函数。
// 它解决什么问题：公司经理不能被页面误当成所有项目负责人，错误分册分工不能保存，撤权不会清掉未保存文字的依据。
import test from 'node:test';
import assert from 'node:assert/strict';
import { assignmentCandidates, chapterCan, eligibleOwners, freezeWorkspace, planScopes, projectAccessLost, projectCan, teamBasis, teamFormValues, teamPayload, volumeOperationAllowed } from '../../frontend/web/src/project-team.ts';

const accounts = [{ id: 'lead', role: 'manager' }, { id: 'tech', role: 'editor' }, { id: 'biz', role: 'editor' }, { id: 'read', role: 'viewer' }];
const members = [
  { user_id: 'lead', project_role: 'lead', volumes: ['technical', 'business'], company_role: 'manager' },
  { user_id: 'tech', project_role: 'writer', volumes: ['technical'], company_role: 'editor' },
  { user_id: 'biz', project_role: 'writer', volumes: ['business'], company_role: 'editor' },
  { user_id: 'read', project_role: 'readonly', volumes: ['technical', 'business'], company_role: 'viewer' },
];
const values = { members, technical_owner_id: 'tech', business_owner_id: 'biz', assembly_owner_id: 'biz', reason: '  两册负责人核对交接，个人草稿由原账号保留。  ' };

test('project and chapter controls use explicit backend permissions and never fall back to company role', () => {
  assert.equal(projectCan({ user: { role: 'manager' } }, 'manage_team'), false);
  assert.equal(projectCan({ permissions: { manage_team: 'true' } }, 'manage_team'), false);
  assert.equal(projectCan({ permissions: { manage_team: true } }, 'manage_team'), true);
  assert.equal(chapterCan({ assignee_id: 'lead' }, 'edit'), false);
  assert.equal(chapterCan({ permissions: { edit: true } }, 'edit'), true);
  assert.equal(chapterCan(null, 'edit'), false);
});

test('owners and chapter assignees must have writable company and project roles and participate in that volume', () => {
  assert.deepEqual(eligibleOwners(members, accounts, 'technical').map(member => member.user_id), ['lead', 'tech']);
  assert.deepEqual(eligibleOwners(members, accounts, 'business').map(member => member.user_id), ['lead', 'biz']);
  assert.deepEqual(assignmentCandidates(members, 'technical').map(member => member.user_id), ['lead', 'tech']);
  assert.deepEqual(assignmentCandidates([...members, { user_id: 'hidden', company_role: 'viewer', project_role: 'writer', volumes: ['technical'] }], 'technical').map(member => member.user_id), ['lead', 'tech']);
});

test('team payload preserves explicit owners and requires safe roles, unique members, a lead and handoff explanation', () => {
  const payload = teamPayload(values, accounts);
  assert.deepEqual(payload.volumes, [{ volume: 'technical', owner_id: 'tech' }, { volume: 'business', owner_id: 'biz' }]);
  assert.equal(payload.assembly_owner_id, 'biz');
  assert.equal(payload.reason, values.reason.trim());
  assert.throws(() => teamPayload({ ...values, technical_owner_id: 'biz' }, accounts), /参与本册/);
  assert.throws(() => teamPayload({ ...values, technical_owner_id: 'read' }, accounts), /参与本册/);
  assert.throws(() => teamPayload({ ...values, assembly_owner_id: 'read' }, accounts), /可以编写/);
  assert.throws(() => teamPayload({ ...values, reason: '   ' }, accounts), /交接安排/);
  assert.throws(() => teamPayload({ ...values, members: members.slice(1) }, accounts), /至少保留/);
  assert.throws(() => teamPayload({ ...values, members: [...members, members[1]] }, accounts), /一次/);
  assert.throws(() => teamPayload({ ...values, members: [...members, { user_id: 'unknown', project_role: 'writer', volumes: ['technical'] }] }, accounts), /同公司/);
  assert.throws(() => teamPayload({ ...values, members: members.map(member => member.user_id === 'read' ? { ...member, project_role: 'writer' } : member) }, accounts), /只读/);
  assert.throws(() => teamPayload({ ...values, members: members.map(member => member.user_id === 'tech' ? { ...member, project_role: 'lead' } : member) }, accounts), /公司经理/);
  assert.throws(() => teamPayload({ ...values, members: members.map(member => member.user_id === 'tech' ? { ...member, volumes: [] } : member) }, accounts), /参与本册/);
});

test('optional participation can remain empty without granting volume owner or assignee rights', () => {
  const emptyRead = members.map(member => member.user_id === 'read' ? { ...member, volumes: [] } : member);
  assert.deepEqual(teamPayload({ ...values, members: emptyRead }, accounts).members.find(member => member.user_id === 'read').volumes, []);
  const emptyWriter = members.map(member => member.user_id === 'tech' ? { ...member, volumes: [] } : member);
  assert.deepEqual(teamPayload({ ...values, technical_owner_id: 'lead', members: emptyWriter }, accounts).members.find(member => member.user_id === 'tech').volumes, []);
  assert.equal(eligibleOwners(emptyWriter, accounts, 'technical').some(member => member.user_id === 'tech'), false);
  assert.equal(assignmentCandidates(emptyWriter, 'technical').some(member => member.user_id === 'tech'), false);
});

test('team form reload copies membership arrays and does not change authoritative team input', () => {
  const team = { members, volumes: [{ volume: 'technical', owner_id: 'tech' }], assembly_owner_id: 'biz' };
  const form = teamFormValues(team); form.members[1].volumes.push('business');
  assert.deepEqual(team.members[1].volumes, ['technical']);
  assert.equal(form.business_owner_id, null);
  assert.equal(form.reason, '');
  assert.deepEqual(teamFormValues().members, []);
});

test('a refreshed project revision does not make an old team form safe to overwrite new assignments', () => {
  const original = { members, volumes: [{ volume: 'technical', owner_id: 'tech' }], assembly_owner_id: 'biz' };
  const loaded = teamBasis(original);
  assert.equal(teamBasis({ ...original, revision: 99, handoffs: [{ reason: '记录更新' }], members: [...members].reverse() }), loaded);
  assert.notEqual(teamBasis({ ...original, volumes: [{ volume: 'technical', owner_id: 'lead' }] }), loaded);
  assert.notEqual(teamBasis({ ...original, members: members.map(member => member.user_id === 'biz' ? { ...member, project_role: 'readonly' } : member) }), loaded);
  assert.notEqual(teamBasis({ ...original, assembly_owner_id: 'lead' }), loaded);
});

test('bulk scopes and check/export scope controls enforce project lead, volume owner and download-only boundaries', () => {
  const workspace = { team: { volumes: [{ volume: 'technical', owner_id: 'tech' }, { volume: 'business', owner_id: 'biz' }] }, chapters: [{ volume: 'technical', permissions: { manage_structure: true } }, { volume: 'business', permissions: { manage_structure: false } }], permissions: { manage_structure: false, check_all: false, export_internal: false, check_volumes: ['technical'], export_volumes: ['technical'] } };
  assert.deepEqual(planScopes(workspace, 'tech'), ['technical']);
  assert.deepEqual(planScopes(workspace, 'biz'), []);
  assert.deepEqual(planScopes({ ...workspace, permissions: { manage_structure: true } }, 'lead'), ['all', 'technical', 'business']);
  assert.equal(volumeOperationAllowed(workspace, 'check', 'technical'), true);
  assert.equal(volumeOperationAllowed(workspace, 'check', 'business'), false);
  assert.equal(volumeOperationAllowed(workspace, 'check', 'all'), false);
  assert.equal(volumeOperationAllowed(workspace, 'export', 'technical'), true);
  assert.equal(volumeOperationAllowed(workspace, 'export', 'all'), false);
  assert.equal(volumeOperationAllowed({ permissions: { export_internal: false, export_volumes: [] } }, 'export', 'all'), false);
});

test('losing access freezes writes while preserving cached official text, personal draft and source basis', () => {
  const workspace = { project: { id: 'p' }, input_fingerprint: 'original-source', permissions: { manage_team: true }, chapters: [{ id: 'c', content: '已提交正文', draft: { content: '尚未提交的个人草稿', input_fingerprint: 'old-source' }, permissions: { edit: true } }], requirements: [{ id: 'r', text: '原要求', response: '原响应', permissions: { response: true } }] };
  const frozen = freezeWorkspace(workspace);
  assert.equal(projectCan(frozen, 'manage_team'), false);
  assert.equal(chapterCan(frozen.chapters[0], 'edit'), false);
  assert.equal(frozen.requirements[0].permissions.response, false);
  assert.equal(frozen.chapters[0].content, '已提交正文');
  assert.equal(frozen.chapters[0].draft.content, '尚未提交的个人草稿');
  assert.equal(frozen.chapters[0].draft.input_fingerprint, 'old-source');
  assert.equal(workspace.chapters[0].permissions.edit, true);
  assert.equal(projectAccessLost({ status: 403 }), true);
  assert.equal(projectAccessLost({ status: 404 }), true);
  assert.equal(projectAccessLost({ status: 409 }), false);
  assert.equal(projectAccessLost(new Error('网络失败')), false);
});
