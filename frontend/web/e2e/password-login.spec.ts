// 为什么有这个文件：在真实浏览器里走 APP-M2-T260 口令登录：新账号首次登录被带到改密页 → 页面按规则就近提示 →
// 改密后进入系统；平台管理员在公司管理页停用公司后该公司账号不能登录，再启用恢复。用例自建账号，停用的乙公司在结束时恢复。
import { expect, test, type APIRequestContext } from '@playwright/test';

async function token(request: APIRequestContext, username: string, password = 'X_2026') {
  const res = await request.post('/api/v1/auth/login', { data: { username, password } });
  expect(res.ok(), await res.text()).toBeTruthy();
  return { Authorization: `Bearer ${(await res.json()).access_token}` };
}

test('a new account must change its password before entering', async ({ page, request }) => {
  const admin = await token(request, 'alpha-company-admin');
  const username = `e2e-t260-${Date.now()}`;
  const created = await request.post('/api/v1/users', { headers: admin, data: {
    username, name: '合成首登用户', company_id: 'alpha', role: 'bid_writer', password: 'Init_Pass_2026' } });
  expect(created.ok(), await created.text()).toBeTruthy();

  await page.goto('/');
  await page.getByTestId('login-username-input').fill(username);
  await page.getByTestId('login-password-input').fill('Init_Pass_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByTestId('password-change-card')).toBeVisible();
  await expect(page.getByTestId('password-policy-text')).toContainText('至少 8 位');
  await expect(page.getByRole('button', { name: '退出' })).toHaveCount(0);

  await page.getByTestId('password-old-input').fill('Init_Pass_2026');
  await page.getByTestId('password-new-input').fill('short1');
  await expect(page.getByTestId('password-problems')).toContainText('至少 8 位（现 6 位）');
  await expect(page.getByTestId('password-problems')).toContainText('缺少大写字母、符号');

  await page.getByTestId('password-new-input').fill('Brand_New_2026');
  await page.getByTestId('password-confirm-input').fill('Brand_New_2026');
  await page.getByTestId('password-change-submit').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();

  const again = await request.post('/api/v1/auth/login', { data: { username, password: 'Brand_New_2026' } });
  expect((await again.json()).must_change_password).toBe(false);
});

test('a disabled company cannot log in until it is enabled again', async ({ page, request }) => {
  const platform = await token(request, 'admin');
  try {
    await page.goto('/admin/rules');
    await page.getByTestId('login-username-input').fill('admin');
    await page.getByTestId('login-password-input').fill('X_2026');
    await page.getByTestId('login-submit-button').click();
    await page.getByRole('tab', { name: /A-01/ }).click();
    await expect(page.getByTestId('company-status-beta')).toHaveText('启用');

    await page.getByTestId('company-disable-beta').click();
    const confirm = page.getByTestId('company-disable-confirm');
    await expect(confirm).toBeDisabled();
    const name = (await (await request.get('/api/v1/companies', { headers: platform })).json())
      .items.find((c: { id: string }) => c.id === 'beta').name as string;
    await page.getByTestId('company-disable-name-input').fill(name);
    await confirm.click();
    await expect(page.getByTestId('company-status-beta')).toHaveText('已停用');

    const refused = await request.post('/api/v1/auth/login', { data: { username: 'beta-manager', password: 'X_2026' } });
    expect(refused.status()).toBe(403);
    expect((await refused.json()).code).toBe('COMPANY_DISABLED');

    await page.getByTestId('company-enable-beta').click();
    await expect(page.getByTestId('company-status-beta')).toHaveText('启用');
    const back = await request.post('/api/v1/auth/login', { data: { username: 'beta-manager', password: 'X_2026' } });
    expect(back.ok()).toBeTruthy();
  } finally {
    await request.post('/api/v1/companies/beta/status', { headers: platform, data: { status: 'active' } });
  }
});
