// 为什么有这个文件：在真实浏览器里使用解析结果页（PRD v1.8 §5.2.2；APP-M2-T104）：三栏顺序、10 类分类树、
// 评分项展开得分要点、星号类没有批量确认、其他类可批量确认，确认按钮旁列出还差的前提。
import { expect, test, type APIRequestContext } from '@playwright/test';

const TENDER = '合成招标文件：解析三栏验收\n招标编号：E2E-TREE\n第二章 评分办法\n一、技术方案（20分）\n1. 架构设计合理的得10分。\n2. 运维方案完整的得10分。\n'
  + '第三章 技术要求\n★1. 提供7×24小时驻场服务。\n2. 每月完成巡检并提交报告。\n3. 按季度提交运维分析报告。\n';

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const id = (await (await request.post('/api/v1/projects', { headers: auth, data: { name: `解析三栏-${Date.now()}` } })).json()).id as string;
  const revision = async () => (await (await request.get(`/api/v1/projects/${id}/workspace`, { headers: auth })).json()).revision;
  const up = await request.post(`/api/v1/projects/${id}/files/raw?filename=tender.txt`, {
    headers: { ...auth, 'Content-Type': 'application/octet-stream', 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() },
    data: Buffer.from(TENDER, 'utf-8') });
  expect(up.ok(), await up.text()).toBeTruthy();
  const parsed = await request.post(`/api/v1/projects/${id}/parse`, { headers: { ...auth, 'If-Match': String(await revision()), 'Idempotency-Key': crypto.randomUUID() }, data: {} });
  expect(parsed.ok(), await parsed.text()).toBeTruthy();
  return id;
}

test('parsed tender opens the editor so the directory can be confirmed', async ({ page, request }) => {
  const id = await seed(request);
  await page.goto(`/projects/${id}/tender`);
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('cell', { name: 'tender.txt' })).toBeVisible();
  await expect(page.getByRole('cell', { name: '已解析' })).toBeVisible();
  await page.getByRole('tab', { name: '覆盖视图' }).click();
  await expect(page.getByTestId('coverage-view')).toBeVisible();
});
