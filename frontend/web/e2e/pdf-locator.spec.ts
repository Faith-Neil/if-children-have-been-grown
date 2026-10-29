// 为什么有这个文件：在真实浏览器里打开招标原件 PDF，点条款来源后跳到所在页并在原件上高亮原句（APP-M2-T103）。
// 原件是有中文文字层的电子版（预定义 CMap、未嵌入字体），同时验证 PDF.js、Worker 与 CMap 都从本站加载。
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
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('clicking a clause source jumps to its page in the original PDF and highlights the sentence', async ({ page, request }) => {
  const projectId = await seedProject(request);
  const external: string[] = [];
  page.on('request', item => {
    const url = new URL(item.url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname) && url.protocol.startsWith('http')) external.push(item.url());
  });
  const cmap = page.waitForResponse(response => response.url().includes('/assets/pdfjs/cmaps/UniGB-UCS2-H.bcmap'));
  await login(page, `/projects/${projectId}/parse`);
  await expect(page.getByTestId('pdf-page')).toBeVisible();
  const card = page.locator('.requirement-card', { hasText: '视为无效投标' });
  await card.locator('.source-link').click();
  await expect(page.getByTestId('pdf-page')).toHaveAttribute('data-page', '2');
  expect((await cmap).ok()).toBeTruthy();
  await expect(page.getByTestId('pdf-hit').first()).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: '已在原件上高亮条款原句' })).toBeVisible();
  const boxes = await page.getByTestId('pdf-hit').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().toJSON()));
  const sheet = await page.getByTestId('pdf-page').boundingBox();
  // 第二页第 3 行：高亮框落在页面上部三分之一内，合起来覆盖整行原句（约 20 个汉字宽）
  const width = Math.max(...boxes.map(b => b.right)) - Math.min(...boxes.map(b => b.left));
  expect(sheet && width > sheet.width / 4 && boxes.every(b => b.top - sheet.y < sheet.height / 3 && b.top > sheet.y)).toBeTruthy();
  // 切到识别文字仍能对照原句
  await page.getByText('识别文字', { exact: true }).click();
  await expect(page.locator('.original-paper mark')).toContainText('视为无效投标');
  expect(external).toEqual([]);
});
