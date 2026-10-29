// 为什么有这个文件：在真实浏览器里新建“只写技术标”的项目，确认页面只出现技术分册且导出页说明不需要合标。
// 它解决什么问题：用户要求能只写技术标、不一定合标；页面不能再出现商务分册的定稿、导出与合标入口。

import { expect, test, type Page } from '@playwright/test';

async function login(page: Page, username: string, path: string) {
  await page.goto(path);
  await page.getByTestId('login-username-input').fill(username);
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('project lead creates a technical-only project without a business volume', async ({ page }) => {
  await login(page, 'alpha-manager', '/workbench');
  await page.getByRole('button', { name: /新建项目/ }).first().click();
  const dialog = page.getByRole('dialog', { name: '新建投标项目' });
  await dialog.getByLabel('项目名称').fill(`只写技术标-${Date.now()}`);
  await dialog.getByText('只写技术标（不合标）').click();
  await dialog.getByRole('button', { name: '创建并上传招标文件' }).click();
  await expect(page).toHaveURL(/\/projects\/[^/]+\/tender$/);
  await expect(page.getByTestId('project-header')).not.toContainText('商务分册');
  const projectPath = page.url().replace(/\/tender$/, '');
  await page.evaluate(path => { window.history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')); }, `${new URL(projectPath).pathname}/export`);
  await expect(page.getByTestId('merge-checklist-card')).toContainText('本项目只写技术标，不需要合标');
  await expect(page.getByText('技术、商务两册合订')).toHaveCount(0);
});
