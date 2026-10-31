// 为什么有这个文件：在真实浏览器里走一遍 R19 关联投标冲突（APP-M2-T096）：乙公司已对某标段立项，
// 甲公司新建同一招标编号的项目时弹出提示，只显示乙公司名称；不写说明不能继续，写明后项目与招标编号保存，项目设置显示已确认。
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

async function token(request: APIRequestContext, username: string) {
  const res = await request.post('/api/v1/auth/login', { data: { username, password: 'X_2026' } });
  return { Authorization: `Bearer ${(await res.json()).access_token}` };
}

async function betaProject(request: APIRequestContext, number: string) {
  const auth = await token(request, 'beta-manager');
  const project = await (await request.post('/api/v1/projects', { headers: auth, data: { name: '乙公司保密项目名称' } })).json();
  const patched = await request.patch(`/api/v1/projects/${project.id}`, { headers: {
    ...auth, 'If-Match': String(project.revision), 'Idempotency-Key': crypto.randomUUID() }, data: { tender_number: number } });
  expect(patched.ok(), await patched.text()).toBeTruthy();
}

async function login(page: Page) {
  await page.goto('/workbench');
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出', exact: true })).toBeVisible();
}

test('creating a project on a lot another group company has entered needs a written reason', async ({ page, request }) => {
  const number = `E2E-R19-${Date.now()}`;
  await betaProject(request, number);
  await login(page);
  await page.getByRole('button', { name: /新建项目/ }).first().click();
  const dialog = page.getByRole('dialog', { name: '新建投标项目' });
  await dialog.getByLabel('项目名称').fill(`甲公司同标段-${Date.now()}`);
  await dialog.getByLabel('招标编号').fill(number.toLowerCase());
  await dialog.getByRole('button', { name: '创建并上传招标文件' }).click();

  const prompt = page.getByTestId('related-bid-prompt');
  await expect(prompt).toContainText('第三十四条');
  await expect(prompt).not.toContainText('乙公司保密项目名称');
  const confirm = page.getByRole('button', { name: '确认无上述关系并继续' });
  await confirm.click();
  await expect(prompt).toBeVisible();  // 不写说明不能继续
  await page.getByTestId('related-bid-reason').fill('甲公司与乙公司无控股、管理关系，负责人不同');
  await confirm.click();
  await expect(page).toHaveURL(/\/projects\/[^/]+\/tender$/);

  const projectId = new URL(page.url()).pathname.split('/')[2];
  const auth = await token(request, 'alpha-manager');
  const status = await (await request.get(`/api/v1/projects/${projectId}/related-bids`, { headers: auth })).json();
  expect(status.needs_ack).toBe(false);
  expect(status.acknowledged.reason).toContain('无控股');
  const workspace = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  expect(workspace.project.tender_number).toBe(number.toLowerCase());

  await page.evaluate(path => { window.history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')); }, `/projects/${projectId}/settings`);
  await expect(page.getByTestId('related-bid-acknowledged')).toContainText('无关联关系');
});
