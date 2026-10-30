// 为什么有这个文件：在真实浏览器里走一遍后台解析任务与进度订阅（APP-M2-T020）：
// 点“解析招标文件”后页面显示任务进度，完成后进入解析结果；事件流被断开时提示已切换为定时刷新，靠轮询同一任务走完。
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const TENDER = '合成招标文件：解析任务验收\n招标编号：E2E-JOB\n投标截止时间：2026-12-31T17:00:00+08:00\n第三章 技术要求\n1. ★提供7×24小时驻场服务。\n2. 每月提交巡检报告。\n';

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const projectId = (await (await request.post('/api/v1/projects', { headers: auth, data: { name: `解析任务-${Date.now()}` } })).json()).id as string;
  const revision = (await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json()).revision;
  const up = await request.post(`/api/v1/projects/${projectId}/files/raw?filename=tender.txt`, {
    headers: { ...auth, 'If-Match': String(revision), 'Idempotency-Key': crypto.randomUUID(), 'Content-Type': 'application/octet-stream' },
    data: Buffer.from(TENDER, 'utf-8') });
  expect(up.ok(), await up.text()).toBeTruthy();
  return projectId;
}

async function open(page: Page, projectId: string) {
  await page.goto(`/projects/${projectId}/tender`);
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('cell', { name: 'tender.txt' })).toBeVisible();
}

test('parsing runs as a background job and lands on the parse results', async ({ page, request }) => {
  const projectId = await seed(request);
  await open(page, projectId);
  const started = page.waitForResponse(r => r.url().endsWith('/parse/jobs') && r.request().method() === 'POST');
  await page.getByRole('button', { name: '解析招标文件' }).click();
  expect((await started).status()).toBe(202);
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/parse$`), { timeout: 15_000 });
  await expect(page.getByText(/原文抽取 [1-9]\d* 条/)).toBeVisible();
});

test('when the event stream drops the page says so and finishes by polling', async ({ page, request }) => {
  const projectId = await seed(request);
  await page.route('**/api/v1/jobs/*/events', route => route.abort('connectionreset'));
  await page.route(/\/api\/v1\/jobs\/[^/]+$/, async route => {
    await new Promise(resolve => setTimeout(resolve, 1500));  // 让“已切换为定时刷新”的提示停留可见
    await route.continue();
  });
  await open(page, projectId);
  await page.getByRole('button', { name: '解析招标文件' }).click();
  await expect(page.getByTestId('parse-job-card').getByTestId('job-stream-fallback-tag')).toBeVisible({ timeout: 20_000 });
  await expect(page).toHaveURL(new RegExp(`/projects/${projectId}/parse$`), { timeout: 20_000 });
});
