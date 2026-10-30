// 为什么有这个文件：在真实浏览器里走一遍编辑台问题标注与侧栏联动（APP-M2-T166）：
// 重新检查查出两段问题 → 正文段落标问题数 → 问题页签列出、定位到段落高亮 → 点段落标记只看这一段 →
// 取得编辑权后定位，编辑框选中整段。用例自己建项目，不改动共用的示例项目。
import { expect, test, type APIRequestContext } from '@playwright/test';

const TENDER = '合成招标文件：问题联动验收\n招标编号：E2E-ISSUE\n第三章 技术要求\n1. 提供7×24小时驻场服务。\n';
const BODY = ['第一段：每月安排巡检并提交巡检报告。', '', '第二段：我司无法提供全天候驻场。', '第三段：项目业绩见【待补：同类业绩】。'].join('\n');

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const projectId = (await (await request.post('/api/v1/projects', { headers: auth, data: { name: `问题联动-${Date.now()}` } })).json()).id as string;
  const workspace = async () => (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const write = async () => ({ ...auth, 'If-Match': String((await workspace()).revision), 'Idempotency-Key': crypto.randomUUID() });
  const up = await request.post(`/api/v1/projects/${projectId}/files/raw?filename=tender.txt`, {
    headers: { ...(await write()), 'Content-Type': 'application/octet-stream' }, data: Buffer.from(TENDER, 'utf-8') });
  expect(up.ok(), await up.text()).toBeTruthy();
  const parsed = await request.post(`/api/v1/projects/${projectId}/parse`, { headers: await write(), data: {} });
  expect(parsed.ok(), await parsed.text()).toBeTruthy();
  const current = await workspace();
  const chapter = current.chapters.find((c: { volume: string }) => c.volume === 'technical');
  const lock = await (await request.post(`/api/chapters/${chapter.id}/lock`, { headers: auth, data: {} })).json();
  const committed = await request.post(`/api/chapters/${chapter.id}/versions`, { headers: auth, data: {
    lease_token: lock.lease_token, base_revision: chapter.revision, content: BODY, idempotency_key: crypto.randomUUID(),
    input_fingerprint: current.input_fingerprint } });
  expect(committed.ok(), await committed.text()).toBeTruthy();
  await request.post(`/api/chapters/${chapter.id}/lock/release`, { headers: auth, data: { lease_token: lock.lease_token } });
  const recheck = await request.post(`/api/v1/projects/${projectId}/chapters/${chapter.id}/loop/recheck`, { headers: await write(), data: {} });
  expect(recheck.ok(), await recheck.text()).toBeTruthy();
  return { projectId, chapterId: chapter.id as string };
}

test('issues are marked on paragraphs, listed in the side panel and located both ways', async ({ page, request }) => {
  const { projectId, chapterId } = await seed(request);
  await page.goto(`/projects/${projectId}/editor/${chapterId}`);
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();

  const text = page.getByTestId('unheld-editor-text');
  await expect(text.getByTestId('paragraph-issue-marker')).toHaveCount(2);
  await page.getByRole('tab', { name: /问题/ }).click();
  const panel = page.getByTestId('editor-issue-panel');
  await expect(panel.getByTestId('issue-item')).toHaveCount(2);

  // 侧栏 → 正文：定位后该段高亮
  const deviation = panel.getByTestId('issue-item').filter({ hasText: '无法提供' });
  const key = await deviation.getAttribute('data-paragraph-key');
  expect(key).toBeTruthy();
  await deviation.getByTestId('issue-locate').click();
  await expect(text.locator(`p[data-paragraph-key="${key}"]`)).toHaveClass(/paragraph-focused/);

  // 正文 → 侧栏：点段落标记只看这一段的问题
  await text.locator(`p[data-paragraph-key="${key}"]`).getByTestId('paragraph-issue-marker').click();
  await expect(panel.getByTestId('issue-paragraph-filter')).toBeVisible();
  await expect(panel.getByTestId('issue-item')).toHaveCount(1);
  await expect(panel.getByTestId('issue-item')).toContainText('无法提供');

  // 持锁编辑时定位：编辑框选中整段
  await page.getByTestId('unheld-acquire-btn').click();
  const box = page.locator('textarea.chapter-editor');
  await expect(box).toHaveValue(BODY);
  await panel.getByTestId('issue-locate').click();
  const selected = await box.evaluate((el: HTMLTextAreaElement) => el.value.slice(el.selectionStart, el.selectionEnd));
  expect(selected).toBe('第二段：我司无法提供全天候驻场。');
});
