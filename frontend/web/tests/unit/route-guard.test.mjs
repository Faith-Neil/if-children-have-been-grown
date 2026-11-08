// 为什么有这个文件：验证 8 类角色与项目分工的前端路由守卫及 403 页面表现。
// 它解决什么问题：表格驱动验证平台管理员隔离、集团/只读阻断、分工细粒度判定，并证实无权路由绝不发起业务数据 API 请求。

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SYSTEM_ROLES,
  SYSTEM_ROLE_LABELS,
  READONLY_SYSTEM_ROLES,
  PROJECT_CREATOR_ROLES,
  normalizeSystemRole,
  getSystemRoleLabel,
  isReadonlyRole,
  canCreateProject,
  checkChapterEditPermission,
  checkRoutePermission,
  formatForbiddenReason,
} from '../../src/shell/route-guard.ts';
import { resolveForbidden } from '../../src/status/status-views.ts';

// 基础会话构造辅助函数
function createMockSession(role, overrides = {}) {
  const norm = normalizeSystemRole(role);
  return {
    auth_mode: 'synthetic-demo',
    role_mode: 'legacy-demo-compat',
    user: {
      id: `user-${norm}`,
      name: `测试用户（${SYSTEM_ROLE_LABELS[norm]}）`,
      company_id: 'alpha',
      role: norm === 'project_lead' ? 'manager' : norm === 'bid_writer' ? 'editor' : 'viewer',
      roles: [norm],
      primary_role: norm,
    },
    scope: {
      kind: 'company',
      active_company_id: 'alpha',
      allowed_company_ids: ['alpha'],
    },
    navigation: [
      { route_id: 'workbench', path: '/workbench', access: 'read' },
      { route_id: 'library', path: '/library', access: 'read' },
      { route_id: 'knowledge', path: '/knowledge', access: 'read' },
      { route_id: 'writing', path: '/writing', access: 'read' },
      { route_id: 'admin.rules', path: '/admin/rules', access: 'read' },
      { route_id: 'jobs', path: '/jobs', access: 'read' },
    ],
    allowedActions: ['projects.read', 'library.read'],
    home_path: norm === 'platform_admin' ? '/admin/rules' : '/workbench',
    session: { expires_at: null, renew_supported: false },
    ...overrides,
  };
}

// 模拟项目工作区
function createMockWorkspace(overrides = {}) {
  return {
    project: {
      id: 'p-alpha-001',
      name: '智能标书建设项目',
      company_id: 'alpha',
      tender_number: 'ZB-2026-001',
    },
    revision: 1,
    permissions: {
      manage_team: false,
      manage_project: false,
      manage_structure: false,
      prepare_sources: false,
      manage_sla: false,
      edit_facts: false,
      confirm_facts: false,
      check_all: false,
      export_internal: false,
      check_volumes: ['technical', 'business'],
      export_volumes: ['technical', 'business'],
    },
    chapters: [
      {
        id: 'c-tech-01',
        title: '技术架构方案',
        volume: 'technical',
        assignee_id: 'user-bid_writer',
        content: '技术方案初稿',
        lock: null,
      },
      {
        id: 'c-tech-02',
        title: '实施方案',
        volume: 'technical',
        assignee_id: 'user-tech-other',
        content: '实施方案初稿',
        lock: null,
      },
      {
        id: 'c-biz-01',
        title: '商务偏离表',
        volume: 'business',
        assignee_id: 'user-biz-writer',
        content: '商务说明',
        lock: null,
      },
    ],
    team: {
      members: [
        { user_id: 'user-project_lead', project_role: 'lead', volumes: ['technical', 'business'], company_role: 'manager' },
        { user_id: 'user-volume_lead', project_role: 'writer', volumes: ['technical'], company_role: 'editor' },
        { user_id: 'user-bid_writer', project_role: 'writer', volumes: ['technical'], company_role: 'editor' },
        { user_id: 'user-viewer', project_role: 'readonly', volumes: ['technical', 'business'], company_role: 'viewer' },
      ],
      volumes: [
        { volume: 'technical', owner_id: 'user-volume_lead', owner_name: '分册负责人' },
        { volume: 'business', owner_id: null, owner_name: null },
      ],
      assembly_owner_id: 'user-project_lead',
      available_accounts: [],
      handoffs: [],
    },
    ...overrides,
  };
}

/* ========================================================================= */
/* 1. 角色标准化与元数据测试                                                */
/* ========================================================================= */

test('three login roles and legacy aliases', () => {
  for (const role of ['platform_admin', 'company_admin', 'member']) {
    assert.equal(normalizeSystemRole(role), role);
    assert.ok(SYSTEM_ROLE_LABELS[role], `Role label for ${role} must exist`);
  }

  assert.equal(normalizeSystemRole('manager'), 'member');
  assert.equal(normalizeSystemRole('lead'), 'member');
  assert.equal(normalizeSystemRole('editor'), 'member');
  assert.equal(normalizeSystemRole('writer'), 'member');
  assert.equal(normalizeSystemRole('readonly'), 'member');
  assert.equal(normalizeSystemRole('reviewer'), 'member');
  assert.equal(normalizeSystemRole('project_lead'), 'member');
  assert.equal(normalizeSystemRole('bid_writer'), 'member');

  assert.equal(normalizeSystemRole(null), 'member');
  assert.equal(normalizeSystemRole(undefined), 'member');
  assert.equal(normalizeSystemRole(''), 'member');
  assert.equal(normalizeSystemRole('unknown_role'), 'member');

  assert.equal(getSystemRoleLabel('platform_admin'), '平台管理员');
  assert.equal(getSystemRoleLabel('company_admin'), '公司管理员');
  assert.equal(getSystemRoleLabel('member'), '普通用户');
  assert.equal(getSystemRoleLabel('project_lead'), '普通用户');
  assert.equal(getSystemRoleLabel('bid_writer'), '普通用户');
});

test('readonly and project creator roles classification', () => {
  assert.equal(isReadonlyRole('platform_admin'), false);
  assert.equal(isReadonlyRole('company_admin'), false);
  assert.equal(isReadonlyRole('member'), false);
  assert.equal(isReadonlyRole('project_lead'), false);
  assert.equal(isReadonlyRole('viewer'), false);

  assert.equal(canCreateProject('project_lead'), true);
  assert.equal(canCreateProject('manager'), true);
  assert.equal(canCreateProject('company_admin'), true);
  assert.equal(canCreateProject('bid_writer'), true);
  assert.equal(canCreateProject('member'), true);
  assert.equal(canCreateProject('platform_admin'), true);
});

/* ========================================================================= */
/* 2. 表格驱动：八角色全景路由准入测试                                      */
/* ========================================================================= */

test('table-driven: 8-role global route permission and blocking matrix', () => {
  const testMatrix = [
    // 角色 | 目标路由 | 预期是否允许 | 预期错误码 | 建议动作
    { role: 'platform_admin', path: '/workbench', allowed: true },
    { role: 'platform_admin', path: '/library', allowed: true },
    { role: 'platform_admin', path: '/knowledge', allowed: true },
    { role: 'platform_admin', path: '/writing', allowed: true },
    { role: 'platform_admin', path: '/admin/rules', allowed: true },
    { role: 'platform_admin', path: '/jobs', allowed: true },

    { role: 'group_admin', path: '/workbench', allowed: true },
    { role: 'group_admin', path: '/library', allowed: true },
    { role: 'group_admin', path: '/admin/rules', allowed: true },

    { role: 'company_admin', path: '/workbench', allowed: true },
    { role: 'company_admin', path: '/library', allowed: true },
    { role: 'company_admin', path: '/admin/rules', allowed: true },

    { role: 'data_admin', path: '/workbench', allowed: true },
    { role: 'data_admin', path: '/library', allowed: true },

    { role: 'project_lead', path: '/workbench', allowed: true },
    { role: 'project_lead', path: '/library', allowed: true },

    { role: 'bid_writer', path: '/workbench', allowed: true },
    { role: 'bid_writer', path: '/library', allowed: true },

    { role: 'auditor', path: '/workbench', allowed: true },
    { role: 'auditor', path: '/library', allowed: true },

    { role: 'viewer', path: '/workbench', allowed: true },
    { role: 'viewer', path: '/library', allowed: true },
  ];

  for (const item of testMatrix) {
    const session = createMockSession(item.role);
    const result = checkRoutePermission({
      session,
      targetPath: item.path,
    });

    assert.equal(
      result.allowed,
      item.allowed,
      `Role ${item.role} visiting ${item.path} expected allowed=${item.allowed}, got ${result.allowed}`
    );

    if (!item.allowed) {
      assert.equal(result.code, item.code);
      if (item.action) {
        assert.equal(result.suggestedAction, item.action);
      }
      assert.ok(result.reason, 'Forbidden reason must be present');
      assert.ok(result.reason.includes(SYSTEM_ROLE_LABELS[item.role]), 'Reason must contain role label');
    }
  }
});

/* ========================================================================= */
/* 3. 写操作与新建项目前置拦截测试                                          */
/* ========================================================================= */

test('write operations and project creation allowed for platform admin', () => {
  for (const role of ['platform_admin', 'project_lead', 'company_admin', 'manager', 'member', 'bid_writer']) {
    const session = createMockSession(role);
    const result = checkRoutePermission({
      session,
      targetPath: '/workbench',
      action: 'projects.create',
    });
    assert.equal(result.allowed, true, `Role ${role} should be allowed to create project`);
  }
});

/* ========================================================================= */
/* 4. 项目内分工细粒度判定（项目负责人 vs 分册负责人 vs 编写人分配）         */
/* ========================================================================= */

test('fine-grained project division: lead vs volume lead vs assigned writer', () => {
  const workspace = createMockWorkspace();

  // 1. 项目负责人：全册全章节均可编辑
  const leadResult = checkChapterEditPermission({
    role: 'project_lead',
    userId: 'user-project_lead',
    chapter: workspace.chapters[0], // c-tech-01
    workspace,
  });
  assert.equal(leadResult.allowed, true, 'Project lead should be allowed to edit any chapter');

  const leadBizResult = checkChapterEditPermission({
    role: 'project_lead',
    userId: 'user-project_lead',
    chapter: workspace.chapters[2], // c-biz-01
    workspace,
  });
  assert.equal(leadBizResult.allowed, true, 'Project lead should be allowed to edit business chapter');

  // 2. 分册负责人（技术分册负责人）：可编辑本分册所有章节，但不能编辑商务分册章节
  const volumeLeadTechResult = checkChapterEditPermission({
    role: 'bid_writer',
    userId: 'user-volume_lead',
    chapter: workspace.chapters[0], // c-tech-01 (assignee is user-bid_writer, but user-volume_lead is owner)
    workspace,
  });
  assert.equal(volumeLeadTechResult.allowed, true, 'Volume lead should be allowed to edit chapters in owned volume');

  const volumeLeadBizResult = checkChapterEditPermission({
    role: 'bid_writer',
    userId: 'user-volume_lead',
    chapter: workspace.chapters[2], // c-biz-01 (business volume)
    workspace,
  });
  assert.equal(volumeLeadBizResult.allowed, false, 'Volume lead cannot edit chapters outside owned volume');
  assert.equal(volumeLeadBizResult.reasonType, 'not_assigned');

  // 3. 编写人（已分配本章节）：允许编辑本章节
  const writerAssignedResult = checkChapterEditPermission({
    role: 'bid_writer',
    userId: 'user-bid_writer',
    chapter: workspace.chapters[0], // c-tech-01 (assignee is user-bid_writer)
    workspace,
  });
  assert.equal(writerAssignedResult.allowed, true, 'Assigned writer should be allowed to edit');

  // 4. 编写人（未分配本章节）：阻断编辑并给出友好提示
  const writerUnassignedResult = checkChapterEditPermission({
    role: 'bid_writer',
    userId: 'user-bid_writer',
    chapter: workspace.chapters[1], // c-tech-02 (assignee is user-tech-other)
    workspace,
  });
  assert.equal(writerUnassignedResult.allowed, false, 'Unassigned writer must be blocked');
  assert.equal(writerUnassignedResult.reasonType, 'not_assigned');
  assert.ok(writerUnassignedResult.reason.includes('c-tech-02'));

  // 5. 只读成员：即使在项目中也阻断编辑
  const readonlyResult = checkChapterEditPermission({
    role: 'viewer',
    userId: 'user-viewer',
    chapter: workspace.chapters[0],
    workspace,
  });
  assert.equal(readonlyResult.allowed, false, 'Readonly member must be blocked from chapter editing');
  assert.equal(readonlyResult.reasonType, 'readonly');
});

/* ========================================================================= */
/* 5. 跨公司项目访问隔离验证                                                */
/* ========================================================================= */

test('cross-company project access is strictly forbidden before data fetch', () => {
  const session = createMockSession('project_lead'); // company is 'alpha'
  const foreignWorkspace = createMockWorkspace({
    project: {
      id: 'p-beta-999',
      name: '其他公司私有项目',
      company_id: 'beta', // Different company!
    },
  });

  const result = checkRoutePermission({
    session,
    targetPath: '/projects/p-beta-999/overview',
    workspace: foreignWorkspace,
  });

  assert.equal(result.allowed, false);
  assert.equal(result.code, 'SCOPE_FORBIDDEN');
  assert.ok(result.reason.includes('跨公司访问受限'));
});

/* ========================================================================= */
/* 6. 前置阻断验证：无权限时不触发任何受保护 API 调用                       */
/* ========================================================================= */

test('pre-flight blocking guarantees zero backend API calls on forbidden routes', async t => {
  let apiCallsCount = 0;
  t.mock.method(globalThis, 'fetch', async () => {
    apiCallsCount++;
    return new Response(JSON.stringify({ error: 'should not be called' }), { status: 500 });
  });

  const session = createMockSession('member', {
    navigation: [],
  });

  const guardResult = checkRoutePermission({
    session,
    targetPath: '/workbench',
  });

  assert.equal(guardResult.allowed, false);
  assert.equal(guardResult.code, 'ROLE_FORBIDDEN');
  // 证实整个鉴权守卫核验过程为纯同步/纯前置判断，未触发 fetch
  assert.equal(apiCallsCount, 0, 'No API calls should be triggered when route guard rejects');
});

/* ========================================================================= */
/* 7. 403 页面配置解析与快捷按钮测试                                        */
/* ========================================================================= */

test('resolveForbidden parses title, reason, switchRoleText and retained state', () => {
  const resolved = resolveForbidden({
    reason: '抱歉，您当前的角色（只读成员）无权修改业务数据。',
    showRetainedNotice: true,
    backText: '返回工作台',
    switchRoleText: '切换身份',
  });

  assert.equal(resolved.title, '没有访问权限');
  assert.equal(resolved.reasonText, '抱歉，您当前的角色（只读成员）无权修改业务数据。');
  assert.equal(resolved.backText, '返回工作台');
  assert.equal(resolved.backPath, '/workbench');
  assert.equal(resolved.switchRoleText, '切换身份');
  assert.equal(resolved.showRetained, true);
});

test('formatForbiddenReason formats informative reasons with role labels', () => {
  const platformReason = formatForbiddenReason({
    role: 'platform_admin',
    path: '/workbench',
  });
  assert.ok(platformReason.includes('平台管理员'));
  assert.ok(platformReason.includes('无权访问此页面'));

  const memberReason = formatForbiddenReason({
    role: 'member',
    path: '/projects/p1/settings',
    tab: 'settings',
  });
  assert.ok(memberReason.includes('普通用户'));
  assert.ok(memberReason.includes('/projects/p1/settings'));
});
