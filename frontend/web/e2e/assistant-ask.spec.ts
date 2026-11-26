// 为什么有这个文件：在真实浏览器里走一遍编辑台自由提问（APP-M2-T179、T177）：不选中文字直接提问 → 回答逐字流式出现 →
// 只能复制、没有写入按钮；本机起一个按 SSE 分段返回的 OpenAI 兼容小服务，绑定到用例自己建的项目。
import { createServer, type Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import { expect, test, type APIRequestContext } from '@playwright/test';

const ANSWER = ['建议写明', '每月巡检的范围、', '时间和报告提交方式。'];
let server: Server;
let baseUrl = '';

test.beforeAll(async () => {
  server = createServer((req, res) => {
    req.on('data', () => undefined);
    req.on('end', () => {
      res.writeHead(200, { 'Content-Type': 'text/event-stream' });
      for (const piece of ANSWER) res.write(`data: ${JSON.stringify({ choices: [{ delta: { content: piece } }] })}\n\n`);
      res.end('data: [DONE]\n\n');
    });
  });
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  baseUrl = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

test.afterAll(async () => { await new Promise(resolve => server.close(resolve)); });

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const created = await request.post('/api/v1/projects', { headers: auth, data: { name: `自由提问-${Date.now()}` } });
  const projectId = (await created.json()).id as string;
  const workspace = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const chapter = workspace.chapters.find((item: { volume: string }) => item.volume === 'technical');
  const lock = await (await request.post(`/api/chapters/${chapter.id}/lock`, { headers: auth, data: {} })).json();
  const committed = await request.post(`/api/chapters/${chapter.id}/versions`, { headers: auth, data: {
    lease_token: lock.lease_token, base_revision: chapter.revision,
    content: '运维服务方案\n\n每月安排巡检，覆盖机房、网络和终端，并提交巡检报告。',
    idempotency_key: crypto.randomUUID() } });
  expect(committed.ok(), await committed.text()).toBeTruthy();
  await request.post(`/api/chapters/${chapter.id}/lock/release`, { headers: auth, data: { lease_token: lock.lease_token } });
  const adminLogin = await request.post('/api/v1/auth/login', { data: { username: 'alpha-company-admin', password: 'X_2026' } });
  const admin = { Authorization: `Bearer ${(await adminLogin.json()).access_token}` };
  const config = await request.post('/api/v1/model-configs', { headers: admin, data: {
    id: `e2e-ask-${Date.now()}`, name: '问答用例模型', provider: 'openai-compatible', base_url: baseUrl, model: 'fake-ask',
    is_local: true, allow_sensitive: true, stream_enabled: true, timeout_seconds: 10 } });
  expect(config.ok(), await config.text()).toBeTruthy();
  const bound = await request.post(`/api/v1/projects/${projectId}/model-config`, { headers: auth, data: { model_config_id: (await config.json()).id } });
  expect(bound.ok(), await bound.text()).toBeTruthy();
  return { projectId };
}

test('ask without a selection, the answer streams in and can only be copied', async ({ page, request }) => {
  const { projectId } = await seed(request);
  await page.goto(`/projects/${projectId}/editor`);
  const usernameInput = page.getByTestId('login-username-input');
  if (await usernameInput.isVisible({ timeout: 5000 }).catch(() => false)) {
    await usernameInput.fill('alpha-manager');
    await page.getByTestId('login-password-input').fill('X_2026');
    await page.getByTestId('login-submit-button').click();
  }
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
  const kb = page.getByTestId('assistant-kb-switch');
  await expect(kb).toBeVisible();
  if (await kb.isChecked()) await kb.click();
  await page.getByRole('button', { name: '问答写作' }).click();
  await page.getByRole('textbox', { name: '问答写作' }).fill('巡检这一节应该写哪些要点？');
  await page.getByTestId('assistant-ask-btn').click();
  const answer = page.getByTestId('assistant-answer');
  await expect(answer).toContainText(ANSWER.join(''));
  await expect(answer.getByRole('button', { name: '复制' })).toBeVisible();
  await expect(answer.getByRole('button', { name: /替换|插在/ })).toHaveCount(0);
  await expect(page.getByTestId('assistant-session-history')).toBeVisible();
});
