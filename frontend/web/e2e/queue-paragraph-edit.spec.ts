// 为什么有这个文件：在真实浏览器里走通人工处理队列的单段编辑（APP-M2-T134）。
// 它解决什么问题：负责人在队列里直接改写问题所在的那一段，只有这一段变化。只读账号不出现按钮由后端用例覆盖（新建项目里没有该账号的成员关系）。
// 用例自己建项目并通过接口造出待处理问题，不依赖共用示例项目的状态与用例顺序。
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const PLACEHOLDER = '项目业绩见【待补：同类业绩】。';
const BODY = `运维服务方案\n${PLACEHOLDER}\n巡检每月一次。`;
const REPLACEMENT = '项目业绩见合同编号 HT-001。';

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const created = await request.post('/api/v1/projects', { headers: auth, data: { name: `队列单段编辑-${Date.now()}` } });
  const projectId = (await created.json()).id as string;
  const workspace = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const chapter = workspace.chapters.find((c: { volume: string }) => c.volume === 'technical');
  const lock = await (await request.post(`/api/chapters/${chapter.id}/lock`, { headers: auth, data: {} })).json();
  const committed = await request.post(`/api/chapters/${chapter.id}/versions`, { headers: auth, data: {
    lease_token: lock.lease_token, base_revision: chapter.revision, content: BODY, idempotency_key: crypto.randomUUID() } });
  expect(committed.ok(), await committed.text()).toBeTruthy();
  const released = await request.post(`/api/chapters/${chapter.id}/lock/release`, { headers: auth, data: { lease_token: lock.lease_token } });
  expect(released.ok(), await released.text()).toBeTruthy();
  const fresh = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const recheck = await request.post(`/api/v1/projects/${projectId}/chapters/${chapter.id}/loop/recheck`, {
    headers: { ...auth, 'If-Match': String(fresh.revision), 'Idempotency-Key': crypto.randomUUID() }, data: {} });
  expect(recheck.ok(), await recheck.text()).toBeTruthy();
  const queue = await (await request.get(`/api/v1/projects/${projectId}/human-queue`, { headers: auth })).json();
  expect(queue.summary.pending).toBeGreaterThan(0);
  return { projectId, chapterId: chapter.id as string, auth };
}

async function login(page: Page, username: string, projectId: string) {
  await page.goto(`/projects/${projectId}/manual`);
  await page.getByTestId('login-username-input').fill(username);
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('project lead rewrites only the flagged paragraph from the queue', async ({ page, request }) => {
  const { projectId, chapterId, auth } = await seed(request);
  await login(page, 'alpha-manager', projectId);
  const issue = page.getByTestId('manual-queue-issue').filter({ hasText: '第 2 段' }).first();
  await expect(issue).toBeVisible();
  await issue.getByTestId('queue-edit-paragraph').click();
  const text = page.getByTestId('queue-edit-text');
  await expect(text).toHaveValue(PLACEHOLDER);
  await text.fill(REPLACEMENT);
  const responded = page.waitForResponse(r => r.url().includes('/human-queue/issues/') && r.url().endsWith('/edit'));
  await page.getByRole('button', { name: '保存本段并标为已处理' }).click();
  expect((await responded).status()).toBe(200);

  const chapter = await (await request.get(`/api/chapters/${chapterId}`, { headers: auth })).json();
  expect(chapter.content).toBe(`运维服务方案\n${REPLACEMENT}\n巡检每月一次。`);
});
