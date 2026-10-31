// 为什么有这个文件：在真实浏览器里验证 WP-4 前端（APP-M2-T097～T102、T107、T109、T110）：
// 招标文件页的类型/版本/解析服务列，以及解析页的合并建议入口。本机无法运行，由 CI 的 Playwright 执行。
import { expect, test, type APIRequestContext } from '@playwright/test';

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const id = (await (await request.post('/api/v1/projects', { headers: auth, data: { name: `解析后处理-${Date.now()}` } })).json()).id as string;
  const revision = async () => (await (await request.get(`/api/v1/projects/${id}/workspace`, { headers: auth })).json()).revision;
  const upload = async (name: string, role: string, text: string) => {
    const up = await request.post(`/api/v1/projects/${id}/files/raw?filename=${name}&file_role=${role}`, {
      headers: { ...auth, 'Content-Type': 'application/octet-stream', 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() },
      data: Buffer.from(text, 'utf-8') });
    expect(up.ok(), await up.text()).toBeTruthy();
  };
  await upload('tender.txt', 'tender', '合成招标文件\n投标保证金：5万元\n服务期限：12个月\n★提供7×24小时驻场服务。\n');
  await upload('addendum.txt', 'addendum', '合成补遗\n投标保证金：8万元\n');
  const parsed = await request.post(`/api/v1/projects/${id}/parse`, { headers: { ...auth, 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() }, data: {} });
  expect(parsed.ok(), await parsed.text()).toBeTruthy();
  return id;
}

async function login(page: import('@playwright/test').Page, path: string) {
  await page.goto(path);
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
}

test('tender page shows role, version and parse service columns', async ({ page, request }) => {
  const id = await seed(request);
  await login(page, `/projects/${id}/tender`);
  await expect(page.getByTestId('file-role-select')).toHaveCount(2);
  await expect(page.getByTestId('file-version').first()).toContainText('v1');
  await expect(page.getByTestId('file-parse-service').first()).toBeVisible();
  await expect(page.getByTestId('retry-service-button').first()).toBeVisible();
});

test('parse page conflict drawer requires a reason before deciding', async ({ page, request }) => {
  const id = await seed(request);
  await login(page, `/projects/${id}/parse`);
  await expect(page.getByTestId('merge-button')).toBeVisible();
  await page.getByRole('button', { name: /冲突待选定/ }).first().click();
  const cards = page.getByTestId('conflict-card');
  if (await cards.count()) {
    const first = cards.first();
    await expect(first.getByTestId('conflict-values')).toBeVisible();
    await expect(first.getByTestId('conflict-not-conflict')).toBeVisible();
    await first.getByTestId('conflict-not-conflict').click();
    await expect(first.getByRole('alert')).toContainText('理由');
  }
});
