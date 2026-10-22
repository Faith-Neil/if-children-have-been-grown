// 为什么有这个文件：验证 <Can> 权限指令的核心算法与八角色权限矩阵。
// 它解决什么问题：落实 PRD v1.8 §2.3，确保 8 类系统角色在项目创建、解析确认、章节编辑、分册定稿与递交导出等关键操作上的准入与阻断完全符合规范。

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { can, normalizeAction } from '../../frontend/web/src/can-directive.ts';

// 基础项目与分册分工 Mock
const mockTeam = {
  members: [
    { user_id: 'user-lead', name: '张主管', company_role: 'manager', project_role: 'lead', volumes: ['technical', 'business'] },
    { user_id: 'user-vol-tech', name: '李技术', company_role: 'editor', project_role: 'writer', volumes: ['technical'] },
    { user_id: 'user-writer', name: '王编写', company_role: 'editor', project_role: 'writer', volumes: ['technical'] },
    { user_id: 'user-readonly', name: '赵只读', company_role: 'viewer', project_role: 'readonly', volumes: ['technical', 'business'] },
  ],
  volumes: [
    { volume: 'technical', owner_id: 'user-vol-tech', owner_name: '李技术' },
    { volume: 'business', owner_id: null, owner_name: null },
  ],
  assembly_owner_id: null,
  available_accounts: [],
  handoffs: [],
};

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
  chapters: [
    { id: 'ch-tech-1', title: '技术方案综述', volume: 'technical', revision: 1, content: '正文', lock: null, assignee_id: 'user-writer' },
    { id: 'ch-tech-2', title: '技术架构图', volume: 'technical', revision: 1, content: '正文', lock: null, assignee_id: 'user-vol-tech' },
    { id: 'ch-biz-1', title: '商务资质响应', volume: 'business', revision: 1, content: '正文', lock: null, assignee_id: null },
  ],
  parse_confirmed: true,
};

test('normalizeAction handles colon formats, object parameters, and aliases', () => {
  // 1. 冒号格式
  assert.deepEqual(normalizeAction('project:create'), { action: 'project:create', resourceType: 'project', resourceData: undefined });
  assert.deepEqual(normalizeAction('chapter:edit'), { action: 'chapter:edit', resourceType: 'chapter', resourceData: undefined });
  assert.deepEqual(normalizeAction('submission:export'), { action: 'submission:export', resourceType: 'submission', resourceData: undefined });

  // 2. 分离式 perform + on 字符串
  assert.deepEqual(normalizeAction('create', 'project'), { action: 'project:create', resourceType: 'project', resourceData: undefined });
  assert.deepEqual(normalizeAction('confirm', 'parse'), { action: 'parse:confirm', resourceType: 'parse', resourceData: undefined });
  assert.deepEqual(normalizeAction('confirm', 'matrix'), { action: 'matrix:confirm', resourceType: 'matrix', resourceData: undefined });
  assert.deepEqual(normalizeAction('export', 'submission'), { action: 'submission:export', resourceType: 'submission', resourceData: undefined });
  assert.deepEqual(normalizeAction('finalize', 'volume'), { action: 'volume:finalize', resourceType: 'volume', resourceData: undefined });

  // 3. 实体对象参数
  const chapterObj = { id: 'ch-1', volume: 'technical', assignee_id: 'u-1' };
  const res = normalizeAction('edit', chapterObj);
  assert.equal(res.action, 'chapter:edit');
  assert.equal(res.resourceType, 'chapter');
  assert.deepEqual(res.resourceData, chapterObj);
});

test('table-driven: 8 roles x project:create permission', () => {
  const cases = [
    { role: 'project_lead', expected: true },
    { role: 'company_admin', expected: true },
    { role: 'manager', expected: true }, // 历史别名
    { role: 'lead', expected: true }, // 历史别名
    { role: 'bid_writer', expected: false },
    { role: 'editor', expected: false }, // 历史别名
    { role: 'data_admin', expected: false },
    { role: 'group_admin', expected: false },
    { role: 'platform_admin', expected: false },
    { role: 'auditor', expected: false },
    { role: 'reviewer', expected: false }, // 历史别名
    { role: 'viewer', expected: false },
    { role: 'readonly', expected: false }, // 历史别名
  ];

  for (const c of cases) {
    const result = can('project:create', null, { role: c.role });
    assert.equal(result.allowed, c.expected, `Role ${c.role} project:create must be ${c.expected}`);
    if (!c.expected) {
      assert.ok(result.reason?.includes('无权新建投标项目') || result.reason?.includes('只读状态') || result.code === 'PROJECT_CREATE_FORBIDDEN');
    }
  }
});

test('table-driven: 8 roles x project:confirm / parse:confirm / matrix:confirm', () => {
  // 仅项目负责人（及公司管理员）可确认，编写人与只读角色一律阻断
  const allowedRoles = ['project_lead', 'company_admin', 'manager', 'lead'];
  const disallowedRoles = ['bid_writer', 'editor', 'data_admin', 'group_admin', 'platform_admin', 'auditor', 'viewer', 'readonly'];

  for (const role of allowedRoles) {
    const res = can('project:confirm', null, { role, workspace: mockWorkspace, userId: 'user-lead' });
    assert.equal(res.allowed, true, `Role ${role} must be allowed to confirm`);
  }

  for (const role of disallowedRoles) {
    const res = can('project:confirm', null, { role, workspace: mockWorkspace, userId: 'user-writer' });
    assert.equal(res.allowed, false, `Role ${role} must NOT be allowed to confirm`);
    assert.ok(res.reason?.length > 0);
  }
});

test('table-driven: 8 roles x submission:export (递交版 Word 导出) strictly limited to project_lead', () => {
  // PRD v1.5 / v1.8 明确：递交版 Word 导出仅限项目负责人，分册负责人与编写人不可导出
  const cases = [
    { role: 'project_lead', userId: 'user-lead', expected: true },
    { role: 'company_admin', userId: 'user-lead', expected: true },
    // 分册负责人仅能导出内部稿，不能导出递交版
    { role: 'bid_writer', userId: 'user-vol-tech', expected: false },
    // 编写人不能导出递交版
    { role: 'bid_writer', userId: 'user-writer', expected: false },
    // 只读角色与管理员不能导出递交版
    { role: 'group_admin', userId: 'user-group', expected: false },
    { role: 'viewer', userId: 'user-readonly', expected: false },
    { role: 'platform_admin', userId: 'user-plat', expected: false },
    { role: 'data_admin', userId: 'user-data', expected: false },
    { role: 'auditor', userId: 'user-audit', expected: false },
  ];

  for (const c of cases) {
    const res = can('submission:export', null, { role: c.role, userId: c.userId, workspace: mockWorkspace });
    assert.equal(res.allowed, c.expected, `submission:export for role=${c.role}, userId=${c.userId} must be ${c.expected}`);
    if (!c.expected) {
      assert.ok(res.reason?.includes('递交版') || res.reason?.includes('只读状态') || res.code === 'SUBMISSION_EXPORT_FORBIDDEN');
    }
  }
});

test('table-driven: volume:export_internal (内部稿导出) scope', () => {
  // 1. 项目负责人：两册及全部均可导出
  assert.equal(can('volume:export_internal', 'technical', { role: 'project_lead', userId: 'user-lead', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('volume:export_internal', 'business', { role: 'project_lead', userId: 'user-lead', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('volume:export_internal', 'all', { role: 'project_lead', userId: 'user-lead', workspace: mockWorkspace }).allowed, true);

  // 2. 技术分册负责人：本分册可导出，商务分册与全册不可导出
  assert.equal(can('volume:export_internal', 'technical', { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('volume:export_internal', 'business', { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, false);
  assert.equal(can('volume:export_internal', 'all', { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, false);

  // 3. 普通编写人：无导出权限
  assert.equal(can('volume:export_internal', 'technical', { role: 'bid_writer', userId: 'user-writer', workspace: mockWorkspace }).allowed, false);

  // 4. 只读角色：无导出权限
  assert.equal(can('volume:export_internal', 'technical', { role: 'viewer', userId: 'user-readonly', workspace: mockWorkspace }).allowed, false);
  assert.equal(can('volume:export_internal', 'technical', { role: 'group_admin', userId: 'user-group', workspace: mockWorkspace }).allowed, false);
});

test('table-driven: chapter:edit and chapter:submit fine-grained division of labor', () => {
  const chTech1 = mockWorkspace.chapters[0]; // assignee: user-writer, volume: technical
  const chTech2 = mockWorkspace.chapters[1]; // assignee: user-vol-tech, volume: technical
  const chBiz1 = mockWorkspace.chapters[2];  // assignee: null, volume: business

  // 1. 项目负责人：全册全章节均可编辑
  assert.equal(can('chapter:edit', chTech1, { role: 'project_lead', userId: 'user-lead', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('chapter:edit', chBiz1, { role: 'project_lead', userId: 'user-lead', workspace: mockWorkspace }).allowed, true);

  // 2. 技术分册负责人：本分册内所有章节可编辑，商务分册不可编辑
  assert.equal(can('chapter:edit', chTech1, { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('chapter:edit', chTech2, { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('chapter:edit', chBiz1, { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, false);

  // 3. 编写人王编写：仅被分配的 chTech1 可编辑，未被分配的 chTech2 和 chBiz1 均不可编辑
  assert.equal(can('chapter:edit', chTech1, { role: 'bid_writer', userId: 'user-writer', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('chapter:edit', chTech2, { role: 'bid_writer', userId: 'user-writer', workspace: mockWorkspace }).allowed, false);
  assert.equal(can('chapter:edit', chBiz1, { role: 'bid_writer', userId: 'user-writer', workspace: mockWorkspace }).allowed, false);

  // 4. 只读角色：一律不可编辑
  assert.equal(can('chapter:edit', chTech1, { role: 'viewer', userId: 'user-readonly', workspace: mockWorkspace }).allowed, false);
  assert.equal(can('chapter:edit', chTech1, { role: 'group_admin', userId: 'user-group', workspace: mockWorkspace }).allowed, false);
  assert.equal(can('chapter:edit', chTech1, { role: 'auditor', userId: 'user-audit', workspace: mockWorkspace }).allowed, false);
});

test('chapter:takeover (接管编辑锁) permissions', () => {
  const chTech = mockWorkspace.chapters[0];
  const chBiz = mockWorkspace.chapters[2];

  // 项目负责人可以接管任意章节锁
  assert.equal(can('chapter:takeover', chTech, { role: 'project_lead', userId: 'user-lead', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('chapter:takeover', chBiz, { role: 'project_lead', userId: 'user-lead', workspace: mockWorkspace }).allowed, true);

  // 技术分册负责人仅可接管本分册内章节锁
  assert.equal(can('chapter:takeover', chTech, { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('chapter:takeover', chBiz, { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, false);

  // 普通编写人不能接管他人锁
  assert.equal(can('chapter:takeover', chTech, { role: 'bid_writer', userId: 'user-writer', workspace: mockWorkspace }).allowed, false);

  // 只读成员不能接管锁
  assert.equal(can('chapter:takeover', chTech, { role: 'viewer', userId: 'user-readonly', workspace: mockWorkspace }).allowed, false);
});

test('volume:finalize, volume:check, volume:unlock permissions', () => {
  // 项目负责人：全放行
  assert.equal(can('volume:finalize', 'technical', { role: 'project_lead', userId: 'user-lead', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('volume:unlock', 'business', { role: 'project_lead', userId: 'user-lead', workspace: mockWorkspace }).allowed, true);

  // 技术分册负责人：技术放行，商务阻断
  assert.equal(can('volume:finalize', 'technical', { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('volume:finalize', 'business', { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, false);
  assert.equal(can('volume:unlock', 'technical', { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, true);
  assert.equal(can('volume:unlock', 'business', { role: 'bid_writer', userId: 'user-vol-tech', workspace: mockWorkspace }).allowed, false);

  // 普通编写人：一律阻断
  assert.equal(can('volume:finalize', 'technical', { role: 'bid_writer', userId: 'user-writer', workspace: mockWorkspace }).allowed, false);
});

test('id_card:view (查看完整身份证号) strictly limited to company_admin and data_admin', () => {
  const allowed = ['company_admin', 'data_admin'];
  const disallowed = ['project_lead', 'bid_writer', 'group_admin', 'platform_admin', 'auditor', 'viewer'];

  for (const role of allowed) {
    const res = can('id_card:view', null, { role });
    assert.equal(res.allowed, true, `Role ${role} must be allowed to view id_card`);
  }

  for (const role of disallowed) {
    const res = can('id_card:view', null, { role });
    assert.equal(res.allowed, false, `Role ${role} must NOT be allowed to view id_card`);
    assert.equal(res.code, 'ID_CARD_VIEW_FORBIDDEN');
  }
});

test('universal readonly safety gate blocks all write operations', () => {
  const writeActions = [
    'project:create',
    'project:confirm',
    'chapter:edit',
    'chapter:submit',
    'chapter:takeover',
    'volume:finalize',
    'volume:unlock',
    'partner:upload',
  ];

  const readonlyRoles = ['viewer', 'readonly', 'group_admin', 'auditor', 'reviewer'];

  for (const role of readonlyRoles) {
    for (const action of writeActions) {
      const res = can(action, null, { role });
      assert.equal(res.allowed, false, `Role ${role} must be blocked from write action ${action}`);
      assert.equal(res.code, 'READONLY_FORBIDDEN');
    }
  }
});
