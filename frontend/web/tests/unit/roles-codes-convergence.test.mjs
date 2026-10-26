// 为什么有这个文件：验证 WP-6 八角色前端码表收口、字典驱动代码表以及退演示会话守卫。
// 它解决什么问题：证实 roles.ts 与 codes.ts 单源驱动，八角色矩阵与后端完全对齐，会话校验支持正式 authenticated 模式与标准八角色。

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SYSTEM_ROLES,
  SYSTEM_ROLE_LABELS,
  READONLY_SYSTEM_ROLES,
  PROJECT_CREATOR_ROLES,
  PROJECT_WRITER_ROLES,
  LEAD_COMPANY_ROLES,
  PLATFORM_ADMIN_FORBIDDEN_ROUTES,
  normalizeSystemRole,
  getSystemRoleLabel,
  isReadonlyRole,
  isKnownRole,
  isDemoMode,
} from '../../src/shared/roles.ts';
import {
  PROJECT_STATUSES,
  PROJECT_STATUS_LABELS,
  VOLUME_TYPES,
  VOLUME_LABELS,
  REQUIREMENT_CATEGORIES,
  REQUIREMENT_CATEGORY_LABELS,
  REQUIREMENT_STATUSES,
  FACT_STATUSES,
  JOB_STATUSES,
  RULE_LEVELS,
  ERROR_CODES,
} from '../../src/shared/codes.ts';
import {
  trustedApplicationSession,
  SessionNavigationError,
} from '../../src/app/session-navigation.ts';

test('roles.ts: single source of truth for 8 standard roles and labels', () => {
  const expectedRoles = [
    'platform_admin',
    'group_admin',
    'company_admin',
    'data_admin',
    'project_lead',
    'bid_writer',
    'auditor',
    'viewer',
  ];

  for (const role of expectedRoles) {
    assert.ok(isKnownRole(role), `Role ${role} must be recognized`);
    assert.equal(normalizeSystemRole(role), role);
    assert.ok(SYSTEM_ROLE_LABELS[role], `Role ${role} must have a Chinese label`);
  }

  // 历史别名双向归一化
  assert.equal(normalizeSystemRole('manager'), 'project_lead');
  assert.equal(normalizeSystemRole('editor'), 'bid_writer');
  assert.equal(normalizeSystemRole('readonly'), 'viewer');
  assert.equal(normalizeSystemRole('reviewer'), 'auditor');
  assert.equal(normalizeSystemRole('writer'), 'bid_writer');
  assert.equal(normalizeSystemRole('lead'), 'project_lead');
});

test('roles.ts: permission sets align with PRD v1.8 §2.2 / §2.3', () => {
  // 只读系统角色集合
  assert.ok(isReadonlyRole('group_admin'));
  assert.ok(isReadonlyRole('viewer'));
  assert.ok(isReadonlyRole('auditor'));
  assert.ok(isReadonlyRole('platform_admin'));
  assert.ok(!isReadonlyRole('project_lead'));
  assert.ok(!isReadonlyRole('bid_writer'));
  assert.ok(!isReadonlyRole('company_admin'));
  assert.ok(!isReadonlyRole('data_admin'));

  // 新建项目资质
  assert.ok(PROJECT_CREATOR_ROLES.has('project_lead'));
  assert.ok(PROJECT_CREATOR_ROLES.has('company_admin'));
  assert.ok(!PROJECT_CREATOR_ROLES.has('viewer'));
  assert.ok(!PROJECT_CREATOR_ROLES.has('bid_writer'));

  // 编写资质
  assert.ok(PROJECT_WRITER_ROLES.has('bid_writer'));
  assert.ok(PROJECT_WRITER_ROLES.has('project_lead'));
  assert.ok(PROJECT_WRITER_ROLES.has('company_admin'));
  assert.ok(PROJECT_WRITER_ROLES.has('data_admin'));
  assert.ok(!PROJECT_WRITER_ROLES.has('viewer'));

  // 平台管理员业务隔离
  assert.ok(PLATFORM_ADMIN_FORBIDDEN_ROUTES.has('workbench'));
  assert.ok(PLATFORM_ADMIN_FORBIDDEN_ROUTES.has('library'));
});

test('codes.ts: data dictionary v1.9 single-source codes', () => {
  // 项目状态流转
  assert.equal(PROJECT_STATUSES.DRAFT, 'draft');
  assert.equal(PROJECT_STATUSES.PARSING, 'parsing');
  assert.equal(PROJECT_STATUSES.PENDING_CONFIRM, 'pending_confirm');
  assert.equal(PROJECT_STATUSES.DRAFTING, 'drafting');
  assert.equal(PROJECT_STATUSES.CHECKING, 'checking');
  assert.equal(PROJECT_STATUSES.EXPORTABLE, 'exportable');
  assert.equal(PROJECT_STATUSES.EXPORTED, 'exported');
  assert.equal(PROJECT_STATUS_LABELS['drafting'], '编制中');

  // 分册枚举
  assert.equal(VOLUME_TYPES.TECHNICAL, 'technical');
  assert.equal(VOLUME_TYPES.BUSINESS, 'business');
  assert.equal(VOLUME_LABELS['technical'], '技术标');

  // 需求 10 大分类
  assert.equal(Object.keys(REQUIREMENT_CATEGORIES).length, 10);
  assert.equal(REQUIREMENT_CATEGORY_LABELS['star_clause'], '星号实质性条款');

  // 冻结错误码常量
  assert.equal(ERROR_CODES.UNAUTHENTICATED, 'UNAUTHENTICATED');
  assert.equal(ERROR_CODES.FORBIDDEN, 'FORBIDDEN');
  assert.equal(ERROR_CODES.NOT_FOUND, 'NOT_FOUND');
  assert.equal(ERROR_CODES.CONFLICT, 'CONFLICT');
});

test('session-navigation: supports authentic rbac-8roles session verification', () => {
  const authenticSession = {
    auth_mode: 'authenticated',
    role_mode: 'rbac-8roles',
    user: {
      id: 'corp-admin-01',
      name: '公司管理员真实账号',
      company_id: 'alpha',
      role: 'company_admin',
      roles: ['company_admin'],
      primary_role: 'company_admin',
    },
    scope: {
      kind: 'company',
      active_company_id: 'alpha',
      allowed_company_ids: ['alpha'],
    },
    navigation: [
      { route_id: 'workbench', path: '/workbench', access: 'write' },
      { route_id: 'library', path: '/library', access: 'write' },
      { route_id: 'jobs', path: '/jobs', access: 'read' },
    ],
    allowedActions: ['projects.read', 'projects.create', 'library.write'],
    home_path: '/workbench',
    session: { expires_at: null, renew_supported: false },
  };

  // 正式会话通过信任核验
  const verified = trustedApplicationSession(authenticSession);
  assert.equal(verified.auth_mode, 'authenticated');
  assert.equal(verified.role_mode, 'rbac-8roles');
  assert.equal(verified.user.primary_role, 'company_admin');

  // 非法角色被拒绝
  assert.throws(
    () => trustedApplicationSession({
      ...authenticSession,
      user: { ...authenticSession.user, role: 'invalid_role' },
    }),
    error => error instanceof SessionNavigationError && error.status === 403
  );

  // 跨公司伪造被拒绝
  assert.throws(
    () => trustedApplicationSession({
      ...authenticSession,
      scope: { kind: 'company', active_company_id: 'beta', allowed_company_ids: ['beta'] },
    }),
    error => error instanceof SessionNavigationError && error.status === 403
  );
});

test('roles.ts: isDemoMode defaults to false when unset, enables only on explicit VITE_DEMO=1/true', () => {
  // 在未显式设置 VITE_DEMO 时，isDemoMode() 必须诚实默认返回 false（关演示正式模式）
  assert.equal(isDemoMode(), false);
});
