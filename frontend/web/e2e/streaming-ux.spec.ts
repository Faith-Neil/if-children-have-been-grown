// 为什么有这个文件：用模拟 SSE 在真实浏览器验证 Gemini 风格柔和流式输出，而不是伪造真实模型验收。
// 它解决什么问题：阶段胶囊、文字渐显、表格中间态、跟随滚动、回到底部与完成交接必须有浏览器证据。

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

function frame(event: Record<string, unknown>) {
  return `event: ${String(event.event)}\ndata: ${JSON.stringify(event)}\n\n`;
}

async function login(page: Page, username: string, path: string) {
  await page.goto(path);
  await page.getByTestId('login-username-input').fill(username);
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

async function managerAuth(request: APIRequestContext) {
  const loginResponse = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  expect(loginResponse.ok()).toBeTruthy();
  return { Authorization: `Bearer ${(await loginResponse.json()).access_token}` };
}

function leafKey(heading: { task_id?: string | null; requirement_id?: string | null; number?: string }) {
  return heading.task_id?.trim() || heading.requirement_id?.trim() || (heading.number ?? '').trim();
}

function withStreamingOutline(workspace: any) {
  const chapter = workspace.chapters.find((item: { volume: string }) => item.volume === 'technical');
  chapter.permissions = { ...(chapter.permissions ?? {}), generate: true, edit: true };
  workspace.plan_confirmed = true;
  workspace.parse_confirmed = true;
  workspace.technical_outline = {
    chapter_id: chapter.id,
    title: '技术方案',
    headings: [
      { level: 1, number: '1', title: '总体方案', task_id: null, requirement_id: null },
      { level: 2, number: '1.1', title: '巡检服务', task_id: 'sim-stream-section', requirement_id: null },
    ],
    missing: [],
    unassigned_requirements: [],
  };
  return workspace;
}

async function installWorkspaceRoute(page: Page, workspace: any) {
  await page.route('**/api/v1/projects/alpha-project/workspace', route => route.fulfill({ json: workspace }));
}

test('simulated SSE renders stage capsule, safe markdown, smart scroll and final handoff', async ({ page, request }) => {
  const auth = await managerAuth(request);
  const baseWorkspace = await (await request.get('/api/v1/projects/alpha-project/workspace', { headers: auth })).json();
  const workspace = withStreamingOutline(baseWorkspace);
  await installWorkspaceRoute(page, workspace);
  const outline = workspace.technical_outline;
  const heading = outline.headings.find((item: { task_id?: string | null; requirement_id?: string | null }) => item.task_id || item.requirement_id);
  const sectionId = leafKey(heading);
  const paragraphs = Array.from({ length: 18 }, (_, index) => `第 ${index + 1} 段巡检响应正文，围绕实施组织、质量控制、服务承诺与验收协同展开，确保长文滚动时有足够内容。`).join('\n');
  const body = `${paragraphs}\n这里包含**重点加粗承诺**和<u>关键下划线响应</u>。\n| 巡检服务项目分项明细与实施频次安排 | 响应承诺与交付物说明 |\n| --- | --- |\n| 巡检频率 | 完全满足 |\n结尾正式落盘内容。`;
  const chunks = body.match(/[\s\S]{1,96}/g) ?? [body];
  let streamRequested = false;
  await page.route('**/api/v1/projects/alpha-project/technical-volume/stream', async route => {
    streamRequested = true;
    // 首包稍作延迟，让浏览器有机会画出不遮挡正文的等待胶囊；后续正文仍由 TextReveal 柔和追赶。
    await new Promise(resolve => setTimeout(resolve, 500));
    const events = [
      { event: 'session.started', job_id: 'simulated-stream-job' },
      { event: 'sections.fanout', concurrency: 1, section_ids: [sectionId] },
      { event: 'section.started', section_id: sectionId, title: heading.title },
      { event: 'task.patched', task_id: sectionId, stage: 'retrieve', generation_status: 'running' },
      { event: 'task.patched', task_id: sectionId, stage: 'deviate', generation_status: 'running' },
      { event: 'session.live' },
      { event: 'task.patched', task_id: sectionId, stage: 'write_section', generation_status: 'running' },
      ...chunks.map(text => ({ event: 'section.delta', section_id: sectionId, text })),
      { event: 'section.done', section_id: sectionId, text: body },
      { event: 'volume.done', chapter_id: outline.chapter_id, revision: workspace.revision + 1, failed: [], replay: false },
    ].map(frame).join('');
    await route.fulfill({ status: 200, contentType: 'text/event-stream', body: events });
  });
  await page.route(`**/api/chapters/${outline.chapter_id}`, async route => {
    if (!streamRequested || route.request().method() !== 'GET') return route.continue();
    const response = await route.fetch();
    const detail = await response.json();
    detail.content = `${heading.number} ${heading.title}\n${body}\n`;
    detail.revision = workspace.revision + 1;
    detail.draft = null;
    return route.fulfill({ response, json: detail });
  });

  await login(page, 'alpha-manager', '/projects/alpha-project/editor');
  await expect(page.getByTestId('paper-editor')).toBeVisible();
  await page.getByTestId('main-path-generate').click();

  await expect(page.getByTestId('streaming-paper-view')).toBeVisible();
  await expect(page.getByTestId('stream-stage-capsule')).toContainText(/正在准备|正在检索|正在核对|正在撰写/);
  await expect(page.locator('.paper-wait')).toHaveCount(0);
  await expect(page.getByTestId('stream-cursor')).toBeVisible();
  // 滚动断言先行：滴显时长有限，趁正文仍在生长时完成跟随/暂停/定位验证。
  const scroller = page.locator('.editor-scroll');
  // 等跟随滚动真实发生（scrollTop 明显离开顶部），后面的手动上翻才能构成有效偏差。
  await expect.poll(async () => scroller.evaluate(node => node.scrollTop > 100), { timeout: 15_000 }).toBe(true);
  // 自然跟随阶段：用户未操作时，活跃光标始终保持在视口内（不会停在空白纸面或滚出视野）。
  await expect.poll(async () => page.locator('.stream-cursor').evaluate(node => {
    const host = node.closest('.editor-scroll');
    if (!(host instanceof HTMLElement)) return false;
    const caretRect = node.getBoundingClientRect();
    const rect = host.getBoundingClientRect();
    return caretRect.top >= rect.top && caretRect.top <= rect.bottom;
  }), { timeout: 10_000 }).toBe(true);
  await scroller.evaluate(node => { node.scrollTop = 0; node.dispatchEvent(new Event('scroll', { bubbles: true })); });
  await expect(page.getByTestId('stream-locate-writing')).toBeVisible();
  await page.getByTestId('stream-locate-writing').click();
  // 点击后光标被平滑带回视口舒适区（约 65%~75% 高度处），而不是整篇文档最底端。
  await expect.poll(async () => page.locator('.stream-cursor').evaluate(node => {
    const host = node.closest('.editor-scroll');
    if (!(host instanceof HTMLElement)) return false;
    const caretRect = node.getBoundingClientRect();
    const rect = host.getBoundingClientRect();
    const ratio = (caretRect.top - rect.top) / host.clientHeight;
    return ratio > 0.5 && ratio < 0.95;
  }), { timeout: 5_000 }).toBe(true);

  await expect(page.getByTestId('stream-table-placeholder')).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('.paper-streaming-view table')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId('streaming-paper-view')).toContainText('重点加粗承诺');

  await expect(page.getByTestId('streaming-paper-view')).toHaveCount(0, { timeout: 35_000 });
  await expect(page.locator('.paper-editor-hidden')).toHaveCount(0);
  await expect(page.getByTestId('paper-editor')).toContainText('结尾正式落盘内容');
  await expect(page.getByTestId('paper-editor')).toContainText('巡检频率');
});

test('simulated SSE failure rolls back without a streaming canvas and explains the failure', async ({ page, request }) => {
  const auth = await managerAuth(request);
  const baseWorkspace = await (await request.get('/api/v1/projects/alpha-project/workspace', { headers: auth })).json();
  const workspace = withStreamingOutline(baseWorkspace);
  await installWorkspaceRoute(page, workspace);
  const heading = workspace.technical_outline.headings.find((item: { task_id?: string | null; requirement_id?: string | null }) => item.task_id || item.requirement_id);
  const sectionId = leafKey(heading);
  await page.route('**/api/v1/projects/alpha-project/technical-volume/stream', async route => {
    const events = [
      { event: 'session.started', job_id: 'simulated-failed-job' },
      { event: 'sections.fanout', concurrency: 1, section_ids: [sectionId] },
      { event: 'section.started', section_id: sectionId, title: heading.title },
      { event: 'session.live' },
      { event: 'volume.failed', message: '模拟生成中断' },
    ].map(frame).join('');
    await route.fulfill({ status: 200, contentType: 'text/event-stream', body: events });
  });
  await login(page, 'alpha-manager', '/projects/alpha-project/editor');
  await page.getByTestId('main-path-generate').click();
  await expect(page.getByText(/生成失败：模拟生成中断|生成没有完成/)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId('streaming-paper-view')).toHaveCount(0);
});
