// 为什么有这个文件：在真实浏览器里打开解析页原文预览，点条款来源后跳到对应页并用 <mark> 高亮原句。
// 预览已改为 HTML 纸页（不再默认挂 PDF.js canvas）；仍校验不向外网拉资源。
import { readFileSync } from 'node:fs';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const PDF = readFileSync(new URL('./fixtures/tender-text-layer.pdf', import.meta.url));

async function seedProject(request: APIRequestContext): Promise<string> {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const created = await request.post('/api/v1/projects', { headers: auth, data: { name: `原件定位-${Date.now()}` } });
  const id = (await created.json()).id as string;
  const revision = async () => (await (await request.get(`/api/v1/projects/${id}/workspace`, { headers: auth })).json()).revision;
  const upload = await request.post(`/api/v1/projects/${id}/files/raw?filename=${encodeURIComponent('原件定位.pdf')}`, {
    headers: { ...auth, 'Content-Type': 'application/octet-stream', 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() },
    data: PDF,
  });
  expect(upload.ok(), await upload.text()).toBeTruthy();
  const parsed = await request.post(`/api/v1/projects/${id}/parse`, {
    headers: { ...auth, 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() }, data: {},
  });
  expect(parsed.ok(), await parsed.text()).toBeTruthy();
  return id;
}

async function login(page: Page, path: string) {
  await page.goto(path);
  const usernameInput = page.getByTestId('login-username-input');
  if (await usernameInput.isVisible({ timeout: 5000 }).catch(() => false)) {
    await usernameInput.fill('alpha-manager');
    await page.getByTestId('login-password-input').fill('X_2026');
    await page.getByTestId('login-submit-button').click();
  }
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('clicking a clause source jumps to its page in the original PDF and highlights the sentence', async ({ page, request }) => {
  const projectId = await seedProject(request);
  const external: string[] = [];
  page.on('request', item => {
    const url = new URL(item.url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname) && url.protocol.startsWith('http')) external.push(item.url());
  });
  await login(page, `/projects/${projectId}/parse`);
  await expect(page.locator('.original-paper').first()).toBeVisible();
  const card = page.locator('.requirement-card', { hasText: '视为无效投标' });
  await card.locator('.source-link').click();
  await expect(page.locator('#doc-page-2.original-paper.is-current')).toBeVisible();
  await expect(page.locator('.original-paper.is-current mark')).toContainText('视为无效投标');
  expect(external).toEqual([]);
});
