// 为什么有这个文件：验证生产登录：只走 /api/v1/auth/login，前端不内置任何账号口令、不做离线回退、不提供令牌直登。
// 它解决什么问题：防止“填入超级管理员”“演示账号”“本地签发令牌”这类后门回到登录页。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import * as auth from '../../src/app/login-auth-core.ts';
import { ApiError } from '../../src/shared/api.ts';

const read = rel => fs.readFileSync(path.resolve(import.meta.dirname, rel), 'utf8');

test('1. 表单校验', () => {
  assert.deepEqual(auth.validateLoginForm({ username: ' ', password: 'x' }), { valid: false, field: 'username', message: '请输入用户名' });
  assert.deepEqual(auth.validateLoginForm({ username: 'u', password: ' ' }), { valid: false, field: 'password', message: '请输入登录密码' });
  assert.deepEqual(auth.validateLoginForm({ username: 'u', password: 'p' }), { valid: true });
});

test('2. 不内置任何账号口令', () => {
  assert.equal(auth.DEFAULT_SUPERADMIN_PASSWORD, undefined);
  assert.equal(auth.isSuperAdminCredentials, undefined);
  const source = read('../../src/app/login-auth-core.ts');
  assert.ok(!source.includes('X_2026') && !source.includes('/api/demo') && !source.includes('token-admin'));
});

test('3. 认证只调用 /api/v1/auth/login，失败如实抛出', async () => {
  const calls = [];
  const ok = async (p, t, m, b) => { calls.push([p, m, b]); return { access_token: 'tok' }; };
  assert.equal(await auth.authenticateUser(' lead ', 'pw', ok), 'tok');
  assert.deepEqual(calls, [['/api/v1/auth/login', 'POST', { username: 'lead', password: 'pw' }]]);
  const rejected = async () => { throw new ApiError(401, 'INVALID_CREDENTIALS', '用户名或密码错误'); };
  await assert.rejects(() => auth.authenticateUser('admin', 'whatever', rejected), error => error instanceof ApiError);
  let called = false;
  await assert.rejects(() => auth.authenticateUser('', 'pw', async () => { called = true; return {}; }));
  assert.equal(called, false);
  await assert.rejects(() => auth.authenticateUser('u', 'p', async () => ({})), /缺少访问令牌/);
});

test('4. 错误文案', () => {
  assert.equal(auth.formatLoginErrorMessage(new ApiError(401, 'INVALID_CREDENTIALS', '')), '用户名或密码错误，请核实后重试');
  assert.equal(auth.formatLoginErrorMessage(new ApiError(423, 'ACCOUNT_LOCKED', '')), '账号已被锁定，请联系管理员解锁');
  assert.equal(auth.formatLoginErrorMessage(new TypeError('fetch failed')), '无法连接服务器，请检查网络后重试');
});

test('5. 登录页只有账号密码表单', () => {
  const content = read('../../src/app/LoginScreen.tsx');
  for (const id of ['login-username-input', 'login-password-input', 'login-submit-button', 'login-error-alert']) {
    assert.ok(content.includes(`data-testid="${id}"`), id);
  }
  for (const banned of ['login-superadmin-shortcut', 'login-token-toggle', 'login-token-input', '演示账号', 'X_2026']) {
    assert.ok(!content.includes(banned), banned);
  }
  assert.ok(content.includes('Input.Password') && content.includes('onPressEnter={handlePasswordSubmit}'));
});

test('6. App 只挂载密码登录且不调用演示接口', () => {
  const content = read('../../src/app/App.tsx');
  assert.ok(content.includes('onPasswordLogin={loginWithPassword}'));
  assert.ok(!content.includes('/api/demo') && !content.includes('isDemoMode'));
  assert.ok(content.split('\n').length <= 400);
});
