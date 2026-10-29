// 为什么有这个文件：在真实浏览器里走一遍编辑台选区改写（APP-M2-T178/T185）：选中一句 → 问对话助手 → 3 种写法 →
// 替换选中内容 → 差异确认 → 写入新版本并显示复查结果。
// 后端调用的是 OpenAI 兼容接口；这里在本机起一个按写法返回固定文字的小服务，并通过“模型配置”接口绑定到用例自己建的项目，
// 不改动其他用例共用的示例项目。
import { createServer, type Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import { expect, test, type APIRequestContext } from '@playwright/test';

const BODY = '技术方案：每月安排巡检，报告由负责人复核。';
const PICK = '每月安排巡检';
const REPLIES: [string, string][] = [['正式、规范', '每月开展一次例行巡检'], ['删去冗余', '每月巡检'], ['实质性响应', '按月巡检并提交巡检报告']];

let server: Server;
let baseUrl = '';
const prompts: string[] = [];

test.beforeAll(async () => {
  server = createServer((req, res) => {
    let raw = '';
    req.on('data', chunk => { raw += chunk; });
    req.on('end', () => {
      const body = JSON.parse(raw || '{}') as { messages?: { role: string; content: string }[] };
      const system = body.messages?.find(m => m.role === 'system')?.content ?? '';
      prompts.push(body.messages?.find(m => m.role === 'user')?.content ?? '');
      const text = REPLIES.find(([hint]) => system.includes(hint))?.[1] ?? '每月巡检一次';
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ choices: [{ message: { role: 'assistant', content: text } }] }));
    });
  });
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  baseUrl = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

test.afterAll(async () => { await new Promise(resolve => server.close(resolve)); });

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const created = await request.post('/api/v1/projects', { headers: auth, data: { name: `选区改写-${Date.now()}` } });
  const projectId = (await created.json()).id as string;
  const workspace = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const chapter = workspace.chapters.find((c: { volume: string }) => c.volume === 'technical');
  const lock = await (await request.post(`/api/chapters/${chapter.id}/lock`, { headers: auth, data: {} })).json();
  const committed = await request.post(`/api/chapters/${chapter.id}/versions`, { headers: auth, data: {
    lease_token: lock.lease_token, base_revision: chapter.revision, content: BODY, idempotency_key: crypto.randomUUID() } });
  expect(committed.ok(), await committed.text()).toBeTruthy();
  await request.post(`/api/chapters/${chapter.id}/lock/release`, { headers: auth, data: { lease_token: lock.lease_token } });
  const config = await request.post('/api/v1/model-configs', { headers: auth, data: {
    id: `e2e-rewrite-${Date.now()}`, name: '用例模型', provider: 'openai-compatible', base_url: baseUrl, model: 'fake-rewrite',
    is_local: true, allow_sensitive: true, stream_enabled: false, timeout_seconds: 10 } });
  expect(config.ok(), await config.text()).toBeTruthy();
  const bound = await request.post(`/api/v1/projects/${projectId}/model-config`, { headers: auth, data: { model_config_id: (await config.json()).id } });
  expect(bound.ok(), await bound.text()).toBeTruthy();
  return { projectId, chapterId: chapter.id as string, auth };
}

test('select a sentence, get three rewrites, replace the selection after confirming the diff', async ({ page, request }) => {
  const { projectId, chapterId, auth } = await seed(request);
  await page.goto(`/projects/${projectId}/editor`);
  await page.getByTestId('login-username-input').fill('alpha-manager');
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await page.getByTestId('unheld-acquire-btn').click();
  const box = page.locator('textarea.chapter-editor');
  await expect(box).toHaveValue(BODY);
  // 像用户一样用键盘选中“每月安排巡检”
  await box.click();
  await page.keyboard.press('ControlOrMeta+Home');
  for (let i = 0; i < BODY.indexOf(PICK); i += 1) await page.keyboard.press('ArrowRight');
  for (let i = 0; i < PICK.length; i += 1) await page.keyboard.press('Shift+ArrowRight');
  await page.getByTestId('bubble-polish-btn').click();
  await expect(page.getByTestId('rewrite-selection')).toHaveText(PICK);
  await page.getByTestId('rewrite-generate-btn').click();
  await expect(page.getByTestId('rewrite-sample')).toHaveCount(3);
  expect(prompts.every(text => text.includes(`【选中的文字】\n${PICK}`) && !text.includes('报告由负责人复核。\n'))).toBeTruthy();
  const first = page.getByTestId('rewrite-sample').filter({ hasText: '每月开展一次例行巡检' });
  await first.getByTestId('rewrite-replace-btn').click();
  await expect(page.getByTestId('rewrite-diff').locator('ins')).not.toHaveCount(0);
  await expect(page.getByTestId('rewrite-diff').locator('del')).not.toHaveCount(0);
  await page.getByTestId('rewrite-confirm-btn').click();
  await expect(box).toHaveValue('技术方案：每月开展一次例行巡检，报告由负责人复核。');
  await expect(page.getByTestId('rewrite-recheck')).toContainText('对话助手替换');
  const operations = await (await request.get(`/api/v1/projects/${projectId}/chapters/${chapterId}/edit-operations`, { headers: auth })).json();
  expect(operations.operations).toHaveLength(1);
  expect(operations.operations[0].original_text).toBe(PICK);
});
