// 为什么有这个文件：核对技术方案工作台里，项目经理不能补录资料库，设置仍可保存，覆盖视图不再提供挂证据。
// 它解决什么问题：资料库写入属于公司管理员；覆盖视图不再走商务证据抽屉。
import { expect, test, type Page } from '@playwright/test';

const project = '/projects/alpha-project';

async function login(page: Page, accountTitle?: string) {
  await page.goto('/');
  let username = 'alpha-manager';
  if (accountTitle) {
    if (accountTitle.includes('查看人') || accountTitle.includes('viewer')) {
      username = 'alpha-viewer';
    } else if (accountTitle.includes('乙公司') || accountTitle.includes('beta')) {
      username = 'beta-editor';
    } else if (accountTitle.includes('编写人') || accountTitle.includes('editor')) {
      username = 'alpha-editor';
    }
  }
  const usernameInput = page.getByTestId('login-username-input');
  if (await usernameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await usernameInput.fill(username);
    await page.getByTestId('login-password-input').fill('X_2026');
    await page.getByTestId('login-submit-button').click();
  } else {
    if (accountTitle) {
      await page.locator('.login-card .ant-select-selector').click();
      await page.getByTitle(accountTitle).click();
    }
    await page.getByRole('button', { name: '进入工作台' }).click();
  }
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

async function go(page: Page, path: string) {
  await page.evaluate(next => {
    window.history.pushState({}, '', next);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, path);
  await expect(page).toHaveURL(new RegExp(`${path}$`));
}

test('project manager cannot create library records, can save settings, and coverage has no evidence attach', async ({ page }) => {
  await login(page);
  await go(page, '/library');
  await expect(page.getByTestId('create-evidence-button')).toBeDisabled();

  await go(page, `${project}/settings`);
  await page.locator('#project-setting-basic').getByLabel('投标截止时间').fill('2026-12-31 17:00');
  await page.locator('#project-setting-basic').getByRole('button', { name: '保存基本信息' }).click();
  await expect(page.getByText('基本信息已保存，旧检查与输出需按当前资料重新核对。')).toBeVisible();

  await go(page, `${project}/analyze`);
  await expect(page.getByTestId('coverage-view')).toBeVisible();
  await expect(page.getByRole('button', { name: '挂证据' })).toHaveCount(0);
});
