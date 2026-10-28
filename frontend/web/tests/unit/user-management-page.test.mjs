// 为什么有这个测试：严格验证 APP-M2-T027 (A-02 用户管理、新增与停用前转交安全表单) 的领域逻辑、密码策略只能调严、停用前资产强制交接门禁及 8 角色权限感知。
// 它解决什么问题：防止停用持有资产的负责人导致项目/章节孤立遗失，防止密码策略低于平台基线 8 位/3 类，防止跨企业越权交接与只读角色非法操作。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  checkUserManagementPermission,
  countPasswordCharClasses,
  countUserActiveAssets,
  DEFAULT_COMPANY_PASSWORD_POLICY,
  executeUserHandoverAndDisable,
  filterUsersList,
  formatAssetSummary,
  hasActiveAssets,
  INITIAL_USERS,
  PLATFORM_PASSWORD_BASELINE,
  validateCompanyPasswordPolicy,
  validateHandoverBeforeDisable,
  validateNewUserForm,
  validatePasswordStrength,
} from '../../src/admin/user-management-core.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '../../../..');

test('1. 用户初始数据集与业务资产统计完整性', () => {
  assert.ok(Array.isArray(INITIAL_USERS));
  assert.ok(INITIAL_USERS.length >= 8, '初始用户数应覆盖多租户多角色场景');

  // 张建国 (project_lead) 拥有 2 个项目与 1 个章节
  const zhang = INITIAL_USERS.find(u => u.username === 'lead_zhang');
  assert.ok(zhang);
  assert.equal(hasActiveAssets(zhang.assigned_assets), true);
  assert.equal(countUserActiveAssets(zhang.assigned_assets), 3);
  const zhangSummary = formatAssetSummary(zhang.assigned_assets);
  assert.match(zhangSummary, /2 个进行中项目/);
  assert.match(zhangSummary, /1 篇在编章节/);

  // 李明 (bid_writer) 拥有 2 个章节与 1 项资料
  const li = INITIAL_USERS.find(u => u.username === 'writer_li');
  assert.ok(li);
  assert.equal(hasActiveAssets(li.assigned_assets), true);
  assert.equal(countUserActiveAssets(li.assigned_assets), 3);

  // 王雪 (auditor) 与 赵小明 (viewer) 0 项资产
  const wang = INITIAL_USERS.find(u => u.username === 'auditor_wang');
  assert.ok(wang);
  assert.equal(hasActiveAssets(wang.assigned_assets), false);
  assert.equal(countUserActiveAssets(wang.assigned_assets), 0);
  assert.match(formatAssetSummary(wang.assigned_assets), /0 项资产（可直接停用）/);
});

test('2. “公司设置只能调严不能调宽”密码策略合规校验', () => {
  // 平台基线
  assert.equal(PLATFORM_PASSWORD_BASELINE.MIN_LENGTH, 8);
  assert.equal(PLATFORM_PASSWORD_BASELINE.MIN_CHAR_CLASSES, 3);
  assert.equal(PLATFORM_PASSWORD_BASELINE.MAX_LOGIN_ATTEMPTS, 5);

  // 正例：调严放行（12位、4类全含、最大失败3次）
  const tighterResult = validateCompanyPasswordPolicy({
    password_min_length: 12,
    password_min_char_classes: 4,
    max_login_attempts: 3,
  });
  assert.equal(tighterResult.valid, true);
  assert.equal(tighterResult.issues.length, 0);

  // 反例：调宽拦截（最少长度 6 位 < 平台底线 8 位）
  const looseLength = validateCompanyPasswordPolicy({
    password_min_length: 6,
  });
  assert.equal(looseLength.valid, false);
  assert.match(looseLength.issues[0], /低于平台基线（8 位），只能调严不能调宽/);

  // 反例：调宽拦截（字符种类 2 类 < 平台底线 3 类）
  const looseClasses = validateCompanyPasswordPolicy({
    password_min_char_classes: 2,
  });
  assert.equal(looseClasses.valid, false);
  assert.match(looseClasses.issues[0], /低于平台基线（3 类），只能调严不能调宽/);

  // 反例：调宽拦截（最大重试次数 8 次 > 平台上限 5 次）
  const looseAttempts = validateCompanyPasswordPolicy({
    max_login_attempts: 8,
  });
  assert.equal(looseAttempts.valid, false);
  assert.match(looseAttempts.issues[0], /高于平台基线（5 次），只能调严不能调宽/);
});

test('3. 密码强度与字符类别动态核验算法', () => {
  // 字符类别计数断言
  assert.equal(countPasswordCharClasses(''), 0);
  assert.equal(countPasswordCharClasses('abcdef'), 1); // 仅小写
  assert.equal(countPasswordCharClasses('abc123'), 2); // 小写 + 数字
  assert.equal(countPasswordCharClasses('Abc123'), 3); // 大写 + 小写 + 数字
  assert.equal(countPasswordCharClasses('Abc123!@#'), 4); // 大写 + 小写 + 数字 + 符号

  // 默认策略下验证
  const validRes = validatePasswordStrength('BidWriter2026!', DEFAULT_COMPANY_PASSWORD_POLICY);
  assert.equal(validRes.valid, true);
  assert.equal(validRes.charClassCount, 4);

  // 长度不足
  const shortRes = validatePasswordStrength('Ab1!', DEFAULT_COMPANY_PASSWORD_POLICY);
  assert.equal(shortRes.valid, false);
  assert.match(shortRes.message, /密码长度至少为 8 位/);

  // 类别不足 (仅小写+数字 2 类)
  const lowClassRes = validatePasswordStrength('bidwriter2026', DEFAULT_COMPANY_PASSWORD_POLICY);
  assert.equal(lowClassRes.valid, false);
  assert.match(lowClassRes.message, /至少包含大写字母、小写字母、数字、特殊符号中的 3 类/);
});

test('4. 新增用户表单校验与查重防线', () => {
  const users = [...INITIAL_USERS];

  // 账号查重拦截
  const dupResult = validateNewUserForm(
    {
      username: 'lead_zhang',
      name: '张三',
      role: 'bid_writer',
      company_id: 'alpha',
      password: 'StrongPassword123!',
      confirm_password: 'StrongPassword123!',
    },
    users
  );
  assert.equal(dupResult.valid, false);
  assert.equal(dupResult.field, 'username');
  assert.match(dupResult.message, /已存在，不可重复/);

  // 账号非法格式（含空格或中文）
  const invalidUserResult = validateNewUserForm(
    {
      username: 'user 123',
      name: '李四',
      role: 'bid_writer',
      company_id: 'alpha',
      password: 'StrongPassword123!',
      confirm_password: 'StrongPassword123!',
    },
    users
  );
  assert.equal(invalidUserResult.valid, false);
  assert.match(invalidUserResult.message, /仅限 3~32 位字母、数字或下划线/);

  // 两次密码不一致
  const mismatchResult = validateNewUserForm(
    {
      username: 'new_writer_01',
      name: '王五',
      role: 'bid_writer',
      company_id: 'alpha',
      password: 'StrongPassword123!',
      confirm_password: 'DifferentPassword123!',
    },
    users
  );
  assert.equal(mismatchResult.valid, false);
  assert.equal(mismatchResult.field, 'confirm_password');
  assert.match(mismatchResult.message, /两次输入的密码不一致/);

  // 合法通过
  const okResult = validateNewUserForm(
    {
      username: 'new_writer_01',
      name: '王五',
      role: 'bid_writer',
      company_id: 'alpha',
      password: 'StrongPassword123!',
      confirm_password: 'StrongPassword123!',
    },
    users
  );
  assert.equal(okResult.valid, true);
});

test('5. 停用前业务资产强制交接合规红线校验（M1-P10-F2）', () => {
  const zhang = INITIAL_USERS.find(u => u.username === 'lead_zhang');
  const li = INITIAL_USERS.find(u => u.username === 'writer_li');
  const disabledQian = INITIAL_USERS.find(u => u.username === 'writer_qian');
  const betaZhou = INITIAL_USERS.find(u => u.username === 'lead_beta_zhou');

  assert.ok(zhang && li && disabledQian && betaZhou);

  // 1. 尝试将资产交接给自己 -> 拦截
  const selfRes = validateHandoverBeforeDisable({
    sourceUser: zhang,
    targetUserId: zhang.id,
    reason: '准备离职交接工作',
    availableUsers: INITIAL_USERS,
  });
  assert.equal(selfRes.valid, false);
  assert.match(selfRes.message, /交接接收人不能是待停用用户本人/);

  // 2. 尝试跨企业交接（Alpha -> Beta） -> 严格拦截多租户数据泄露
  const crossCompanyRes = validateHandoverBeforeDisable({
    sourceUser: zhang,
    targetUserId: betaZhou.id,
    reason: '将水利工程项目交接',
    availableUsers: INITIAL_USERS,
  });
  assert.equal(crossCompanyRes.valid, false);
  assert.match(crossCompanyRes.message, /严禁跨企业租户进行业务资产转交/);

  // 3. 尝试交接给已停用用户 -> 拦截
  const disabledTargetRes = validateHandoverBeforeDisable({
    sourceUser: zhang,
    targetUserId: disabledQian.id,
    reason: '交接给前任员工',
    availableUsers: INITIAL_USERS,
  });
  assert.equal(disabledTargetRes.valid, false);
  assert.match(disabledTargetRes.message, /接收人当前状态不可用/);

  // 4. 交接理由过短 (< 5 字) -> 拦截
  const shortReasonRes = validateHandoverBeforeDisable({
    sourceUser: zhang,
    targetUserId: li.id,
    reason: '转交',
    availableUsers: INITIAL_USERS,
  });
  assert.equal(shortReasonRes.valid, false);
  assert.match(shortReasonRes.message, /交接理由不得少于 5 个字/);

  // 5. 合法同公司在职交接 -> 校验通过
  const passRes = validateHandoverBeforeDisable({
    sourceUser: zhang,
    targetUserId: li.id,
    reason: '张建国调休离职，将进行中智慧水利标段统筹权及章节移交李明负责',
    availableUsers: INITIAL_USERS,
  });
  assert.equal(passRes.valid, true);
});

test('6. 执行资产交接与状态停用领域逻辑断言', () => {
  const users = JSON.parse(JSON.stringify(INITIAL_USERS));
  const zhang = users.find(u => u.username === 'lead_zhang');
  const li = users.find(u => u.username === 'writer_li');

  const { updatedUsers, handoverRecord } = executeUserHandoverAndDisable({
    users,
    sourceUserId: zhang.id,
    targetUserId: li.id,
    reason: '岗位变动转交全部水利工程项目与章节资产',
    operatorId: 'admin_alpha',
  });

  // 交接记录审计断言
  assert.equal(handoverRecord.source_user_id, zhang.id);
  assert.equal(handoverRecord.target_user_id, li.id);
  assert.equal(handoverRecord.transferred_projects_count, 2);
  assert.equal(handoverRecord.transferred_chapters_count, 1);
  assert.equal(handoverRecord.company_id, 'alpha');

  // 源用户状态停用，资产清空
  const updatedZhang = updatedUsers.find(u => u.id === zhang.id);
  assert.equal(updatedZhang.status, 'disabled');
  assert.equal(hasActiveAssets(updatedZhang.assigned_assets), false);
  assert.equal(updatedZhang.assigned_assets.active_projects.length, 0);

  // 接收人资产合并增多
  const updatedLi = updatedUsers.find(u => u.id === li.id);
  assert.equal(updatedLi.status, 'active');
  assert.equal(updatedLi.assigned_assets.active_projects.length, 2); // 原有0 + 接收2
  assert.equal(updatedLi.assigned_assets.active_chapters.length, 3); // 原有2 + 接收1
  assert.equal(updatedLi.assigned_assets.kb_items.length, 1); // 原有1
});

test('7. 8 角色 RBAC 细粒度权限感知与多租户隔离过滤', () => {
  // 管理员享有管理权
  const platformAdminPerm = checkUserManagementPermission('platform_admin');
  assert.equal(platformAdminPerm.canOperate, true);
  assert.equal(platformAdminPerm.isReadOnly, false);

  const companyAdminPerm = checkUserManagementPermission('company_admin');
  assert.equal(companyAdminPerm.canOperate, true);
  assert.equal(companyAdminPerm.isReadOnly, false);

  // 业务角色全只读
  const roles = ['project_lead', 'bid_writer', 'auditor', 'viewer', 'data_admin', 'reviewer', 'readonly'];
  for (const role of roles) {
    const perm = checkUserManagementPermission(role);
    assert.equal(perm.canOperate, false, `角色 ${role} 不应具备写操作权限`);
    assert.equal(perm.isReadOnly, true, `角色 ${role} 应为只读`);
    assert.match(perm.readOnlyNotice, /仅具备用户与角色列表查阅权限/);
  }

  // 租户强隔离过滤：Alpha 用户只能看到 Alpha 的用户，无法窥探 Beta
  const alphaUsers = filterUsersList(INITIAL_USERS, {}, 'alpha', false);
  assert.ok(alphaUsers.every(u => u.company_id === 'alpha'));
  assert.equal(alphaUsers.some(u => u.company_id === 'beta'), false);

  // 平台超管可查看全部租户
  const allUsers = filterUsersList(INITIAL_USERS, {}, 'system', true);
  assert.equal(allUsers.length, INITIAL_USERS.length);
});

test('8. UsersPage.tsx 与 GlobalPagesContent.tsx AST 静态契约断言', () => {
  const usersPagePath = path.resolve(REPO_ROOT, 'frontend/web/src/admin/UsersPage.tsx');
  assert.ok(fs.existsSync(usersPagePath), 'UsersPage.tsx 必须存在于 admin 域内');
  const usersPageContent = fs.readFileSync(usersPagePath, 'utf-8');

  // 核心 testid 与交互契约断言
  assert.match(usersPageContent, /data-testid="user-management-overview"/);
  assert.match(usersPageContent, /data-testid="user-permission-tag"/);
  assert.match(usersPageContent, /data-testid="user-add-btn"/);
  assert.match(usersPageContent, /data-testid="user-security-policy-btn"/);
  assert.match(usersPageContent, /data-testid="user-filter-bar"/);
  assert.match(usersPageContent, /data-testid="user-table"/);
  assert.match(usersPageContent, /data-testid="user-add-modal"/);
  assert.match(usersPageContent, /data-testid="user-handover-drawer"/);
  assert.match(usersPageContent, /data-testid="handover-warning-alert"/);
  assert.match(usersPageContent, /data-testid="handover-target-select"/);
  assert.match(usersPageContent, /data-testid="handover-confirm-btn"/);
  assert.match(usersPageContent, /data-testid="user-security-policy-drawer"/);

  // 路由集成断言
  const globalPagesPath = path.resolve(REPO_ROOT, 'frontend/web/src/app/GlobalPagesContent.tsx');
  const globalContent = fs.readFileSync(globalPagesPath, 'utf-8');
  assert.match(globalContent, /key: 'users'/);
  assert.match(globalContent, /label: 'A-02 用户与角色'/);
  assert.match(globalContent, /<UsersPage/);
});
