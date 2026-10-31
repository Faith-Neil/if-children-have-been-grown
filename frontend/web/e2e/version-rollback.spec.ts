// 为什么有这个文件：在真实浏览器里走一遍版本对比与回退（APP-M2-T175）：打开版本历史 → 逐段对比 → 回退到旧版本 →
// 生成新版本、修改方式记“版本回退”，历史保留。用例自己建项目，不改动其他用例共用的示例项目。
import { expect, test, type APIRequestContext } from '@playwright/test';

const V1 = '运维服务方案\n\n驻场工程师两名，七乘二十四小时值守。';
const V2 = '运维服务方案\n\n驻场工程师一名，七乘二十四小时值守。\n\n应急演练每季度一次。';

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const created = await request.post('/api/v1/projects', { headers: auth, data: { name: `版本回退-${Date.now()}` } });
  const projectId = (await created.json()).id as string;
  const workspace = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const chapter = workspace.chapters.find((c: { volume: string }) => c.volume === 'technical');
  const lock = await (await request.post(`/api/chapters/${chapter.id}/lock`, { headers: auth, data: {} })).json();
  let revision = chapter.revision as number;
  for (const body of [V1, V2]) {
    const committed = await request.post(`/api/chapters/${chapter.id}/versions`, { headers: auth, data: {
      lease_token: lock.lease_token, base_revision: revision, content: body, idempotency_key: crypto.randomUUID() } });
    expect(committed.ok(), await committed.text()).toBeTruthy();
    revision = (await committed.json()).revision;
  }
  await request.post(`/api/chapters/${chapter.id}/lock/release`, { headers: auth, data: { lease_token: lock.lease_token } });
  return { projectId, chapterId: chapter.id as string, auth, revision };
}

test('compare paragraphs with an older version and roll back to it', async ({ page, request }) => {
  const { projectId, chapterId, auth, revision } = await seed(request);
  await page.goto(`/projects/${projectId}/editor`);
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await page.getByTestId('unheld-acquire-btn').click();
  await expect(page.locator('textarea.chapter-editor')).toHaveValue(V2);

  await page.getByRole('button', { name: '版本' }).click();
  await page.getByText('逐段对比', { exact: true }).click();
  await expect(page.getByTestId('version-diff-summary')).toContainText(`v${revision - 1} → v${revision}：改动 1 段，新增 1 段`);
  await expect(page.getByTestId('version-diff').locator('[data-change="changed"] del')).not.toHaveCount(0);

  await page.getByTestId(`rollback-btn-${revision - 1}`).click();
  await page.getByRole('button', { name: '确认回退' }).click();
  await expect(page.locator('textarea.chapter-editor')).toHaveValue(V1);
  await expect(page.getByText(`已回退到 v${revision - 1}，生成新版本 v${revision + 1}`)).toBeVisible();

  const history = await (await request.get(`/api/chapters/${chapterId}/versions`, { headers: auth })).json();
  const latest = history.versions[history.versions.length - 1];
  expect(latest.revision).toBe(revision + 1);
  expect(latest.edit_mode).toBe('rollback');
  expect(history.versions.some((v: { content: string }) => v.content === V2)).toBeTruthy();
});
