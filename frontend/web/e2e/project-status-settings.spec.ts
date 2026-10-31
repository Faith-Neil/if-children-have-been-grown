// 为什么有这个文件：在真实浏览器里验证项目设置的新分组与取消后只读（APP-M2-T097～T100）：
// 设置页显示合作方缺协议、保存基本信息后出现“已人工修改”、取消项目后设置只读且概览显示“已取消”。
// 本文件在本机未执行（本机无浏览器与后端依赖），由 CI 运行。
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

async function token(request: APIRequestContext, username: string) {
  const res = await request.post('/api/v1/auth/login', { data: { username, password: 'X_2026' } });
  return { Authorization: `Bearer ${(await res.json()).access_token}` };
}

async function login(page: Page) {
  await page.goto('/workbench');
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出', exact: true })).toBeVisible();
}

test('settings show partner agreement gaps, manual-edit marks and become read-only after cancel', async ({ page, request }) => {
  const auth = await token(request, 'alpha-manager');
  const created = await (await request.post('/api/v1/projects', { headers: auth, data: { name: `状态设置-${Date.now()}` } })).json();
  const base = `/api/v1/projects/${created.id}`;
  const revision = async () => (await (await request.get(`${base}/workspace`, { headers: auth })).json()).revision as number;
  const write = async (method: 'patch' | 'post', path: string, data: unknown) => {
    const res = await request[method](`${base}${path}`, { headers: { ...auth, 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() }, data });
    expect(res.ok(), await res.text()).toBeTruthy();
  };
  await write('patch', '', { project_partners: [{ partner_entity_id: 'e2e-partner', agreement_attachment_id: null }], basic_info: { tenderee_name: '合成招标人' } });

  await login(page);
  await page.evaluate(path => { window.history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')); }, `/projects/${created.id}/settings`);
  await expect(page.getByTestId('partners-card')).toContainText('缺协议');
  await expect(page.getByTestId('manual-edit-tenderee_name')).toContainText('已人工修改');
  await expect(page.getByTestId('project-status-tag')).toContainText('草稿');

  await write('post', '/status', { action: 'cancel', reason: '端到端测试取消' });
  await page.reload();
  await expect(page.getByTestId('project-status-tag')).toContainText('已取消');
  await expect(page.getByText('项目已取消，所有设置只读。')).toBeVisible();
  const blocked = await request.patch(base, { headers: { ...auth, 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() }, data: { name: '取消后改名' } });
  expect(blocked.status()).toBe(409);
  expect((await blocked.json()).code).toBe('PROJECT_CANCELLED');
});
