// 为什么有这个文件：在真实浏览器里走一遍段落锁定（APP-M2-T163）：光标放进一段 → 锁定 → 改动这段提交被拒 →
// 只改别的段提交成功 → 解除锁定。用例自己建项目，不改动其他用例共用的示例项目。
import { expect, test, type APIRequestContext } from '@playwright/test';

const LOCKED = '本项目提供七乘二十四小时驻场运维。';
const BODY = `运维服务方案\n\n${LOCKED}\n\n巡检每月一次。`;

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const created = await request.post('/api/v1/projects', { headers: auth, data: { name: `段落锁定-${Date.now()}` } });
  const projectId = (await created.json()).id as string;
  const workspace = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const chapter = workspace.chapters.find((c: { volume: string }) => c.volume === 'technical');
  const lock = await (await request.post(`/api/chapters/${chapter.id}/lock`, { headers: auth, data: {} })).json();
  const committed = await request.post(`/api/chapters/${chapter.id}/versions`, { headers: auth, data: {
    lease_token: lock.lease_token, base_revision: chapter.revision, content: BODY, idempotency_key: crypto.randomUUID() } });
  expect(committed.ok(), await committed.text()).toBeTruthy();
  await request.post(`/api/chapters/${chapter.id}/lock/release`, { headers: auth, data: { lease_token: lock.lease_token } });
  return { projectId, chapterId: chapter.id as string, auth };
}

test('lock a paragraph, a commit that changes it is refused, then unlock', async ({ page, request }) => {
  const { projectId, chapterId, auth } = await seed(request);
  await page.goto(`/projects/${projectId}/editor`);
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await page.getByTestId('unheld-acquire-btn').click();
  const box = page.locator('textarea.chapter-editor');
  await expect(box).toHaveValue(BODY);
  // 光标放进要锁的段落
  await box.click();
  await page.keyboard.press('ControlOrMeta+Home');
  for (let i = 0; i < BODY.indexOf(LOCKED) + 3; i += 1) await page.keyboard.press('ArrowRight');
  await page.getByTestId('paragraph-lock-btn').hover();
  await expect(page.getByTestId('paragraph-lock-btn')).toHaveText('锁定光标所在段落');
  await page.getByTestId('paragraph-lock-btn').click();
  await expect(page.getByTestId('paragraph-lock-count')).toHaveText('已锁定 1');
  await expect(page.getByTestId('locked-paragraphs-notice')).toContainText(LOCKED);

  // 改动锁定段落后提交：后台拒绝，正文不变
  await box.fill(BODY.replace('驻场运维', '远程运维'));
  await page.getByRole('button', { name: '提交本节' }).click();
  await expect(page.getByTestId('editor-center-section').getByText(/改动或删除了 1 个已锁定段落/)).toBeVisible();
  const kept = await (await request.get(`/api/chapters/${chapterId}`, { headers: auth })).json();
  expect(kept.content).toBe(BODY);

  // 只改别的段落：可以提交
  await box.fill(BODY.replace('每月一次', '每两周一次'));
  await page.getByRole('button', { name: '提交本节' }).click();
  await expect(page.getByText(/已提交正文 v/)).toBeVisible();

  // 解除锁定
  await page.getByTestId('paragraph-lock-count').click();
  await page.getByTestId('paragraph-unlock-btn').click();
  await expect(page.getByTestId('paragraph-lock-count')).toHaveText('已锁定 0');
  const locks = await (await request.get(`/api/v1/projects/${projectId}/chapters/${chapterId}/paragraph-locks`, { headers: auth })).json();
  expect(locks.locks).toHaveLength(0);
});
