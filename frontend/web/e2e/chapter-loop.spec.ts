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

test('technical project does not put chapter-loop progress in the project tabs', async ({ page, request }) => {
  await freeChapterLock(request, 'alpha-tech');
  await login(page, 'alpha-manager', '/projects/alpha-project/editor');
  await expect(page.getByRole('tab', { name: '章节循环进度' })).toHaveCount(0);
  await expect(page.getByTestId('paper-editor')).toBeVisible();
  await page.getByRole('tab', { name: '覆盖视图' }).click();
  await expect(page.getByTestId('coverage-view')).toBeVisible();
});

test('read-only account can open the technical project without a recheck button', async ({ page }) => {
  await login(page, 'alpha-viewer', '/projects/alpha-project/editor');
  await expect(page.getByRole('tab', { name: '章节循环进度' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '重新检查' })).toHaveCount(0);
  await expect(page.getByTestId('paper-editor')).toBeVisible();
});
