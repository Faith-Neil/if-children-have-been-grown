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

test('parse page: original · category tree · cards, with gated confirmation', async ({ page, request }) => {
  const id = await seed(request);
  await page.goto(`/projects/${id}/parse`);
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByTestId('parse-tree-category')).toHaveCount(10);
  // 从左到右：原文预览、分类树、条目卡片
  const boxes = await Promise.all(['.original-preview', '.parse-category', '.parse-cards'].map(s => page.locator(s).boundingBox()));
  expect(boxes[0]!.x < boxes[1]!.x && boxes[1]!.x < boxes[2]!.x).toBeTruthy();
  await expect(page.getByTestId('parse-confirm-button')).toBeDisabled();
  await expect(page.getByTestId('parse-gate-summary')).toContainText('还差');
  await page.locator('[data-category="star"]').click();
  await expect(page.getByTestId('parse-individual-only')).toBeVisible();
  await expect(page.getByTestId('parse-batch-confirm')).toHaveCount(0);
  await page.locator('[data-category="scoring"]').click();
  await expect(page.getByTestId('parse-tree-group').first()).toContainText('要点');
  await page.locator('[data-category="technical"]').click();
  const batch = page.getByTestId('parse-batch-confirm');
  await expect(batch).toContainText(/确认本类 [1-9]/);
  await batch.click();
  await expect(batch).toContainText('确认本类 0 条');
  await expect(page.locator('.parse-cards .requirement-card').first()).toContainText('已确认');
});
