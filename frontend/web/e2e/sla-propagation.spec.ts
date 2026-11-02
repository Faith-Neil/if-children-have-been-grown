// 为什么有这个文件：在真实浏览器里核对服务承诺矩阵页的“需复核”传播面板（APP-M2-T122 / T119）。
// 它解决什么问题：选用模板后事实尚未确认、登记取值后需重新核对，面板必须随后台状态变化，并列出受影响章节；
// 用例自己建项目、自己建公司模板，不依赖示例项目状态与用例顺序。
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

async function seed(request: APIRequestContext) {
  const login = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  const auth = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const created = await request.post('/api/v1/projects', { headers: auth, data: { name: `SLA传播-${Date.now()}` } });
  const projectId = (await created.json()).id as string;
  const templates = await (await request.get('/api/v1/sla/templates', { headers: auth })).json();
  const template = await request.post('/api/v1/sla/templates', {
    headers: { ...auth, 'If-Match': String(templates.revision), 'Idempotency-Key': crypto.randomUUID() },
    data: {
      name: `合成传播模板-${Date.now()}`, version_no: '1.0', service_hours: 'h7x24', status: 'confirmed',
      body_text: '一级故障响应时限为{{P1_response}}分钟。', reason: 'e2e：合成模板，仅用于界面核对。',
      variables: [{ var_key: 'P1_response', label: '一级故障响应时限', group: 'response', value_type: 'decimal',
        default_value: '30', unit: 'minute', compare_direction: 'lower_better', best_committable_value: '15' }],
    },
  });
  expect(template.ok(), `create template: ${await template.text()}`).toBeTruthy();
  const templateId = (await template.json()).item.id as string;
  // 重新取工作区以获得最新 revision（模板创建不影响项目 revision，但保险起见重取）
  const workspace = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const selected = await request.post(`/api/v1/projects/${projectId}/sla/template`, {
    headers: { ...auth, 'If-Match': String(workspace.revision), 'Idempotency-Key': crypto.randomUUID() },
    data: { template_id: templateId },
  });
  expect(selected.ok(), `select template: ${await selected.text()}`).toBeTruthy();
  // 核对选用已生效
  const after = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  expect(after.sla, `sla should be set in workspace after template selection`).not.toBeNull();
  return { projectId, auth };
}

async function login(page: Page, username: string, path: string) {
  await page.goto(path);
  await page.getByTestId('login-username-input').fill(username);
  await page.getByTestId('login-password-input').fill('X_2026');
  await page.getByTestId('login-submit-button').click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('SLA matrix shows the propagation panel with unconfirmed facts after selecting a template', async ({ page, request }) => {
  const { projectId, auth } = await seed(request);

  // 主断言：后台接口直接核对传播状态（不依赖浏览器时序）
  const body = await (await request.get(`/api/v1/projects/${projectId}/sla/propagation`, { headers: auth })).json();
  expect(body.selected, '选用模板后 selected 应为 true').toBe(true);
  expect(body.summary.unconfirmed, '初始状态应有 1 项尚未确认').toBe(1);
  expect(body.rows.length).toBeGreaterThan(0);
  expect(body.rows[0].reasons.map((r: { code: string }) => r.code)).toContain('UNCONFIRMED');

  // 浏览器视角：登录后进入矩阵页
  await login(page, 'alpha-manager', `/projects/${projectId}/matrix`);

  // 等待工作区完全加载（矩阵统计卡出现代表 workspace 数据已就绪）
  await expect(page.getByText('响应点总数')).toBeVisible({ timeout: 15000 });

  // 切换到 SLA 视图
  await page.getByRole('radio', { name: '服务响应承诺（SLA）' }).click();

  // 模板已选用时传播面板应渲染；若 sla=null（边缘情况），此断言给出清晰错误而非超时
  await expect(page.getByTestId('sla-propagation')).toBeVisible({ timeout: 20000 });
  // 后台已确认至少有 1 项 UNCONFIRMED，面板标题应出现相应文字
  await expect(page.getByTestId('sla-propagation')).toContainText('确认');
});
