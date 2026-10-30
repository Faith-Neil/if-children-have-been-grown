// 为什么有这个文件：APP-M2-T260 强制改密与公司停用的前端规则测试。
// 它解决什么问题：页面提示的位数与字符类数必须与服务端 password_problems 同一口径（PRD §5.12.1 验收⑧）；
// 须改密的登录不能直接进入系统；公司列表与停用只调后台接口，不再有写死的示例公司。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import * as core from '../../src/app/password-change-core.ts';
import * as auth from '../../src/app/login-auth-core.ts';
import * as company from '../../src/admin/company-manage-core.ts';

const read = rel => fs.readFileSync(path.resolve(import.meta.dirname, rel), 'utf8');

test('1. 字符分类只认 ASCII，空格与中文不计入任何一类', () => {
  assert.deepEqual([...core.charClasses('Aa1!')].sort(), ['digit', 'lower', 'symbol', 'upper']);
  assert.equal(core.charClasses('中文 密码').size, 0);
  assert.deepEqual([...core.charClasses('Ａｂ１')], []); // 全角字母数字不算
});

test('2. 逐项问题与服务端措辞一致', () => {
  assert.deepEqual(core.passwordProblems('short1'), [
    '至少 8 位（现 6 位）',
    '大写字母、小写字母、数字、符号中至少含 3 类（现 2 类，缺少大写字母、符号）',
  ]);
  assert.deepEqual(core.passwordProblems('Brand_New_2026'), []);
  const strict = { min_length: 12, min_char_classes: 4, char_classes: [], scope: 'company' };
  assert.deepEqual(core.passwordProblems('Only_Three1', strict), ['至少 12 位（现 11 位）']);
  assert.deepEqual(core.passwordProblems('Four_Classes_2026', strict), []);
  assert.equal(core.policyText(strict), '至少 12 位，大写字母、小写字母、数字、符号中至少含 4 类');
});

test('3. 改密表单：原密码必填、不能与原密码相同、两次一致', () => {
  assert.equal(core.checkPasswordChange({ oldPassword: '', newPassword: 'x', confirmPassword: 'x' }).field, 'oldPassword');
  const same = core.checkPasswordChange({ oldPassword: 'Init_Pass_2026', newPassword: 'Init_Pass_2026', confirmPassword: 'Init_Pass_2026' });
  assert.equal(same.ok, false);
  assert.ok(same.problems.includes('不能与当前密码相同'));
  const mismatch = core.checkPasswordChange({ oldPassword: 'Init_Pass_2026', newPassword: 'Brand_New_2026', confirmPassword: 'Brand_New_2025' });
  assert.deepEqual(mismatch, { ok: false, field: 'confirmPassword', problems: ['两次输入的新密码不一致'] });
  assert.deepEqual(core.checkPasswordChange({ oldPassword: 'a', newPassword: 'Brand_New_2026', confirmPassword: 'Brand_New_2026' }), { ok: true, problems: [] });
});

test('4. 登录带回须改密；改密与退出只调 /api/v1/auth 接口', async () => {
  const calls = [];
  const fake = async (p, t, m, b) => {
    calls.push([p, t, m, b]);
    if (p === '/api/v1/auth/login') return { access_token: 'tok', must_change_password: true, password_policy: { min_length: 8, min_char_classes: 3, char_classes: [], scope: 'company' } };
    return { success: true };
  };
  const result = await auth.passwordLogin(' writer ', 'Init_Pass_2026', fake);
  assert.deepEqual(result, { token: 'tok', mustChangePassword: true, policy: { min_length: 8, min_char_classes: 3, char_classes: [], scope: 'company' } });
  await auth.changeOwnPassword('tok', 'Init_Pass_2026', 'Brand_New_2026', fake);
  await auth.revokeSession('tok', fake);
  await auth.revokeSession(null, fake);
  assert.deepEqual(calls.map(c => [c[0], c[1], c[2]]), [
    ['/api/v1/auth/login', null, 'POST'],
    ['/api/v1/auth/password', 'tok', 'POST'],
    ['/api/v1/auth/logout', 'tok', 'POST'],
  ]);
  assert.deepEqual(calls[1][3], { old_password: 'Init_Pass_2026', new_password: 'Brand_New_2026' });
  await auth.revokeSession('dead', async () => { throw new Error('401'); }); // 退出不因令牌已失效而报错
});

test('5. App 在须改密时显示改密页，不调用 loginWithToken', () => {
  const app = read('../../src/app/App.tsx');
  assert.match(app, /if \(r\.mustChangePassword\) \{ setPendingChange\(/);
  assert.match(app, /if \(pendingChange\) return <PasswordChangeScreen/);
  assert.match(app, /onLogout=\{\(\) => requestDiscard\(signOut\)\}/);
  const screen = read('../../src/app/PasswordChangeScreen.tsx');
  for (const id of ['password-old-input', 'password-new-input', 'password-confirm-input', 'password-change-submit', 'password-policy-text']) {
    assert.ok(screen.includes(`data-testid="${id}"`), id);
  }
});

test('6. 公司管理只用后台数据', async () => {
  const calls = [];
  const fake = async (p, t, m, b) => { calls.push([p, t, m ?? 'GET', b]); return { items: [], can_change_status: false }; };
  await company.listCompanies(fake, 'tok');
  await company.updateCompanyStatus(fake, 'tok', 'alpha', 'disabled', 'Alpha 科技');
  await company.updateCompanyStatus(fake, 'tok', 'alpha', 'active');
  assert.deepEqual(calls, [
    ['/api/v1/companies', 'tok', 'GET', undefined],
    ['/api/v1/companies/alpha/status', 'tok', 'POST', { status: 'disabled', confirm_name: 'Alpha 科技' }],
    ['/api/v1/companies/alpha/status', 'tok', 'POST', { status: 'active' }],
  ]);
  assert.equal(company.DEFAULT_COMPANIES, undefined);
  const page = read('../../src/admin/CompanyManagePage.tsx');
  for (const fakeText of ['91310000', '华东数智', '法人代表', 'storage_space_id']) assert.ok(!page.includes(fakeText), fakeText);
});
