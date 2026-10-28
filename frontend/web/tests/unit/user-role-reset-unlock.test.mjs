// 为什么有这个测试：严格验证 APP-M2-T028 (A-02 用户角色分配、锁定/解锁与重置密码表单) 的领域逻辑、密码合规重置、锁定解锁保护及 8 角色权限边界。
// 它解决什么问题：防止越权篡改超管角色、防止企业超管越权提权、防止降级持有活动项目的项目负责人导致项目无人负责、确保重置密码符合企业密码合规底线、满足交接约束 M1-P10-F3（已锁定用户显示解锁并恢复活跃）。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  DEFAULT_COMPANY_PASSWORD_POLICY,
  executeLockUser,
  executePasswordReset,
  executeRoleAssignment,
  executeUnlockUser,
  generateCompliantPassword,
  INITIAL_USERS,
  validatePasswordReset,
  validateRoleAssignment,
} from '../../src/admin/user-management-core.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '../../../..');

test('1. 角色分配安全校验：超管保护、企业管理员越权提权拦截与同角色校验', () => {
  const adminUser = INITIAL_USERS.find(u => u.username === 'admin');
  assert.ok(adminUser);

  // 1.1 严禁修改超管角色
  const adminRes = validateRoleAssignment({
    sourceUser: adminUser,
    newRole: 'company_admin',
    operatorRole: 'platform_admin',
  });
  assert.equal(adminRes.valid, false);
  assert.match(adminRes.message || '', /平台超级管理员角色受系统保护/);

  // 1.2 相同角色分配拦截
  const zhang = INITIAL_USERS.find(u => u.username === 'lead_zhang');
  assert.ok(zhang);
  const sameRes = validateRoleAssignment({
    sourceUser: zhang,
    newRole: 'project_lead',
    operatorRole: 'company_admin',
  });
  assert.equal(sameRes.valid, false);
  assert.match(sameRes.message || '', /用户已具备该系统角色/);

  // 1.3 操作者权限不足拦截（普通用户/写手无法分配角色）
  const noPermRes = validateRoleAssignment({
    sourceUser: zhang,
    newRole: 'bid_writer',
    operatorRole: 'bid_writer',
  });
  assert.equal(noPermRes.valid, false);
  assert.match(noPermRes.message || '', /当前操作者无权变更用户角色/);

  // 1.4 企业管理员越权提权拦截（company_admin 不能将用户提权为 platform_admin 或 group_admin）
  const li = INITIAL_USERS.find(u => u.username === 'writer_li');
  assert.ok(li);
  const escalatePlatform = validateRoleAssignment({
    sourceUser: li,
    newRole: 'platform_admin',
    operatorRole: 'company_admin',
  });
  assert.equal(escalatePlatform.valid, false);
  assert.match(escalatePlatform.message || '', /公司管理员无权分配平台级或集团级管理角色/);

  const escalateGroup = validateRoleAssignment({
    sourceUser: li,
    newRole: 'group_admin',
    operatorRole: 'company_admin',
  });
  assert.equal(escalateGroup.valid, false);
  assert.match(escalateGroup.message || '', /公司管理员无权分配平台级或集团级管理角色/);

  // 1.5 平台超管可以分配任何角色
  const platformCanAssign = validateRoleAssignment({
    sourceUser: li,
    newRole: 'company_admin',
    operatorRole: 'platform_admin',
  });
  assert.equal(platformCanAssign.valid, true);
});

test('2. 降级项目负责人时的进行中项目强预警提示', () => {
  // 张建国拥有 2 个进行中项目
  const zhang = INITIAL_USERS.find(u => u.username === 'lead_zhang');
  assert.ok(zhang);
  assert.ok(zhang.assigned_assets.active_projects.length > 0);

  const demoteZhang = validateRoleAssignment({
    sourceUser: zhang,
    newRole: 'bid_writer',
    operatorRole: 'company_admin',
  });
  assert.equal(demoteZhang.valid, true);
  assert.ok(demoteZhang.warning);
  assert.match(demoteZhang.warning, /该用户当前担任 2 个项目的总负责人/);
  assert.match(demoteZhang.warning, /建议及时进行团队调整或资产交接/);

  // 王雪 (auditor) 0 项项目，变更为 viewer 时不应有项目预警
  const wang = INITIAL_USERS.find(u => u.username === 'auditor_wang');
  assert.ok(wang);
  const changeWang = validateRoleAssignment({
    sourceUser: wang,
    newRole: 'viewer',
    operatorRole: 'company_admin',
  });
  assert.equal(changeWang.valid, true);
  assert.equal(changeWang.warning, undefined);
});

test('3. 角色分配执行不可变更新', () => {
  const li = INITIAL_USERS.find(u => u.username === 'writer_li');
  assert.ok(li);
  assert.equal(li.role, 'bid_writer');

  const { updatedUsers, updatedUser } = executeRoleAssignment(INITIAL_USERS, li.id, 'auditor');
  assert.equal(updatedUser.role, 'auditor');
  const updatedLi = updatedUsers.find(u => u.id === li.id);
  assert.ok(updatedLi);
  assert.equal(updatedLi.role, 'auditor');

  // 原列表未被就地污染
  assert.equal(li.role, 'bid_writer');
});

test('4. 重置密码合规校验：符合企业密码策略与确认一致性', () => {
  const policy = DEFAULT_COMPANY_PASSWORD_POLICY;

  // 4.1 弱密码被拦截（过短）
  const shortPwdRes = validatePasswordReset({
    password: 'Ab1!',
    confirmPassword: 'Ab1!',
    policy,
  });
  assert.equal(shortPwdRes.valid, false);
  assert.match(shortPwdRes.message || '', /密码长度至少为 8 位/);

  // 4.2 弱密码被拦截（字符种类不足：仅大小写2类）
  const fewClassesRes = validatePasswordReset({
    password: 'Abcdefghijk',
    confirmPassword: 'Abcdefghijk',
    policy,
  });
  assert.equal(fewClassesRes.valid, false);
  assert.match(fewClassesRes.message || '', /至少包含大写字母、小写字母、数字、特殊符号中的 3 类/);

  // 4.3 确认密码不一致拦截
  const mismatchRes = validatePasswordReset({
    password: 'StrongPwd123!',
    confirmPassword: 'StrongPwd123?',
    policy,
  });
  assert.equal(mismatchRes.valid, false);
  assert.match(mismatchRes.message || '', /两次输入的新密码不一致/);

  // 4.4 合规强密码通过
  const validRes = validatePasswordReset({
    password: 'StrongPwd123!',
    confirmPassword: 'StrongPwd123!',
    policy,
  });
  assert.equal(validRes.valid, true);
  assert.equal(validRes.message, undefined);
});

test('5. 随机合规密码生成器：必含全部4类字符且满足长度策略', () => {
  for (let i = 0; i < 20; i++) {
    const pwd = generateCompliantPassword(DEFAULT_COMPANY_PASSWORD_POLICY);
    assert.ok(pwd.length >= 10);
    assert.ok(/[A-Z]/.test(pwd), '必须包含大写字母');
    assert.ok(/[a-z]/.test(pwd), '必须包含小写字母');
    assert.ok(/[0-9]/.test(pwd), '必须包含数字');
    assert.ok(/[^A-Za-z0-9]/.test(pwd), '必须包含特殊符号');

    const check = validatePasswordReset({
      password: pwd,
      confirmPassword: pwd,
      policy: DEFAULT_COMPANY_PASSWORD_POLICY,
    });
    assert.equal(check.valid, true);
  }
});

test('6. 重置密码执行与锁定账号自动恢复活跃（M1-P10-F3）', () => {
  const lockedChen = INITIAL_USERS.find(u => u.id === 'u_locked_chen');
  assert.ok(lockedChen);
  assert.equal(lockedChen.status, 'locked');

  // 重置密码自动解除锁定
  const { updatedUsers, updatedUser } = executePasswordReset(INITIAL_USERS, lockedChen.id, 'NewSecPass123!');
  assert.equal(updatedUser.status, 'active', '重置密码后应自动解除锁定状态');
  const targetInList = updatedUsers.find(u => u.id === lockedChen.id);
  assert.ok(targetInList);
  assert.equal(targetInList.status, 'active');
});

test('7. 账号手动锁定与解锁逻辑（M1-P10-F3：锁定状态显示解锁按钮）', () => {
  // 7.1 解锁锁定账号
  const lockedChen = INITIAL_USERS.find(u => u.id === 'u_locked_chen');
  assert.ok(lockedChen);
  const { updatedUsers: unlockedList, updatedUser: unlockedChen } = executeUnlockUser(INITIAL_USERS, lockedChen.id);
  assert.equal(unlockedChen.status, 'active');
  const targetUnlocked = unlockedList.find(u => u.id === lockedChen.id);
  assert.ok(targetUnlocked);
  assert.equal(targetUnlocked.status, 'active');

  // 7.2 锁定活跃账号
  const wang = INITIAL_USERS.find(u => u.username === 'auditor_wang');
  assert.ok(wang);
  assert.equal(wang.status, 'active');
  const { updatedUsers: lockedList, updatedUser: lockedWang } = executeLockUser(INITIAL_USERS, wang.id);
  assert.equal(lockedWang.status, 'locked');
  const targetLocked = lockedList.find(u => u.id === wang.id);
  assert.ok(targetLocked);
  assert.equal(targetLocked.status, 'locked');

  // 7.3 超管不可被锁定
  const adminUser = INITIAL_USERS.find(u => u.username === 'admin');
  assert.ok(adminUser);
  assert.throws(() => {
    executeLockUser(INITIAL_USERS, adminUser.id);
  }, /超级管理员账号受系统保护，不可锁定/);
});

test('8. UsersPage.tsx AST 静态契约断言：角色表单、重置密码、锁定/解锁交互元素', () => {
  const usersPagePath = path.resolve(REPO_ROOT, 'frontend/web/src/admin/UsersPage.tsx');
  assert.ok(fs.existsSync(usersPagePath), 'UsersPage.tsx 必须存在于 admin 域内');
  const usersPageContent = fs.readFileSync(usersPagePath, 'utf-8');

  // 角色分配模态框契约
  assert.match(usersPageContent, /data-testid="user-role-modal"/);
  assert.match(usersPageContent, /data-testid="role-select"/);
  assert.match(usersPageContent, /role-confirm-btn/);
  assert.match(usersPageContent, /data-testid="role-change-warning"/);

  // 重置密码模态框契约
  assert.match(usersPageContent, /data-testid="user-reset-pwd-modal"/);
  assert.match(usersPageContent, /data-testid="reset-pwd-input"/);
  assert.match(usersPageContent, /data-testid="reset-pwd-confirm-input"/);
  assert.match(usersPageContent, /data-testid="reset-pwd-generate-btn"/);
  assert.match(usersPageContent, /reset-pwd-submit-btn/);

  // 操作列按钮契约 (M1-P10-F3)
  assert.match(usersPageContent, /data-testid=\{`user-unlock-btn-\$\{record\.id\}`\}/);
  assert.match(usersPageContent, /data-testid=\{`user-lock-btn-\$\{record\.id\}`\}/);
  assert.match(usersPageContent, /data-testid=\{`user-role-btn-\$\{record\.id\}`\}/);
  assert.match(usersPageContent, /data-testid=\{`user-reset-pwd-btn-\$\{record\.id\}`\}/);

  // 锁定状态徽标 (Badge)
  assert.match(usersPageContent, /已锁定 \(登录超限\)/);
});
