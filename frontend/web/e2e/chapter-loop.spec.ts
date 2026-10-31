// 为什么有这个文件：在真实浏览器里走通章节循环进度页与轮次时间线（APP-M2-T130 / T131）。
// 它解决什么问题：负责人能看到全部章节的循环状态，对有正文的章节重新检查后，时间线逐轮显示查出与修正、
// 依据（任务/模型/输入/版本）与前章摘要接力；只读账号看得到但不能重新检查。

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

// 先前的用例在编辑台打开过本章，编辑权仍在有效期内；重新检查会被如实拒绝（409 CHAPTER_IN_USE）。
// 这里由项目负责人按正式流程接管并释放编辑权，让本用例不依赖执行顺序。
async function freeChapterLock(request: APIRequestContext, chapterId: string) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  expect(login.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const lock = await request.post(`/api/v1/chapters/${chapterId}/lock`, {
    headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, data: { takeover_reason: 'e2e：重新检查前释放遗留编辑权' },
  });
  expect(lock.ok(), await lock.text()).toBeTruthy();
  const release = await request.post(`/api/v1/chapters/${chapterId}/lock/release`, {
    headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, data: { lease_token: (await lock.json()).lease_token },
  });
  expect(release.ok(), await release.text()).toBeTruthy();
}

async function login(page: Page, username: string, path: string) {
  await page.goto(path);
  await page.getByTestId('login-username-input').fill(username);
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('project lead rechecks a chapter and reads its round timeline', async ({ page, request }) => {
  await freeChapterLock(request, 'alpha-tech');
  await login(page, 'alpha-manager', '/projects/alpha-project/manual');
  await page.getByRole('tab', { name: '章节循环进度' }).click();
  const table = page.getByTestId('chapter-loop-table');
  await expect(table.locator('tbody tr').first()).toBeVisible();

  const row = table.locator('tbody tr').filter({ has: page.getByRole('button', { name: '重新检查', disabled: false }) }).first();
  await expect(row).toBeVisible();
  const responded = page.waitForResponse(r => r.url().includes('/loop/recheck'));
  await row.getByRole('button', { name: '重新检查' }).click();
  expect((await responded).status()).toBe(200);
  await expect(row.getByRole('button', { name: '轮次时间线' })).toBeEnabled();
  await expect(row).toContainText('第 1 次');

  await row.getByRole('button', { name: '轮次时间线' }).click();
  const timeline = page.getByTestId('chapter-loop-timeline');
  await expect(timeline.getByTestId('chapter-loop-entry')).toHaveCount(1);
  await expect(timeline).toContainText('重新检查');
  await expect(timeline).toContainText('未调用模型');
  await expect(timeline).toContainText('实际输入');
  await expect(timeline.getByTestId('chapter-loop-round').first()).toContainText('第 1 轮');
  await expect(timeline.locator('.ant-alert')).toHaveCount(1); // 前章摘要接力提示（可用/缺失/第一章三者之一）
});

test('read-only account sees loop progress but cannot recheck', async ({ page }) => {
  await login(page, 'alpha-viewer', '/projects/alpha-project/manual');
  await page.getByRole('tab', { name: '章节循环进度' }).click();
  const table = page.getByTestId('chapter-loop-table');
  await expect(table.locator('tbody tr').first()).toBeVisible();
  await expect(table.getByRole('button', { name: '重新检查', disabled: false })).toHaveCount(0);
});
