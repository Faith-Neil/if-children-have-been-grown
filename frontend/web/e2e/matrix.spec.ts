// 为什么有这个文件：在真实浏览器里使用响应矩阵：风险列、批量智能匹配抽屉与 Excel 导出（APP-M2-T112～T117）。
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const TENDER = '合成招标文件：矩阵验收\n招标编号：E2E-MATRIX\n★技术要求：每月完成巡检并提交报告。\n商务要求：提供有效企业资质证明。';

// 新建一个项目并上传、解析招标文件，避免改动其他用例共用的示例项目
async function seedProject(request: APIRequestContext): Promise<string> {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const created = await request.post('/api/v1/projects', { headers: auth, data: { name: `矩阵验收-${Date.now()}` } });
  const id = (await created.json()).id as string;
  const revision = async () => (await (await request.get(`/api/v1/projects/${id}/workspace`, { headers: auth })).json()).revision;
  const upload = await request.post(`/api/v1/projects/${id}/files/raw?filename=tender.txt`, {
    headers: { ...auth, 'Content-Type': 'application/octet-stream', 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() },
    data: Buffer.from(TENDER, 'utf-8'),
  });
  expect(upload.ok(), await upload.text()).toBeTruthy();
  const parsed = await request.post(`/api/v1/projects/${id}/parse`, {
    headers: { ...auth, 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() }, data: {},
  });
  expect(parsed.ok(), await parsed.text()).toBeTruthy();
  return id;
}

async function login(page: Page, username: string, path: string) {
  await page.goto(path);
  await page.getByTestId('login-username-input').fill(username);
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('lead opens the coverage view after the tender is parsed', async ({ page, request }) => {
  const projectId = await seedProject(request);
  await login(page, 'alpha-manager', `/projects/${projectId}/tender`);
  await expect(page.getByRole('cell', { name: '已解析' })).toBeVisible();
  await page.getByRole('tab', { name: '覆盖视图' }).click();
  await expect(page.getByTestId('coverage-view')).toBeVisible();
  await expect(page.getByTestId('coverage-view-notice')).toContainText('不挡');
  await expect(page.getByRole('button', { name: '挂证据' })).toHaveCount(0);
});
