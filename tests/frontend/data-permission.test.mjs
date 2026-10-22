// 为什么有这个文件：验证多粒度数据权限判定（项目 / 分册 / 章节）与只读态切换逻辑。
// 它解决什么问题：落实 PRD v1.8 §2.3 与 §5.11.9，确保系统只读角色、项目只读成员、跨分册负责人及未指派编写人在对应层级严格进入只读态，并提供语义化解释。

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  getScopeLabel,
  getVolumeDisplayName,
  resolveDataPermission,
} from '../../frontend/web/src/data-permission.ts';

// 基础 Mock 团队分工数据
const mockTeam = {
  members: [
    { user_id: 'user-lead', name: '张主管', company_role: 'manager', project_role: 'lead', volumes: ['technical', 'business'] },
    { user_id: 'user-vol-tech', name: '李技术', company_role: 'editor', project_role: 'writer', volumes: ['technical'] },
    { user_id: 'user-vol-biz', name: '钱商务', company_role: 'editor', project_role: 'writer', volumes: ['business'] },
    { user_id: 'user-writer', name: '王编写', company_role: 'editor', project_role: 'writer', volumes: ['technical'] },
    { user_id: 'user-readonly', name: '赵只读', company_role: 'viewer', project_role: 'readonly', volumes: ['technical', 'business'] },
  ],
  volumes: [
    { volume: 'technical', owner_id: 'user-vol-tech', owner_name: '李技术' },
    { volume: 'business', owner_id: 'user-vol-biz', owner_name: '钱商务' },
  ],
  assembly_owner_id: null,
  available_accounts: [],
  handoffs: [],
};

const mockChapters = [
  { id: 'ch-tech-1', title: '技术方案综述', volume: 'technical', revision: 1, content: '技术正文 1', lock: null, assignee_id: 'user-writer' },
  { id: 'ch-tech-2', title: '系统性能指标', volume: 'technical', revision: 1, content: '技术正文 2', lock: null, assignee_id: 'user-vol-tech' },
  { id: 'ch-biz-1', title: '商务资质响应', volume: 'business', revision: 1, content: '商务正文 1', lock: null, assignee_id: 'user-vol-biz' },
  { id: 'ch-biz-2', title: '商务报价明细', volume: 'business', revision: 1, content: '商务正文 2', lock: null, assignee_id: null },
];

const mockWorkspace = {
  permissions: {
    manage_team: true,
    manage_project: true,
    manage_structure: true,
    prepare_sources: true,
    manage_sla: true,
    edit_facts: true,
    confirm_facts: true,
    check_all: true,
    export_internal: true,
    check_volumes: ['technical', 'business'],
    export_volumes: ['technical', 'business'],
  },
  team: mockTeam,
  chapters: mockChapters,
};

test('table-driven: 8 system roles in project-level data permission', () => {
  const roleCases = [
    { role: 'platform_admin', expectedReadOnly: true, expectedScope: 'project', reasonType: 'role_readonly' },
    { role: 'group_admin', expectedReadOnly: true, expectedScope: 'project', reasonType: 'role_readonly' },
    { role: 'auditor', expectedReadOnly: true, expectedScope: 'project', reasonType: 'role_readonly' },
    { role: 'viewer', expectedReadOnly: true, expectedScope: 'project', reasonType: 'role_readonly' },
    { role: 'company_admin', expectedReadOnly: false, expectedScope: 'none', reasonType: undefined },
    { role: 'project_lead', expectedReadOnly: false, expectedScope: 'none', reasonType: undefined },
  ];

  for (const { role, expectedReadOnly, expectedScope, reasonType } of roleCases) {
    const res = resolveDataPermission({
      role,
      userId: role === 'project_lead' ? 'user-lead' : 'user-any',
      workspace: mockWorkspace,
    });

    assert.equal(res.readOnly, expectedReadOnly, `Role ${role} readOnly expectation mismatch`);
    assert.equal(res.canEdit, !expectedReadOnly, `Role ${role} canEdit expectation mismatch`);
    assert.equal(res.scope, expectedScope, `Role ${role} scope expectation mismatch`);
    if (reasonType) {
      assert.equal(res.reasonType, reasonType, `Role ${role} reasonType mismatch`);
      assert.ok(res.readOnlyReason?.includes('只读状态'), `Role ${role} reason mismatch`);
    }
  }
});

test('project team member role restrictions: readonly member and non-member', () => {
  // 1. 项目内只读成员（project_role = 'readonly'）
  const readonlyMemberRes = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-readonly',
    workspace: mockWorkspace,
  });
  assert.equal(readonlyMemberRes.readOnly, true);
  assert.equal(readonlyMemberRes.canEdit, false);
  assert.equal(readonlyMemberRes.scope, 'project');
  assert.equal(readonlyMemberRes.reasonType, 'project_readonly');
  assert.ok(readonlyMemberRes.readOnlyReason?.includes('只读成员'));

  // 2. 非项目团队成员（not in workspace.team.members）
  const outsiderRes = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-outsider-999',
    workspace: mockWorkspace,
  });
  assert.equal(outsiderRes.readOnly, true);
  assert.equal(outsiderRes.canEdit, false);
  assert.equal(outsiderRes.scope, 'project');
  assert.equal(outsiderRes.reasonType, 'not_member');
  assert.ok(outsiderRes.readOnlyReason?.includes('不是当前项目团队成员'));

  // 3. 项目负责人（project_role = 'lead'）全项目放行
  const leadRes = resolveDataPermission({
    role: 'project_lead',
    userId: 'user-lead',
    workspace: mockWorkspace,
    volume: 'business',
    chapterId: 'ch-biz-2',
  });
  assert.equal(leadRes.readOnly, false);
  assert.equal(leadRes.canEdit, true);
  assert.equal(leadRes.scope, 'none');
});

test('table-driven: volume lead cross-volume division of labor', () => {
  // 1. 技术分册负责人访问技术分册 -> 放行
  const techLeadInTech = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-vol-tech',
    workspace: mockWorkspace,
    volume: 'technical',
  });
  assert.equal(techLeadInTech.readOnly, false);
  assert.equal(techLeadInTech.canEdit, true);
  assert.equal(techLeadInTech.scope, 'none');

  // 2. 技术分册负责人访问商务分册 -> volume 级只读拦截
  const techLeadInBiz = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-vol-tech',
    workspace: mockWorkspace,
    volume: 'business',
  });
  assert.equal(techLeadInBiz.readOnly, true);
  assert.equal(techLeadInBiz.canEdit, false);
  assert.equal(techLeadInBiz.scope, 'volume');
  assert.equal(techLeadInBiz.scopeName, '商务分册');
  assert.equal(techLeadInBiz.reasonType, 'wrong_volume');
  assert.ok(techLeadInBiz.readOnlyReason?.includes('您当前是【技术分册】负责人，在【商务分册】中处于只读浏览状态'));

  // 3. 商务分册负责人访问商务分册 -> 放行
  const bizLeadInBiz = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-vol-biz',
    workspace: mockWorkspace,
    volume: 'business',
  });
  assert.equal(bizLeadInBiz.readOnly, false);
  assert.equal(bizLeadInBiz.canEdit, true);

  // 4. 商务分册负责人访问技术分册 -> volume 级只读拦截
  const bizLeadInTech = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-vol-biz',
    workspace: mockWorkspace,
    volume: 'technical',
  });
  assert.equal(bizLeadInTech.readOnly, true);
  assert.equal(bizLeadInTech.canEdit, false);
  assert.equal(bizLeadInTech.scope, 'volume');
  assert.equal(bizLeadInTech.scopeName, '技术分册');
  assert.equal(bizLeadInTech.reasonType, 'wrong_volume');
  assert.ok(bizLeadInTech.readOnlyReason?.includes('您当前是【商务分册】负责人，在【技术分册】中处于只读浏览状态'));
});

test('table-driven: chapter-level assignment division of labor for bid writers', () => {
  // 1. 编写人访问已分配章节（ch-tech-1）-> 放行
  const assignedChapterRes = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-writer',
    workspace: mockWorkspace,
    volume: 'technical',
    chapterId: 'ch-tech-1',
  });
  assert.equal(assignedChapterRes.readOnly, false);
  assert.equal(assignedChapterRes.canEdit, true);
  assert.equal(assignedChapterRes.scope, 'none');

  // 2. 编写人访问同分册内未指派给自己的章节（ch-tech-2）-> chapter 级只读拦截
  const unassignedChapterRes = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-writer',
    workspace: mockWorkspace,
    volume: 'technical',
    chapterId: 'ch-tech-2',
  });
  assert.equal(unassignedChapterRes.readOnly, true);
  assert.equal(unassignedChapterRes.canEdit, false);
  assert.equal(unassignedChapterRes.scope, 'chapter');
  assert.equal(unassignedChapterRes.scopeName, '系统性能指标');
  assert.equal(unassignedChapterRes.reasonType, 'not_assigned');
  assert.ok(unassignedChapterRes.readOnlyReason?.includes('本章节【系统性能指标】未分配给您'));

  // 3. 编写人未分配商务分册，进入商务分册章节 -> volume 级只读拦截
  const wrongVolumeChapterRes = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-writer',
    workspace: mockWorkspace,
    chapterId: 'ch-biz-1',
  });
  assert.equal(wrongVolumeChapterRes.readOnly, true);
  assert.equal(wrongVolumeChapterRes.canEdit, false);
  assert.equal(wrongVolumeChapterRes.scope, 'volume');
  assert.equal(wrongVolumeChapterRes.scopeName, '商务分册');
  assert.equal(wrongVolumeChapterRes.reasonType, 'wrong_volume');
  assert.ok(wrongVolumeChapterRes.readOnlyReason?.includes('您未被分配参与【商务分册】'));
});

test('volume lead has full chapter edit rights within their own volume', () => {
  // 技术分册负责人访问属于技术分册但分配给其他编写人的章节（ch-tech-1）
  const volumeLeadChapterRes = resolveDataPermission({
    role: 'bid_writer',
    userId: 'user-vol-tech',
    workspace: mockWorkspace,
    chapterId: 'ch-tech-1',
  });
  assert.equal(volumeLeadChapterRes.readOnly, false);
  assert.equal(volumeLeadChapterRes.canEdit, true);
  assert.equal(volumeLeadChapterRes.scope, 'none');
});

test('helper functions contract: getVolumeDisplayName and getScopeLabel', () => {
  assert.equal(getVolumeDisplayName('technical'), '技术分册');
  assert.equal(getVolumeDisplayName('business'), '商务分册');
  assert.equal(getVolumeDisplayName('all'), '全部分册');
  assert.equal(getVolumeDisplayName(null), '全部分册');

  assert.equal(getScopeLabel('project'), '全项目');
  assert.equal(getScopeLabel('volume'), '分册');
  assert.equal(getScopeLabel('chapter'), '章节');
  assert.equal(getScopeLabel('none'), '无限制');
});
