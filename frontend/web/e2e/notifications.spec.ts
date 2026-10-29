// 为什么有这个文件：在真实浏览器里使用站内提醒（PRD v1.8 §5.12.2；APP-M2-T029～T031）。
// 公司管理员新增一份 10 天后到期的证书 → 铃铛显示未读 → 下拉里点提醒跳到资料库并标已读 → “查看全部”进入列表页。
import { expect, test } from '@playwright/test';

test('an expiring certificate raises a reminder that jumps to the library', async ({ page, request }) => {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-company-admin', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const library = await (await request.get('/api/v1/library', { headers: auth })).json();
  const until = new Date(Date.now() + 10 * 86400_000).toISOString().slice(0, 10);
  const name = `浏览器用例证书-${Date.now()}`;
  const created = await request.post('/api/v1/library', {
    headers: { ...auth, 'If-Match': String(library.revision), 'Idempotency-Key': crypto.randomUUID() },
    data: { name, type: 'qualification', content: '合成证书，仅供用例。', valid_until: until, status: 'confirmed' },
  });
  expect(created.ok(), await created.text()).toBeTruthy();

  await page.goto('/workbench');
  await page.getByTestId('login-username-input').fill('alpha-company-admin');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByTestId('notification-bell')).toHaveAttribute('aria-label', /条未读/);
  await page.getByTestId('notification-bell').click();
  const item = page.getByTestId('notification-item').filter({ hasText: name });
  await expect(item).toContainText('资料到期提醒');
  await item.locator('.notice-link').click();
  await expect(page).toHaveURL(/\/library$/);

  await page.getByTestId('notification-bell').click();
  await page.getByTestId('notification-view-all').click();
  await expect(page).toHaveURL(/\/notifications$/);
  const row = page.getByTestId('notifications-table').locator('tr', { hasText: name });
  await expect(row).toContainText('已读');
});
