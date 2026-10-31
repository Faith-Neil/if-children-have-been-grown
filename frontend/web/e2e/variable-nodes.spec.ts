// 为什么有这个文件：在真实浏览器里走一遍变量节点（APP-M2-T164）：已确认事实的变量按取值带底色显示 →
// 编辑时变量栏列出取值 → 写入不存在的变量提交被拒，正文不变，提示去数据源。用例自己建项目，不改动共用的示例项目。
import { expect, test, type APIRequestContext } from '@playwright/test';

const TENDER = '合成招标文件：变量节点验收\n招标编号：E2E-VAR\n服务期限：12个月\n第三章 技术要求\n1. 提供7×24小时驻场服务。\n';

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const projectId = (await (await request.post('/api/v1/projects', { headers: auth, data: { name: `变量节点-${Date.now()}` } })).json()).id as string;
  const workspace = async () => (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const write = async () => ({ ...auth, 'If-Match': String((await workspace()).revision), 'Idempotency-Key': crypto.randomUUID() });
  const up = await request.post(`/api/v1/projects/${projectId}/files/raw?filename=tender.txt`, {
    headers: { ...(await write()), 'Content-Type': 'application/octet-stream' }, data: Buffer.from(TENDER, 'utf-8') });
  expect(up.ok(), await up.text()).toBeTruthy();
  const parsed = await request.post(`/api/v1/projects/${projectId}/parse`, { headers: await write(), data: {} });
  expect(parsed.ok(), await parsed.text()).toBeTruthy();
  const facts = (await workspace()).facts as { id: string; key: string; value: string }[];
  const fact = facts.find(item => item.value.includes('12')) ?? facts[0];
  expect(fact, JSON.stringify(facts)).toBeTruthy();
  const confirmed = await request.patch(`/api/v1/projects/${projectId}/facts/${fact.id}`, { headers: await write(), data: { status: 'confirmed', reason: '核对原文' } });
  expect(confirmed.ok(), await confirmed.text()).toBeTruthy();
  const current = await workspace();
  const chapter = current.chapters.find((c: { volume: string }) => c.volume === 'technical');
  const body = `服务期为 {{fact:${fact.id}}}，期满后续签。`;
  const lock = await (await request.post(`/api/chapters/${chapter.id}/lock`, { headers: auth, data: {} })).json();
  const committed = await request.post(`/api/chapters/${chapter.id}/versions`, { headers: auth, data: {
    lease_token: lock.lease_token, base_revision: chapter.revision, content: body, idempotency_key: crypto.randomUUID(),
    input_fingerprint: current.input_fingerprint } });
  expect(committed.ok(), await committed.text()).toBeTruthy();
  await request.post(`/api/chapters/${chapter.id}/lock/release`, { headers: auth, data: { lease_token: lock.lease_token } });
  return { projectId, chapterId: chapter.id as string, auth, body, fact };
}

test('variables show the confirmed value; a new unknown variable is refused on commit', async ({ page, request }) => {
  const { projectId, chapterId, auth, body, fact } = await seed(request);
  await page.goto(`/projects/${projectId}/editor`);
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();

  const chip = page.getByTestId('unheld-editor-text').getByTestId('variable-node');
  await expect(chip).toHaveAttribute('data-status', 'valid');
  await expect(chip).toContainText(fact.value.replace(/\s+/g, '').slice(0, 2));
  await expect(page.getByTestId('unheld-editor-text')).not.toContainText('{{fact:');

  await page.getByTestId('unheld-acquire-btn').click();
  const box = page.locator('textarea.chapter-editor');
  await expect(box).toHaveValue(body);
  await expect(page.getByTestId('editor-variable-bar').getByTestId('variable-node')).toHaveAttribute('data-status', 'valid');

  await box.fill(`${body}\n另有 {{fact:not-a-fact}} 项。`);
  await expect(page.getByTestId('invalid-variables-notice')).toContainText('1 个变量已失效');
  await page.getByRole('button', { name: '提交本节' }).click();
  await expect(page.getByTestId('editor-center-section').getByText(/写入了 1 个失效变量/)).toBeVisible();
  await expect(page.getByRole('button', { name: '去项目事实表' }).first()).toBeVisible();
  const kept = await (await request.get(`/api/chapters/${chapterId}`, { headers: auth })).json();
  expect(kept.content).toBe(body);
});
