// 为什么有这个文件：在真实浏览器里下载内部响应追溯表 Excel（APP-M2-T201），并确认合标核对清单卡片不再是写死的提示。
// 它解决什么问题：Excel 必须是后台真实生成的 .xlsx（以 PK 压缩包开头），页面按钮能直接拿到文件。

import { readFileSync } from 'node:fs';
import { expect, test, type Page } from '@playwright/test';

async function login(page: Page, username: string, path: string) {
  await page.goto(path);
  await page.getByTestId('login-username-input').fill(username);
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('project lead downloads the internal response trace Excel', async ({ page }) => {
  await login(page, 'alpha-manager', '/projects/alpha-project/export');
  await expect(page.getByTestId('merge-checklist-card')).toContainText('导出递交版时会同时生成合标核对清单');
  const waiting = page.waitForEvent('download');
  await page.getByTestId('response-trace-btn').click();
  const file = await waiting;
  expect(file.suggestedFilename()).toMatch(/^response-trace-.*\.xlsx$/);
  const path = await file.path();
  expect(readFileSync(path).subarray(0, 2).toString()).toBe('PK');
});
