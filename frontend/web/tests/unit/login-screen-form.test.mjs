// 为什么有这个文件：验证 FE-LOGIN-ACCOUNT-PASSWORD 生产正式账号密码登录表单、超级管理员接入与 Layout First 契约。
// 它解决什么问题：
// 1. 验证即时防空表单校验（validateLoginForm）；
// 2. 验证超级管理员凭据（admin / X_2026）识别与判定；
// 3. 验证端点鉴权胶水（authenticateUser）请求与容错降级；
// 4. 验证登录错误提示格式化（formatLoginErrorMessage）；
// 5. 验证 LoginScreen.tsx AST 静态契约（密码框、回车提交、超管快捷入口、令牌直登扩展槽、无冗余 demo Tabs）；
// 6. 验证 App.tsx 对 onPasswordLogin 的集成装配与行数门禁（<= 400 行）。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

import {
  DEFAULT_SUPERADMIN_USER,
  DEFAULT_SUPERADMIN_PASSWORD,
  DEFAULT_SUPERADMIN,
  validateLoginForm,
  isSuperAdminCredentials,
  authenticateUser,
  formatLoginErrorMessage,
} from '../../src/app/login-auth-core.ts';
import { ApiError } from '../../src/shared/api.ts';

function parseSource(relPath) {
  const fullPath = path.resolve(import.meta.dirname, relPath);
  const content = fs.readFileSync(fullPath, 'utf8');
  const tree = ts.createSourceFile(
    fullPath,
    content,
    ts.ScriptTarget.Latest,
    true
  );
  return { content, tree };
}

test('1. 登录表单校验规则：即时轻量防空校验（validateLoginForm）', () => {
  // 1.1 空账号与空格账号拦截
  const resEmptyUser = validateLoginForm({ username: '', password: 'any-password' });
  assert.equal(resEmptyUser.valid, false);
  assert.equal(resEmptyUser.field, 'username');
  assert.equal(resEmptyUser.message, '请输入用户名 / 账号');

  const resWhitespaceUser = validateLoginForm({ username: '   ', password: 'any-password' });
  assert.equal(resWhitespaceUser.valid, false);
  assert.equal(resWhitespaceUser.field, 'username');

  // 1.2 空密码与空格密码拦截
  const resEmptyPass = validateLoginForm({ username: 'admin', password: '' });
  assert.equal(resEmptyPass.valid, false);
  assert.equal(resEmptyPass.field, 'password');
  assert.equal(resEmptyPass.message, '请输入登录密码');

  const resWhitespacePass = validateLoginForm({ username: 'admin', password: '   ' });
  assert.equal(resWhitespacePass.valid, false);
  assert.equal(resWhitespacePass.field, 'password');

  // 1.3 合法输入校验通过
  const resValid = validateLoginForm({ username: 'admin', password: 'X_2026' });
  assert.equal(resValid.valid, true);
  assert.equal(resValid.field, undefined);
  assert.equal(resValid.message, undefined);
});

test('2. 超级管理员凭据（admin / X_2026）规范与识别', () => {
  assert.equal(DEFAULT_SUPERADMIN_USER, 'admin');
  assert.equal(DEFAULT_SUPERADMIN_PASSWORD, 'X_2026');
  assert.equal(DEFAULT_SUPERADMIN.role, 'platform_admin');

  // 正向识别
  assert.equal(isSuperAdminCredentials('admin', 'X_2026'), true);
  assert.equal(isSuperAdminCredentials(' admin ', 'X_2026'), true, '自动去除首尾空格');

  // 反向拦截
  assert.equal(isSuperAdminCredentials('admin', 'wrong-pass'), false);
  assert.equal(isSuperAdminCredentials('user1', 'X_2026'), false);
  assert.equal(isSuperAdminCredentials('', ''), false);
});

test('3. 账号密码认证胶水函数（authenticateUser）网络交互与异常处理', async () => {
  // 3.1 正常端点调用成功
  const mockRequestSuccess = async (path, token, method, body) => {
    assert.equal(path, '/api/v1/auth/login');
    assert.equal(method, 'POST');
    assert.equal(body.username, 'lead_user');
    assert.equal(body.password, 'mypass123');
    return { access_token: 'mock-valid-token-12345' };
  };

  const token = await authenticateUser('lead_user', 'mypass123', mockRequestSuccess);
  assert.equal(token, 'mock-valid-token-12345');

  // 3.2 表单验证失败直接拦截，不触发网络请求
  let networkCalled = false;
  const mockNetworkNoCall = async () => {
    networkCalled = true;
    return {};
  };
  await assert.rejects(
    async () => authenticateUser('', '123', mockNetworkNoCall),
    /请输入用户名 \/ 账号/
  );
  assert.equal(networkCalled, false);

  // 3.3 业务账号密码错误抛出异常
  const mockAuthReject = async () => {
    throw new ApiError(401, 'INVALID_CREDENTIALS', '用户名或密码错误，请核实后重试。');
  };
  await assert.rejects(
    async () => authenticateUser('unknown_user', 'wrong_pass', mockAuthReject),
    err => err instanceof ApiError && err.status === 401
  );

  // 3.4 超级管理员 admin / X_2026 在端点尚未装配或离线时的容错降级
  const mockEndpoint404 = async path => {
    if (path === '/api/v1/auth/login') {
      throw new ApiError(404, 'NOT_FOUND', 'Not found');
    }
    if (path === '/api/demo/login') {
      return { access_token: 'token-admin-platform' };
    }
    throw new Error('unexpected path');
  };
  const superToken = await authenticateUser('admin', 'X_2026', mockEndpoint404);
  assert.ok(superToken.length > 0);
});

test('4. 错误提示格式化（formatLoginErrorMessage）', () => {
  const apiError401 = new ApiError(401, 'INVALID_CREDENTIALS', '用户名或密码错误');
  assert.equal(formatLoginErrorMessage(apiError401), '用户名或密码错误');

  const apiError500 = new ApiError(500, 'INTERNAL_SERVER_ERROR', '后端服务开小差了');
  assert.equal(formatLoginErrorMessage(apiError500), '后端服务开小差了');

  const stdError = new Error('网络连接超时');
  assert.equal(formatLoginErrorMessage(stdError), '网络连接超时');

  const unknownErr = null;
  assert.equal(formatLoginErrorMessage(unknownErr), '登录认证失败，请核实账号与密码');
});

test('5. LoginScreen.tsx AST 静态契约与 Layout First 规范断言', () => {
  const { content } = parseSource('../../src/app/LoginScreen.tsx');

  // 5.1 包含核心输入与操作组件的 data-testid
  assert.ok(content.includes('data-testid="login-username-input"'), '必须包含账号输入框 testid');
  assert.ok(content.includes('data-testid="login-password-input"'), '必须包含密码输入框 testid');
  assert.ok(content.includes('data-testid="login-submit-button"'), '必须包含登录按钮 testid');
  assert.ok(content.includes('data-testid="login-error-alert"'), '必须包含错误告警条 testid');
  assert.ok(content.includes('data-testid="login-superadmin-shortcut"'), '必须包含超级管理员快捷入口 testid');

  // 5.2 包含密码框可见性与回车快捷提交支持
  assert.ok(content.includes('Input.Password'), '密码输入框必须使用 Input.Password 支持可见性切换');
  assert.ok(content.includes('onPressEnter={handlePasswordSubmit}'), '必须支持回车键快捷提交');

  // 5.3 包含令牌直登扩展槽与切换机制
  assert.ok(content.includes('data-testid="login-token-toggle"'), '必须保留令牌直登切换入口');
  assert.ok(content.includes('data-testid="login-token-input"'), '必须保留令牌输入框');
  assert.ok(content.includes('data-testid="login-token-submit-button"'), '必须保留令牌提交按钮');
  assert.ok(content.includes('data-testid="login-password-toggle"'), '必须包含返回账号密码登录入口');

  // 5.4 贯彻 Layout First：严禁包含旧版体验账号下拉框与冗余 demo Tabs
  assert.ok(!content.includes('aria-label="演示账号"'), '严禁再包含演示账号下拉框 Select');
  assert.ok(!content.includes("key: 'demo'"), '严禁包含旧版 demo Tab');
  assert.ok(!content.includes("label: '体验账号'"), '严禁包含旧版“体验账号”Tab标签');
});

test('6. App.tsx 集成装配与单文件架构门禁（<= 400 行）', () => {
  const { content } = parseSource('../../src/app/App.tsx');

  // 6.1 验证 onPasswordLogin 鉴权装配
  assert.ok(content.includes('loginWithPassword'), 'App.tsx 必须声明 loginWithPassword 鉴权函数');
  assert.ok(content.includes('onPasswordLogin={loginWithPassword}'), 'LoginScreen 必须挂载 onPasswordLogin');
  assert.ok(content.includes('authenticateUser'), 'App.tsx 必须导入 authenticateUser 逻辑');

  // 6.2 严格单文件行数门禁（<= 400 行）
  const lines = content.split('\n').length;
  assert.ok(lines <= 400, `App.tsx 巨石单文件行数必须严格控制在 400 行以内，当前为 ${lines} 行`);
});
