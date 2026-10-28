// 为什么有这个文件：用正式账号（资料管理员）走通知识类业务流程：方案片段新建→被拦截→修正→发布，
// 资料库按后端类别录入，知识库管理页在未连接 RAGFlow 时如实提示。
// 它解决什么问题：这些页面此前只能看不能写，或提交的类别后端不认（422），只有单元测试覆盖不到。

import { expect, test, type Page } from '@playwright/test';

async function login(page: Page, username: string, path = '/knowledge') {
  await page.goto(path);
  await page.getByTestId('login-username-input').fill(username);
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('data admin creates, fixes and publishes a snippet', async ({ page }) => {
  await login(page, 'alpha-data-admin');
  await page.getByTestId('snippet-create-button').click();
  const drawer = page.getByRole('dialog', { name: '新建方案片段' });
  const product = `合成巡检方案-${Date.now()}`;
  await drawer.getByLabel('产品 / 方案名称').fill(product);
  await drawer.getByLabel('片段正文').fill('每月巡检一次，一级故障 {{response_minutes}} 分钟内响应。');
  await expect(drawer.getByText('正文使用了未声明的变量')).toBeVisible();
  await drawer.getByTestId('snippet-publish-button').click();
  await expect(page.getByTestId('snippet-block-reasons')).toContainText('未声明的变量');
  await page.getByRole('button', { name: '全部声明' }).click();
  await page.getByTestId('snippet-publish-button').click();
  await expect(page.getByText('已发布。系统正在把它同步到公司知识库')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('row', { name: new RegExp(product) })).toBeVisible();
});

test('library form uses backend categories and the knowledge base admin page is honest when unconnected', async ({ page }) => {
  await login(page, 'alpha-data-admin', '/library');
  await page.getByTestId('create-evidence-button').click();
  const dialog = page.getByRole('dialog', { name: '补录企业资料' });
  const name = `合成服务承诺-${Date.now()}`;
  await dialog.getByLabel('资料名称').fill(name);
  await dialog.locator('.ant-form-item').filter({ has: page.getByText('资料类别', { exact: true }) }).locator('.ant-select-selector').click();
  await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').getByText('服务承诺', { exact: true }).click();
  await dialog.getByLabel('资料内容要点与证明事实').fill('7×24 小时响应，合成测试数据。');
  await dialog.locator('.ant-form-item').filter({ has: page.getByText('核验状态', { exact: true }) }).locator('.ant-select-selector').click();
  await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').getByText('待核验 (暂不可引用)', { exact: true }).click();
  await dialog.getByRole('button', { name: '保存提交审核' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('row', { name: new RegExp(name) })).toBeVisible();
  await expect(page.getByTestId('knowledge-base-panel')).toContainText('尚未配置知识库');

  await page.evaluate(() => { window.history.pushState({}, '', '/knowledge'); window.dispatchEvent(new PopStateEvent('popstate')); });
  await page.getByText('知识库管理（RAGFlow）', { exact: true }).click();
  await expect(page.getByTestId('kb-admin-page')).toContainText('尚未连接 RAGFlow');
});
